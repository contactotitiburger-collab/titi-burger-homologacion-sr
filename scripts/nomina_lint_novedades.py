#!/usr/bin/env python3
"""
nomina_lint_novedades.py — corre cada 5 min via cron.

Revisa la pestaña Novedades del sheet "Cambios de saldos Nomina" y auto-corrige:
  - Fechas mal formateadas (15-07-2026, 2026-07-15, "hoy", etc.) → dd/mm/yyyy
  - Tipo con capitalización rara → normalizado ("sin app" → "Sin app")
  - Empleado con espacios extras → trim
  - Empleado con typo obvio → fuzzy match al catálogo (solo si confianza >= 88%)
  - Col G (Semana auto): si tiene número escrito a mano, lo reemplaza por fórmula

No manda notificaciones. Log en /home/tito/.openclaw/logs/nomina_lint.log
"""
import json
import re
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

SID = "141Tcn1ZYHQQYjbgWM0DZCXT9YX1hExdFKfarLz5mBo8"
SA_FILE = "/home/tito/.openclaw/credentials/google/service-account.json"
APODOS_PATH = Path("/home/tito/.openclaw/data/nomina/apodos.json")
CATALOGO_EMP = Path("/home/tito/.openclaw/data/nomina/catalogo_empleados.json")
LOG_PATH = Path("/home/tito/.openclaw/logs/nomina_lint.log")

TIPOS_CONOCIDOS = ["Sin app", "Adelanto", "Vacaciones", "Préstamo", "Bono", "Descuento", "Ajuste"]


def log(msg):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")


def parse_fecha(texto):
    """Intenta parsear una fecha desde cualquier formato razonable. Devuelve date o None."""
    if not texto:
        return None
    s = str(texto).strip().lower()
    hoy = date.today()
    # Palabras
    if s in ("hoy", "today"):
        return hoy
    if s in ("ayer", "yesterday"):
        return hoy - timedelta(days=1)
    if s in ("antier", "anteayer"):
        return hoy - timedelta(days=2)
    # Formatos numéricos
    formatos = [
        "%d/%m/%Y", "%d/%m/%y",
        "%d-%m-%Y", "%d-%m-%y",
        "%Y-%m-%d", "%Y/%m/%d",
        "%m/%d/%Y",  # yankee, último para no confundir
        "%d.%m.%Y",
    ]
    for fmt in formatos:
        try:
            return datetime.strptime(str(texto).strip(), fmt).date()
        except ValueError:
            continue
    return None


def normaliza_tipo(t):
    """Normaliza el Tipo a capitalización estándar. Solo si es fuzzy-match a un tipo conocido."""
    if not t:
        return t
    s = str(t).strip()
    s_low = s.lower()
    for known in TIPOS_CONOCIDOS:
        if s_low == known.lower():
            return known  # cambia capitalización
        # fuzzy: sin acentos, sin espacios
        a = re.sub(r"\s+", "", s_low.replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u"))
        b = re.sub(r"\s+", "", known.lower().replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u"))
        if a == b:
            return known
    return s


def fuzzy_empleado(nombre_raw, apodos, cat):
    """Devuelve el mejor match del empleado. None si no supera 88% de confianza."""
    if not nombre_raw:
        return None
    s = str(nombre_raw).strip().lower()
    if not s:
        return None

    # Candidatos: apodos + nombres cortos del catálogo
    candidatos = set()
    for apodo in apodos.keys():
        if apodo:
            candidatos.add(apodo.lower())
    for e in cat:
        partes = e.get("nombre","").split()
        if len(partes) >= 2:
            candidatos.add(partes[0].lower())
            candidatos.add(partes[-2].lower())

    # Match exacto
    if s in candidatos:
        return s.title()

    # Fuzzy
    mejor = None
    mejor_score = 0
    for c in candidatos:
        score = SequenceMatcher(None, s, c).ratio()
        if score > mejor_score:
            mejor_score = score
            mejor = c
    if mejor_score >= 0.88:
        return mejor.title()
    return None


def main():
    creds = service_account.Credentials.from_service_account_file(
        SA_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    svc = build('sheets', 'v4', credentials=creds, cache_discovery=False)

    # Leer valores formateados (para que fechas ya-parseadas lleguen como "15/07/2026",
    # no como serial 46218). Así el parser detecta cambios reales.
    got = svc.spreadsheets().values().get(
        spreadsheetId=SID, range="Novedades!A1:H200",
        valueRenderOption='FORMATTED_VALUE'
    ).execute()
    filas = got.get('values', [])
    if len(filas) < 2:
        log("(sin filas de datos)")
        return

    # Cargar catálogos
    try:
        apodos = json.loads(APODOS_PATH.read_text())
    except Exception:
        apodos = {}
    try:
        cat = json.loads(CATALOGO_EMP.read_text())
    except Exception:
        cat = []

    # Leer fórmulas de col B (Semana auto) para saber si tiene fórmula o valor manual
    got_form = svc.spreadsheets().values().get(
        spreadsheetId=SID, range="Novedades!B2:B200",
        valueRenderOption='FORMULA'
    ).execute()
    formulas_g = got_form.get('values', [])

    cambios = []  # (rango, valor_nuevo, motivo)
    # Layout: A=Fecha B=Semana(auto,fórmula) C=Empleado D=Tipo E=Monto F=Razón G=Autoriza H=Notas
    for i, row in enumerate(filas[1:], start=2):
        if not row or not any(str(c).strip() for c in row):
            continue
        row = row + [""] * (8 - len(row))
        fecha, sem_auto, empleado, tipo, monto, razon, autoriza, notas = row[:8]

        # 1) Fecha (col A)
        if fecha:
            d = parse_fecha(fecha)
            if d:
                fecha_std = d.strftime("%d/%m/%Y")
                if str(fecha).strip() != fecha_std:
                    cambios.append((f"A{i}", fecha_std, f"fecha '{fecha}' → '{fecha_std}'"))
            else:
                log(f"fila {i}: fecha no parseable '{fecha}' — dejo como está")

        # 2) Tipo (col D)
        if tipo:
            t_norm = normaliza_tipo(tipo)
            if t_norm != str(tipo).strip():
                cambios.append((f"D{i}", t_norm, f"tipo '{tipo}' → '{t_norm}'"))

        # 3) Empleado (col C, trim + fuzzy si no matchea)
        if empleado:
            trim = str(empleado).strip()
            if trim != str(empleado):
                cambios.append((f"C{i}", trim, f"empleado trim '{empleado}' → '{trim}'"))
            e_low = trim.lower()
            en_catalogo = e_low in [a.lower() for a in apodos.keys() if a] or any(
                e_low in e.get("nombre","").lower() for e in cat
            )
            if not en_catalogo:
                sug = fuzzy_empleado(trim, apodos, cat)
                if sug and sug.lower() != trim.lower():
                    cambios.append((f"C{i}", sug, f"empleado fuzzy '{trim}' → '{sug}'"))

        # 4) Col B (Semana): si tiene número manual, restaurar fórmula
        f_b = formulas_g[i-2] if i-2 < len(formulas_g) else [""]
        val_b = f_b[0] if f_b else ""
        if val_b and not str(val_b).startswith("="):
            formula = f'=IF(A{i}="","",IFERROR(ISOWEEKNUM(A{i}),IFERROR(ISOWEEKNUM(DATEVALUE(A{i})),"")))'
            cambios.append((f"B{i}", formula, f"col B tenía '{val_b}' manual → fórmula restaurada"))

    # Aplicar cambios
    if cambios:
        data = [{"range": f"Novedades!{r}", "values": [[v]]} for r, v, _ in cambios]
        svc.spreadsheets().values().batchUpdate(
            spreadsheetId=SID,
            body={"valueInputOption": "USER_ENTERED", "data": data}
        ).execute()
        log(f"✓ {len(cambios)} correcciones aplicadas:")
        for r, v, motivo in cambios:
            log(f"    {r}: {motivo}")
    else:
        log("(sin cambios necesarios)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"ERROR: {type(e).__name__}: {e}")
        raise
