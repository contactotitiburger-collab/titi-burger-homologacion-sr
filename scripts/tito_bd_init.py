#!/usr/bin/env python3
"""
tito_bd_init.py

Crea la BD SQLite del sistema de nómina de Titi Burger y puebla:
  - empleados (Libro 1) desde catalogo_empleados.json
  - descuentos_fijos (Libro 3) con los descuentos confirmados por Don Titi el 2-jul
  - nominas_semanales (Libro 4) con las 10 semanas v2 ya subidas a Drive

movimientos y cierres_mensuales quedan vacías.

Idempotente: si la BD existe, la deja como está a menos que --reset.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path("/home/tito/.openclaw/data/nomina/nomina.db")
CATALOGO_JSON = Path("/home/tito/.openclaw/data/nomina/catalogo_empleados.json")

sys.path.insert(0, str(Path(__file__).parent))
from _nombres_cortos import nombre_corto_para

# --------------------------------------------------------------------------- #
# ESQUEMA
# --------------------------------------------------------------------------- #

SCHEMA = """
CREATE TABLE IF NOT EXISTS empleados (
  id INTEGER PRIMARY KEY,
  nombre_corto TEXT NOT NULL,
  nombre_completo TEXT NOT NULL,
  nss TEXT,
  sucursal_codigo TEXT,
  sucursal_nombre TEXT,
  puesto TEXT,
  salario_semanal REAL,
  bono_puntual REAL,
  bono_encargado REAL,
  fecha_ingreso DATE,
  fecha_baja DATE,
  activo INTEGER DEFAULT 1,
  notas TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS movimientos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fecha DATE NOT NULL,
  empleado_id INTEGER NOT NULL,
  tipo TEXT NOT NULL CHECK(tipo IN ('adelanto','abono','castigo','evento','horas_extra','bono_especial','otro')),
  monto REAL NOT NULL,
  razon TEXT,
  autoriza TEXT,
  semana_afectada TEXT,
  capturado_por TEXT,
  notas TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (empleado_id) REFERENCES empleados(id)
);

CREATE INDEX IF NOT EXISTS idx_mov_empleado ON movimientos(empleado_id);
CREATE INDEX IF NOT EXISTS idx_mov_fecha ON movimientos(fecha);

CREATE TABLE IF NOT EXISTS descuentos_fijos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  empleado_id INTEGER NOT NULL,
  tipo TEXT NOT NULL CHECK(tipo IN ('FONACOT','INFONAVIT','PENSION','CELULAR')),
  monto REAL NOT NULL,
  frecuencia TEXT NOT NULL CHECK(frecuencia IN ('semanal','mensual')),
  fecha_inicio DATE,
  fecha_fin_estimada DATE,
  pagos_hechos INTEGER DEFAULT 0,
  pagos_totales INTEGER,
  activo INTEGER DEFAULT 1,
  notas TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (empleado_id) REFERENCES empleados(id)
);

CREATE TABLE IF NOT EXISTS nominas_semanales (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  semana_num INTEGER NOT NULL,
  fecha_inicio DATE NOT NULL,
  fecha_fin DATE NOT NULL,
  fecha_generada DATE DEFAULT (date('now')),
  total_pagado REAL,
  drive_file_id TEXT,
  version TEXT,
  estado TEXT DEFAULT 'borrador' CHECK(estado IN ('borrador','pagada')),
  notas TEXT,
  UNIQUE(semana_num, version)
);

CREATE TABLE IF NOT EXISTS cierres_mensuales (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  anio INTEGER NOT NULL,
  mes INTEGER NOT NULL,
  total_prestado REAL DEFAULT 0,
  total_abonado REAL DEFAULT 0,
  balance REAL DEFAULT 0,
  empleados_con_adelanto_pendiente INTEGER DEFAULT 0,
  reporte_drive_file_id TEXT,
  fecha_cierre DATE DEFAULT (date('now')),
  UNIQUE(anio, mes)
);
"""

# --------------------------------------------------------------------------- #
# DATOS FIJOS
# --------------------------------------------------------------------------- #

# Descuentos confirmados por Don Titi (via Staff, 2-jul-2026)
# Los pagos_hechos vienen del CATALOGO_CELULARES para celulares.
DESCUENTOS_FIJOS = [
    # FONACOT semanal
    {"nombre_corto": "José Antonio", "tipo": "FONACOT",   "monto": 590.07, "frecuencia": "semanal"},
    {"nombre_corto": "Lucina",       "tipo": "FONACOT",   "monto": 330.45, "frecuencia": "semanal"},
    {"nombre_corto": "Félix",        "tipo": "FONACOT",   "monto": 354.38, "frecuencia": "semanal"},
    {"nombre_corto": "Angel",        "tipo": "FONACOT",   "monto": 413.43, "frecuencia": "semanal"},
    {"nombre_corto": "Sandra",       "tipo": "FONACOT",   "monto": 650.00, "frecuencia": "semanal"},
    # INFONAVIT semanal
    {"nombre_corto": "Guillermo",    "tipo": "INFONAVIT", "monto": 575.54, "frecuencia": "semanal"},
    {"nombre_corto": "Andrónica",    "tipo": "INFONAVIT", "monto": 393.94, "frecuencia": "semanal"},
    # Pensión semanal
    {"nombre_corto": "Carlos",       "tipo": "PENSION",   "monto": 350.00, "frecuencia": "semanal"},
    # Celulares (fuente: Nancy, catalogo celulares confirmado por Don Titi)
    {"nombre_corto": "Guillermo",    "tipo": "CELULAR",   "monto": 257.00, "frecuencia": "semanal",
     "pagos_hechos": 26, "pagos_totales": 97, "notas": "fuente: catálogo Nancy"},
    {"nombre_corto": "David",        "tipo": "CELULAR",   "monto": 264.00, "frecuencia": "mensual",
     "pagos_hechos": 7,  "pagos_totales": 25, "notas": "fuente: catálogo Nancy"},
    {"nombre_corto": "Félix",        "tipo": "CELULAR",   "monto": 150.00, "frecuencia": "semanal",
     "pagos_hechos": 26, "pagos_totales": 145, "notas": "fuente: catálogo Nancy"},
]

# 10 archivos v2 en Drive (fuente: batch_report.json)
NOMINAS_V2 = [
    (18, "2026-04-27", "2026-05-03",  86559.48, "1LCgltm3P9x0lTLuS5ZPcDNk7ArnxxusUiREssRjXQMs"),
    (19, "2026-05-04", "2026-05-10",  89645.57, "14U7YulD4EOsu-OZ6dufIVFBV3fRP42WxGBwA4rmaLRs"),
    (20, "2026-05-11", "2026-05-17",  92217.31, "1oB4xqcaG4hzZF3p1zqvQiV2ljia-qk1rRC23WNVfnx0"),
    (21, "2026-05-18", "2026-05-24",  89131.22, "11_XyXQpSL-nhleh1cR1bcbOxgJzZIXRGcqhxZPT_VqQ"),
    (22, "2026-05-25", "2026-05-31",  90674.27, "1qMFEydA81Q9Ge5OgtfKp5OAVMhMjzbN_qBaz5VZ9OSY"),
    (23, "2026-06-01", "2026-06-07",  88102.53, "1_TwxlBXsCk45w4nNyyGc-07nDLLnABnK9YCCwPWgwec"),
    (24, "2026-06-08", "2026-06-14",  87588.18, "1MgoArOxuV9lT_CCtMT6FWcEDumnDlFAtaPM7tcA7cvc"),
    (25, "2026-06-15", "2026-06-21",  84502.09, "1mka8GlzLpeZGyFG_0uOuyLen04LUuaToypFRo9S8qk4"),
    (26, "2026-06-22", "2026-06-28", 136250.97, "1zdo1lIa_Qlr3P5OHhnW5psX--jmOdwU1ZJTugZINsY4"),
    (27, "2026-06-29", "2026-07-05",  50555.10, "1TU2Su3qgKgYMmwxY9K-JXcaQ87sVKmHD-uW4ewZQZDo"),
]

# Rosa María fue despedida ~14-jun-2026 (fin sem 24), [[regla-bono-bajo-problemas]]
ROSA_MARIA_BAJA = "2026-06-14"


# --------------------------------------------------------------------------- #
# LÓGICA
# --------------------------------------------------------------------------- #

def crear_esquema(conn):
    conn.executescript(SCHEMA)
    conn.commit()


def poblar_empleados(conn, catalogo):
    cur = conn.cursor()
    for e in catalogo:
        nombre_completo = e["nombre"]
        nombre_corto = nombre_corto_para(nombre_completo)
        notas = "; ".join(e.get("notas", []) or [])
        activo = 1
        fecha_baja = None
        if nombre_completo == "MAGAÑA LOPEZ ROSA MARIA":
            activo = 0
            fecha_baja = ROSA_MARIA_BAJA
            notas = (notas + "; " if notas else "") + "baja ~14-jun-2026 (bono bajado 3 semanas consecutivas)"
        cur.execute("""
            INSERT OR REPLACE INTO empleados
              (id, nombre_corto, nombre_completo, nss, sucursal_codigo, sucursal_nombre,
               puesto, salario_semanal, bono_puntual, bono_encargado,
               fecha_ingreso, fecha_baja, activo, notas)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            e["id"], nombre_corto, nombre_completo, e.get("nss"),
            e.get("sucursal_codigo"), e.get("sucursal_nombre"),
            e.get("puesto"), e.get("salario_semanal"),
            e.get("bono_puntual"), e.get("bono_encargado"),
            e.get("fecha_ingreso"), fecha_baja, activo, notas or None,
        ))
    conn.commit()


def poblar_descuentos(conn):
    cur = conn.cursor()
    # limpia primero para evitar duplicados si se re-ejecuta
    cur.execute("DELETE FROM descuentos_fijos")
    for d in DESCUENTOS_FIJOS:
        cur.execute("SELECT id FROM empleados WHERE nombre_corto=?", (d["nombre_corto"],))
        row = cur.fetchone()
        if not row:
            print(f"  WARN: no encuentro empleado '{d['nombre_corto']}' para descuento {d['tipo']}", file=sys.stderr)
            continue
        cur.execute("""
            INSERT INTO descuentos_fijos
              (empleado_id, tipo, monto, frecuencia, pagos_hechos, pagos_totales, notas, activo)
            VALUES (?,?,?,?,?,?,?,1)
        """, (
            row[0], d["tipo"], d["monto"], d["frecuencia"],
            d.get("pagos_hechos", 0), d.get("pagos_totales"),
            d.get("notas"),
        ))
    conn.commit()


def poblar_nominas(conn):
    cur = conn.cursor()
    cur.execute("DELETE FROM nominas_semanales")
    for sem, ini, fin, total, fid in NOMINAS_V2:
        cur.execute("""
            INSERT INTO nominas_semanales
              (semana_num, fecha_inicio, fecha_fin, total_pagado, drive_file_id, version, estado)
            VALUES (?,?,?,?,?,?,?)
        """, (sem, ini, fin, total, fid, "v2", "borrador"))
    conn.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="Borra la BD y la recrea")
    args = ap.parse_args()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if args.reset and DB_PATH.exists():
        DB_PATH.unlink()
        print(f"[reset] BD borrada: {DB_PATH}")

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")

    print("1) Creando esquema...")
    crear_esquema(conn)

    print("2) Cargando catálogo empleados...")
    with open(CATALOGO_JSON) as f:
        catalogo = json.load(f)
    poblar_empleados(conn, catalogo)
    n_emp = conn.execute("SELECT COUNT(*) FROM empleados").fetchone()[0]
    n_act = conn.execute("SELECT COUNT(*) FROM empleados WHERE activo=1").fetchone()[0]
    print(f"   Empleados: {n_emp} total, {n_act} activos, {n_emp-n_act} baja")

    print("3) Descuentos fijos...")
    poblar_descuentos(conn)
    n_desc = conn.execute("SELECT COUNT(*) FROM descuentos_fijos").fetchone()[0]
    print(f"   Descuentos: {n_desc}")

    print("4) Nóminas semanales v2...")
    poblar_nominas(conn)
    n_nom = conn.execute("SELECT COUNT(*) FROM nominas_semanales").fetchone()[0]
    print(f"   Nóminas: {n_nom}")

    print(f"\nBD lista en: {DB_PATH}")
    conn.close()


if __name__ == "__main__":
    main()
