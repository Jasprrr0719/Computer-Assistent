"""
Email – Sendet Emails über SMTP (Gmail/Outlook).
Prüft neue Emails über IMAP.
"""

import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import os
import sys
import json

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class EmailTool:
    def __init__(self, config=None):
        config = config or {}
        self.email_user = config.get("email_user", os.getenv("EMAIL_USER", ""))
        self.email_pass = config.get("email_pass", os.getenv("EMAIL_PASS", ""))
        self.email_provider = config.get("email_provider", "gmail")  # gmail oder outlook
        self.enabled = bool(self.email_user and self.email_pass)

        self.smtp_servers = {
            "gmail": ("smtp.gmail.com", 587),
            "outlook": ("smtp.office365.com", 587),
            "gmx": ("mail.gmx.net", 587),
            "web.de": ("smtp.web.de", 587),
        }

        self.imap_servers = {
            "gmail": ("imap.gmail.com", 993),
            "outlook": ("outlook.office365.com", 993),
            "gmx": ("imap.gmx.net", 993),
            "web.de": ("imap.web.de", 993),
        }

    def send_email(self, to="", subject="", body=""):
        """Sendet eine Email."""
        if not self.enabled:
            return "Email nicht konfiguriert. Setze EMAIL_USER und EMAIL_PASS in der .env Datei."

        if not to or not subject:
            return "Empfänger und Betreff werden benötigt."

        try:
            msg = MIMEMultipart()
            msg["From"] = self.email_user
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            server_info = self.smtp_servers.get(self.email_provider, self.smtp_servers["gmail"])
            server = smtplib.SMTP(server_info[0], server_info[1])
            server.starttls()
            server.login(self.email_user, self.email_pass)
            server.send_message(msg)
            server.quit()

            return f"Email an {to} gesendet."
        except smtplib.SMTPAuthenticationError:
            return "Email Login fehlgeschlagen. Prüfe Benutzername und Passwort."
        except Exception as e:
            return f"Email-Fehler: {e}"

    def check_emails(self, count=5):
        """Prüft die neuesten Emails."""
        if not self.enabled:
            return "Email nicht konfiguriert."

        try:
            server_info = self.imap_servers.get(self.email_provider, self.imap_servers["gmail"])
            mail = imaplib.IMAP4_SSL(server_info[0], server_info[1])
            mail.login(self.email_user, self.email_pass)
            mail.select("inbox")

            _, messages = mail.search(None, "ALL")
            msg_ids = messages[0].split()

            if not msg_ids:
                mail.logout()
                return "Keine Emails gefunden."

            # Letzte N Emails
            latest = msg_ids[-count:]
            latest.reverse()

            result = f"Letzte {min(count, len(latest))} Emails: "

            for msg_id in latest:
                _, data = mail.fetch(msg_id, "(RFC822)")
                raw = email.message_from_bytes(data[0][1])
                sender = email.utils.parseaddr(raw["From"])[1]
                subject = raw["Subject"] or "Kein Betreff"
                # Betreff dekodieren
                if subject:
                    decoded = email.header.decode_header(subject)
                    subject = ""
                    for part, enc in decoded:
                        if isinstance(part, bytes):
                            subject += part.decode(enc or "utf-8", errors="replace")
                        else:
                            subject += str(part)

                result += f"Von {sender}: {subject[:50]}. "

            mail.logout()
            return result

        except imaplib.IMAP4.error as e:
            return f"Email Login fehlgeschlagen: {e}"
        except Exception as e:
            return f"Email-Fehler: {e}"

    def handle(self, text):
        """Verarbeitet Email-Befehle aus Spracheingabe."""
        text_lower = text.lower().strip()

        # Emails checken
        if any(w in text_lower for w in ["emails checken", "emails prüfen", "neue emails",
                                          "meine emails", "posteingang", "inbox"]):
            return self.check_emails()

        # Email senden: "schreib eine email an test@mail.com betreff Meeting text Morgen um 10"
        send_match = re.search(
            r"(?:email|mail)\s+(?:an\s+)?([\w.+-]+@[\w-]+\.[\w.]+)\s+(?:betreff\s+)?(.+?)(?:\s+(?:text|inhalt|nachricht)\s+(.+))?$",
            text_lower
        )
        if send_match:
            to = send_match.group(1)
            subject = send_match.group(2).strip()
            body = send_match.group(3).strip() if send_match.group(3) else subject
            return self.send_email(to=to, subject=subject, body=body)

        # KI soll Email schreiben
        if any(w in text_lower for w in ["schreib eine email", "email schreiben", "mail schreiben"]):
            return "EMAIL_AI_GENERATE"  # Signal für brain.py

        return None