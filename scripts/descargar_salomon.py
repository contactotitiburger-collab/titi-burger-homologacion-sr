#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Descarga TODOS los correos del despacho contable Salomon y Asociados
(cualquier remitente que contenga 'salomon' o 'sya.'), con adjuntos, en todas
las carpetas de Yahoo. Registra remitente exacto, asunto y adjuntos."""
import imaplib, email, json, os, re, hashlib
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
imaplib._MAXLINE=10_000_000
BASE="/home/tito/.openclaw/data/estados_financieros"
def dh(s):
    try: return str(make_header(decode_header(s or "")))
    except: return s or ""
def norm(s): return (s or "").lower().translate(str.maketrans("áéíóúñü","aeiounu"))
def safe(s,n=40): return (re.sub(r"[^a-z0-9]+","_",norm(s)).strip("_")[:n]) or "sin"
DL_EXT={".pdf",".xlsx",".xls",".csv",".xml",".zip",".txt"}

c=json.load(open("/home/tito/.openclaw/credentials/yahoo/creds.json"))
M=imaplib.IMAP4_SSL(c["imap_host"],c["imap_port"]); M.login(c["user"],c["password"])
typ,data=M.list(); folders=[]
for raw in data or []:
    line=raw.decode(errors="replace")
    if "\\Noselect" in line: continue
    m=re.search(r'"([^"]*)"\s*$',line); folders.append(m.group(1) if m else line.split()[-1])
report=[]; seen=set()
for f in folders:
    typ,_=M.select(f'"{f}"',readonly=True)
    if typ!="OK": continue
    hits={}
    for term in ["salomon","sya.professional","sya","asociados"]:
        for key in ("FROM",):
            try: typ,d=M.search(None,key,term)
            except: continue
            for n in (d[0].split() if typ=="OK" and d and d[0] else []): hits[n]=1
    for num in hits:
        typ,md=M.fetch(num,"(BODY.PEEK[])")
        if typ!="OK" or not md: continue
        raw=b"".join(p[1] for p in md if isinstance(p,tuple) and p[1])
        msg=email.message_from_bytes(raw)
        frm=dh(msg.get("From","")); subj=dh(msg.get("Subject","")); to=dh(msg.get("To",""))
        if "salomon" not in norm(frm) and "sya" not in norm(frm):
            continue  # asegurar que ES del despacho
        try:
            dt=parsedate_to_datetime(msg.get("Date","")); dstr=dt.strftime("%Y-%m-%d"); year=dt.year
        except: dstr=(msg.get("Date","") or "")[:10]; year=0
        k=(frm,subj,dstr)
        if k in seen: continue
        seen.add(k)
        saved=[]; atts=[]
        ydir=os.path.join(BASE,str(year) if year else "sin_fecha")
        for p in msg.walk():
            fn=p.get_filename()
            if not fn: continue
            fn=dh(fn); atts.append(fn); ext=os.path.splitext(fn)[1].lower()
            if ext not in DL_EXT: continue
            payload=p.get_payload(decode=True)
            if not payload: continue
            os.makedirs(ydir,exist_ok=True)
            b=f"{dstr}_DESPACHO_{safe(subj,34)}_{safe(os.path.splitext(fn)[0],26)}{ext}"
            path=os.path.join(ydir,b)
            if os.path.exists(path):
                path=os.path.join(ydir,f"{os.path.splitext(b)[0]}_{hashlib.md5(payload).hexdigest()[:6]}{ext}")
            open(path,"wb").write(payload); saved.append((os.path.basename(path),len(payload)))
        report.append({"folder":f,"date":dstr,"from":frm,"to":to,"subject":subj,"attachments":atts,"saved":saved})
        print(f"[{f}] {dstr} | {frm[:45]} | {subj[:45]} | adj={atts} sav={len(saved)}")
M.logout()
json.dump(report,open(os.path.join(BASE,"_despacho_salomon.json"),"w"),ensure_ascii=False,indent=2)
print("\nTOTAL correos despacho Salomon:",len(report))
