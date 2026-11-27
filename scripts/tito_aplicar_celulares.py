#!/usr/bin/env python3
"""
tito_aplicar_celulares.py — aplica descuentos de celular a la nómina de la semana,
leyendo cuotas y fechas DEL CATÁLOGO (sin hardcodear montos).

Fuente de verdad = "Catálogo Celulares (activo Jul 2026)" en Drive.
Estructura del catálogo:
  - Fila 3: header "DESCUENTOS POR SEMANA" o "DESCUENTOS POR MES" por bloque
  - Fila 5: nombre del empleado (columna donde empieza su bloque)
  - Fila 8: sub-headers "ABONO / CANTIDAD / FECHA / STATUS"
  - Fila 9+: los abonos

Bloques conocidos hoy:
  - Guillermo (SEM)  cols 2-5
  - David    (MES)   cols 7-10
  - Yazmín   (MES)   cols 12-15
  - Nancy    (MES)   cols 17-20
  - Félix    (SEM)   cols 22-25
  - Maura    (MES)   cols 46+ (plan mixto, aparte)

Uso:
    python3 tito_aplicar_celulares.py --sem 27
    python3 tito_aplicar_celulares.py --sem 27 --dry-run
"""

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKENS = Path("/home/tito/.openclaw/credentials/google/oauth/tito_tokens.json")
NOVEDADES_ID = "141Tcn1ZYHQQYjbgWM0DZCXT9YX1hExdFKfarLz5mBo8"
CATALOGO_ID  = "1L_ZbBfTSd8R8fGaCdSEPU4mB_59vFn3Dx20FdbWPnNg"

NOMINA_POR_SEM = {
    "18": ("1LCgltm3P9x0lTLuS5ZPcDNk7ArnxxusUiREssRjXQMs", "2026-04-27"),
    "19": ("14U7YulD4EOsu-OZ6dufIVFBV3fRP42WxGBwA4rmaLRs", "2026-05-04"),
    "20": ("1oB4xqcaG4hzZF3p1zqvQiV2ljia-qk1rRC23WNVfnx0", "2026-05-11"),
    "21": ("11_XyXQpSL-nhleh1cR1bcbOxgJzZIXRGcqhxZPT_VqQ", "2026-05-18"),
    "22": ("1qMFEydA81Q9Ge5OgtfKp5OAVMhMjzbN_qBaz5VZ9OSY", "2026-05-25"),
    "23": ("1_TwxlBXsCk45w4nNyyGc-07nDLLnABnK9YCCwPWgwec", "2026-06-01"),
    "24": ("1MgoArOxuV9lT_CCtMT6FWcEDumnDlFAtaPM7tcA7cvc", "2026-06-08"),
    "25": ("1mka8GlzLpeZGyFG_0uOuyLen04LUuaToypFRo9S8qk4", "2026-06-15"),
    "26": ("1zdo1lIa_Qlr3P5OHhnW5psX--jmOdwU1ZJTugZINsY4", "2026-06-22"),
    "27": ("1TU2Su3qgKgYMmwxY9K-JXcaQ87sVKmHD-uW4ewZQZDo", "2026-06-29"),
}

# Bloques del catálogo (col A1, tipo detectado por header F3)
# NOMBRE_EN_CATALOGO : (col_abono_1-idx, tipo)
BLOQUES_CATALOGO = [
    ("ACOSTA ANGULO GUILLERMO GEOVANNY",  2,  "semanal"),
    ("AGUIRRE MEJIA DAVID",               7,  "mensual"),
    ("DOMINGUEZ LOPEZ YAZMIN",            12, "mensual"),
    ("SERRANO CEDANO NANCY LIZETH",       17, "mensual"),
    ("MEJIA ORTEGA FELIX ERNESTO",        22, "semanal"),
]

COL_CELULAR = "AG"


def creds():
    with open(TOKENS) as f:
        td = json.load(f)
    c = Credentials(**td)
    if not c.valid and c.refresh_token:
        c.refresh(Request())
    return c


def dias_semana(iso_lunes):
    base = datetime.strptime(iso_lunes, "%Y-%m-%d").date()
    return [(base + timedelta(days=i)).isoformat() for i in range(7)]


def parse_monto(v):
    if v is None: return 0.0
    s = str(v).strip().replace("$", "").replace(" ", "")
    if not s or s == "-": return 0.0
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try: return float(s)
    except: return 0.0


MESES_ES = {"ene":1,"feb":2,"mar":3,"abr":4,"may":5,"jun":6,
            "jul":7,"ago":8,"sept":9,"sep":9,"oct":10,"nov":11,"dic":12}


def parse_fecha(v, año_default):
    """Convierte '19-feb' o 'feb-27' o '2026-02-19' a fecha ISO."""
    if not v: return None
    s = str(v).strip().lower()
    # formato "DD-mes" (ej "19-feb")
    m = re.match(r"^(\d{1,2})-([a-z]+)$", s)
    if m:
        dia, mes_s = int(m.group(1)), m.group(2)
        mes = MESES_ES.get(mes_s)
        if mes:
            # Si el mes es mayor al mes actual + 6, probable año anterior; sino mismo año
            return date(año_default, mes, dia).isoformat()
    # formato "mes-YY" (ej "ago-25") — un mes de ese año YY
    m = re.match(r"^([a-z]+)-(\d{2})$", s)
    if m:
        mes_s, yy = m.group(1), int(m.group(2))
        mes = MESES_ES.get(mes_s)
        if mes:
            año = 2000 + yy
            # asumir día 15 (medio del mes) para chequear si cae en semana
            return date(año, mes, 15).isoformat()
    # ISO ya
    try:
        return datetime.strptime(s, "%Y-%m-%d").date().isoformat()
    except: pass
    return None


def leer_catalogo(sh):
    """Devuelve dict[empleado] = {'tipo': 'semanal'/'mensual', 'cuota': float, 'abonos': [(fecha_iso, pagado_bool)]}"""
    vals = sh.spreadsheets().values().get(spreadsheetId=CATALOGO_ID, range="Hoja1").execute().get('values', [])
    resultado = {}
    for nombre, col1, tipo in BLOQUES_CATALOGO:
        # col1 es 1-idx en el bloque (col ABONO). CANTIDAD=col1+1, FECHA=col1+2, STATUS=col1+3
        cant_col = col1  # 0-idx = col1 - 1 + 1 = col1 (wait, si col1 es 1-idx, en Python row[col1-1])
        c_abono, c_cant, c_fecha, c_status = col1-1, col1, col1+1, col1+2
        cuota = None
        abonos = []
        # los abonos empiezan en fila 9 (idx 8)
        for r in range(8, len(vals)):
            row = vals[r]
            if len(row) <= c_status: continue
            # detectar cuota (primera cantidad no vacía)
            cantidad = parse_monto(row[c_cant]) if len(row) > c_cant else 0
            fecha_raw = row[c_fecha] if len(row) > c_fecha else ""
            status = str(row[c_status]).strip() if len(row) > c_status else ""
            if cantidad > 0 and cuota is None:
                cuota = cantidad
            fecha_iso = parse_fecha(fecha_raw, 2026)
            if fecha_iso:
                pagado = "PAGADO" in status.upper()
                abonos.append((fecha_iso, pagado, r+1))  # +1 para 1-idx
        resultado[nombre] = {"tipo": tipo, "cuota": cuota, "abonos": abonos, "cols": (c_abono, c_cant, c_fecha, c_status)}
    return resultado


def abono_de_la_semana(catalogo_emp, dias_iso):
    """Encuentra el abono no pagado que caiga dentro de la semana."""
    for fecha, pagado, fila in catalogo_emp["abonos"]:
        if fecha in dias_iso and not pagado:
            return (fecha, fila)
    return None


def asegurar_bitacora(sh, spreadsheet_id, year):
    titulo = f"Bitácora {year}"
    meta = sh.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for h in meta["sheets"]:
        if h["properties"]["title"] == titulo: return titulo
    sh.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests":[{"addSheet":{"properties":{"title":titulo}}}]}
    ).execute()
    sh.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id, range=f"{titulo}!A1",
        valueInputOption="USER_ENTERED",
        body={"values":[["Fecha aplicación","Semana nómina","Empleado","Tipo","Monto",
                         "Columna Excel","Razón","Autoriza","Notas","Fecha registro"]]}
    ).execute()
    return titulo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.sem not in NOMINA_POR_SEM:
        print(f"❌ Semana {args.sem} desconocida"); sys.exit(1)

    nomina_id, lunes = NOMINA_POR_SEM[args.sem]
    dias = dias_semana(lunes)

    print(f"{'='*70}")
    print(f"CELULARES → Nómina S{args.sem}  {lunes}..{dias[-1]}  {'(DRY RUN)' if args.dry_run else ''}")
    print(f"{'='*70}\n")

    sh = build("sheets", "v4", credentials=creds())
    catalogo = leer_catalogo(sh)

    # fila de cada empleado en la nómina
    nom_vals = sh.spreadsheets().values().get(
        spreadsheetId=nomina_id, range="Hoja1!F9:F40"
    ).execute().get("values", [])
    fila_por_emp = {}
    for i, row in enumerate(nom_vals):
        if row and row[0]:
            fila_por_emp[str(row[0]).strip().upper()] = 9 + i

    updates = []
    aplicados = []
    for emp, info in catalogo.items():
        fila = fila_por_emp.get(emp)
        if fila is None:
            print(f"  ⚠️ {emp}: no está en la nómina"); continue
        if info["cuota"] is None:
            print(f"  ⚠️ {emp}: sin cuota detectada en el catálogo"); continue

        motivo = None
        if info["tipo"] == "semanal":
            motivo = f"descuento semanal ${info['cuota']} (catálogo)"
        else:
            match = abono_de_la_semana(info, dias)
            if match:
                fecha_ab, _ = match
                motivo = f"cobro mensual del {fecha_ab} (catálogo)"

        if not motivo:
            print(f"  ⏭  {emp[:35]:<37} skip (mensual sin abono esta semana)")
            continue

        # ¿ya tiene valor?
        v = sh.spreadsheets().values().get(spreadsheetId=nomina_id,
            range=f"Hoja1!{COL_CELULAR}{fila}").execute().get("values",[[""]])
        actual = parse_monto(v[0][0] if v and v[0] else "")
        if actual >= info["cuota"] - 1:
            print(f"  ✓  {emp[:35]:<37} ya tiene ${actual:.0f} — no re-aplico")
            continue

        cuota = info["cuota"]
        print(f"  💰 {emp[:35]:<37} ${actual:.0f} → ${cuota:.0f}  ({motivo})")
        updates.append({"range": f"Hoja1!{COL_CELULAR}{fila}", "values": [[cuota]]})
        aplicados.append((emp, info["tipo"], cuota, motivo))

    if not updates:
        print("\n(nada por aplicar)"); return

    if args.dry_run:
        print(f"\n[DRY RUN] {len(updates)} celdas se aplicarían"); return

    sh.spreadsheets().values().batchUpdate(
        spreadsheetId=nomina_id,
        body={"valueInputOption":"USER_ENTERED", "data": updates}
    ).execute()
    print(f"\n✅ {len(updates)} descuentos aplicados en S{args.sem}")

    # Bitácora
    sys.path.insert(0, str(Path(__file__).parent))
    from _nombres_cortos import NOMBRE_CORTO
    titulo_bit = asegurar_bitacora(sh, NOVEDADES_ID, str(date.today().year))
    hoy = date.today().isoformat()
    filas_bit = []
    for emp, tipo, cuota, motivo in aplicados:
        filas_bit.append([hoy, f"S{args.sem}", NOMBRE_CORTO.get(emp, emp),
                          "Celular", cuota, COL_CELULAR, motivo,
                          "Automático (catálogo)", "tito_aplicar_celulares.py", ""])
    sh.spreadsheets().values().append(
        spreadsheetId=NOVEDADES_ID, range=f"{titulo_bit}!A1",
        valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
        body={"values": filas_bit}
    ).execute()
    print(f"📖 {len(filas_bit)} registros en Bitácora")


if __name__ == "__main__":
    main()
