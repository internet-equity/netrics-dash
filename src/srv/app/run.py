import importlib
import pathlib
import pkgutil

import bottle
import whitenoise
from decouple import config

from app import handler


APP_PATH = pathlib.Path(__file__).absolute().parent

STATIC_PATH = APP_PATH / 'static'


def init_submodules(pkg):
    for module_info in pkgutil.walk_packages(pkg.__path__, f'{pkg.__name__}.'):
        if not module_info.ispkg:
            importlib.import_module(module_info.name)


def main():
    init_submodules(handler)

    app_should_reload = config('APP_RELOAD', default=False, cast=bool)

    # WhiteNoise not strictly required --
    # Bottle does support static assets --
    # (but, WhiteNoise is more robust, etc.)
    app = whitenoise.WhiteNoise(
        bottle.app(),
        autorefresh=app_should_reload,
        index_file=True,
        prefix='/dashboard/',
        root=STATIC_PATH,
    )

    bottle.run(
        app,
        server='waitress',
        host=config('APP_HOST', default='127.0.0.1'),
        port=config('APP_PORT', default=8080, cast=int),
        quiet=config('APP_QUIET', default=False, cast=bool),
        reloader=app_should_reload,
    )
