import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ORT_1 = "Oberallgäu (DE)"
LAT_1, LON_1 = 47.5743, 10.2917
ORT_2 = "Maspalomas (Gran Canaria)"
LAT_2, LON_2 = 27.762679, -15.590605
RUECKBLICK_TAGE = 14
VORHERSAGE_TAGE = 7

def hole_json(url, params):
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full_url, headers={"User-Agent": "SonnenVergleich-Web/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

heute = datetime.now(ZoneInfo("Europe/Berlin")).date()
gestern = heute - timedelta(days=1)
start_archiv = heute - timedelta(days=RUECKBLICK_TAGE)

# 1. Oberallgäu (DWD Bright Sky + ICON Forecast)
res_bs = hole_json("https://" + "api.brightsky.dev" + "/weather", {
    "lat": LAT_1, "lon": LON_1,
    "date": start_archiv.strftime("%Y-%m-%d"),
    "last_date": heute.strftime("%Y-%m-%d"), "max_dist": 60000
})
berlin_tz = ZoneInfo("Europe/Berlin")
dwd_tage = {}
for e in res_bs.get("weather", []):
    if e.get("sunshine") is not None:
        dt = datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")).astimezone(berlin_tz)
        if start_archiv <= dt.date() <= gestern:
            k = dt.date().strftime("%Y-%m-%d")
            dwd_tage[k] = dwd_tage.get(k, 0.0) + float(e["sunshine"])

d1 = {k: (round(dwd_tage[k] / 60.0, 2), "past") for k in sorted(dwd_tage)}
res_fc1 = hole_json("https://" + "api.open-meteo.com" + "/v1/forecast", {
    "latitude": LAT_1, "longitude": LON_1, "daily": "sunshine_duration",
    "timezone": "auto", "forecast_days": VORHERSAGE_TAGE, "models": "icon_seamless"
})
for t, s in zip(res_fc1["daily"]["time"], res_fc1["daily"]["sunshine_duration"]):
    if t not in d1 and s is not None:
        d1[t] = (round(s / 3600.0, 2), "fc")

# 2. Maspalomas (Satellit + Forecast)
d2 = {}
res_sat2 = hole_json("https://" + "satellite-api.open-meteo.com" + "/v1/archive", {
    "latitude": LAT_2, "longitude": LON_2,
    "start_date": start_archiv.strftime("%Y-%m-%d"),
    "end_date": gestern.strftime("%Y-%m-%d"),
    "daily": "sunshine_duration", "timezone": "auto"
})
for t, s in zip(res_sat2["daily"]["time"], res_sat2["daily"]["sunshine_duration"]):
    if s is not None:
        d2[t] = (round(s / 3600.0, 2), "past")

res_fc1 = hole_json("https://" + "api.open-meteo.com" + "/v1/forecast", {
    "latitude": LAT_2, "longitude": LON_2, "daily": "sunshine_duration",
    "timezone": "auto", "forecast_days": VORHERSAGE_TAGE
})
for t, s in zip(res_fc2["daily"]["time"], res_fc2["daily"]["sunshine_duration"]):
    if t not in d2 and s is not None:
        d2[t] = (round(s / 3600.0, 2), "fc")

def prep(d):
    ks = sorted(d.keys())
    lbls = [datetime.strptime(k, "%Y-%m-%d").strftime("%d.%m.") for k in ks]
    vals = [d[k] for k in ks]
    cols = ["#1f77b4" if d[k] == "past" else "#ff7f0e" for k in ks]
    sp = sum(d[k] for k in ks if d[k] == "past")
    sf = sum(d[k] for k in ks if d[k] == "fc")
    return lbls, vals, cols, round(sp, 1), round(sf, 1)

l1, v1, c1, sp1, sf1 = prep(d1)
l2, v2, c2, sp2, sf2 = prep(d2)
stand = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%d.%m.%Y %H:%M Uhr")

cdn_chart = "https://" + "cdn.jsdelivr.net" + "/npm/chart.js"
cdn_labels = "https://" + "cdn.jsdelivr.net" + "/npm/chartjs-plugin-datalabels@2"

html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="SonnenVergleich">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<title>SonnenVergleich</title>
<script src="{cdn_chart}"></script>
<script src="{cdn_labels}"></script>
<style>
  body {{ margin:0; padding:12px; background:#1a1c23; color:#fff; font-family:-apple-system,BlinkMacSystemFont,sans-serif; }}
  .head {{ display:flex; justify-content:space-between; align-items:center; font-size:13px; color:#aaa; margin-bottom:10px; }}
  .card {{ background:#242731; border-radius:14px; padding:12px; margin-bottom:14px; }}
  h2 {{ font-size:15px; margin:0 0 4px 0; }}
  .sub {{ font-size:12px; color:#ccc; margin-bottom:8px; }}
  .dot-b {{ color:#1f77b4; }} .dot-o {{ color:#ff7f0e; }}
  .chart-wrap {{ position:relative; height:235px; width:100%; }}
</style>
</head>
<body>
<div class="head"><span>Sonnenstunden-Vergleich</span><span>Stand: {stand}</span></div>
<div class="card">
  <h2>{ORT_1}</h2>
  <div class="sub"><span class="dot-b">■</span> Messung (14d): <b>{sp1} h</b> &nbsp;|&nbsp; <span class="dot-o">■</span> Vorhersage (7d): <b>{sf1} h</b></div>
  <div class="chart-wrap"><canvas id="c1"></canvas></div>
</div>
<div class="card">
  <h2>{ORT_2}</h2>
  <div class="sub"><span class="dot-b">■</span> Satellit (14d): <b>{sp2} h</b> &nbsp;|&nbsp; <span class="dot-o">■</span> Vorhersage (7d): <b>{sf2} h</b></div>
  <div class="chart-wrap"><canvas id="c2"></canvas></div>
</div>
<script>
Chart.register(ChartDataLabels);
function mk(id, labels, data, colors) {{
  new Chart(document.getElementById(id), {{
    type: 'bar',
    data: {{ labels: labels, datasets: [{{ data: data, backgroundColor: colors, borderRadius: 4 }}] }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      layout: {{ padding: {{ top: 18 }} }},
      plugins: {{
        legend: {{ display: false }},
        datalabels: {{
          color: '#eee',
          anchor: 'end',
          align: 'end',
          offset: -2,
          font: {{ size: 9, weight: 'bold' }},
          formatter: v => v > 0 ? v.toFixed(1) : ''
        }},
        tooltip: {{ callbacks: {{ label: ctx => ctx.parsed.y + ' Std.' }} }}
      }},
      scales: {{
        x: {{ ticks: {{ color: '#bbb', font: {{ size: 10 }} }}, grid: {{ display: false }} }},
        y: {{ beginAtZero: true, max: 14.5, ticks: {{ color: '#bbb', callback: v => v + 'h' }}, grid: {{ color: '#333' }} }}
      }}
    }}
  }});
}}
mk('c1', {json.dumps(l1)}, {json.dumps(v1)}, {json.dumps(c1)});
mk('c2', {json.dumps(l2)}, {json.dumps(v2)}, {json.dumps(c2)});
</script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
