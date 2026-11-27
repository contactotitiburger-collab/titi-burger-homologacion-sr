#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import imaplib, email, json, re
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
imaplib._MAXLINE = 10_000_000
def dh(s):
    if not s: return ""
    try: return str(make_header(decode_header(s)))
    except Exception: return s

y = json.load(open("/home/tito/.openclaw/credentials/yahoo/creds.json"))
M = imaplib.IMAP4_SSL(y["imap_host"], y["imap_port"]); M.login(y["user"], y["password"])

# 1) conteo TOTAL por carpeta contable/relevante (sin SINCE) y rango de fechas
probe_folders = ["TIMSA","timsa stefany","SAT","FACTURAS","cortes titi  burgers",
                 "BANCO BANAMEX","BAJIO","fernando garcia","spinm","viruett",
                 "JUAN PEDRO (HOLGAZAN)","imss","Inbox"]
for f in probe_folders:
    try:
        M.select(f'"{f}"', readonly=True)
        typ,d = M.search(None,"ALL")
        ids = d[0].split() if d and d[0] else []
        n = len(ids)
        # primeras/ultimas fechas y remitentes de muestra
        sample = []
        for num in (ids[:2]+ids[-3:] if n>3 else ids):
            typ,md = M.fetch(num,"(BODY.PEEK[HEADER.FIELDS (FROM DATE SUBJECT)])")
            if typ=="OK" and md and isinstance(md[0],tuple):
                msg = email.message_from_bytes(md[0][1])
                sample.append(f"{(msg.get('Date') or '')[:16]} | {dh(msg.get('From'))[:45]} | {dh(msg.get('Subject'))[:50]}")
        print(f"\n### {f}: {n} mensajes TOTAL")
        for s in sample: print("   ", s)
    except Exception as e:
        print(f"### {f}: ERROR {e}")

# 2) el correo de estados financieros REALES (2024-04-12) — ver remitente original / cuerpo
print("\n\n===== BUSCAR 'estados financieros' original (remitente contador) en Sent+Inbox =====")
for f in ["Sent","Inbox","Archive"]:
    M.select(f'"{f}"', readonly=True)
    typ,d = M.search("UTF-8","SUBJECT","estados financieros")
    if typ!="OK" or not d or not d[0]:
        typ,d = M.search(None,"SUBJECT","financieros")
    ids = d[0].split() if d and d[0] else []
    for num in ids:
        typ,md = M.fetch(num,"(BODY.PEEK[])")
        if typ!="OK" or not md: continue
        raw=b"".join(p[1] for p in md if isinstance(p,tuple) and p[1])
        msg=email.message_from_bytes(raw)
        body=""
        for p in msg.walk():
            if p.get_content_type()=="text/plain" and "attachment" not in str(p.get("Content-Disposition") or ""):
                try: body+= (p.get_payload(decode=True) or b"").decode(errors="replace")
                except: pass
        print(f"\n--- [{f}] {(msg.get('Date') or '')[:16]}")
        print("FROM:", dh(msg.get('From')))
        print("TO:", dh(msg.get('To')))
        print("SUBJECT:", dh(msg.get('Subject')))
        print("BODY:", body.strip()[:600])
M.logout()
