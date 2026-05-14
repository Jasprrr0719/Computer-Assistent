"""
Gehirn – ALLE Features.
"""

import datetime
import re
import os
import sys
import webbrowser
import subprocess
import threading
import time
import math
import json
import getpass
import random
import string
import requests
import feedparser
import psutil
from tools.browser import BrowserTool
from tools.webhooks import WebhookSystem
from tools.whatsapp import WhatsAppTool
from tools.email_tool import EmailTool
from tools.discord_bot import DiscordTool
from agent.executor import AgentExecutor
from groq import Groq

from memory import Memory, Notes, Todos
from smarthome import SmartHome
from config_manager import APP_DIR, load_config, save_config

SPEECH_CORRECTIONS = {
    "valerian": "valorant", "walorant": "valorant", "walloran": "valorant",
    "fortneid": "fortnite", "fort night": "fortnite", "fortnacht": "fortnite",
    "chattarino": "chatterino", "tschatterino": "chatterino",
    "ob es": "obs", "opps": "obs", "ops": "obs",
    "lohle": "lol", "league off legends": "league of legends",
    "disco": "discord", "diskord": "discord", "dis court": "discord",
    "spotifei": "spotify", "spot i fei": "spotify",
    "goovy": "govee", "govi": "govee",
}

def correct_speech(text):
    for wrong, right in SPEECH_CORRECTIONS.items():
        text = text.replace(wrong, right)
    return text

WMO_CODES = {
    0: "klarer Himmel", 1: "überwiegend klar", 2: "teilweise bewölkt", 3: "bewölkt",
    45: "Nebel", 48: "Reifnebel", 51: "leichter Nieselregen", 53: "Nieselregen",
    61: "leichter Regen", 63: "Regen", 65: "starker Regen",
    71: "leichter Schneefall", 73: "Schneefall", 75: "starker Schneefall",
    80: "leichte Regenschauer", 81: "Regenschauer", 95: "Gewitter",
}

USER = getpass.getuser()

KNOWN_APPS = {
    "discord": "auto_discord",
    "spotify": rf"C:\Users\{USER}\AppData\Roaming\Spotify\Spotify.exe",
    "steam": r"C:\Program Files (x86)\Steam\steam.exe",
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "edge": "msedge", "notepad": "notepad", "rechner": "calc",
    "taschenrechner": "calc", "explorer": "explorer", "terminal": "wt",
    "cmd": "cmd", "word": "winword", "excel": "excel", "powerpoint": "powerpnt",
    "teams": "ms-teams", "outlook": "outlook", "paint": "mspaint",
    "vlc": r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    "obs": r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\OBS Studio\OBS Studio (64bit).lnk",
    "obs studio": r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\OBS Studio\OBS Studio (64bit).lnk",
    "vscode": "code", "vs code": "code", "visual studio code": "code",
    "telegram": rf"C:\Users\{USER}\AppData\Roaming\Telegram Desktop\Telegram.exe",
    "whatsapp": "whatsapp",
    "chatterino": r"C:\Program Files\Chatterino\chatterino.exe",
    "valorant": rf"C:\Riot Games\Riot Client\RiotClientServices.exe --launch-product=valorant --launch-patchline=live",
    "fortnite": "com.epicgames.launcher://apps/fn",
    "league of legends": rf"C:\Riot Games\Riot Client\RiotClientServices.exe --launch-product=league_of_legends --launch-patchline=live",
    "lol": rf"C:\Riot Games\Riot Client\RiotClientServices.exe --launch-product=league_of_legends --launch-patchline=live",
    "apex": "steam://rungameid/1172470", "cs2": "steam://rungameid/730",
    "gta": "steam://rungameid/271590", "rocket league": "steam://rungameid/252950",
    "minecraft": "minecraft",
}

KNOWN_URLS = {
    "amar": "https://www.twitch.tv/amar", "montanablack": "https://www.twitch.tv/montanablack88",
    "trymacs": "https://www.twitch.tv/trymacs", "elotrix": "https://www.twitch.tv/elotrix",
    "gronkh": "https://www.twitch.tv/gronkh", "papaplatte": "https://www.twitch.tv/papaplatte",
    "knossi": "https://www.twitch.tv/therealknossi", "reved": "https://www.twitch.tv/reved",
    "youtube": "https://www.youtube.com", "twitch": "https://www.twitch.tv",
    "twitter": "https://www.twitter.com", "instagram": "https://www.instagram.com",
    "tiktok": "https://www.tiktok.com", "reddit": "https://www.reddit.com",
    "google": "https://www.google.com", "chatgpt": "https://chat.openai.com",
    "netflix": "https://www.netflix.com", "amazon": "https://www.amazon.de",
    "disney plus": "https://www.disneyplus.com", "prime video": "https://www.primevideo.com",
}

STREAMING_PROFILES = {
    "default": {"apps": ["obs", "chatterino"], "message": "Streaming-Setup hochgefahren."},
    "fortnite": {"apps": ["obs", "chatterino", "fortnite"], "message": "Fortnite Stream startet."},
    "valorant": {"apps": ["obs", "chatterino", "valorant"], "message": "Valorant Stream startet."},
    "cs2": {"apps": ["obs", "chatterino", "cs2"], "message": "CS2 Stream startet."},
    "minecraft": {"apps": ["obs", "chatterino", "minecraft"], "message": "Minecraft Stream startet."},
    "just chatting": {"apps": ["obs", "chatterino"], "message": "Just Chatting bereit."},
}

MULTI_MODES = {
    "gaming modus": {"apps": ["discord", "steam", "spotify"], "message": "Gaming-Modus."},
    "gaming": {"apps": ["discord", "steam", "spotify"], "message": "Gaming-Modus."},
    "arbeitsmodus": {"apps": ["chrome", "spotify", "outlook"], "message": "Arbeitsmodus."},
    "chill modus": {"apps": ["spotify", "discord"], "urls": ["https://www.youtube.com"], "message": "Chill-Modus."},
    "chillmodus": {"apps": ["spotify", "discord"], "urls": ["https://www.youtube.com"], "message": "Chill-Modus."},
}

NEWS_FEEDS = {
    "allgemein": "https://www.tagesschau.de/xml/rss2/",
    "tech": "https://www.heise.de/rss/heise-atom.xml",
    "gaming": "https://www.gamestar.de/rss/gamestar.rss",
}

MOTIVATIONS = [
    "Boss, du schaffst das. Kein Zweifel.",
    "Boss, Erfolg ist kein Zufall. Du arbeitest härter als die meisten.",
    "Boss, jeder Profi war mal ein Anfänger. Bleib dran.",
    "Boss, die einzige Grenze bist du selbst.",
    "Boss, heute ist dein Tag. Mach was draus.",
    "Boss, du bist nicht hier um durchschnittlich zu sein.",
    "Boss, Disziplin schlägt Motivation. Und du hast beides.",
    "Boss, Diamanten entstehen unter Druck.",
    "Boss, Legenden werden nicht geboren. Sie werden gebaut.",
]

KOMPLIMENTE = [
    "Boss, du siehst heute besonders gut aus.",
    "Boss, dein Geschmack ist exzellent.",
    "Boss, wenn Intelligenz strahlen würde, wärst du eine Supernova.",
    "Boss, die Welt hat Glück, dass es dich gibt.",
    "Boss, Tony Stark wäre stolz auf dich.",
]

BIRTHDAY_FILE = os.path.join(APP_DIR, "birthdays.json")
WATCHLIST_FILE = os.path.join(APP_DIR, "watchlist.json")


class Brain:
    def __init__(self, config):
        # Integrations
        self.whatsapp = WhatsAppTool()
        self.email = EmailTool(config)
        self.discord_tool = DiscordTool(config)
        self.discord_tool.start_bot()
        self.name = config.get("assistant_name", "Computer")
        self.client = Groq(api_key=config["groq_api_key"])
        self.memory = Memory()
        self.notes = Notes()
        self.todos = Todos()
        self.smarthome = SmartHome()
        self.voice_ref = None  # Wird von main.py gesetzt
        self.chat_history = []
        self.max_history = 20
        self.config = config
        self.custom_commands = config.get("custom_commands", {})
        self._timer_callback = None
        self._reminder_callback = None
        self.muted = False
        self.browser = BrowserTool()
        self.webhooks = WebhookSystem()
        # Agent-System
        self.agent = AgentExecutor(self.client)
        self.is_recording = False
        self._check_birthdays_today()
        self._start_watchlist_checker()

    def set_voice(self, voice):
        self.voice_ref = voice

    def _check_birthdays_today(self):
        self._birthday_message = None
        if os.path.exists(BIRTHDAY_FILE):
            with open(BIRTHDAY_FILE, "r", encoding="utf-8") as f:
                birthdays = json.load(f)
            today = datetime.datetime.now().strftime("%d.%m")
            msgs = [n for n, d in birthdays.items() if d.startswith(today)]
            if msgs:
                self._birthday_message = f"Boss, nicht vergessen: {', '.join(msgs)} hat heute Geburtstag!"

    def get_birthday_message(self):
        msg = self._birthday_message; self._birthday_message = None; return msg

    def _start_watchlist_checker(self):
        def check_loop():
            while True:
                time.sleep(300)  # Alle 5 Minuten prüfen
                self._check_watchlist()
        threading.Thread(target=check_loop, daemon=True).start()

    def _check_watchlist(self):
        if not os.path.exists(WATCHLIST_FILE):
            return
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            watchlist = json.load(f)
        to_remove = []
        for item in watchlist:
            try:
                if item["type"] == "crypto":
                    r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={item['asset']}&vs_currencies=usd", timeout=5)
                    price = r.json()[item["asset"]]["usd"]
                    if item["direction"] == "above" and price >= item["target"]:
                        if self.voice_ref:
                            self.voice_ref.play_sound("notify")
                            self.voice_ref.speak(f"Boss, Alarm! {item['asset'].title()} ist über {item['target']} Dollar. Aktuell: {price} Dollar.")
                        to_remove.append(item)
                    elif item["direction"] == "below" and price <= item["target"]:
                        if self.voice_ref:
                            self.voice_ref.play_sound("notify")
                            self.voice_ref.speak(f"Boss, Alarm! {item['asset'].title()} ist unter {item['target']} Dollar. Aktuell: {price} Dollar.")
                        to_remove.append(item)
            except:
                pass
        if to_remove:
            for item in to_remove:
                watchlist.remove(item)
            with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(watchlist, f, indent=4)

    def process(self, user_input):
        text = correct_speech(user_input.lower().strip())
        if self.muted and "unmute" not in text and "mikrofon an" not in text:
            return None
        mem = self.memory.check_and_store(text)
        if mem:
            return f"Selbstverständlich. {mem}"
            # WhatsApp
        if any(w in text for w in ["whatsapp", "kontakt speichern", "kontakte zeigen"]):
            result = self.whatsapp.handle(text)
            if result: return result

        # Email
        if any(w in text for w in ["email", "mail", "posteingang", "inbox"]):
            result = self.email.handle(text)
            if result == "EMAIL_AI_GENERATE":
                return None  # KI übernimmt
            if result: return result

        # Discord Bot
        if "discord" in text and any(w in text for w in ["nachricht", "message", "nachrichten", "schreib"]):
            result = self.discord_tool.handle(text)
            if result: return result
            # Browser-Automatisierung
        if any(w in text for w in ["folge", "follow", "geh auf", "navigiere",
                                    "browser öffne", "klick", "klicke",
                                    "tippe", "lies die seite", "seite vorlesen",
                                    "scroll", "browser schließen", "browser screenshot"]):
            result = self.browser.handle(text)
            if result: return result

        # Webhooks
        if "webhook" in text:
            result = self.webhooks.handle(text)
            if result: return result
        local = self._handle_local(text)
        if local is not None:
            self._add_history("user", user_input)
            self._add_history("assistant", local)
            return local
        # Agent versucht autonom zu lösen
        agent_result = self.agent.process_autonomous(user_input)
        if agent_result:
            return agent_result

        # Fallback: KI-Antwort
        answer = self._ask_ai(user_input)
        urls_found = re.findall(r'https?://[^\s\)\]\,\"\']+', answer)
        for url in urls_found:
            webbrowser.open(url)
        self._add_history("user", user_input)
        self._add_history("assistant", answer)
        return answer

    def _handle_local(self, text):
        # Kontext / Verlauf
        if any(w in text for w in ["was hab ich gefragt", "was habe ich gefragt", "letzte frage",
                                    "wiederhole", "verlauf", "gesprächsverlauf", "zusammenfassung"]):
            return self._get_context(text)

        # Multi-Monitor
        if any(w in text for w in ["verschiebe", "schieb", "anderen bildschirm", "zweiten bildschirm",
                                    "zweiten monitor", "anderen monitor"]):
            result = self._move_window(text)
            if result: return result

        # Habit-Tracker
        if any(w in text for w in ["habit", "habits", "gewohnheit", "gewohnheiten"]):
            result = self._habit_tracker(text)
            if result: return result
        # Habit erledigt (ohne "habit" im Text)
        try:
            habit_file = os.path.join(APP_DIR, "habits.json")
            if os.path.exists(habit_file):
                with open(habit_file, "r", encoding="utf-8") as f:
                    habit_data = json.load(f)
                for habit_key in habit_data.get("habits", {}).keys():
                    if habit_key in text and any(w in text for w in ["erledigt", "gemacht", "geschafft", "done"]):
                        result = self._habit_tracker(text)
                        if result: return result
        except:
            pass
        
        # Tagebuch
        if any(w in text for w in ["tagebuch", "diary", "journal"]):
            result = self._diary(text)
            if result: return result

        # Mute
        if "unmute" in text or "mikrofon an" in text:
            self.muted = False; return "Ich höre wieder zu."
        if "mute" in text or "mikrofon aus" in text or "sei still" in text:
            self.muted = True; return "Stumm. F6 oder 'unmute' zum Reaktivieren."

        # Stimme wechseln
        if any(w in text for w in ["stimme wechsel", "wechsel stimme", "weibliche stimme",
                                    "männliche stimme", "andere stimme"]):
            return self._change_voice(text)

        # Geschwindigkeit
        if any(w in text for w in ["rede schneller", "rede langsamer", "sprich schneller",
                                    "sprich langsamer", "normal speed", "normale geschwindigkeit"]):
            return self._change_speed(text)

        # System Monitor
        if any(w in text for w in ["system status", "cpu", "ram", "arbeitsspeicher",
                                    "speicherplatz", "system info", "pc status"]):
            return self._system_monitor(text)

        # Watchlist
        if any(w in text for w in ["watchlist", "alarm", "benachrichtige", "sag mir wenn",
                                    "bitcoin", "ethereum", "krypto preis"]):
            return self._watchlist(text)

        # PC sperren
        if any(w in text for w in ["pc sperren", "computer sperren", "bildschirm sperren"]):
            return self._lock_pc()

        # Bildschirmaufnahme
        if any(w in text for w in ["aufnahme starten", "bildschirm aufnehmen", "recording starten"]):
            return self._start_recording()
        if any(w in text for w in ["aufnahme stoppen", "aufnahme beenden", "recording stoppen"]):
            return self._stop_recording()

        # Datei suchen
        if any(w in text for w in ["finde datei", "suche datei", "wo ist", "finde meine"]):
            return self._find_file(text)

        # Email schreiben
        if any(w in text for w in ["schreib eine email", "email schreiben", "mail schreiben",
                                    "schreib eine mail", "email an"]):
            return self._write_email(text)

        # Code schreiben
        if any(w in text for w in ["schreib code", "schreib ein script", "schreib ein programm",
                                    "code schreiben", "programmiere"]):
            return self._write_code(text)

        # Nachrichten
        if any(w in text for w in ["nachrichten", "news", "was gibt es neues", "schlagzeilen"]):
            return self._news(text)

        # Spotify
        if any(w in text for w in ["welcher song", "welches lied", "was läuft", "aktueller song"]):
            return self._current_song()
        if any(w in text for w in ["playlist", "spiel meine", "spiele meine"]):
            return self._spotify_playlist(text)

        # Spaß
        if any(w in text for w in ["witz", "witze", "was lustiges", "zum lachen"]):
            return self._joke()
        if any(w in text for w in ["würfel", "wirf einen würfel", "zufallszahl"]):
            return self._dice(text)
        if any(w in text for w in ["motivation", "motivier mich", "push me"]):
            return random.choice(MOTIVATIONS)
        if any(w in text for w in ["kompliment", "sag mir was nettes"]):
            return random.choice(KOMPLIMENTE)

        # Tools
        if any(w in text for w in ["passwort", "password"]):
            return self._password(text)
        if any(w in text for w in ["qr code", "qr-code", "qrcode"]):
            return self._qr_code(text)
        if any(w in text for w in ["meilen", "kilometer", "fahrenheit", "celsius", "pfund",
                                    "zoll", "zentimeter", "fuß", "unzen", "umrechnen"]):
            r = self._convert_units(text)
            if r: return r
        if any(w in text for w in ["dollar", "euro", "yen", "franken", "währung", "bitcoin kurs"]):
            r = self._convert_currency(text)
            if r: return r
        if "geburtstag" in text:
            return self._birthday(text)

        # Custom Commands
        r = self._custom_command(text)
        if r: return r
        r = self._streaming(text)
        if r: return r
        r = self._multi_mode(text)
        if r: return r

        if any(w in text for w in ["stream beenden", "stream stoppen", "obs stoppen"]):
            return self._stop_stream()

        r = self._translate(text)
        if r: return r
        r = self._wikipedia(text)
        if r: return r

        if any(w in text for w in ["wie spät", "uhrzeit", "wieviel uhr"]):
            return f"Es ist {datetime.datetime.now().strftime('%H:%M')} Uhr."
        if any(w in text for w in ["welcher tag", "welches datum", "datum heute"]):
            now = datetime.datetime.now()
            tage = ["Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"]
            return f"Heute ist {tage[now.weekday()]}, der {now.strftime('%d.%m.%Y')}."

        if "wetter" in text: return self._weather(text)
        if "timer" in text: return self._timer(text)
        if "erinner" in text: return self._reminder(text)

        sh_result, sh_handled = self.smarthome.handle(text)
        if sh_handled: return sh_result
        if any(w in text for w in ["geräte status", "smart home status"]): return self.smarthome.get_states()

        if any(w in text for w in ["merke", "merk", "notiz", "notiere", "schreib auf", "notizen"]):
            return self._notes(text)
        if any(w in text for w in ["todo", "to do", "aufgabe", "auf die liste", "ich muss"]):
            return self._todos(text)
        if any(w in text for w in ["pause", "play", "abspielen", "skip", "nächster song",
                                    "nächstes lied", "überspringen", "vorheriger song",
                                    "weiter song", "song zurück", "musik"]):
            r = self._music(text)
            if r: return r
        if any(w in text for w in ["lauter", "leiser", "stumm", "lautstärke", "volume"]):
            r = self._volume(text)
            if r: return r
        if any(w in text for w in ["was ist", "berechne", "rechne", "wie viel ist"]):
            r = self._math(text)
            if r: return r
        if any(w in text for w in ["herunterfahren", "shutdown", "neustart", "restart", "pc aus", "abbrechen"]):
            return self._pc(text)
        if "neuer befehl" in text or "neues kommando" in text:
            return self._create_custom_command(text)
        if any(w in text for w in ["meine befehle", "alle befehle"]):
            return self._list_custom_commands()
        if text.startswith("öffne") or text.startswith("starte") or text.startswith("mach"):
            r = self._open(text)
            if r: return r

        search_match = re.search(r"(?:such|google|suche)\s*(?:nach|mal|mir)?\s+(.+)", text)
        if search_match:
            q = search_match.group(1).strip()
            webbrowser.open(f"https://www.google.com/search?q={q.replace(' ', '+')}")
            return f"Wird gesucht."

        return None

    # ========== NEUE FEATURES ==========

    def _change_voice(self, text):
        if not self.voice_ref: return "Stimmen-Wechsel nicht verfügbar."
        if "weiblich" in text:
            return self.voice_ref.set_voice("weiblich")
        elif "männlich" in text:
            return self.voice_ref.set_voice("männlich")
        elif "conrad" in text:
            return self.voice_ref.set_voice("conrad")
        elif "seraphina" in text:
            return self.voice_ref.set_voice("seraphina")
        elif "florian" in text:
            return self.voice_ref.set_voice("florian")
        elif "killian" in text:
            return self.voice_ref.set_voice("killian")
        return "Boss, verfügbare Stimmen: männlich, weiblich, conrad, seraphina, florian, killian."

    def _change_speed(self, text):
        if not self.voice_ref: return "Speed nicht verfügbar."
        if "schneller" in text: return self.voice_ref.set_speed("schneller")
        if "langsamer" in text: return self.voice_ref.set_speed("langsamer")
        if "normal" in text: return self.voice_ref.set_speed("normal")
        return self.voice_ref.set_speed("normal")

    def _system_monitor(self, text):
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\')
        battery = psutil.sensors_battery()

        result = f"Boss, System-Status: CPU bei {cpu} Prozent. "
        result += f"RAM: {ram.percent} Prozent belegt, {round(ram.available/1024**3, 1)} GB frei. "
        result += f"Festplatte C: {disk.percent} Prozent belegt, {round(disk.free/1024**3, 1)} GB frei. "
        if battery:
            result += f"Akku: {battery.percent} Prozent"
            if battery.power_plugged:
                result += ", lädt."
            else:
                mins = battery.secsleft // 60 if battery.secsleft > 0 else 0
                result += f", noch etwa {mins} Minuten."
        return result

    def _watchlist(self, text):
        # "sag mir wenn bitcoin über 100000 geht"
        match = re.search(r"(?:sag mir wenn|alarm wenn|benachrichtige wenn|watchlist)\s+(\w+)\s+(?:über|above|über)\s+(\d+)", text)
        if match:
            asset = match.group(1).lower()
            target = int(match.group(2))
            asset_map = {"bitcoin": "bitcoin", "btc": "bitcoin", "ethereum": "ethereum", "eth": "ethereum",
                        "solana": "solana", "sol": "solana", "dogecoin": "dogecoin", "doge": "dogecoin"}
            asset_id = asset_map.get(asset, asset)

            watchlist = []
            if os.path.exists(WATCHLIST_FILE):
                with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                    watchlist = json.load(f)
            watchlist.append({"type": "crypto", "asset": asset_id, "target": target, "direction": "above"})
            with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(watchlist, f, indent=4)
            return f"Watchlist. Ich sage Bescheid wenn {asset_id.title()} über {target} Dollar geht."

        # "sag mir wenn bitcoin unter 50000 geht"
        match = re.search(r"(?:sag mir wenn|alarm wenn)\s+(\w+)\s+(?:unter|below)\s+(\d+)", text)
        if match:
            asset = match.group(1).lower()
            target = int(match.group(2))
            asset_map = {"bitcoin": "bitcoin", "btc": "bitcoin", "ethereum": "ethereum", "eth": "ethereum"}
            asset_id = asset_map.get(asset, asset)
            watchlist = []
            if os.path.exists(WATCHLIST_FILE):
                with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                    watchlist = json.load(f)
            watchlist.append({"type": "crypto", "asset": asset_id, "target": target, "direction": "below"})
            with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(watchlist, f, indent=4)
            return f"Watchlist. Alarm wenn {asset_id.title()} unter {target} Dollar fällt."

        # Aktueller Preis
        if any(w in text for w in ["bitcoin", "ethereum", "solana", "krypto"]):
            try:
                coins = "bitcoin,ethereum,solana"
                r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coins}&vs_currencies=usd,eur", timeout=5)
                data = r.json()
                result = "Boss, aktuelle Krypto-Kurse: "
                for coin in ["bitcoin", "ethereum", "solana"]:
                    if coin in data:
                        result += f"{coin.title()}: {data[coin]['usd']:,.0f} Dollar ({data[coin]['eur']:,.0f} Euro). "
                return result
            except:
                return "Krypto-Kurse nicht verfügbar."

        return None

    def _find_file(self, text):
        match = re.search(r"(?:finde|suche|wo ist)\s+(?:datei|meine|die)?\s*(.+)", text)
        if not match: return "Boss, welche Datei soll ich suchen?"
        query = match.group(1).strip().rstrip(".")
        search_dirs = [
            os.path.expanduser("~\\Desktop"),
            os.path.expanduser("~\\Documents"),
            os.path.expanduser("~\\Downloads"),
        ]
        found = []
        for search_dir in search_dirs:
            if not os.path.exists(search_dir): continue
            for root, dirs, files in os.walk(search_dir):
                for f in files:
                    if query.lower() in f.lower():
                        found.append(os.path.join(root, f))
                if len(found) >= 5: break
        if not found:
            return f"Boss, ich konnte keine Datei mit '{query}' finden."
        result = f"Boss, ich habe {len(found)} Datei(en) gefunden: "
        for f in found[:5]:
            result += f"{os.path.basename(f)} in {os.path.dirname(f)}. "
        # Erste Datei im Explorer markieren
        if found:
            subprocess.Popen(f'explorer /select,"{found[0]}"')
        return result

    def _write_email(self, text):
        match = re.search(r"(?:email|mail)\s+(?:an\s+)?(.+?)(?:\s+(?:mit|betreff|über|wegen)\s+(.+))?$", text)
        if not match: return "Boss, an wen und worüber soll die Email sein?"
        recipient = match.group(1).strip()
        topic = match.group(2).strip() if match.group(2) else "Nachricht"
        try:
            r = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": "Schreibe eine professionelle aber freundliche Email auf Deutsch. Nur die Email, nichts anderes. Beginne mit 'Betreff:' dann Leerzeile dann der Text."},
                          {"role": "user", "content": f"Email an {recipient} über: {topic}"}],
                max_tokens=400, temperature=0.7)
            email_text = r.choices[0].message.content.strip()
            # In Zwischenablage
            try:
                subprocess.run(['clip'], input=email_text.encode('utf-8'), check=True)
            except: pass
            # Outlook öffnen
            webbrowser.open(f"mailto:{recipient}?subject={topic}")
            return f"Boss, die Email wurde geschrieben und in die Zwischenablage kopiert. Outlook wird geöffnet."
        except Exception as e: return f"Email-Fehler, Boss: {e}"

    def _write_code(self, text):
        match = re.search(r"(?:schreib|programmiere|code)\s+(?:mir\s+)?(?:ein\s+)?(.+)", text)
        if not match: return "Boss, was soll ich programmieren?"
        task = match.group(1).strip()
        try:
            r = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": "Du bist ein Programmierer. Schreibe sauberen, kommentierten Code. Antworte NUR mit dem Code, keine Erklärung drumherum. Erkenne die Sprache aus der Aufgabe."},
                          {"role": "user", "content": task}],
                max_tokens=1000, temperature=0.3)
            code = r.choices[0].message.content.strip()
            # Code in Datei speichern
            ext = ".py" if "python" in task.lower() else ".js" if "javascript" in task.lower() else ".py"
            filename = f"code_{datetime.datetime.now().strftime('%H%M%S')}{ext}"
            filepath = os.path.join(APP_DIR, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)
            # In VS Code öffnen
            subprocess.Popen(f'code "{filepath}"', shell=True)
            return f"Boss, Code geschrieben und in VS Code geöffnet: {filename}"
        except Exception as e: return f"Code-Fehler, Boss: {e}"

    # ========== BESTEHENDE FEATURES ==========

    def _lock_pc(self):
        if sys.platform == "win32":
            import ctypes; ctypes.windll.user32.LockWorkStation()
        return "PC gesperrt."

    def _start_recording(self):
        if self.is_recording: return "Aufnahme läuft bereits."
        try:
            import ctypes
            for vk in [0x5B, 0x12, 0x52]:
                ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.1)
            for vk in [0x52, 0x12, 0x5B]:
                ctypes.windll.user32.keybd_event(vk, 0, 0x0002, 0)
            self.is_recording = True; return "Aufnahme gestartet."
        except Exception as e: return f"Aufnahme-Fehler: {e}"

    def _stop_recording(self):
        if not self.is_recording: return "Keine Aufnahme aktiv."
        try:
            import ctypes
            for vk in [0x5B, 0x12, 0x52]:
                ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.1)
            for vk in [0x52, 0x12, 0x5B]:
                ctypes.windll.user32.keybd_event(vk, 0, 0x0002, 0)
            self.is_recording = False; return "Aufnahme gespeichert."
        except Exception as e: return f"Fehler: {e}"

    def _news(self, text):
        cat = "allgemein"
        if any(w in text for w in ["tech", "technologie"]): cat = "tech"
        elif any(w in text for w in ["gaming", "spiele"]): cat = "gaming"
        try:
            feed = feedparser.parse(NEWS_FEEDS.get(cat, NEWS_FEEDS["allgemein"]))
            if not feed.entries: return "Keine Nachrichten."
            result = f"Boss, {cat.title()}-Nachrichten: "
            for i, e in enumerate(feed.entries[:5]): result += f"{i+1}. {e.get('title','')}. "
            return result
        except Exception as e: return f"News-Fehler: {e}"

    def _current_song(self):
        if sys.platform != "win32": return "Nur Windows."
        try:
            import ctypes
            titles = []
            def cb(hwnd, _):
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    l = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if l > 0:
                        b = ctypes.create_unicode_buffer(l+1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, b, l+1)
                        if " - " in b.value: titles.append(b.value)
                return True
            ctypes.windll.user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))(cb), 0)
            for t in titles:
                if "Spotify" in t and t not in ["Spotify","Spotify Free","Spotify Premium"]:
                    c = t.replace(" - Spotify","").strip()
                    if " - " in c:
                        p = c.split(" - ",1); return f"Boss, gerade läuft: {p[1]} von {p[0]}."
                    return f"Boss, gerade läuft: {c}."
            return "Kein Song erkannt."
        except: return "Song-Erkennung fehlgeschlagen."

    def _spotify_playlist(self, text):
        m = re.search(r"(?:spiel|spiele|starte)\s+(?:meine\s+)?(.+?)(?:\s+playlist)?$", text)
        if m:
            p = m.group(1).strip()
            webbrowser.open(f"https://open.spotify.com/search/{p.replace(' ','%20')}/playlists")
            return f"{p.title()} Playlist wird gesucht."
        return "Welche Playlist, Boss?"

    def _joke(self):
        try:
            r = self.client.chat.completions.create(model="llama-3.3-70b-versatile",
                messages=[{"role":"system","content":"Erzähle einen kurzen Witz auf Deutsch. Beginne mit 'Boss,'."},
                          {"role":"user","content":"Witz"}], max_tokens=150, temperature=0.9)
            return r.choices[0].message.content
        except: return "Boss, warum können Geister nicht lügen? Man sieht durch sie durch."

    def _dice(self, text):
        m = re.search(r"(\d+)", text); sides = int(m.group(1)) if m else 6
        return f"Boss, eine {random.randint(1, sides)} gewürfelt."

    def _password(self, text):
        m = re.search(r"(\d+)", text); l = max(8,min(64,int(m.group(1)))) if m else 16
        pw = ''.join(random.choices(string.ascii_letters+string.digits+"!@#$%&*", k=l))
        try: subprocess.run(['clip'],input=pw.encode(),check=True); return f"Passwort ({l} Zeichen) in Zwischenablage."
        except: return f"Passwort: {pw}"

    def _qr_code(self, text):
        m = re.search(r"(?:qr.?code)\s*(?:für|von|mit)?\s*(.+)", text)
        if not m: return "Was soll der QR-Code enthalten, Boss?"
        content = m.group(1).strip()
        try:
            import qrcode; qr = qrcode.make(content)
            path = os.path.join(APP_DIR, "qrcode.png"); qr.save(path); os.startfile(path)
            return f"QR-Code erstellt."
        except Exception as e: return f"QR-Fehler: {e}"

    def _convert_units(self, text):
        convs = {
            (r"(\d+[.,]?\d*)\s*meilen","km"): lambda x: (x*1.60934,"Kilometer"),
            (r"(\d+[.,]?\d*)\s*(?:km|kilometer)","meilen"): lambda x: (x/1.60934,"Meilen"),
            (r"(\d+[.,]?\d*)\s*fahrenheit","celsius"): lambda x: ((x-32)*5/9,"Grad Celsius"),
            (r"(\d+[.,]?\d*)\s*celsius","fahrenheit"): lambda x: (x*9/5+32,"Grad Fahrenheit"),
            (r"(\d+[.,]?\d*)\s*(?:pfund|lbs)","kg"): lambda x: (x*0.453592,"Kilogramm"),
            (r"(\d+[.,]?\d*)\s*(?:zoll|inch)","cm"): lambda x: (x*2.54,"Zentimeter"),
            (r"(\d+[.,]?\d*)\s*(?:fuß|feet)","meter"): lambda x: (x*0.3048,"Meter"),
        }
        for (p,t),f in convs.items():
            m = re.search(p, text)
            if m:
                v = float(m.group(1).replace(",",".")); r,u = f(v)
                return f"Boss, {v} = {round(r,2)} {u}."
        return None

    def _convert_currency(self, text):
        m = re.search(r"(\d+[.,]?\d*)\s*(dollar|euro|pfund|yen|franken)", text)
        if not m: return None
        amount = float(m.group(1).replace(",",".")); cur = m.group(2).lower()
        cmap = {"dollar":"USD","euro":"EUR","pfund":"GBP","yen":"JPY","franken":"CHF"}
        src = cmap.get(cur,"USD"); tgt = "EUR" if src != "EUR" else "USD"
        if "in euro" in text: tgt="EUR"
        elif "in dollar" in text: tgt="USD"
        try:
            r = requests.get(f"https://api.exchangerate-api.com/v4/latest/{src}",timeout=5).json()
            result = amount * r["rates"].get(tgt,1)
            tname = {"EUR":"Euro","USD":"Dollar","GBP":"Pfund","JPY":"Yen","CHF":"Franken"}.get(tgt,tgt)
            return f"Boss, {amount} {cur.title()} = {round(result,2)} {tname}."
        except: return "Währung nicht verfügbar."

    def _birthday(self, text):
        m = re.search(r"geburtstag\s+(?:von\s+)?(\w+)\s+(?:ist\s+)?(?:am\s+)?(\d{1,2})\.(\d{1,2})", text)
        if m:
            name=m.group(1).title(); bdays={}
            if os.path.exists(BIRTHDAY_FILE):
                with open(BIRTHDAY_FILE,"r",encoding="utf-8") as f: bdays=json.load(f)
            bdays[name]=f"{m.group(2).zfill(2)}.{m.group(3).zfill(2)}"
            with open(BIRTHDAY_FILE,"w",encoding="utf-8") as f: json.dump(bdays,f,indent=4,ensure_ascii=False)
            return f"Gemerkt. {name} am {m.group(2)}.{m.group(3)}."
        if any(w in text for w in ["alle geburtstage","geburtstage zeigen","wer hat geburtstag"]):
            if not os.path.exists(BIRTHDAY_FILE): return "Keine Geburtstage gespeichert."
            with open(BIRTHDAY_FILE,"r",encoding="utf-8") as f: bdays=json.load(f)
            if not bdays: return "Keine Geburtstage."
            r = "Boss, Geburtstage: "
            for n,d in bdays.items(): r += f"{n} am {d}. "
            return r
        return None

    def _streaming(self, text):
        m = re.search(r"(?:ich will|ich möchte|starte|stream|streame)\s+(.+?)\s*(?:streamen|stream|starten)?$", text)
        if not m:
            if any(w in text for w in ["will streamen","starte stream"]): return self._launch_profile("default")
            return None
        g = m.group(1).strip()
        if g in STREAMING_PROFILES: return self._launch_profile(g)
        apps = ["obs","chatterino"];
        if g in KNOWN_APPS: apps.append(g)
        self._launch_apps(apps); return f"OBS, Chatterino und {g.title()} starten."

    def _launch_profile(self, n):
        p=STREAMING_PROFILES.get(n)
        if not p: return None
        self._launch_apps(p["apps"])
        if "urls" in p:
            for u in p["urls"]: webbrowser.open(u)
        return p["message"]

    def _stop_stream(self):
        os.system("taskkill /f /im obs64.exe >nul 2>&1")
        os.system("taskkill /f /im obs.exe >nul 2>&1")
        os.system("taskkill /f /im chatterino.exe >nul 2>&1")
        return "Stream beendet."

    def _multi_mode(self, text):
        for t,m in MULTI_MODES.items():
            if t in text:
                self._launch_apps(m["apps"])
                if "urls" in m:
                    for u in m["urls"]: webbrowser.open(u)
                return m["message"]
        return None

    def _custom_command(self, text):
        for t,c in self.custom_commands.items():
            if t.lower() in text:
                if c.get("apps"): self._launch_apps(c["apps"])
                for u in c.get("urls",[]): webbrowser.open(u)
                if c.get("timer_minutes"):
                    self._timer_callback = {"seconds":c["timer_minutes"]*60,"label":f"{c['timer_minutes']} Min"}
                return c.get("message","Ausgeführt.")
        return None

    def _create_custom_command(self, text):
        m = re.search(r"(?:neuer befehl|neues kommando)\s+(.+)", text)
        if not m: return "Sage: neuer Befehl Name Apps App1 App2."
        parts=m.group(1).strip(); nm=re.match(r"(\w+(?:\s\w+)?)",parts)
        if not nm: return "Name fehlt."
        cn=nm.group(1).strip(); rest=parts[nm.end():].strip()
        apps=[]; am=re.search(r"apps?\s+(.+?)(?:\s+(?:timer|url)|$)",rest)
        if am:
            for a in am.group(1).split(): apps.append(a)
        if not apps: return f"'{cn}' braucht Apps."
        cmd={"apps":apps,"urls":[],"message":f"{cn.title()}-Modus."}
        self.custom_commands[cn.lower()]=cmd; self.config["custom_commands"]=self.custom_commands
        save_config(self.config); return f"'{cn}' gespeichert."

    def _list_custom_commands(self):
        if not self.custom_commands: return "Keine Befehle."
        r="Deine Befehle: "
        for n,c in self.custom_commands.items(): r+=f"{n}: {', '.join(c.get('apps',[]))}. "
        return r

    def _launch_apps(self, apps):
        for a in apps:
            try:
                cmd = KNOWN_APPS.get(a.lower(), a)

                # Discord Auto-Detect
                if cmd == "auto_discord":
                    discord_base = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Discord")
                    if os.path.exists(discord_base):
                        # Finde den neuesten app-X.X.XXXX Ordner
                        app_dirs = [d for d in os.listdir(discord_base) if d.startswith("app-")]
                        if app_dirs:
                            app_dirs.sort(reverse=True)  # Neueste Version zuerst
                            exe = os.path.join(discord_base, app_dirs[0], "Discord.exe")
                            if os.path.exists(exe):
                                subprocess.Popen(exe)
                                time.sleep(1.5)
                                continue
                    # Fallback: Update.exe
                    update_exe = os.path.join(discord_base, "Update.exe")
                    if os.path.exists(update_exe):
                        subprocess.Popen(f'"{update_exe}" --processStart Discord.exe')
                        time.sleep(1.5)
                        continue
                    # Letzter Fallback
                    subprocess.Popen("start discord", shell=True)
                    time.sleep(1.5)
                    continue

                if cmd.startswith("steam://") or cmd.startswith("com.epicgames"):
                    webbrowser.open(cmd)
                elif cmd.endswith(".lnk"):
                    os.startfile(cmd)
                elif os.path.exists(cmd.split(" --")[0].split(" -")[0].strip('"')):
                    subprocess.Popen(cmd, shell=True)
                elif sys.platform == "win32":
                    subprocess.Popen(f'start "" "{cmd}"', shell=True)
                else:
                    subprocess.Popen([cmd])
                time.sleep(1.5)
            except Exception as e:
                print(f"  [Fehler: {a}: {e}]")

    def _translate(self, text):
        m = re.search(r"(?:was hei[ßs]t|übersetze?)\s+(.+?)\s+(?:auf|ins?)\s+(\w+)", text)
        if not m: return None
        word=m.group(1).strip(); lang=m.group(2).strip()
        lmap={"englisch":"English","französisch":"French","spanisch":"Spanish","italienisch":"Italian",
              "türkisch":"Turkish","russisch":"Russian","japanisch":"Japanese","koreanisch":"Korean"}
        try:
            r=self.client.chat.completions.create(model="llama-3.3-70b-versatile",
                messages=[{"role":"system","content":f"Übersetze ins {lmap.get(lang.lower(),lang)}. NUR die Übersetzung."},
                          {"role":"user","content":word}], max_tokens=200, temperature=0.1)
            return f"Boss, '{word}' auf {lang.title()}: {r.choices[0].message.content.strip()}."
        except: return "Übersetzungsfehler."

    def _wikipedia(self, text):
        m = re.search(r"(?:wikipedia|wiki|erkläre?)\s+(?:mir\s+)?(.+)", text)
        if not m: return None
        topic=m.group(1).strip().rstrip(".")
        try:
            r=requests.get(f"https://de.wikipedia.org/api/rest_v1/page/summary/{topic.replace(' ','_')}",
                          timeout=5,headers={"User-Agent":"ComputerAssistant/1.0"})
            if r.status_code==200:
                d=r.json(); e=d.get("extract",""); u=d.get("content_urls",{}).get("desktop",{}).get("page","")
                if e:
                    s=". ".join(e.split(". ")[:4])+"."
                    if u: webbrowser.open(u)
                    return f"Boss, {s}"
            return None
        except: return None

    def _weather(self, text):
        m=re.search(r"wetter\s*(?:in|für|von)?\s*(.+)",text)
        city=m.group(1).strip().rstrip(".") if m else self.memory.get("wohnort","Berlin")
        try:
            geo=requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=de",timeout=5).json()
            if "results" not in geo: return f"{city} nicht gefunden."
            r=geo["results"][0]
            w=requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={r['latitude']}&longitude={r['longitude']}&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m&timezone=auto",timeout=5).json()["current"]
            return f"Boss, {r.get('name',city)}: {WMO_CODES.get(w['weather_code'],'?')} bei {round(w['temperature_2m'])}°, gefühlt {round(w['apparent_temperature'])}°. Wind {round(w['wind_speed_10m'])} km/h."
        except Exception as e: return f"Wetter-Fehler: {e}"

    def _timer(self, text):
        m=re.search(r"timer\s*(?:auf|von|für)?\s*(\d+)\s*(sekunde|minute|stunde)",text)
        if not m: return None
        a=int(m.group(1)); u=m.group(2)
        s=a*(3600 if "stunde" in u else 60 if "minute" in u else 1)
        l=f"{a} {'Stunden' if 'stunde' in u else 'Minuten' if 'minute' in u else 'Sekunden'}"
        self._timer_callback={"seconds":s,"label":l}; return f"Timer: {l}."

    def get_pending_timer(self):
        t=self._timer_callback; self._timer_callback=None; return t

    def _reminder(self, text):
        m=re.search(r"erinner\w*\s+(?:mich\s+)?um\s+(\d{1,2})(?::(\d{2}))?\s*(?:uhr\s+)?(?:an\s+)?(.+)",text)
        if not m: return None
        h,mi=int(m.group(1)),int(m.group(2) or 0); task=m.group(3).strip().rstrip(".")
        now=datetime.datetime.now(); tgt=now.replace(hour=h,minute=mi,second=0)
        if tgt<=now: tgt+=datetime.timedelta(days=1)
        self._reminder_callback={"seconds":(tgt-now).total_seconds(),"task":task}
        return f"Erinnerung {h:02d}:{mi:02d}: {task}."

    def get_pending_reminder(self):
        r=self._reminder_callback; self._reminder_callback=None; return r

    def _notes(self, text):
        m=re.search(r"(?:merke?|notiz|notiere|schreib auf|merk dir)[:\s]+(.+)",text)
        if m: return f"Notiert. {self.notes.add(m.group(1).strip().rstrip('.'))}"
        if any(w in text for w in ["notizen zeigen","meine notizen","alle notizen"]): return f"Boss, {self.notes.list_all()}"
        if "notizen löschen" in text: return f"Erledigt. {self.notes.clear()}"
        return None

    def _todos(self, text):
        m=re.search(r"(?:todo|to do|aufgabe|auf die liste)[:\s]+(.+)",text)
        if not m: m=re.search(r"(?:ich muss noch|ich muss)\s+(.+)",text)
        if m: return f"Verstanden. {self.todos.add(m.group(1).strip().rstrip('.'))}"
        if any(w in text for w in ["todo liste","meine aufgaben","meine todos"]): return f"Boss, {self.todos.list_open()}"
        dm=re.search(r"(?:aufgabe|todo)\s+(\d+)\s+(?:erledigt|fertig)",text)
        if dm: return f"Abgehakt. {self.todos.complete(int(dm.group(1))-1)}"
        if "todos löschen" in text: return f"{self.todos.clear()}"
        return None

    def _music(self, text):
        try:
            import ctypes
            keys={"pause":0xB3,"play":0xB3,"abspielen":0xB3,"pausieren":0xB3,"nächster song":0xB0,
                  "nächstes lied":0xB0,"skip":0xB0,"überspringen":0xB0,"vorheriger song":0xB1,"song zurück":0xB1}
            labels={0xB3:"Play/Pause.",0xB0:"Nächster Song.",0xB1:"Vorheriger Song."}
            for kw,vk in keys.items():
                if kw in text:
                    ctypes.windll.user32.keybd_event(vk,0,1,0); ctypes.windll.user32.keybd_event(vk,0,3,0)
                    return labels[vk]
        except: pass
        return None

    def _volume(self, text):
        try:
            from ctypes import cast,POINTER; from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities,IAudioEndpointVolume
            d=AudioUtilities.GetSpeakers(); i=d.Activate(IAudioEndpointVolume._iid_,CLSCTX_ALL,None)
            vol=cast(i,POINTER(IAudioEndpointVolume)); cur=vol.GetMasterVolumeLevelScalar()
            if any(w in text for w in ["lauter"]): v=min(1,cur+0.1); vol.SetMasterVolumeLevelScalar(v,None); return f"{int(v*100)}%."
            if any(w in text for w in ["leiser"]): v=max(0,cur-0.1); vol.SetMasterVolumeLevelScalar(v,None); return f"{int(v*100)}%."
            if any(w in text for w in ["stumm","ton aus"]): vol.SetMasterVolumeLevelScalar(0,None); return "Stumm."
            if "ton an" in text: vol.SetMasterVolumeLevelScalar(0.5,None); return "50%."
            m=re.search(r"lautstärke\s*(?:auf)?\s*(\d+)",text)
            if m: l=max(0,min(100,int(m.group(1)))); vol.SetMasterVolumeLevelScalar(l/100,None); return f"{l}%."
        except: pass
        return None

    def _math(self, text):
        m=re.search(r"(?:was ist|berechne|rechne|wie viel ist)\s+(.+)",text)
        if not m: return None
        e=m.group(1).strip().rstrip(".")
        e=e.replace("mal","*").replace("plus","+").replace("minus","-").replace("geteilt durch","/").replace("durch","/").replace("hoch","**").replace(",",".")
        s=re.sub(r"[^0-9+\-*/.()\s]","",e)
        if not s.strip(): return None
        try: r=eval(s,{"__builtins__":{}}); return f"{round(r,4) if isinstance(r,float) else r}."
        except: return None

    def _pc(self, text):
        if any(w in text for w in ["herunterfahren","pc aus","shutdown"]):
            threading.Thread(target=lambda:os.system("shutdown /s /t 10"),daemon=True).start()
            return "Herunterfahren in 10s."
        if any(w in text for w in ["neustart","restart"]):
            threading.Thread(target=lambda:os.system("shutdown /r /t 10"),daemon=True).start()
            return "Neustart in 10s."
        if "abbrechen" in text: os.system("shutdown /a"); return "Abgebrochen."
        return None

    def _open(self, text):
        tw=re.search(r"(?:öffne|starte|mach)\s+(.+?)\s+(?:auf|in|bei)\s+twitch",text)
        if tw: s=tw.group(1).strip(); webbrowser.open(KNOWN_URLS.get(s,f"https://www.twitch.tv/{s}")); return f"{s.title()} auf Twitch."
        yt=re.search(r"(?:öffne|starte|mach)\s+(.+?)\s+(?:auf|in|bei)\s+youtube",text)
        if yt: webbrowser.open(f"https://www.youtube.com/results?search_query={yt.group(1).strip().replace(' ','+')}"); return f"{yt.group(1).title()} auf YouTube."
        target=text.replace("öffne","").replace("starte","").replace("mach","").replace("an","").replace("auf","").strip()
        if target in KNOWN_URLS: webbrowser.open(KNOWN_URLS[target]); return f"{target.title()} geöffnet."
        if target in KNOWN_APPS: self._launch_apps([target]); return f"{target.title()} gestartet."
        return None
        # ========== KONTEXT / VERLAUF ==========

    def _get_context(self, text):
        if any(w in text for w in ["was hab ich gefragt", "was habe ich gefragt", "was war meine frage",
                                    "wiederhole", "was hab ich gesagt", "letzte frage"]):
            user_msgs = [m["content"] for m in self.chat_history if m["role"] == "user"]
            if not user_msgs:
                return "Boss, du hast noch nichts gefragt."
            last = user_msgs[-1]
            return f"Boss, deine letzte Frage war: {last}"

        if any(w in text for w in ["verlauf", "gesprächsverlauf", "was haben wir besprochen",
                                    "zusammenfassung"]):
            if not self.chat_history:
                return "Boss, wir haben noch nicht gesprochen."
            result = "Boss, hier unser bisheriges Gespräch: "
            for m in self.chat_history[-10:]:
                role = "Du" if m["role"] == "user" else self.name
                content = m["content"][:80]
                result += f"{role}: {content}. "
            return result

        return None

    # ========== HABIT-TRACKER ==========

    def _habit_tracker(self, text):
        HABIT_FILE = os.path.join(APP_DIR, "habits.json")

        def load_habits():
            if os.path.exists(HABIT_FILE):
                with open(HABIT_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {"habits": {}, "log": {}}

        def save_habits(data):
            with open(HABIT_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        data = load_habits()

        # Neues Habit erstellen: "neues habit sport"
        match = re.search(r"(?:neues habit|neuer habit|neue gewohnheit|habit erstellen)\s+(.+)", text)
        if match:
            habit = match.group(1).strip().rstrip(".")
            data["habits"][habit.lower()] = {"name": habit, "created": today}
            save_habits(data)
            return f"Habit '{habit}' erstellt. Sage '{habit} erledigt' wenn du es gemacht hast."

        # Habit als erledigt markieren: "sport erledigt" / "ich habe sport gemacht"
        for habit_key, habit_info in data["habits"].items():
            if habit_key in text and any(w in text for w in ["erledigt", "gemacht", "geschafft", "done", "fertig"]):
                if today not in data["log"]:
                    data["log"][today] = []
                if habit_key not in data["log"][today]:
                    data["log"][today].append(habit_key)
                    save_habits(data)
                    # Streak berechnen
                    streak = 0
                    check_date = datetime.datetime.now()
                    while True:
                        d = check_date.strftime("%Y-%m-%d")
                        if d in data["log"] and habit_key in data["log"][d]:
                            streak += 1
                            check_date -= datetime.timedelta(days=1)
                        else:
                            break
                    return f"Abgehakt! {habit_info['name']} erledigt. Streak: {streak} Tage am Stück!"
                else:
                    return f"Boss, {habit_info['name']} hast du heute schon abgehakt."

        # Status abfragen: "hab ich heute sport gemacht" / "meine habits"
        if any(w in text for w in ["meine habits", "habit status", "alle habits", "gewohnheiten",
                                    "hab ich heute", "was muss ich noch"]):
            if not data["habits"]:
                return "Boss, du hast noch keine Habits. Sage 'neues Habit Sport' zum Erstellen."
            result = "Boss, deine Habits für heute: "
            today_log = data["log"].get(today, [])
            for key, info in data["habits"].items():
                done = "erledigt" if key in today_log else "offen"
                # Streak
                streak = 0
                check_date = datetime.datetime.now()
                if done == "erledigt":
                    while True:
                        d = check_date.strftime("%Y-%m-%d")
                        if d in data["log"] and key in data["log"][d]:
                            streak += 1; check_date -= datetime.timedelta(days=1)
                        else: break
                result += f"{info['name']}: {done}"
                if streak > 1:
                    result += f" ({streak} Tage Streak)"
                result += ". "
            return result

        # Habit löschen
        if any(w in text for w in ["habit löschen", "habit entfernen", "lösche habit"]):
            match = re.search(r"(?:lösche|entferne|lösch)\s+(?:habit\s+)?(.+)", text)
            if match:
                h = match.group(1).strip().rstrip(".")
                if h.lower() in data["habits"]:
                    del data["habits"][h.lower()]
                    save_habits(data)
                    return f"Habit '{h}' gelöscht."
            return "Boss, welches Habit soll ich löschen?"

        return None

    # ========== TAGEBUCH ==========

    def _diary(self, text):
        DIARY_FILE = os.path.join(APP_DIR, "diary.json")

        def load_diary():
            if os.path.exists(DIARY_FILE):
                with open(DIARY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {"entries": []}

        def save_diary(data):
            with open(DIARY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

        # Eintrag schreiben: "tagebuch heute war ein guter tag"
        match = re.search(r"(?:tagebuch|diary|journal)[:\s]+(.+)", text)
        if match:
            entry = match.group(1).strip().rstrip(".")
            data = load_diary()
            now = datetime.datetime.now()
            data["entries"].append({
                "date": now.strftime("%d.%m.%Y"),
                "time": now.strftime("%H:%M"),
                "text": entry,
                "weekday": ["Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"][now.weekday()],
            })
            save_diary(data)
            return f"Tagebuch-Eintrag gespeichert. {now.strftime('%d.%m.%Y %H:%M')}."

        # Einträge lesen: "lies mein tagebuch" / "tagebuch von heute"
        if any(w in text for w in ["lies tagebuch", "tagebuch zeigen", "mein tagebuch",
                                    "tagebuch von heute", "tagebuch lesen", "tagebucheinträge"]):
            data = load_diary()
            if not data["entries"]:
                return "Boss, dein Tagebuch ist noch leer."

            # Heute oder alle?
            if "heute" in text:
                today = datetime.datetime.now().strftime("%d.%m.%Y")
                entries = [e for e in data["entries"] if e["date"] == today]
                if not entries:
                    return "Boss, heute hast du noch nichts geschrieben."
                result = f"Boss, deine Einträge von heute: "
                for e in entries:
                    result += f"Um {e['time']}: {e['text']}. "
                return result
            else:
                # Letzte 5 Einträge
                result = "Boss, deine letzten Tagebuch-Einträge: "
                for e in data["entries"][-5:]:
                    result += f"{e['weekday']} {e['date']} um {e['time']}: {e['text']}. "
                return result

        return None

    # ========== MULTI-MONITOR ==========

    def _move_window(self, text):
        match = re.search(r"(?:verschiebe|schieb|mach|pack)\s+(.+?)\s+(?:auf|zum|auf den|zum)\s+(?:den\s+)?(?:zweiten|2\.?|anderen|rechten|linken)\s+(?:bildschirm|monitor|screen)", text)
        if not match:
            return None

        app_name = match.group(1).strip().lower()

        try:
            import pygetwindow as gw
            import ctypes

            # Alle Fenster finden die den App-Namen enthalten
            windows = gw.getWindowsWithTitle('')
            target = None

            search_terms = {
                "discord": "discord",
                "spotify": "spotify",
                "chrome": "google chrome",
                "firefox": "firefox",
                "steam": "steam",
                "obs": "obs",
                "vscode": "visual studio code",
                "vs code": "visual studio code",
                "notepad": "notepad",
                "explorer": "explorer",
            }

            search = search_terms.get(app_name, app_name)

            for w in windows:
                if search.lower() in w.title.lower() and w.visible:
                    target = w
                    break

            if not target:
                return f"Boss, ich kann das {app_name.title()}-Fenster nicht finden."

            # Monitor-Info holen
            user32 = ctypes.windll.user32
            monitors = []

            def monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
                rect = lprcMonitor.contents
                monitors.append({
                    "left": rect.left,
                    "top": rect.top,
                    "right": rect.right,
                    "bottom": rect.bottom,
                })
                return True

            MonitorEnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int),
                                                  ctypes.POINTER(ctypes.c_int),
                                                  ctypes.POINTER(ctypes.wintypes.RECT),
                                                  ctypes.POINTER(ctypes.c_int))
            import ctypes.wintypes
            user32.EnumDisplayMonitors(None, None, MonitorEnumProc(monitor_enum_proc), 0)

            if len(monitors) < 2:
                return "Boss, ich sehe nur einen Monitor. Für Multi-Monitor brauchst du zwei Bildschirme."

            # Aktueller Monitor des Fensters
            win_center_x = target.left + target.width // 2
            current_monitor = 0
            for i, m in enumerate(monitors):
                if m["left"] <= win_center_x < m["right"]:
                    current_monitor = i
                    break

            # Zum anderen Monitor verschieben
            other = 1 if current_monitor == 0 else 0
            new_x = monitors[other]["left"] + 50
            new_y = monitors[other]["top"] + 50

            target.moveTo(new_x, new_y)
            return f"{app_name.title()} auf den anderen Bildschirm verschoben."

        except ImportError:
            return "Boss, pygetwindow ist nicht installiert. Sage 'pip install pygetwindow'."
        except Exception as e:
            return f"Fenster-Fehler, Boss: {e}"

    def _ask_ai(self, user_input):
        now=datetime.datetime.now()
        tage=["Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"]
        un=self.memory.get("user_name","")
        prompt=f"""Du bist {self.name}, hochintelligenter KI-Assistent.
Wie JARVIS: intelligent, eloquent, loyal, sarkastisch. IMMER "Boss" sagen.
WICHTIG zur Anrede: Sage "Boss" Nur Bei Begrüßung unmd verabschiedung. Bei Normalen antworten KEIN "Boss". Antworte Dierekt und natürlich ohne ständig "boss" zu sagen.
Keine Emojis, kein Markdown, natürlich aussprechbar, Deutsch.
{"Nutzer: "+un+"." if un else ""}
ZEIT: {now.strftime("%H:%M")} | {tage[now.weekday()]}, {now.strftime("%d.%m.%Y")}
NUTZER: {self.memory.get_context()}
Befehle: 1-2 Sätze. Wissen: 4-8 Sätze. URLs wenn passend.
Bei "erkläre mir X" gib eine ausführliche, lehrreiche Erklärung."""

        msgs=[{"role":"system","content":prompt}]+self.chat_history+[{"role":"user","content":user_input}]
        try:
            r=self.client.chat.completions.create(model="llama-3.3-70b-versatile",messages=msgs,max_tokens=600,temperature=0.7)
            return r.choices[0].message.content
        except Exception as e: return f"API-Fehler, Boss: {e}"

    def _add_history(self, role, content):
        self.chat_history.append({"role":role,"content":content})
        while len(self.chat_history)>self.max_history: self.chat_history.pop(0)
