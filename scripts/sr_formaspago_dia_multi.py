#!/usr/bin/env python3
"""Desglose de formas de pago (agregado) de un día, sobre las sucursales con SQL en vivo.
Agrupa en: Efectivo, Tarjeta, Rappi, DiDi, Uber, Otros."""
import pymssql, socket, sys, json
from collections import defaultdict

U, P, DB, TDS = "tito", os.environ.get("SR_SQL_PASS",""), "softrestaurant11", "7.0"
SUC = [
    ("Hacienda del Río", "100.80.102.110"),
    ("Cine Curto",       "100.94.218.56"),
    ("Villas del Rey",   "100.66.22.9"),
    ("San Marcos",       "100.101.205.89"),
]
FECHA = sys.argv[1] if len(sys.argv) > 1 else "2026-09-08"

# idformadepago -> categoría del pastel
CAT = {
    "EF": "Efectivo", "DLL": "Efectivo",
    "TC": "Tarjeta", "TD": "Tarjeta", "VISA": "Tarjeta", "MC": "Tarjeta",
    "AMEX": "Tarjeta", "CR": "Tarjeta",
    "RA": "Rappi", "DI": "DiDi", "UB": "Uber",
}

def puerto(h):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(5)
    try:
        s.sendto(b"\x02", (h, 1434)); d, _ = s.recvfrom(65535)
        p = d[3:].decode("ascii", "replace").split(";")
        for i, x in enumerate(p):
            if x == "tcp": return int(p[i + 1])
    finally:
        s.close()
    return None

agg = defaultdict(float)
cubiertas, caidas = [], []
for nombre, host in SUC:
    try:
        pt = puerto(host)
        if not pt:
            caidas.append(nombre); continue
        c = pymssql.connect(server=host, port=pt, user=U, password=P, database=DB,
                            tds_version=TDS, timeout=25, login_timeout=12)
        cur = c.cursor()
        cur.execute("""
            SELECT cp.idformadepago, SUM(cp.importe)
            FROM chequespagos cp JOIN cheques ch ON ch.folio = cp.folio
            WHERE CONVERT(date, ch.fecha) = %s AND ch.cancelado = 0
            GROUP BY cp.idformadepago
        """, (FECHA,))
        sub = 0.0
        for idfp, monto in cur.fetchall():
            monto = float(monto or 0); sub += monto
            cat = CAT.get((idfp or "").strip(), "Otros")
            agg[cat] += monto
        c.close()
        cubiertas.append((nombre, sub))
    except Exception as e:
        caidas.append(f"{nombre} (err {type(e).__name__})")

print(f"FECHA {FECHA}")
print("Sucursales cubiertas por SQL:")
tot = 0.0
for n, s in cubiertas:
    print(f"   {n:<18} ${s:,.2f}"); tot += s
print(f"   {'—— subtotal SQL':<18} ${tot:,.2f}")
print("No disponibles:", ", ".join(caidas) if caidas else "ninguna")
print("\nDesglose por forma de pago (agregado):")
for cat in ["Efectivo","Tarjeta","Rappi","DiDi","Uber","Otros"]:
    v = agg.get(cat, 0)
    pct = v/tot*100 if tot else 0
    print(f"   {cat:<10} ${v:,.2f}   {pct:4.1f}%")
