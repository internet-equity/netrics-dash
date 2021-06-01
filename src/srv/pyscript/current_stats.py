import json

from influxdb import InfluxDBClient
from decouple import AutoConfig


config = AutoConfig('/etc/nm-exp-active-netrics/')


query_speed = """\
SELECT
  time,
  speedtest_ookla_download,
  speedtest_ookla_upload
FROM networks
WHERE
  install = $install_id AND
  time > now() - 2d
ORDER BY time DESC
LIMIT 1;
"""

query_speed_sd = """\
SELECT
  time,
  STDDEV(speedtest_ookla_download) AS ookla_dl_stdev
FROM networks
WHERE
  install = $install_id AND
  time > now() - 1w
ORDER BY time DESC
"""


query_latency = """\
SELECT time, google_rtt_avg_ms
FROM   networks
WHERE  install = $install_id AND time > now() - 2d
ORDER BY time DESC
LIMIT 1;
"""

query_consumption = """\
SELECT time, MAX(consumption_download) AS max_consumption_dl
FROM   networks
WHERE  install = $install_id AND time > now() - 1d
"""

query_ndev = """\
SELECT time, devices_1week
FROM   networks
WHERE  install = $install_id AND time > now() - 2d
ORDER BY time DESC
LIMIT 1;
"""


def get_point(response, *args):
    if not args:
        raise TypeError('at least one value name required')
    elif isinstance(args[-1], str):
        (names, round_to) = (args, None)
    else:
        (*names, round_to) = args

    try:
        all_values = next(response.get_points())
    except StopIteration:
        return (None,) * len(names)

    values = (all_values[name] for name in names)

    if round_to is None:
        return list(values)

    return [round(value, round_to) for value in values]


def get_recent_results():
    client = InfluxDBClient(
        host=config('INFLUXDB_SERVER'),
        port=config('INFLUXDB_PORT'),
        username=config('INFLUXDB_USERNAME'),
        password=config('INFLUXDB_PASSWORD'),
        database=config('INFLUXDB_DATABASE'),
        ssl=True,
        verify_ssl=True,
    )

    bind_params = {'install_id': config('INSTALL_ID')}

    res = client.query(query_speed, bind_params=bind_params)
    (dl, ul) = get_point(res, 'speedtest_ookla_download', 'speedtest_ookla_upload', 1)

    res = client.query(query_speed_sd, bind_params=bind_params)
    (dl_sd,) = get_point(res, 'ookla_dl_stdev', 1)

    res = client.query(query_latency, bind_params=bind_params)
    (latency,) = get_point(res, 'google_rtt_avg_ms', 1)

    res = client.query(query_consumption, bind_params=bind_params)
    (consumption,) = get_point(res, 'max_consumption_dl', 1)

    res = client.query(query_ndev, bind_params=bind_params)
    (devices,) = get_point(res, 'devices_1week', 1)

    return {
        "ookla_dl" : dl,
        "ookla_dl_sd" : dl_sd,
        "ookla_ul" : ul,
        "latency"  : latency,
        "consumption" : consumption,
        "ndev_week"   : devices,
    }


def application(environ, start_response):
    # data = get_and_save_post_data(environ)
    # value = data.get("perf", 50)

    stats = get_recent_results()

    start_response('200 OK', [('Content-type','text/json')])

    return [json.dumps(stats).encode('UTF-8')]
