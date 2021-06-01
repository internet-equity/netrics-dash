import pathlib
import re

from argcmdr import (
    Local,
    LocalRoot,
    localmethod,
)


NETRICS_USER = 'ubuntu'
NETRICS_HOST = 'netrics.local'


REPO_PATH = pathlib.Path(__file__).absolute().parent


def stream_requirements(file_path):
    for line in file_path.read_text().splitlines():
        spec = re.sub(r'#.*$', '', line).strip()
        if spec:
            yield spec


DEPENDENCIES = ' '.join(stream_requirements(REPO_PATH / 'dependency' / 'main.txt'))

REQUIREMENTS = ' '.join(stream_requirements(REPO_PATH / 'requirement' / 'main.txt'))


class Management(LocalRoot):
    """manage dashboard project"""


@Management.register
class Dash(Local):
    """manage local dashboard"""

    @localmethod('--username', default=NETRICS_USER, metavar='NAME',
                 help="netrics host username (default: %(default)s)")
    @localmethod('--host', default=NETRICS_HOST, metavar='NETLOC',
                 help="netrics local hostname or network locator (default: %(default)s)")
    def provision(self, args):
        """set up a local raspberry pi"""
        rpi_cmd = self.local['ssh'][f'{args.username}@{args.host}']

        # for now ...
        #
        # 1. scp tar'd src to rpi
        #
        yield self.local.FG, self.local['tar'][
            '-c',
            '-z',
            '--directory', REPO_PATH,
            'src',
        ] | rpi_cmd[
            # ssh-tar reads from stdin b/c it's awesome
            '''
                rm -rf /tmp/netrics-dash
                mkdir /tmp/netrics-dash
                tar -xz -C /tmp/netrics-dash
            '''
        ]

        #
        # 2. ensure dependencies on rpi
        #
        yield self.local.FG, rpi_cmd[
            f'''
                sudo apt-get install -y {DEPENDENCIES}
                sudo modprobe tcp_bbr

                sudo pip install {REQUIREMENTS}
            '''
        ]

        #
        # 3. set up ndt
        #
        # FIXME: should be able to build in dev (with multiarch support) and push/pull instead
        # FIXME: (and then can just grab script from repo rather than clone)
        yield self.local.FG, rpi_cmd[
            r'''
                cd /tmp/

                if [ -d ndt-server ]; then
                  cd ndt-server
                  git fetch --verbose origin master
                  UPDATED="$(git log --oneline origin/master...)"
                  if [ -n "$UPDATED" ]; then
                    git merge
                  fi
                else
                  git clone https://github.com/m-lab/ndt-server.git
                  UPDATED=true
                  cd ndt-server
                fi

                if [ ! -d certs ]; then
                  install -d certs datadir
                  ./gen_local_test_certs.bash
                fi

                if [ -n "$UPDATED" ]; then
                  sudo docker build . -t ndt-server

                  sudo docker stop ndt7 2>/dev/null
                  sudo docker rm ndt7 2>/dev/null

                  sudo docker run -d --restart=always       \
                    --network=host                          \
                    --volume `pwd`/certs:/certs:ro          \
                    --volume `pwd`/datadir:/datadir         \
                    --read-only                             \
                    --user `id -u`:`id -g`                  \
                    --cap-drop=all                          \
                    --name ndt7                             \
                    ndt-server                              \
                    -cert /certs/cert.pem                   \
                    -key /certs/key.pem                     \
                    -datadir /datadir                       \
                    -ndt7_addr :4443                        \
                    -ndt5_addr :3001                        \
                    -ndt5_wss_addr :3010                    \
                    -ndt7_addr_cleartext :8080
                fi
            '''
        ]

        #
        # 4. set up dashboard
        #
        # FIXME: apache worth re-consideration
        yield self.local.FG, rpi_cmd[
            r'''
                sudo rm -rf /var/www/html/dashboard \
                            /var/www/script/dashboard

                sudo mkdir -p /var/www/script \
                              /var/www/data/dashboard/

                sudo chown www-data:www-data /var/www/data/dashboard/

                sudo cp -r /tmp/netrics-dash/src/srv/static /var/www/html/dashboard
                sudo cp -r /tmp/netrics-dash/src/srv/pyscript /var/www/script/dashboard

                basename -s .py /var/www/script/dashboard/* |
                  xargs -I {} echo -e "WSGIScriptAlias /dashboard/{} \t /var/www/script/dashboard/{}.py" |
                  sudo tee /etc/apache2/conf-available/dashboard.conf

                sudo a2enconf dashboard >/dev/null
                sudo systemctl reload apache2
            '''
        ]
