from bottle import abort, request, route

from app.db import sqlite as db


PERF_LABELS = ('good', 'slow', 'unusable')

TABLE_STMT = """\
create table if not exists survey (
    ts integer primary key default (strftime('%s', 'now')),
    subj integer
);
"""


@route('/dashboard/survey/', method='POST')
def handle_survey():
    subj_label = request.forms.get('subjective')

    try:
        subj_code = PERF_LABELS.index(subj_label)
    except ValueError:
        abort(400, 'Bad request')

    with db.connection as conn:
        conn.execute(TABLE_STMT)
        conn.execute("insert into survey (subj) values (?)", (subj_code,))

    return {
        'inserted': {
            'value': subj_label,
            'code': subj_code,
        }
    }
