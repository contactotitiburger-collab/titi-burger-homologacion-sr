#!/usr/bin/env python3
"""
nomina_generar_semana.py — genera la nómina de una semana en el formato
exacto de Andrónica (Titi Burger), a partir del template limpio.

Uso:
  python3 nomina_generar_semana.py --sem 28 --from 2026-07-06 --to 2026-07-12 \
      --sesame ~/.openclaw/data/nomina/sesame_export_sem28.xlsx \
      --output /tmp/nomina_sem28.xlsx

Flujo:
  1. Copia template_nomina.xlsx
  2. Actualiza A3 (periodo), AG3/AI3 (rango fechas), fila 8 col L-R
  3. Por empleado (fila 9-32):
     - Match nombre catálogo ↔ SESAME
     - Llena L..R con 1/vacío según fichaje
     - Bono puntual (V): monto esperado si 0 faltas, si no 0.
       Excepciones (Enrique, Yazmín, David): siempre 0 (no aplica regla).
     - Bono encargado (X): valor esperado del catálogo, sin cambios.
     - Descuento celular (AA): aplica el monto del catálogo si toca semana.
  4. Actualiza hojas CHECADOR y PRESTAMOS Y AHORROS con las fechas.
  5. Guarda xlsx.

Reglas conocidas (13-jul-2026):
  - Semana martes-lunes? NO, es lunes-domingo (verificado con SESAME S27).
  - Puntualidad: 1 falta = 0 bono. Excepto Enrique/Yazmín/David.
  - Bryan: sueldo $2100 medio tiempo (ya en catálogo).
  - Celular semanal: se aplica todas las semanas.
  - Celular mensual: se aplica en la 1a semana del mes (heurística; verificar).
"""
from __future__ import annotations
import argparse
import json
import sys
import shutil
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

import openpyxl

TEMPLATE = Path("/home/tito/.openclaw/data/nomina/template_nomina.xlsx")
CATALOGO_EMP = Path("/home/tito/.openclaw/data/nomina/catalogo_empleados_s27.json")
CATALOGO_CEL = Path("/home/tito/.openclaw/data/nomina/catalogo_celular.json")
APODOS_PATH = Path("/home/tito/.openclaw/data/nomina/horarios/apodos.json")
HORARIO_DIR = Path("/home/tito/.openclaw/data/nomina/horarios")

# Empleados de oficina que NO aplican regla de bono puntual (siempre BP=0)
# Confirmado por comparación con nómina S27 de Nancy 13-jul-2026
BP_NO_APLICA = {"ENRIQUE"}  # David ahora sí recibe BP (Rafael 16-jul)

MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def norm(s: str) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return " ".join(s.upper().split())


def tokens(s: str) -> set:
    return set(norm(s).split())


def safe_set(ws, row, col, value):
    try:
        ws.cell(row=row, column=col).value = value
    except AttributeError:
        pass  # MergedCell


def load_sesame(path: Path):
    """dict[nombre_sesame] -> {fecha_iso: horas_float}"""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Grupos y tipos de registro"] if "Grupos y tipos de registro" in wb.sheetnames else wb.active
    from collections import defaultdict
    horas = defaultdict(lambda: defaultdict(float))
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or len(row) < 9: continue
        emp, _, _, fecha, _, _, ent, sal, tiempo = row[:9]
        if not emp or emp == "TOTAL" or not fecha or not ent or not sal: continue
        try:
            if isinstance(fecha, datetime):
                f_iso = fecha.strftime("%Y-%m-%d")
            else:
                d, m, y = str(fecha).split("/")
                f_iso = f"{y}-{int(m):02d}-{int(d):02d}"
        except Exception:
            continue
        h = 0.0
        if tiempo:
            try:
                if isinstance(tiempo, str):
                    hh, mm, ss = tiempo.split(":")
                    h = int(hh) + int(mm)/60 + int(ss)/3600
                else:
                    h = float(tiempo) * 24
            except Exception:
                pass
        horas[emp][f_iso] += h
    return dict(horas)


def match_sesame(nombre_cat: str, sesame_names) -> str | None:
    ct = tokens(nombre_cat)
    best, best_sc = None, 0
    for sn in sesame_names:
        st = tokens(sn)
        sc = len(ct & st)
        if sc > best_sc:
            best, best_sc = sn, sc
    return best if best_sc >= 2 else None


def descuento_celular_esta_semana(nombre_cat: str, catalogo_cel: dict, lunes: date):
    """Retorna monto a descontar esta semana (0 si no aplica)."""
    for nc, info in catalogo_cel.items():
        if tokens(nombre_cat) == tokens(nc):
            if info["frecuencia"] == "semana":
                return info["monto_por_periodo"] or 0
            elif info["frecuencia"] == "mes":
                # Se aplica en la ÚLTIMA semana del mes (día del lunes >= 22)
                # Corregido 16-jul: Nancy no descuenta al inicio del mes
                if lunes.day >= 22:
                    return info["monto_por_periodo"] or 0
    return 0


def es_bryan(nombre): return "BRYAN" in norm(nombre) and "GONZALEZ" in norm(nombre)
def es_felix(nombre): return "FELIX" in norm(nombre) and "MEJIA" in norm(nombre)
def no_ficha_sesame(nombre):
    """Empleados que no fichan SESAME — dar días del horario como trabajados."""
    n = norm(nombre)
    return ("FELIX" in n and "MEJIA" in n) or ("FRANCISCO" in n and "JAVIER" in n)


def cargar_horario(sem):
    """Carga el horario semanal si existe. Devuelve dict apodo -> [7 códigos L-D]."""
    for p in HORARIO_DIR.glob(f"s{sem}_*.json"):
        return json.loads(p.read_text())
    return None


def leer_sin_app(sem):
    sem = int(sem)  # fix: args.sem es string
    """
    Devuelve dict {nombre_completo_upper: n_dias_sin_app} para la semana dada.
    Cada fila "Sin app" en Novedades cuenta como 1 día perdonado.
    Semana se puede especificar en col "Semana afectada" o se deriva de "Fecha".
    """
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from collections import defaultdict

    NOV = "141Tcn1ZYHQQYjbgWM0DZCXT9YX1hExdFKfarLz5mBo8"
    SA_FILE = "/home/tito/.openclaw/credentials/google/service-account.json"
    try:
        c = service_account.Credentials.from_service_account_file(
            SA_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        sh = build("sheets", "v4", credentials=c)
        # Layout desde 2026-07-15: A=Fecha B=Semana(auto) C=Empleado D=Tipo E=Monto F=Razón G=Autoriza H=Notas
        rows = sh.spreadsheets().values().get(
            spreadsheetId=NOV, range="Novedades!A2:H200"
        ).execute().get("values", [])
    except Exception as e:
        print(f"[warn] no pude leer Sin app: {e}")
        return {}

    # Cargar apodos para invertir apodo/nombre corto → nombre completo
    apodos = json.loads(APODOS_PATH.read_text())
    nombre_a_apodo = {v: k for k, v in apodos.items() if v}
    # Diccionario palabra → nombre completo: cada palabra del nombre apunta al full
    # Ej: "VELAZQUEZ PEREZ OSCAR" genera keys VELAZQUEZ, PEREZ, OSCAR (fix bug 16-jul)
    cat = json.loads(CATALOGO_EMP.read_text())
    corto_a_completo = {}
    for e in cat:
        for palabra in e["nombre"].split():
            key = norm(palabra)
            if len(key) >= 3:
                if key not in corto_a_completo:
                    corto_a_completo[key] = e["nombre"]
                elif corto_a_completo[key] != e["nombre"]:
                    corto_a_completo[key] = None  # ambiguo

    # 2026-07-15: cada fila "Sin app" = 1 día perdonado.
    # Layout: A=Fecha B=Semana(auto) C=Empleado D=Tipo E=Monto F=Razón G=Autoriza H=Notas
    # Prioridad para determinar semana:
    #   1) col B (Semana auto) si es número
    #   2) col A (Fecha) si es fecha válida
    #   3) FALLBACK: asumir "semana pasada" (la que estamos regenerando = sem del arg)
    # Con eso Rafael puede capturar solo "empleado + Sin app" sin fecha ni semana y funciona.
    from datetime import datetime
    sin_app = defaultdict(int)
    for row in rows:
        if len(row) < 4: continue
        row = row + [""] * (8 - len(row))
        fecha_str, sem_auto, empleado, tipo, monto, razon, autoriza, notas = row[:8]
        if not tipo: continue
        if "sin app" not in tipo.lower(): continue
        # Determinar semana
        sem_row = None
        if str(sem_auto).strip().isdigit():
            sem_row = int(sem_auto)
        elif fecha_str:
            try:
                fecha_str = str(fecha_str).strip()
                for fmt in ("%Y-%m-%d","%d/%m/%Y","%d-%m-%Y","%m/%d/%Y"):
                    try:
                        d = datetime.strptime(fecha_str, fmt).date()
                        sem_row = d.isocalendar()[1]
                        break
                    except ValueError: continue
            except Exception: pass
        # Fallback: sin fecha ni semana → asumimos que es de la semana pasada (sem)
        if sem_row is None:
            sem_row = sem
        if sem_row != sem: continue
        e_upper = norm(empleado)
        # 1) apodo directo
        if e_upper in apodos and apodos[e_upper]:
            sin_app[apodos[e_upper]] += 1
            continue
        # 2) palabra única del catálogo
        if e_upper in corto_a_completo and corto_a_completo[e_upper]:
            sin_app[corto_a_completo[e_upper]] += 1
            continue
        # 3) intersección de palabras
        palabras_sh = set(p for p in e_upper.split() if len(p) >= 3)
        if palabras_sh:
            mejor, sc = None, 0
            for cand in cat:
                pcat = set(norm(p) for p in cand["nombre"].split() if len(p) >= 3)
                s = len(palabras_sh & pcat)
                if s > sc: sc, mejor = s, cand["nombre"]
                elif s == sc and s > 0: mejor = None
            if mejor:
                sin_app[mejor] += 1
    return dict(sin_app)


def leer_novedades_por_tipo(sem):
    import sys
    sem = int(sem)  # fix: args.sem es string
    """
    Lee TODAS las novedades del sheet y devuelve dict {(nombre_completo, tipo): monto_total_semana}.
    Tipos manejados: FONACOT, INFONAVIT, Vacaciones, Horas extra, Bono, Adelanto, Abono.
    Sin app se ignora aquí (ya lo maneja leer_sin_app para el bono puntual).
    """
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from collections import defaultdict

    NOV = "141Tcn1ZYHQQYjbgWM0DZCXT9YX1hExdFKfarLz5mBo8"
    SA_FILE = "/home/tito/.openclaw/credentials/google/service-account.json"
    try:
        c = service_account.Credentials.from_service_account_file(
            SA_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        sh = build("sheets", "v4", credentials=c)
        rows = sh.spreadsheets().values().get(
            spreadsheetId=NOV, range="Novedades!A2:H200",
            valueRenderOption='UNFORMATTED_VALUE'
        ).execute().get("values", [])
    except Exception as e:
        print(f"[warn] no pude leer novedades por tipo: {e}")
        return {}

    apodos = json.loads(APODOS_PATH.read_text())
    cat = json.loads(CATALOGO_EMP.read_text())
    # Mapa nombre_corto → nombre_completo: cada palabra del nombre completo apunta al full
    # Ej: "VELAZQUEZ PEREZ OSCAR" genera keys ["VELAZQUEZ", "PEREZ", "OSCAR"]
    corto_a_completo = {}
    for e in cat:
        for palabra in e["nombre"].split():
            key = norm(palabra)
            if len(key) >= 3:  # evitar apellidos de 2 letras raros
                # si ya existía y apunta a otro nombre, no sobreescribir (ambigüedad)
                if key not in corto_a_completo:
                    corto_a_completo[key] = e["nombre"]
                elif corto_a_completo[key] != e["nombre"]:
                    corto_a_completo[key] = None  # ambiguo, no usable

    from datetime import datetime
    result = defaultdict(float)
    for row in rows:
        if len(row) < 4: continue
        row = list(row) + [""] * (8 - len(row))
        fecha_str, sem_auto, empleado, tipo, monto, razon, autoriza, notas = row[:8]
        # Determinar semana
        sem_row = None
        if str(sem_auto).strip().replace('.0','').isdigit():
            sem_row = int(float(sem_auto))
        elif fecha_str:
            try:
                if isinstance(fecha_str, (int, float)):
                    d = (datetime(1899,12,30) + timedelta(days=int(fecha_str))).date()
                    sem_row = d.isocalendar()[1]
                else:
                    for fmt in ("%Y-%m-%d","%d/%m/%Y","%d-%m-%Y","%m/%d/%Y"):
                        try:
                            d = datetime.strptime(str(fecha_str).strip(), fmt).date()
                            sem_row = d.isocalendar()[1]; break
                        except ValueError: continue
            except Exception: pass
        if sem_row is None: sem_row = sem
        if sem_row != sem: continue
        if not tipo: continue
        tipo_norm = str(tipo).strip()
        if tipo_norm.lower() == 'sin app': continue  # ya lo maneja leer_sin_app
        # Match empleado: 1) apodo directo  2) palabra única del catálogo  3) intersección máxima
        e_upper = norm(empleado)
        nombre_full = None
        if e_upper in apodos and apodos[e_upper]:
            nombre_full = apodos[e_upper]
        elif e_upper in corto_a_completo and corto_a_completo[e_upper]:
            nombre_full = corto_a_completo[e_upper]
        else:
            palabras_sheet = set(p for p in e_upper.split() if len(p) >= 3)
            if palabras_sheet:
                mejor, mejor_score = None, 0
                for cand in cat:
                    palabras_cat = set(norm(p) for p in cand["nombre"].split() if len(p) >= 3)
                    score = len(palabras_sheet & palabras_cat)
                    if score > mejor_score:
                        mejor_score = score
                        mejor = cand["nombre"]
                    elif score == mejor_score and score > 0:
                        mejor = None  # empate → ambiguo
                if mejor_score > 0 and mejor:
                    nombre_full = mejor
        if not nombre_full: continue
        # Sumar monto
        try:
            m = float(monto) if monto else 0
        except (ValueError, TypeError):
            m = 0
        result[(nombre_full, tipo_norm)] += m
    return dict(result)


# Mapeo tipo → índice de columna en el sheet NOMINA (1-based)
# Header: ...V=BP W=Total X=Encargados Y=Festivo Z=Venta AA=Fonacot AB=Infonavit AC=Consumos
#         AD=Otros AE=Vacaciones AF=Pensión AG=Celular AH=Eventos AI=Horas Extra AJ=Total
TIPO_A_COL = {
    'FONACOT':      27,   # AA (descuenta)
    'INFONAVIT':    28,   # AB (descuenta)
    'Vacaciones':   34,   # AH (suma — pago de vacaciones acumuladas; el descuento del banco va en Saldos)
    'Horas extra':  35,   # AI (suma)
    'Bono':         35,   # AI (Horas Extra) — Nancy pone bonos aquí (16-jul)
    'Abono':        30,   # AD (descuenta — pago hacia deuda de Saldos)
    'Adelanto':     30,   # AD (descuenta esta semana — Nancy resta en la semana)
    'Descuento':    30,   # AD (descuenta)
    'Préstamo':     30,   # AD (descuenta)
    # 'Adelanto' NO aquí: va al sheet Saldos como deuda; NO afecta pago semanal.
    # 'Ajuste' NO aquí: el linter debe reclasificarlo a un tipo real.
}


def leer_vacaciones_perdon(sem):
    """Devuelve dict {nombre_completo: n_dias_vacaciones} para perdonar BP sin sumar salario.
    Rafael 16-jul: si un empleado está de vacaciones, se respeta su BP aunque no fiche."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from collections import defaultdict
    sem = int(sem)
    NOV = "141Tcn1ZYHQQYjbgWM0DZCXT9YX1hExdFKfarLz5mBo8"
    SA_FILE = "/home/tito/.openclaw/credentials/google/service-account.json"
    try:
        c = service_account.Credentials.from_service_account_file(
            SA_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
        sh = build("sheets", "v4", credentials=c)
        rows = sh.spreadsheets().values().get(spreadsheetId=NOV,
            range="Novedades!A2:H200").execute().get("values", [])
    except Exception as e:
        return {}
    apodos = json.loads(APODOS_PATH.read_text())
    cat = json.loads(CATALOGO_EMP.read_text())
    corto_a_completo = {}
    for e in cat:
        for palabra in e["nombre"].split():
            key = norm(palabra)
            if len(key) >= 3:
                if key not in corto_a_completo:
                    corto_a_completo[key] = e["nombre"]
                elif corto_a_completo[key] != e["nombre"]:
                    corto_a_completo[key] = None
    from datetime import datetime
    vac = defaultdict(int)
    for row in rows:
        if len(row) < 4: continue
        row = list(row) + [""] * (8 - len(row))
        fecha_str, sem_auto, empleado, tipo, monto, razon, autoriza, notas = row[:8]
        if not tipo or "vacacion" not in tipo.lower(): continue
        sem_row = None
        if str(sem_auto).strip().isdigit(): sem_row = int(sem_auto)
        elif fecha_str:
            for fmt in ("%Y-%m-%d","%d/%m/%Y","%d-%m-%Y","%m/%d/%Y"):
                try: d = datetime.strptime(str(fecha_str).strip(), fmt).date(); sem_row = d.isocalendar()[1]; break
                except: continue
        if sem_row is None: sem_row = sem
        if sem_row != sem: continue
        e_upper = norm(empleado)
        nombre_full = None
        if e_upper in apodos and apodos[e_upper]: nombre_full = apodos[e_upper]
        elif e_upper in corto_a_completo and corto_a_completo[e_upper]: nombre_full = corto_a_completo[e_upper]
        else:
            pw = set(p for p in e_upper.split() if len(p)>=3)
            mejor, sc = None, 0
            for cand in cat:
                pcat = set(norm(p) for p in cand["nombre"].split() if len(p)>=3)
                s = len(pw & pcat)
                if s > sc: sc, mejor = s, cand["nombre"]
                elif s == sc and s > 0: mejor = None
            if mejor: nombre_full = mejor
        if not nombre_full: continue
        vac[nombre_full] += 1
    return dict(vac)


def dias_esperados_por_apodo(horario, apodo):
    """Cuenta días que el empleado DEBIÓ trabajar (T=trabajo, V=vacaciones cuentan como trabajado)."""
    if not horario or apodo not in horario:
        return None  # sin horario, no aplicamos regla
    codigos = horario[apodo]
    return sum(1 for c in codigos if c in ("T", "V"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem", required=True)
    ap.add_argument("--from", dest="from_date", required=True)
    ap.add_argument("--to", dest="to_date", required=True)
    ap.add_argument("--sesame", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    lunes = datetime.strptime(args.from_date, "%Y-%m-%d").date()
    domingo = datetime.strptime(args.to_date, "%Y-%m-%d").date()
    dias_iso = [(lunes + timedelta(days=i)).isoformat() for i in range(7)]

    # Fecha de pago (jueves siguiente = domingo + 4)
    pago = domingo + timedelta(days=4)
    pago_str = f"{pago.day} DE {MESES_ES[pago.month-1].upper()} DE {pago.year}"

    # Cargar catálogos
    catalogo_emp = json.loads(CATALOGO_EMP.read_text())
    catalogo_cel = json.loads(CATALOGO_CEL.read_text())
    apodos = json.loads(APODOS_PATH.read_text())
    # Días con "Sin app" (Nancy avisó que a X no le funcionó SESAME) — no cuenta como falta
    sin_app_por_empleado = leer_sin_app(args.sem)
    # Todas las demás novedades (FONACOT, INFONAVIT, Vacaciones, Horas extra, Bono, Adelanto, etc.)
    novedades_por_tipo = leer_novedades_por_tipo(args.sem)
    # Vacaciones que perdonan BP sin sumar salario (Rafael 16-jul)
    vacaciones_perdon = leer_vacaciones_perdon(args.sem)
    # Invertir mapa: nombre_completo -> apodo
    nombre_a_apodo = {v: k for k, v in apodos.items() if v}
    horario = cargar_horario(args.sem)
    horas = load_sesame(Path(args.sesame))

    # Copiar template
    shutil.copy(TEMPLATE, args.output)
    wb = openpyxl.load_workbook(args.output)
    ws = wb["NOMINA "]

    # Header general
    safe_set(ws, 3, 1, f"PERIODO SEMANAL N°{args.sem}")
    safe_set(ws, 3, 33, datetime(lunes.year, lunes.month, lunes.day))   # AG3
    safe_set(ws, 3, 35, datetime(domingo.year, domingo.month, domingo.day))  # AI3

    # Fechas fila 8 col L..R
    for i, iso in enumerate(dias_iso):
        d = datetime.strptime(iso, "%Y-%m-%d")
        safe_set(ws, 8, 12 + i, d)

    # Por empleado
    resumen = []
    for e in catalogo_emp:
        r = e["row"]
        # Match SESAME
        ses_name = match_sesame(e["nombre"], horas.keys())
        dias = 0
        for i, iso in enumerate(dias_iso):
            col = 12 + i
            if es_bryan(e["nombre"]):
                # Bryan captura manual — dejar vacío
                safe_set(ws, r, col, None)
                continue
            if no_ficha_sesame(e["nombre"]):
                # Félix / Bubu — no fichan SESAME. 6 días trabajados + 1 DES (descanso).
                # Nancy usa este layout: 6 marks de "1" + 1 celda con "DES". Nosotros solo ponemos "1"
                # y damos 6 días (no 7) — así no se dispara el 7mo día extra.
                if i < 6:  # primeros 6 días como trabajados
                    safe_set(ws, r, col, 1)
                    dias += 1
                else:  # día 7 = descanso, dejar vacío
                    safe_set(ws, r, col, None)
                continue
            h = horas.get(ses_name, {}).get(iso, 0) if ses_name else 0
            if h > 0:
                safe_set(ws, r, col, 1)
                dias += 1
            else:
                safe_set(ws, r, col, None)  # blanco → Nancy decide DESCANSO/FALTA

        # Sumar los "Sin app" al conteo de días trabajados (como hace Nancy):
        # Nancy los cuenta como día trabajado para pagar salario + 7mo día.
        # 2026-07-16 fix: antes solo perdonaba BP, ahora también suma al salario.
        sin_app_dias = sin_app_por_empleado.get(e["nombre"], 0)
        if sin_app_dias and not es_bryan(e["nombre"]) and not no_ficha_sesame(e["nombre"]):
            dias += sin_app_dias
            # Marcar en el sheet: llenar las celdas L-R vacías con "1" hasta cubrir los sin_app
            marcados = sin_app_dias
            for i2, iso2 in enumerate(dias_iso):
                if marcados <= 0: break
                col2 = 12 + i2
                if ws.cell(row=r, column=col2).value is None:
                    safe_set(ws, r, col2, 1)
                    marcados -= 1

        # Bono puntual (V = col 22): regla 1 falta = 0
        # Días esperados vienen del HORARIO (T=trabajo + V=vacaciones cuentan).
        # Faltas = esperados - fichados. Si faltas>0 → BP=0.
        bp_esperado = e.get("bono_puntual_esperado") or 0
        nombre_upper = norm(e["nombre"])
        apodo = None
        for nc, ap in nombre_a_apodo.items():
            if norm(nc) == norm(e["nombre"]):
                apodo = ap
                break
        esperados = dias_esperados_por_apodo(horario, apodo) if apodo else None
        if any(nn in nombre_upper for nn in BP_NO_APLICA):
            bp = 0
            regla_bp = "exento"
        elif no_ficha_sesame(e["nombre"]):
            bp = bp_esperado
            regla_bp = "no_ficha_sesame"
        elif esperados is None:
            # Sin horario, fallback: 6+ días → BP completo
            bp = bp_esperado if dias >= 6 else 0
            regla_bp = "fallback_sin_horario"
        else:
            # `dias` YA incluye los sin_app sumados arriba, comparar directo con esperados
            # Además, vacaciones "perdonan" BP sin sumar días de salario (Rafael 16-jul).
            vac_dias = vacaciones_perdon.get(e["nombre"], 0)
            faltas = max(esperados - dias - vac_dias, 0)
            bp = bp_esperado if faltas == 0 else 0
            regla_bp = (f"esp={esperados},dias={dias},vac_perdon={vac_dias},faltas={faltas}")
        safe_set(ws, r, 22, bp)

        # Bono encargado (X = col 24) — del catálogo directo
        safe_set(ws, r, 24, e.get("bono_encargado_esperado") or 0)

        # Descuento celular (AG = col 33)  ← corregido 16-jul (antes iba en AA que es FONACOT)
        desc_cel = descuento_celular_esta_semana(e["nombre"], catalogo_cel, lunes)
        safe_set(ws, r, 33, desc_cel)

        # Novedades del sheet (FONACOT, INFONAVIT, Vacaciones, Horas extra, Bono, Adelanto, etc.)
        for tipo, col in TIPO_A_COL.items():
            monto = novedades_por_tipo.get((e["nombre"], tipo), 0)
            if monto:
                safe_set(ws, r, col, monto)

        resumen.append({
            "num": e["num"],
            "nombre": e["nombre"],
            "apodo": apodo,
            "dias_fichados": dias,
            "dias_esperados": esperados,
            "bp": bp, "bp_esperado": bp_esperado,
            "regla_bp": regla_bp,
            "desc_celular": desc_cel,
        })

    # CHECADOR: título fechas
    ws2 = wb["CHECADOR"]
    dia_from = f"{lunes.day} DE {MESES_ES[lunes.month-1].upper()}"
    dia_to = f"{domingo.day} DE {MESES_ES[domingo.month-1].upper()} DE {domingo.year}"
    safe_set(ws2, 3, 2, f"REGISTRO DE CHECADAS DE SEMANA DEL DIA {dia_from} AL {dia_to}")

    # PRESTAMOS Y AHORROS
    ws3 = wb["PRESTAMOS Y AHORROS YAZMIN"]
    safe_set(ws3, 2, 4, f"PAGO DIA  {pago_str}")
    # Semana de ahorro: incrementar contador — heurística: número de semana del año
    safe_set(ws3, 6, 4, f"SEMANA   PAGADA  DEL  {dia_from} AL {dia_to}")

    wb.save(args.output)

    resultado = {
        "ok": True,
        "output": args.output,
        "sem": args.sem,
        "rango": f"{args.from_date} .. {args.to_date}",
        "pago": pago.isoformat(),
        "empleados": len(catalogo_emp),
        "sesame_matched": sum(1 for e in catalogo_emp if match_sesame(e["nombre"], horas.keys())),
        "resumen": resumen,
    }
    print(json.dumps(resultado, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
