#!/usr/bin/env python3
"""
geofs_live_radar.py

Run:
    pip install flask requests
    python geofs_live_radar.py

Open http://127.0.0.1:5000

Notes:
- The server proxies the public endpoint https://mps.geo-fs.com/map as /api/map
- The UI fetches /api/map every REFRESH_MS and updates markers smoothly
- To add a richer aircraft id->name mapping (including community models), set AC_MAP_URL
  to a raw JSON file mapping IDs to names (e.g. {"10":"Airbus A320", "24":"B737"}).
- Added feature: show only aircraft whose callsign contains at least one keyword in SHOW_KEYWORDS
"""
from flask import Flask, Response, make_response
import requests
import os
import json

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

# ---------------- HTML/JS UI ----------------
HTML_PAGE = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>IAF Radar </title>
<meta name="viewport" content="width=device-width,initial-scale=1" />
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin=""/>
<style>
  html,body,#map { height:100%; margin:0; }
  .hud {
    position:absolute; left:8px; top:8px; z-index:9999;
    background:rgba(0,0,0,0.65); color:#fff; padding:8px 10px; border-radius:8px;
    font-family: system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial; font-size:13px;
  }
  .label {
    background: rgba(255,255,255,0.95);
    padding:3px 7px;
    border-radius:4px;
    font-weight:700;
    font-size:12px;
    color:#000;
    border:1px solid rgba(0,0,0,0.12);
    white-space:nowrap;
    pointer-events:none;
  }
</style>
</head>
<body>
<div id="map"></div>
<div class="hud">
  <div style="font-weight:700">IAF Radar</div>
  <div id="stats">Loading…</div>
  <div id="last">—</div>
  <br>
  <div style="font-size:10px;">&copy; developed by MASSIV4515[IAF]</div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
<script>
(async function(){
  const REFRESH_MS = 2000;
  const ANIMATE_MS = REFRESH_MS;
  const STALE_MS = 15000;
  const LABEL_ZOOM_MIN = 0;
  const roleId = "1203013719752446042";
  const DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1406218574845972501/U01k2UlXJJl7X51qVyajddgh-rFAqOPn4Wg9tMkOw88TPQ_ZlynOl8swbg9xmJooD7PU";


  // Define airspaces polygons
  const AIRSPACES = [
    {
        name: "Mainland",
        coords: [
            { lat: 25, lon: 61.5 },
            { lat: 27.5, lon: 62.8 },
            { lat: 29.7, lon: 60.8 },
            { lat: 32.66, lon: 68.86 },
            { lat: 36.88, lon: 72.22 },
            { lat: 35.5, lon: 80 },
            {lat: 31.8, lon: 79 },
            { lat: 30.33, lon: 80.97 },
            { lat: 28.95, lon: 80 },
            { lat: 26.5, lon: 88 },
            {lat: 27.96, lon: 88 },
            { lat: 29.4, lon: 97.5 },
            { lat: 20.86, lon: 92.4 },
            { lat: 21.7, lon: 88.84 },
            {lat: 7.5, lon: 78.4 },
            {lat: 7.67, lon: 76.2 },
            {lat: 21, lon: 68.5 },
        ]
    },
    {
        name: "Islands",
        coords: [
            { lat: 13.55, lon: 92.83 },
            { lat: 13.59, lon: 93.13 },
            { lat: 10.6, lon: 92.6 },
            { lat: 6.84, lon: 94 },
            { lat: 6.73, lon: 93.69 },
            { lat: 10.65, lon: 92.27 },
        ]
    },
    {
        name: "Africa",
        coords: [
            { lat: 10.57, lon: 22.4 },
            { lat: 10.51, lon: 34.1 },
            { lat: 14.7, lon: 37.9 },
            { lat: 13.98, lon: 40.86 },
            { lat: 12.47, lon: 42.35 },
            { lat: 11, lon: 41.75 },
            {lat: 7.8, lon: 47.34 },
            { lat: 5, lon: 44.76 },
            { lat: 3.84, lon: 38 },
            { lat: 3, lon: 16 },
            {lat: 7.68, lon: 15.5 },
        ]
    },
  ];



  // Define keywords to filter callsigns
  const SHOW_KEYWORDS = ["[U]","[UTP]","[P]","[PMC]","[SHL]","[NFS]","[RPAF]","[RNLAF]","[RNZAF]","[USAF]","[RAAF]","[tuAF]","[TuAF]","[TUAF]","[TASC]","[TaSC]","[UAC]","[UAEAF]","[USSR]","[BAF]","[PAF]","[RAF]","(U)","(UTP)","(P)","(PMC)","(RNLAF)","(RNZAF)","(SHL)","(NFS)","(RPAF)","(RAAF)","(USAF)","(tuAF)","(TuAF)","(TASC)","(TaSC)","(TUAF)","(UAC)","(UAEAF)","(USSR)","(BAF)","(PAF)","(RAF)"]; // add your keywords here // add your keywords here

  let AC_MAP = {};
  try {
    const r = await fetch('/api/acmap');
    AC_MAP = await r.json();
  } catch (e) { AC_MAP = {}; }

  const map = L.map('map', { preferCanvas:true }).setView([20,0], 2);

  AIRSPACES.forEach(space => {
    L.polygon(space.coords.map(p => [p.lat, p.lon]), {
        color: 'orange',
        weight: 0.25,
        fillOpacity: 0.05
    }).addTo(map);
  });



  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap & Carto',
    maxZoom: 19
  }).addTo(map);

  const AC = {};

  const AIRSPACE_STATUS = {};  // { aircraft_id: { "Mainland": true/false, ... } }// Track which aircraft are inside which airspace


  function nowMs(){ return Date.now(); }

  function svgArrow(deg){
    return `<div style="transform: rotate(${deg}deg); display:block;">
      <svg width="22" height="22" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" style="display:block;">
        <path d="M12 2 L16 14 L12 11 L8 14 Z" fill="#0a84ff" stroke="#003a6b" stroke-width="0.6"/>
        <rect x="11" y="11" width="2" height="8" fill="#0a84ff" stroke="#003a6b" stroke-width="0.4"/>
      </svg>
    </div>`;
  }

  function makeIcon(bearing){
    return L.divIcon({ className:'', html: svgArrow(bearing), iconSize:[22,22], iconAnchor:[11,11] });
  }
  function makeLabel(text){
    return L.divIcon({ className:'', html:`<div class="label">${text}</div>`, iconSize:[10,10], iconAnchor:[0,-12] });
  }

  function bearingFromTo(lat1, lon1, lat2, lon2){
    const φ1 = lat1 * Math.PI/180, φ2 = lat2 * Math.PI/180;
    const Δλ = (lon2 - lon1) * Math.PI/180;
    const y = Math.sin(Δλ) * Math.cos(φ2);
    const x = Math.cos(φ1)*Math.sin(φ2) - Math.sin(φ1)*Math.cos(φ2)*Math.cos(Δλ);
    const θ = Math.atan2(y, x);
    return (θ * 180/Math.PI + 360) % 360;
  }

  let animating = false;
  function startAnimationLoop(){
    if (animating) return;
    animating = true;
    function frame(){
      const t = nowMs();
      for (const id in AC){
        const item = AC[id];
        if (t - item.lastSeen > STALE_MS){
          if (item.marker) map.removeLayer(item.marker);
          if (item.label) map.removeLayer(item.label);
          delete AC[id];
          continue;
        }
        if (item.prevPos && item.nextPos && item.t0 != null && item.t1 != null){
          const p = Math.min(1, Math.max(0, (t - item.t0) / (item.t1 - item.t0)));
          const lat = item.prevPos.lat + (item.nextPos.lat - item.prevPos.lat) * p;
          const lon = item.prevPos.lon + (item.nextPos.lon - item.prevPos.lon) * p;
          if (item.marker) item.marker.setLatLng([lat, lon]);
          if (item.label) item.label.setLatLng([lat, lon]);
        }
      }
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }


  function inPolygon(lat, lon, polygon) {
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const xi = polygon[i].lat, yi = polygon[i].lon;
        const xj = polygon[j].lat, yj = polygon[j].lon;
        const intersect = ((yi > lon) != (yj > lon)) && (lat < (xj - xi) * (lon - yi) / (yj - yi) + xi);
        if (intersect) inside = !inside;
    }
    return inside;
  }

  async function sendDiscordMessage(content){
    try {
        await fetch(DISCORD_WEBHOOK_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content })
        });
    } catch(e){
        console.error("Discord message failed:", e);
    }
  }


  async function refreshLoop(){
    try {
        const r = await fetch('/api/map', {cache:'no-store'});
        if (!r.ok) throw new Error('upstream status ' + r.status);
        const data = await r.json();
        const users = Array.isArray(data.users) ? data.users : [];
        const reported = (typeof data.userCount === 'number') ? data.userCount : users.length;
        const t_fetch = nowMs();

        for (const u of users){
            if (!u || !Array.isArray(u.co) || u.co.length < 4) continue;
            const lat = u.co[0], lon = u.co[1], alt = u.co[2], hdgServer = u.co[3];
            if (typeof lat !== 'number' || typeof lon !== 'number') continue;
            if (!isFinite(lat) || !isFinite(lon)) continue;
            if (Math.abs(lat) > 90 || Math.abs(lon) > 180) continue;

            const csRaw = (typeof u.cs === 'string') ? u.cs.trim() : '';
            if (!csRaw) continue;

            // --- Exclude specific bot ---
            if (csRaw.toLowerCase() === 'randomassguy[u]') continue;

            const callsign = csRaw;

            // --- Keyword filter ---
            const show = SHOW_KEYWORDS.length === 0 || SHOW_KEYWORDS.some(k => callsign.toUpperCase().includes(k.toUpperCase()));
            if (!show) continue;
            // --- End keyword filter ---

            const id = String(u.id || u.acid || Math.random());
            const prevItem = AC[id];

            // --- Airspace entry/exit detection ---
            const prevAirspaces = prevItem ? prevItem.airspaces || [] : [];
            const currentAirspaces = [];

            for (const airspace of AIRSPACES) {
                if (inPolygon(lat, lon, airspace.coords)) {
                    currentAirspaces.push(airspace.name);
                    if (!prevAirspaces.includes(airspace.name)) {
                        //console.log(`ALERT: ${callsign} has ENTERED our ${airspace.name}`);
                        sendDiscordMessage(`ALERT:          ${callsign} has ENTERED our ${airspace.name} <@&${roleId}> `);
                    }
                }
            }

            // detect exit
            if (prevItem && prevAirspaces.length > 0) {
                for (const exited of prevAirspaces) {
                    if (!currentAirspaces.includes(exited)) {
                        //console.log(`${callsign} has LEFT our ${exited}`);
                        sendDiscordMessage(`${callsign} LEFT our ${exited}`);
                    }
                }
            }

            // update aircraft's airspaces
            if (!prevItem) AC[id] = {};
            AC[id].airspaces = currentAirspaces;



            if (!prevItem){
                const m = L.marker([lat, lon], { icon: makeIcon(hdgServer || 0) }).addTo(map);
                const lab = L.marker([lat, lon], { icon: makeLabel(callsign), interactive:false });
                if (map.getZoom() >= LABEL_ZOOM_MIN) lab.addTo(map);
                AC[id] = {
                    marker: m,
                    label: lab,
                    prevPos: {lat, lon},
                    nextPos: {lat, lon},
                    t0: t_fetch,
                    t1: t_fetch + ANIMATE_MS,
                    lastSeen: t_fetch,
                    lastBearing: hdgServer || 0,
                    callsign,
                    airspaces: currentAirspaces
                };
            } else {
                prevItem.prevPos = prevItem.nextPos || { lat: prevItem.prevPos.lat, lon: prevItem.prevPos.lon };
                prevItem.nextPos = { lat, lon };
                prevItem.t0 = t_fetch; prevItem.t1 = t_fetch + ANIMATE_MS;
                
                // --- Correct heading ---
                let cog = hdgServer != null ? hdgServer : prevItem.lastBearing || 0;
                const moved = Math.abs(lat - prevItem.prevPos.lat) + Math.abs(lon - prevItem.prevPos.lon);
                if (moved > 1e-5 && hdgServer == null) {
                    cog = bearingFromTo(prevItem.prevPos.lat, prevItem.prevPos.lon, lat, lon);
                }
                prevItem.lastBearing = cog;
                if (prevItem.marker) prevItem.marker.setIcon(makeIcon(prevItem.lastBearing));
                if (prevItem.label) prevItem.label.setIcon(makeLabel(callsign));

                prevItem.lastSeen = t_fetch;
                prevItem.callsign = callsign;
                prevItem.airspaces = currentAirspaces;
            }
        }

        document.getElementById('stats').textContent = `Showing ${Object.keys(AC).length} markers • Reported total: ${reported}`;
        document.getElementById('last').textContent = `Last fetch: ${new Date().toLocaleTimeString()}`;

    } catch(err){
        console.error("Fetch error:", err);
        document.getElementById('stats').textContent = 'Fetch error';
    } finally {
        setTimeout(refreshLoop, REFRESH_MS);
    }
  }


  startAnimationLoop();
  refreshLoop();

  map.on('zoomend', ()=>{
    const z = map.getZoom();
    for (const id in AC){
      const it = AC[id];
      if (!it.label) continue;
      if (z >= LABEL_ZOOM_MIN){
        if (!map.hasLayer(it.label)) map.addLayer(it.label);
      } else {
        if (map.hasLayer(it.label)) map.removeLayer(it.label);
      }
    }
  });

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

    print(f"GeoFS Live Radar running on http://0.0.0.1:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)

