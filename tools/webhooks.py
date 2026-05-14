"""
Webhook-System – Empfängt und sendet Webhooks.
Twitch/Discord Events können Aktionen triggern.
"""

import json
import os
import sys
import threading
import requests
import re
import datetime

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WEBHOOKS_FILE = os.path.join(APP_DIR, "webhooks.json")


class WebhookSystem:
    def __init__(self):
        self.webhooks = self._load()
        self.on_trigger = None  # Callback wenn Webhook ausgelöst wird

    def _load(self):
        if os.path.exists(WEBHOOKS_FILE):
            with open(WEBHOOKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"outgoing": {}, "actions": {}}

    def _save(self):
        with open(WEBHOOKS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.webhooks, f, indent=4, ensure_ascii=False)

    def send_webhook(self, name="", url="", data=None):
        """Sendet einen Webhook an eine URL."""
        if name and name in self.webhooks.get("outgoing", {}):
            url = self.webhooks["outgoing"][name]["url"]

        if not url:
            return f"Webhook '{name}' nicht gefunden."

        try:
            payload = data or {"text": f"Triggered by Computer-Agent at {datetime.datetime.now().strftime('%H:%M')}"}
            r = requests.post(url, json=payload, timeout=10)
            return f"Webhook gesendet. Status: {r.status_code}"
        except Exception as e:
            return f"Webhook-Fehler: {e}"

    def send_discord_webhook(self, url="", message=""):
        """Sendet eine Nachricht über Discord Webhook."""
        if not url:
            url = self.webhooks.get("outgoing", {}).get("discord", {}).get("url", "")
        if not url:
            return "Kein Discord Webhook konfiguriert."

        try:
            payload = {"content": message}
            r = requests.post(url, json=payload, timeout=10)
            if r.status_code in [200, 204]:
                return "Discord Webhook gesendet."
            return f"Discord Webhook Fehler: {r.status_code}"
        except Exception as e:
            return f"Webhook-Fehler: {e}"

    def register_webhook(self, name, url, action=""):
        """Registriert einen neuen ausgehenden Webhook."""
        if "outgoing" not in self.webhooks:
            self.webhooks["outgoing"] = {}
        self.webhooks["outgoing"][name] = {
            "url": url,
            "action": action,
            "created": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
        }
        self._save()
        return f"Webhook '{name}' registriert."

    def register_action(self, trigger, action):
        """Registriert eine Aktion die bei einem bestimmten Event ausgeführt wird."""
        if "actions" not in self.webhooks:
            self.webhooks["actions"] = {}
        self.webhooks["actions"][trigger] = {
            "action": action,
            "created": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
        }
        self._save()
        return f"Aktion für '{trigger}' registriert: {action}"

    def process_incoming(self, data):
        """Verarbeitet einen eingehenden Webhook."""
        event_type = data.get("type", data.get("event", "unknown"))

        # Prüfe ob eine Aktion registriert ist
        for trigger, action_info in self.webhooks.get("actions", {}).items():
            if trigger.lower() in str(data).lower():
                if self.on_trigger:
                    self.on_trigger(action_info["action"])
                return f"Aktion ausgelöst: {action_info['action']}"

        return f"Webhook empfangen: {event_type}"

    def list_webhooks(self):
        """Listet alle registrierten Webhooks."""
        result = "Webhooks: "
        outgoing = self.webhooks.get("outgoing", {})
        actions = self.webhooks.get("actions", {})

        if not outgoing and not actions:
            return "Keine Webhooks registriert."

        if outgoing:
            result += "Ausgehend: "
            for name, info in outgoing.items():
                result += f"{name} ({info.get('url', '')[:30]}...). "

        if actions:
            result += "Aktionen: "
            for trigger, info in actions.items():
                result += f"Bei '{trigger}' → {info['action']}. "

        return result

    def handle(self, text):
        """Verarbeitet Webhook-Befehle aus Spracheingabe."""
        text = text.lower().strip()

        # Webhook registrieren: "webhook erstellen discord https://discord.com/api/webhooks/..."
        reg_match = re.search(r"webhook\s+(?:erstellen|registrieren|hinzufügen)\s+(\w+)\s+(https?://\S+)", text)
        if reg_match:
            name = reg_match.group(1).strip()
            url = reg_match.group(2).strip()
            return self.register_webhook(name, url)

        # Discord Webhook senden: "webhook discord nachricht hallo welt"
        discord_match = re.search(r"webhook\s+discord\s+(?:nachricht|message|sende?)\s+(.+)", text)
        if discord_match:
            msg = discord_match.group(1).strip()
            return self.send_discord_webhook(message=msg)

        # Webhook senden: "webhook senden test"
        send_match = re.search(r"webhook\s+senden\s+(\w+)", text)
        if send_match:
            name = send_match.group(1).strip()
            return self.send_webhook(name=name)

        # Webhooks anzeigen
        if any(w in text for w in ["webhook liste", "webhooks zeigen", "meine webhooks"]):
            return self.list_webhooks()

        return None