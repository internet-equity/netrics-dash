from bottle import route

from app.data.db import influx as db


@route('/dashboard/stats', method='GET')
def get_recent_results():
    with db.Client() as client:
        res = client.query(QUERY_SPEED)
        (dl, ul) = db.get_point(res, 'speedtest_ookla_download', 'speedtest_ookla_upload', 1)

        res = client.query(QUERY_SPEED_SD)
        (dl_sd,) = db.get_point(res, 'ookla_dl_stdev', 1)

        res = client.query(QUERY_LATENCY)
        (latency,) = db.get_point(res, 'google_rtt_avg_ms', 1)

        res = client.query(QUERY_CONSUMPTION)
        (consumption,) = db.get_point(res, 'max_consumption_dl', 1)

        res = client.query(QUERY_NDEV)
        (devices,) = db.get_point(res, 'devices_1week', 1)

    return {
        "ookla_dl" : dl,
        "ookla_dl_sd" : dl_sd,
        "ookla_ul" : ul,
        "latency"  : latency,
        "consumption" : consumption,
        "ndev_week"   : devices,
    }


QUERY_SPEED = """\
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

QUERY_SPEED_SD = """\
SELECT
  time,
  STDDEV(speedtest_ookla_download) AS ookla_dl_stdev
FROM networks
WHERE
  install = $install_id AND
  time > now() - 1w
ORDER BY time DESC
"""

QUERY_LATENCY = """\
SELECT time, google_rtt_avg_ms
FROM   networks
WHERE  install = $install_id AND time > now() - 2d
ORDER BY time DESC
LIMIT 1;
"""

QUERY_CONSUMPTION = """\
SELECT time, MAX(consumption_download) AS max_consumption_dl
FROM   networks
WHERE  install = $install_id AND time > now() - 1d
"""

QUERY_NDEV = """\
SELECT time, devices_1week
FROM   networks
WHERE  install = $install_id AND time > now() - 2d
ORDER BY time DESC
LIMIT 1;
"""
