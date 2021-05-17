import json, time, sqlite3
from urllib.parse import parse_qs


def get_and_save_post_data(env, sqlite_fname = "/var/www/scripts/wsgi.sqlite"):

    con = sqlite3.connect(sqlite_fname)
    # con.execute("CREATE TABLE IF NOT EXISTS wsgi (ts INT, subj INT);")

    try:
        request_body_size = int(env.get('CONTENT_LENGTH', 0))
    except:
        return ""

    if not request_body_size: return {}

    request_body = env['wsgi.input'].read(request_body_size)
    parsed_data = parse_qs(request_body)
    data = {k.decode('utf-8') : v[0].decode('utf-8') for k, v in parsed_data.items()}

    now = int(time.time())

    perf_map = {"unusable" : 2, "slow" : 1, "good" : 0}

    value_str = data["subjective"]
    value_int = perf_map[value_str]

    con.execute(f"INSERT INTO wsgi VALUES ({now}, {value_int});")
    con.commit()
    con.close()

    return value_str



def application(environ, start_response):

    value = get_and_save_post_data(environ)

    if not value: 
        start_response("400 Bad Request", [('Content-type','text/html')])
        return ["Badly formed post request.".encode("utf-8")]

    start_response('200 OK', [('Content-type','text/json')])

    return [json.dumps({"inserted" : value}).encode('UTF-8')]


