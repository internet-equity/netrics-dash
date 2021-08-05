import grp
import os
import pathlib
import re

from argcmdr import Local, localmethod
from plumbum import colors
from plumbum.cmd import sudo
from plumbum.commands import ExecutionModifier


BINFMT_TAG = 'a7996909642ee92942dcd6cff44b9b95f08dad64'
BINFMT_TARGET = pathlib.Path('/proc/sys/fs/binfmt_misc/qemu-aarch64')

NDT_SERVER_TAG = 'v0.20.6'
NDT_SERVER_ORIGIN = 'm-lab/ndt-server'

NETRICS_USER = 'ubuntu'
NETRICS_HOST = 'netrics.local'


class _SHH(ExecutionModifier):
    """plumbum execution modifier to ensure output is not echoed to terminal

    essentially a no-op, this may be used to override argcmdr settings
    and cli flags controlling this feature, on a line-by-line basis, to
    hide unnecessary or problematic (e.g. highly verbose) command output.

    """
    __slots__ = ('retcode', 'timeout')

    def __init__(self, retcode=0, timeout=None):
        self.retcode = retcode
        self.timeout = timeout

    def __rand__(self, cmd):
        return cmd.run(retcode=self.retcode, timeout=self.timeout)


SHH = _SHH()


def stream_requirements(file_path):
    for line in file_path.read_text().splitlines():
        spec = re.sub(r'#.*$', '', line).strip()
        if spec:
            yield spec


REPO_PATH = pathlib.Path(__file__).absolute().parent

ENV_FILE = REPO_PATH / '.env'

DEPENDENCIES = ' '.join(stream_requirements(REPO_PATH / 'dependency' / 'main.txt'))


def version_type(value):
    if not re.match(r'\d\.\d\.\d', value):
        raise ValueError('invalid version number')

    return value


class Management(Local):
    """manage local dashboard project"""

    def __init__(self, parser):
        parser.add_argument(
            '--image-repo',
            default='chicagocdac',
            metavar='NAME|URI',
            help="Docker organization repository or generic image repository URI with which to "
                 "tag and to which to push built images (default: %(default)s)",
        )

        if any(grp.getgrgid(group).gr_name == 'docker' for group in os.getgroups()):
            self.docker = self.local['docker']
        else:
            self.docker = sudo['-E', '--preserve-env=PATH', 'docker']

    @localmethod('target', choices=('dash', 'ndt'), nargs='?',
                 help="build target (default: all)")
    @localmethod('--version', type=version_type,
                 help="version to apply to the local dashboard app (e.g.: 1.0.1)")
    @localmethod('--ndt-cache', default=(REPO_PATH / '.ndt-server'),
                 metavar='PATH', type=pathlib.Path,
                 help="path at which to cache the ndt-server repository (default: %(default)s)")
    @localmethod('--builder', default='netrics-dashboard', metavar='NAME',
                 help="name to assign to builder (default: %(default)s)")
    @localmethod('--binfmt', default=BINFMT_TAG, metavar='TAG',
                 help="Docker image tag of binfmt (default: %(default)s)")
    @localmethod('--push', action='store_true',
                 help="push images to remote repository (rather than load images locally)")
    @localmethod('--no-latest', action='store_false', dest='tag_latest',
                 help="do NOT tag images as \"latest\"")
    def build(self, args, parser):
        """build dashboard images for amd64 & arm64"""
        targets = {'dash', 'ndt'} if not args.target else {args.target}

        if 'dash' in targets:
            if not args.version:
                parser.error('--version required to build dash')
        elif args.version:
            parser.error('--version only applies to dash build')

        platforms = 'linux/amd64,linux/arm64' if args.push else 'linux/amd64'

        action = '--push' if args.push else '--load'

        if not BINFMT_TARGET.exists():
            yield self.local.FG, self.docker[
                'run',
                '--rm',
                '--privileged',
                f'docker/binfmt:{args.binfmt}',
            ]

        try:
            yield self.local.FG, self.docker[
                'buildx',
                'ls',
            ] | self.local['grep'][args.builder]
        except self.local.ProcessExecutionError:
            yield self.local.FG, self.docker[
                'buildx',
                'create',
                '--name', args.builder,
                '--platform', 'linux/amd64,linux/arm64',
            ]

        yield self.local.FG, self.docker[
            'buildx',
            'use',
            args.builder,
        ]

        if 'ndt' in targets:
            if not args.ndt_cache.exists():
                yield self.local.FG, self.local['git'][
                    'clone',
                    '--branch', NDT_SERVER_TAG,
                    '--config', 'advice.detachedHead=false',
                    '--depth', '1',
                    f'https://github.com/{NDT_SERVER_ORIGIN}.git',
                    args.ndt_cache,
                ]

            (_retcode, stdout, _stderr) = yield SHH, self.local['git'][
                '-C', args.ndt_cache,
                'describe',
                '--tag',
            ]
            ndt_tag = 'DRY.RUN' if stdout is None else stdout.strip()

            yield self.local.FG, self.docker[
                'buildx',
                'build',
                '--platform', platforms,
                '-t', f'{args.image_repo}/ndt-server:{ndt_tag}',
                ('-t', f'{args.image_repo}/ndt-server:latest') if args.tag_latest else (),
                args.ndt_cache,
                action,
            ]

        if 'dash' in targets:
            yield self.local.FG, self.docker[
                'buildx',
                'build',
                '--platform', platforms,
                '--build-arg', f'APPVERSION={args.version}',
                '-t', f'{args.image_repo}/netrics-dashboard:{args.version}',
                ('-t', f'{args.image_repo}/netrics-dashboard:latest') if args.tag_latest else (),
                REPO_PATH,
                action,
            ]

    @localmethod('--name', default='ndash',
                 help="name to apply to local dashboard container (default: %(default)s)")
    @localmethod('--version', default='latest',
                 help="version/tag of image to run (default: %(default)s)")
    @localmethod('--no-dev', action='store_false', dest='serve_dev',
                 help="do NOT mount the host filesystem's under-development "
                      "repository tree (src/) into the container and "
                      "do NOT configure server to autoreload source")
    def serve(self, args):
        """serve dashboard locally"""
        for cleanup_command in ('stop', 'rm'):
            try:
                yield SHH, self.docker[
                    cleanup_command,
                    args.name,
                ]
            except self.local.ProcessExecutionError:
                pass

        run_command = self.docker[
            'run',
            '-d',
            '-p', '8080:8080',
            '--name', args.name,
        ]

        if ENV_FILE.exists():
            run_command = run_command['--env-file', ENV_FILE]
        else:
            print('warning: dashboard will not operate correctly without environment values')
            print(f'tip: scp {NETRICS_HOST}:/etc/nm-exp-active-netrics/.env .')

        if args.serve_dev:
            yield self.local['mkdir']['-p', REPO_PATH / '.var']

            run_command = run_command[
                '--env', 'APP_RELOAD=1',
                '--volume', str(REPO_PATH / 'src') + ':/usr/src/dashboard',
                '--volume', str(REPO_PATH / '.var') + ':/var/lib/dashboard',
            ]

        yield SHH, run_command[
            f'{args.image_repo}/netrics-dashboard:{args.version}',
        ]

        if args.execute_commands:
            print('SUCCESS:' | colors.success,
                  'view local dashboard at',
                  'http://localhost:8080/' | colors.underline)

    @localmethod('--username', default=NETRICS_USER, metavar='NAME',
                 help="netrics host username (default: %(default)s)")
    @localmethod('--host', default=NETRICS_HOST, metavar='NETLOC',
                 help="netrics local hostname or network locator (default: %(default)s)")
    def provision(self, args):
        """set up a local raspberry pi"""
        yield self.local.FG, self.local['ssh'][f'{args.username}@{args.host}'][
            #
            # ensure dependencies on rpi
            #
            f'''
                sudo apt-get install -y {DEPENDENCIES}
                sudo modprobe tcp_bbr
            '''

            #
            # set up ndt-server
            #
            rf'''
                if [ ! -f /usr/local/bin/ndt-generate-local-test-certs ]; then
                  sudo curl \
                    -o /usr/local/bin/ndt-generate-local-test-certs \
                    https://raw.githubusercontent.com/{NDT_SERVER_ORIGIN}/{NDT_SERVER_TAG}/gen_local_test_certs.bash

                  sudo chmod 775 /usr/local/bin/ndt-generate-local-test-certs
                fi

                if [ ! -f /usr/local/lib/ndt-server/certs/cert.pem ]; then
                  sudo mkdir -p /usr/local/lib/ndt-server
                  pushd /usr/local/lib/ndt-server

                  sudo install -d certs datadir

                  sudo /usr/local/bin/ndt-generate-local-test-certs

                  sudo chown root:$(id -g) certs/key.pem
                  sudo chmod g+r certs/key.pem

                  sudo chown root:$(id -g) datadir
                  sudo chmod g+w datadir

                  popd

                  sudo docker stop ndt7 &>/dev/null
                  sudo docker rm ndt7 &>/dev/null

                  sudo docker run                                           \
                    --detach                                                \
                    --restart=always                                        \
                    --network=bridge                                        \
                    --publish 4444:4444                                     \
                    --publish 8888:8888                                     \
                    --volume /usr/local/lib/ndt-server/certs:/certs:ro      \
                    --volume /usr/local/lib/ndt-server/datadir:/datadir     \
                    --read-only                                             \
                    --user $(id -u):$(id -g)                                \
                    --cap-drop=all                                          \
                    --name ndt7                                             \
                    {args.image_repo}/ndt-server                            \
                    -cert /certs/cert.pem                                   \
                    -key /certs/key.pem                                     \
                    -datadir /datadir                                       \
                    -ndt7_addr :4444                                        \
                    -ndt5_addr :3001                                        \
                    -ndt5_wss_addr :3010                                    \
                    -ndt7_addr_cleartext :8888
                fi
            '''

            #
            # set up dashboard
            #
            rf'''
                if [ ! -e /var/lib/netrics-dashboard ]; then
                  sudo mkdir -p /var/lib/netrics-dashboard
                  sudo chown root:$(id -g) /var/lib/netrics-dashboard
                  sudo chmod g+w /var/lib/netrics-dashboard
                fi

                sudo mkdir -p /var/run/netrics-dashboard

                if [ ! -f /var/run/netrics-dashboard/version ]; then
                  sudo docker stop netrics-dashboard &>/dev/null
                  sudo docker rm netrics-dashboard &>/dev/null

                  sudo docker run                                             \
                    --detach                                                  \
                    --restart=always                                          \
                    --network=bridge                                          \
                    --publish 80:8080                                         \
                    --env-file /etc/nm-exp-active-netrics/.env                \
                    --volume /var/lib/netrics-dashboard:/var/lib/dashboard    \
                    --read-only                                               \
                    --user $(id -u):$(id -g)                                  \
                    --name netrics-dashboard                                  \
                    {args.image_repo}/netrics-dashboard

                  sudo docker inspect                                         \
                    --format="{{{{.Config.Labels.appversion}}}}"              \
                    netrics-dashboard                                         \
                    | sudo tee /var/run/netrics-dashboard/version             \
                    | xargs echo netrics-dashboard:
                fi
            '''
        ]

        #
        # success
        #
        # (Via echo rather than in-Python s.t. carries over to bin/)
        #
        yield self.local.FG, self.local['echo'][
            "Success! "
            f"Visit http://{NETRICS_HOST}/ to view your local dashboard."
        ]
