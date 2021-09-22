import pathlib
import re

from manage import config, lib
from manage.main import Management


def version_type(value):
    if not re.match(r'\d\.\d\.\d', value):
        raise ValueError('invalid version number')

    return value


@Management.register
class Build(lib.DockerCommand):
    """build dashboard images for amd64 & arm64"""

    def __init__(self, parser):
        parser.add_argument('target', choices=('dash', 'ndt'), nargs='?',
                            help="build target (default: all)")
        parser.add_argument('--version', type=version_type,
                            help="version to apply to the local dashboard app (e.g.: 1.0.1)")
        parser.add_argument('--ndt-cache', default=(config.REPO_PATH / '.ndt-server'),
                            metavar='PATH', type=pathlib.Path,
                            help="path at which to cache the ndt-server repository (default: %(default)s)")
        parser.add_argument('--builder', default='netrics-dashboard', metavar='NAME',
                            help="name to assign to builder (default: %(default)s)")
        parser.add_argument('--binfmt', default=config.BINFMT_TAG, metavar='TAG',
                            help="Docker image tag of binfmt (default: %(default)s)")
        parser.add_argument('--push', action='store_true',
                            help="push images to remote repository (rather than load images locally)")
        parser.add_argument('--no-latest', action='store_false', dest='tag_latest',
                            help="do NOT tag images as \"latest\"")

    def prepare(self, args, parser):
        targets = {'dash', 'ndt'} if not args.target else {args.target}

        if 'dash' in targets:
            if not args.version:
                parser.error('--version required to build dash')
        elif args.version:
            parser.error('--version only applies to dash build')

        platforms = 'linux/amd64,linux/arm64' if args.push else 'linux/amd64'

        action = '--push' if args.push else '--load'

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

        if 'ndt' in targets:
            if not args.ndt_cache.exists():
                yield self.local.FG, self.local['git'][
                    'clone',
                    '--branch', config.NDT_SERVER_TAG,
                    '--config', 'advice.detachedHead=false',
                    '--depth', '1',
                    f'https://github.com/{config.NDT_SERVER_ORIGIN}.git',
                    args.ndt_cache,
                ]

            (_retcode, stdout, _stderr) = yield lib.SHH, self.local['git'][
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
                config.REPO_PATH,
                action,
            ]
