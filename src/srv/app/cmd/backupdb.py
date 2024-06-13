import contextlib
import csv
import gzip
import pathlib
import re
import sys
from typing import Optional
from datetime import datetime

from argcmdr import Command

from app.data.db import sqlite as db
from app.lib.iteration import prime_iterator, storeresults
from app.lib.path import PathLock

from .run import Main


@Main.register
class BackupDB(Command):
    """write incremental backups of database tables"""

    file_name_format = 'dashboard_data_{date_time}_{timestamp}_{table_name}_{columns}.chunk.csv'

    file_name_pattern = re.compile(r'^dashboard_data_\d{8}_\d{6}'
                                   r'_(?P<timestamp>\d+)'
                                   r'_(?P<table_name>[a-z]+)'
                                   r'_[-a-z]+\.chunk\.csv(?:\.gz)?$')

    Nil = object()

    @classmethod
    def find_last_written(cls, *directories: pathlib.Path, table_name: Optional[str] = None) -> int:
        """Determine from target `directories` when a backup was last run.

        Directories' contents are listed, in order, to inspect their
        contained files.

        Upon discovery of file names which reflect generation by this
        command, timestamps are extracted from these names, and the most
        recent timestamp is returned.

        Backups under consideration may be filtered to a specific
        `table_name`.

        If no appropriately-named files are found, the epoch timestamp
        `0` is returned.

        """
        for target in directories:
            matches = (cls.file_name_pattern.search(path.name) for path in target.iterdir())

            timestamps = (
                int(match.group('timestamp'))
                for match in matches
                if match and (
                    table_name is None or
                    match.group('table_name') == table_name
                )
            )

            try:
                return max(timestamps)
            except ValueError:
                pass

        return 0

    @storeresults
    def execute_statements(self, statements):
        result = thrown = self.Nil

        with db.client.connect() as conn:
            while True:
                try:
                    if result is not self.Nil:
                        statement = statements.send(result)
                    elif thrown is not self.Nil:
                        statement = statements.throw(thrown)
                    else:
                        statement = next(statements)
                except StopIteration as finale:
                    return finale.value

                if isinstance(statement, str):
                    args = ()
                else:
                    try:
                        (statement, args) = statement
                    except ValueError:
                        try:
                            (statement,) = statement
                        except ValueError:
                            raise TypeError("unexpected statement structure", statement)
                        else:
                            args = ()

                try:
                    result = conn.execute(statement, args)
                except Exception as exc:
                    result = self.Nil
                    thrown = exc
                else:
                    thrown = self.Nil
                    yield result

    def backup_table_statements(self, table_name, since=0):
        ((now,),) = yield """\
            SELECT strftime('%s', 'now')
        """

        yield f"""\
            SELECT * FROM {table_name} WHERE ts > ? AND ts <= ?
        """, (since, now)

        return now

    def __init__(self, parser):
        parser.add_argument(
            'target',
            metavar='path',
            nargs='?',
            type=pathlib.Path,
            help="directory to which backup files are written (default: stdout)",
        )
        parser.add_argument(
            '--table',
            action='append',
            dest='tables',
            metavar='name',
            help="table(s) to back up (default: all)",
        )
        parser.add_argument(
            '--flat',
            action='store_true',
            help='write backup files to target directory without intermediary directories',
        )
        parser.add_argument(
            '--compress',
            action='store_true',
            help='gzip backup files',
        )

    def __call__(self, args):
        if args.compress and not args.target:
            sys.stderr.write('[FATAL] will not write compressed output to stdout')
            raise SystemExit(1)

        if args.target:
            # fail fast on directory permissions
            args.target.mkdir(parents=True, exist_ok=True)

            # attempt to prevent overlapping/conflicting backups
            lock = PathLock(args.target)
        else:
            lock = contextlib.nullcontext()

        for (table_name, columns) in db.TABLE_SCHEMA:
            if args.tables and table_name not in args.tables:
                continue

            with lock:
                self.backup_table(table_name, columns, args.target, args.flat, args.compress)

    def backup_table(self, table_name, columns, target, flat, compress):
        if target:
            if flat:
                table_target = target
                table_archive = target.parent.joinpath('archive')
            else:
                table_target = target / 'pending' / table_name / 'csv'
                table_archive = target / 'archive' / table_name / 'csv'

            table_target.mkdir(parents=True, exist_ok=True)
            table_archive.mkdir(parents=True, exist_ok=True)

            # fall back to archive directory in case pending recently emptied
            since = self.find_last_written(table_target, table_archive, table_name=table_name)
        else:
            since = 0
            table_target = None

        statements = self.backup_table_statements(table_name, since)

        results = self.execute_statements(statements)

        # first result is consumed internally and preserved by .result;
        # we only need the second one
        (_now_result, data_result) = results

        # don't bother if there are no novel results to write
        try:
            data_result = prime_iterator(data_result)
        except StopIteration:
            sys.stderr.write(f"[INFO] {table_name}: since {since}: no rows to back up")
            return

        if table_target:
            now = int(results.result)
            dt = datetime.fromtimestamp(now)
            file_name = self.file_name_format.format(
                date_time=dt.strftime('%Y%m%d_%H%M%S'),
                timestamp=now,
                table_name=table_name,
                columns='-'.join(columns),
            )

            if compress:
                file_name += '.gz'
                opener = lambda: gzip.open(table_target / file_name, 'wt')  # noqa: E731
            else:
                opener = lambda: open(table_target / file_name, 'w')  # noqa: E731
        else:
            opener = lambda: contextlib.nullcontext(sys.stdout)  # noqa: E731

        with opener() as file_descriptor:
            writer = csv.writer(file_descriptor)
            writer.writerows(data_result)
