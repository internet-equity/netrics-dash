import re

from descriptors import cachedproperty

from manage import config, lib
from manage.main import Management


def version_type(value):
    if not re.match(r'v?\d+\.\d+\.\d+', value):
        raise ValueError('invalid version number')

    return value


@Management.register
class Build(lib.DockerCommand):
    """build dashboard images for amd64 & arm64"""

    def __init__(self, parser):
        parser.add_argument('target', choices=('dash', 'ndt'), help="build target")
        parser.add_argument('version', type=version_type,
                            help="version to apply to the local dashboard app or to "
                                 "the extended ndt server (e.g.: 1.0.1)")
        parser.add_argument('--builder', default='netrics-dashboard', metavar='NAME',
                            help="name to assign to builder (default: %(default)s)")
        parser.add_argument('--binfmt', default=config.BINFMT_TAG, metavar='TAG',
                            help="Docker image tag of binfmt (default: %(default)s)")
        parser.add_argument('--push', action='store_true',
                            help="push images to remote repository "
                                 "(rather than load images locally)")
        parser.add_argument('--no-latest', action='store_false', dest='tag_latest',
                            help="do NOT tag images as \"latest\"")

    @cachedproperty
    def action(self):
        return '--push' if self.args.push else '--load'

    @cachedproperty
    def platforms(self):
        return 'linux/amd64,linux/arm64' if self.args.push else 'linux/amd64'

    def tag_args(self, uri, version):
        args = ('-t', f'{uri}:{version}')

        return args + ('-t', f'{uri}:latest') if self.args.tag_latest else args

    def prepare_ndt(self):
        yield self.local.FG, self.docker[
            'buildx',
            'build',
            '--platform', self.platforms,
            '--build-arg', f'BASE_TAG={config.NDT_SERVER_TAG}',
            self.tag_args(f'{self.args.image_repo}/ndt-server-full', self.args.version),
            config.REPO_PATH / 'image' / 'ndt',
            self.action,
        ]

    def prepare_dash(self):
        yield self.local.FG, self.docker[
            'buildx',
            'build',
            '--platform', self.platforms,
            '--build-arg', f'APPVERSION={self.args.version}',
            self.tag_args(f'{self.args.image_repo}/netrics-dashboard', self.args.version),
            config.REPO_PATH,
            self.action,
        ]

    def prepare(self, args):
        if not config.BINFMT_TARGET.exists():
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

        if args.target == 'ndt':
            yield from self.prepare_ndt()

        elif args.target == 'dash':
            yield from self.prepare_dash()

        else:
            raise NotImplementedError(args.target)
