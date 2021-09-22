import re

from argcmdr import cmdmethod

from manage import config, lib
from manage.main import Management


def stream_requirements(file_path):
    for line in file_path.read_text().splitlines():
        spec = re.sub(r'#.*$', '', line).strip()
        if spec:
            yield spec


@Management.register
class Provision(lib.LocalPiCommand):
    """set up a (local) raspberry pi"""

    dependencies = ' '.join(stream_requirements(config.REPO_PATH / 'dependency' / 'main.txt'))

    def __init__(self, parser):
        super().__init__(parser)

        parser.add_argument(
            '--version',
            default='latest',
            help="version of dashboard image to provision (default: %(default)s)",
        )

    def render_script(self):
        return lib.Template.render(
            'provision.bash.tpl',
            dependencies=self.dependencies,
            image_repo=self.args.image_repo,
            version=self.args.version,
            ndt_server_origin=config.NDT_SERVER_ORIGIN,
            ndt_server_tag=config.NDT_SERVER_TAG,
        )

    def prepare(self, args):
        commands = self.render_script()

        yield self.local.FG, self.local['ssh'][f'{args.username}@{args.host}'][commands]

        if args.execute_commands:
            print("Success!", f"Visit http://{config.NETRICS_HOST}/ to view your local dashboard.")

    @cmdmethod
    def show(self, args, parser):
        """merely print remote actions (does NOT execute commands)"""
        if not args.execute_commands:
            parser.error('--dry-run does not make sense in this context')

        print(self.render_script())
