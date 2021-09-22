import os
import pathlib

import plumbum
from argcmdr import local

from manage import config
from manage.main import Management


@Management.register
@local('path', nargs='?',
       default=f'{os.path.curdir}{os.path.sep}ext.zip',
       type=lambda path: pathlib.Path(path).absolute(),
       help="path to which to write file (default: %(default)s)")
def zip(context, args):
    """build a zip file of the extension source tree suitable for publishing"""
    with plumbum.local.cwd(config.EXTENSION_PATH):
        # can't just pass * without shell
        # ensure relative paths for zip member names
        extension_sources = tuple(pathlib.Path(os.path.curdir).glob('*'))

        # yield (not return) s.t. still in cwd when executed
        yield context.local['zip'][
            '-r',
            args.path,
            extension_sources,
        ]
