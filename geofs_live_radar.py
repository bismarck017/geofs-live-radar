#!/usr/bin/env python3
"""
geofs_live_radar.py

Run:
    pip install flask requests
    python geofs_live_radar.py

Then open http://127.0.0.1:5000

Features:
- Proxies GeoFS public endpoint as /api/map
- Shows all aircraft filtered by keywords
- Smooth marker updates with heading + callsign labels
"""

from flask import Flask, Response, make_response
import requests
import os
import json

# ---------------- Config ----------------
UPSTREAM_URL = "https://mps.geo-fs.com/map"
TIMEOUT = 3
PORT = int(os.environ.get("PORT", 5000))

# ---------------- Flask / proxy ----------------
app = Flask(__name__)

@app.route("/api/map", methods=["GET"])
def proxy_map():
    """Proxy GeoFS map API."""
    try:
        r = requests.post(UPSTREAM_URL, data={}, timeout=TIMEOUT)
        r.raise_for_status()
        resp = make_response(r.content, 200)
        resp.headers["Content-Type"] = "application/json; charset=utf-8"
        return resp
    except Exception as e:
        return make_response(json.dumps({"error": str(e)}), 502, {"Content-Type": "application/json"})

@app.route("/", methods=["GET"])
def index():
    return Response(HTML_PAGE, mimetype="text/html")

# ---------------- HTML/JS UI ----------------
HTML_PAGE = r"""<!doctype html>
<html>
<head>
<script defer data-domain="geofs-live-radar.onrender.com" src="https://plausible.io/js/script.js"></script>
<meta charset="utf-8" />
<title>GeoFS Radar</title>
<meta name="viewport" content="width=device-width,initial-scale=1" />
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin=""/>
<style>
  html,body,#map { height:100%; margin:0; }
  .hud {
    position:fixed; left:8px; top:8px; z-index:9999;
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
  
  body{
    background: linear-gradient(180deg, rgba(173,216,230,0.22), rgba(245,245,220,0.22));
  }
  
  #map { 
    height:90%;
    width:95%;  
    margin: 40px auto;
    border: 2px solid;
  }
  .contact-bar {
    background: rgba(0,0,0,0.8);
    color: white;
    text-align: center;
    padding: 8px;
    font-family: system-ui, sans-serif;
    font-size: 14px;
    margin-top: 15px;
    border-radius: 6px;
    width: 95%;
    margin-left: auto;
    margin-right: auto;
  }
  .contact-bar a {
    color: #0af;
    margin: 0 10px;
    text-decoration: none;
    font-weight: bold;
  }
  .contact-bar a:hover {
    text-decoration: underline;
  }
</style>
</head>
<body>
<div id="map"></div>
<div class="hud">
  <div style="font-weight:700">GeoFS Military Radar</div>
  <div id="stats">Loading…</div>
  <div id="last">—</div>
</div>

<div class="contact-bar">
  📧 Email: <a href="mailto:massiv4515@gmail.com">massiv4515@gmail.com</a> &nbsp;|&nbsp;
  💬 Discord: <a href="https://discord.com/users/1421366810200244246" target="_blank">massiv4515</a> &nbsp;|&nbsp;
  💻 GitHub: <a href="https://github.com/Massiv4515" target="_blank">Massiv4515</a> &nbsp;|&nbsp;
  🤝 Contributors: <a href="https://discord.com/users/702415876904976424" target="_blank">BigBoi69</a>
  <div style="font-size:10px;">&copy; developed by MASSIV4515</div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
<script>
(async function(){
  const REFRESH_MS = 2000;
  const ANIMATE_MS = REFRESH_MS;
  const STALE_MS = 15000;
  const LABEL_ZOOM_MIN = 0;

  // Show only callsigns with these tags
  const SHOW_KEYWORDS = [
    "[U]","[UTP]","[P]","[PMC]","[NKG-KG]","[SHL]","[NFS]","[AEF]", "lasallian", "butter", "ek-069", "tarun", "massiv4515", "walch", "ljf", "ek-1", "ek-01",
    "[RPAF]","[WANK]","[NIUF]","[RNLAF]","[RNZAF]","[USAF]","[RAAF]", "[TBD]", "[CAEAF]", "[Luftwaffe]", "[BPYR]", "[BYDAF]", "[Luftwafe]", "ek-69",
    "[TUAF]","[TASC]","[UAC]","[UAEAF]","[USSR]","[BAF]","[PAF]", "[JASDF]","[RAF]", "[RFAF]", "[EVKS]", "[VKS]", "[ACP]", "[PYR]", "[FFL]", "[IAF]", "[AAF]", "[CAF]", "[IOA]", "[PLAAF]", "[RIAF]", "AF]",
    "(U)","(UTP)","(P)","(NKG-KG)","(PMC)","(RNLAF)","(AEF)","(RNZAF)", "(RFAF)", "(EVKS)", "(VKS)", "(ACP)", "(PYR)", "(FFL)", "(IAF)", "(AAF)", "(CAF)", "(IOA)", "(PLAAF)", "AF)",
    "(SHL)","(NFS)","(RPAF)","(RAAF)","(USAF)", "(JASDF)", "(TUAF)","(TASC)","(UAC)", "(RIAF)", "(Luftwaffe)",
    "(UAEAF)","(USSR)","(BAF)","(WANK)","(NIUF)","(PAF)","(RAF)", "(TBD)", "(CAEAF)"
  ];


  const map = L.map('map', { 
    preferCanvas:true, 
    worldCopyJump: false,
    minZoom: 1,
    maxBounds: [[-300, -300], [300, 300]],
  }).setView([20,0], 2);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap & Carto',
    maxZoom: 19,
  }).addTo(map);

  const AC = {};

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

  // Smooth animation loop
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

            // Skip specific bots
            if (csRaw.toLowerCase() === 'randomassguy[u]') continue;
            if (csRaw === 'EventHorizon[USAF]') continue;

            const callsign = csRaw;

            // Keyword filter
            const show = SHOW_KEYWORDS.length === 0 || SHOW_KEYWORDS.some(k => callsign.toUpperCase().includes(k.toUpperCase()));
            if (!show) continue;

            const id = String(u.id || u.acid || Math.random());
            const prevItem = AC[id];

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
                };
            } else {
                prevItem.prevPos = prevItem.nextPos || { lat: prevItem.prevPos.lat, lon: prevItem.prevPos.lon };
                prevItem.nextPos = { lat, lon };
                prevItem.t0 = t_fetch; prevItem.t1 = t_fetch + ANIMATE_MS;
                
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

  // Show/hide labels based on zoom
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
    
    print(f"GeoFS Live Radar running on http://0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
