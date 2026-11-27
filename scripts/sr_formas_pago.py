#!/usr/bin/env python3
"""Desglose real de formas de pago (Efectivo/Tarjeta/Rappi/Uber/DiDi) por sucursal,
leído directo de la base SQL de cada carreta (misma conexión que el inventario VMI).

El "día de negocio" de un turno es la fecha de APERTURA, no la de cierre
(un turno que abre 20-sep 18:05 y cierra 21-sep 00:00 es del día 20 — verificado
contra vwrepventascheques el 21-sep-2026).
"""
import json, socket, datetime
from pathlib import Path
import pymssql

CREDS_DIR = Path("/home/tito/.openclaw/credentials/sr_sql")

# Sucursales con conexión SQL lista (Montecarlo sin Tailscale todavía)
SUCURSALES = [
    ("Hacienda del Río", "hacienda_del_rio.json"),
    ("Villas del Rey",   "villas_del_rey.json"),
    ("San Marcos",       "san_marcos.json"),
    ("Cine Curto",       "cine_curto.json"),
    ("L Montejano",      "montejano.json"),
]

BUCKETS = {
    "EFECTIVO": "Efectivo",
    "TARJETA CREDITO": "Tarjeta",
    "TARJETA DEBITO": "Tarjeta",
    "RAPPI": "Rappi",
    "UBER": "Uber",
    "DIDI": "DiDi",
}


def resolver_puerto(host):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(6)
    try:
        s.sendto(b"\x02", (host, 1434))
        data, _ = s.recvfrom(65535)
        parts = data[3:].decode("ascii", "replace").split(";")
        for i, p in enumerate(parts):
            if p == "tcp":
                return int(parts[i + 1])
    finally:
        s.close()
    return None


def desglose_sucursal(ref, fecha):
    """fecha: datetime.date. Devuelve dict {bucket: monto} para esa sucursal."""
    port = resolver_puerto(ref["server"])
    if port is None:
        return None
    conn = pymssql.connect(server=ref["server"], port=port, user=ref["user"],
                            password=ref["password"], database=ref["database"],
                            tds_version=ref["tds_version"], timeout=15)
    cur = conn.cursor()
    cur.execute("""
        SELECT fp.descripcion, SUM(cp.importe)
        FROM chequespagos cp
        JOIN formasdepago fp ON fp.idformadepago = cp.idformadepago
        JOIN turnos t ON t.idturno = cp.idturno_cierre
        WHERE CAST(t.apertura AS DATE) = %s
        GROUP BY fp.descripcion
    """, (fecha,))
    out = {}
    for descripcion, monto in cur.fetchall():
        bucket = BUCKETS.get(descripcion, "Otros")
        out[bucket] = out.get(bucket, 0) + float(monto)
    conn.close()
    return out


def desglose_dia(fecha):
    """fecha: datetime.date. Devuelve dict {sucursal: {bucket: monto}}."""
    resultado = {}
    for nombre, archivo in SUCURSALES:
        ref = json.loads((CREDS_DIR / archivo).read_text())
        try:
            resultado[nombre] = desglose_sucursal(ref, fecha)
        except Exception as e:
            resultado[nombre] = {"_error": str(e)[:150]}
    return resultado


def texto(desglose):
    orden_buckets = ["Efectivo", "Tarjeta", "Rappi", "Uber", "DiDi", "Otros"]
    lineas = ["Formas de pago por carreta:"]
    for suc, d in desglose.items():
        if not d:
            lineas.append(f"  {suc}: sin datos")
            continue
        if "_error" in d:
            lineas.append(f"  {suc}: no se pudo leer ({d['_error']})")
            continue
        partes = [f"{b} ${d[b]:,.0f}" for b in orden_buckets if d.get(b)]
        lineas.append(f"  {suc}: " + " · ".join(partes))
    return "\n".join(lineas)


if __name__ == "__main__":
    import sys
    fecha = datetime.date.today() - datetime.timedelta(days=1)
    if len(sys.argv) > 1:
        fecha = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    d = desglose_dia(fecha)
    print(texto(d))
