#!/usr/bin/env python3
"""
tito_bd.py — CLI para operar la BD de nómina de Titi Burger.

Subcomandos:
  agregar_movimiento --empleado X --tipo Y --monto Z --razon "..." --autoriza "..."
  saldo <empleado_corto>
  saldos
  descuentos_semana <YYYY-MM-DD>
  resumen_mes YYYY-MM
  empleado_historial <nombre>
  borrar_movimiento <id>   (uso interno / pruebas)

BD: /home/tito/.openclaw/data/nomina/nomina.db
"""

import argparse
import sqlite3
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

DB_PATH = Path("/home/tito/.openclaw/data/nomina/nomina.db")

TIPOS_VALIDOS = ("adelanto","abono","castigo","evento","horas_extra","bono_especial","otro")


def conn():
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def resolver_empleado(c, nombre):
    """Busca por nombre_corto (case-insensitive). Devuelve dict o None."""
    row = c.execute("SELECT * FROM empleados WHERE lower(nombre_corto)=lower(?)", (nombre,)).fetchone()
    if row:
        return row
    # fuzzy: contiene
    row = c.execute("SELECT * FROM empleados WHERE lower(nombre_corto) LIKE lower(?)", (f"%{nombre}%",)).fetchone()
    return row


# --------------------------------------------------------------------------- #
# COMANDOS
# --------------------------------------------------------------------------- #

def cmd_agregar_movimiento(args):
    if args.tipo not in TIPOS_VALIDOS:
        print(f"ERROR: tipo '{args.tipo}' no válido. Válidos: {TIPOS_VALIDOS}", file=sys.stderr)
        return 2
    c = conn()
    emp = resolver_empleado(c, args.empleado)
    if not emp:
        print(f"ERROR: no encuentro empleado '{args.empleado}'", file=sys.stderr)
        return 2
    fecha = args.fecha or date.today().isoformat()
    cur = c.execute("""
        INSERT INTO movimientos
          (fecha, empleado_id, tipo, monto, razon, autoriza, semana_afectada, capturado_por, notas)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (fecha, emp["id"], args.tipo, args.monto, args.razon, args.autoriza,
          args.semana, args.capturado_por or "CLI", args.notas))
    c.commit()
    mov_id = cur.lastrowid
    print(f"OK: movimiento #{mov_id} — {emp['nombre_corto']} {args.tipo} ${args.monto:+.2f} ({args.razon or '-'})")
    return 0


def cmd_saldo(args):
    c = conn()
    emp = resolver_empleado(c, args.empleado)
    if not emp:
        print(f"ERROR: no encuentro empleado '{args.empleado}'", file=sys.stderr)
        return 2
    r = c.execute("""
        SELECT
          COALESCE(SUM(CASE WHEN monto<0 THEN monto END), 0) AS adelantos_castigos,
          COALESCE(SUM(CASE WHEN monto>0 THEN monto END), 0) AS abonos_eventos,
          COALESCE(SUM(monto), 0) AS saldo
        FROM movimientos WHERE empleado_id=?
    """, (emp["id"],)).fetchone()
    print(f"{emp['nombre_corto']}: saldo ${r['saldo']:+.2f}"
          f"  (a favor de la empresa: ${abs(r['adelantos_castigos']):.2f}"
          f" / a favor del empleado: ${r['abonos_eventos']:.2f})")
    return 0


def cmd_saldos(args):
    c = conn()
    rows = c.execute("""
        SELECT e.nombre_corto, e.activo,
               COALESCE(SUM(CASE WHEN m.monto<0 THEN m.monto END), 0) AS deuda,
               COALESCE(SUM(CASE WHEN m.monto>0 THEN m.monto END), 0) AS credito,
               COALESCE(SUM(m.monto), 0) AS saldo
        FROM empleados e
        LEFT JOIN movimientos m ON m.empleado_id = e.id
        GROUP BY e.id
        ORDER BY e.activo DESC, e.nombre_corto
    """).fetchall()
    print(f"{'Empleado':<20} {'Deuda':>12} {'Crédito':>12} {'Saldo':>12}  Estado")
    print("-"*72)
    for r in rows:
        estado = "activo" if r["activo"] else "BAJA"
        print(f"{r['nombre_corto']:<20} ${abs(r['deuda']):>10.2f} ${r['credito']:>10.2f} ${r['saldo']:>+10.2f}  {estado}")
    return 0


def _semana_de_fecha(f: date):
    """Devuelve (lunes, domingo) de la semana que contiene f."""
    lun = f - timedelta(days=f.weekday())
    dom = lun + timedelta(days=6)
    return lun, dom


def cmd_descuentos_semana(args):
    """Muestra qué descuentos fijos aplican en la semana que contiene esa fecha."""
    try:
        f = datetime.strptime(args.fecha, "%Y-%m-%d").date()
    except ValueError:
        print("ERROR: fecha debe ser YYYY-MM-DD", file=sys.stderr)
        return 2
    lun, dom = _semana_de_fecha(f)
    c = conn()
    print(f"Descuentos que aplican para semana {lun} a {dom}:")
    print("-"*70)

    # semanales: todos los activos
    rows = c.execute("""
        SELECT e.nombre_corto, d.tipo, d.monto, d.frecuencia, d.pagos_hechos, d.pagos_totales
        FROM descuentos_fijos d JOIN empleados e ON e.id=d.empleado_id
        WHERE d.activo=1 AND e.activo=1
        ORDER BY d.frecuencia, e.nombre_corto, d.tipo
    """).fetchall()
    total_sem = 0
    total_men = 0
    for r in rows:
        aplica = False
        if r["frecuencia"] == "semanal":
            aplica = True
        elif r["frecuencia"] == "mensual":
            # aplica solo si esa semana contiene el día 1..7 del mes (primera semana)
            for d_off in range(7):
                d_ = lun + timedelta(days=d_off)
                if d_.day <= 7:
                    aplica = True
                    break
        if not aplica:
            continue
        pagos = f" ({r['pagos_hechos']}/{r['pagos_totales']})" if r['pagos_totales'] else ""
        print(f"  {r['nombre_corto']:<18} {r['tipo']:<10} ${r['monto']:>8.2f}  ({r['frecuencia']}){pagos}")
        if r["frecuencia"] == "semanal":
            total_sem += r["monto"]
        else:
            total_men += r["monto"]
    print("-"*70)
    print(f"Total semanales: ${total_sem:.2f}   Total mensuales que aplican esta semana: ${total_men:.2f}")
    return 0


def cmd_resumen_mes(args):
    try:
        y, m = args.mes.split("-")
        y = int(y); m = int(m)
    except (ValueError, AttributeError):
        print("ERROR: mes debe ser YYYY-MM", file=sys.stderr)
        return 2
    c = conn()
    ini = date(y, m, 1)
    if m == 12:
        fin = date(y+1, 1, 1) - timedelta(days=1)
    else:
        fin = date(y, m+1, 1) - timedelta(days=1)
    print(f"Resumen {ini} a {fin}")
    rows = c.execute("""
        SELECT tipo, COUNT(*) AS n, SUM(monto) AS total
        FROM movimientos WHERE fecha BETWEEN ? AND ?
        GROUP BY tipo ORDER BY tipo
    """, (ini.isoformat(), fin.isoformat())).fetchall()
    tot_prest = 0
    tot_abon = 0
    for r in rows:
        print(f"  {r['tipo']:<15} n={r['n']:>3}  total=${r['total']:>+12.2f}")
        if r["tipo"] in ("adelanto","castigo"):
            tot_prest += abs(r["total"] or 0)
        if r["tipo"] in ("abono","evento","horas_extra","bono_especial"):
            tot_abon += (r["total"] or 0)
    balance = c.execute("""
        SELECT COALESCE(SUM(monto),0) FROM movimientos WHERE fecha BETWEEN ? AND ?
    """, (ini.isoformat(), fin.isoformat())).fetchone()[0]
    con_deuda = c.execute("""
        SELECT COUNT(*) FROM (
          SELECT empleado_id, SUM(monto) s FROM movimientos
          WHERE fecha<=? GROUP BY empleado_id HAVING s < 0
        )
    """, (fin.isoformat(),)).fetchone()[0]
    print(f"Prestado (adelantos+castigos): ${tot_prest:.2f}")
    print(f"Abonado:                        ${tot_abon:.2f}")
    print(f"Balance del mes:                ${balance:+.2f}")
    print(f"Empleados con adelanto pendiente al cierre: {con_deuda}")
    return 0


def cmd_empleado_historial(args):
    c = conn()
    emp = resolver_empleado(c, args.empleado)
    if not emp:
        print(f"ERROR: no encuentro empleado '{args.empleado}'", file=sys.stderr)
        return 2
    rows = c.execute("""
        SELECT id, fecha, tipo, monto, razon, autoriza, semana_afectada
        FROM movimientos WHERE empleado_id=? ORDER BY fecha DESC, id DESC
    """, (emp["id"],)).fetchall()
    print(f"Historial de {emp['nombre_corto']} ({len(rows)} movimientos):")
    print("-"*90)
    for r in rows:
        print(f"  #{r['id']:>4} {r['fecha']}  {r['tipo']:<12} ${r['monto']:>+10.2f}"
              f"  {r['razon'] or '-':<28} autoriza={r['autoriza'] or '-'}")
    tot = c.execute("SELECT COALESCE(SUM(monto),0) FROM movimientos WHERE empleado_id=?", (emp["id"],)).fetchone()[0]
    print("-"*90)
    print(f"  Saldo actual: ${tot:+.2f}")
    return 0


def cmd_borrar_movimiento(args):
    c = conn()
    r = c.execute("SELECT * FROM movimientos WHERE id=?", (args.id,)).fetchone()
    if not r:
        print(f"ERROR: no existe movimiento #{args.id}", file=sys.stderr)
        return 2
    c.execute("DELETE FROM movimientos WHERE id=?", (args.id,))
    c.commit()
    print(f"OK: borrado movimiento #{args.id}")
    return 0


# --------------------------------------------------------------------------- #

def build_parser():
    p = argparse.ArgumentParser(prog="tito_bd.py")
    sp = p.add_subparsers(dest="cmd", required=True)

    a = sp.add_parser("agregar_movimiento")
    a.add_argument("--empleado", required=True)
    a.add_argument("--tipo", required=True)
    a.add_argument("--monto", type=float, required=True)
    a.add_argument("--razon")
    a.add_argument("--autoriza")
    a.add_argument("--semana")
    a.add_argument("--fecha", help="YYYY-MM-DD, default hoy")
    a.add_argument("--capturado-por", dest="capturado_por")
    a.add_argument("--notas")
    a.set_defaults(func=cmd_agregar_movimiento)

    a = sp.add_parser("saldo")
    a.add_argument("empleado")
    a.set_defaults(func=cmd_saldo)

    a = sp.add_parser("saldos")
    a.set_defaults(func=cmd_saldos)

    a = sp.add_parser("descuentos_semana")
    a.add_argument("fecha")
    a.set_defaults(func=cmd_descuentos_semana)

    a = sp.add_parser("resumen_mes")
    a.add_argument("mes", help="YYYY-MM")
    a.set_defaults(func=cmd_resumen_mes)

    a = sp.add_parser("empleado_historial")
    a.add_argument("empleado")
    a.set_defaults(func=cmd_empleado_historial)

    a = sp.add_parser("borrar_movimiento")
    a.add_argument("id", type=int)
    a.set_defaults(func=cmd_borrar_movimiento)

    return p


def main():
    args = build_parser().parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
