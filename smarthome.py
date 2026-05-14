"""
Smart Home – Govee API mit Timer und Wecker.
"""

import requests
import re
import os
import sys
import threading
import time
import datetime
from config_manager import load_config, save_config, APP_DIR


class SmartHome:
    def __init__(self, **kwargs):
        config = load_config()
        self.api_key = config.get("govee_api_key", "")
        self.enabled = bool(self.api_key)
        self.base_url = "https://developer-api.govee.com/v1"
        self._speak_callback = None

        self.devices = config.get("govee_devices", {
            "hexagons": {
                "device": "36:19:D0:05:C0:46:61:8F",
                "model": "H6061",
                "name": "Bed Led",
            },
        })

        self.aliases = {
            "licht": "hexagons", "lichter": "hexagons", "lampe": "hexagons",
            "led": "hexagons", "leds": "hexagons", "hexagon": "hexagons",
            "hexagons": "hexagons", "bed led": "hexagons", "schlafzimmer": "hexagons",
            "zimmer": "hexagons", "alles": "hexagons",
        }

        self.colors = {
            "rot": {"r": 255, "g": 0, "b": 0},
            "grün": {"r": 0, "g": 255, "b": 0},
            "blau": {"r": 0, "g": 0, "b": 255},
            "gelb": {"r": 255, "g": 255, "b": 0},
            "lila": {"r": 128, "g": 0, "b": 255},
            "violett": {"r": 128, "g": 0, "b": 255},
            "pink": {"r": 255, "g": 105, "b": 180},
            "orange": {"r": 255, "g": 165, "b": 0},
            "weiß": {"r": 255, "g": 255, "b": 255},
            "warm": {"r": 255, "g": 180, "b": 100},
            "warmweiß": {"r": 255, "g": 180, "b": 100},
            "kalt": {"r": 200, "g": 220, "b": 255},
            "kaltweiß": {"r": 200, "g": 220, "b": 255},
            "türkis": {"r": 0, "g": 255, "b": 255},
            "cyan": {"r": 0, "g": 255, "b": 255},
            "magenta": {"r": 255, "g": 0, "b": 255},
            "gold": {"r": 255, "g": 215, "b": 0},
        }

        self.mood_presets = {
            "gaming": [{"r": 255, "g": 0, "b": 0}],
            "chill": [{"r": 255, "g": 180, "b": 100}],
            "party": [{"r": 128, "g": 0, "b": 255}],
            "focus": [{"r": 200, "g": 220, "b": 255}],
            "romance": [{"r": 255, "g": 50, "b": 100}],
            "nacht": [{"r": 255, "g": 100, "b": 0}],
            "film": [{"r": 30, "g": 0, "b": 80}],
        }

    def set_speak_callback(self, callback):
        self._speak_callback = callback

    def _get_headers(self):
        return {"Govee-API-Key": self.api_key, "Content-Type": "application/json"}

    def _send_command(self, device_key, cmd_name, cmd_value):
        if not self.enabled:
            return "Smart Home nicht konfiguriert, Boss."
        device = self.devices.get(device_key)
        if not device:
            return f"Gerät '{device_key}' nicht gefunden, Boss."
        payload = {
            "device": device["device"],
            "model": device["model"],
            "cmd": {"name": cmd_name, "value": cmd_value}
        }
        try:
            r = requests.put(f"{self.base_url}/devices/control", json=payload,
                           headers=self._get_headers(), timeout=5)
            if r.status_code == 200:
                return None
            else:
                return f"Govee Fehler: {r.json().get('message', r.status_code)}"
        except requests.ConnectionError:
            return "Keine Internetverbindung, Boss."
        except Exception as e:
            return f"Govee Fehler: {e}"

    def _resolve_device(self, text):
        for alias, device_key in self.aliases.items():
            if alias in text.lower():
                return device_key
        return "hexagons"

    def handle(self, text):
        text = text.lower().strip()

        is_smart = any(w in text for w in [
            "licht", "lichter", "lampe", "led", "leds", "hexagon", "hexagons",
            "hell", "dunkel", "dimm", "farbe", "color"
        ])
        if not is_smart:
            return None, False
        if not self.enabled:
            return "Smart Home nicht konfiguriert, Boss.", True

        device_key = self._resolve_device(text)
        device = self.devices.get(device_key, {})
        device_name = device.get("name", device_key)

        # --- Licht-Timer: "licht aus in 30 minuten" ---
        timer_match = re.search(r"licht\s*(?:aus|an)\s*(?:in|nach)\s*(\d+)\s*(sekunde|minute|stunde)", text)
        if timer_match:
            amount = int(timer_match.group(1))
            unit = timer_match.group(2)
            action = "off" if "aus" in text else "on"
            seconds = amount * (3600 if "stunde" in unit else 60 if "minute" in unit else 1)
            label = f"{amount} {'Stunden' if 'stunde' in unit else 'Minuten' if 'minute' in unit else 'Sekunden'}"

            def timer_thread():
                time.sleep(seconds)
                self._send_command(device_key, "turn", action)
                if self._speak_callback:
                    msg = f"Boss, {device_name} ist jetzt {'an' if action == 'on' else 'aus'}."
                    self._speak_callback(msg)

            threading.Thread(target=timer_thread, daemon=True).start()
            return f"Verstanden, Boss. {device_name} geht in {label} {'aus' if action == 'off' else 'an'}.", True

        # --- Licht-Wecker: "licht an um 7 uhr" ---
        wecker_match = re.search(r"licht\s*(?:an|aus)\s*(?:um)\s*(\d{1,2})(?::(\d{2}))?\s*(?:uhr)?", text)
        if wecker_match:
            hour = int(wecker_match.group(1))
            minute = int(wecker_match.group(2)) if wecker_match.group(2) else 0
            action = "on" if "an" in text else "off"

            now = datetime.datetime.now()
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += datetime.timedelta(days=1)
            wait = (target - now).total_seconds()

            def wecker_thread():
                time.sleep(wait)
                self._send_command(device_key, "turn", action)
                if action == "on":
                    # Sanftes Aufwachen: erst dunkel dann hell
                    self._send_command(device_key, "brightness", 20)
                    self._send_command(device_key, "color", {"r": 255, "g": 180, "b": 100})
                    time.sleep(30)
                    self._send_command(device_key, "brightness", 50)
                    time.sleep(30)
                    self._send_command(device_key, "brightness", 100)
                if self._speak_callback:
                    msg = f"Boss, {device_name} ist jetzt {'an' if action == 'on' else 'aus'}. Es ist {hour:02d}:{minute:02d} Uhr."
                    self._speak_callback(msg)

            threading.Thread(target=wecker_thread, daemon=True).start()
            return f"Licht-Wecker gesetzt, Boss. {device_name} geht um {hour:02d}:{minute:02d} Uhr {'an' if action == 'on' else 'aus'}.", True

        # --- Stimmungs-Modi ---
        for mood, colors in self.mood_presets.items():
            if mood in text and "licht" in text:
                self._send_command(device_key, "turn", "on")
                self._send_command(device_key, "color", colors[0])
                if mood == "chill" or mood == "romance" or mood == "film" or mood == "nacht":
                    self._send_command(device_key, "brightness", 40)
                elif mood == "gaming" or mood == "party":
                    self._send_command(device_key, "brightness", 80)
                else:
                    self._send_command(device_key, "brightness", 60)
                return f"{mood.title()}-Licht aktiviert, Boss.", True

        # Licht AN
        if any(w in text for w in ["licht an", "lichter an", "lampe an", "led an",
                                    "leds an", "hexagons an", "hexagon an",
                                    "mach licht an", "mach das licht an",
                                    "licht einschalten", "licht anmachen"]):
            error = self._send_command(device_key, "turn", "on")
            if error: return error, True
            return f"{device_name} ist an, Boss.", True

        # Licht AUS
        if any(w in text for w in ["licht aus", "lichter aus", "lampe aus", "led aus",
                                    "leds aus", "hexagons aus", "hexagon aus",
                                    "mach licht aus", "mach das licht aus",
                                    "licht ausschalten", "licht ausmachen",
                                    "alles aus"]):
            error = self._send_command(device_key, "turn", "off")
            if error: return error, True
            return f"{device_name} ist aus, Boss.", True

        # Farbe
        for color_name, rgb in self.colors.items():
            if color_name in text:
                self._send_command(device_key, "turn", "on")
                error = self._send_command(device_key, "color", rgb)
                if error: return error, True
                return f"{device_name} ist jetzt {color_name}, Boss.", True

        # Helligkeit Prozent
        brightness_match = re.search(r"(\d+)\s*(?:prozent|%)", text)
        if brightness_match:
            level = max(0, min(100, int(brightness_match.group(1))))
            self._send_command(device_key, "turn", "on")
            error = self._send_command(device_key, "brightness", level)
            if error: return error, True
            return f"{device_name} auf {level} Prozent, Boss.", True

        if any(w in text for w in ["heller", "hell"]):
            self._send_command(device_key, "turn", "on")
            error = self._send_command(device_key, "brightness", 80)
            if error: return error, True
            return f"{device_name} heller, Boss.", True

        if any(w in text for w in ["dunkler", "dunkel", "dimm", "dimmen"]):
            self._send_command(device_key, "turn", "on")
            error = self._send_command(device_key, "brightness", 30)
            if error: return error, True
            return f"{device_name} gedimmt, Boss.", True

        return None, False

    def get_states(self):
        if not self.enabled:
            return "Smart Home nicht konfiguriert, Boss."
        results = "Geräte-Status: "
        for key, device in self.devices.items():
            try:
                r = requests.get(f"{self.base_url}/devices/state",
                               params={"device": device["device"], "model": device["model"]},
                               headers=self._get_headers(), timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    props = data.get("data", {}).get("properties", [])
                    power = "Unbekannt"
                    for p in props:
                        if "powerState" in p:
                            power = "An" if p["powerState"] == "on" else "Aus"
                    results += f"{device['name']}: {power}. "
                else:
                    results += f"{device['name']}: Fehler. "
            except Exception as e:
                results += f"{device['name']}: {e}. "
        return results