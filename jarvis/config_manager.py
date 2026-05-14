"""
Konfiguration & Einstellungen – einmalige Abfragen, persistente Speicherung.
"""

import json
import os
import sys

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(APP_DIR, "config.json")


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def setup():
    config = load_config()

    if "groq_api_key" not in config:
        key = os.getenv("GROQ_API_KEY", "")
        if not key:
            key = input("Groq API-Key (einmalig): ").strip()
        if not key:
            print("FEHLER: Kein API-Key!")
            input("Enter zum Beenden...")
            sys.exit(1)
        config["groq_api_key"] = key
        save_config(config)
        print("API-Key gespeichert.")

    if "assistant_name" not in config:
        name = input("Name deines Assistenten (einmalig): ").strip()
        if not name:
            name = "Jarvis"
        config["assistant_name"] = name
        save_config(config)
        print(f"Name gespeichert: {name}")

    if "home_assistant_url" not in config:
        print("\nSmart Home Setup (optional, Enter zum Überspringen):")
        ha_url = input("Home Assistant URL (z.B. http://192.168.1.100:8123): ").strip()
        ha_token = ""
        if ha_url:
            ha_token = input("Home Assistant Token: ").strip()
        config["home_assistant_url"] = ha_url
        config["home_assistant_token"] = ha_token
        save_config(config)
        if ha_url:
            print("Smart Home konfiguriert.")
        else:
            print("Smart Home übersprungen.")

    return config