import json

from influxdb import InfluxDBClient

query_speed = """
SELECT
  time,
  speedtest_ookla_download,
  speedtest_ookla_upload
FROM networks
WHERE
  install = 'saxon' AND 
  time > now() - 2d
ORDER BY time DESC
LIMIT 1;
"""

query_speed_sd = """
SELECT
  time,
  STDDEV(speedtest_ookla_download) AS ookla_dl_stdev
FROM networks
WHERE
  install = 'saxon' AND 
  time > now() - 1w
ORDER BY time DESC
"""


query_latency = """
SELECT time, google_rtt_avg_ms 
FROM   networks
WHERE  install = 'saxon' AND time > now() - 2d
ORDER BY time DESC
LIMIT 1;
"""

query_consumption = """
SELECT time, MAX(consumption_download) AS max_consumption_dl
FROM   networks
WHERE  install = 'saxon' AND time > now() - 1d
"""

query_ndev = """
SELECT time, devices_1week
FROM   networks
WHERE  install = 'saxon' AND time > now() - 2d
ORDER BY time DESC
LIMIT 1;
"""

def get_recent_results():

    client = InfluxDBClient(host = "", port = -9999, username = "", password = "", ssl = True, verify_ssl = True)

    res = client.query(query_speed, database = "netrics")
    dl = round(list(res.get_points())[0]["speedtest_ookla_download"], 1)
    ul = round(list(res.get_points())[0]["speedtest_ookla_upload"], 1)

    res = client.query(query_speed_sd, database = "netrics")
    dl_sd = round(list(res.get_points())[0]["ookla_dl_stdev"], 1)


    res = client.query(query_latency, database = "netrics")
    latency = round(list(res.get_points())[0]["google_rtt_avg_ms"], 1)

    res = client.query(query_consumption, database = "netrics")
    consumption = round(list(res.get_points())[0]["max_consumption_dl"], 1)

    res = client.query(query_ndev, database = "netrics")
    devices = round(list(res.get_points())[0]["devices_1week"], 1)


    stats = {"ookla_dl" : dl, 
             "ookla_dl_sd" : dl_sd,
             "ookla_ul" : ul,
             "latency"  : latency,
             "consumption" : consumption,
             "ndev_week"   : devices}


    return stats


def application(environ, start_response):

    # data = get_and_save_post_data(environ)
    # value = data.get("perf", 50)

    stats = get_recent_results()

    start_response('200 OK', [('Content-type','text/json')])

    return [json.dumps(stats).encode('UTF-8')]


