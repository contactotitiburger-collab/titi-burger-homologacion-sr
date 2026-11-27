#!/usr/bin/env python3
"""
nomina_highlights_diff_nancy.py

Aplica highlights (verde/amarillo/naranja) + notas en la col AJ (TOTAL) de la nómina
comparando con el Excel real de Nancy que Rafael sube por WhatsApp.

Corre DESPUÉS del generador (nomina_aplicar_respuestas.py) porque el template borra el formato.
"""
import openpyxl
import json
from pathlib import Path
from collections import defaultdict
from google.oauth2 import service_account
from googleapiclient.discovery import build

SID = "1yinXDaC1Icmnt7YoZOYVc01dNv6zvejhyFx3Qnz0UkA"  # sheet nómina S28
SID_NOV = "141Tcn1ZYHQQYjbgWM0DZCXT9YX1hExdFKfarLz5mBo8"
NANCY_XLSX = "/home/tito/.openclaw/media/inbound/NOMINA_28_TITI_BURGER_2026---075718d2-3590-4d97-896e-5efa11662351.xlsx"

def norm(s): return ' '.join(str(s).upper().strip().split())

def main():
    if not Path(NANCY_XLSX).exists():
        print(f"[warn] no hay Excel Nancy en {NANCY_XLSX} — skip highlights")
        return

    creds = service_account.Credentials.from_service_account_file(
        "/home/tito/.openclaw/credentials/google/service-account.json",
        scopes=['https://www.googleapis.com/auth/spreadsheets'])
    svc = build('sheets','v4',credentials=creds,cache_discovery=False)
    meta = svc.spreadsheets().get(spreadsheetId=SID).execute()
    gid = next(s['properties']['sheetId'] for s in meta['sheets'] if 'NOMINA' in s['properties']['title'].upper())

    wb = openpyxl.load_workbook(NANCY_XLSX, data_only=True)
    ws = wb['NOMINA']
    nancy = {}
    for r in range(9, 35):
        n = ws.cell(row=r, column=6).value
        if not n: continue
        total = ws.cell(row=r, column=36).value or 0
        if isinstance(total, (int, float)):
            nancy[norm(n)] = total

    r = svc.spreadsheets().values().get(spreadsheetId=SID,
        range="'NOMINA '!F9:AJ32", valueRenderOption='UNFORMATTED_VALUE').execute()

    # Sin app por empleado (para agregar detalle de días)
    nov_data = svc.spreadsheets().values().get(spreadsheetId=SID_NOV,
        range="Novedades!A2:H50", valueRenderOption='FORMATTED_VALUE').execute()
    sin_app_by_emp = defaultdict(int)
    apodo_map = {
        'LUCINA': 'NORIEGA ROSALES LUCINA ALEJANDRA', 'OSCAR': 'VELAZQUEZ PEREZ OSCAR',
        'GUILLERMO ANTONIO': 'CONTRERAS ALEJANDRO GUILLERMO ANTONIO',
        'ANGEL': 'ZELAYA RAMOS ANGEL GEOVANNI',
        'HERBERTH': 'MEJIA AYALA HERBERTH ANTONIO',
        'ANDRONICA': 'BAUTISTA GOMEZ ANDRONICA', 'ANDY': 'BAUTISTA GOMEZ ANDRONICA',
    }
    for row in nov_data.get('values', []):
        if not row or len(row) < 4: continue
        row = row + [""] * (8 - len(row))
        _, _, emp, tipo, *_ = row
        if 'sin app' not in str(tipo).lower(): continue
        e_up = norm(emp)
        sin_app_by_emp[norm(apodo_map.get(e_up, e_up))] += 1

    # Preguntas específicas por empleado (se pueden ir editando aquí)
    preguntas_base = {
        'CONTRERAS ALEJANDRO GUILLERMO ANTONIO': "❓ INFONAVIT $566: ¿aplica esta semana? Yo se lo descuento, tú no.",
        'AGUIRRE MEJIA DAVID': "❓ Falta descuento celular $264 esta semana?",
        'BAUTISTA GOMEZ ANDRONICA': "❓ ¿Por qué le rebajas BP a $388.50 (no $420 completo)?",
        'MARTINEZ DOMINGUEZ JENNIFER AYLIN': "❓ Rafael puso Bono $515 en Novedades. Tú no lo tienes. ¿Se paga?",
        'MEJIA ORTEGA FELIX ERNESTO': "❓ CELULAR real esta semana",
        'ACOSTA ANGULO GUILLERMO GEOVANNY': "❓ Falta descuento celular ~$257",
        'DOMINGUEZ LOPEZ YAZMIN': "❓ Falta descuento celular $100",
        'ROCHA RODRIGUEZ SUSANO ANDRES': "❓ Diff -$410 (posible 7mo día o vacaciones)",
    }
    # Empleados con esperados especiales (para el cálculo de días)
    esperados_special = {'MEJIA AYALA HERBERTH ANTONIO': 6}
    criticos = {'CONTRERAS ALEJANDRO GUILLERMO ANTONIO'}

    naranja = {'red': 1.0, 'green': 0.75, 'blue': 0.45}
    amarillo = {'red': 1.0, 'green': 0.92, 'blue': 0.55}
    verde = {'red': 0.72, 'green': 0.88, 'blue': 0.72}

    reqs = [
        {'repeatCell': {'range': {'sheetId': gid, 'startRowIndex': 8, 'endRowIndex': 32, 'startColumnIndex': 35, 'endColumnIndex': 36},
            'cell': {'userEnteredFormat': {'backgroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'textFormat': {'bold': False}}},
            'fields': 'userEnteredFormat(backgroundColor,textFormat)'}},
        {'updateCells': {
            'range': {'sheetId': gid, 'startRowIndex': 8, 'endRowIndex': 32, 'startColumnIndex': 35, 'endColumnIndex': 36},
            'rows': [{'values': [{'note': ''}]} for _ in range(24)],
            'fields': 'note'}}]

    verdes = 0; amarillos = 0; naranjas = 0
    for i, row in enumerate(r.get('values', []), start=9):
        if not row or not row[0]: continue
        n = str(row[0]).strip(); n_n = norm(n)
        yo = float(row[30]) if len(row) > 30 and row[30] else 0
        n_ref = nancy.get(n_n, 0)
        diff = yo - n_ref
        dias = int(float(row[13])) if len(row) > 13 and row[13] else 0
        sin_app = sin_app_by_emp.get(n_n, 0)
        esperado = esperados_special.get(n_n, 6)
        if abs(diff) <= 1:
            color = verde
            nota = f"✅ Cuadra con Nancy (${n_ref:,.2f})"
            verdes += 1
        else:
            if n_n in criticos:
                color = naranja; naranjas += 1
            else:
                color = amarillo; amarillos += 1
            header = f"NANCY:  ${n_ref:,.2f}\nTITO:   ${yo:,.2f}\nDIFF:   ${diff:+,.2f}"
            preg = preguntas_base.get(n_n, f"Diff ${diff:+,.2f} — verificar")
            detalle = ""
            if sin_app > 0:
                fich = max(dias - sin_app, 0)
                faltantes = esperado - dias
                if faltantes > 0:
                    detalle = f"\n\nDÍAS: fichó {fich} + {sin_app} Sin app = {dias} de {esperado}.\n❓ FALTAN {faltantes} día(s) — ¿qué pasó?"
                else:
                    detalle = f"\n\nDÍAS: fichó {fich} + {sin_app} Sin app = {dias} ✓"
            nota = f"{header}\n—\n{preg}{detalle}"
        reqs.append({'repeatCell': {
            'range': {'sheetId': gid, 'startRowIndex': i - 1, 'endRowIndex': i, 'startColumnIndex': 35, 'endColumnIndex': 36},
            'cell': {'userEnteredFormat': {'backgroundColor': color, 'textFormat': {'bold': True}}},
            'fields': 'userEnteredFormat(backgroundColor,textFormat)'}})
        reqs.append({'updateCells': {
            'range': {'sheetId': gid, 'startRowIndex': i - 1, 'endRowIndex': i, 'startColumnIndex': 35, 'endColumnIndex': 36},
            'rows': [{'values': [{'note': nota}]}], 'fields': 'note'}})

    # Flags contadores en fila 34
    svc.spreadsheets().values().batchUpdate(spreadsheetId=SID,
        body={'valueInputOption': 'USER_ENTERED', 'data': [
            {'range': "'NOMINA '!AK34", 'values': [[f"🟢 {verdes} cuadran"]]},
            {'range': "'NOMINA '!AL34", 'values': [[f"🟡 {amarillos} revisar"]]},
            {'range': "'NOMINA '!AM34", 'values': [[f"🟠 {naranjas} crítico"]]},
        ]}).execute()

    svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={'requests': reqs}).execute()
    print(f"✓ Highlights aplicados: 🟢 {verdes} · 🟡 {amarillos} · 🟠 {naranjas}")


if __name__ == "__main__":
    main()
