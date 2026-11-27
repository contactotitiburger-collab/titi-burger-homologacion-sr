#!/usr/bin/env python3
"""DIAG 2: confirmar esquema cheques/chequespagos y desglose real de un día con ventas."""
import pymssql, socket, sys

U, P, DB, TDS = "tito", os.environ.get("SR_SQL_PASS",""), "softrestaurant11", "7.0"
HOST = "100.94.218.56"  # Cine Curto
FECHA = sys.argv[1] if len(sys.argv) > 1 else "2026-09-06"

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

pt = puerto(HOST)
c = pymssql.connect(server=HOST, port=pt, user=U, password=P, database=DB,
                    tds_version=TDS, timeout=30, login_timeout=15)
cur = c.cursor()

print("=== columnas de chequespagos ===")
cur.execute("SELECT TOP 1 * FROM chequespagos")
print([d[0] for d in cur.description])

print("\n=== columnas de cheques (con 'fecha','total','cancel') ===")
cur.execute("""SELECT c.name FROM sys.columns c
               JOIN sys.tables t ON t.object_id=c.object_id
               WHERE t.name='cheques' ORDER BY c.column_id""")
cols = [r[0] for r in cur.fetchall()]
print(cols)

print(f"\n=== cheques del {FECHA}: conteo y total ===")
for campo in ("fecha","apertura","cierre"):
    if campo in cols:
        try:
            cur.execute(f"SELECT COUNT(*), SUM(total) FROM cheques WHERE CONVERT(date,{campo})=%s", (FECHA,))
            r = cur.fetchone()
            print(f"   por {campo}: {r[0]} cheques, total ${float(r[1] or 0):,.2f}")
        except Exception as e:
            print(f"   {campo}: err {e}")

print(f"\n=== desglose forma de pago del {FECHA} (por fecha de cheque) ===")
cur.execute("""
    SELECT fp.descripcion, COUNT(*) n, SUM(cp.importe) monto
    FROM chequespagos cp
    JOIN cheques ch ON ch.folio = cp.folio
    LEFT JOIN formasdepago fp ON fp.idformadepago = cp.idformadepago
    WHERE CONVERT(date, ch.fecha) = %s
    GROUP BY fp.descripcion ORDER BY monto DESC
""", (FECHA,))
tot=0
for desc,n,monto in cur.fetchall():
    monto=float(monto or 0); tot+=monto
    print(f"   {str(desc):<20} {n:>4}  ${monto:,.2f}")
print(f"   {'TOTAL':<20} {'':>4}  ${tot:,.2f}")
c.close()
