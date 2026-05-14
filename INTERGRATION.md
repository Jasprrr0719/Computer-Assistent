# AR-Display fuer Computer-Assistent

Erweitert deinen bestehenden Python-Assistenten um ein Browser-basiertes
AR-Display mit Hand-Tracking. Du sagst "zeig mir Spotify" - im Browser
erscheint ein schwebendes Icon. Du drueckst mit der Hand drauf - Spotify
oeffnet sich. Minority-Report-Style.

## Was du bekommst

- `ar_server.py` - WebSocket-Server (startet mit deinem Assistenten)
- `docs/ar.html` + `docs/app.js` - die AR-Browser-Seite
- Patches fuer deine bestehenden `main.py` und `brain.py`

Deine bestehenden Dateien (`voice.py`, `memory.py`, `smarthome.py`,
`gui.py`, `config_manager.py`) werden **nicht angefasst**.

---

## Schritt 1: Dateien ins Projekt kopieren

Kopiere diese Dateien in dein `ki-assistent/` Projekt:

```
ki-assistent/
├── ar_server.py           ← NEU (ins Root-Verzeichnis)
├── main.py                ← BESTEHEND (wir aendern 3 Zeilen)
├── brain.py               ← BESTEHEND (wir ergaenzen 4 Methoden + Prompt)
├── voice.py               ← unveraendert
├── memory.py              ← unveraendert
├── smarthome.py           ← unveraendert
├── gui.py                 ← unveraendert
├── config_manager.py      ← unveraendert
└── docs/
    ├── index.html         ← DEINE BESTEHENDE Landing-Page
    ├── ar.html            ← NEU
    └── app.js             ← NEU
```

## Schritt 2: Dependency installieren

Im VS-Code-Terminal:

```
pip install websockets
```

Dann in deiner `requirements.txt` ergaenzen:
```
websockets
```

## Schritt 3: main.py anpassen

**Ganz oben** bei den Imports ergaenzen:

```python
from ar_server import ar_server
```

In der `main()` Funktion, **nach** `setup_autostart()` und **vor** `brain = Brain(config)`:

```python
# AR-Display starten
ar_server.start()
```

In der `main()` Funktion, **nach** `brain = Brain(config)`:

```python
# Icon-Klicks vom Browser an das Brain weiterreichen
ar_server.on_icon_clicked = brain.handle_ar_click
```

Das wars fuer main.py. Drei Zeilen.

## Schritt 4: brain.py erweitern

**Die drei neuen Tool-Methoden** in der `Brain`-Klasse ergaenzen (am besten
neben den bestehenden `_tool_open_app`-Methoden):

```python
def _tool_zeige_icon(self, app: str) -> str:
    """Zeigt ein App-Icon im AR-Browser-Display."""
    from ar_server import ar_server
    if not ar_server.has_clients():
        return "AR-Display ist nicht verbunden. Oeffne die AR-Seite im Browser, Boss."
    app = app.strip().lower()
    ar_server.add_icon(app)
    return f"Icon fuer {app} ist jetzt im Raum, Boss."

def _tool_verstecke_icon(self, app: str) -> str:
    from ar_server import ar_server
    ar_server.remove_icon(app.strip().lower())
    return f"Icon fuer {app} entfernt."

def _tool_leere_ar(self, _: str = "") -> str:
    from ar_server import ar_server
    ar_server.clear_icons()
    return "AR-Display geleert, Boss."
```

**Callback-Methode** in der `Brain`-Klasse ergaenzen:

```python
def handle_ar_click(self, app: str):
    """Wird aufgerufen wenn Boss mit der Hand auf ein AR-Icon drueckt."""
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

    msg = f"{app.capitalize()} wird geoeffnet, Boss."
    try:
        self.voice.speak(msg)
    except Exception:
        print(f"[Computer] {msg}")

    from ar_server import ar_server
    ar_server.speak(msg)
```

**Wichtig:** Damit `self.voice` im `handle_ar_click` funktioniert, musst du
in `main.py` nach dem Erstellen des `voice`-Objekts die Referenz ans
Brain geben. Falls du das noch nicht hast, in `main.py`:

```python
voice = Voice(brain.name)
brain.voice = voice   # ← diese Zeile sicherstellen
ar_server.on_icon_clicked = brain.handle_ar_click
```

**Tool-Dispatcher erweitern** - in der Methode die `[TOOL: name | arg]`
parst und ausfuehrt, die drei neuen Tools registrieren:

```python
# wo du bereits hast:
#   "open_url": self._tool_open_url,
#   "open_app": self._tool_open_app,
#   ...
# ergaenze:
"zeige_icon":     self._tool_zeige_icon,
"verstecke_icon": self._tool_verstecke_icon,
"leere_ar":       self._tool_leere_ar,
```

**System-Prompt erweitern** - in `build_prompt()` unter der TOOLS-Liste:

```
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
```

## Schritt 5: Testen

Terminal 1:
```
python main.py
```

Im Browser: `docs/ar.html` oeffnen (einfach Doppelklick auf die Datei
oder `file:///pfad/zu/ar.html`).

- Klick auf **START**
- Kamera-Zugriff erlauben
- Du solltest dich sehen, mit neonblauem Skeleton ueber deiner Hand
- Oben rechts sollte **LINKED** stehen (= WebSocket-Verbindung zum Python-Backend)

Sprich:
- **"Computer, zeig mir Spotify"** → Spotify-Icon erscheint im Raum
- **"Computer, pack mir noch YouTube dazu"** → zweites Icon
- Pinche Daumen+Zeigefinger zusammen → du kannst Icons verschieben
- Halte deinen Zeigefinger ca. 1 Sekunde ueber einem Icon → Aktivierungs-Ring
  faellt voll, Partikel-Explosion, App oeffnet sich
- **"Computer, leere den Raum"** → alle Icons weg

## Schritt 6 (optional): Als GitHub Pages hosten

Deine `docs/ar.html` kannst du direkt ueber deine bestehende GitHub-Pages
einbinden:

```
https://jasprrr0719.github.io/Computer-Assistent/ar.html
```

Dann laeuft die AR-Seite im Browser, verbindet sich aber per WebSocket
zu `ws://localhost:8765` - also zu deinem lokalen Python-Assistenten.

⚠️ **Wichtig bei GitHub Pages**: HTTPS-Seiten duerfen kein unverschluesseltes
`ws://` ansprechen (Mixed Content). Loesung:

1. **Einfach**: Die AR-Seite immer lokal oeffnen (`file://` oder `http://localhost`)
2. **Sauber**: In deinem `ar_server.py` TLS einrichten und `wss://` verwenden
   (komplizierter, erst machen wenn du's wirklich hosten willst)

## Unterstuetzte Apps

Eingebaut (mit Emoji + Farbe):
spotify, youtube, github, discord, netflix, twitch, gmail, maps, chatgpt, claude

Unbekannte Apps funktionieren trotzdem: sie bekommen ein Default-Icon und
oeffnen Google-Suche.

**Neue App hinzufuegen:** In `docs/app.js`, `APP_CATALOG` erweitern:
```javascript
steam: { emoji: '\ud83c\udfae', color: '#1b2838', label: 'Steam' },
```
Und in `brain.py`, `handle_ar_click`, die `known`-Map erweitern:
```python
"steam": "steam://open/main",
```

## Troubleshooting

**"AR-Display ist nicht verbunden"**
→ Die Browser-Seite ist nicht offen oder der WebSocket-Server laeuft nicht.
Schau im Python-Terminal nach `[ar] WebSocket-Server laeuft...`.

**FPS sind niedrig / Kamera-Feed ruckelt**
→ MediaPipe ist rechenintensiv. Schliesse andere Tabs. Falls es immer
noch langsam ist, in `app.js` `modelComplexity: 0` setzen statt `1`.

**Icon laesst sich nicht greifen**
→ Pinch muss deutlich sein (Daumen und Zeigefinger nah zusammen).
Threshold laesst sich in `app.js` anpassen: `pinchDist < 0.35` ist der Wert.

**Kamera ist gespiegelt falsch**
→ Die `transform: scaleX(-1)` im CSS dreht das Video. Falls du das
Spiegeln nicht willst, entferne diese Zeile - aber dann fuehlt es sich
nicht mehr wie ein Spiegel an.
