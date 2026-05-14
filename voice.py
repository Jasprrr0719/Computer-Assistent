"""
Voice – Edge-TTS, Interrupt, Sound-Effekte, Stimmen-Wechsel, Speed.
"""

import asyncio
import os
import tempfile
import threading
import struct
import wave
import math
import speech_recognition as sr
import edge_tts
import pygame

VOICES = {
    "männlich": "de-DE-ConradNeural",
    "weiblich": "de-DE-SeraphinaMultilingualNeural",
    "conrad": "de-DE-ConradNeural",
    "seraphina": "de-DE-SeraphinaMultilingualNeural",
    "florian": "de-DE-FlorianMultilingualNeural",
    "killian": "de-DE-KillianNeural",
}

SPEED_MAP = {
    "langsamer": "-15%", "langsam": "-25%", "normal": "+0%",
    "schneller": "+15%", "schnell": "+25%", "sehr schnell": "+40%",
}


class Voice:
    def __init__(self, assistant_name="Computer"):
        self.name = assistant_name
        self.recognizer = sr.Recognizer()
        self.is_speaking = False
        self.is_listening = False
        self._stop_flag = False
        self._interrupt_text = None
        self.amplitude = 0.0
        self.state = "idle"
        self.current_voice = "de-DE-ConradNeural"
        self.current_speed = "+0%"
        self.current_pitch = "-5Hz"
        pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
        self._sounds_dir = os.path.join(tempfile.gettempdir(), "jarvis_sounds")
        os.makedirs(self._sounds_dir, exist_ok=True)
        self._generate_sounds()

    def set_voice(self, voice_name):
        voice_name = voice_name.lower().strip()
        if voice_name in VOICES:
            self.current_voice = VOICES[voice_name]
            return f"Stimme gewechselt zu {voice_name.title()}."
        return f"Stimme '{voice_name}' nicht gefunden. Verfügbar: {', '.join(VOICES.keys())}."

    def set_speed(self, speed_name):
        speed_name = speed_name.lower().strip()
        if speed_name in SPEED_MAP:
            self.current_speed = SPEED_MAP[speed_name]
            return f"Geschwindigkeit auf {speed_name}."
        return None

    def _generate_sounds(self):
        for name, freqs, dur, vol in [
            ("startup", [400, 600, 800, 1000, 1200], 0.12, 0.25),
            ("notify", [800, 1200], 0.1, 0.2),
            ("listen", [600, 900], 0.06, 0.12),
            ("error", [600, 400, 300], 0.1, 0.2),
            ("success", [600, 800, 1000], 0.08, 0.18),
        ]:
            path = os.path.join(self._sounds_dir, f"{name}.wav")
            if os.path.exists(path): continue
            samples = []; sr_rate = 44100
            for freq in freqs:
                n = int(sr_rate * dur)
                for i in range(n):
                    env = min(i / (n * 0.1), 1.0, (n - i) / (n * 0.3))
                    samples.append(int(vol * env * math.sin(2 * math.pi * freq * i / sr_rate) * 32767))
            with wave.open(path, 'w') as f:
                f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr_rate)
                f.writeframes(struct.pack(f'{len(samples)}h', *samples))

    def play_sound(self, sound_name):
        try:
            path = os.path.join(self._sounds_dir, f"{sound_name}.wav")
            if os.path.exists(path): pygame.mixer.Sound(path).play()
        except: pass

    def speak(self, text):
        clean = text.split("[TOOL:")[0].strip() if "[TOOL:" in text else text
        if not clean: clean = "Erledigt."
        print(f"\n{self.name}: {clean}")
        try:
            self.is_speaking = True; self.state = "speaking"; self._stop_flag = False; self.amplitude = 0.5
            tmp = os.path.join(tempfile.gettempdir(), "assistant_tts.mp3")
            asyncio.run(self._generate(clean, tmp))
            pygame.mixer.music.load(tmp); pygame.mixer.music.play()
            threading.Thread(target=self._listen_for_interrupt, daemon=True).start()
            threading.Thread(target=self._simulate_amplitude, daemon=True).start()
            while pygame.mixer.music.get_busy():
                if self._stop_flag: pygame.mixer.music.stop(); break
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
            self.amplitude = 0.0
            try: os.remove(tmp)
            except: pass
        except Exception as e: print(f"  [TTS Fehler: {e}]")
        finally: self.is_speaking = False; self.amplitude = 0.0; self.state = "idle"

    def _simulate_amplitude(self):
        import random
        while self.is_speaking and not self._stop_flag:
            self.amplitude = 0.3 + random.random() * 0.7
            try: import time; time.sleep(0.05)
            except: break
        self.amplitude = 0.0

    def _listen_for_interrupt(self):
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                self.recognizer.energy_threshold = 500
                try:
                    audio = self.recognizer.listen(source, timeout=0.5, phrase_time_limit=2)
                    text = self.recognizer.recognize_google(audio, language="de-DE")
                    if text and len(text.strip()) > 0:
                        self._stop_flag = True; self._interrupt_text = text.lower()
                except: pass
        except: pass

    def get_interrupt_text(self):
        text = self._interrupt_text; self._interrupt_text = None; return text

    async def _generate(self, text, output_file):
        communicate = edge_tts.Communicate(text, self.current_voice, rate=self.current_speed, pitch=self.current_pitch)
        await communicate.save(output_file)

    def listen(self):
        if self.is_speaking: return ""
        self.state = "listening"; self.is_listening = True
        with sr.Microphone() as source:
            print("... höre zu ...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 1.5
            self.recognizer.non_speaking_duration = 1.0
            try: audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=60)
            except sr.WaitTimeoutError:
                self.is_listening = False; self.state = "idle"; return ""
        self.is_listening = False; self.state = "idle"
        try:
            text = self.recognizer.recognize_google(audio, language="de-DE")
            print(f"Du: {text}"); return text.lower()
        except sr.UnknownValueError: return ""
        except sr.RequestError as e: print(f"Speech-API Fehler: {e}"); return ""