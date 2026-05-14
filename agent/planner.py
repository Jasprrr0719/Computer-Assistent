"""
Planner – Zerlegt komplexe Aufgaben in Schritte und plant die Ausführung.
Multi-Step Thinking, Task Queue, Retry-System.
"""

import json
import datetime
import threading
import time
import uuid
from collections import deque
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    CANCELLED = "cancelled"


class Task:
    def __init__(self, description, tool=None, args=None, depends_on=None, max_retries=2):
        self.id = str(uuid.uuid4())[:8]
        self.description = description
        self.tool = tool
        self.args = args or {}
        self.depends_on = depends_on  # ID einer vorherigen Task
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.retries = 0
        self.max_retries = max_retries
        self.created_at = datetime.datetime.now()
        self.completed_at = None

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "tool": self.tool,
            "args": self.args,
            "status": self.status.value,
            "result": str(self.result)[:200] if self.result else None,
            "error": str(self.error) if self.error else None,
            "retries": self.retries,
            "created": self.created_at.strftime("%H:%M:%S"),
        }


class Plan:
    def __init__(self, goal, steps=None):
        self.id = str(uuid.uuid4())[:8]
        self.goal = goal
        self.steps = steps or []
        self.created_at = datetime.datetime.now()
        self.status = TaskStatus.PENDING

    def to_dict(self):
        return {
            "id": self.id,
            "goal": self.goal,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "created": self.created_at.strftime("%H:%M:%S"),
        }


class Planner:
    def __init__(self, ai_client, model="llama-3.3-70b-versatile"):
        self.ai_client = ai_client
        self.model = model
        self.task_queue = deque()
        self.completed_tasks = []
        self.active_plan = None
        self.background_tasks = []
        self._lock = threading.Lock()
        self.on_task_complete = None  # Callback
        self.on_speak = None  # Callback für Sprachausgabe

    def create_plan(self, goal, available_tools):
        """Lässt die KI einen Plan erstellen um ein Ziel zu erreichen."""
        tool_descriptions = "\n".join([
            f"- {name}: {info.get('description', '')}"
            for name, info in available_tools.items()
        ])

        prompt = f"""Du bist ein AI-Planungssystem. Erstelle einen Plan um folgendes Ziel zu erreichen.

ZIEL: {goal}

VERFÜGBARE TOOLS:
{tool_descriptions}

Antworte NUR mit einem JSON-Array von Schritten. Jeder Schritt hat:
- "description": Was gemacht wird (kurz)
- "tool": Name des Tools (oder "ai" für KI-Antwort)
- "args": Dictionary mit Argumenten für das Tool

Beispiel:
[
  {{"description": "Chrome öffnen", "tool": "open_app", "args": {{"app": "chrome"}}}},
  {{"description": "Webseite aufrufen", "tool": "open_url", "args": {{"url": "https://google.com"}}}}
]

Wenn kein Tool passt, nutze "tool": "ai" mit "args": {{"prompt": "die Frage"}}.
Antworte NUR mit dem JSON-Array, nichts anderes."""

        try:
            response = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.3,
            )
            text = response.choices[0].message.content.strip()

            # JSON extrahieren
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            steps_data = json.loads(text)
            tasks = []
            prev_id = None

            for step in steps_data:
                task = Task(
                    description=step.get("description", ""),
                    tool=step.get("tool", "ai"),
                    args=step.get("args", {}),
                    depends_on=prev_id,
                )
                tasks.append(task)
                prev_id = task.id

            plan = Plan(goal=goal, steps=tasks)
            self.active_plan = plan
            return plan

        except json.JSONDecodeError:
            # Fallback: Einzelne Task
            task = Task(description=goal, tool="ai", args={"prompt": goal})
            plan = Plan(goal=goal, steps=[task])
            self.active_plan = plan
            return plan

        except Exception as e:
            task = Task(description=f"Fehler beim Planen: {e}", tool="ai", args={"prompt": goal})
            plan = Plan(goal=goal, steps=[task])
            self.active_plan = plan
            return plan

    def add_task(self, task):
        """Fügt eine einzelne Task zur Queue hinzu."""
        with self._lock:
            self.task_queue.append(task)

    def add_background_task(self, func, interval_seconds, name=""):
        """Startet einen Hintergrundprozess."""
        def loop():
            while True:
                try:
                    func()
                except Exception as e:
                    print(f"  [Background Task '{name}' Fehler: {e}]")
                time.sleep(interval_seconds)

        t = threading.Thread(target=loop, daemon=True)
        t.start()
        self.background_tasks.append({"name": name, "thread": t, "interval": interval_seconds})

    def execute_plan(self, plan, tool_executor):
        """Führt einen Plan Schritt für Schritt aus."""
        plan.status = TaskStatus.RUNNING
        results = []

        for task in plan.steps:
            # Prüfe Abhängigkeiten
            if task.depends_on:
                dep = next((t for t in plan.steps if t.id == task.depends_on), None)
                if dep and dep.status == TaskStatus.FAILED:
                    task.status = TaskStatus.CANCELLED
                    results.append(f"⊘ {task.description} (übersprungen)")
                    continue

            # Task ausführen
            task.status = TaskStatus.RUNNING

            try:
                if task.tool == "ai":
                    # KI-Antwort generieren
                    result = self._ai_response(task.args.get("prompt", task.description))
                else:
                    # Tool ausführen
                    result = tool_executor(task.tool, task.args)

                task.result = result
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.datetime.now()
                results.append(f"✓ {task.description}")

            except Exception as e:
                task.error = str(e)
                task.retries += 1

                if task.retries <= task.max_retries:
                    task.status = TaskStatus.RETRY
                    time.sleep(1)
                    # Retry
                    try:
                        if task.tool == "ai":
                            result = self._ai_response(task.args.get("prompt", task.description))
                        else:
                            result = tool_executor(task.tool, task.args)
                        task.result = result
                        task.status = TaskStatus.COMPLETED
                        results.append(f"✓ {task.description} (Retry)")
                    except Exception as e2:
                        task.status = TaskStatus.FAILED
                        task.error = str(e2)
                        results.append(f"✗ {task.description}: {e2}")
                else:
                    task.status = TaskStatus.FAILED
                    results.append(f"✗ {task.description}: {e}")

            # Callback
            if self.on_task_complete:
                self.on_task_complete(task)

        # Plan-Status
        failed = [t for t in plan.steps if t.status == TaskStatus.FAILED]
        plan.status = TaskStatus.COMPLETED if not failed else TaskStatus.FAILED

        return results

    def _ai_response(self, prompt):
        """Generiert eine KI-Antwort."""
        response = self.ai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.7,
        )
        return response.choices[0].message.content

    def get_status(self):
        """Gibt den aktuellen Status zurück."""
        return {
            "active_plan": self.active_plan.to_dict() if self.active_plan else None,
            "queue_size": len(self.task_queue),
            "completed": len(self.completed_tasks),
            "background_tasks": len(self.background_tasks),
        }