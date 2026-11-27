#!/usr/bin/env python3
"""
tito_query.py — consultas rápidas de asistencia/nómina para el bot de WhatsApp de Tito.

Fuentes:
  - ~/.openclaw/data/nomina/sesame_ultima_semana.xlsx  (export SESAME, semana 22-28 jun 2026)
  - ~/.openclaw/data/nomina/catalogo_empleados.json     (26 empleados con sucursal/salario)

Salida SIEMPRE en texto plano corto (<= 5 líneas), listo para WhatsApp.
NO JSON, NO tablas. En español natural.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

DATA_DIR = Path.home() / ".openclaw" / "data" / "nomina"
SESAME_XLSX = DATA_DIR / "sesame_ultima_semana.xlsx"
CATALOGO_JSON = DATA_DIR / "catalogo_empleados.json"

# Empleados con reglas especiales (excluidos de "sin fichaje")
FELIX_TOKENS = {"MEJIA", "ORTEGA", "FELIX"}       # patrón no ficha
BRYAN_TOKENS = {"GONZALEZ", "MONTOYA", "BRYAN"}   # medio tiempo


# ---------- helpers ----------
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


def load_sesame():
    """Devuelve dict[sesame_name] -> {fecha_iso: total_horas_float}."""
    import openpyxl  # lazy import

    wb = openpyxl.load_workbook(SESAME_XLSX, data_only=True)
    ws = wb["Grupos y tipos de registro"]
    horas = defaultdict(lambda: defaultdict(float))
    fechas_set = set()
    for row in ws.iter_rows(min_row=2, values_only=True):
        emp, _tipo, _ident, fecha, _act, _grupo, ent, sal, tiempo = row
        if not emp or emp == "TOTAL":
            continue
        if not fecha or not ent or not sal:
            continue
        try:
            d, m, y = fecha.split("/")
            fecha_iso = f"{y}-{int(m):02d}-{int(d):02d}"
        except Exception:
            continue
        fechas_set.add(fecha_iso)
        h = 0.0
        if tiempo:
            try:
                hh, mm, ss = str(tiempo).split(":")
                h = int(hh) + int(mm) / 60 + int(ss) / 3600
            except Exception:
                h = 0.0
        horas[emp][fecha_iso] += h
    fechas_ord = sorted(fechas_set)
    return dict(horas), fechas_ord


def fuzzy_find_sesame(query: str, sesame_names):
    """Empata query (fragmento) contra nombres SESAME. Devuelve el mejor o None."""
    qt = tokens(query)
    best = None
    best_sc = 0
    for name in sesame_names:
        st = tokens(name)
        sc = len(qt & st)
        if sc > best_sc:
            best_sc = sc
            best = name
    return best if best_sc >= 1 else None


def fuzzy_find_catalogo(query: str, catalogo):
    qt = tokens(query)
    best = None
    best_sc = 0
    for e in catalogo:
        st = tokens(e["nombre"])
        sc = len(qt & st)
        if sc > best_sc:
            best_sc = sc
            best = e
    return best if best_sc >= 1 else None


def match_cat_to_sesame(cat_entry, sesame_names):
    """Empata un empleado del catálogo con su nombre SESAME. None si no aparece."""
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


def es_felix(nombre: str) -> bool:
    return FELIX_TOKENS.issubset(tokens(nombre))


def es_bryan(nombre: str) -> bool:
    return BRYAN_TOKENS.issubset(tokens(nombre))


def fmt_nombre_corto(nombre_upper: str) -> str:
    """MARTINEZ DOMINGUEZ JENNIFER AYLIN -> Jennifer Aylin Martínez."""
    parts = nombre_upper.split()
    if len(parts) >= 3:
        return f"{parts[-2].capitalize()} {parts[-1].capitalize()} {parts[0].capitalize()}"
    return " ".join(p.capitalize() for p in parts)


# ---------- subcomandos ----------
def cmd_quien_falto(args):
    horas, fechas = load_sesame()
    cat = load_catalogo()
    if not fechas:
        print("SESAME vacío o corrupto.")
        return

    rango_ini, rango_fin = fechas[0], fechas[-1]

    if args.fecha:
        target = [args.fecha]
    else:
        target = fechas  # semana completa por default

    sin_fichaje = []
    incierto = []
    felix_note = False
    for e in cat:
        ses_name = match_cat_to_sesame(e, horas.keys())
        if es_felix(e["nombre"]):
            felix_note = True
            continue  # excluido: patrón no ficha
        dias_fichados = 0
        if ses_name:
            for f in target:
                if horas[ses_name].get(f, 0) > 0:
                    dias_fichados += 1
        total = len(target)
        if dias_fichados == 0:
            entry = (e, dias_fichados, total)
            # Andrónica: status incierto
            if "ANDRONICA" in tokens(e["nombre"]):
                incierto.append(entry)
            else:
                sin_fichaje.append(entry)

    ini_d = datetime.strptime(rango_ini, "%Y-%m-%d").strftime("%d")
    fin_d = datetime.strptime(rango_fin, "%Y-%m-%d").strftime("%d")
    mes = datetime.strptime(rango_fin, "%Y-%m-%d").strftime("%b").lower()
    if args.fecha:
        target_txt = datetime.strptime(args.fecha, "%Y-%m-%d").strftime("%d %b").lower()
        header = f"Fecha {target_txt} (SESAME):"
    else:
        header = f"Semana {ini_d}-{fin_d} {mes} (SESAME):"

    lineas = [header]
    if not sin_fichaje and not incierto:
        lineas.append("Sin fichaje: (nadie).")
    else:
        chunks = []
        for e, d, t in sin_fichaje:
            nm = fmt_nombre_corto(e["nombre"])
            suc = e.get("sucursal_codigo", "?")
            chunks.append(f"{nm} ({suc}, {d}/{t} días)")
        if incierto:
            for e, d, t in incierto:
                nm = fmt_nombre_corto(e["nombre"])
                suc = e.get("sucursal_codigo", "?")
                chunks.append(f"{nm} ({suc}, INC. {d}/{t})")
        if chunks:
            lineas.append("Sin fichaje: " + ", ".join(chunks) + ".")
    lineas.append('Nota: no puedo distinguir "descanso" de "falta" hasta integrar el Sheet de Félix.')
    print("\n".join(lineas))


def cmd_horas(args):
    horas, fechas = load_sesame()
    q = " ".join(args.horas)
    ses_name = fuzzy_find_sesame(q, horas.keys())
    if not ses_name:
        # buscar en catálogo por si aparece pero no ficha
        cat = load_catalogo()
        c = fuzzy_find_catalogo(q, cat)
        if c:
            if es_felix(c["nombre"]):
                print(f"{fmt_nombre_corto(c['nombre'])}: no ficha (patrón).")
            else:
                print(f"{fmt_nombre_corto(c['nombre'])}: 0h (sin fichaje esta semana).")
            return
        print(f'No encontré a "{q}" en SESAME ni catálogo.')
        return
    total = sum(horas[ses_name].values())
    dias = sum(1 for v in horas[ses_name].values() if v > 0)
    ini = datetime.strptime(fechas[0], "%Y-%m-%d").strftime("%d")
    fin = datetime.strptime(fechas[-1], "%Y-%m-%d").strftime("%d %b").lower()
    print(f"{ses_name}: {total:.1f}h en {dias} días ({ini}-{fin}).")


def cmd_resumen(args):
    horas, fechas = load_sesame()
    cat = load_catalogo()
    if not fechas:
        print("SESAME vacío.")
        return
    con_fichaje = 0
    sin_fichaje = 0
    total_horas = 0.0
    for e in cat:
        if es_felix(e["nombre"]):
            continue  # no cuenta
        ses_name = match_cat_to_sesame(e, horas.keys())
        h = sum(horas.get(ses_name, {}).values()) if ses_name else 0
        if h > 0:
            con_fichaje += 1
            total_horas += h
        else:
            sin_fichaje += 1
    prom = total_horas / con_fichaje if con_fichaje else 0
    ini_d = datetime.strptime(fechas[0], "%Y-%m-%d").strftime("%d")
    fin_d = datetime.strptime(fechas[-1], "%Y-%m-%d").strftime("%d %b").lower()
    print(f"Semana {ini_d}-{fin_d} (SESAME):")
    print(f"Con fichaje: {con_fichaje}. Sin fichaje: {sin_fichaje} (excl. Félix).")
    print(f"Total: {total_horas:.0f}h. Promedio: {prom:.1f}h/empleado.")


def cmd_dias(args):
    horas, fechas = load_sesame()
    q = " ".join(args.dias_trabajados)
    ses_name = fuzzy_find_sesame(q, horas.keys())
    if not ses_name:
        cat = load_catalogo()
        c = fuzzy_find_catalogo(q, cat)
        if c:
            if es_felix(c["nombre"]):
                print(f"{fmt_nombre_corto(c['nombre'])}: no ficha (patrón).")
            else:
                print(f"{fmt_nombre_corto(c['nombre'])}: 0 días fichados esta semana.")
            return
        print(f'No encontré a "{q}".')
        return
    dias = sum(1 for v in horas[ses_name].values() if v > 0)
    total = len(fechas)
    ini_d = datetime.strptime(fechas[0], "%Y-%m-%d").strftime("%d")
    fin_d = datetime.strptime(fechas[-1], "%Y-%m-%d").strftime("%d %b").lower()
    print(f"{ses_name}: {dias}/{total} días fichados ({ini_d}-{fin_d}).")


# ---------- CLI ----------
def build_parser():
    p = argparse.ArgumentParser(
        description="Consultas de asistencia/nómina desde SESAME + catálogo. Salida corta lista para WhatsApp."
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--quien-falto", action="store_true", help="Empleados sin fichaje esa semana/fecha.")
    g.add_argument("--horas", nargs="+", metavar="NOMBRE", help="Total de horas de un empleado (fuzzy).")
    g.add_argument("--resumen-semana", action="store_true", help="Resumen ejecutivo de la semana.")
    g.add_argument("--dias-trabajados", nargs="+", metavar="NOMBRE", help="Cuántos días fichó un empleado.")

    p.add_argument("--semana-pasada", action="store_true", help="(default) usar toda la semana del export.")
    p.add_argument("--fecha", metavar="YYYY-MM-DD", help="Un solo día (solo para --quien-falto).")
    return p


def main():
    p = build_parser()
    args = p.parse_args()
    if args.quien_falto:
        cmd_quien_falto(args)
    elif args.horas:
        cmd_horas(args)
    elif args.resumen_semana:
        cmd_resumen(args)
    elif args.dias_trabajados:
        cmd_dias(args)


if __name__ == "__main__":
    main()
