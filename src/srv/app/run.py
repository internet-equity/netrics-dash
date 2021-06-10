import importlib
import pkgutil

import bottle
from decouple import config

from app import handler


def init_submodules(pkg):
    for module_info in pkgutil.walk_packages(pkg.__path__, f'{pkg.__name__}.'):
        if not module_info.ispkg:
            importlib.import_module(module_info.name)


def main():
    init_submodules(handler)
    bottle.run(
        host=config('APP_HOST', default='127.0.0.1'),
        port=config('APP_PORT', default=8080, cast=int),
        reloader=config('APP_RELOAD', default=False, cast=bool),
        quiet=config('APP_QUIET', default=False, cast=bool),
        server='waitress',
    )
