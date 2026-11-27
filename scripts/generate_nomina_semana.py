#!/usr/bin/env python3
"""
generate_nomina_semana.py — genera el Excel formato Nancy (mitad izquierda v2)
para una semana dada, usando /tmp/nomina_30.xlsx como template.

Uso:
  python3 generate_nomina_semana.py --sem 22 --from 2026-05-25 --to 2026-05-31 \
      --sesame ~/.openclaw/data/nomina/sesame_export_sem22.xlsx \
      --output /tmp/nomina_sem22.xlsx

- Clona el template de Nancy /tmp/nomina_30.xlsx (mismos estilos, fuentes,
  formulas de la mitad derecha etc.).
- Sobrescribe:
  * L8 (fecha lunes)
  * L9..R34 (una fila por empleado del catálogo, 7 días L-M-M-J-V-S-D):
      - 1  si el empleado fichó en SESAME ese día
      - "" (vacío) si NO fichó — Nancy marcará luego DESCANSO/FALTA
      - excepto Bryan (fila 15): siempre vacío (medio tiempo, manual)
      - excepto Andrónica: se calcula normal pero fill amarillo (INC.)
- Emite JSON con métricas al stdout final: total_empleados, con_fichaje, sin_fichaje.
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

TEMPLATE = Path('/tmp/nomina_30.xlsx')
CATALOGO_JSON = Path('/tmp/catalogo_empleados.json')

FELIX_TOKENS = {"MEJIA", "ORTEGA", "FELIX"}
BRYAN_TOKENS = {"GONZALEZ", "MONTOYA", "BRYAN"}
ANDRO_TOKENS = {"BAUTISTA", "GOMEZ", "ANDRONICA"}


def norm(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\s+", " ", s).strip().upper()
    return s


def tokens(s: str) -> set[str]:
    return set(norm(s).split())


def load_catalogo():
    return json.loads(CATALOGO_JSON.read_text(encoding="utf-8"))


def load_sesame(xlsx_path: Path):
    """Devuelve dict[sesame_name] -> {fecha_iso: total_horas_float}."""
    import openpyxl
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    # Detectar hoja
    ws = wb["Grupos y tipos de registro"] if "Grupos y tipos de registro" in wb.sheetnames else wb.active
    horas = defaultdict(lambda: defaultdict(float))
    fechas_set = set()
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or len(row) < 9:
            continue
        emp, _tipo, _ident, fecha, _act, _grupo, ent, sal, tiempo = row[:9]
        if not emp or emp == "TOTAL":
            continue
        if not fecha or not ent or not sal:
            continue
        try:
            if isinstance(fecha, datetime):
                fecha_iso = fecha.strftime("%Y-%m-%d")
            else:
                d, m, y = str(fecha).split("/")
                fecha_iso = f"{y}-{int(m):02d}-{int(d):02d}"
        except Exception:
            continue
        fechas_set.add(fecha_iso)
        h = 0.0
        if tiempo:
            try:
                if isinstance(tiempo, str):
                    hh, mm, ss = tiempo.split(":")
                    h = int(hh) + int(mm) / 60 + int(ss) / 3600
                else:
                    h = float(tiempo) * 24  # excel-time float
            except Exception:
                h = 0.0
        horas[emp][fecha_iso] += h
    return dict(horas), sorted(fechas_set)


def match_cat_to_sesame(cat_entry, sesame_names):
    ct = tokens(cat_entry["nombre"])
    best = None
    best_sc = 0
    for name in sesame_names:
        st = tokens(name)
        sc = len(ct & st)
        if sc > best_sc:
            best_sc = sc
            best = name
    return best if best_sc >= 2 else None


def es_bryan(nombre): return BRYAN_TOKENS.issubset(tokens(nombre))
def es_andronica(nombre): return ANDRO_TOKENS.issubset(tokens(nombre))
def es_felix(nombre): return FELIX_TOKENS.issubset(tokens(nombre))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem", required=True)
    ap.add_argument("--from", dest="from_date", required=True)
    ap.add_argument("--to", dest="to_date", required=True)
    ap.add_argument("--sesame", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    import openpyxl
    from openpyxl.styles import PatternFill

    sesame_path = Path(args.sesame).expanduser()
    if not sesame_path.exists():
        print(json.dumps({"ok": False, "error": f"No existe {sesame_path}"}))
        sys.exit(1)

    horas, fechas = load_sesame(sesame_path)
    cat = load_catalogo()

    lunes = datetime.strptime(args.from_date, "%Y-%m-%d")
    # Generar los 7 días ISO
    dias_iso = [(lunes + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    # 1) Copiar template
    shutil.copy(TEMPLATE, args.output)
    wb = openpyxl.load_workbook(args.output)
    ws = wb.active

    # 2) Sobrescribir L8 con fecha lunes de la semana
    ws["L8"] = lunes
    # M8..R8 son formulas =L8+1..+6, se recalculan al abrir (openpyxl no evalúa)

    # 3) Para cada empleado (fila 9 = catálogo id=1 ... fila 34 = id=26)
    #    Regenerar celdas L..R (col 12..18) con 1 o vacío según SESAME.

    yellow_fill = PatternFill(start_color="FFFFFF00", end_color="FFFFFF00", fill_type="solid")
    white_fill = PatternFill(fill_type=None)

    con_fichaje = 0
    sin_fichaje = 0
    empleados_sin = []
    for idx, e in enumerate(cat):
        row = 9 + idx  # fila 9 = primer empleado
        # Regla Bryan: dejar toda la semana en blanco (manual). Ya el template tiene
        # valores; los vaciamos.
        if es_bryan(e["nombre"]):
            for col in range(12, 19):
                cell = ws.cell(row=row, column=col)
                cell.value = None
                # mantener fill pastel amarillo para "captura manual"
                cell.fill = yellow_fill
            continue

        # Regla Félix: no ficha, dejar toda la semana con "1" (patrón trabaja siempre)
        # -- el template los pone en 1; NO lo tocamos.
        if es_felix(e["nombre"]):
            for col in range(12, 19):
                cell = ws.cell(row=row, column=col)
                cell.value = 1
                cell.fill = white_fill
            continue

        ses_name = match_cat_to_sesame(e, horas.keys())
        dias_fichados = 0
        for i, iso in enumerate(dias_iso):
            col = 12 + i  # L=12..R=18
            cell = ws.cell(row=row, column=col)
            h = 0.0
            if ses_name:
                h = horas[ses_name].get(iso, 0)
            if h > 0:
                cell.value = 1
                cell.fill = white_fill  # sin resaltar
                dias_fichados += 1
            else:
                cell.value = None
                # amarillo = "requiere decisión humana DESCANSO vs FALTA"
                cell.fill = yellow_fill

        if dias_fichados > 0:
            con_fichaje += 1
        else:
            sin_fichaje += 1
            empleados_sin.append(e["nombre"])

    # Guardar
    wb.save(args.output)

    print(json.dumps({
        "ok": True,
        "output": args.output,
        "sem": args.sem,
        "rango": f"{args.from_date} .. {args.to_date}",
        "total_empleados": len(cat),
        "con_fichaje": con_fichaje,
        "sin_fichaje": sin_fichaje,
        "sesame_names": len(horas),
        "sin_fichaje_lista": empleados_sin[:10],
        "sesame_fechas_cubiertas": fechas[:3] + ["..."] + fechas[-3:] if len(fechas) > 6 else fechas,
    }))


if __name__ == "__main__":
    main()
