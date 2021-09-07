from bottle import route

from app.data.db import influx as db


@route('/dashboard/plots', method='GET')
def get_measurements():
    with db.Client() as client:
        res = client.query(QUERY_SPEED)
        bw_ts = [pt['time'] for pt in res.get_points()]
        (bw_dl, bw_ul) = db.get_points(res, 'dl', 'ul', 2)

        res = client.query(QUERY_LATENCY)
        rtt_ts = [pt['time'] for pt in res.get_points()]
        (rtt_google, rtt_amazon, rtt_wikipedia) = db.get_points(
            res,
            'google',
            'amazon',
            'wikipedia',
            2,
        )

        res = client.query(QUERY_CONSUMPTION)
        con_ts = [pt['time'] for pt in res.get_points()]
        (con_dl, con_ul) = db.get_points(res, 'dl', 'ul', 2)

        res = client.query(QUERY_NDEV)
        dev_ts = [pt['time'] for pt in res.get_points()]
        (dev_now, dev_1d, dev_1w, dev_tot) = db.get_points(
            res,
            'devices_active',
            'devices_1day',
            'devices_1week',
            'devices_total',
            2,
        )

    return {
        'bw': {
            'ts': bw_ts,
            'dl': bw_dl,
            'ul': bw_ul,
        },
        'latency': {
            'ts': rtt_ts,
            'google': rtt_google,
            'amazon': rtt_amazon,
            'wikipedia': rtt_wikipedia,
        },
        'consumption': {
            'ts': con_ts,
            'dl': con_dl,
            'ul': con_ul,
        }, 
        'devices': {
            'ts': dev_ts,
            'active': dev_now,
            '1d': dev_1d,
            '1w': dev_1w,
            'tot': dev_tot,
        },
    }


QUERY_SPEED = """\
SELECT
  time,
  speedtest_ookla_download AS dl,
  speedtest_ookla_upload   AS ul
FROM networks
WHERE
  install = $install_id AND 
  time > now() - 1w
ORDER BY time ASC
"""

QUERY_LATENCY = """\
SELECT
  time,
  google_rtt_avg_ms AS google,
  amazon_rtt_avg_ms AS amazon,
  wikipedia_rtt_avg_ms AS wikipedia
FROM 
  networks
WHERE
  install = $install_id AND 
  time > now() - 1w
ORDER BY time ASC
"""

QUERY_CONSUMPTION = """\
SELECT time, consumption_download AS dl, consumption_upload AS ul
FROM   networks
WHERE  install = $install_id AND time > now() - 1w
ORDER BY time ASC
"""

QUERY_NDEV = """\
SELECT
  time, devices_active, devices_1day, devices_1week, devices_total
FROM 
  networks
WHERE
  install = $install_id AND 
  time > now() - 1w
ORDER BY time ASC
"""
