"""
Persönlicher KI-Assistent mit Sprachsteuerung (Groq + Edge-TTS)
Hört IMMER zu – kein Wake-Word nötig.
"""

from groq import Groq
import json
import os
import webbrowser
import subprocess
import sys
import datetime
import asyncio
import tempfile
import re
import threading
import time
import math
import requests
import speech_recognition as sr
import edge_tts
import pygame
import geocoder


# =====================
# PFADE
# =====================
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(APP_DIR, "config.json")
MEMORY_FILE = os.path.join(APP_DIR, "memory.json")
NOTES_FILE = os.path.join(APP_DIR, "notes.json")
TODO_FILE = os.path.join(APP_DIR, "todo.json")


# =====================
# JSON HELPERS
# =====================
def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# =====================
# KONFIGURATION
# =====================
config = load_json(CONFIG_FILE)

if "groq_api_key" not in config:
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        key = input("Groq API-Key (einmalig, wird gespeichert): ").strip()
    if not key:
        print("FEHLER: Kein API-Key!")
        input("Enter zum Beenden...")
        sys.exit(1)
    config["groq_api_key"] = key
    save_json(CONFIG_FILE, config)
    print("API-Key gespeichert.")

API_KEY = config["groq_api_key"]
client = Groq(api_key=API_KEY)

if "assistant_name" not in config:
    name = input("Name deines Assistenten (einmalig): ").strip()
    if not name:
        name = "Jarvis"
    config["assistant_name"] = name
    save_json(CONFIG_FILE, config)
    print(f"Name gespeichert: {name}")

assistant_name = config["assistant_name"]
print(f"Assistent: {assistant_name}")

VOICE = "de-DE-ConradNeural"

pygame.mixer.init()


# =====================
# SPEECH ENGINE
# =====================
recognizer = sr.Recognizer()
is_speaking = False


def speak(text):
    global is_speaking
    clean = text.split("[TOOL:")[0].strip() if "[TOOL:" in text else text
    if not clean:
        clean = "Erledigt."
    print(f"\n{assistant_name}: {clean}")
    try:
        is_speaking = True
        tmp = os.path.join(tempfile.gettempdir(), "assistant_tts.mp3")
        asyncio.run(_generate_speech(clean, tmp))
        pygame.mixer.music.load(tmp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
        try:
            os.remove(tmp)
        except:
            pass
    except Exception as e:
        print(f"  [TTS Fehler: {e}]")
    finally:
        is_speaking = False


async def _generate_speech(text, output_file):
    communicate = edge_tts.Communicate(text, VOICE, rate="+0%", pitch="-5Hz")
    await communicate.save(output_file)


def listen():
    if is_speaking:
        return ""
    with sr.Microphone() as source:
        print("... höre zu ...")
        recognizer.adjust_for_ambient_noise(source, duration=0.3)
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8
        try:
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=15)
        except sr.WaitTimeoutError:
            return ""
    try:
        text = recognizer.recognize_google(audio, language="de-DE")
        print(f"Du: {text}")
        return text.lower()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        print(f"Speech-API Fehler: {e}")
        return ""


# =====================
# MEMORY
# =====================
memory = load_json(MEMORY_FILE) if os.path.exists(MEMORY_FILE) else {}


def update_memory(text):
    triggers = {
        "mein name ist": "user_name",
        "ich mag": "likes",
        "ich hasse": "dislikes",
        "ich wohne in": "wohnort",
        "ich arbeite bei": "arbeitgeber",
        "ich bin": "status",
    }
    for trigger, key in triggers.items():
        if trigger in text:
            value = text.split(trigger)[-1].strip().rstrip(".")
            if value:
                memory[key] = value
                save_json(MEMORY_FILE, memory)
                return f"Gemerkt: {key} = {value}"
    return None


# =====================
# NOTIZEN & TO-DO
# =====================
def load_notes():
    return load_json(NOTES_FILE) if os.path.exists(NOTES_FILE) else {"notes": []}


def load_todos():
    return load_json(TODO_FILE) if os.path.exists(TODO_FILE) else {"todos": []}


def handle_notes(text):
    notes_data = load_notes()

    match = re.search(r"(?:merke?|notiz|notiere|schreib auf|merk dir)[:\s]+(.+)", text)
    if match:
        note = match.group(1).strip().rstrip(".")
        notes_data["notes"].append({
            "text": note,
            "time": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        })
        save_json(NOTES_FILE, notes_data)
        return f"Notiert: {note}", True

    if any(w in text for w in ["notizen zeigen", "meine notizen", "alle notizen", "was habe ich notiert"]):
        if not notes_data["notes"]:
            return "Du hast keine Notizen.", True
        result = "Deine Notizen: "
        for i, n in enumerate(notes_data["notes"], 1):
            result += f"{i}. {n['text']}. "
        return result, True

    if any(w in text for w in ["notizen löschen", "alle notizen löschen"]):
        notes_data["notes"] = []
        save_json(NOTES_FILE, notes_data)
        return "Alle Notizen gelöscht.", True

    return None, False


def handle_todos(text):
    todo_data = load_todos()

    match = re.search(r"(?:todo|to do|aufgabe|auf die liste)[:\s]+(.+)", text)
    if not match:
        match = re.search(r"(?:ich muss noch|ich muss)\s+(.+)", text)
    if match:
        todo = match.group(1).strip().rstrip(".")
        todo_data["todos"].append({
            "text": todo,
            "done": False,
            "time": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        })
        save_json(TODO_FILE, todo_data)
        return f"Auf die Liste: {todo}", True

    if any(w in text for w in ["todo liste", "to do liste", "meine aufgaben", "meine todos", "was muss ich"]):
        open_todos = [t for t in todo_data["todos"] if not t["done"]]
        if not open_todos:
            return "Deine To-Do Liste ist leer.", True
        result = "Deine Aufgaben: "
        for i, t in enumerate(open_todos, 1):
            result += f"{i}. {t['text']}. "
        return result, True

    match = re.search(r"(?:aufgabe|todo|to do)\s+(\d+)\s+(?:erledigt|fertig|abhaken|done)", text)
    if match:
        idx = int(match.group(1)) - 1
        open_todos = [t for t in todo_data["todos"] if not t["done"]]
        if 0 <= idx < len(open_todos):
            open_todos[idx]["done"] = True
            save_json(TODO_FILE, todo_data)
            return f"Erledigt: {open_todos[idx]['text']}", True
        return "Diese Aufgabe gibt es nicht.", True

    if any(w in text for w in ["todos löschen", "to do liste löschen", "aufgaben löschen"]):
        todo_data["todos"] = []
        save_json(TODO_FILE, todo_data)
        return "To-Do Liste gelöscht.", True

    return None, False


# =====================
# TIMER & ERINNERUNGEN
# =====================
def handle_timer(text):
    match = re.search(r"timer\s*(?:auf|von|für)?\s*(\d+)\s*(sekunde|minute|stunde)", text)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        if "minute" in unit:
            seconds = amount * 60
            label = f"{amount} Minuten"
        elif "stunde" in unit:
            seconds = amount * 3600
            label = f"{amount} Stunden"
        else:
            seconds = amount
            label = f"{amount} Sekunden"

        def timer_thread():
            time.sleep(seconds)
            speak(f"Timer abgelaufen! {label} sind um.")

        t = threading.Thread(target=timer_thread, daemon=True)
        t.start()
        return f"Timer gestellt auf {label}.", True

    return None, False


def handle_reminder(text):
    match = re.search(r"erinner\w*\s+(?:mich\s+)?um\s+(\d{1,2})(?::(\d{2}))?\s*(?:uhr\s+)?(?:an\s+)?(.+)", text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        task = match.group(3).strip().rstrip(".")

        now = datetime.datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += datetime.timedelta(days=1)

        wait_seconds = (target - now).total_seconds()

        def reminder_thread():
            time.sleep(wait_seconds)
            speak(f"Erinnerung: {task}")

        t = threading.Thread(target=reminder_thread, daemon=True)
        t.start()
        return f"Erinnerung gesetzt für {hour:02d}:{minute:02d} Uhr: {task}", True

    return None, False


# =====================
# WETTER (Open-Meteo)
# =====================
WMO_CODES = {
    0: "klarer Himmel", 1: "überwiegend klar", 2: "teilweise bewölkt", 3: "bewölkt",
    45: "Nebel", 48: "Reifnebel",
    51: "leichter Nieselregen", 53: "Nieselregen", 55: "starker Nieselregen",
    61: "leichter Regen", 63: "Regen", 65: "starker Regen",
    66: "gefrierender Regen", 67: "starker gefrierender Regen",
    71: "leichter Schneefall", 73: "Schneefall", 75: "starker Schneefall",
    77: "Schneekörner",
    80: "leichte Regenschauer", 81: "Regenschauer", 82: "starke Regenschauer",
    85: "leichte Schneeschauer", 86: "starke Schneeschauer",
    95: "Gewitter", 96: "Gewitter mit Hagel", 99: "Gewitter mit starkem Hagel",
}


def get_coordinates(city):
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=de"
        r = requests.get(url, timeout=5)
        data = r.json()
        if "results" in data and data["results"]:
            result = data["results"][0]
            return result["latitude"], result["longitude"], result.get("name", city)
    except:
        pass
    return None, None, city


def handle_weather(text):
    match = re.search(r"wetter\s*(?:in|für|von)?\s*(.+)", text)
    if match:
        city = match.group(1).strip().rstrip(".")
    else:
        city = memory.get("wohnort", "Berlin")

    lat, lon, resolved_name = get_coordinates(city)
    if lat is None:
        return f"Konnte {city} nicht finden.", True

    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
            f"weather_code,wind_speed_10m"
            f"&timezone=auto"
        )
        r = requests.get(url, timeout=5)
        data = r.json()
        current = data["current"]

        temp = round(current["temperature_2m"])
        feels = round(current["apparent_temperature"])
        humidity = current["relative_humidity_2m"]
        wind = round(current["wind_speed_10m"])
        desc = WMO_CODES.get(current["weather_code"], "unbekannt")

        return (
            f"Wetter in {resolved_name}: {desc}, {temp} Grad, "
            f"fühlt sich an wie {feels} Grad. "
            f"Luftfeuchtigkeit {humidity} Prozent, Wind {wind} Kilometer pro Stunde."
        ), True

    except Exception as e:
        return f"Wetter-Fehler: {e}", True


# =====================
# MUSIK-STEUERUNG
# =====================
def handle_music(text):
    try:
        import ctypes
        VK_MEDIA_PLAY_PAUSE = 0xB3
        VK_MEDIA_NEXT = 0xB0
        VK_MEDIA_PREV = 0xB1
        KEYEVENTF_EXTENDEDKEY = 0x0001
        KEYEVENTF_KEYUP = 0x0002

        def press_key(vk):
            ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY, 0)
            ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)

        if any(w in text for w in ["pause", "pausieren", "stopp musik", "musik stopp", "anhalten"]):
            press_key(VK_MEDIA_PLAY_PAUSE)
            return "Musik pausiert.", True

        if any(w in text for w in ["play", "abspielen", "weiter", "musik weiter", "fortsetzen"]):
            press_key(VK_MEDIA_PLAY_PAUSE)
            return "Musik wird abgespielt.", True

        if any(w in text for w in ["nächster song", "nächstes lied", "skip", "überspringen", "weiter song"]):
            press_key(VK_MEDIA_NEXT)
            return "Nächster Song.", True

        if any(w in text for w in ["vorheriger song", "vorheriges lied", "lied zurück", "song zurück"]):
            press_key(VK_MEDIA_PREV)
            return "Vorheriger Song.", True

    except Exception as e:
        return f"Musik-Steuerung Fehler: {e}", True

    return None, False


# =====================
# LAUTSTÄRKE
# =====================
def handle_volume(text):
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))

        current = volume.GetMasterVolumeLevelScalar()

        if any(w in text for w in ["lauter", "laut", "volume up", "ton hoch"]):
            new_vol = min(1.0, current + 0.1)
            volume.SetMasterVolumeLevelScalar(new_vol, None)
            return f"Lautstärke auf {int(new_vol * 100)} Prozent.", True

        if any(w in text for w in ["leiser", "ton runter", "volume down", "ton leiser"]):
            new_vol = max(0.0, current - 0.1)
            volume.SetMasterVolumeLevelScalar(new_vol, None)
            return f"Lautstärke auf {int(new_vol * 100)} Prozent.", True

        if any(w in text for w in ["stumm", "mute", "ton aus"]):
            volume.SetMasterVolumeLevelScalar(0.0, None)
            return "Ton ist stumm.", True

        if any(w in text for w in ["ton an", "unmute", "laut machen"]):
            volume.SetMasterVolumeLevelScalar(0.5, None)
            return "Ton ist wieder an, 50 Prozent.", True

        match = re.search(r"lautstärke\s*(?:auf)?\s*(\d+)", text)
        if match:
            level = max(0, min(100, int(match.group(1))))
            volume.SetMasterVolumeLevelScalar(level / 100, None)
            return f"Lautstärke auf {level} Prozent.", True

    except Exception as e:
        return f"Lautstärke-Fehler: {e}", True

    return None, False


# =====================
# RECHNEN
# =====================
def handle_math(text):
    match = re.search(r"(?:was ist|berechne|rechne|wie viel ist)\s+(.+)", text)
    if not match:
        return None, False

    expr = match.group(1).strip().rstrip(".")
    expr = expr.replace("mal", "*").replace("x", "*")
    expr = expr.replace("plus", "+").replace("und", "+")
    expr = expr.replace("minus", "-").replace("weniger", "-")
    expr = expr.replace("geteilt durch", "/").replace("durch", "/")
    expr = expr.replace("hoch", "**")
    expr = expr.replace(",", ".")

    safe = re.sub(r"[^0-9+\-*/.()\s]", "", expr)
    if not safe.strip():
        return None, False

    try:
        result = eval(safe, {"__builtins__": {}})
        if isinstance(result, float):
            result = round(result, 4)
        return f"Das Ergebnis ist {result}.", True
    except Exception:
        return None, False


# =====================
# PC-STEUERUNG
# =====================
def handle_pc(text):
    if any(w in text for w in ["herunterfahren", "pc aus", "computer ausschalten", "shutdown"]):
        speak("PC wird in 10 Sekunden heruntergefahren. Sage abbrechen zum Stoppen.")

        def shutdown_thread():
            if sys.platform == "win32":
                os.system("shutdown /s /t 10")
            else:
                os.system("shutdown -h +0")

        t = threading.Thread(target=shutdown_thread, daemon=True)
        t.start()
        return None, True

    if any(w in text for w in ["neustart", "pc neustarten", "computer neustarten", "restart"]):
        speak("PC wird in 10 Sekunden neugestartet.")

        def restart_thread():
            if sys.platform == "win32":
                os.system("shutdown /r /t 10")
            else:
                os.system("shutdown -r +0")

        t = threading.Thread(target=restart_thread, daemon=True)
        t.start()
        return None, True

    if any(w in text for w in ["shutdown abbrechen", "abbrechen", "nicht herunterfahren"]):
        os.system("shutdown /a")
        return "Herunterfahren abgebrochen.", True

    return None, False


# =====================
# BEKANNTE APPS & URLS
# =====================
KNOWN_APPS = {
    "discord": "discord", "spotify": "spotify", "steam": "steam",
    "chrome": "chrome", "firefox": "firefox", "edge": "msedge",
    "notepad": "notepad", "rechner": "calc", "taschenrechner": "calc",
    "explorer": "explorer", "terminal": "wt", "cmd": "cmd",
    "word": "winword", "excel": "excel", "powerpoint": "powerpnt",
    "teams": "ms-teams", "outlook": "outlook", "paint": "mspaint",
    "vlc": "vlc", "obs": "obs64", "vscode": "code", "vs code": "code",
    "visual studio code": "code", "telegram": "telegram",
    "whatsapp": "whatsapp", "epic games": "com.epicgames.launcher:",
    "minecraft": "minecraft",
}

KNOWN_URLS = {
    "amar": "https://www.twitch.tv/amar",
    "montanablack": "https://www.twitch.tv/montanablack88",
    "trymacs": "https://www.twitch.tv/trymacs",
    "elotrix": "https://www.twitch.tv/elotrix",
    "gronkh": "https://www.twitch.tv/gronkh",
    "papaplatte": "https://www.twitch.tv/papaplatte",
    "knossi": "https://www.twitch.tv/therealknossi",
    "unsympathisch": "https://www.twitch.tv/unsympathischtv",
    "reved": "https://www.twitch.tv/reved",
    "youtube": "https://www.youtube.com",
    "twitch": "https://www.twitch.tv",
    "twitter": "https://www.twitter.com",
    "x": "https://www.x.com",
    "instagram": "https://www.instagram.com",
    "tiktok": "https://www.tiktok.com",
    "reddit": "https://www.reddit.com",
    "github": "https://www.github.com",
    "google": "https://www.google.com",
    "chatgpt": "https://chat.openai.com",
    "netflix": "https://www.netflix.com",
    "amazon": "https://www.amazon.de",
    "disney plus": "https://www.disneyplus.com",
    "disney+": "https://www.disneyplus.com",
    "prime video": "https://www.primevideo.com",
}


# =====================
# LOKALE BEFEHLE
# =====================
def handle_local(user_input):
    text = user_input.lower().strip()

    if any(w in text for w in ["wie spät", "uhrzeit", "wieviel uhr"]):
        now = datetime.datetime.now().strftime("%H:%M")
        return f"Es ist {now} Uhr.", True

    if any(w in text for w in ["welcher tag", "welches datum", "datum heute"]):
        now = datetime.datetime.now()
        tage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        return f"Heute ist {tage[now.weekday()]}, der {now.strftime('%d.%m.%Y')}.", True

    if "wetter" in text:
        return handle_weather(text)

    if "timer" in text:
        return handle_timer(text)

    if "erinner" in text:
        return handle_reminder(text)

    if any(w in text for w in ["merke", "merk", "notiz", "notiere", "schreib auf", "notizen"]):
        return handle_notes(text)

    if any(w in text for w in ["todo", "to do", "aufgabe", "auf die liste", "ich muss"]):
        return handle_todos(text)

    if any(w in text for w in ["pause", "play", "abspielen", "skip", "nächster song",
                                "nächstes lied", "überspringen", "vorheriger song",
                                "weiter song", "song zurück", "musik"]):
        result, handled = handle_music(text)
        if handled:
            return result, True

    if any(w in text for w in ["lauter", "leiser", "stumm", "mute", "unmute",
                                "ton", "lautstärke", "volume"]):
        result, handled = handle_volume(text)
        if handled:
            return result, True

    if any(w in text for w in ["was ist", "berechne", "rechne", "wie viel ist"]):
        result, handled = handle_math(text)
        if handled:
            return result, True

    if any(w in text for w in ["herunterfahren", "shutdown", "neustart", "restart",
                                "pc aus", "computer aus", "abbrechen"]):
        return handle_pc(text)

    if text.startswith("öffne") or text.startswith("starte") or text.startswith("mach"):

        twitch_match = re.search(r"(?:öffne|starte|mach)\s+(.+?)\s+(?:auf|in|bei)\s+twitch", text)
        if twitch_match:
            streamer = twitch_match.group(1).strip()
            url = KNOWN_URLS.get(streamer, f"https://www.twitch.tv/{streamer}")
            webbrowser.open(url)
            return f"{streamer.title()} auf Twitch wird geöffnet.", True

        yt_match = re.search(r"(?:öffne|starte|mach)\s+(.+?)\s+(?:auf|in|bei)\s+youtube", text)
        if yt_match:
            kanal = yt_match.group(1).strip().replace(" ", "+")
            webbrowser.open(f"https://www.youtube.com/results?search_query={kanal}")
            return f"{yt_match.group(1).title()} auf YouTube wird gesucht.", True

        target = text.replace("öffne", "").replace("starte", "").replace("mach", "")
        target = target.replace("an", "").replace("auf", "").strip()

        if target in KNOWN_URLS:
            webbrowser.open(KNOWN_URLS[target])
            return f"{target.title()} wird geöffnet.", True

        if target in KNOWN_APPS:
            cmd = KNOWN_APPS[target]
            try:
                if sys.platform == "win32":
                    subprocess.Popen(f"start {cmd}", shell=True)
                return f"{target.title()} wird geöffnet.", True
            except Exception as e:
                return f"Fehler beim Öffnen von {target}: {e}", True

    search_match = re.search(r"(?:such|google|suche)\s*(?:nach|mal|mir)?\s+(.+)", text)
    if search_match:
        query = search_match.group(1).strip()
        webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        return f"{query} wird gesucht.", True

    return None, False


# =====================
# TOOLS (Fallback für KI)
# =====================
def run_tool(name, arg):
    name = name.strip().lower()
    arg = arg.strip()

    if name == "open_url":
        shortcut = arg.lower().strip()
        url = KNOWN_URLS.get(shortcut, arg)
        if not url.startswith("http"):
            url = f"https://www.{url}"
        webbrowser.open(url)
        return f"URL geöffnet: {url}"

    elif name == "open_app":
        app = arg.lower().strip()
        if app in KNOWN_URLS:
            webbrowser.open(KNOWN_URLS[app])
            return f"URL geöffnet: {KNOWN_URLS[app]}"
        cmd = KNOWN_APPS.get(app, app)
        try:
            if sys.platform == "win32":
                subprocess.Popen(f"start {cmd}", shell=True)
            return f"App gestartet: {arg}"
        except Exception as e:
            return f"Fehler: {e}"

    elif name == "search_web":
        webbrowser.open(f"https://www.google.com/search?q={arg.replace(' ', '+')}")
        return f"Suche: {arg}"

    elif name == "get_time":
        return datetime.datetime.now().strftime("%H:%M")

    elif name == "get_date":
        now = datetime.datetime.now()
        tage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        return f"{tage[now.weekday()]}, {now.strftime('%d.%m.%Y')}"

    return f"Unbekanntes Tool: {name}"


def extract_tool(text):
    if "[TOOL:" not in text:
        return None, None
    try:
        part = text.split("[TOOL:")[1].split("]")[0]
        if "|" in part:
            name, arg = part.split("|", 1)
            return name.strip(), arg.strip()
        else:
            return part.strip(), ""
    except (IndexError, ValueError):
        return None, None


# =====================
# CHAT HISTORY
# =====================
chat_history = []
MAX_HISTORY = 20


def add_to_history(role, content):
    chat_history.append({"role": role, "content": content})
    while len(chat_history) > MAX_HISTORY:
        chat_history.pop(0)


# =====================
# SYSTEM PROMPT
# =====================
def build_prompt(name, mem):
    memory_text = "\n".join([f"- {k}: {v}" for k, v in mem.items()])
    if not memory_text:
        memory_text = "Noch keine Infos gespeichert."

    now = datetime.datetime.now()
    tage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

    return f"""Du bist {name}, ein intelligenter persönlicher KI-Assistent.

IDENTITÄT:
- Du sprichst immer als {name}
- Du bist präzise, effizient und leicht sarkastisch
- Keine Emojis, keine unnötigen Erklärungen
- Antworte auf Deutsch
- Deine Antworten werden vorgelesen, also schreibe natürlich und aussprechbar

AKTUELLE ZEIT: {now.strftime("%H:%M")}
AKTUELLES DATUM: {tage[now.weekday()]}, {now.strftime("%d.%m.%Y")}

BEKANNTE INFOS ÜBER DEN NUTZER:
{memory_text}

Du wirst nur für Fragen aufgerufen die nicht lokal gelöst werden können.
Beantworte Fragen kurz und präzise (1-3 Sätze).
Sei hilfreich, witzig wenn passend, und leicht sarkastisch.
"""


# =====================
# HAUPTSCHLEIFE
# =====================
def main():
    print(f"\n{'='*50}")
    print(f"  {assistant_name} ist bereit.")
    print(f"  Sprich einfach – kein Wake-Word nötig.")
    print(f"  Sage 'beenden' zum Stoppen.")
    print(f"{'='*50}\n")

    speak(f"{assistant_name} ist online. Ich höre zu.")

    while True:
        try:
            user_input = listen()

            if not user_input:
                continue

            # Beenden
            if user_input.strip() in ["beenden", "stopp", "exit", "tschüss", "auf wiedersehen"]:
                speak("Bis dann.")
                break

            # Memory prüfen
            mem_result = update_memory(user_input)
            if mem_result:
                speak(mem_result)
                continue

            # Lokal versuchen
            local_answer, handled = handle_local(user_input)
            if handled:
                if local_answer:
                    speak(local_answer)
                add_to_history("user", user_input)
                add_to_history("assistant", local_answer or "Erledigt.")
                continue

            # KI fragen
            messages = [
                {"role": "system", "content": build_prompt(assistant_name, memory)}
            ] + chat_history + [
                {"role": "user", "content": user_input}
            ]

            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    max_tokens=300,
                    temperature=0.7,
                )
                answer = response.choices[0].message.content
            except Exception as e:
                speak(f"API-Fehler: {e}")
                continue

            tool_name, tool_arg = extract_tool(answer)
            if tool_name:
                result = run_tool(tool_name, tool_arg)
                print(f"  [Tool: {tool_name} → {result}]")
                clean_answer = answer.split("[TOOL:")[0].strip()
                if tool_name == "get_time":
                    speak(f"Es ist {result} Uhr.")
                elif tool_name == "get_date":
                    speak(f"Heute ist {result}.")
                elif clean_answer:
                    speak(clean_answer)
                else:
                    speak("Erledigt.")
            else:
                speak(answer)

            add_to_history("user", user_input)
            add_to_history("assistant", answer)

        except KeyboardInterrupt:
            speak("Tschüss.")
            break


if __name__ == "__main__":
    main()