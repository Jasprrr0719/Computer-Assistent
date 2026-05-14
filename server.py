"""
Server – Web-Dashboard + Handy-Steuerung + WebSocket Live-Updates.
Sci-Fi Control Center UI.
"""

from flask import Flask, request, jsonify, render_template_string
from flask_socketio import SocketIO
import threading
import socket
import json
import time
import datetime
import psutil
import os
import sys

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>{{ name }} – Control Center</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.4/socket.io.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#050510;--card:#0a0a1a;--border:#1a2a3c;--gold:#ff9d2e;--gold-dim:#5a4020;--green:#00ff88;--red:#ff4444;--blue:#4488ff;--text:#c0c0c0;--text-dim:#555}
body{background:var(--bg);color:var(--text);font-family:'Consolas','Courier New',monospace;min-height:100vh;overflow-x:hidden}
.top-bar{background:var(--card);border-bottom:1px solid var(--border);padding:12px 20px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}
.top-bar h1{color:var(--gold);font-size:16px;letter-spacing:4px}
.top-bar .status{font-size:11px;color:var(--green)}
.top-bar .time{color:var(--gold-dim);font-size:12px}
.nav{background:var(--card);border-bottom:1px solid var(--border);padding:8px 20px;display:flex;gap:8px;overflow-x:auto;position:sticky;top:44px;z-index:99}
.nav button{background:transparent;border:1px solid var(--border);color:var(--text-dim);padding:6px 14px;border-radius:6px;font-family:inherit;font-size:11px;cursor:pointer;white-space:nowrap;transition:all 0.2s}
.nav button:hover,.nav button.active{border-color:var(--gold);color:var(--gold);background:rgba(255,157,46,0.05)}
.container{padding:15px;max-width:1200px;margin:0 auto}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:700px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;transition:border-color 0.3s}
.card:hover{border-color:var(--gold-dim)}
.card h3{color:var(--gold);font-size:12px;letter-spacing:2px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center}
.card h3 .badge{font-size:9px;padding:2px 6px;border-radius:4px;background:rgba(0,255,136,0.1);color:var(--green)}
.full{grid-column:span 2}
@media(max-width:700px){.full{grid-column:span 1}}
.metric{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.03)}
.metric:last-child{border:none}
.metric .label{color:var(--text-dim);font-size:11px}
.metric .value{color:var(--gold);font-size:13px;font-weight:bold}
.bar-bg{width:100%;height:6px;background:rgba(255,255,255,0.05);border-radius:3px;margin-top:4px}
.bar-fill{height:100%;border-radius:3px;transition:width 0.5s}
.bar-fill.cpu{background:linear-gradient(90deg,var(--green),var(--gold))}
.bar-fill.ram{background:linear-gradient(90deg,var(--blue),var(--gold))}
.bar-fill.disk{background:linear-gradient(90deg,var(--gold),var(--red))}
.log-list{max-height:300px;overflow-y:auto;font-size:11px}
.log-item{padding:5px 8px;border-bottom:1px solid rgba(255,255,255,0.02);display:flex;gap:8px}
.log-item .time{color:var(--text-dim);min-width:55px}
.log-item .type{min-width:60px;font-size:10px;padding:1px 4px;border-radius:3px}
.log-item .type.EXECUTED{color:var(--green);background:rgba(0,255,136,0.05)}
.log-item .type.BLOCKED{color:var(--red);background:rgba(255,68,68,0.05)}
.log-item .type.ALLOWED{color:var(--blue);background:rgba(68,136,255,0.05)}
.input-area{display:flex;gap:8px;margin-bottom:15px}
.input-area input{flex:1;background:var(--card);border:1px solid var(--border);border-radius:8px;color:var(--gold);font-family:inherit;font-size:13px;padding:10px 14px;outline:none}
.input-area input:focus{border-color:var(--gold)}
.input-area input::placeholder{color:var(--text-dim)}
.btn{background:rgba(255,157,46,0.08);border:1px solid var(--gold-dim);border-radius:6px;color:var(--gold);padding:8px 16px;font-family:inherit;font-size:12px;cursor:pointer;transition:all 0.2s;-webkit-tap-highlight-color:transparent}
.btn:hover,.btn:active{background:rgba(255,157,46,0.15);border-color:var(--gold)}
.btn.danger{border-color:var(--red);color:var(--red)}
.btn.danger:hover{background:rgba(255,68,68,0.1)}
.btn-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.btn-grid .btn{padding:10px 8px;font-size:11px;text-align:center}
.task-item{padding:8px;border:1px solid var(--border);border-radius:6px;margin-bottom:6px;font-size:11px}
.task-item .task-status{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.task-item .task-status.completed{background:var(--green)}
.task-item .task-status.running{background:var(--gold);animation:pulse 1s infinite}
.task-item .task-status.failed{background:var(--red)}
.task-item .task-status.pending{background:var(--text-dim)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}}
.tool-item{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.03);font-size:11px}
.tool-item .tool-name{color:var(--gold)}
.tool-item .tool-desc{color:var(--text-dim);font-size:10px}
.toggle{width:36px;height:20px;background:var(--border);border-radius:10px;position:relative;cursor:pointer;transition:background 0.3s}
.toggle.on{background:var(--green)}
.toggle::after{content:'';position:absolute;width:16px;height:16px;background:white;border-radius:50%;top:2px;left:2px;transition:left 0.3s}
.toggle.on::after{left:18px}
.setting-row{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.03)}
.setting-row .label{color:var(--text-dim);font-size:11px}
.setting-row select,.setting-row input[type=text]{background:var(--bg);border:1px solid var(--border);color:var(--gold);padding:4px 8px;border-radius:4px;font-family:inherit;font-size:11px}
.response-box{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px;font-size:12px;color:var(--text);min-height:60px;max-height:200px;overflow-y:auto;margin-top:10px}
.section{display:none}
.section.active{display:block}
.orb-mini{width:40px;height:40px;border-radius:50%;border:1px solid var(--gold-dim);position:relative;display:flex;align-items:center;justify-content:center}
.orb-mini::after{content:'';width:20px;height:20px;border-radius:50%;background:radial-gradient(circle,rgba(255,157,46,0.4),transparent);animation:pulse 2s infinite}
</style>
</head>
<body>

<div class="top-bar">
<div style="display:flex;align-items:center;gap:12px">
<div class="orb-mini"></div>
<div>
<h1>{{ name }}</h1>
<div class="status" id="status">● ONLINE</div>
</div>
</div>
<div class="time" id="clock"></div>
</div>

<div class="nav">
<button class="active" onclick="showSection('control')">Steuerung</button>
<button onclick="showSection('agent')">Agent</button>
<button onclick="showSection('tools')">Tools</button>
<button onclick="showSection('monitor')">Monitor</button>
<button onclick="showSection('logs')">Logs</button>
<button onclick="showSection('settings')">Settings</button>
</div>

<div class="container">

<!-- STEUERUNG -->
<div class="section active" id="sec-control">
<div class="input-area">
<input type="text" id="cmd" placeholder="Befehl eingeben..." autocomplete="off">
<button class="btn" onclick="sendCmd()">➤</button>
</div>
<div class="response-box" id="response">Bereit.</div>

<div class="grid" style="margin-top:15px">
<div class="card">
<h3>SMART HOME</h3>
<div class="btn-grid">
<button class="btn" onclick="quick('licht an')">💡 Licht An</button>
<button class="btn" onclick="quick('licht aus')">🌙 Licht Aus</button>
<button class="btn" onclick="quick('licht rot')">🔴 Rot</button>
<button class="btn" onclick="quick('licht blau')">🔵 Blau</button>
<button class="btn" onclick="quick('licht lila')">🟣 Lila</button>
<button class="btn" onclick="quick('licht grün')">🟢 Grün</button>
<button class="btn" onclick="quick('gaming licht')">🎮 Gaming</button>
<button class="btn" onclick="quick('chill licht')">😎 Chill</button>
</div>
</div>
<div class="card">
<h3>MEDIA</h3>
<div class="btn-grid">
<button class="btn" onclick="quick('pause')">⏸ Pause</button>
<button class="btn" onclick="quick('play')">▶ Play</button>
<button class="btn" onclick="quick('nächster song')">⏭ Skip</button>
<button class="btn" onclick="quick('lauter')">🔊 Lauter</button>
<button class="btn" onclick="quick('leiser')">🔉 Leiser</button>
<button class="btn" onclick="quick('welcher song läuft')">🎵 Song?</button>
</div>
</div>
<div class="card">
<h3>APPS</h3>
<div class="btn-grid">
<button class="btn" onclick="quick('öffne discord')">Discord</button>
<button class="btn" onclick="quick('öffne spotify')">Spotify</button>
<button class="btn" onclick="quick('öffne chrome')">Chrome</button>
<button class="btn" onclick="quick('öffne steam')">Steam</button>
<button class="btn" onclick="quick('gaming modus')">🎮 Gaming</button>
<button class="btn" onclick="quick('chill modus')">😎 Chill</button>
</div>
</div>
<div class="card">
<h3>SYSTEM</h3>
<div class="btn-grid">
<button class="btn" onclick="quick('wie spät ist es')">🕐 Uhrzeit</button>
<button class="btn" onclick="quick('wetter')">🌤 Wetter</button>
<button class="btn" onclick="quick('system status')">💻 System</button>
<button class="btn" onclick="quick('nachrichten')">📰 News</button>
<button class="btn" onclick="quick('mute')">🔇 Mute</button>
<button class="btn" onclick="quick('unmute')">🔈 Unmute</button>
<button class="btn danger" onclick="quick('pc sperren')">🔒 Sperren</button>
<button class="btn danger" onclick="if(confirm('PC herunterfahren?'))quick('herunterfahren')">⏻ Shutdown</button>
</div>
</div>
</div>
</div>

<!-- AGENT -->
<div class="section" id="sec-agent">
<div class="card full">
<h3>AKTIVER PLAN <span class="badge" id="plan-status">IDLE</span></h3>
<div id="plan-goal" style="color:var(--gold);margin-bottom:10px;font-size:12px">Kein aktiver Plan.</div>
<div id="plan-steps"></div>
</div>
<div class="grid" style="margin-top:12px">
<div class="card">
<h3>STATISTIKEN</h3>
<div class="metric"><span class="label">Verarbeitete Befehle</span><span class="value" id="stat-commands">0</span></div>
<div class="metric"><span class="label">Agent-Pläne</span><span class="value" id="stat-plans">0</span></div>
<div class="metric"><span class="label">Tool-Aufrufe</span><span class="value" id="stat-tools">0</span></div>
<div class="metric"><span class="label">Fehler</span><span class="value" id="stat-errors" style="color:var(--red)">0</span></div>
</div>
<div class="card">
<h3>HINTERGRUND-TASKS</h3>
<div id="bg-tasks" style="font-size:11px;color:var(--text-dim)">Keine aktiven Hintergrund-Tasks.</div>
</div>
</div>
</div>

<!-- TOOLS -->
<div class="section" id="sec-tools">
<div class="card full">
<h3>REGISTRIERTE TOOLS <span class="badge" id="tool-count">0</span></h3>
<div id="tool-list"></div>
</div>
</div>

<!-- MONITOR -->
<div class="section" id="sec-monitor">
<div class="grid">
<div class="card">
<h3>CPU</h3>
<div class="metric"><span class="label">Auslastung</span><span class="value" id="cpu-val">0%</span></div>
<div class="bar-bg"><div class="bar-fill cpu" id="cpu-bar" style="width:0%"></div></div>
</div>
<div class="card">
<h3>RAM</h3>
<div class="metric"><span class="label">Belegt</span><span class="value" id="ram-val">0%</span></div>
<div class="bar-bg"><div class="bar-fill ram" id="ram-bar" style="width:0%"></div></div>
<div class="metric"><span class="label">Frei</span><span class="value" id="ram-free">0 GB</span></div>
</div>
<div class="card">
<h3>FESTPLATTE</h3>
<div class="metric"><span class="label">Belegt</span><span class="value" id="disk-val">0%</span></div>
<div class="bar-bg"><div class="bar-fill disk" id="disk-bar" style="width:0%"></div></div>
<div class="metric"><span class="label">Frei</span><span class="value" id="disk-free">0 GB</span></div>
</div>
<div class="card">
<h3>AKKU</h3>
<div class="metric"><span class="label">Ladung</span><span class="value" id="batt-val">–</span></div>
<div class="metric"><span class="label">Status</span><span class="value" id="batt-status">–</span></div>
</div>
</div>
</div>

<!-- LOGS -->
<div class="section" id="sec-logs">
<div class="card full">
<h3>ACTION LOG <button class="btn" onclick="clearLogs()" style="font-size:10px;padding:3px 8px">Clear</button></h3>
<div class="log-list" id="log-list"></div>
</div>
</div>

<!-- SETTINGS -->
<div class="section" id="sec-settings">
<div class="grid">
<div class="card">
<h3>STIMME</h3>
<div class="setting-row">
<span class="label">Stimme</span>
<select id="voice-select" onchange="changeSetting('voice',this.value)">
<option value="männlich">Conrad (männlich)</option>
<option value="weiblich">Seraphina (weiblich)</option>
<option value="florian">Florian</option>
<option value="killian">Killian</option>
</select>
</div>
<div class="setting-row">
<span class="label">Geschwindigkeit</span>
<select id="speed-select" onchange="changeSetting('speed',this.value)">
<option value="langsam">Langsam</option>
<option value="normal" selected>Normal</option>
<option value="schneller">Schneller</option>
<option value="schnell">Schnell</option>
</select>
</div>
</div>
<div class="card">
<h3>KI-MODELL</h3>
<div class="setting-row">
<span class="label">Provider</span>
<select id="ai-provider" onchange="changeSetting('ai_provider',this.value)">
<option value="groq">Groq (Llama 3.3)</option>
<option value="openai">OpenAI (GPT-4)</option>
<option value="ollama">Ollama (Lokal)</option>
</select>
</div>
<div class="setting-row">
<span class="label">API-Key ändern</span>
<button class="btn" onclick="changeKey()">Ändern</button>
</div>
</div>
<div class="card full">
<h3>ÜBER</h3>
<div class="metric"><span class="label">Version</span><span class="value">2.0</span></div>
<div class="metric"><span class="label">Name</span><span class="value">{{ name }}</span></div>
<div class="metric"><span class="label">Uptime</span><span class="value" id="uptime">0s</span></div>
</div>
</div>
</div>

</div>

<script>
var socket=io();
var startTime=Date.now();
var stats={commands:0,plans:0,tools:0,errors:0};

function showSection(id){
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  document.querySelectorAll('.nav button').forEach(b=>b.classList.remove('active'));
  document.getElementById('sec-'+id).classList.add('active');
  event.target.classList.add('active');
  if(id==='monitor')fetchMonitor();
  if(id==='tools')fetchTools();
  if(id==='logs')fetchLogs();
  if(id==='agent')fetchAgent();
}

function sendCmd(){
  var cmd=document.getElementById('cmd').value.trim();
  if(!cmd)return;
  document.getElementById('cmd').value='';
  execute(cmd);
}

function quick(cmd){execute(cmd)}

function execute(cmd){
  document.getElementById('status').textContent='⏳ VERARBEITE...';
  document.getElementById('status').style.color='#ffaa00';
  stats.commands++;
  document.getElementById('stat-commands').textContent=stats.commands;
  fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:cmd})})
  .then(r=>r.json())
  .then(d=>{
    document.getElementById('response').textContent=d.response||'Erledigt.';
    document.getElementById('status').textContent='● ONLINE';
    document.getElementById('status').style.color='#00ff88';
  })
  .catch(e=>{
    document.getElementById('response').textContent='Fehler: '+e;
    document.getElementById('status').textContent='● OFFLINE';
    document.getElementById('status').style.color='#ff4444';
    stats.errors++;
  });
}

function fetchMonitor(){
  fetch('/api/system').then(r=>r.json()).then(d=>{
    document.getElementById('cpu-val').textContent=d.cpu+'%';
    document.getElementById('cpu-bar').style.width=d.cpu+'%';
    document.getElementById('ram-val').textContent=d.ram_percent+'%';
    document.getElementById('ram-bar').style.width=d.ram_percent+'%';
    document.getElementById('ram-free').textContent=d.ram_free+'GB';
    document.getElementById('disk-val').textContent=d.disk_percent+'%';
    document.getElementById('disk-bar').style.width=d.disk_percent+'%';
    document.getElementById('disk-free').textContent=d.disk_free+'GB';
    if(d.battery){
      document.getElementById('batt-val').textContent=d.battery.percent+'%';
      document.getElementById('batt-status').textContent=d.battery.plugged?'Lädt':'Akku';
    }
  });
}

function fetchTools(){
  fetch('/api/tools').then(r=>r.json()).then(d=>{
    document.getElementById('tool-count').textContent=Object.keys(d).length;
    var html='';
    for(var name in d){
      var t=d[name];
      html+='<div class="tool-item"><div><span class="tool-name">'+name+'</span><br><span class="tool-desc">'+t.description+'</span></div>'+(t.dangerous?'<span style="color:var(--red);font-size:9px">⚠ DANGEROUS</span>':'')+'</div>';
    }
    document.getElementById('tool-list').innerHTML=html;
  });
}

function fetchLogs(){
  fetch('/api/logs').then(r=>r.json()).then(d=>{
    var html='';
    d.reverse().forEach(l=>{
      html+='<div class="log-item"><span class="time">'+l.time.split(' ')[1]+'</span><span class="type '+l.type+'">'+l.type+'</span><span>'+l.action.substring(0,80)+'</span></div>';
    });
    document.getElementById('log-list').innerHTML=html||'<div style="color:var(--text-dim);padding:10px">Keine Logs.</div>';
  });
}

function fetchAgent(){
  fetch('/api/agent').then(r=>r.json()).then(d=>{
    if(d.active_plan){
      document.getElementById('plan-status').textContent=d.active_plan.status.toUpperCase();
      document.getElementById('plan-goal').textContent=d.active_plan.goal;
      var html='';
      d.active_plan.steps.forEach(s=>{
        var sc=s.status==='completed'?'completed':s.status==='running'?'running':s.status==='failed'?'failed':'pending';
        html+='<div class="task-item"><span class="task-status '+sc+'"></span>'+s.description+' <span style="color:var(--text-dim)">['+s.tool+']</span></div>';
      });
      document.getElementById('plan-steps').innerHTML=html;
    }
    stats.plans=d.completed||0;
    document.getElementById('stat-plans').textContent=stats.plans;
  });
}

function clearLogs(){fetch('/api/logs/clear',{method:'POST'}).then(()=>fetchLogs())}

function changeSetting(key,val){
  fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:key,value:val})})
  .then(r=>r.json()).then(d=>{document.getElementById('response').textContent=d.response||'OK';});
}

function changeKey(){
  var key=prompt('Neuen API-Key eingeben:');
  if(key)changeSetting('api_key',key);
}

// Clock
setInterval(()=>{
  var now=new Date();
  document.getElementById('clock').textContent=now.toLocaleTimeString('de-DE');
  var up=Math.floor((Date.now()-startTime)/1000);
  var h=Math.floor(up/3600),m=Math.floor(up%3600/60),s=up%60;
  document.getElementById('uptime').textContent=(h?h+'h ':'')+(m?m+'m ':'')+s+'s';
},1000);

// Auto-refresh monitor
setInterval(()=>{if(document.getElementById('sec-monitor').classList.contains('active'))fetchMonitor()},3000);

// WebSocket
socket.on('update',function(data){
  if(data.type==='log')fetchLogs();
  if(data.type==='task')fetchAgent();
  if(data.type==='response'){
    document.getElementById('response').textContent=data.text;
    document.getElementById('status').textContent='● ONLINE';
    document.getElementById('status').style.color='#00ff88';
  }
});

document.getElementById('cmd').addEventListener('keypress',function(e){if(e.key==='Enter')sendCmd()});
</script>
</body>
</html>
"""


class DashboardServer:
    def __init__(self, brain, voice, port=5050):
        self.brain = brain
        self.voice = voice
        self.port = port
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'computer-agent-secret'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='threading')
        self.ip = self._get_ip()
        self.start_time = time.time()

        # Routes
        self.app.route("/")(self._dashboard)
        self.app.route("/api/command", methods=["POST"])(self._command)
        self.app.route("/api/system")(self._system)
        self.app.route("/api/tools")(self._tools)
        self.app.route("/api/logs")(self._logs)
        self.app.route("/api/logs/clear", methods=["POST"])(self._clear_logs)
        self.app.route("/api/agent")(self._agent)
        self.app.route("/api/settings", methods=["POST"])(self._settings)
        self.app.route("/api/status")(self._status)

    def _get_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]; s.close(); return ip
        except: return "127.0.0.1"

    def _dashboard(self):
        return render_template_string(DASHBOARD_HTML, name=self.brain.name)

    def _command(self):
        data = request.get_json()
        cmd = data.get("command", "")
        if not cmd: return jsonify({"response": "Kein Befehl."})
        answer = self.brain.process(cmd)
        if answer:
            threading.Thread(target=self.voice.speak, args=(answer,), daemon=True).start()
        self.socketio.emit('update', {'type': 'log'})
        return jsonify({"response": answer or "Erledigt."})

    def _system(self):
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\')
        battery = psutil.sensors_battery()
        result = {
            "cpu": cpu,
            "ram_percent": ram.percent,
            "ram_free": round(ram.available / 1024**3, 1),
            "disk_percent": disk.percent,
            "disk_free": round(disk.free / 1024**3, 1),
        }
        if battery:
            result["battery"] = {"percent": battery.percent, "plugged": battery.power_plugged}
        return jsonify(result)

    def _tools(self):
        if hasattr(self.brain, 'agent'):
            return jsonify(self.brain.agent.tools.get_available_tools())
        return jsonify({})

    def _logs(self):
        if hasattr(self.brain, 'agent'):
            return jsonify(self.brain.agent.security.get_log())
        return jsonify([])

    def _clear_logs(self):
        if hasattr(self.brain, 'agent'):
            self.brain.agent.security.action_log = []
        return jsonify({"ok": True})

    def _agent(self):
        if hasattr(self.brain, 'agent'):
            return jsonify(self.brain.agent.planner.get_status())
        return jsonify({})

    def _settings(self):
        data = request.get_json()
        key = data.get("key", "")
        value = data.get("value", "")

        if key == "voice" and self.voice:
            result = self.voice.set_voice(value)
            return jsonify({"response": result})

        if key == "speed" and self.voice:
            result = self.voice.set_speed(value)
            return jsonify({"response": result or "OK"})

        if key == "api_key":
            from config_manager import load_config, save_config
            config = load_config()
            config["groq_api_key"] = value
            save_config(config)
            return jsonify({"response": "API-Key aktualisiert. Neustart nötig."})

        if key == "ai_provider":
            from config_manager import load_config, save_config
            config = load_config()
            config["ai_provider"] = value
            save_config(config)
            return jsonify({"response": f"KI-Provider auf {value} geändert. Neustart nötig."})

        return jsonify({"response": "Unbekannte Einstellung."})

    def _status(self):
        return jsonify({
            "online": True,
            "name": self.brain.name,
            "muted": self.brain.muted,
            "uptime": int(time.time() - self.start_time),
        })

    def start(self):
        print(f"\n  🌐 Dashboard: http://{self.ip}:{self.port}")
        print(f"  📱 Handy:     http://{self.ip}:{self.port}")
        print(f"  💻 Lokal:     http://localhost:{self.port}\n")

        thread = threading.Thread(
            target=lambda: self.socketio.run(self.app, host="0.0.0.0", port=self.port,
                                              debug=False, use_reloader=False, allow_unsafe_werkzeug=True),
            daemon=True
        )
        thread.start()
        return self.ip