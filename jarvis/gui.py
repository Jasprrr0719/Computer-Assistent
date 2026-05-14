"""
GUI mit Wellenform-Animation und Sound-Effekten.
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

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class WaveformCanvas(ctk.CTkCanvas):
    """Animierte Wellenform die auf Sprach-Amplitude reagiert."""
    def __init__(self, master, **kwargs):
        super().__init__(master, bg="#0a0a1a", highlightthickness=0, **kwargs)
        self.bars = 24
        self.amplitude = 0.0
        self.target_amplitude = 0.0
        self.bar_heights = [0.0] * self.bars
        self._animate()

    def set_amplitude(self, amp):
        self.target_amplitude = amp

    def _animate(self):
        # Smooth interpolation
        self.amplitude += (self.target_amplitude - self.amplitude) * 0.3

        w = self.winfo_width() or 200
        h = self.winfo_height() or 40
        self.delete("all")

        bar_width = max(2, (w / self.bars) - 2)
        spacing = w / self.bars

        for i in range(self.bars):
            # Wellenform-Pattern
            wave = math.sin(time.time() * 3 + i * 0.5) * 0.3 + 0.7
            noise = random.random() * 0.2
            target = self.amplitude * wave * (0.3 + noise) * h * 0.8

            # Smooth per bar
            self.bar_heights[i] += (target - self.bar_heights[i]) * 0.4
            bar_h = max(2, self.bar_heights[i])

            x = i * spacing + spacing / 2
            y_top = (h - bar_h) / 2
            y_bot = (h + bar_h) / 2

            # Farbe basierend auf Höhe
            intensity = min(1.0, bar_h / (h * 0.6))
            r_val = int(0 + intensity * 30)
            g_val = int(180 + intensity * 75)
            b_val = int(100 + intensity * 55)
            color = f"#{r_val:02x}{g_val:02x}{b_val:02x}"

            self.create_rectangle(
                x - bar_width/2, y_top, x + bar_width/2, y_bot,
                fill=color, outline=""
            )

        self.after(30, self._animate)


class AssistantGUI:
    def __init__(self, brain, voice):
        self.brain = brain
        self.voice = voice
        self.message_queue = queue.Queue()
        self.running = True

        self.root = ctk.CTk()
        self.root.title(f"{brain.name} – KI-Assistent")
        self.root.geometry("520x750")
        self.root.minsize(400, 500)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        self._build_ui()
        self._start_listener()
        self._update_waveform()
        self.root.after(100, self._process_queue)

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self.root, height=70, corner_radius=0, fg_color="#0a0a1a")
        header.pack(fill="x")
        header.pack_propagate(False)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", padx=20, pady=10)

        self.status_dot = ctk.CTkLabel(left, text="●", font=("Arial", 22), text_color="#00ff88")
        self.status_dot.pack(side="left", padx=(0, 10))

        name_frame = ctk.CTkFrame(left, fg_color="transparent")
        name_frame.pack(side="left")
        ctk.CTkLabel(name_frame, text=self.brain.name.upper(), font=("Consolas", 20, "bold"), text_color="#ffffff").pack(anchor="w")
        ctk.CTkLabel(name_frame, text="KI-ASSISTENT", font=("Consolas", 9), text_color="#444444").pack(anchor="w")

        self.status_label = ctk.CTkLabel(header, text="● ONLINE", font=("Consolas", 11, "bold"), text_color="#00ff88")
        self.status_label.pack(side="right", padx=20)

        # Wellenform
        self.waveform = WaveformCanvas(self.root, height=45)
        self.waveform.pack(fill="x")

        ctk.CTkFrame(self.root, height=1, fg_color="#1a3a5c", corner_radius=0).pack(fill="x")

        # Chat
        self.chat_frame = ctk.CTkScrollableFrame(self.root, fg_color="#0d0d1a", corner_radius=0,
                                                   scrollbar_button_color="#1a3a5c")
        self.chat_frame.pack(fill="both", expand=True)

        ctk.CTkFrame(self.root, height=1, fg_color="#1a3a5c", corner_radius=0).pack(fill="x")

        # Input
        bottom = ctk.CTkFrame(self.root, height=60, corner_radius=0, fg_color="#0a0a1a")
        bottom.pack(fill="x")
        bottom.pack_propagate(False)

        self.input_field = ctk.CTkEntry(bottom, placeholder_text="Nachricht eingeben...",
                                         font=("Consolas", 13), height=40,
                                         fg_color="#111128", border_color="#1a3a5c", border_width=1,
                                         text_color="#e0e0e0", corner_radius=8)
        self.input_field.pack(side="left", fill="x", expand=True, padx=(15, 10), pady=10)
        self.input_field.bind("<Return>", self._on_text_input)

        ctk.CTkButton(bottom, text="➤", width=40, height=40, font=("Arial", 16),
                      fg_color="#0f3460", hover_color="#1a5276", corner_radius=8,
                      command=lambda: self._on_text_input(None)).pack(side="right", padx=(0, 15), pady=10)

        self._add_message(f"{self.brain.name} ist online. Ich höre zu, Chef.", "assistant")

    def _add_message(self, text, role="assistant"):
        is_user = role == "user"
        outer = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        outer.pack(fill="x", padx=10, pady=3)

        bubble = ctk.CTkFrame(outer, fg_color="#0f3460" if is_user else "#1a1a3e", corner_radius=14)
        bubble.pack(side="right" if is_user else "left", anchor="e" if is_user else "w")

        hdr = ctk.CTkFrame(bubble, fg_color="transparent")
        hdr.pack(fill="x", padx=12, pady=(8, 0))
        ctk.CTkLabel(hdr, text="Du" if is_user else self.brain.name,
                     font=("Consolas", 10, "bold"),
                     text_color="#6ab0de" if is_user else "#00ff88").pack(side="left")
        ctk.CTkLabel(hdr, text=datetime.datetime.now().strftime("%H:%M"),
                     font=("Consolas", 9), text_color="#444444").pack(side="right")

        ctk.CTkLabel(bubble, text=text, font=("Consolas", 12),
                     text_color="#c8e6ff" if is_user else "#d0d0d0",
                     wraplength=380, justify="left", anchor="w").pack(fill="x", padx=12, pady=(4, 10))

        self.root.after(50, lambda: self.chat_frame._parent_canvas.yview_moveto(1.0))

    def _update_waveform(self):
        self.waveform.set_amplitude(self.voice.amplitude)
        if self.running:
            self.root.after(30, self._update_waveform)

    def _on_text_input(self, event):
        text = self.input_field.get().strip()
        if not text: return
        self.input_field.delete(0, "end")
        self._process_input(text)

    def _process_input(self, text):
        self.message_queue.put(("user", text, None))
        self.voice.play_sound("listen")

        def process():
            self.message_queue.put(("status", "Denke nach...", "#ffaa00"))
            answer = self.brain.process(text)
            if answer:
                self.message_queue.put(("assistant", answer, None))
                self.message_queue.put(("speak", answer, None))

                timer = self.brain.get_pending_timer()
                if timer:
                    def run_t():
                        time.sleep(timer["seconds"])
                        self.voice.play_sound("notify")
                        msg = f"Timer abgelaufen! {timer['label']} sind um, Chef."
                        self.message_queue.put(("assistant", msg, None))
                        self.message_queue.put(("speak", msg, None))
                    threading.Thread(target=run_t, daemon=True).start()

                reminder = self.brain.get_pending_reminder()
                if reminder:
                    def run_r():
                        time.sleep(reminder["seconds"])
                        self.voice.play_sound("notify")
                        msg = f"Chef, Erinnerung: {reminder['task']}"
                        self.message_queue.put(("assistant", msg, None))
                        self.message_queue.put(("speak", msg, None))
                    threading.Thread(target=run_r, daemon=True).start()

            self.message_queue.put(("status", "● ONLINE", "#00ff88"))

        threading.Thread(target=process, daemon=True).start()

    def _start_listener(self):
        def listen_loop():
            self.voice.play_sound("startup")
            time.sleep(0.5)
            self.message_queue.put(("speak", f"{self.brain.name} ist online. Ich höre zu, Chef.", None))

            while self.running:
                if self.voice.is_speaking:
                    time.sleep(0.1)
                    continue

                self.message_queue.put(("status", "● ONLINE", "#00ff88"))
                interrupt = self.voice.get_interrupt_text()
                text = interrupt if interrupt else self.voice.listen()

                if not text: continue

                if text.strip() in ["beenden", "stopp", "exit", "tschüss"]:
                    self.message_queue.put(("speak", "Bis dann, Chef.", None))
                    time.sleep(2)
                    self.message_queue.put(("quit", None, None))
                    break

                self._process_input(text)

        threading.Thread(target=listen_loop, daemon=True).start()

    def _process_queue(self):
        try:
            while True:
                t, text, extra = self.message_queue.get_nowait()
                if t == "user": self._add_message(text, "user")
                elif t == "assistant": self._add_message(text, "assistant")
                elif t == "speak": threading.Thread(target=self.voice.speak, args=(text,), daemon=True).start()
                elif t == "status":
                    self.status_label.configure(text=text, text_color=extra or "#00ff88")
                    self.status_dot.configure(text_color=extra or "#00ff88")
                elif t == "quit": self.quit(); return
        except queue.Empty: pass
        if self.running: self.root.after(100, self._process_queue)

    def quit(self):
        self.running = False
        self.root.destroy()

    def run(self):
        self.root.mainloop()