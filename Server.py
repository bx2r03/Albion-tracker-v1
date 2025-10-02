import requests, time, os
from threading import Thread
from flask import Flask, jsonify, render_template_string
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

BASE = "https://gameinfo.albiononline.com/api/gameinfo"
seen = set()
kills_cache = []

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Albion Live Killboard</title>
    <script src="https://cdn.socket.io/4.6.1/socket.io.min.js"></script>
    <style>
        body { background:#0a0a0a; color:#fff; font-family:Arial; text-align:center; padding:20px; }
        h1 {
            margin-bottom:0;
            font-size:36px;
            font-weight:bold;
            color:#00c8ff;
            text-shadow: 0 0 5px #00c8ff, 0 0 10px #00c8ff, 0 0 20px #00e5ff;
            animation: glowPulse 2s ease-in-out infinite alternate;
        }
        h2 { margin-top:5px; font-weight:normal; font-size:14px; color:#888; }
        .kill {
            background:#111;
            margin:5px 0;
            padding:10px;
            border-radius:10px;
            display:flex;
            justify-content:center;
            gap:10px;
            box-shadow:0 0 10px rgba(0,200,255,0.1);
        }
        .player { font-weight:bold; }
        .fame { font-weight:bold; }
        @keyframes glowPulse {
            from { text-shadow: 0 0 5px #00c8ff, 0 0 10px #00c8ff, 0 0 20px #00e5ff; }
            to   { text-shadow: 0 0 10px #00e5ff, 0 0 20px #00faff, 0 0 30px #00ffff; }
        }
    </style>
</head>
<body>
    <h1>AHZ MIPPONN</h1>
    <h2>dev by bx2r03</h2>

    <label>Filter Guild: <input type="text" id="guildFilter" placeholder="Enter guild name"></label>
    <div id="feed"></div>

    <script>
        const socket = io();
        const feed = document.getElementById("feed");
        const guildInput = document.getElementById("guildFilter");
        const guildColors = {};

        function getFameColor(fame) {
            if(fame >= 1000) return "gold";
            if(fame >= 500) return "orange";
            return "white";
        }

        function getGuildColor(guild) {
            if(!guild) return "#00ffcc";
            if(!guildColors[guild]) {
                const color = `hsl(${Math.floor(Math.random()*360)}, 70%, 60%)`;
                guildColors[guild] = color;
            }
            return guildColors[guild];
        }

        function createKillDiv(k) {
            if(guildInput.value && (!k.killer_guild || !k.killer_guild.toLowerCase().includes(guildInput.value.toLowerCase()))) return null;
            const div = document.createElement("div");
            div.classList.add("kill");
            div.innerHTML = `
                <span class="player killer" style="color:${getGuildColor(k.killer_guild)}">${k.killer}</span> ⚔️
                <span class="player victim">${k.victim}</span> 
                <span class="fame" style="color:${getFameColor(k.fame)}">(+${k.fame} fame)</span>
            `;
            return div;
        }

        function loadKills() {
            fetch("/api/kills").then(res => res.json()).then(data => {
                feed.innerHTML = "";
                data.reverse().forEach(k => {
                    const div = createKillDiv(k);
                    if(div) feed.prepend(div);
                });
            });
        }

        function addKill(k) {
            const div = createKillDiv(k);
            if(div) {
                feed.prepend(div);
                if(feed.children.length > 50) feed.removeChild(feed.lastChild);
            }
        }

        socket.on("new_kill", data => addKill(data));
        loadKills();
        setInterval(loadKills, 30000);
        guildInput.addEventListener("input", () => loadKills());
    </script>
</body>
</html>
"""

def fetch_kills():
    global kills_cache
    while True:
        try:
            resp = requests.get(f"{BASE}/events?limit=20&offset=0")
            if resp.status_code == 200:
                data = resp.json()
                new_kills = []
                for event in data:
                    event_id = event.get("EventId")
                    if event_id not in seen:
                        seen.add(event_id)
                        killer = event.get("Killer", {}).get("Name")
                        victim = event.get("Victim", {}).get("Name")
                        killer_guild = event.get("Killer", {}).get("GuildName")
                        fame = event.get("TotalVictimKillFame")
                        kill = {"killer": killer, "victim": victim, "killer_guild": killer_guild, "fame": fame}
                        new_kills.append(kill)
                if new_kills:
                    kills_cache = new_kills + kills_cache[:50]
                    for k in new_kills:
                        socketio.emit("new_kill", k)
        except Exception as e:
            print("Error:", e)
        time.sleep(5)

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/api/kills")
def get_kills():
    return jsonify(kills_cache)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    Thread(target=fetch_kills, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=port)
