#!/usr/bin/env python3
"""Lee CUENTAS POR PAGAR.xlsx, arma el Directorio de proveedores en Drive
(folder 'Proveedores' dentro de 'Titiburger las originales') como Google Sheet con formato."""
import json, datetime, re
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

PARENT = "1Bql9OzXtZ_OBNikYF3KEr0qJUA83f-U2"  # Titiburger las originales
XLSX = "/home/tito/.openclaw/data/pe_montejano/CUENTAS_POR_PAGAR.xlsx"
TOK = Path.home()/".openclaw/credentials/google/oauth/tito_tokens.json"

def svc(kind):
    t=json.loads(TOK.read_text())
    c=Credentials(token=t["token"],refresh_token=t["refresh_token"],token_uri=t["token_uri"],
                  client_id=t["client_id"],client_secret=t["client_secret"],scopes=t["scopes"])
    if not c.valid:
        c.refresh(Request()); t["token"]=c.token; TOK.write_text(json.dumps(t,indent=2))
    return build(kind,"v4" if kind=="sheets" else "v3",credentials=c)

# --- parsear ---
import openpyxl
wb=openpyxl.load_workbook(XLSX,data_only=True); ws=wb["Hoja1"]
rows=[list(r) for r in ws.iter_rows(values_only=True)]
isdate=lambda v: isinstance(v,(datetime.datetime,datetime.date))
isnum=lambda v: isinstance(v,(int,float))
provs=[]; cur=None
for i,r in enumerate(rows):
    c1=r[1] if len(r)>1 else None; c3=r[3] if len(r)>3 else None
    s1=str(c1).strip() if c1 is not None else ""
    nxt=str(rows[i+1][1]).strip() if i+1<len(rows) and len(rows[i+1])>1 and rows[i+1][1] else ""
    if s1 and not isdate(c1) and nxt.upper().startswith("RFC"):
        cur={"nombre":s1,"rfc":"","fac":0,"suma":0.0,"total":None,"primera":None,"ultima":None,"afavor":0.0}
        provs.append(cur); continue
    if cur is None: continue
    if s1.upper().startswith("RFC"):
        cur["rfc"]=re.sub(r"\s+"," ",s1.replace("RFC","").strip()); continue
    if isdate(c1) and isnum(c3):
        cur["fac"]+=1; cur["suma"]+=float(c3)
        d=c1.date() if isinstance(c1,datetime.datetime) else c1
        cur["primera"]=d if not cur["primera"] else min(cur["primera"],d)
        cur["ultima"]=d if not cur["ultima"] else max(cur["ultima"],d)
    elif s1.lower()=="a favor" and isnum(c3):
        cur["afavor"]+=float(c3); cur["suma"]+=float(c3)
    elif (c1 in (None,"")) and isnum(c3):
        cur["total"]=float(c3)

for p in provs:
    p["saldo"]=p["total"] if p["total"] is not None else p["suma"]

# detectar RFC duplicados (error de captura)
from collections import Counter
rfc_cnt=Counter(p["rfc"] for p in provs if p["rfc"])
dup={k for k,v in rfc_cnt.items() if v>1}

# --- crear folder + sheet ---
d=svc("drive"); sh=svc("sheets")
# folder Proveedores (reusar si existe)
q=f"name='Proveedores' and '{PARENT}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
ex=d.files().list(q=q,fields="files(id)").execute().get("files",[])
folder=ex[0]["id"] if ex else d.files().create(
    body={"name":"Proveedores","mimeType":"application/vnd.google-apps.folder","parents":[PARENT]},
    fields="id").execute()["id"]
print("folder Proveedores:",folder)
ss=d.files().create(body={"name":"Directorio de proveedores",
    "mimeType":"application/vnd.google-apps.spreadsheet","parents":[folder]},fields="id").execute()
sid=ss["id"]; print("sheet:",sid)
meta=sh.spreadsheets().get(spreadsheetId=sid).execute()
gid=meta["sheets"][0]["properties"]["sheetId"]

def fdate(x): return x.strftime("%d/%m/%Y") if x else ""
hdr=["#","Proveedor","RFC","Facturas pendientes","Saldo por pagar","Factura más antigua","Última compra","Notas"]
values=[["DIRECTORIO DE PROVEEDORES — Cuentas por pagar"],
        ["Corte: 07/08/2026  ·  Fuente: CUENTAS POR PAGAR (contadora)"],
        [], hdr]
for i,p in enumerate(sorted(provs,key=lambda x:-x["saldo"]),1):
    notas=[]
    if p["rfc"] in dup: notas.append("RFC repetido — verificar")
    if p["afavor"]: notas.append(f"incluye saldo a favor ${p['afavor']:,.0f}")
    values.append([i,p["nombre"],p["rfc"],p["fac"],round(p["saldo"],2),
                   fdate(p["primera"]),fdate(p["ultima"])," · ".join(notas)])
tot_row=4+len(provs)+1
values.append(["","","TOTAL",f"=SUM(D5:D{4+len(provs)})",f"=SUM(E5:E{4+len(provs)})","","",""])

sh.spreadsheets().values().update(spreadsheetId=sid,range="A1",
    valueInputOption="USER_ENTERED",body={"values":values}).execute()

# --- formato ---
last=tot_row
reqs=[
 {"mergeCells":{"range":{"sheetId":gid,"startRowIndex":0,"endRowIndex":1,"startColumnIndex":0,"endColumnIndex":8},"mergeType":"MERGE_ALL"}},
 {"mergeCells":{"range":{"sheetId":gid,"startRowIndex":1,"endRowIndex":2,"startColumnIndex":0,"endColumnIndex":8},"mergeType":"MERGE_ALL"}},
 {"repeatCell":{"range":{"sheetId":gid,"startRowIndex":0,"endRowIndex":1},"cell":{"userEnteredFormat":{"textFormat":{"bold":True,"fontSize":14,"foregroundColor":{"red":1,"green":1,"blue":1}},"backgroundColor":{"red":0.7,"green":0.15,"blue":0.13},"horizontalAlignment":"CENTER"}},"fields":"userEnteredFormat"}},
 {"repeatCell":{"range":{"sheetId":gid,"startRowIndex":1,"endRowIndex":2},"cell":{"userEnteredFormat":{"textFormat":{"italic":True,"foregroundColor":{"red":0.4,"green":0.4,"blue":0.4}},"horizontalAlignment":"CENTER"}},"fields":"userEnteredFormat"}},
 {"repeatCell":{"range":{"sheetId":gid,"startRowIndex":3,"endRowIndex":4},"cell":{"userEnteredFormat":{"textFormat":{"bold":True,"foregroundColor":{"red":1,"green":1,"blue":1}},"backgroundColor":{"red":0.2,"green":0.22,"blue":0.28},"horizontalAlignment":"CENTER","wrapStrategy":"WRAP"}},"fields":"userEnteredFormat"}},
 {"repeatCell":{"range":{"sheetId":gid,"startRowIndex":4,"endRowIndex":4+len(provs),"startColumnIndex":4,"endColumnIndex":5},"cell":{"userEnteredFormat":{"numberFormat":{"type":"CURRENCY","pattern":"$#,##0.00"}}},"fields":"userEnteredFormat"}},
 {"repeatCell":{"range":{"sheetId":gid,"startRowIndex":last-1,"endRowIndex":last,"startColumnIndex":4,"endColumnIndex":5},"cell":{"userEnteredFormat":{"numberFormat":{"type":"CURRENCY","pattern":"$#,##0.00"}}},"fields":"userEnteredFormat"}},
 {"repeatCell":{"range":{"sheetId":gid,"startRowIndex":last-1,"endRowIndex":last},"cell":{"userEnteredFormat":{"textFormat":{"bold":True},"backgroundColor":{"red":0.93,"green":0.93,"blue":0.85}}},"fields":"userEnteredFormat"}},
 {"updateSheetProperties":{"properties":{"sheetId":gid,"gridProperties":{"frozenRowCount":4}},"fields":"gridProperties.frozenRowCount"}},
 {"updateDimensionProperties":{"range":{"sheetId":gid,"dimension":"COLUMNS","startIndex":1,"endIndex":2},"properties":{"pixelSize":170},"fields":"pixelSize"}},
 {"updateDimensionProperties":{"range":{"sheetId":gid,"dimension":"COLUMNS","startIndex":2,"endIndex":3},"properties":{"pixelSize":150},"fields":"pixelSize"}},
 {"updateDimensionProperties":{"range":{"sheetId":gid,"dimension":"COLUMNS","startIndex":3,"endIndex":8},"properties":{"pixelSize":130},"fields":"pixelSize"}},
 {"updateBorders":{"range":{"sheetId":gid,"startRowIndex":3,"endRowIndex":last,"startColumnIndex":0,"endColumnIndex":8},"top":{"style":"SOLID"},"bottom":{"style":"SOLID"},"left":{"style":"SOLID"},"right":{"style":"SOLID"},"innerHorizontal":{"style":"SOLID","color":{"red":0.8,"green":0.8,"blue":0.8}},"innerVertical":{"style":"SOLID","color":{"red":0.8,"green":0.8,"blue":0.8}}}},
]
sh.spreadsheets().batchUpdate(spreadsheetId=sid,body={"requests":reqs}).execute()
print("proveedores:",len(provs),"total saldo:",round(sum(p["saldo"] for p in provs),2))
print("LINK: https://docs.google.com/spreadsheets/d/%s/edit"%sid)
