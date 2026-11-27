#!/usr/bin/env python3
"""
tito_cierre_mensual.py — corre el 1° de cada mes:

1) Toma movimientos del MES ANTERIOR.
2) Inserta entrada en cierres_mensuales con totales.
3) Copia esas novedades al Sheet en pestaña 'Histórico YYYY-MM' (se crea si no existe).
4) Imprime resumen (para que el cron lo mande por WA si quiere).

Uso:
  tito_cierre_mensual.py                  # cierra el mes anterior a hoy
  tito_cierre_mensual.py --mes 2026-06    # cierra ese mes específico
"""

import argparse
import json
import sqlite3
import sys
from datetime import date, timedelta
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


def _rango_mes(y, m):
    ini = date(y, m, 1)
    if m == 12:
        fin = date(y+1, 1, 1) - timedelta(days=1)
    else:
        fin = date(y, m+1, 1) - timedelta(days=1)
    return ini, fin


def _fmt_money(v):
    return f"${v:,.2f}" if v >= 0 else f"-${abs(v):,.2f}"


def crear_pestana_si_falta(sheets, nombre):
    meta = sheets.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == nombre:
            return s["properties"]["sheetId"]
    r = sheets.spreadsheets().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={"requests":[{"addSheet":{"properties":{"title":nombre}}}]},
    ).execute()
    return r["replies"][0]["addSheet"]["properties"]["sheetId"]


def escribir_historico(sheets, tab, filas):
    sheets.spreadsheets().values().clear(
        spreadsheetId=SHEET_ID, range=f"'{tab}'!A1:H1000"
    ).execute()
    sheets.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range=f"'{tab}'!A1",
        valueInputOption="USER_ENTERED",
        body={"values": filas},
    ).execute()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mes", help="YYYY-MM (default: mes anterior)")
    args = ap.parse_args()

    hoy = date.today()
    if args.mes:
        y, m = map(int, args.mes.split("-"))
    else:
        # mes anterior
        if hoy.month == 1:
            y, m = hoy.year - 1, 12
        else:
            y, m = hoy.year, hoy.month - 1

    ini, fin = _rango_mes(y, m)
    print(f"Cerrando mes {y}-{m:02d}  ({ini} a {fin})")

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT m.fecha, e.nombre_corto, m.tipo, m.monto, m.razon, m.autoriza, m.semana_afectada, m.notas
        FROM movimientos m JOIN empleados e ON e.id = m.empleado_id
        WHERE m.fecha BETWEEN ? AND ?
        ORDER BY m.fecha, m.id
    """, (ini.isoformat(), fin.isoformat())).fetchall()

    # Totales
    total_prest = sum(-r["monto"] for r in rows if r["monto"] < 0)
    total_abon  = sum(r["monto"] for r in rows if r["monto"] > 0)
    balance = total_abon - total_prest
    con_deuda = conn.execute("""
        SELECT COUNT(*) FROM (
          SELECT empleado_id, SUM(monto) s FROM movimientos
          WHERE fecha<=? GROUP BY empleado_id HAVING s < 0
        )
    """, (fin.isoformat(),)).fetchone()[0]

    # Guardar cierre
    conn.execute("""
        INSERT OR REPLACE INTO cierres_mensuales
          (anio, mes, total_prestado, total_abonado, balance, empleados_con_adelanto_pendiente)
        VALUES (?,?,?,?,?,?)
    """, (y, m, total_prest, total_abon, balance, con_deuda))
    conn.commit()
    conn.close()

    print(f"  Movimientos: {len(rows)}")
    print(f"  Prestado: {_fmt_money(total_prest)}")
    print(f"  Abonado:  {_fmt_money(total_abon)}")
    print(f"  Balance:  {_fmt_money(balance)}")
    print(f"  Con adelanto pendiente al cierre: {con_deuda}")

    # Volcar histórico al Sheet
    creds = _creds()
    sheets = build("sheets", "v4", credentials=creds)
    tab = f"Histórico {y}-{m:02d}"
    crear_pestana_si_falta(sheets, tab)
    filas = [["Fecha","Empleado","Tipo","Monto","Razón","Autoriza","Semana afectada","Notas"]]
    for r in rows:
        filas.append([
            r["fecha"], r["nombre_corto"], TIPO_LABEL.get(r["tipo"], r["tipo"]),
            _fmt_money(r["monto"]), r["razon"] or "", r["autoriza"] or "",
            r["semana_afectada"] or "", r["notas"] or "",
        ])
    escribir_historico(sheets, tab, filas)
    print(f"OK histórico volcado en pestaña '{tab}' del Sheet")


if __name__ == "__main__":
    main()
