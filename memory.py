"""
Gedächtnis – speichert Infos über den Nutzer persistent in JSON.
"""

import json
import os
import datetime
import sys

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

MEMORY_FILE = os.path.join(APP_DIR, "memory.json")
NOTES_FILE = os.path.join(APP_DIR, "notes.json")
TODO_FILE = os.path.join(APP_DIR, "todo.json")


class Memory:
    def __init__(self):
        self.data = self._load(MEMORY_FILE) if os.path.exists(MEMORY_FILE) else {}
        self.triggers = {
            "mein name ist": "user_name", "ich heiße": "user_name", "nenn mich": "user_name",
            "ich mag": "likes", "ich liebe": "loves", "ich hasse": "dislikes",
            "ich wohne in": "wohnort", "ich komme aus": "herkunft",
            "ich arbeite bei": "arbeitgeber", "ich arbeite als": "beruf",
            "ich bin": "status", "mein hobby ist": "hobby",
            "mein lieblingsessen ist": "lieblingsessen",
            "meine lieblingsfarbe ist": "lieblingsfarbe",
            "ich spiele": "spiele", "ich höre": "musik",
            "mein geburtstag ist": "geburtstag",
        }

    def _load(self, path):
        with open(path, "r", encoding="utf-8") as f: return json.load(f)

    def _save(self, path, data):
        with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

    def check_and_store(self, text):
        text_lower = text.lower()
        for trigger, key in self.triggers.items():
            if trigger in text_lower:
                value = text_lower.split(trigger)[-1].strip().rstrip(".")
                if value and len(value) < 100:
                    self.data[key] = value
                    self._save(MEMORY_FILE, self.data)
                    return f"Gemerkt: {value}"
        return None

    def get_context(self):
        if not self.data: return "Noch keine Infos über den Nutzer."
        return "\n".join([f"- {k}: {v}" for k, v in self.data.items()])

    def get(self, key, default=None): return self.data.get(key, default)


class Notes:
    def __init__(self): self.file = NOTES_FILE
    def _load(self):
        if os.path.exists(self.file):
            with open(self.file, "r", encoding="utf-8") as f: return json.load(f)
        return {"notes": []}
    def _save(self, data):
        with open(self.file, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
    def add(self, text):
        data = self._load()
        data["notes"].append({"text": text, "time": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")})
        self._save(data); return f"Notiert: {text}"
    def list_all(self):
        data = self._load()
        if not data["notes"]: return "Keine Notizen."
        r = "Notizen: "
        for i, n in enumerate(data["notes"], 1): r += f"{i}. {n['text']}. "
        return r
    def clear(self): self._save({"notes": []}); return "Alle Notizen gelöscht."


class Todos:
    def __init__(self): self.file = TODO_FILE
    def _load(self):
        if os.path.exists(self.file):
            with open(self.file, "r", encoding="utf-8") as f: return json.load(f)
        return {"todos": []}
    def _save(self, data):
        with open(self.file, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
    def add(self, text):
        data = self._load()
        data["todos"].append({"text": text, "done": False, "time": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")})
        self._save(data); return f"Auf die Liste: {text}"
    def list_open(self):
        data = self._load(); open_t = [t for t in data["todos"] if not t["done"]]
        if not open_t: return "To-Do Liste ist leer."
        r = "Aufgaben: "
        for i, t in enumerate(open_t, 1): r += f"{i}. {t['text']}. "
        return r
    def complete(self, index):
        data = self._load(); open_t = [t for t in data["todos"] if not t["done"]]
        if 0 <= index < len(open_t):
            open_t[index]["done"] = True; self._save(data)
            return f"Erledigt: {open_t[index]['text']}"
        return "Aufgabe nicht gefunden."
    def clear(self): self._save({"todos": []}); return "To-Do Liste gelöscht."