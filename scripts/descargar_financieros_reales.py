#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Descarga TODOS los adjuntos de correos cuyo asunto trae 'financieros'
(estados financieros propiamente dichos), en Sent/Inbox/Archive/Draft."""
import imaplib, email, json, os, re, hashlib
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
imaplib._MAXLINE = 10_000_000
BASE = "/home/tito/.openclaw/data/estados_financieros"
def dh(s):
    if not s: return ""
    try: return str(make_header(decode_header(s)))
    except Exception: return s
def norm(s): return (s or "").lower().translate(str.maketrans("áéíóúñü","aeiounu"))
def safe(s,n=40): return (re.sub(r"[^a-z0-9]+","_",norm(s)).strip("_")[:n]) or "sin"
DL_EXT={".pdf",".xlsx",".xls",".csv",".xml",".zip"}

y=json.load(open("/home/tito/.openclaw/credentials/yahoo/creds.json"))
M=imaplib.IMAP4_SSL(y["imap_host"],y["imap_port"]); M.login(y["user"],y["password"])
report=[]
for f in ["Sent","Inbox","Archive","Draft","Synced Messages"]:
    typ,_=M.select(f'"{f}"',readonly=True)
    if typ!="OK": continue
    typ,d=M.search(None,"SUBJECT","financieros")
    ids=d[0].split() if typ=="OK" and d and d[0] else []
    for num in ids:
        typ,md=M.fetch(num,"(BODY.PEEK[])")
        if typ!="OK" or not md: continue
        raw=b"".join(p[1] for p in md if isinstance(p,tuple) and p[1])
        msg=email.message_from_bytes(raw)
        subj=dh(msg.get("Subject","")); frm=dh(msg.get("From","")); to=dh(msg.get("To",""))
        try:
            dt=parsedate_to_datetime(msg.get("Date","")); dstr=dt.strftime("%Y-%m-%d"); year=dt.year
        except Exception: dstr=(msg.get("Date","") or "")[:10]; year=0
        # solo estados financieros de negocio/persona, no cursos CETYS ni ruido
        if any(x in norm(frm) for x in ["cetys","vevor","macys","roadrunner","camp.","wordpress","laboratorio"]):
            continue
        saved=[]
        ydir=os.path.join(BASE,str(year) if year else "sin_fecha")
        for p in msg.walk():
            fn=p.get_filename()
            if not fn: continue
            fn=dh(fn); ext=os.path.splitext(fn)[1].lower()
            if ext not in DL_EXT: continue
            payload=p.get_payload(decode=True)
            if not payload: continue
            os.makedirs(ydir,exist_ok=True)
            b=f"{dstr}_EF_{safe(subj,30)}_{safe(os.path.splitext(fn)[0],28)}{ext}"
            path=os.path.join(ydir,b)
            if os.path.exists(path):
                path=os.path.join(ydir,f"{os.path.splitext(b)[0]}_{hashlib.md5(payload).hexdigest()[:6]}{ext}")
            open(path,"wb").write(payload); saved.append((os.path.basename(path),len(payload)))
        if saved:
            report.append({"folder":f,"date":dstr,"from":frm,"to":to,"subject":subj,"saved":saved})
            print(f"[{f}] {dstr} | {subj[:50]} -> {[s[0] for s in saved]}")
M.logout()
json.dump(report,open(os.path.join(BASE,"_financieros_reales.json"),"w"),ensure_ascii=False,indent=2)
print("\nTOTAL correos con estados financieros y adjuntos:",len(report))
