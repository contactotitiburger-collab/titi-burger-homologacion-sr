#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import imaplib, email, json
from email.header import decode_header, make_header
imaplib._MAXLINE = 10_000_000
def dh(s):
    if not s: return ""
    try: return str(make_header(decode_header(s)))
    except Exception: return s

y = json.load(open("/home/tito/.openclaw/credentials/yahoo/creds.json"))
M = imaplib.IMAP4_SSL(y["imap_host"], y["imap_port"]); M.login(y["user"], y["password"])

# 1) email real de estados financieros: remitente y cuerpo
print("===== estados financieros originales (ASCII search) =====")
for f in ["Sent","Inbox","Archive","Draft"]:
    M.select(f'"{f}"', readonly=True)
    typ,d = M.search(None,"SUBJECT","financieros")
    ids = d[0].split() if typ=="OK" and d and d[0] else []
    for num in ids:
        typ,md = M.fetch(num,"(BODY.PEEK[])")
        if typ!="OK" or not md: continue
        raw=b"".join(p[1] for p in md if isinstance(p,tuple) and p[1])
        msg=email.message_from_bytes(raw)
        body=""
        for p in msg.walk():
            if p.get_content_type()=="text/plain" and "attachment" not in str(p.get("Content-Disposition") or ""):
                try: body+=(p.get_payload(decode=True) or b"").decode(errors="replace")
                except: pass
        print(f"\n--- [{f}] {(msg.get('Date') or '')[:16]}")
        print("FROM:", dh(msg.get('From')), "| TO:", dh(msg.get('To')), "| CC:", dh(msg.get('Cc')))
        print("SUBJ:", dh(msg.get('Subject')))
        print("BODY:", " ".join(body.split())[:500])

# 2) PAGINAR Inbox y BAJIO por ventanas de fecha para vencer el cap de 1000, buscar terminos financieros fuertes
print("\n\n===== PAGINADO buscar terminos financieros fuertes (vencer cap 1000) =====")
STRONG = ["financieros","resultados","balance","balanza","posicion financiera","declaracion anual","contabilidad"]
windows = [("01-Sep-2023","01-Jan-2024"),("01-Jan-2024","01-Jul-2024"),("01-Jul-2024","01-Jan-2025"),
           ("01-Jan-2025","01-Jul-2025"),("01-Jul-2025","01-Jan-2026"),("01-Jan-2026","02-Sep-2026")]
for f in ["Inbox","BAJIO","Archive","Bulk"]:
    M.select(f'"{f}"', readonly=True)
    hits={}
    for (a,b) in windows:
        for t in STRONG:
            try:
                typ,d = M.search(None, f'(SINCE "{a}" BEFORE "{b}" SUBJECT "{t}")')
            except Exception: continue
            for num in (d[0].split() if typ=="OK" and d and d[0] else []):
                hits[num.decode()]=1
    print(f"\n### {f}: {len(hits)} candidatos por asunto (STRONG, paginado)")
    for num in list(hits)[:40]:
        typ,md=M.fetch(num.encode(),"(BODY.PEEK[HEADER.FIELDS (FROM DATE SUBJECT)])")
        if typ=="OK" and md and isinstance(md[0],tuple):
            msg=email.message_from_bytes(md[0][1])
            print(f"   {(msg.get('Date') or '')[:16]} | {dh(msg.get('From'))[:38]} | {dh(msg.get('Subject'))[:55]}")
M.logout()
