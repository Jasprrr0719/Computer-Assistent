"""
Browser-Automatisierung – Webseiten steuern, klicken, Formulare ausfüllen.
Nutzt Playwright für echte Browser-Steuerung.
"""

import threading
import time
import os
import sys
import re


class BrowserTool:
    def __init__(self):
        self.browser = None
        self.page = None
        self._ready = False

    def _ensure_browser(self):
        """Startet Browser wenn nötig."""
        if self._ready and self.page:
            return True
        try:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            self.browser = self._playwright.chromium.launch(
                headless=False,
                args=["--start-maximized"]
            )
            context = self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            self.page = context.new_page()
            self._ready = True
            return True
        except ImportError:
            return False
        except Exception as e:
            print(f"  [Browser-Fehler: {e}]")
            return False

    def goto(self, url=""):
        """Navigiert zu einer URL."""
        if not self._ensure_browser():
            return "Browser konnte nicht gestartet werden. Ist Playwright installiert?"
        if not url.startswith("http"):
            url = f"https://{url}"
        try:
            self.page.goto(url, timeout=15000)
            title = self.page.title()
            return f"Seite geöffnet: {title}"
        except Exception as e:
            return f"Navigation fehlgeschlagen: {e}"

    def click(self, text="", selector=""):
        """Klickt auf ein Element."""
        if not self._ready:
            return "Browser nicht gestartet."
        try:
            if text:
                self.page.get_by_text(text, exact=False).first.click(timeout=5000)
                return f"Auf '{text}' geklickt."
            elif selector:
                self.page.click(selector, timeout=5000)
                return f"Element geklickt."
            return "Kein Ziel angegeben."
        except Exception as e:
            return f"Klick fehlgeschlagen: {e}"

    def type_text(self, selector="", text="", field_name=""):
        """Tippt Text in ein Feld."""
        if not self._ready:
            return "Browser nicht gestartet."
        try:
            if field_name:
                self.page.get_by_placeholder(field_name).first.fill(text)
            elif selector:
                self.page.fill(selector, text)
            else:
                self.page.keyboard.type(text)
            return f"Text eingegeben."
        except Exception as e:
            return f"Eingabe fehlgeschlagen: {e}"

    def read_page(self):
        """Liest den sichtbaren Text der aktuellen Seite."""
        if not self._ready:
            return "Browser nicht gestartet."
        try:
            text = self.page.inner_text("body")
            return text[:3000]
        except Exception as e:
            return f"Lesen fehlgeschlagen: {e}"

    def screenshot_page(self):
        """Macht einen Screenshot der aktuellen Seite."""
        if not self._ready:
            return "Browser nicht gestartet."
        try:
            path = os.path.join(os.path.expanduser("~"), "Desktop", "browser_screenshot.png")
            self.page.screenshot(path=path)
            os.startfile(path)
            return f"Screenshot gespeichert: {path}"
        except Exception as e:
            return f"Screenshot fehlgeschlagen: {e}"

    def scroll(self, direction="down"):
        """Scrollt die Seite."""
        if not self._ready:
            return "Browser nicht gestartet."
        try:
            if direction == "down":
                self.page.mouse.wheel(0, 500)
            else:
                self.page.mouse.wheel(0, -500)
            return f"Gescrollt: {direction}"
        except Exception as e:
            return f"Scroll fehlgeschlagen: {e}"

    def wait(self, seconds=2):
        """Wartet X Sekunden."""
        time.sleep(seconds)
        return f"{seconds} Sekunden gewartet."

    def close(self):
        """Schließt den Browser."""
        try:
            if self.browser:
                self.browser.close()
            if self._playwright:
                self._playwright.stop()
            self._ready = False
            self.page = None
            self.browser = None
            return "Browser geschlossen."
        except:
            return "Browser war nicht offen."

    def twitch_follow(self, channel=""):
        """Öffnet Twitch-Kanal. Folgen muss manuell passieren (Login nötig)."""
        if not channel:
            return "Kein Kanal angegeben."
        result = self.goto(f"https://www.twitch.tv/{channel}")
        return f"Twitch-Kanal {channel} geöffnet. Klicke auf 'Folgen' wenn du eingeloggt bist."

    def google_search(self, query=""):
        """Sucht bei Google und gibt die Ergebnisse zurück."""
        if not self._ensure_browser():
            return "Browser nicht verfügbar."
        try:
            self.page.goto(f"https://www.google.com/search?q={query}", timeout=15000)
            time.sleep(2)
            results = self.page.query_selector_all("h3")
            texts = []
            for r in results[:5]:
                texts.append(r.inner_text())
            return "Suchergebnisse: " + ". ".join(texts) if texts else "Keine Ergebnisse."
        except Exception as e:
            return f"Suche fehlgeschlagen: {e}"

    def handle(self, text):
        """Verarbeitet Browser-Befehle aus Spracheingabe."""
        text = text.lower().strip()

        # Twitch folgen
        follow_match = re.search(r"(?:folge|follow)\s+(\w+)\s+(?:auf|on)\s+twitch", text)
        if follow_match:
            return self.twitch_follow(follow_match.group(1).strip())

        # Webseite öffnen im automatisierten Browser
        goto_match = re.search(r"(?:geh auf|navigiere zu|öffne im browser|browser öffne)\s+(.+)", text)
        if goto_match:
            url = goto_match.group(1).strip().rstrip(".")
            return self.goto(url)

        # Klicken
        click_match = re.search(r"(?:klick|klicke|drücke|press)\s+(?:auf\s+)?(.+)", text)
        if click_match:
            target = click_match.group(1).strip().rstrip(".")
            return self.click(text=target)

        # Text eingeben
        type_match = re.search(r"(?:tippe|schreibe?|eingabe|type)\s+(.+?)(?:\s+in\s+(.+))?$", text)
        if type_match:
            content = type_match.group(1).strip()
            field = type_match.group(2).strip() if type_match.group(2) else ""
            return self.type_text(field_name=field, text=content)

        # Seite lesen
        if any(w in text for w in ["lies die seite", "seite vorlesen", "was steht auf der seite"]):
            return self.read_page()

        # Screenshot
        if "browser screenshot" in text:
            return self.screenshot_page()

        # Scrollen
        if any(w in text for w in ["scroll runter", "nach unten"]):
            return self.scroll("down")
        if any(w in text for w in ["scroll hoch", "nach oben"]):
            return self.scroll("up")

        # Browser schließen
        if any(w in text for w in ["browser schließen", "browser zu", "schließe browser"]):
            return self.close()

        return None