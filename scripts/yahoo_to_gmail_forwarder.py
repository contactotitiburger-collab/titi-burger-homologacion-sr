#!/usr/bin/env python3
"""Reenvía correos de Rappi, DiDi y Uber desde Yahoo IMAP hacia Gmail (contactotitiburger@gmail.com).

Modo normal (cron): procesa solo correos con UID > último guardado por app.
Modo backfill (--backfill): procesa TODO el histórico con delay entre envíos.

Estado: ~/.openclaw/state/yahoo_forwarder.json
Log: ~/.openclaw/logs/yahoo_forwarder.log
"""
import argparse
import imaplib
import json
import smtplib
import ssl
import sys
import time
from datetime import datetime
from email.message import EmailMessage
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path

YAHOO_CREDS = Path.home() / ".openclaw/credentials/yahoo/creds.json"
GMAIL_CREDS = Path.home() / ".openclaw/credentials/gmail/creds.json"
STATE_FILE = Path.home() / ".openclaw/state/yahoo_forwarder.json"
LOG_FILE = Path.home() / ".openclaw/logs/yahoo_forwarder.log"

APPS = {
    "uber":  {"from_substrings": ["uber.com"]},
    "rappi": {"from_substrings": ["TECNOLOGIAS RAPPI"]},
    "didi":  {"from_substrings": ["didiglobal.com"]},
}

DEST_EMAIL = "contactotitiburger@gmail.com"


def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts}  {msg}"
    print(line, flush=True)
    with LOG_FILE.open("a") as f:
        f.write(line + "\n")


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    return json.loads(STATE_FILE.read_text())


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def imap_search_uids(M, from_substr: str) -> list[int]:
    typ, data = M.uid("SEARCH", None, f'FROM "{from_substr}"')
    if typ != "OK" or not data or not data[0]:
        return []
    return sorted(int(x) for x in data[0].split())


def fetch_raw(M, uid: int) -> bytes | None:
    typ, data = M.uid("FETCH", str(uid).encode(), "(BODY.PEEK[])")
    if typ != "OK" or not data:
        return None
    for chunk in data:
        if isinstance(chunk, tuple) and len(chunk) >= 2:
            return chunk[1]
    return None


def parse_header(raw: bytes, field: str) -> str:
    for line in raw.split(b"\n", 200):
        line_s = line.decode("utf-8", errors="ignore").rstrip("\r")
        if line_s.lower().startswith(field.lower() + ":"):
            return line_s[len(field) + 1 :].strip()
    return ""


def forward_email(smtp, app: str, uid: int, raw: bytes) -> bool:
    original_subject = parse_header(raw, "Subject") or "(sin asunto)"
    original_from = parse_header(raw, "From") or "(desconocido)"
    original_date = parse_header(raw, "Date") or ""

    msg = MIMEMultipart()
    msg["From"] = DEST_EMAIL
    msg["To"] = DEST_EMAIL
    msg["Subject"] = f"[Yahoo→Gmail | {app.upper()}] {original_subject}"

    body = (
        f"Reenviado automáticamente desde titiburger_cordova@yahoo.com.mx\n"
        f"App: {app.upper()}\n"
        f"Yahoo UID: {uid}\n"
        f"---\n"
        f"From: {original_from}\n"
        f"Date: {original_date}\n"
        f"Subject: {original_subject}\n"
    )
    msg.attach(MIMEText(body, "plain", "utf-8"))

    attachment = MIMEBase("message", "rfc822")
    attachment.set_payload(raw)
    attachment.add_header(
        "Content-Disposition",
        f'attachment; filename="{app}_{uid}.eml"',
    )
    msg.attach(attachment)

    smtp.send_message(msg)
    return True


def run(backfill: bool, dry_run: bool, limit: int | None) -> None:
    yc = json.loads(YAHOO_CREDS.read_text())
    gc = json.loads(GMAIL_CREDS.read_text())

    yahoo_user = yc.get("user") or yc.get("email")
    yahoo_pass = yc.get("app_password") or yc.get("password")
    gmail_user = gc.get("user") or gc.get("email")
    gmail_pass = gc.get("app_password") or gc.get("password")

    state = load_state()
    state.setdefault("last_uid", {"uber": 0, "rappi": 0, "didi": 0})

    log(f"START | backfill={backfill} dry_run={dry_run} limit={limit}")

    M = imaplib.IMAP4_SSL("imap.mail.yahoo.com")
    M.login(yahoo_user, yahoo_pass)
    M.select("INBOX", readonly=True)

    smtp = None
    if not dry_run:
        smtp = smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context())
        smtp.login(gmail_user, gmail_pass)

    total_sent = 0
    try:
        for app, cfg in APPS.items():
            last_uid = state["last_uid"].get(app, 0) if not backfill else 0
            all_uids = []
            for sub in cfg["from_substrings"]:
                all_uids.extend(imap_search_uids(M, sub))
            uids = sorted(set(u for u in all_uids if u > last_uid))
            log(f"[{app}] {len(uids)} correos por reenviar (last_uid={last_uid})")

            if limit is not None:
                uids = uids[:limit]

            for uid in uids:
                raw = fetch_raw(M, uid)
                if not raw:
                    log(f"[{app}] UID {uid}: fetch vacío, salto")
                    continue
                if dry_run:
                    log(f"[{app}] UID {uid}: DRY-RUN — {parse_header(raw, 'Subject')[:80]}")
                else:
                    try:
                        forward_email(smtp, app, uid, raw)
                        state["last_uid"][app] = max(state["last_uid"].get(app, 0), uid)
                        save_state(state)
                        total_sent += 1
                        log(f"[{app}] UID {uid}: OK")
                        time.sleep(3 if backfill else 1)
                    except Exception as e:
                        log(f"[{app}] UID {uid}: ERROR {e}")
                        time.sleep(5)
    finally:
        if smtp:
            smtp.quit()
        M.logout()

    log(f"END | total_sent={total_sent}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--backfill", action="store_true", help="procesar TODO el histórico")
    p.add_argument("--dry-run", action="store_true", help="no manda, solo simula")
    p.add_argument("--limit", type=int, default=None, help="máx correos por app (para pruebas)")
    args = p.parse_args()
    run(backfill=args.backfill, dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    main()
