import threading
import time
import requests
from flask import Flask

app = Flask(__name__)

# ------------------ Config ------------------
PORT = 5000
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1406156183827382282/nRpVsLaN8uAV9189JmzwKthgv7vLTOMGMJwss-SYV8AzTyuYkJ0NjYSzrCPryFPxJ13D"
AC_MAP_URL = None  # keep as it is unless you load external AC map

# Track who is in airspace
in_airspace = set()

# ------------------ Functions ------------------
def get_players():
    print("🔍 DEBUG: get_players() called")  
    try:
        # Replace this with your actual player fetching logic
        # Example (dummy):
        response = requests.get("https://your-api-or-source.com/players")
        players = response.json()
        print(f"🔍 DEBUG: API returned {len(players)} players")
        return players
    except Exception as e:
        print(f"❌ ERROR in get_players: {e}")
        return []

def send_discord_message(msg):
    print(f"📡 DEBUG: Sending Discord message: {msg}")
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
        print(f"📡 DEBUG: Discord response {r.status_code}")
    except Exception as e:
        print(f"❌ ERROR sending to Discord: {e}")

def airspace_monitor_loop():
    print("✅ Airspace monitor loop started")
    global in_airspace

    while True:
        try:
            players = get_players()
            current_players = set(p["id"] for p in players)  # assuming players have "id"

            # Detect entries
            for pid in current_players - in_airspace:
                msg = f"✈️ Player {pid} ENTERED airspace"
                send_discord_message(msg)

            # Detect exits
            for pid in in_airspace - current_players:
                msg = f"🛫 Player {pid} LEFT airspace"
                send_discord_message(msg)

            # Update state
            in_airspace = current_players

            print(f"🔁 DEBUG: Loop iteration done. Now {len(in_airspace)} players in airspace.")
            time.sleep(10)

        except Exception as e:
            print(f"❌ ERROR in monitor loop: {e}")
            time.sleep(5)

def start_background():
    t = threading.Thread(target=airspace_monitor_loop, daemon=True)
    t.start()
    print("✅ Background thread started")

# ------------------ Main ------------------
if __name__ == "__main__":
    if AC_MAP_URL:
        try:
            try_load_ac_map()
        except Exception as e:
            print("Error loading AC map:", e)
    else:
        print(f"Using default AC map. Set AC_MAP_URL to load more.")

    start_background()

    print(f"🌍 GeoFS Live Radar running on http://0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
