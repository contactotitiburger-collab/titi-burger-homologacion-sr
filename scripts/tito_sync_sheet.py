#!/usr/bin/env python3
"""
tito_sync_sheet.py — sincroniza SQLite (fuente de verdad) -> Sheet "Novedades y Saldos".

- Pestaña 'Novedades': movimientos del MES ACTUAL, ordenados por fecha desc.
- Pestaña 'Saldos':    valores estáticos (no fórmulas) por empleado.

Sheet ID: 141Tcn1ZYHQQYjbgWM0DZCXT9YX1hExdFKfarLz5mBo8

Usa OAuth ([[oauth-drive-listo]]).
"""

import json
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

DB_PATH = Path("/home/tito/.openclaw/data/nomina/nomina.db")
TOKENS = Path("/home/tito/.openclaw/credentials/google/oauth/tito_tokens.json")
SHEET_ID = "141Tcn1ZYHQQYjbgWM0DZCXT9YX1hExdFKfarLz5mBo8"

TIPO_LABEL = {
    "adelanto": "Adelanto",
    "abono": "Abono",
    "castigo": "Castigo",
    "evento": "Evento",
    "horas_extra": "Horas extra",
    "bono_especial": "Bono especial",
    "otro": "Otro",
}


def _creds():
    with open(TOKENS) as f:
        td = json.load(f)
    c = Credentials(**td)
    if not c.valid and c.refresh_token:
        c.refresh(Request())
    return c


def _fmt_money(v):
    if v is None:
        return "$0.00"
    return f"${v:,.2f}" if v >= 0 else f"-${abs(v):,.2f}"


def _mes_actual_rango():
    hoy = date.today()
    ini = date(hoy.year, hoy.month, 1)
    if hoy.month == 12:
        fin = date(hoy.year+1, 1, 1) - timedelta(days=1)
    else:
        fin = date(hoy.year, hoy.month+1, 1) - timedelta(days=1)
    return ini, fin


def obtener_novedades(c):
    ini, fin = _mes_actual_rango()
    rows = c.execute("""
        SELECT m.fecha, e.nombre_corto, m.tipo, m.monto, m.razon, m.autoriza, m.semana_afectada, m.notas
        FROM movimientos m JOIN empleados e ON e.id = m.empleado_id
        WHERE m.fecha BETWEEN ? AND ?
        ORDER BY m.fecha DESC, m.id DESC
    """, (ini.isoformat(), fin.isoformat())).fetchall()
    out = [["Fecha","Empleado","Tipo","Monto","Razón","Autoriza","Semana afectada","Notas"]]
    for r in rows:
        out.append([
            r["fecha"],
            r["nombre_corto"],
            TIPO_LABEL.get(r["tipo"], r["tipo"]),
            _fmt_money(r["monto"]),
            r["razon"] or "",
            r["autoriza"] or "",
            r["semana_afectada"] or "",
            r["notas"] or "",
        ])
    return out


def obtener_saldos(c):
    rows = c.execute("""
        SELECT e.nombre_corto, e.activo,
               COALESCE(SUM(CASE WHEN m.monto<0 THEN -m.monto END), 0) AS adelantos_totales,
               COALESCE(SUM(CASE WHEN m.monto>0 THEN  m.monto END), 0) AS abonos_totales,
               COALESCE(SUM(m.monto), 0) AS saldo,
               MAX(m.fecha) AS ultima
        FROM empleados e
        LEFT JOIN movimientos m ON m.empleado_id = e.id
        GROUP BY e.id
        ORDER BY e.activo DESC, e.nombre_corto
    """).fetchall()
    hoy = date.today().isoformat()
    out = [["Empleado","Adelantos totales","Abonos totales","Saldo actual","Última actualización"]]
    for r in rows:
        # Empleados de baja: los seguimos mostrando por si tienen saldo pendiente,
        # pero les agregamos marca
        nombre = r["nombre_corto"] + ("" if r["activo"] else " (BAJA)")
        out.append([
            nombre,
            _fmt_money(r["adelantos_totales"]),
            _fmt_money(r["abonos_totales"]),
            _fmt_money(r["saldo"]),
            r["ultima"] or hoy,
        ])
    return out


def escribir_pestana(sheets, tab, values):
    # Limpia el rango entero antes de escribir (para dejar sólo el nuevo dataset)
    sheets.spreadsheets().values().clear(
        spreadsheetId=SHEET_ID, range=f"'{tab}'!A1:H1000"
    ).execute()
    sheets.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range=f"'{tab}'!A1",
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()


def main():
    creds = _creds()
    sheets = build("sheets", "v4", credentials=creds)

    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row

    nov = obtener_novedades(c)
    sal = obtener_saldos(c)

    escribir_pestana(sheets, "Novedades", nov)
    escribir_pestana(sheets, "Saldos", sal)

    print(f"OK sync: novedades={len(nov)-1} filas, saldos={len(sal)-1} filas")


if __name__ == "__main__":
    main()
