#!/usr/bin/env python3
"""Arma el esqueleto del Punto de equilibrio en Drive:
- 6 folders por carreta dentro de 'Punto de equilibrio'
- En 'A - L Montejano': Google Sheet 'PE - L Montejano' con 4 pestañas.
  Productos y precios se llena con los 91 productos (junio 2026); las otras 3 quedan de esqueleto con fórmulas.
"""
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

PE_FOLDER="1k15fAbmlQBbWQ200v6zImdZ6LULB9eUq"  # Punto de equilibrio
PROD_JSON="/home/tito/.openclaw/data/pe_montejano/productos_montejano_jun2026.json"
TOK=Path.home()/".openclaw/credentials/google/oauth/tito_tokens.json"
CARRETAS=["A - L Montejano","B - Hacienda del Río","C - Montecarlo",
          "D - Villas del Rey","E - San Marcos","F - Cine Curto"]

def svc(kind):
    t=json.loads(TOK.read_text())
    c=Credentials(token=t["token"],refresh_token=t["refresh_token"],token_uri=t["token_uri"],
                  client_id=t["client_id"],client_secret=t["client_secret"],scopes=t["scopes"])
    if not c.valid: c.refresh(Request()); t["token"]=c.token; TOK.write_text(json.dumps(t,indent=2))
    return build(kind,"v4" if kind=="sheets" else "v3",credentials=c)

d=svc("drive"); sh=svc("sheets")

def get_or_mkfolder(name,parent):
    q=f"name='{name}' and '{parent}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    ex=d.files().list(q=q,fields="files(id)").execute().get("files",[])
    if ex: return ex[0]["id"]
    return d.files().create(body={"name":name,"mimeType":"application/vnd.google-apps.folder","parents":[parent]},fields="id").execute()["id"]

folders={c:get_or_mkfolder(c,PE_FOLDER) for c in CARRETAS}
print("carretas:",{k:v[:6] for k,v in folders.items()})

# --- sheet PE - L Montejano ---
A=folders["A - L Montejano"]
ss=d.files().create(body={"name":"PE - L Montejano",
    "mimeType":"application/vnd.google-apps.spreadsheet","parents":[A]},fields="id").execute()
sid=ss["id"]; print("PE sheet:",sid)

# crear 4 pestañas
TABS=["Productos y precios","Costeo (costo variable)","Gastos fijos","PUNTO DE EQUILIBRIO"]
meta=sh.spreadsheets().get(spreadsheetId=sid).execute()
first_gid=meta["sheets"][0]["properties"]["sheetId"]
reqs=[{"updateSheetProperties":{"properties":{"sheetId":first_gid,"title":TABS[0]},"fields":"title"}}]
for t in TABS[1:]:
    reqs.append({"addSheet":{"properties":{"title":t}}})
res=sh.spreadsheets().batchUpdate(spreadsheetId=sid,body={"requests":reqs}).execute()
gids={TABS[0]:first_gid}
for r in res["replies"]:
    if "addSheet" in r:
        p=r["addSheet"]["properties"]; gids[p["title"]]=p["sheetId"]

prod=json.loads(Path(PROD_JSON).read_text())
ps=sorted(prod["productos"],key=lambda x:-x["importe_sin_imp"])
tot_imp=sum(p["importe_sin_imp"] for p in ps) or 1
tot_un=sum(p["cantidad"] for p in ps) or 1
n=len(ps)

# ---- Pestaña 1: Productos y precios ----
v1=[["PRODUCTOS Y PRECIOS — L Montejano (junio 2026)"],
    ["Fuente: Soft Restaurant, reporte de productos vendidos · mes normal antes del incendio"],
    [],
    ["Clave","Producto","Vendidos (mes)","Precio promedio","Importe (mes)","% de la venta","% de unidades"]]
for p in ps:
    v1.append([p["clave"],p["descripcion"],p["cantidad"],round(p["precio_promedio"],2),
               round(p["importe_sin_imp"],2),
               f"=E{len(v1)+1}/$E${4+n+1}", f"=C{len(v1)+1}/$C${4+n+1}"])
v1.append(["","TOTAL",tot_un,"",round(tot_imp,2),"",""])

# ---- Pestaña 2: Costeo (costo variable) ----
v2=[["COSTEO — COSTO VARIABLE POR PRODUCTO"],
    ["Captura el costo de insumos por producto (o jálalo del Costeo de Cocina con IMPORTRANGE). El margen se calcula solo."],
    [],
    ["Clave","Producto","Precio venta","Costo insumos (unit)","Margen contribución $","Margen %","Vendidos (mes)","Margen total $"]]
for i,p in enumerate(ps):
    row=len(v2)+1
    v2.append([p["clave"],p["descripcion"],round(p["precio_promedio"],2),"",
               f"=C{row}-D{row}", f"=IF(C{row}=0,0,E{row}/C{row})", p["cantidad"], f"=E{row}*G{row}"])
last2=4+n
v2.append(["","TOTAL","","",f"=SUM(E5:E{last2})","",f"=SUM(G5:G{last2})",f"=SUM(H5:H{last2})"])

# ---- Pestaña 3: Gastos fijos ----
conceptos=["Renta","Nómina base (sueldos fijos)","Luz (CFE)","Gas","Agua","Internet / teléfono",
           "Mantenimiento","Publicidad","Otros gastos fijos"]
v3=[["GASTOS FIJOS MENSUALES — L Montejano"],
    ["Captura el monto mensual de cada concepto. Total se suma solo."],
    [],
    ["Concepto","Monto mensual"]]
for c in conceptos: v3.append([c,""])
last3=4+len(conceptos)
v3.append(["TOTAL GASTOS FIJOS",f"=SUM(B5:B{last3})"])

# ---- Pestaña 4: PUNTO DE EQUILIBRIO ----
prod_tab="'Productos y precios'"; cost_tab="'Costeo (costo variable)'"; fijo_tab="'Gastos fijos'"
v4=[["PUNTO DE EQUILIBRIO — L Montejano"],
    ["Se calcula solo una vez que captures el costeo (pestaña 2) y los gastos fijos (pestaña 3)."],
    [],
    ["Concepto","Valor","Nota"],
    ["Venta del mes",f"={prod_tab}!E{4+n+1}","Importe vendido (junio 2026)"],
    ["Unidades vendidas (mes)",f"={prod_tab}!C{4+n+1}","Piezas totales"],
    ["Costo variable total (mes)",f"={cost_tab}!H{4+n+1}","Suma del margen se deriva de aquí"],
    ["Margen de contribución $ (mes)","=B5-B7","Venta − costo variable"],
    ["Margen de contribución ponderado %","=IF(B5=0,0,B8/B5)","Qué % de cada peso queda para fijos+utilidad"],
    ["Gastos fijos (mes)",f"={fijo_tab}!B{last3+1}","De la pestaña Gastos fijos"],
    ["",""],
    ["PUNTO DE EQUILIBRIO (venta $/mes)","=IF(B9=0,0,B10/B9)","Venta mensual para no perder ni ganar"],
    ["Punto de equilibrio (venta $/día)","=B12/30","/30 días"],
    ["Ticket promedio","=IF(B6=0,0,B5/B6)","Venta ÷ unidades"],
    ["Punto de equilibrio (tickets/día)","=IF(B14=0,0,B13/B14)","Tickets diarios para llegar"],
    ["",""],
    ["Venta real promedio ($/día) — jun","=B5/30","Para comparar contra el PE"],
    ["¿Arriba del punto de equilibrio?","=IF(B18>B13,\"SÍ ✅\",\"NO ⚠️\")","Compara venta real vs PE diario"]]

for tab,vals in [("Productos y precios",v1),("Costeo (costo variable)",v2),
                 ("Gastos fijos",v3),("PUNTO DE EQUILIBRIO",v4)]:
    sh.spreadsheets().values().update(spreadsheetId=sid,range=f"'{tab}'!A1",
        valueInputOption="USER_ENTERED",body={"values":vals}).execute()

# ---- formato basico por pestaña ----
def hdr_fmt(gid,row,cols,bg=(0.2,0.22,0.28)):
    return {"repeatCell":{"range":{"sheetId":gid,"startRowIndex":row,"endRowIndex":row+1,"startColumnIndex":0,"endColumnIndex":cols},
        "cell":{"userEnteredFormat":{"textFormat":{"bold":True,"foregroundColor":{"red":1,"green":1,"blue":1}},
        "backgroundColor":{"red":bg[0],"green":bg[1],"blue":bg[2]},"horizontalAlignment":"CENTER","wrapStrategy":"WRAP"}},"fields":"userEnteredFormat"}}
def title_fmt(gid,cols):
    return {"repeatCell":{"range":{"sheetId":gid,"startRowIndex":0,"endRowIndex":1,"startColumnIndex":0,"endColumnIndex":cols},
        "cell":{"userEnteredFormat":{"textFormat":{"bold":True,"fontSize":13,"foregroundColor":{"red":1,"green":1,"blue":1}},
        "backgroundColor":{"red":0.7,"green":0.15,"blue":0.13}}},"fields":"userEnteredFormat"}}
def money(gid,r0,r1,c0,c1):
    return {"repeatCell":{"range":{"sheetId":gid,"startRowIndex":r0,"endRowIndex":r1,"startColumnIndex":c0,"endColumnIndex":c1},
        "cell":{"userEnteredFormat":{"numberFormat":{"type":"CURRENCY","pattern":"$#,##0.00"}}},"fields":"userEnteredFormat"}}
def pct(gid,r0,r1,c0,c1):
    return {"repeatCell":{"range":{"sheetId":gid,"startRowIndex":r0,"endRowIndex":r1,"startColumnIndex":c0,"endColumnIndex":c1},
        "cell":{"userEnteredFormat":{"numberFormat":{"type":"PERCENT","pattern":"0.0%"}}},"fields":"userEnteredFormat"}}

fmt=[]
g1=gids["Productos y precios"]
fmt+=[title_fmt(g1,7),hdr_fmt(g1,3,7),money(g1,4,4+n+1,3,5),pct(g1,4,4+n,5,7),
      {"updateSheetProperties":{"properties":{"sheetId":g1,"gridProperties":{"frozenRowCount":4}},"fields":"gridProperties.frozenRowCount"}},
      {"updateDimensionProperties":{"range":{"sheetId":g1,"dimension":"COLUMNS","startIndex":1,"endIndex":2},"properties":{"pixelSize":230},"fields":"pixelSize"}}]
g2=gids["Costeo (costo variable)"]
fmt+=[title_fmt(g2,8),hdr_fmt(g2,3,8),money(g2,4,4+n+1,2,3),money(g2,4,4+n+1,3,5),pct(g2,4,4+n,5,6),money(g2,4,4+n+1,7,8),
      {"updateSheetProperties":{"properties":{"sheetId":g2,"gridProperties":{"frozenRowCount":4}},"fields":"gridProperties.frozenRowCount"}},
      {"updateDimensionProperties":{"range":{"sheetId":g2,"dimension":"COLUMNS","startIndex":1,"endIndex":2},"properties":{"pixelSize":230},"fields":"pixelSize"}}]
g3=gids["Gastos fijos"]
fmt+=[title_fmt(g3,2),hdr_fmt(g3,3,2),money(g3,4,last3+1,1,2),
      {"updateDimensionProperties":{"range":{"sheetId":g3,"dimension":"COLUMNS","startIndex":0,"endIndex":1},"properties":{"pixelSize":230},"fields":"pixelSize"}}]
g4=gids["PUNTO DE EQUILIBRIO"]
fmt+=[title_fmt(g4,3),hdr_fmt(g4,3,3),
      {"updateDimensionProperties":{"range":{"sheetId":g4,"dimension":"COLUMNS","startIndex":0,"endIndex":1},"properties":{"pixelSize":300},"fields":"pixelSize"}},
      {"updateDimensionProperties":{"range":{"sheetId":g4,"dimension":"COLUMNS","startIndex":1,"endIndex":2},"properties":{"pixelSize":150},"fields":"pixelSize"}},
      {"updateDimensionProperties":{"range":{"sheetId":g4,"dimension":"COLUMNS","startIndex":2,"endIndex":3},"properties":{"pixelSize":320},"fields":"pixelSize"}}]
sh.spreadsheets().batchUpdate(spreadsheetId=sid,body={"requests":fmt}).execute()

print("OK PE Montejano — productos:",n)
print("LINK: https://docs.google.com/spreadsheets/d/%s/edit"%sid)
