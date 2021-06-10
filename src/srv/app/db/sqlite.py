import pathlib
import sqlite3

import app


APP_DIRECTORY = pathlib.Path(app.__path__).absolute().parent

SQLITE_DEFAULT = APP_DIRECTORY / 'data.sqlite'


connection = sqlite3.connect(
    app.config('APP_DATABASE', default=f'file:{SQLITE_DEFAULT}'),
    uri=True,
)
