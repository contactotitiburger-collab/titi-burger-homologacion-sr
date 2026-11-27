#!/usr/bin/env python3
"""SOLO LECTURA: disparadores (triggers) en las tablas que Tito Editor podria tocar, en las 7 bases."""
from lib_lectura import conn, q, SUCS, REF
TABLAS = ("insumosdetalle", "insumos", "insumospresentaciones", "insumospresentacionesdetalle", "productos",
          "productosdetalle", "modificadores", "formasdepago", "costos")
for n, cf in [REF] + SUCS:
    try:
        cn = conn(cf); cur = cn.cursor()
        todos = q(cur, "SELECT t.name trig, OBJECT_NAME(t.parent_id) tabla, t.is_disabled FROM sys.triggers t WHERE t.parent_class=1")
        db = q(cur, "SELECT COUNT(*) n FROM sys.triggers WHERE parent_class=0")[0]["n"]
        rel = [r for r in todos if (r["tabla"] or "").lower() in TABLAS]
        print(f"{n}: {len(todos)} triggers de tabla en total, {db} de base; en tablas del Editor: {rel}")
        cn.close()
    except Exception as e: print(n, "ERROR", e)
