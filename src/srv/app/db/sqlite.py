import sqlite3
import threading

import app


SQLITE_DEFAULT = app.APP_PATH / 'data.sqlite'

TABLE_STMT_SURVEY = """\
create table if not exists survey (
    ts integer primary key default (strftime('%s', 'now')),
    subj integer
) without rowid;
"""
# NOTE: rowid ommitted to prevent sqlite from substituting a sequential rowid
# NOTE: for the correct timestamp default;
# NOTE: (however, there might be better solutions).


class Client(threading.local):

    @staticmethod
    def make_connection():
        return sqlite3.connect(
            app.config('APP_DATABASE', default=f'file:{SQLITE_DEFAULT}'),
            uri=True,
        )

    def connect(self):
        try:
            conn = self.connection
        except AttributeError:
            conn = self.connection = self.make_connection()

        return conn

    def prepare_database(self):
        with self.connect() as conn:
            conn.execute(TABLE_STMT_SURVEY)


client = Client()

client.prepare_database()
