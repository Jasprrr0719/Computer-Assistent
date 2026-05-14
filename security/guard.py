"""
Security Guard – Prüft Befehle, Allowlist, Logging.
"""

import json
import os
import datetime
import sys

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(APP_DIR, "action_log.json")


# Befehle die NIEMALS ausgeführt werden dürfen
BLOCKED_COMMANDS = [
    "format", "del /f /s /q", "rd /s /q", "rmdir /s /q",
    "rm -rf", "mkfs", ":(){:|:&};:",
    "reg delete", "bcdedit", "diskpart",
    "net user", "net localgroup",
]

# Befehle die Bestätigung brauchen
CONFIRM_REQUIRED = [
    "shutdown", "restart", "taskkill", "del ", "rm ",
    "reg ", "netsh", "schtasks",
]


class SecurityGuard:
    def __init__(self):
        self.action_log = []
        self.blocked_count = 0

    def check_command(self, command):
        """Prüft ob ein Befehl sicher ist. Gibt (erlaubt, grund) zurück."""
        cmd_lower = command.lower().strip()

        # Blockierte Befehle
        for blocked in BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                self.blocked_count += 1
                self._log("BLOCKED", command, f"Enthält blockierten Befehl: {blocked}")
                return False, f"Befehl blockiert: '{blocked}' ist nicht erlaubt."

        # Bestätigung nötig
        for confirm in CONFIRM_REQUIRED:
            if confirm in cmd_lower:
                self._log("CONFIRM_REQUIRED", command, f"Braucht Bestätigung: {confirm}")
                return "confirm", f"Dieser Befehl braucht Bestätigung: {command}"

        self._log("ALLOWED", command, "OK")
        return True, "OK"

    def check_tool(self, tool_name, args, tool_info):
        """Prüft ob ein Tool-Aufruf sicher ist."""
        if tool_info.get("dangerous"):
            self._log("DANGEROUS_TOOL", f"{tool_name}: {args}", "Gefährliches Tool")
            return "confirm", f"'{tool_name}' ist ein gefährliches Tool. Bestätigung nötig."
        return True, "OK"

    def _log(self, action_type, action, detail):
        """Loggt eine Aktion."""
        entry = {
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": action_type,
            "action": str(action)[:200],
            "detail": detail,
        }
        self.action_log.append(entry)

        # In Datei schreiben
        try:
            log_path = os.path.normpath(LOG_FILE)
            existing = []
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing.append(entry)
            # Nur letzte 1000 Einträge behalten
            existing = existing[-1000:]
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
        except:
            pass

    def get_log(self, limit=50):
        """Gibt die letzten Log-Einträge zurück."""
        return self.action_log[-limit:]

    def get_stats(self):
        return {
            "total_actions": len(self.action_log),
            "blocked": self.blocked_count,
        }