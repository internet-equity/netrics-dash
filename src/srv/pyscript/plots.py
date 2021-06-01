import json

from influxdb import InfluxDBClient

query_speed = """
SELECT
  time,
  speedtest_ookla_download AS dl,
  speedtest_ookla_upload   AS ul
FROM networks
WHERE
  install = 'saxon' AND 
  time > now() - 1w
ORDER BY time ASC
"""

query_latency = """
SELECT
  time,
  google_rtt_avg_ms AS google,
  amazon_rtt_avg_ms AS amazon,
  wikipedia_rtt_avg_ms AS wikipedia
FROM 
  networks
WHERE
  install = 'saxon' AND 
  time > now() - 1w
ORDER BY time ASC
"""

query_consumption = """
SELECT time, consumption_download AS dl, consumption_upload AS ul
FROM   networks
WHERE  install = 'saxon' AND time > now() - 1w
ORDER BY time ASC
"""

query_ndev = """
SELECT
  time, devices_active, devices_1day, devices_1week, devices_total
FROM 
  networks
WHERE
  install = 'saxon' AND 
  time > now() - 1w
ORDER BY time ASC
"""

def ext_values(res, label):

    return [round(pt[label], 2) for pt in res.get_points()]


def get_measurements():

    client = InfluxDBClient(host = "", port = -9999, username = "", password = "", ssl = True, verify_ssl = True)

    res = client.query(query_speed, database = "netrics")
    bw_ts = [pt["time"] for pt in res.get_points()]
    bw_dl = ext_values(res, "dl")
    bw_ul = ext_values(res, "ul")

    res = client.query(query_latency, database = "netrics")
    rtt_ts = [pt["time"] for pt in res.get_points()]
    rtt_google = ext_values(res, "google")
    rtt_amazon = ext_values(res, "amazon")
    rtt_wikipedia = ext_values(res, "wikipedia")

    res = client.query(query_consumption, database = "netrics")
    con_ts = [pt["time"] for pt in res.get_points()]
    con_dl = ext_values(res, "dl")
    con_ul = ext_values(res, "ul")

    res = client.query(query_ndev, database = "netrics")
    dev_ts = [pt["time"] for pt in res.get_points()]
    dev_now = ext_values(res, "devices_active")
    dev_1d  = ext_values(res, "devices_1day")
    dev_1w  = ext_values(res, "devices_1week")
    dev_tot = ext_values(res, "devices_total")

    stats = {"bw" : {"ts" : bw_ts, "dl" : bw_dl, "ul" : bw_ul},
             "latency" : {"ts" : rtt_ts, "google" : rtt_google, "amazon" : rtt_amazon, "wikipedia" : rtt_wikipedia},
             "consumption" : {"ts" : con_ts, "dl" : con_dl, "ul" : con_ul}, 
             "devices" : {"ts" : dev_ts, "active" : dev_now, "1d" : dev_1d, "1w" : dev_1w, "tot" : dev_tot}
             }

    return stats


def application(environ, start_response):

    stats = get_measurements()

    start_response('200 OK', [('Content-type','text/json')])

    return [json.dumps(stats).encode('UTF-8')]


