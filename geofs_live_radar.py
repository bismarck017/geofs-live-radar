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
- Shows all Aircraft's Details
- Advanced Search Filter
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

  :root {
    --bg-main: #f5f7fa;
    --bg-panel: rgba(255,255,255,0.85);
    --toggle-button: rgba(0,0,0,0.65);
    --bg-map-border: #ccc;
    --bg-search-panel-border: #ccc;

    --text-main: #000;
    --text-muted: #444;

    --label-bg: rgba(255,255,255,0.95);
    --label-text: #000;
    --label-border: rgba(0,0,0,0.12);

    --accent: #0a84ff;
  }

  body.dark {
    --bg-main: #0b0f14;
    --bg-panel: rgba(0,0,0,0.7);
    --toggle-button: rgba(255,255,255,0.5);
    --bg-map-border: #1e2a38;
    --bg-search-panel-border: rgba(0,255,140,0.35);

    --text-main: #ffffff;
    --text-muted: #b0b0b0;

    --label-bg: #2a2a2a;
    --label-text: #39FF14;
    --label-border: rgba(255,255,255,0.15);
    --filter-header-color: #30f00c;

    --accent: #00ff9c;
  }




  html,body,#map { height:100%; margin:0; }


  .hud {
    position:fixed; left:8px; top:8px; z-index:9999;
    background:rgba(0,0,0,0.65); color:#fff; padding:8px 10px; border-radius:8px;
    font-family: system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial; font-size:13px;
  }
  .label {
    background: var(--label-bg);
    padding:3px 7px;
    border-radius:4px;
    font-weight:700;
    font-size:12px;
    color: var(--label-text);
    border: 1px solid var(--label-border);
    white-space:nowrap;
    pointer-events:none;
    box-shadow: 0 2px 6px rgba(0,0,0,0.35);
  }
  
  body {
    background: linear-gradient(
        180deg,
        rgba(173,216,230,0.22),
        rgba(245,245,220,0.22)
    );
    color: var(--text-main);
  }

  body.dark {
    background: linear-gradient(
        180deg,
        #181818,
        #202020
    );
  }


  
  #map { 
    height:90%;
    width:95%;  
    margin: 40px auto;
    border: 2px solid var(--bg-map-border);
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


  .theme-toggle {
    position: fixed;
    top: 15px;
    right: 15px;
    z-index: 10000;

    width: 50px;
    height: 50px;
    border-radius: 50%;
    border: none;

    background: var(--toggle-button);
    color: var(--accent);

    font-size: 18px;
    cursor: pointer;

    display: flex;
    align-items: center;
    justify-content: center;

    backdrop-filter: blur(6px);
    transition: transform 0.2s ease;
  }

  .theme-toggle:hover {
    transform: scale(1.08);
  }

  
  /* Leaflet popup – light mode (optional, matches your UI) */
  .leaflet-popup-content-wrapper,
  .leaflet-popup-tip {
    background: #ffffff;
    color: #000;
  }

  /* Leaflet popup – dark mode */
  body.dark .leaflet-popup-content-wrapper,
  body.dark .leaflet-popup-tip {
    background: #2a2a2a;   /* YouTube-like dark */
    color: #eaeaea;
    box-shadow: 0 8px 20px rgba(0,0,0,0.6);
  }

  /* Popup text inside */
  body.dark .leaflet-popup-content {
    color: #eaeaea;
  }

  /* Optional: popup close button */
  body.dark .leaflet-popup-close-button {
    color: #ccc;
  }
  body.dark .leaflet-popup-close-button:hover {
    color: #fff;
  }

  body.dark .leaflet-popup-content-wrapper {
    border: 1px solid rgba(0,255,140,0.25);
  }


  /* FILTER MODAL */

  .filter-toggle {
    position: fixed;
    top: 2px;
    left: 50%;
    transform: translateX(-50%);

    z-index: 10000;

    padding: 10px 14px;
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.25);

    cursor: pointer;
    font-weight: 700;

    background: rgba(0,0,0,0.65);
    color: white;

    backdrop-filter: blur(6px);
  }


  .filter-panel {
    position: fixed;
    top: 65px;
    left: 50%;
    transform: translateX(-50%) scale(.96);

    width: fit-content;
    min-width: 320px;
    max-width: 95%;

    max-height: none;

    background: var(--bg-panel);
    color: var(--text-main);

    border: 1px solid var(--bg-search-panel-border);
    border-radius: 12px;

    box-shadow: 0 18px 35px rgba(0,0,0,0.45);

    padding: 12px 14px;

    opacity: 0;
    pointer-events: none;
    transition: opacity .2s ease, transform .2s ease;

    z-index: 12000;
  }

  .filter-panel.open {
    opacity: 1;
    pointer-events: auto;
    transform: translateX(-50%) translateY(-17%) scale(1);
  }



  .filter-header {
    color: var(--filter-header-color);
    font-family: sans-serif;
    font-weight: 200;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: bold;
    font-size: 15px;
  }

  .close-btn {
    background: transparent;
    border: none;
    font-size: 16px;
    cursor: pointer;
    color: var(--text-main);
  }

  .tag-input-row {
    display: flex;
    gap: 6px;
    margin: 10px 0;
  }

  #tagInput {
    flex: 1;
    padding: 6px;
    border-radius: 6px;
    border: 1px solid var(--bg-map-border);
    background: var(--bg-main);
    color: var(--text-main);
  }


  /* BUTTONS — clean glass style */

  .add-btn,
  #resetBtn {
    padding: 8px 12px;
    border-radius: 10px;

    background: rgba(255,255,255,0.35);
    border: 1px solid rgba(0,0,0,0.15);
    color: #111;

    font-weight: 600;
    cursor: pointer;

    backdrop-filter: blur(8px);

    transition: background .15s ease, transform .15s ease, box-shadow .15s ease;
  }

  .add-btn:hover,
  #resetBtn:hover {
    background: rgba(255,255,255,0.55);
    transform: translateY(-1px);
    box-shadow: 0 10px 18px rgba(0,0,0,0.15);
  }

  /* DARK MODE BUTTONS */
  body.dark .add-btn,
  body.dark #resetBtn {
    background: rgba(0,0,0,0.55);
    border: 1px solid rgba(0,255,140,0.28);
    color: #dfffe7;
  }

  body.dark .add-btn:hover,
  body.dark #resetBtn:hover {
    background: rgba(0,0,0,0.75);
    box-shadow: 0 14px 26px rgba(0,0,0,0.6);
  }


  .tag-list {
    margin-top: 8px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .tag {
    background: rgba(255,255,255,0.45);
    padding: 2px 6px;
    border-radius: 5px;
    color: #0a0a0a;
    border: 1px solid rgba(0,0,0,0.15);
    backdrop-filter: blur(6px);
    font-weight: 600;
    font-size: 11px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  body.dark .tag {
    background: rgba(0,0,0,0.55);
    color: #D0D9CD;
    border: 1px solid rgba(0,255,140,0.35);
  }

  .tag button {
    font-size: 10px;
    border: none;
    background: transparent;
    cursor: pointer;
    font-weight: bold;
    opacity: 0.6;
    transition: opacity .15s;
  }

  .tag button:hover {
    opacity: 1;
  }

  body.dark .tag button {
    font-size: 10px;
    border: none;
    background: transparent;
    cursor: pointer;
    font-weight: bold;
    color: #D0D9CD;
    opacity: 0.6;
    transition: opacity .15s;
  }

  body.dark .tag button:hover {
    opacity: 1;
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

<button id="themeToggle" class="theme-toggle">🌙</button>   

<!-- FILTER MODAL -->
<div id="filterPanel" class="filter-panel">
  <div class="filter-header">
    <span>Filters:</span>
    <button id="closeFilter" class="close-btn">✖</button>
  </div>

  <div class="tag-input-row">
    <input id="tagInput" type="text" placeholder="Example: DoI, [UAE], Harry…">
    <button id="addTagBtn" class="add-btn">Add</button>
  </div>

  <div id="tagList" class="tag-list"></div>

  <button id="resetBtn" class="add-btn" style="margin-top:10px; width:100%;"> Reset </button>

</div>

<!-- OPEN BUTTON -->
<button id="openFilter" class="filter-toggle">🔍 Filter-Callsigns</button>


<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
<script>
(async function(){
  const REFRESH_MS = 2000;
  const ANIMATE_MS = REFRESH_MS;
  const STALE_MS = 15000;
  const LABEL_ZOOM_MIN = 0;

  // Show only callsigns with these tags
  const DEFAULT_TAGS = [
    "[U]","[UTP]","[P]","[PMC]","[NKG-KG]","[SHL]","[NFS]","[AEF]", "lasallian", "butter", "ek-069", "tarun", "massiv4515", "walch", "ljf", "ek-1", "notipa", "est201", "raptor4001", "speedbird",
    "[WANK]", "[NIUF]", "[TBD]", "[Luftwaffe]", "[BPYR]", "[Luftwafe]", "[MAC]", "[PRC]", "xavier", "tassin",
    "[TASC]", "[UAC]", "[USSR]", "[JASDF]", "[EVKS]", "[VKS]", "[ACP]", "[PYR]", "[FFL]", "[IOA]", "AF]"
  ];

  const TAGS_KEY = "geofs_radar_tags";

  
  let activeTags;
  try {
    activeTags = JSON.parse(localStorage.getItem(TAGS_KEY)) || [...DEFAULT_TAGS];
  } catch {
    activeTags = [...DEFAULT_TAGS];
  }


  
  const AIRCRAFT_DB = {
    1: "Piper Cub",
    2: "Cessna 172",
    3: "Alphajet PAF",
    4: "Boeing 737-700",
    5: "Embraer Phenom 100",
    6: "de Havilland DHC6 Twin Otter",
    7: "F-16 Fighting Falcon",
    8: "Pitts Special S1",
    9: "Eurocopter EC135",
    10: "Airbus A380",
    11: "Alisport Silent 2 Electro",
    12: "Pilatus PC-7 Mk-I",
    13: "de Havilland Canada DHC-2 Beaver",
    14: "Colomban MC-15 Cri-cri",
    15: "Lockheed P-38 Lightning F-5B",
    16: "Douglas DC-3",
    18: "Sukhoi Su-35",
    20: "Concorde",
    21: "Zlin Z-50",
    22: "Cessna 152",
    23: "Piper PA-28 161 Warrior II Aerobility",
    24: "Airbus A350",
    25: "Boeing 777-300ER",
    26: "Antonov An-140",
    27: "Boeing F/A-18F Super Hornet",
    28: "Beechcraft Baron B55",
    29: "Dassault Rafale",
    31: "Potez 25",
    32: "Northrop T-38 Talon",
    40: "Evektor Sportstar",
    41: "szd-48-3 Jantar",
    50: "Paraglider",
    51: "Major Tom (hot air balloon)",
    52: "Hughes 269a/TH-55 Osage",
    53: "Goat Airchair",
    102: "Citroen 2CV",
    103: "Wingsuit",
    235: "Boeing 787-8 (by GX Development)",
    236: "Embraer E190 (by GX Development)",
    237: "Boeing 767-300ER (by GX Development)",
    238: "Boeing 757-200 (by GX Development)",
    239: "Airbus A350-900 (by GX Development)",
    240: "Boeing 777-300ER (by LRX)",
    242: "Airbus A321neo (by LRX)",
    244: "Airbus A330-300 (by LRX)",
    247: "Bombardier Dash 8 Q400 (by LRX)",
    252: "Boeing 747-8 Freighter (by LRX)",
    1069: "Cirrus SR22 GTS Turbo (by LRX)",
    2000: "Retro 172",
    2003: "Boeing 737-800 (by King Solomon)",
    2004: "CRJ-900 (by King Solomon)",
    2153: "Airbus A340-600 (by LRX)",
    2310: "A-10C Thunderbolt II (by Eco[LAC])",
    2364: "Lockheed SR-71A Blackbird (by BritishPilot[GeoAD])",
    2386: "Boeing 787-9 Dreamliner (by LRX)",
    2395: "BAe 146-300/Avro RJ100 (by Eco[LAC])",
    2418: "ATR 72-600 (HOP!) (by JAaMDG)",
    2420: "ATR 72-600 (Silver) (by JAaMDG)",
    2426: "ATR 72-600 (UTair) (by JAaMDG)",
    2461: "Cirrus Vision Jet/SF50 G2 (by Eco[LAC])",
    2556: "Northrop Grumman B-2 Spirit (by NS-Studios)",
    2581: "F-14B Tomcat (by Eco[LAC])",
    2700: "Embraer ERJ-195AR (Breeze) (by Featherway[UAE232])",
    2706: "Bombardier CRJ 200 (by Aero281)",
    2726: 'Scaled 339 "SpaceShipTwo" (by JAaMDG)',
    2750: "Caproni Stipa (by Echo_3)",
    2752: 'Scaled 348 "WhiteKnightTwo" (by JAaMDG)',
    2769: "Boeing 737 Max 8 (TUI) (by Spice_9)",
    2772: "Boeing 737 Max 8 (SpiceJet) (by Spice_9)",
    2786: "Grumman JF2-5 Duck (by Echo_3)",
    2788: "Antonov An-225 Mriya (by NS-Studios)",
    2806: "Sikorsky S-97 Raider (by JAaMDG)",
    2808: "Supermarine Spitfire Mk XIV (by Eco[LAC])",
    2840: "Bell UH-1H Iroquois (by ElonMusk(VrA)(LAC))",
    2843: "Airbus A220-300 (Air Tanzania) (by GT-VRA)",
    2844: "Falcon 9 (by Echo_3)",
    2852: "Cameron R-650 Rozière Balloon (by JAaMDG)",
    2856: "Airbus a330-200 (by Aero281)",
    2857: "F-22 Raptor (by SpaceRage)",
    2864: "AgustaWestland AW609 (by JAaMDG)",
    2865: "Airbus a320neo(Air India) (by Spice_9)",
    2870: "Airbus a320neo (Flynas) (by Spice_9)",
    2871: "Airbus a320neo (Iberia) (by Spice_9)",
    2878: "Airbus A319 (Air China) (by GT-VRA)",
    2879: "Airbus A319 (Finnair) (by GT-VRA)",
    2892: "SAAB 340 (by Spice_9)",
    2899: "Airbus A220-300 (Swiss) (by GT-VRA)",
    2943: "Embraer EMB120 Brasillia (by GT-VRA)",
    2948: "(JAaMDG) North American XB-70 Valkyrie (by Johani_(NeoAD))",
    2951: "Airbus a340-300 (by Aero281)",
    2953: "Space Shuttle Atlantis (OV-104) (by JAaMDG)",
    2968: "Windward Performance Perlan II (by JAaMDG)",
    2973: "Airbus A350-1000 XWB (by NS-Studios)",
    2976: "Pilatus PC12 (by GT-VRA)",
    2988: "(TBSG, GeoAD) North American X-15 (by Johani_(NeoAD))",
    2989: "MQ9B Reaper (by Aero281)",
    3011: "Airbus a320-232 (by Spice_9)",
    3036: "Embraer E195-E2 (by GT-VRA)",
    3049: "Lockheed Martin P-791 (LMH-1) (by JAaMDG)",
    3054: "Boeing 737-800 [Spice9] (by Spice_9)",
    3109: "Pilatus PC24 (by GT-VRA)",
    3140: "Airbus A319 (United) (by GT-VRA)",
    3179: "Boeing 787-10 Dreamliner (British Airways) (by Spice_9)",
    3180: "Boeing 787-10 Dreamliner (Etihad) (by Spice_9)",
    3211: "UTVA75 (by GT-VRA)",
    3289: "Dornier 228-200 (by Spice_9)",
    3292: "Boeing p8I Neptune (by Spice_9)",
    3307: "Bombardier CRJ-700 (by AriakimTaiyo)",
    3341: "Embraer ERJ-170 (by AriakimTaiyo)",
    3436: "Dornier do228-100 (Coast Gaurd) (by Spice_9)",
    3460: "Grumman E-2C Hawkeye (by ElonMusk(VrA)(LAC))",
    3534: "airbus a320-214(Easyjet) (by Spice_9)",
    3575: "Boeing 787-9(Spice9) (by Spice_9)",
    3591: "F-15C Eagle (by AriakimTaiyo)",
    3617: "Dassault Mirage 2000-5 (by ElonMusk(VrA)(LAC))",
    4017: "Embraer ERJ145LR (by Spice 9) & (by GT-VRA)",
    4090: "Robinson R-44 (by (CCDev)DevHunter77)",
    4140: "Boeing 737-200 (by AriakimTaiyo)",
    4197: "Robinson R22 (by (CCDev)DevHunter77)",
    4251: "Chance Vought F4U-1D Corsair (by JAaMDG)",
    4341: "Spirit of St louis (by Echo_3)",
    4390: "Piper PA-28 Floatplane (by coolpilot11)",
    4398: "Britten-Norman BN-2 Islander (Loganair) (by coolpilot11)",
    4401: "Britten-Norman BN-2 Islander (St. Barth Commuter) (by coolpilot11)",
    4402: "Boeing 777 Freighter (by LRX)",
    4409: "Zenith Stol CH701 (by coolpilot11)",
    4596: "Vans RV6 (by coolpilot11)",
    4631: "Airbus A330-900neo (Virgin Atlantic) (by GT-VRA)",
    4646: "Airbus a321neo (spice9) (by Spice_9)",
    4743: "Boeing 757-300 (by GT-VRA)",
    4745: "Boeing 757-300wl (by GT-VRA)",
    4764: "Boeing 767-400 (by GT-VRA)",
    4949: "Goodyear Blimp (by BritishPilot[GeoAD])",
    5002: "Beta Alia Prototype (N250UT) (by coolpilot11)",
    5038: "Lockheed L-1011-1 (by AriakimTaiyo)",
    5061: "Sonex-B Kit (Jabiru 3300) (by TurboMaximus)",
    5073: "Bombardier Learjet 45 XR (by Spice_9)",
    5086: "Airbus a321-211 (by Spice_9)",
    5156: "Airbus a318-112 by Luca & (by Spice_9)",
    5193: "Boeing 747-8i (by JAaMDG)",
    5203: "Boeing 737-600 by Luca & (by Spice_9)",
    5229: "F-35B Lightning II (by JAaMDG)",
    5314: "Boeing 747-100 SCA by JAaMDG & (by Jeffa)",
    5316: "Boeing 717-200 (by Plane2222222)",
    5347: "Dassault Mirage F1 (by MirageModels)",
    5405: "Chengdu J-20 (by MirageModels)",
    5409: "Boeing 747-400D by JAaMDG & (by BOA93(EAA))",
    5431: "Northrop YF-23 (by MirageModels)",
    5486: "Aviat A-1B Husky (by coolpilot11)",
    5499: "CubCrafters CC19 XCub (by AriakimTaiyo)",
    5516: "Boeing 747-400 LCF by Luca & (by JAaMDG)"
    // you can keep extending this list
  };

  function getAircraftName(ac) {
    if (ac == null) return "Unknown Aircraft";
    return AIRCRAFT_DB[ac] || `Unknown Aircraft (ID ${ac})`;
  }


  
  const AC = {};

  let LOCKED_ID = null;

  const map = L.map('map', { 
    preferCanvas:true, 
    worldCopyJump: false,
    minZoom: 1,
    maxBounds: [[-300, -300], [300, 300]],
  }).setView([20,0], 2);

  
  const lightTiles = L.tileLayer(
    'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    {
        attribution: '&copy; OpenStreetMap & Carto',
        maxZoom: 19,
    }
  );

  const darkTiles = L.tileLayer(
    'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    {
        attribution: '&copy; OpenStreetMap & Carto',
        maxZoom: 19,
    }
  );

// default (light mode)
lightTiles.addTo(map);


  

  map.on('click', function () {
    if (LOCKED_ID) {
        const it = AC[LOCKED_ID];
        if (it && it.marker) it.marker.closePopup();
        LOCKED_ID = null;
    }
  });




  function nowMs(){ return Date.now(); }

  
  document.getElementById("resetBtn").onclick = () => {
    activeTags = [...DEFAULT_TAGS];
    renderTags();
    applyFilterNow();
    localStorage.removeItem(TAGS_KEY);
    location.reload(); //remove this in the next update
  };




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
    return L.divIcon({ className:'', html:`<div class="label">${text}</div>`, iconSize:[10,10], iconAnchor:[-2,-7] });
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

  function popupHTML(it){
    return `
      <div style="font-size:13px; line-height:1.45; min-width:200px">
        <div><b>Callsign:</b> ${it.callsign}</div>
        <div><b>User ID:</b> ${it.uid ?? '—'}</div>
        <div><b>ACID:</b> ${it.acid ?? '—'}</div>
        <div><b>Aircraft Type:</b> ${it.aircraft ?? '—'}</div>
        <div><b>Altitude:</b> ${it.alt != null ? Math.round(it.alt) + ' ft' : '—'}</div>
        <div><b>Speed:</b> ${it.speed != null ? Math.round(it.speed) + ' kt' : '—'}</div>
        <div><b>Heading:</b> ${it.lastBearing != null ? Math.round(it.lastBearing) + '°' : '—'}</div>
      </div>
    `;
  }

  
  function normalizeHeading(hdg){
    if (typeof hdg !== 'number' || !isFinite(hdg)) return null;
    return (hdg + 360) % 360;
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

            const lat = u.co[0], lon = u.co[1], alt_in_meters = u.co[2], hdgServer = u.co[3];

            const alt = alt_in_meters * 3.28084;



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
            const show = activeTags.length === 0 || activeTags.some(k => callsign.toUpperCase().includes(k.toUpperCase()));
            if (!show) continue;

            const id = String(u.id || u.acid || Math.random());
            const prevItem = AC[id];

            if (!prevItem){
                const m = L.marker([lat, lon], { icon: makeIcon(hdgServer || 0), riseOnHover: true }).addTo(map);

                m.bindPopup('Loading...', { closeButton: true, autoClose: false, closeOnClick: false,});

                m.on('mouseover', function () {
                    if (LOCKED_ID && LOCKED_ID !== id) return;
                    this.openPopup();
                });

                m.on('mouseout', function () {
                    if (LOCKED_ID) return;
                    this.closePopup();
                });

                m.on('click', function (e) {
                    e.originalEvent.stopPropagation();
                    // Clicking the same aircraft unlocks it
                    if (LOCKED_ID === id) {
                        LOCKED_ID = null;
                        this.closePopup();
                        return;
                    }

                    // Lock this aircraft
                    LOCKED_ID = id;
                    this.openPopup();
                });




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
                    uid: u.id ?? null,
                    acid: u.acid ?? null,
                    alt,
                    speed: u.st?.as ?? null,
                    aircraft: getAircraftName(u.ac),
                };

                m.setPopupContent(popupHTML(AC[id]));


            } else {
                prevItem.prevPos = prevItem.nextPos || { lat: prevItem.prevPos.lat, lon: prevItem.prevPos.lon };
                prevItem.nextPos = { lat, lon };
                prevItem.t0 = t_fetch; prevItem.t1 = t_fetch + ANIMATE_MS;
                
                let cog = hdgServer != null ? hdgServer : prevItem.lastBearing || 0;
                const moved = Math.abs(lat - prevItem.prevPos.lat) + Math.abs(lon - prevItem.prevPos.lon);
                if (moved > 1e-5 && hdgServer == null) {
                    cog = bearingFromTo(prevItem.prevPos.lat, prevItem.prevPos.lon, lat, lon);
                }
                prevItem.lastBearing = normalizeHeading(cog);
                if (prevItem.marker) prevItem.marker.setIcon(makeIcon(prevItem.lastBearing));
                if (prevItem.label) prevItem.label.setIcon(makeLabel(callsign));


                prevItem.alt = alt;
                prevItem.speed = u.st?.as ?? prevItem.speed;
                prevItem.aircraft = getAircraftName(u.ac);
                prevItem.uid = u.id ?? prevItem.uid;
                prevItem.acid = u.acid ?? prevItem.acid;


                if (prevItem.marker){
                    prevItem.marker.setPopupContent(popupHTML(prevItem));
                }


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


  function applyFilterNow() {
    for (const id in AC) {
        const it = AC[id];
        const cs = it.callsign || "";

        const show =
            activeTags.length === 0 ||
            activeTags.some(k =>
                cs.toUpperCase().includes(k.toUpperCase())
            );

        if (!show) {
            if (it.marker) map.removeLayer(it.marker);
            if (it.label) map.removeLayer(it.label);
            delete AC[id];
        }
    }
  }


  
  const panel = document.getElementById("filterPanel");
  const openBtn = document.getElementById("openFilter");
  const closeBtn = document.getElementById("closeFilter");


  function renderTags() {
    const list = document.getElementById("tagList");
    list.innerHTML = "";

    activeTags.forEach((tag, i) => {
      const el = document.createElement("div");
      el.className = "tag";
      el.innerHTML = `
        ${tag}
        <button onclick="removeTag(${i}, event)">✖</button>
      `;
      list.appendChild(el);
    });

    // SAVE
    localStorage.setItem(TAGS_KEY, JSON.stringify(activeTags));

  }

  window.removeTag = function(i, e){
    e.stopPropagation();
    activeTags.splice(i, 1);
    renderTags();
    applyFilterNow();
  };


  document.getElementById("addTagBtn").onclick = () => {
    const inp = document.getElementById("tagInput");
    const v = inp.value.trim();
    if (!v) return;

    activeTags.push(v);
    inp.value = "";
    renderTags();
    applyFilterNow();
  };

  const tagInput = document.getElementById("tagInput");

  tagInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      document.getElementById("addTagBtn").click();
    }
  });


  


  openBtn.onclick = () => panel.classList.toggle("open");
  closeBtn.onclick = () => panel.classList.remove("open");

  document.addEventListener("click", (e) => {
    const themeBtn = document.getElementById("themeToggle");

    if (
      panel.contains(e.target) ||
      openBtn.contains(e.target) ||
      themeBtn.contains(e.target)
    ) {
      return;                 // don't close
    }

    panel.classList.remove("open");
  });





  renderTags();

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


  const toggleBtn = document.getElementById("themeToggle");

  function setTheme(dark) {
    document.body.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
    toggleBtn.textContent = dark ? "☀️" : "🌙";

    if (dark) {
        map.removeLayer(lightTiles);
        darkTiles.addTo(map);
    } else {
        map.removeLayer(darkTiles);
        lightTiles.addTo(map);
    }
  }

  const saved = localStorage.getItem("theme");
  setTheme(saved === "dark");

  toggleBtn.addEventListener("click", () => {
    setTheme(!document.body.classList.contains("dark"));
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
