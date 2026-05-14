"""
Discord Bot – Einfacher Bot der Nachrichten senden und lesen kann.
"""

import threading
import os
import sys
import json
import asyncio

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")


class DiscordTool:
    def __init__(self, config=None):
        config = config or {}
        self.token = config.get("discord_token", DISCORD_TOKEN)
        self.enabled = bool(self.token)
        self.bot = None
        self.last_messages = []
        self._ready = False

    def start_bot(self):
        """Startet den Discord Bot im Hintergrund."""
        if not self.enabled:
            print("  Discord Bot: Kein Token gesetzt.")
            return

        try:
            import discord

            intents = discord.Intents.default()
            intents.message_content = True
            self.bot = discord.Client(intents=intents)

            @self.bot.event
            async def on_ready():
                self._ready = True
                print(f"  Discord Bot online: {self.bot.user}")

            @self.bot.event
            async def on_message(message):
                if message.author == self.bot.user:
                    return
                self.last_messages.append({
                    "author": str(message.author),
                    "content": message.content[:200],
                    "channel": str(message.channel),
                    "time": message.created_at.strftime("%H:%M"),
                })
                # Nur letzte 50 speichern
                self.last_messages = self.last_messages[-50:]

            def run_bot():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.bot.start(self.token))

            thread = threading.Thread(target=run_bot, daemon=True)
            thread.start()

        except ImportError:
            print("  discord.py nicht installiert: pip install discord.py")
        except Exception as e:
            print(f"  Discord Bot Fehler: {e}")

    def send_message(self, channel_name="", message=""):
        """Sendet eine Nachricht in einen Discord-Kanal."""
        if not self.bot or not self._ready:
            return "Discord Bot ist nicht verbunden."
        if not message:
            return "Keine Nachricht angegeben."

        try:
            for guild in self.bot.guilds:
                for channel in guild.text_channels:
                    if channel_name.lower() in channel.name.lower():
                        asyncio.run_coroutine_threadsafe(
                            channel.send(message),
                            self.bot.loop
                        )
                        return f"Nachricht in #{channel.name} gesendet."
            return f"Kanal '{channel_name}' nicht gefunden."
        except Exception as e:
            return f"Discord Fehler: {e}"

    def get_recent_messages(self, count=5):
        """Gibt die letzten Nachrichten zurück."""
        if not self.last_messages:
            return "Keine neuen Discord-Nachrichten."
        result = "Letzte Discord-Nachrichten: "
        for msg in self.last_messages[-count:]:
            result += f"{msg['author']} in #{msg['channel']}: {msg['content'][:60]}. "
        return result

    def handle(self, text):
        """Verarbeitet Discord-Befehle."""
        text_lower = text.lower().strip()

        # Nachrichten lesen
        if any(w in text_lower for w in ["discord nachrichten", "discord messages",
                                          "was gibt es auf discord", "neue discord"]):
            return self.get_recent_messages()

        # Nachricht senden: "discord nachricht in general: hey leute"
        import re
        send_match = re.search(
            r"discord\s+(?:nachricht|message|schreib)\s+(?:in\s+)?(\w+)[\s:]+(.+)",
            text_lower
        )
        if send_match:
            channel = send_match.group(1).strip()
            message = send_match.group(2).strip()
            return self.send_message(channel_name=channel, message=message)

        return None