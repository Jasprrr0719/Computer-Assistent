"""
Tool Registry – Registriert und verwaltet alle verfügbaren Tools.
JSON-basiert, dynamisch erweiterbar.
"""

import json
import os
import sys
import webbrowser
import subprocess
import time
import getpass
import requests
import datetime


USER = getpass.getuser()


class ToolRegistry:
    def __init__(self):
        self.tools = {}
        self._register_builtin_tools()

    def register(self, name, func, description="", args_schema=None, dangerous=False):
        """Registriert ein neues Tool."""
        self.tools[name] = {
            "func": func,
            "description": description,
            "args_schema": args_schema or {},
            "dangerous": dangerous,
        }

    def execute(self, tool_name, args=None):
        """Führt ein Tool aus."""
        args = args or {}
        tool = self.tools.get(tool_name)
        if not tool:
            return f"Tool '{tool_name}' nicht gefunden."
        try:
            return tool["func"](**args)
        except Exception as e:
            return f"Tool-Fehler ({tool_name}): {e}"

    def get_available_tools(self):
        """Gibt alle Tools mit Beschreibung zurück (ohne Funktionsreferenz)."""
        return {
            name: {
                "description": info["description"],
                "args": info["args_schema"],
                "dangerous": info["dangerous"],
            }
            for name, info in self.tools.items()
        }

    def _register_builtin_tools(self):
        """Registriert alle eingebauten Tools."""

        # === APP MANAGEMENT ===
        self.register("open_app", self._open_app,
            description="Öffnet eine Anwendung",
            args_schema={"app": "Name der App"})

        self.register("close_app", self._close_app,
            description="Schließt eine Anwendung",
            args_schema={"app": "Name der App"},
            dangerous=True)

        self.register("open_url", self._open_url,
            description="Öffnet eine URL im Browser",
            args_schema={"url": "Die URL"})

        # === TERMINAL ===
        self.register("run_command", self._run_command,
            description="Führt einen Terminal-Befehl aus",
            args_schema={"command": "Der Befehl"},
            dangerous=True)

        # === DATEIEN ===
        self.register("read_file", self._read_file,
            description="Liest eine Textdatei",
            args_schema={"path": "Dateipfad"})

        self.register("write_file", self._write_file,
            description="Schreibt in eine Datei",
            args_schema={"path": "Dateipfad", "content": "Inhalt"},
            dangerous=True)

        self.register("list_files", self._list_files,
            description="Listet Dateien in einem Ordner",
            args_schema={"path": "Ordnerpfad"})

        self.register("find_file", self._find_file,
            description="Sucht nach Dateien",
            args_schema={"query": "Suchbegriff"})

        # === WEB ===
        self.register("web_search", self._web_search,
            description="Sucht etwas bei Google",
            args_schema={"query": "Suchbegriff"})

        self.register("fetch_url", self._fetch_url,
            description="Lädt den Inhalt einer Webseite",
            args_schema={"url": "Die URL"})

        # === SYSTEM ===
        self.register("system_info", self._system_info,
            description="Zeigt System-Informationen")

        self.register("screenshot", self._screenshot,
            description="Macht einen Screenshot")

        self.register("lock_pc", self._lock_pc,
            description="Sperrt den PC",
            dangerous=True)

        self.register("shutdown", self._shutdown,
            description="Fährt den PC herunter",
            dangerous=True)

        # === CLIPBOARD ===
        self.register("get_clipboard", self._get_clipboard,
            description="Liest die Zwischenablage")

        self.register("set_clipboard", self._set_clipboard,
            description="Schreibt in die Zwischenablage",
            args_schema={"text": "Der Text"})

        # === ZEIT ===
        self.register("get_time", self._get_time,
            description="Gibt die aktuelle Uhrzeit")

        self.register("get_date", self._get_date,
            description="Gibt das aktuelle Datum")

        # === WETTER ===
        self.register("get_weather", self._get_weather,
            description="Holt das aktuelle Wetter",
            args_schema={"city": "Stadtname"})

        # === MEDIA ===
        self.register("media_play_pause", self._media_play_pause,
            description="Play/Pause für Medien")

        self.register("media_next", self._media_next,
            description="Nächster Song")

        self.register("media_prev", self._media_prev,
            description="Vorheriger Song")

    # === IMPLEMENTIERUNGEN ===

    def _open_app(self, app=""):
        APPS = {
            "discord": "auto_discord",
            "spotify": rf"C:\Users\{USER}\AppData\Roaming\Spotify\Spotify.exe",
            "steam": r"C:\Program Files (x86)\Steam\steam.exe",
            "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
            "edge": "msedge", "notepad": "notepad", "rechner": "calc",
            "explorer": "explorer", "terminal": "wt", "cmd": "cmd",
            "obs": r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\OBS Studio\OBS Studio (64bit).lnk",
            "vscode": "code", "vs code": "code",
            "chatterino": r"C:\Program Files\Chatterino\chatterino.exe",
            "valorant": rf"C:\Riot Games\Riot Client\RiotClientServices.exe --launch-product=valorant --launch-patchline=live",
            "fortnite": "com.epicgames.launcher://apps/fn",
        }
        cmd = APPS.get(app.lower(), app)

        # Discord Auto-Detect
        if cmd == "auto_discord":
            discord_base = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Discord")
            if os.path.exists(discord_base):
                app_dirs = sorted([d for d in os.listdir(discord_base) if d.startswith("app-")], reverse=True)
                if app_dirs:
                    exe = os.path.join(discord_base, app_dirs[0], "Discord.exe")
                    if os.path.exists(exe):
                        subprocess.Popen(exe)
                        return f"Discord geöffnet."
            subprocess.Popen("start discord", shell=True)
            return "Discord geöffnet."

        if cmd.startswith("steam://") or cmd.startswith("com.epicgames"):
            webbrowser.open(cmd)
        elif cmd.endswith(".lnk"):
            os.startfile(cmd)
        elif os.path.exists(cmd.split(" --")[0].split(" -")[0].strip('"')):
            subprocess.Popen(cmd, shell=True)
        else:
            subprocess.Popen(f'start "" "{cmd}"', shell=True)
        return f"{app} geöffnet."

    def _close_app(self, app=""):
        process_map = {
            "discord": "Discord.exe", "chrome": "chrome.exe", "firefox": "firefox.exe",
            "spotify": "Spotify.exe", "steam": "steam.exe", "obs": "obs64.exe",
            "vscode": "Code.exe", "notepad": "notepad.exe", "edge": "msedge.exe",
        }
        proc = process_map.get(app.lower(), f"{app}.exe")
        os.system(f"taskkill /f /im {proc} >nul 2>&1")
        return f"{app} geschlossen."

    def _open_url(self, url=""):
        if not url.startswith("http"): url = f"https://{url}"
        webbrowser.open(url)
        return f"URL geöffnet: {url}"

    def _run_command(self, command=""):
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout or result.stderr or "Kein Output."
            return output[:2000]
        except subprocess.TimeoutExpired:
            return "Befehl hat zu lange gedauert."
        except Exception as e:
            return f"Fehler: {e}"

    def _read_file(self, path=""):
        try:
            with open(path, "r", encoding="utf-8") as f: return f.read()[:5000]
        except Exception as e: return f"Fehler: {e}"

    def _write_file(self, path="", content=""):
        try:
            with open(path, "w", encoding="utf-8") as f: f.write(content)
            return f"Datei geschrieben: {path}"
        except Exception as e: return f"Fehler: {e}"

    def _list_files(self, path=""):
        try:
            files = os.listdir(path)
            return "\n".join(files[:50])
        except Exception as e: return f"Fehler: {e}"

    def _find_file(self, query=""):
        found = []
        for d in [os.path.expanduser(f"~\\{f}") for f in ["Desktop", "Documents", "Downloads"]]:
            if not os.path.exists(d): continue
            for root, dirs, files in os.walk(d):
                for f in files:
                    if query.lower() in f.lower(): found.append(os.path.join(root, f))
                if len(found) >= 10: break
        if found:
            subprocess.Popen(f'explorer /select,"{found[0]}"')
        return "\n".join(found[:10]) if found else "Keine Dateien gefunden."

    def _web_search(self, query=""):
        webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        return f"Suche geöffnet: {query}"

    def _fetch_url(self, url=""):
        try:
            from bs4 import BeautifulSoup
            r = requests.get(url, timeout=10, headers={"User-Agent": "ComputerAgent/1.0"})
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]): tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            return text[:3000]
        except Exception as e: return f"Fehler: {e}"

    def _system_info(self):
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\')
        battery = psutil.sensors_battery()
        result = f"CPU: {cpu}%, RAM: {ram.percent}% ({round(ram.available/1024**3,1)}GB frei), "
        result += f"Disk: {disk.percent}% ({round(disk.free/1024**3,1)}GB frei)"
        if battery: result += f", Akku: {battery.percent}%"
        return result

    def _screenshot(self):
        try:
            import ctypes
            ctypes.windll.user32.keybd_event(0x2C, 0, 0, 0)  # PrintScreen
            time.sleep(0.5)
            ctypes.windll.user32.keybd_event(0x2C, 0, 0x0002, 0)
            return "Screenshot in Zwischenablage."
        except: return "Screenshot fehlgeschlagen."

    def _lock_pc(self):
        import ctypes; ctypes.windll.user32.LockWorkStation()
        return "PC gesperrt."

    def _shutdown(self):
        os.system("shutdown /s /t 10")
        return "PC fährt in 10 Sekunden herunter."

    def _get_clipboard(self):
        try:
            import ctypes
            ctypes.windll.user32.OpenClipboard(0)
            try:
                data = ctypes.windll.user32.GetClipboardData(13)  # CF_UNICODETEXT
                text = ctypes.wstring_at(data) if data else ""
                return text[:1000] if text else "Zwischenablage ist leer."
            finally:
                ctypes.windll.user32.CloseClipboard()
        except: return "Zwischenablage konnte nicht gelesen werden."

    def _set_clipboard(self, text=""):
        try:
            subprocess.run(['clip'], input=text.encode('utf-8'), check=True)
            return "In Zwischenablage kopiert."
        except: return "Fehler beim Kopieren."

    def _get_time(self):
        return datetime.datetime.now().strftime("%H:%M")

    def _get_date(self):
        now = datetime.datetime.now()
        tage = ["Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"]
        return f"{tage[now.weekday()]}, {now.strftime('%d.%m.%Y')}"

    def _get_weather(self, city="Berlin"):
        WMO = {0:"klar",1:"klar",2:"bewölkt",3:"bewölkt",61:"Regen",63:"Regen",71:"Schnee",95:"Gewitter"}
        try:
            geo = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=de", timeout=5).json()
            if "results" not in geo: return f"{city} nicht gefunden."
            r = geo["results"][0]
            w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={r['latitude']}&longitude={r['longitude']}&current=temperature_2m,weather_code,wind_speed_10m&timezone=auto", timeout=5).json()["current"]
            return f"{r.get('name',city)}: {WMO.get(w['weather_code'],'?')}, {round(w['temperature_2m'])}°C, Wind {round(w['wind_speed_10m'])} km/h"
        except Exception as e: return f"Wetter-Fehler: {e}"

    def _media_play_pause(self):
        import ctypes; ctypes.windll.user32.keybd_event(0xB3, 0, 1, 0); ctypes.windll.user32.keybd_event(0xB3, 0, 3, 0)
        return "Play/Pause."

    def _media_next(self):
        import ctypes; ctypes.windll.user32.keybd_event(0xB0, 0, 1, 0); ctypes.windll.user32.keybd_event(0xB0, 0, 3, 0)
        return "Nächster Song."

    def _media_prev(self):
        import ctypes; ctypes.windll.user32.keybd_event(0xB1, 0, 1, 0); ctypes.windll.user32.keybd_event(0xB1, 0, 3, 0)
        return "Vorheriger Song."