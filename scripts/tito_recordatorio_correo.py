#!/usr/bin/env python3
"""Recordatorio simple de Tito por correo (Yahoo SMTP -> Gmail).
Uso: tito_recordatorio_correo.py --asunto "..." --mensaje "..." [--to correo]
Canal de respaldo cuando WhatsApp está apagado.
"""
import argparse
import json
import smtplib
import ssl
from email.mime.text import MIMEText
from pathlib import Path

YAHOO_CREDS = Path.home() / ".openclaw/credentials/yahoo/creds.json"
DEFAULT_TO = "contactotitiburger@gmail.com"
YAHOO_SMTP = "smtp.mail.yahoo.com"
YAHOO_PORT = 465


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asunto", required=True)
    ap.add_argument("--mensaje", required=True)
    ap.add_argument("--to", default=DEFAULT_TO)
    args = ap.parse_args()

    yc = json.loads(YAHOO_CREDS.read_text())
    user = yc.get("user") or yc.get("email") or "titiburger_cordova@yahoo.com.mx"
    passwd = yc.get("app_password") or yc.get("password")

    msg = MIMEText(args.mensaje, "plain", "utf-8")
    msg["Subject"] = args.asunto
    msg["From"] = user
    msg["To"] = args.to

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(YAHOO_SMTP, YAHOO_PORT, context=ctx) as s:
        s.login(user, passwd)
        s.send_message(msg)
    print(f"OK enviado a {args.to}: {args.asunto}")


if __name__ == "__main__":
    main()
