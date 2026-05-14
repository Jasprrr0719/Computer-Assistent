"""
Konfiguration – fragt beim ersten Start nach allen APIs.
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


def _ask_gui(title, prompt, hide=False):
    try:
        import tkinter as tk
        from tkinter import simpledialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        if hide:
            result = simpledialog.askstring(title, prompt, show='*', parent=root)
        else:
            result = simpledialog.askstring(title, prompt, parent=root)
        root.destroy()
        return result.strip() if result else ""
    except Exception:
        try:
            return input(prompt).strip()
        except:
            return ""


def _ask_yesno(title, prompt):
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        result = messagebox.askyesno(title, prompt, parent=root)
        root.destroy()
        return result
    except:
        return False


def _show_info(title, message):
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        messagebox.showinfo(title, message, parent=root)
        root.destroy()
    except:
        print(message)


def setup():
    config = load_config()
    first_run = "groq_api_key" not in config

    if first_run:
        _show_info("Willkommen", 
            "Willkommen beim Computer-Assistenten!\n\n"
            "Im nächsten Schritt werden ein paar API-Keys abgefragt.\n"
            "Pflicht ist nur der Groq-Key.\n"
            "Alles andere ist optional – einfach leer lassen zum Überspringen.")

    # === PFLICHT: Groq API Key ===
    if "groq_api_key" not in config:
        key = os.getenv("GROQ_API_KEY", "")
        if not key:
            key = _ask_gui("1/7 – KI-Engine (PFLICHT)",
                "Groq API-Key eingeben:\n\n"
                "Kostenlos von: https://console.groq.com/keys\n\n"
                "Ohne diesen Key funktioniert nichts!", hide=True)
        if not key:
            _show_info("Fehler", "Kein API-Key eingegeben. Programm wird beendet.")
            sys.exit(1)
        config["groq_api_key"] = key
        save_config(config)

    # === PFLICHT: Name ===
    if "assistant_name" not in config:
        name = _ask_gui("2/7 – Name",
            "Name deines Assistenten:\n\n"
            "(z.B. Computer, Jarvis, Atlas)")
        if not name:
            name = "Computer"
        config["assistant_name"] = name
        save_config(config)

    # === OPTIONAL: Govee Smart Home ===
    if "govee_api_key" not in config:
        if _ask_yesno("3/7 – Smart Home (optional)",
            "Hast du Govee Smart Home Geräte?\n\n"
            "Damit kannst du per Sprache Lichter steuern."):
            govee_key = _ask_gui("Govee Setup",
                "Govee API-Key eingeben:\n\n"
                "Govee App → Profil → Einstellungen → API-Verwaltung", hide=True)
            config["govee_api_key"] = govee_key if govee_key else ""
        else:
            config["govee_api_key"] = ""
        save_config(config)

    # === OPTIONAL: Email ===
    if "email_user" not in config:
        if _ask_yesno("4/7 – Email (optional)",
            "Email-Integration einrichten?\n\n"
            "Damit kannst du Emails senden und empfangen per Sprache.\n"
            "Funktioniert mit Gmail, Outlook, GMX, Web.de"):
            email_user = _ask_gui("Email Setup", "Email-Adresse:")
            email_pass = _ask_gui("Email Setup",
                "Email App-Passwort:\n\n"
                "Gmail: Google Account → Sicherheit → App-Passwörter\n"
                "Outlook: Account → Sicherheit → App-Passwort erstellen", hide=True)
            # Provider erkennen
            provider = "gmail"
            if email_user:
                if "outlook" in email_user or "hotmail" in email_user or "live" in email_user:
                    provider = "outlook"
                elif "gmx" in email_user:
                    provider = "gmx"
                elif "web.de" in email_user:
                    provider = "web.de"
            config["email_user"] = email_user or ""
            config["email_pass"] = email_pass or ""
            config["email_provider"] = provider
        else:
            config["email_user"] = ""
            config["email_pass"] = ""
            config["email_provider"] = ""
        save_config(config)

    # === OPTIONAL: Discord Bot ===
    if "discord_token" not in config:
        if _ask_yesno("5/7 – Discord Bot (optional)",
            "Discord Bot einrichten?\n\n"
            "Damit kann der Assistent Discord-Nachrichten lesen und senden.\n\n"
            "Du brauchst einen Bot-Token von:\n"
            "https://discord.com/developers/applications"):
            token = _ask_gui("Discord Setup",
                "Discord Bot Token eingeben:", hide=True)
            config["discord_token"] = token if token else ""
        else:
            config["discord_token"] = ""
        save_config(config)

    # === OPTIONAL: WhatsApp Kontakte ===
    if first_run and "whatsapp_setup_done" not in config:
        if _ask_yesno("6/7 – WhatsApp (optional)",
            "WhatsApp-Kontakte einrichten?\n\n"
            "Du kannst später per Sprache Kontakte hinzufügen:\n"
            "\"Kontakt speichern Max +4917612345678\""):
            _show_info("WhatsApp",
                "WhatsApp funktioniert über WhatsApp Web.\n\n"
                "Sage einfach:\n"
                "\"Kontakt speichern Max +4917612345678\"\n"
                "\"Schreib Max auf WhatsApp hey wie gehts\"")
        config["whatsapp_setup_done"] = True
        save_config(config)

    # === OPTIONAL: Wohnort für Wetter ===
    if "default_city" not in config:
        city = _ask_gui("7/7 – Standort (optional)",
            "Dein Wohnort für Wetter-Abfragen:\n\n"
            "(z.B. Hamburg, Berlin, München)\n"
            "Leer lassen für Berlin als Standard")
        config["default_city"] = city if city else "Berlin"
        save_config(config)

    # Setup abgeschlossen
    if first_run:
        _show_info("Fertig!",
            f"Setup abgeschlossen!\n\n"
            f"Name: {config.get('assistant_name', 'Computer')}\n"
            f"KI: {'✓' if config.get('groq_api_key') else '✗'}\n"
            f"Smart Home: {'✓' if config.get('govee_api_key') else '✗'}\n"
            f"Email: {'✓' if config.get('email_user') else '✗'}\n"
            f"Discord: {'✓' if config.get('discord_token') else '✗'}\n"
            f"WhatsApp: ✓ (über WhatsApp Web)\n\n"
            f"Du kannst alles später in config.json ändern.")

    return config