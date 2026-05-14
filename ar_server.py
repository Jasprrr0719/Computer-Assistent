"""
AR-Display WebSocket-Server
---------------------------
Verbindet den Computer-Assistenten mit der Browser-AR-Seite.
Lauft auf ws://localhost:8765.

Nachrichtenformate:
  Python -> Browser:
    { "type": "add_icon",    "app": "spotify", "label": "Spotify" }
    { "type": "remove_icon", "app": "spotify" }
    { "type": "clear_icons" }
    { "type": "speak",       "text": "Spotify wird ge\u00f6ffnet, Boss." }

  Browser -> Python:
    { "type": "icon_clicked", "app": "spotify" }
    { "type": "hello" }        # beim Verbinden

Der Server h\u00e4lt eine Referenz auf alle verbundenen Clients und kann von
\u00fcberall im Projekt (z.B. aus brain.py) mit `ar_server.send(...)` Befehle
an den Browser pushen.
"""

import asyncio
import json
import threading
from typing import Callable, Optional, Set

import websockets
from websockets.server import WebSocketServerProtocol


class ARServer:
    """Kleiner WebSocket-Server, der die Verbindung zum Browser h\u00e4lt."""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        # Callback, den brain.py setzen kann, um auf Icon-Klicks zu reagieren.
        self.on_icon_clicked: Optional[Callable[[str], None]] = None

        # Eigener Event-Loop in einem Hintergrund-Thread \u2013 so blockiert
        # der Server nicht den Haupt-Assistenten und wir k\u00f6nnen aus
        # synchronem Python-Code (brain.py) Befehle schicken.
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()

    # ---------- \u00d6ffentliche API (wird aus brain.py aufgerufen) ----------

    def start(self):
        """Startet den Server im Hintergrund-Thread."""
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)  # warten bis Loop steht
        print(f"[ar] WebSocket-Server l\u00e4uft auf ws://{self.host}:{self.port}")

    def add_icon(self, app: str, label: Optional[str] = None):
        """Icon im Browser anzeigen. `app` ist der interne Name (z.B. 'spotify')."""
        self._broadcast({
            "type": "add_icon",
            "app": app.lower(),
            "label": label or app.capitalize(),
        })

    def remove_icon(self, app: str):
        self._broadcast({"type": "remove_icon", "app": app.lower()})

    def clear_icons(self):
        self._broadcast({"type": "clear_icons"})

    def speak(self, text: str):
        """Den Assistenten-Text auch im Browser als Untertitel zeigen."""
        self._broadcast({"type": "speak", "text": text})

    def has_clients(self) -> bool:
        return len(self.clients) > 0

    # ---------- Interne Methoden ----------

    def _run_loop(self):
        """L\u00e4uft im Hintergrund-Thread \u2013 startet asyncio-Server."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop

        async def main():
            async with websockets.serve(self._handle_client, self.host, self.port):
                self._ready.set()
                await asyncio.Future()  # l\u00e4uft ewig

        try:
            loop.run_until_complete(main())
        except Exception as e:
            print(f"[ar] Server-Fehler: {e}")

    async def _handle_client(self, ws: WebSocketServerProtocol):
        """Eine Browser-Verbindung behandeln."""
        self.clients.add(ws)
        print(f"[ar] Browser verbunden ({len(self.clients)} aktiv)")
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                if msg.get("type") == "icon_clicked":
                    app = msg.get("app", "")
                    print(f"[ar] Icon geklickt: {app}")
                    # Callback im Hauptthread des Assistenten triggern
                    if self.on_icon_clicked:
                        try:
                            self.on_icon_clicked(app)
                        except Exception as e:
                            print(f"[ar] Callback-Fehler: {e}")
        except websockets.ConnectionClosed:
            pass
        finally:
            self.clients.discard(ws)
            print(f"[ar] Browser getrennt ({len(self.clients)} aktiv)")

    def _broadcast(self, msg: dict):
        """Thread-safe an alle verbundenen Clients schicken."""
        if not self._loop or not self.clients:
            return
        payload = json.dumps(msg)

        async def send_all():
            # Kopie der Menge, weil sich die Menge w\u00e4hrend des Sendens \u00e4ndern k\u00f6nnte.
            dead = set()
            for client in list(self.clients):
                try:
                    await client.send(payload)
                except Exception:
                    dead.add(client)
            self.clients -= dead

        # Von anderem Thread aus in den asyncio-Loop einreihen
        asyncio.run_coroutine_threadsafe(send_all(), self._loop)


# Singleton-Instanz, die brain.py importieren kann
ar_server = ARServer()
