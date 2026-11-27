#!/usr/bin/env python3
"""Parcha PE - L Montejano: locale en_US (arregla fórmulas IF) + corrige la pestaña PUNTO DE EQUILIBRIO."""
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SID="1Nwjl3otYLoP6h9V-zLQFUDmg1sU0paE9NTeMyfHAo30"
TOK=Path.home()/".openclaw/credentials/google/oauth/tito_tokens.json"
N=91
def svc():
    t=json.loads(TOK.read_text())
    c=Credentials(token=t["token"],refresh_token=t["refresh_token"],token_uri=t["token_uri"],
                  client_id=t["client_id"],client_secret=t["client_secret"],scopes=t["scopes"])
    if not c.valid: c.refresh(Request()); t["token"]=c.token; TOK.write_text(json.dumps(t,indent=2))
    return build("sheets","v4",credentials=c)
sh=svc()
# 1) locale en_US (para que , funcione en fórmulas)
sh.spreadsheets().batchUpdate(spreadsheetId=SID,body={"requests":[
    {"updateSpreadsheetProperties":{"properties":{"locale":"en_US"},"fields":"locale"}}]}).execute()

TP=4+N+1  # fila total en Productos/Costeo = 96
prod="'Productos y precios'"; cost="'Costeo (costo variable)'"; fijo="'Gastos fijos'"
v4=[["PUNTO DE EQUILIBRIO — L Montejano"],
    ["Se calcula solo una vez que captures el costeo (pestaña 2) y los gastos fijos (pestaña 3)."],
    [],
    ["Concepto","Valor","Nota"],
    ["Venta del mes",f"={prod}!E{TP}","Importe vendido (junio 2026)"],
    ["Unidades vendidas (mes)",f"={prod}!C{TP}","Piezas totales"],
    ["Margen de contribución total (mes)",f"={cost}!H{TP}","Suma de (precio − costo) × vendidos"],
    ["Costo variable total (mes)","=B5-B7","Venta − margen"],
    ["Margen de contribución ponderado %","=IF(B5=0,0,B7/B5)","% de cada peso que queda para fijos + utilidad"],
    ["Gastos fijos (mes)",f"={fijo}!B14","De la pestaña Gastos fijos"],
    ["",""],
    ["PUNTO DE EQUILIBRIO (venta $/mes)","=IF(B9=0,0,B10/B9)","Venta mensual para no perder ni ganar"],
    ["Punto de equilibrio (venta $/día)","=B12/30","/30 días"],
    ["Ticket promedio","=IF(B6=0,0,B5/B6)","Venta ÷ unidades"],
    ["Punto de equilibrio (tickets/día)","=IF(B14=0,0,B13/B14)","Tickets diarios para llegar"],
    ["",""],
    ["Venta real promedio ($/día) — jun","=B5/30","Para comparar contra el PE"],
    ['¿Arriba del punto de equilibrio?','=IF(B17>B13,"SÍ ✅","NO ⚠️")',"Compara venta real vs PE diario"]]
sh.spreadsheets().values().update(spreadsheetId=SID,range="'PUNTO DE EQUILIBRIO'!A1",
    valueInputOption="USER_ENTERED",body={"values":v4}).execute()
# leer de vuelta
r=sh.spreadsheets().values().get(spreadsheetId=SID,range="'PUNTO DE EQUILIBRIO'!A5:B18").execute()["values"]
for x in r: print(x)
