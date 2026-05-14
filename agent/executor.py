"""
Executor – Führt Pläne aus mit Security-Checks.
Verbindet Planner, Tool-Registry und Security Guard.
"""

import threading
from agent.planner import Planner, Task, Plan, TaskStatus
from tools.registry import ToolRegistry
from security.guard import SecurityGuard


class AgentExecutor:
    def __init__(self, ai_client):
        self.ai_client = ai_client
        self.planner = Planner(ai_client)
        self.tools = ToolRegistry()
        self.security = SecurityGuard()
        self.on_speak = None
        self.on_status = None
        self._pending_confirmation = None

    def process_autonomous(self, user_input):
        """
        Verarbeitet eine Aufgabe autonom:
        1. Analysiert ob Multi-Step nötig ist
        2. Erstellt Plan wenn nötig
        3. Führt aus mit Security-Checks
        """
        # Einfache Befehle direkt ausführen
        simple = self._try_simple(user_input)
        if simple is not None:
            return simple

        # Komplexe Aufgabe → Plan erstellen
        available = self.tools.get_available_tools()
        plan = self.planner.create_plan(user_input, available)

        if len(plan.steps) == 1 and plan.steps[0].tool == "ai":
            # Nur eine KI-Antwort nötig
            return None  # Lass brain.py die KI-Antwort machen

        # Plan ausführen
        if self.on_status:
            self.on_status(f"Plan erstellt: {len(plan.steps)} Schritte")

        results = self.planner.execute_plan(plan, self._safe_execute)

        # Zusammenfassung
        summary = f"Aufgabe erledigt. {len([r for r in results if '✓' in r])} von {len(results)} Schritten erfolgreich."
        return summary

    def _try_simple(self, text):
        """Versucht einfache Tool-Aufrufe direkt auszuführen."""
        text_lower = text.lower()

        # Direkte Tool-Mappings
        simple_mappings = {
            "screenshot": ("screenshot", {}),
            "zwischenablage": ("get_clipboard", {}),
            "was hab ich kopiert": ("get_clipboard", {}),
            "system info": ("system_info", {}),
            "system status": ("system_info", {}),
        }

        for trigger, (tool, args) in simple_mappings.items():
            if trigger in text_lower:
                return self._safe_execute(tool, args)

        return None

    def _safe_execute(self, tool_name, args):
        """Führt ein Tool mit Security-Check aus."""
        tool_info = self.tools.get_available_tools().get(tool_name, {})

        # Security Check
        allowed, reason = self.security.check_tool(tool_name, args, tool_info)

        if allowed == "confirm":
            # Bestätigung speichern für später
            self._pending_confirmation = {"tool": tool_name, "args": args}
            if self.on_speak:
                self.on_speak(f"Sicherheitscheck: {reason}. Soll ich fortfahren?")
            return f"Bestätigung nötig: {reason}"

        if not allowed:
            return f"Blockiert: {reason}"

        # Ausführen
        result = self.tools.execute(tool_name, args)
        self.security._log("EXECUTED", f"{tool_name}: {args}", str(result)[:100])
        return result

    def confirm_pending(self):
        """Bestätigt einen ausstehenden gefährlichen Befehl."""
        if self._pending_confirmation:
            tool = self._pending_confirmation["tool"]
            args = self._pending_confirmation["args"]
            self._pending_confirmation = None
            return self.tools.execute(tool, args)
        return "Nichts zu bestätigen."

    def deny_pending(self):
        """Verweigert einen ausstehenden Befehl."""
        self._pending_confirmation = None
        return "Befehl abgebrochen."