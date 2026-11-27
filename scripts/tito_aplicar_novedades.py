#!/usr/bin/env python3
"""
tito_aplicar_novedades.py — aplica lo registrado en el sheet "Novedades y Saldos"
al Excel de nómina de la semana en Drive.

Flujo:
1. Lee la pestaña "Novedades" filtrando por "Semana afectada".
2. Para cada empleado, agrupa por columna destino y suma montos.
3. Escribe el resultado en la nómina correspondiente (col OTROS, EVENTOS, etc.).
4. Marca la novedad como "aplicada" (agrega ✅ al final de la fila).
5. Actualiza los saldos en la pestaña "Saldos".

Mapeo tipo → columna del Excel de Nancy (ver [[nomina-reglas-confirmadas-2jul]]):
- Adelanto / Castigo         → OTROS (AD, resta al pago)
- Abono                      → OTROS (resta el descuento — es plata que devuelve)
- Bono especial / Evento     → EVENTOS (AH, suma al pago)
- Horas extra                → HORAS EXTRA (AI, suma al pago)
- Vacaciones                 → VACACIONES (AE, resta al pago — es pago adelantado)

Uso:
    python3 tito_aplicar_novedades.py --sem 27
    python3 tito_aplicar_novedades.py --sem 27 --dry-run
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _nombres_cortos import NOMBRE_CORTO

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKENS = Path("/home/tito/.openclaw/credentials/google/oauth/tito_tokens.json")
NOVEDADES_ID = "141Tcn1ZYHQQYjbgWM0DZCXT9YX1hExdFKfarLz5mBo8"
# Único usuario autorizado a editar/borrar filas de la Bitácora (owner del Sheet).
BITACORA_OWNER = "contactotitiburger@gmail.com"

NOMINA_POR_SEM = {
    "18": "1LCgltm3P9x0lTLuS5ZPcDNk7ArnxxusUiREssRjXQMs",
    "19": "14U7YulD4EOsu-OZ6dufIVFBV3fRP42WxGBwA4rmaLRs",
    "20": "1oB4xqcaG4hzZF3p1zqvQiV2ljia-qk1rRC23WNVfnx0",
    "21": "11_XyXQpSL-nhleh1cR1bcbOxgJzZIXRGcqhxZPT_VqQ",
    "22": "1qMFEydA81Q9Ge5OgtfKp5OAVMhMjzbN_qBaz5VZ9OSY",
    "23": "1_TwxlBXsCk45w4nNyyGc-07nDLLnABnK9YCCwPWgwec",
    "24": "1MgoArOxuV9lT_CCtMT6FWcEDumnDlFAtaPM7tcA7cvc",
    "25": "1mka8GlzLpeZGyFG_0uOuyLen04LUuaToypFRo9S8qk4",
    "26": "1zdo1lIa_Qlr3P5OHhnW5psX--jmOdwU1ZJTugZINsY4",
    "27": "1TU2Su3qgKgYMmwxY9K-JXcaQ87sVKmHD-uW4ewZQZDo",
}

# Columna destino por tipo (letra col A1) y signo (+1 suma, -1 resta al pago)
MAPEO = {
    "adelanto":       ("AD", -1),   # OTROS - resta al pago
    "castigo":        ("AD", -1),   # OTROS
    "abono":          ("AD", +1),   # OTROS - devuelve plata, entonces resta al descuento
    "bono especial":  ("AH", +1),   # EVENTOS - suma
    "evento":         ("AH", +1),   # EVENTOS
    "horas extra":    ("AI", +1),   # HORAS EXTRA
    "vacaciones":     ("AE", -1),   # VACACIONES
}


def creds():
    with open(TOKENS) as f:
        td = json.load(f)
    c = Credentials(**td)
    if not c.valid and c.refresh_token:
        c.refresh(Request())
    return c


def norm(s):
    return str(s or "").strip().lower()


def formatear_fecha(v):
    """Convierte serial Excel (int/float) o string a YYYY-MM-DD si se puede."""
    if v is None or v == "": return ""
    s = str(v).strip()
    # ¿es número serial de Excel?
    try:
        n = float(s)
        if 40000 < n < 60000:  # rango razonable 2009-2064
            base = datetime(1899, 12, 30)  # epoch Excel
            return (base + __import__("datetime").timedelta(days=int(n))).date().isoformat()
    except ValueError:
        pass
    return s


def nombre_corto_a_completo(corto):
    """Invierte el mapeo: 'Angel' -> 'ZELAYA RAMOS ANGEL GEOVANNI'."""
    c = norm(corto)
    for completo, corto_map in NOMBRE_CORTO.items():
        if norm(corto_map) == c:
            return completo
    return None


def parse_monto(s):
    if s is None: return 0.0
    txt = str(s).strip().replace("$", "").replace(" ", "")
    if not txt or txt == "-": return 0.0
    # Detectar formato mirando cuál separador aparece DESPUÉS
    # Americano/MX: "1,000.00" → coma miles, punto decimal
    # Europeo (Nancy): "1.000,00" → punto miles, coma decimal
    if "," in txt and "." in txt:
        if txt.rfind(",") > txt.rfind("."):
            # coma es decimal (europeo)
            txt = txt.replace(".", "").replace(",", ".")
        else:
            # punto es decimal (americano/MX) — solo quitar comas de miles
            txt = txt.replace(",", "")
    elif "," in txt:
        # solo coma: si tiene 1-2 dígitos después es decimal, si 3 es miles
        parte = txt.split(",")[-1]
        if len(parte) <= 2:
            txt = txt.replace(",", ".")
        else:
            txt = txt.replace(",", "")
    # solo punto: dejarlo como decimal
    try: return float(txt)
    except: return 0.0


BITACORA_HEADERS = [
    "Fecha aplicación", "Semana nómina", "Empleado", "Tipo", "Monto",
    "Columna Excel", "Razón", "Autoriza", "Notas", "Fecha registro"
]


def asegurar_bitacora(sh, spreadsheet_id, year):
    """Crea la pestaña 'Bitácora YYYY' si no existe (con protección) y devuelve su title."""
    titulo = f"Bitácora {year}"
    meta = sh.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for h in meta["sheets"]:
        if h["properties"]["title"] == titulo:
            return titulo
    # crear pestaña
    resp = sh.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [{"addSheet": {"properties": {"title": titulo}}}]}
    ).execute()
    new_sheet_id = resp["replies"][0]["addSheet"]["properties"]["sheetId"]
    # escribir headers
    sh.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{titulo}!A1",
        valueInputOption="USER_ENTERED",
        body={"values": [BITACORA_HEADERS]}
    ).execute()
    # Proteger la pestaña completa: solo el owner del Sheet puede editar/borrar.
    # Sin `editors.users` explícito, cualquier editor del Sheet puede saltarse la protección.
    sh.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [{
            "addProtectedRange": {
                "protectedRange": {
                    "range": {"sheetId": new_sheet_id},
                    "description": f"Bitácora {year} — registro inmutable. Solo {BITACORA_OWNER} puede editar.",
                    "warningOnly": False,
                    "editors": {"users": [BITACORA_OWNER]}
                }
            }
        }]}
    ).execute()
    print(f"📖 Pestaña '{titulo}' creada y protegida contra edición")
    return titulo


def agregar_a_bitacora(sh, spreadsheet_id, titulo, filas):
    """Appendea filas al final de la Bitácora."""
    sh.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{titulo}!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": filas}
    ).execute()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem", required=True, help="Número de semana (ej. 27)")
    ap.add_argument("--dry-run", action="store_true", help="Solo mostrar cambios, no escribir")
    args = ap.parse_args()

    if args.sem not in NOMINA_POR_SEM:
        print(f"❌ No conozco la semana {args.sem}. Semanas disponibles: {list(NOMINA_POR_SEM)}")
        sys.exit(1)

    sh = build("sheets", "v4", credentials=creds())
    nomina_id = NOMINA_POR_SEM[args.sem]

    # 1) Leer novedades
    novedades = sh.spreadsheets().values().get(
        spreadsheetId=NOVEDADES_ID, range="Novedades"
    ).execute().get("values", [])

    if len(novedades) < 2:
        print("📭 No hay novedades registradas todavía.")
        return

    headers = [str(h).strip().lower() for h in novedades[0]]
    idx = {h: i for i, h in enumerate(headers)}
    for req in ["empleado", "tipo", "monto", "semana afectada"]:
        if req not in idx:
            print(f"❌ Falta columna '{req}' en la pestaña Novedades")
            sys.exit(1)

    # 2) Filtrar por semana y aplicar mapeo
    por_empleado_columna = defaultdict(lambda: defaultdict(float))
    aplicados = []
    ignorados = []

    for r, row in enumerate(novedades[1:], start=2):
        def g(k): return row[idx[k]] if idx[k] < len(row) else ""
        sem_afect = str(g("semana afectada")).strip()
        if sem_afect != args.sem:
            continue
        # ¿ya aplicada?
        if len(row) >= len(headers) + 1 and "✅" in str(row[-1]):
            continue

        emp_corto = g("empleado")
        tipo = norm(g("tipo"))
        monto = parse_monto(g("monto"))

        if tipo not in MAPEO:
            ignorados.append(f"F{r}: tipo '{tipo}' no reconocido (opciones: {', '.join(MAPEO)})")
            continue
        emp_completo = nombre_corto_a_completo(emp_corto)
        if not emp_completo:
            ignorados.append(f"F{r}: empleado '{emp_corto}' no encontrado en el catálogo")
            continue

        col_letra, signo = MAPEO[tipo]
        # ojo: para OTROS/VACACIONES el "signo" indica si es descuento (-1) o abono al descuento (+1)
        # todas las columnas guardan valores positivos; el "abono" resta al descuento existente
        por_empleado_columna[emp_completo][col_letra] += monto * signo
        aplicados.append({
            "fila": r,
            "emp_corto": emp_corto,
            "tipo": g("tipo"),  # original con mayúsculas
            "monto": monto,
            "col_letra": col_letra,
            "razon": g("razón") if "razón" in idx else "",
            "autoriza": g("autoriza") if "autoriza" in idx else "",
            "notas": g("notas") if "notas" in idx else "",
            "fecha_registro": formatear_fecha(g("fecha")) if "fecha" in idx else "",
        })

    if not aplicados and not ignorados:
        print(f"📭 Sin novedades pendientes para la semana {args.sem}.")
        return

    # 3) Localizar filas en la nómina
    nom_vals = sh.spreadsheets().values().get(
        spreadsheetId=nomina_id, range="Hoja1!F9:F40"
    ).execute().get("values", [])
    fila_por_empleado = {}
    for i, row in enumerate(nom_vals):
        if row and row[0]:
            fila_por_empleado[str(row[0]).strip().upper()] = 9 + i

    # 4) Leer valores actuales de las columnas destino
    letras_usadas = {col for cols in por_empleado_columna.values() for col in cols}
    valores_actuales = {}
    for emp_comp, cols in por_empleado_columna.items():
        fila = fila_por_empleado.get(emp_comp.upper())
        if fila is None:
            ignorados.append(f"'{emp_comp}' no está en la nómina S{args.sem}")
            continue
        for col in cols:
            rng = f"Hoja1!{col}{fila}"
            v = sh.spreadsheets().values().get(spreadsheetId=nomina_id, range=rng).execute().get("values", [[""]])
            actual = parse_monto(v[0][0] if v and v[0] else "")
            valores_actuales[(emp_comp, col)] = (fila, actual)

    # 5) Construir updates y mostrar plan
    print(f"\n{'='*70}")
    print(f"APLICAR NOVEDADES → Nómina S{args.sem}  {'(DRY RUN)' if args.dry_run else ''}")
    print(f"{'='*70}\n")
    updates = []
    for emp_comp, cols in por_empleado_columna.items():
        if not any((emp_comp, c) in valores_actuales for c in cols):
            continue
        for col, delta in cols.items():
            fila, actual = valores_actuales[(emp_comp, col)]
            nuevo = max(0, actual + abs(delta)) if delta < 0 else max(0, actual - delta) if delta > 0 and col == "AD" else actual + delta
            # simple: nuevo = actual + |delta| (todo se suma en positivo a la col; el signo del descuento lo interpreta la col misma)
            # excepto abono (delta > 0 en col AD) = resta al descuento existente
            if col == "AD" and delta > 0:  # abono en OTROS
                nuevo = max(0, actual - delta)
            else:
                nuevo = actual + abs(delta)
            emp_corto = NOMBRE_CORTO.get(emp_comp, emp_comp)
            print(f"  {emp_corto:<15} col {col}: {actual:>7.2f}  →  {nuevo:>7.2f}  (Δ {nuevo-actual:+.2f})")
            updates.append({"range": f"Hoja1!{col}{fila}", "values": [[nuevo]]})

    if not updates:
        print("  (nada que aplicar)")
    elif not args.dry_run:
        hoy = date.today().isoformat()

        # 6) PASO 1 - Copiar a Bitácora ANTES de aplicar.
        # Si algo falla en la nómina, al menos queda registro de lo que se intentó.
        # La pestaña Bitácora está protegida contra edición (auditoría inmutable).
        year = str(date.today().year)
        titulo_bit = asegurar_bitacora(sh, NOVEDADES_ID, year)
        filas_bit = []
        for a in aplicados:
            filas_bit.append([
                hoy,                   # Fecha aplicación
                f"S{args.sem}",        # Semana nómina
                a["emp_corto"],        # Empleado
                a["tipo"],             # Tipo
                a["monto"],            # Monto
                a["col_letra"],        # Columna Excel
                a["razon"],            # Razón
                a["autoriza"],         # Autoriza
                a["notas"],            # Notas
                a["fecha_registro"],   # Fecha registro (cuando se puso en Novedades)
            ])
        if filas_bit:
            agregar_a_bitacora(sh, NOVEDADES_ID, titulo_bit, filas_bit)
            print(f"📖 {len(filas_bit)} filas archivadas en '{titulo_bit}' (bitácora inmutable)")

        # 7) PASO 2 - Aplicar a la nómina
        sh.spreadsheets().values().batchUpdate(
            spreadsheetId=nomina_id,
            body={"valueInputOption": "USER_ENTERED", "data": updates}
        ).execute()
        print(f"✅ {len(updates)} celdas actualizadas en la nómina S{args.sem}")

        # 8) PASO 3 - Marcar novedades como aplicadas en la pestaña Novedades
        col_check = len(headers) + 1  # una col después de la última
        letra_check = chr(64 + col_check) if col_check <= 26 else chr(64 + col_check//26) + chr(64 + col_check%26)
        marca_updates = []
        for a in aplicados:
            marca_updates.append({
                "range": f"Novedades!{letra_check}{a['fila']}",
                "values": [[f"✅ aplicado {hoy}"]]
            })
        if marca_updates:
            sh.spreadsheets().values().batchUpdate(
                spreadsheetId=NOVEDADES_ID,
                body={"valueInputOption": "USER_ENTERED", "data": marca_updates}
            ).execute()
            print(f"✅ {len(marca_updates)} novedades marcadas como aplicadas")

    if ignorados:
        print(f"\n⚠️  Ignoradas ({len(ignorados)}):")
        for i in ignorados: print(f"   - {i}")

    print()


if __name__ == "__main__":
    main()
