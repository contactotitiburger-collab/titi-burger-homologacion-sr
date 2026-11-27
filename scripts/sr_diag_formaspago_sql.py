#!/usr/bin/env python3
"""DIAGNÓSTICO SQL: catálogo de formas de pago + desglose de un día en Soft Restaurant."""
import pymssql, socket, sys
from collections import defaultdict

U, P, DB, TDS = "tito", os.environ.get("SR_SQL_PASS",""), "softrestaurant11", "7.0"
SUC = [("Hacienda del Río", "100.80.102.110"), ("Cine Curto", "100.94.218.56")]
FECHA = sys.argv[1] if len(sys.argv) > 1 else "2026-09-07"

def puerto(h):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(6)
    try:
        s.sendto(b"\x02", (h, 1434)); d, _ = s.recvfrom(65535)
        p = d[3:].decode("ascii", "replace").split(";")
        for i, x in enumerate(p):
            if x == "tcp": return int(p[i + 1])
    finally:
        s.close()
    return None

def probe(nombre, host):
    print(f"\n############ {nombre} ({host}) ############")
    pt = puerto(host)
    if not pt:
        print("  sin puerto (offline)"); return
    c = pymssql.connect(server=host, port=pt, user=U, password=P, database=DB,
                        tds_version=TDS, timeout=30, login_timeout=15)
    cur = c.cursor()

    print("\n--- catálogo formasdepago ---")
    try:
        cur.execute("SELECT idformadepago, descripcion FROM formasdepago ORDER BY idformadepago")
        for r in cur.fetchall():
            print(f"   {r[0]!r:>8}  {r[1]}")
    except Exception as e:
        print("   error:", e)

    print(f"\n--- desglose por forma de pago del {FECHA} (chequespagos join cheques) ---")
    try:
        cur.execute("""
            SELECT fp.descripcion, COUNT(*) AS n, SUM(cp.importe) AS monto
            FROM chequespagos cp
            JOIN cheques ch ON ch.folio = cp.folio
            LEFT JOIN formasdepago fp ON fp.idformadepago = cp.idformadepago
            WHERE CONVERT(date, ch.fecha) = %s AND ch.cancelado = 0
            GROUP BY fp.descripcion
            ORDER BY monto DESC
        """, (FECHA,))
        tot = 0.0
        for desc, n, monto in cur.fetchall():
            monto = float(monto or 0); tot += monto
            print(f"   {str(desc):<20} {n:>4} pagos  ${monto:,.2f}")
        print(f"   {'TOTAL':<20} {'':>10} ${tot:,.2f}")
    except Exception as e:
        print("   error chequespagos:", e)

    print(f"\n--- columnas directas cheques (efectivo/tarjeta/otros) del {FECHA} ---")
    try:
        cur.execute("""
            SELECT SUM(efectivo), SUM(tarjeta), SUM(vales), SUM(otros), SUM(total)
            FROM cheques WHERE CONVERT(date, fecha) = %s AND cancelado = 0
        """, (FECHA,))
        r = cur.fetchone()
        cols = ["efectivo","tarjeta","vales","otros","total"]
        for k, v in zip(cols, r):
            print(f"   {k:<12} ${float(v or 0):,.2f}")
    except Exception as e:
        print("   error cheques cols:", e)

    c.close()

for nombre, host in SUC:
    try:
        probe(nombre, host)
    except Exception as e:
        print(f"  ERROR {nombre}: {e}")
