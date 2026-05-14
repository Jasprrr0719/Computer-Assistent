"""
Jarvis Hologramm GUI – verbessert mit mehr Partikeln, Reaktionen, Statusanzeigen.
"""

import customtkinter as ctk
import threading
import queue
import datetime
import time
import math
import random
import sys
import os
import tkinter as tk

ctk.set_appearance_mode("dark")


class HologramOrb(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg="#050510", highlightthickness=0, **kwargs)
        self.state = "idle"
        self.ring_angles = [0] * 12
        self.ring_speeds = [0.3, -0.5, 0.7, -0.4, 0.6, -0.8, 0.35, -0.55, 0.45, -0.65, 0.25, -0.75]
        self.amplitude = 0.0
        self.particles = []
        self.sparks = []
        self._init_particles()
        self._animate()

    def _init_particles(self):
        self.particles = []
        for _ in range(50):
            self.particles.append({
                "angle": random.uniform(0, 2 * math.pi),
                "dist": random.uniform(30, 170),
                "speed": random.uniform(0.003, 0.025),
                "size": random.uniform(0.5, 3),
                "alpha_offset": random.uniform(0, 2 * math.pi),
                "layer": random.choice([0, 1, 2]),
            })

    def set_state(self, state):
        if state != self.state and state == "speaking":
            self._create_sparks()
        self.state = state

    def set_amplitude(self, amp):
        self.amplitude = amp

    def _create_sparks(self):
        for _ in range(8):
            self.sparks.append({
                "x": 0, "y": 0,
                "vx": random.uniform(-3, 3),
                "vy": random.uniform(-3, 3),
                "life": 1.0,
                "decay": random.uniform(0.02, 0.05),
                "size": random.uniform(1, 3),
            })

    def _animate(self):
        w = self.winfo_width() or 500
        h = self.winfo_height() or 450
        cx, cy = w // 2, h // 2
        self.delete("all")

        t = time.time()

        # === HINTERGRUND GLOW ===
        if self.state == "speaking":
            glow_layers = 8
            base_r = 150 + math.sin(t * 4) * 40 * self.amplitude
            base_alpha = 0.08 + self.amplitude * 0.06
        elif self.state == "listening":
            glow_layers = 6
            base_r = 130 + math.sin(t * 2) * 20
            base_alpha = 0.06
        elif self.state == "thinking":
            glow_layers = 5
            base_r = 120 + math.sin(t * 6) * 10
            base_alpha = 0.05
        else:
            glow_layers = 4
            base_r = 110
            base_alpha = 0.03

        for i in range(glow_layers):
            r = base_r + i * 20
            alpha = max(0, base_alpha - i * 0.01)
            self.create_oval(cx-r, cy-r, cx+r, cy+r, outline=self._gold(alpha), width=0.5)

        # === ROTIERENDE RINGE (12 Stück, 3D-Effekt) ===
        for i in range(12):
            self.ring_angles[i] += self.ring_speeds[i] * (2 if self.state == "speaking" else 1)
            base_ring_r = 50 + i * 12

            if self.state == "speaking":
                ring_r = base_ring_r + math.sin(t * 3 + i * 0.7) * 20 * self.amplitude
                line_alpha = 0.12 + self.amplitude * 0.15
            elif self.state == "listening":
                ring_r = base_ring_r + math.sin(t * 1.5 + i) * 10
                line_alpha = 0.08
            elif self.state == "thinking":
                ring_r = base_ring_r + math.sin(t * 4 + i * 0.5) * 5
                line_alpha = 0.06
            else:
                ring_r = base_ring_r + math.sin(t * 0.5 + i * 0.5) * 3
                line_alpha = 0.04 + i * 0.005

            angle = math.radians(self.ring_angles[i])
            tilt = 0.2 + (i % 4) * 0.12
            points = []
            segments = 80
            for j in range(segments):
                a = j * (2 * math.pi / segments) + angle
                x = cx + ring_r * math.cos(a)
                y = cy + ring_r * tilt * math.sin(a)
                points.extend([x, y])

            if len(points) >= 6:
                color = self._gold(line_alpha)
                self.create_polygon(points, outline=color, fill="", width=0.5, smooth=True)

        # === KERN ===
        if self.state == "speaking":
            core_r = 42 + math.sin(t * 5) * 18 * self.amplitude
        elif self.state == "listening":
            core_r = 38 + math.sin(t * 2) * 10
        elif self.state == "thinking":
            core_r = 35 + math.sin(t * 8) * 6
        else:
            core_r = 32 + math.sin(t * 1) * 3

        # Kern-Schichten (mehr für besseren Glow)
        for i in range(12):
            r = core_r - i * 3
            if r <= 0: break
            alpha = 0.03 + i * 0.035
            if self.state == "speaking":
                alpha += self.amplitude * 0.06
            self.create_oval(cx-r, cy-r, cx+r, cy+r, fill=self._gold(alpha), outline="")

        # Kern Highlight
        hr = core_r * 0.25
        self.create_oval(cx-hr, cy-hr-core_r*0.2, cx+hr, cy+hr-core_r*0.2,
                         fill=self._gold(0.2), outline="")

        # === PARTIKEL ===
        for p in self.particles:
            speed_mult = 3 if self.state == "speaking" else 1.5 if self.state == "listening" else 1
            p["angle"] += p["speed"] * speed_mult

            alpha = 0.2 + 0.3 * math.sin(t * 2 + p["alpha_offset"])
            if self.state == "speaking":
                alpha = 0.4 + 0.5 * math.sin(t * 4 + p["alpha_offset"])

            dist = p["dist"]
            if self.state == "speaking":
                dist += math.sin(t * 3 + p["alpha_offset"]) * 25 * self.amplitude

            # Verschiedene Ebenen für 3D-Effekt
            tilt = [0.5, 0.35, 0.65][p["layer"]]
            x = cx + dist * math.cos(p["angle"])
            y = cy + dist * tilt * math.sin(p["angle"])
            s = p["size"]

            if self.state == "speaking":
                s *= (1 + self.amplitude * 0.5)

            self.create_oval(x-s, y-s, x+s, y+s, fill=self._gold(alpha), outline="")

        # === VERBINDUNGSLINIEN ===
        for i in range(0, len(self.particles), 3):
            p1 = self.particles[i]
            if i + 3 < len(self.particles):
                p2 = self.particles[i + 3]
                t1 = [0.5, 0.35, 0.65][p1["layer"]]
                t2 = [0.5, 0.35, 0.65][p2["layer"]]
                x1 = cx + p1["dist"] * math.cos(p1["angle"])
                y1 = cy + p1["dist"] * t1 * math.sin(p1["angle"])
                x2 = cx + p2["dist"] * math.cos(p2["angle"])
                y2 = cy + p2["dist"] * t2 * math.sin(p2["angle"])
                dist = math.sqrt((x2-x1)**2 + (y2-y1)**2)
                if dist < 100:
                    alpha = 0.04 * (1 - dist/100)
                    if self.state == "speaking": alpha *= 2
                    self.create_line(x1, y1, x2, y2, fill=self._gold(alpha), width=0.5)

        # === SPARKS (bei Zustandswechsel) ===
        alive_sparks = []
        for spark in self.sparks:
            spark["x"] += spark["vx"]
            spark["y"] += spark["vy"]
            spark["life"] -= spark["decay"]
            if spark["life"] > 0:
                sx = cx + spark["x"]
                sy = cy + spark["y"]
                s = spark["size"] * spark["life"]
                self.create_oval(sx-s, sy-s, sx+s, sy+s,
                               fill=self._gold(spark["life"] * 0.8), outline="")
                alive_sparks.append(spark)
        self.sparks = alive_sparks

        # === PULS-RING (beim Sprechen) ===
        if self.state == "speaking":
            pulse_r = 80 + (t * 60 % 100)
            pulse_alpha = max(0, 0.15 - (pulse_r - 80) / 100 * 0.15)
            if pulse_alpha > 0:
                self.create_oval(cx-pulse_r, cy-pulse_r*0.5, cx+pulse_r, cy+pulse_r*0.5,
                               outline=self._gold(pulse_alpha), width=1)

        # === LISTENING INDIKATOR ===
        if self.state == "listening":
            for i in range(3):
                dot_alpha = 0.3 + 0.3 * math.sin(t * 3 + i * 1)
                dot_x = cx - 15 + i * 15
                dot_y = cy + core_r + 30
                self.create_oval(dot_x-2, dot_y-2, dot_x+2, dot_y+2,
                               fill=self._gold(dot_alpha), outline="")

        self.after(25, self._animate)

    def _gold(self, alpha):
        alpha = max(0, min(1, alpha))
        r = int(min(255, 255 * alpha))
        g = int(min(255, 165 * alpha))
        b = int(min(255, 40 * alpha))
        return f"#{r:02x}{g:02x}{b:02x}"


class AssistantGUI:
    def __init__(self, brain, voice):
        self.brain = brain
        self.voice = voice
        self.message_queue = queue.Queue()
        self.running = True

        self.root = ctk.CTk()
        self.root.title(brain.name)
        self.root.geometry("620x750")
        self.root.minsize(400, 500)
        self.root.configure(fg_color="#050510")
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.bind("<F6>", self._toggle_mute)

        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        self._build_ui()
        self._start_listener()
        self._update_orb()
        self.root.after(100, self._process_queue)

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self.root, height=45, corner_radius=0, fg_color="#050510")
        header.pack(fill="x")
        header.pack_propagate(False)

        self.time_label = ctk.CTkLabel(header, text="", font=("Consolas", 14, "bold"),
                                        text_color="#ff9d2e")
        self.time_label.pack(side="left", padx=20)
        self._update_time()

        self.status_label = ctk.CTkLabel(header, text="● ONLINE",
                                          font=("Consolas", 11, "bold"),
                                          text_color="#00ff88")
        self.status_label.pack(side="right", padx=20)

        # Mute-Indikator
        self.mute_label = ctk.CTkLabel(header, text="", font=("Consolas", 10),
                                        text_color="#ff4444")
        self.mute_label.pack(side="right", padx=5)

        # Trennlinie
        ctk.CTkFrame(self.root, height=1, fg_color="#1a2a3c", corner_radius=0).pack(fill="x")

        # Hologramm
        self.orb = HologramOrb(self.root, width=620, height=420)
        self.orb.pack(fill="both", expand=True)

        # Status-Bereich
        status_frame = ctk.CTkFrame(self.root, fg_color="#050510", corner_radius=0)
        status_frame.pack(fill="x", padx=20)

        self.state_text = ctk.CTkLabel(status_frame, text="ONLINE // BEREIT",
                                        font=("Consolas", 14, "bold"),
                                        text_color="#ff9d2e")
        self.state_text.pack(pady=(8, 2))

        self.transcript = ctk.CTkLabel(status_frame, text="Ich höre zu, Boss.",
                                        font=("Consolas", 12),
                                        text_color="#8a7040",
                                        wraplength=520)
        self.transcript.pack(pady=(2, 4))

        # Letzte Antwort
        self.answer_frame = ctk.CTkFrame(self.root, fg_color="#0a0a18", corner_radius=10)
        self.answer_frame.pack(fill="x", padx=15, pady=(4, 8))

        self.last_answer = ctk.CTkLabel(self.answer_frame, text="",
                                         font=("Consolas", 11),
                                         text_color="#6a5a30",
                                         wraplength=540,
                                         justify="left",
                                         anchor="w")
        self.last_answer.pack(fill="x", padx=12, pady=8)

        # Footer
        footer = ctk.CTkFrame(self.root, height=28, corner_radius=0, fg_color="#050510")
        footer.pack(fill="x")
        footer.pack_propagate(False)

        ctk.CTkLabel(footer, text="AUDIO INPUT ● AKTIV", font=("Consolas", 8),
                     text_color="#1a2a10").pack(side="left", padx=20)
        ctk.CTkLabel(footer, text="F6 = MUTE", font=("Consolas", 8),
                     text_color="#1a2a10").pack(side="right", padx=20)

    def _toggle_mute(self, event=None):
        self.brain.muted = not self.brain.muted
        if self.brain.muted:
            self.mute_label.configure(text="MUTED")
            self.message_queue.put(("status", "MUTED", "#ff4444"))
            self.message_queue.put(("speak", "Stumm, Boss. F6 zum Reaktivieren.", None))
        else:
            self.mute_label.configure(text="")
            self.message_queue.put(("status", "● ONLINE", "#00ff88"))
            self.message_queue.put(("speak", "Ich höre wieder zu, Boss.", None))

    def _update_time(self):
        now = datetime.datetime.now()
        self.time_label.configure(text=now.strftime("%H:%M:%S"))
        if self.running:
            self.root.after(1000, self._update_time)

    def _update_orb(self):
        self.orb.set_state(self.voice.state)
        self.orb.set_amplitude(self.voice.amplitude)
        if self.running:
            self.root.after(25, self._update_orb)

    def _start_listener(self):
        def listen_loop():
            self.voice.play_sound("startup")
            time.sleep(0.5)
            self.message_queue.put(("speak", f"{self.brain.name} ist online. Ich höre zu, Boss.", None))

            bday = self.brain.get_birthday_message()
            if bday:
                time.sleep(2)
                self.message_queue.put(("answer", bday, None))
                self.message_queue.put(("speak", bday, None))

            while self.running:
                if self.voice.is_speaking:
                    time.sleep(0.1)
                    continue

                self.message_queue.put(("status", "LISTENING...", "#ff9d2e"))
                self.message_queue.put(("transcript", "Ich höre zu, Boss.", None))

                interrupt = self.voice.get_interrupt_text()
                text = interrupt if interrupt else self.voice.listen()

                if not text: continue

                if text.strip() in ["beenden", "stopp", "exit", "tschüss"]:
                    self.message_queue.put(("speak", "Bis dann, Boss.", None))
                    time.sleep(2)
                    self.message_queue.put(("quit", None, None))
                    break

                self.message_queue.put(("user_said", text, None))
                self._process_input(text)

        threading.Thread(target=listen_loop, daemon=True).start()

    def _process_input(self, text):
        self.voice.play_sound("listen")

        def process():
            self.message_queue.put(("status", "VERARBEITE...", "#ffaa00"))
            self.voice.state = "thinking"
            answer = self.brain.process(text)
            if answer:
                self.message_queue.put(("answer", answer, None))
                self.message_queue.put(("speak", answer, None))

                timer = self.brain.get_pending_timer()
                if timer:
                    def rt():
                        time.sleep(timer["seconds"])
                        self.voice.play_sound("notify")
                        msg = f"Timer! {timer['label']} um, Boss."
                        self.message_queue.put(("answer", msg, None))
                        self.message_queue.put(("speak", msg, None))
                    threading.Thread(target=rt, daemon=True).start()

                rem = self.brain.get_pending_reminder()
                if rem:
                    def rr():
                        time.sleep(rem["seconds"])
                        self.voice.play_sound("notify")
                        msg = f"Boss, Erinnerung: {rem['task']}"
                        self.message_queue.put(("answer", msg, None))
                        self.message_queue.put(("speak", msg, None))
                    threading.Thread(target=rr, daemon=True).start()

            self.message_queue.put(("status", "● ONLINE", "#00ff88"))

        threading.Thread(target=process, daemon=True).start()

    def _process_queue(self):
        try:
            while True:
                t, text, extra = self.message_queue.get_nowait()
                if t == "speak":
                    threading.Thread(target=self.voice.speak, args=(text,), daemon=True).start()
                elif t == "status":
                    self.state_text.configure(text=text, text_color=extra or "#ff9d2e")
                    self.status_label.configure(text=f"● {text.split('//')[0].strip()}", text_color=extra or "#00ff88")
                elif t == "transcript":
                    self.transcript.configure(text=text, text_color="#8a7040")
                elif t == "user_said":
                    self.transcript.configure(text=f'"{text}"', text_color="#c0a050")
                elif t == "answer":
                    display = text[:300] + "..." if len(text) > 300 else text
                    self.last_answer.configure(text=display)
                elif t == "quit":
                    self.quit(); return
        except queue.Empty:
            pass
        if self.running:
            self.root.after(100, self._process_queue)

    def quit(self):
        self.running = False
        self.root.destroy()

    def run(self):
        self.root.mainloop()