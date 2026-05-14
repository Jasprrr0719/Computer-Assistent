"""
WhatsApp – Öffnet WhatsApp Web mit vorgefüllter Nachricht.
Nutzt das wa.me URL-Schema. Funktioniert ohne API.
"""

import webbrowser
import re
import json
import os
import sys

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONTACTS_FILE = os.path.join(APP_DIR, "contacts.json")


class WhatsAppTool:
    def __init__(self):
        self.contacts = self._load_contacts()

    def _load_contacts(self):
        if os.path.exists(CONTACTS_FILE):
            with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_contacts(self):
        with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.contacts, f, indent=4, ensure_ascii=False)

    def send_message(self, name="", message="", number=""):
        """Öffnet WhatsApp Web mit vorgefüllter Nachricht."""
        # Kontakt nachschlagen
        if name and not number:
            number = self.contacts.get(name.lower(), "")
            if not number:
                return f"Kontakt '{name}' nicht gefunden. Speichere ihn mit: Kontakt speichern {name} +49..."

        if not number:
            return "Keine Nummer angegeben."

        # Nummer formatieren
        number = re.sub(r"[^0-9+]", "", number)
        if number.startswith("0"):
            number = "+49" + number[1:]
        if not number.startswith("+"):
            number = "+49" + number

        # URL erstellen
        clean_number = number.replace("+", "")
        if message:
            from urllib.parse import quote
            url = f"https://wa.me/{clean_number}?text={quote(message)}"
        else:
            url = f"https://wa.me/{clean_number}"

        webbrowser.open(url)
        return f"WhatsApp an {name or number} wird geöffnet."

    def add_contact(self, name, number):
        """Speichert einen Kontakt."""
        number = re.sub(r"[^0-9+]", "", number)
        if number.startswith("0"):
            number = "+49" + number[1:]
        self.contacts[name.lower()] = number
        self._save_contacts()
        return f"Kontakt '{name}' mit {number} gespeichert."

    def list_contacts(self):
        if not self.contacts:
            return "Keine Kontakte gespeichert."
        result = "Kontakte: "
        for name, number in self.contacts.items():
            result += f"{name.title()}: {number}. "
        return result

    def handle(self, text):
        """Verarbeitet WhatsApp-Befehle aus Spracheingabe."""
        text = text.lower().strip()

        # Kontakt speichern: "kontakt speichern max +4917612345678"
        save_match = re.search(r"kontakt\s+speichern\s+(\w+)\s+(\+?\d[\d\s]+)", text)
        if save_match:
            name = save_match.group(1).strip()
            number = save_match.group(2).strip()
            return self.add_contact(name, number)

        # Kontakte anzeigen
        if any(w in text for w in ["kontakte zeigen", "meine kontakte", "alle kontakte"]):
            return self.list_contacts()

        # Nachricht senden: "schreib max auf whatsapp hey wie gehts"
        # oder "whatsapp an max: hey wie gehts"
        msg_match = re.search(
            r"(?:schreib|schreibe|sende|send|nachricht)\s+(?:an\s+)?(\w+)\s+(?:auf\s+whatsapp|per\s+whatsapp|whatsapp)[\s:]+(.+)",
            text
        )
        if not msg_match:
            msg_match = re.search(
                r"whatsapp\s+(?:an\s+)?(\w+)[\s:]+(.+)",
                text
            )
        if not msg_match:
            msg_match = re.search(
                r"(?:schreib|schreibe)\s+(\w+)\s+(?:auf\s+whatsapp|per\s+whatsapp)[\s:]*(.+)?",
                text
            )

        if msg_match:
            name = msg_match.group(1).strip()
            message = msg_match.group(2).strip() if msg_match.group(2) else ""
            return self.send_message(name=name, message=message)

        # Nur Chat öffnen: "öffne whatsapp mit max"
        open_match = re.search(r"(?:öffne|open)\s+whatsapp\s+(?:mit|von|an)\s+(\w+)", text)
        if open_match:
            name = open_match.group(1).strip()
            return self.send_message(name=name)

        return None