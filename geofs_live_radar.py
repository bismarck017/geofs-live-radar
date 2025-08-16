#!/usr/bin/env python3
"""
geofs_live_radar.py

Run:
    pip install flask requests
    python geofs_live_radar.py

Open http://127.0.0.1:5000
"""

from flask import Flask, Response, make_response
import requests
import os
import json
import threading
import time

# ---------------- Config ----------------
UPSTREAM_URL = "https://mps.geo-fs.com/map"
TIMEOUT = 3
PORT = int(os.environ.get("PORT", 5000))

AC_MAP_URL = None

SMALL_DEFAULT_AC_MAP = {
    "1": "Piper Cub",
    "2": "Cessna Citation",
    "4": "F-16",
    "5": "Cessna 172",
    "10": "Airbus A320",
    "13": "Airbus A380",
    "18": "Boeing 737",
    "24": "Boeing 747/777 (large)",
    "29": "B737 Classic",
    "1013": "Aero L-1011 (community?)",
}

SHOW_KEYWORDS = ["[U]","[UTP]","[P]","[PMC]","[RNLAF]","[RNZAF]","[USAF]","[RAAF]","[tuAF]","[TuAF]","[TUAF]","[TASC]","[TaSC]","[UAC]","[UAEAF]","[USSR]","[BAF]","[PAF]","[RAF]","(U)","(UTP)","(P)","(PMC)","(RNLAF)","(RNZAF)","(USAF)","(tuAF)","(TuAF)","(TASC)","(TaSC)","(TUAF)","(UAC)","(UAEAF)","(USSR)","(BAF)","(PAF)","(RAF)"]


AC_STATE = {}  # Tracks which airspaces each aircraft is currently in

# ---------------- Discord Config ----------------
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1406156183827382282/nRpVsLaN8uAV9189JmzwKthgv7vLTOMGMJwss-SYV8AzTyuYkJ0NjYSzrCPryFPxJ13D"
ROLE_ID = "1203013719752446042"  # optional, leave empty string "" if not tagging

def send_discord_message(msg):
    try:
        payload = {"content": f"{msg}"} if ROLE_ID else {"content": msg}
        r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        print("Discord response:", r.status_code, r.text)
        r.raise_for_status()
    except Exception as e:
        print("Discord message failed:", e)

# ---------------- Flask / proxy ----------------
app = Flask(__name__)
_ac_map = SMALL_DEFAULT_AC_MAP.copy()

def try_load_ac_map():
    global _ac_map
    if not AC_MAP_URL:
        return
    try:
        r = requests.get(AC_MAP_URL, timeout=8)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            _ac_map = {str(k): str(v) for k, v in data.items()}
            print(f"Loaded AC map from {AC_MAP_URL} ({len(_ac_map)} entries)")
    except Exception as e:
        print("Failed to load external AC map:", e)

@app.route("/api/map", methods=["GET"])
def proxy_map():
    try:
        r = requests.post(UPSTREAM_URL, data={}, timeout=TIMEOUT)
        r.raise_for_status()
        resp = make_response(r.content, 200)
        resp.headers["Content-Type"] = "application/json; charset=utf-8"
        return resp
    except Exception as e:
        return make_response(json.dumps({"error": str(e)}), 502, {"Content-Type": "application/json"})

@app.route("/api/acmap", methods=["GET"])
def api_acmap():
    return make_response(json.dumps(_ac_map), 200, {"Content-Type": "application/json"})

@app.route("/", methods=["GET"])
def index():
    return Response(HTML_PAGE, mimetype="text/html")

# ------------------ Airspace detection ------------------
def point_in_polygon(lat, lon, polygon):
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]['lat'], polygon[i]['lon']
        xj, yj = polygon[j]['lat'], polygon[j]['lon']
        if ((yi > lon) != (yj > lon)) and (lat < (xj - xi) * (lon - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def airspace_monitor_loop():
    AIRSPACES = [
        {
            "name": "Mainland",
            "coords": [
                {"lat": 25, "lon": 61.5}, {"lat": 27.5, "lon": 62.8}, {"lat": 29.7, "lon": 60.8},
                {"lat": 32.66, "lon": 68.86}, {"lat": 36.88, "lon": 72.22}, {"lat": 35.5, "lon": 80},
                {"lat": 31.8, "lon": 79}, {"lat": 30.33, "lon": 80.97}, {"lat": 28.95, "lon": 80},
                {"lat": 26.5, "lon": 88}, {"lat": 27.96, "lon": 88}, {"lat": 29.4, "lon": 97.5},
                {"lat": 20.86, "lon": 92.4}, {"lat": 21.7, "lon": 88.84}, {"lat": 7.5, "lon": 78.4},
                {"lat": 7.67, "lon": 76.2}, {"lat": 21, "lon": 68.5},
            ],
        },
        {
            "name": "Islands",
            "coords": [
                {"lat": 13.55, "lon": 92.83}, {"lat": 13.59, "lon": 93.13}, {"lat": 10.6, "lon": 92.6},
                {"lat": 6.84, "lon": 94}, {"lat": 6.73, "lon": 93.69}, {"lat": 10.65, "lon": 92.27},
            ],
        },
        {
            "name": "Africa",
            "coords": [
                {"lat": 10.57, "lon": 22.4}, {"lat": 10.51, "lon": 34.1}, {"lat": 14.7, "lon": 37.9},
                {"lat": 13.98, "lon": 40.86}, {"lat": 12.47, "lon": 42.35}, {"lat": 11, "lon": 41.75},
                {"lat": 7.8, "lon": 47.34}, {"lat": 5, "lon": 44.76}, {"lat": 3.84, "lon": 38},
                {"lat": 3, "lon": 16}, {"lat": 7.68, "lon": 15.5},
            ],
        },
    ]


    REFRESH_INTERVAL = 2  # seconds
    while True:
        try:
            r = requests.post(UPSTREAM_URL, data={}, timeout=3)
            r.raise_for_status()
            data = r.json()
            users = data.get("users", [])

            for u in users:
                if not u or 'co' not in u or len(u['co']) < 4:
                    continue
                lat, lon = u['co'][0], u['co'][1]
                callsign = u.get('cs', '').strip()
                if not callsign:
                    continue
                if callsign.lower() == 'randomassguy[u]':
                    continue
                if callsign == 'AOD-12[D99][P][Chief]':
                    continue
                show = any(k.upper() in callsign.upper() for k in SHOW_KEYWORDS)
                if not show:
                    continue

                user_id = str(u.get('id', u.get('acid', str(time.time()))))

                # Initialize state if not present
                if user_id not in AC_STATE:
                    AC_STATE[user_id] = {}

                for space in AIRSPACES:
                    inside = point_in_polygon(lat, lon, space['coords'])
                    was_inside = AC_STATE[user_id].get(space['name'], False)

                    if inside and not was_inside:
                        # Player just entered
                        print(f"{callsign} ENTERED {space['name']}")
                        send_discord_message(f"ALERT:        {callsign} has ENTERED our {space['name']}")
                        AC_STATE[user_id][space['name']] = True

                    elif not inside and was_inside:
                        # Player just left
                        print(f"{callsign} LEFT {space['name']}")
                        send_discord_message(f"{callsign} has LEFT {space['name']}")
                        AC_STATE[user_id][space['name']] = False

        except Exception as e:
            print("Airspace monitor error:", e)

        time.sleep(REFRESH_INTERVAL)

# ---------------- HTML/JS UI ----------------
HTML_PAGE = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>IAF Radar Alerts</title>
<meta name="viewport" content="width=device-width,initial-scale=1" />
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin=""/>
<style>
  html,body,#map { height:100%; margin:0; }
  .hud { position:absolute; left:8px; top:8px; z-index:9999; background:rgba(0,0,0,0.65); color:#fff; padding:8px 10px; border-radius:8px; font-family: system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial; font-size:13px; }
  .label { background: rgba(255,255,255,0.95); padding:3px 7px; border-radius:4px; font-weight:700; font-size:12px; color:#000; border:1px solid rgba(0,0,0,0.12); white-space:nowrap; pointer-events:none; }
</style>
</head>
<body>
<div id="map"></div>
<div class="hud">
  <div style="font-weight:700">IAF Radar Alerts</div>
  <br>
  <div style="font-size:10px;">&copy; developed by MASSIV4515[IAF]</div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
<script>
(async function(){
    const map = L.map('map', { preferCanvas:true }).setView([20,0], 2);

    const AIRSPACES = [
        {
            name: "Mainland",
            coords: [
                { lat: 25, lon: 61.5 }, { lat: 27.5, lon: 62.8 }, { lat: 29.7, lon: 60.8 },
                { lat: 32.66, lon: 68.86 }, { lat: 36.88, lon: 72.22 }, { lat: 35.5, lon: 80 },
                { lat: 31.8, lon: 79 }, { lat: 30.33, lon: 80.97 }, { lat: 28.95, lon: 80 },
                { lat: 26.5, lon: 88 }, { lat: 27.96, lon: 88 }, { lat: 29.4, lon: 97.5 },
                { lat: 20.86, lon: 92.4 }, { lat: 21.7, lon: 88.84 }, { lat: 7.5, lon: 78.4 },
                { lat: 7.67, lon: 76.2 }, { lat: 21, lon: 68.5 }
            ]
        },
        {
            name: "Islands",
            coords: [
                { lat: 13.55, lon: 92.83 }, { lat: 13.59, lon: 93.13 }, { lat: 10.6, lon: 92.6 },
                { lat: 6.84, lon: 94 }, { lat: 6.73, lon: 93.69 }, { lat: 10.65, lon: 92.27 }
            ]
        },
        {
            name: "Africa",
            coords: [
                { lat: 10.57, lon: 22.4 }, { lat: 10.51, lon: 34.1 }, { lat: 14.7, lon: 37.9 },
                { lat: 13.98, lon: 40.86 }, { lat: 12.47, lon: 42.35 }, { lat: 11, lon: 41.75 },
                { lat: 7.8, lon: 47.34 }, { lat: 5, lon: 44.76 }, { lat: 3.84, lon: 38 },
                { lat: 3, lon: 16 }, { lat: 7.68, lon: 15.5 }
            ]
        }
    ];

    // Draw airspace polygons
    AIRSPACES.forEach(space => {
        L.polygon(space.coords.map(p => [p.lat, p.lon]), {
            color: 'orange',
            weight: 0.25,
            fillOpacity: 0.05
        }).addTo(map);
    });

    // Add tile layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap & Carto',
        maxZoom: 19
    }).addTo(map);
})();
</script>

</body>
</html>
"""

# ------------------ Main ------------------
if __name__ == "__main__":
    if AC_MAP_URL:
        try:
            try_load_ac_map()
        except Exception as e:
            print("Error loading AC map:", e)
    else:
        print(f"Using default AC map with {len(_ac_map)} entries. Set AC_MAP_URL to load more.")

    # Start background thread for 24/7 monitoring
    threading.Thread(target=airspace_monitor_loop, daemon=True).start()

    print(f"GeoFS Live Radar running on http://0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
