"""
Hauptprogramm – GUI + Autostart + Handy-Server + Geburtstags-Check.
"""

import sys
import os
import threading
import time
from config_manager import setup, load_config, save_config, APP_DIR
from brain import Brain
from voice import Voice


def setup_autostart():
    if sys.platform != "win32": return
    config = load_config()
    if config.get("autostart_configured"): return
    exe = sys.executable if getattr(sys,'frozen',False) else f'pythonw "{os.path.abspath(__file__)}"'
    try:
        import winreg
        k=winreg.OpenKey(winreg.HKEY_CURRENT_USER,r"Software\Microsoft\Windows\CurrentVersion\Run",0,winreg.KEY_SET_VALUE)
        winreg.SetValueEx(k,"KI-Assistent",0,winreg.REG_SZ,exe); winreg.CloseKey(k)
        config["autostart_configured"]=True; save_config(config)
        print("Autostart eingerichtet.")
    except Exception as e: print(f"Autostart-Fehler: {e}")


def main():
    config = setup()
    setup_autostart()

    brain = Brain(config)
    voice = Voice(brain.name)

    # Referenzen setzen
    brain.set_voice(voice)
    brain.smarthome.set_speak_callback(voice.speak)

    # Handy-Server starten
    try:
        from server import DashboardServer
        server = DashboardServer(brain, voice)
        server.start()
    except ImportError:
        print("Flask nicht installiert. Handy-Steuerung deaktiviert.")
    except Exception as e:
        print(f"Server-Fehler: {e}")

    try:
        from gui import AssistantGUI
        print(f"{brain.name} startet...")
        app = AssistantGUI(brain, voice)
        app.run()
    except ImportError:
        print("CustomTkinter fehlt. Terminal-Modus.")
        _terminal_mode(brain, voice)
    except Exception as e:
        print(f"GUI-Fehler: {e}. Terminal-Modus.")
        _terminal_mode(brain, voice)


def _terminal_mode(brain, voice):
    print(f"\n{'='*50}\n  {brain.name} ist bereit, Boss.\n{'='*50}\n")
    voice.speak(f"{brain.name} ist online. Ich höre zu, Boss.")

    bday = brain.get_birthday_message()
    if bday: voice.speak(bday)

    while True:
        try:
            interrupt = voice.get_interrupt_text()
            user_input = interrupt if interrupt else voice.listen()
            if not user_input: continue
            if user_input.strip() in ["beenden","stopp","exit","tschüss"]:
                voice.speak("Bis dann, Boss."); break
            answer = brain.process(user_input)
            if answer: voice.speak(answer)

            timer = brain.get_pending_timer()
            if timer:
                def rt(s,l): time.sleep(s); voice.play_sound("notify"); voice.speak(f"Timer! {l} um, Boss.")
                threading.Thread(target=rt,args=(timer["seconds"],timer["label"]),daemon=True).start()

            rem = brain.get_pending_reminder()
            if rem:
                def rr(s,t): time.sleep(s); voice.play_sound("notify"); voice.speak(f"Boss, Erinnerung: {t}")
                threading.Thread(target=rr,args=(rem["seconds"],rem["task"]),daemon=True).start()
        except KeyboardInterrupt:
            voice.speak("Tschüss, Boss."); break


if __name__ == "__main__":
    main()