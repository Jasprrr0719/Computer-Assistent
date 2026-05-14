"""
AR-Tools f\u00fcr brain.py
--------------------
Diese Funktionen werden in brain.py integriert. Sie erweitern das
Tool-System um:
  - zeige_icon     : l\u00e4sst ein schwebendes App-Icon im Browser erscheinen
  - verstecke_icon : einzelnes Icon entfernen
  - leere_ar       : alle Icons weg

Der System-Prompt wird so erg\u00e4nzt dass Computer diese neuen Tools kennt.
"""

# --- NEUE TOOLS F\u00dcR brain.py ----------------------------------------------
# Diese Funktion in Brain-Klasse einf\u00fcgen (nach _tool_open_app o.\u00e4.):

def _tool_zeige_icon(self, app: str) -> str:
    """Zeigt ein App-Icon im AR-Browser-Display."""
    from ar_server import ar_server
    if not ar_server.has_clients():
        return "AR-Display ist nicht verbunden. \u00d6ffne die AR-Seite im Browser, Boss."
    app = app.strip().lower()
    ar_server.add_icon(app)
    return f"Icon f\u00fcr {app} ist jetzt im Raum, Boss."


def _tool_verstecke_icon(self, app: str) -> str:
    from ar_server import ar_server
    ar_server.remove_icon(app.strip().lower())
    return f"Icon f\u00fcr {app} entfernt."


def _tool_leere_ar(self, _: str = "") -> str:
    from ar_server import ar_server
    ar_server.clear_icons()
    return "AR-Display geleert, Boss."


# --- CALLBACK F\u00dcR ICON-KLICKS --------------------------------------------
# Diese Methode in Brain-Klasse einf\u00fcgen:

def handle_ar_click(self, app: str):
    """Wird vom AR-Server aufgerufen wenn Boss mit der Hand auf ein Icon dr\u00fcckt.
    \u00d6ffnet die App \u00fcber die bestehende open_app/open_url-Logik."""
    # Bekannte Apps auf URLs mappen; Unbekanntes landet im Browser-Suche
    known = {
        "spotify": "https://open.spotify.com",
        "youtube": "https://youtube.com",
        "github":  "https://github.com",
        "discord": "https://discord.com/app",
        "netflix": "https://netflix.com",
        "twitch":  "https://twitch.tv",
        "gmail":   "https://mail.google.com",
        "maps":    "https://maps.google.com",
        "chatgpt": "https://chat.openai.com",
        "claude":  "https://claude.ai",
    }
    import webbrowser
    url = known.get(app, f"https://www.google.com/search?q={app}")
    webbrowser.open(url)

    # Sprachausgabe \u00fcber die bestehende Voice-Engine
    msg = f"{app.capitalize()} wird ge\u00f6ffnet, Boss."
    # Annahme: self.voice existiert (wie in main.py gesetzt) \u2013 sonst print
    try:
        self.voice.speak(msg)
    except Exception:
        print(f"[Computer] {msg}")

    # Untertitel auch im AR-Display
    from ar_server import ar_server
    ar_server.speak(msg)


# --- SYSTEM-PROMPT ERWEITERUNG --------------------------------------------
# In der build_prompt()-Funktion unter TOOLS erg\u00e4nzen:

AR_TOOLS_PROMPT_ADDITION = """
5. zeige_icon     | Zeigt ein schwebendes App-Icon im AR-Raum des Boss
6. verstecke_icon | Entfernt ein Icon aus dem AR-Raum
7. leere_ar       | Entfernt alle AR-Icons

BEISPIELE AR:
User: zeig mir spotify
Antwort: Spotify erscheint im Raum. [TOOL: zeige_icon | spotify]

User: pack mir youtube und github dahin
Antwort: Beide Icons sind da. [TOOL: zeige_icon | youtube] [TOOL: zeige_icon | github]

User: mach den raum leer
Antwort: Wird geleert. [TOOL: leere_ar | ]
"""
