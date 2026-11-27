#!/usr/bin/env python3
"""Mermas y cortesías por carreta — misma fuente SQL que sr_formas_pago.py.
Merma = registros de la tabla `traspasosalmacen` (header de traspasos entre almacenes) con
almacendestino = almacén de MERMAS de la sucursal, ese día (confirmado real 21-sep-2026 con Rafael:
326 traspasos históricos en Cine Curto, muchos con nota "MERMAS"/descripción del motivo).
No pasan todos los días — 2 a 13 veces al mes es lo normal, así que $0/0 movimientos en un día
cualquiera NO es un error, es lo esperado.
OJO: no se encontró tabla de detalle (cantidad/costo) ligada al folio del traspaso — movtosalmacen
y foliosalmacen están vacíos en las sucursales revisadas — así que merma_total queda en $0 siempre;
lo real que sí se tiene es merma_n (cuántos traspasos a mermas hubo) y merma_notas (el texto que
escribió el encargado, cuando lo llenó).
Solo Hacienda del Río y Cine Curto tienen almacén de MERMAS configurado en SR; Villas, San Marcos
y Montejano no lo tienen (no es hueco de captura, la bodega no existe ahí) — para esas MERMAS_ALMACEN
es None.
Cortesías = columna totalcortesias de vwrepventascheques (agrupada por día de apertura del turno, ya la calcula SR).
"""
import json, socket
from pathlib import Path
import pymssql

CREDS_DIR = Path("/home/tito/.openclaw/credentials/sr_sql")

SUCURSALES = [
    ("Hacienda del Río", "hacienda_del_rio.json"),
    ("Villas del Rey",   "villas_del_rey.json"),
    ("San Marcos",       "san_marcos.json"),
    ("Cine Curto",       "cine_curto.json"),
    ("L Montejano",      "montejano.json"),
]

# idalmacen del almacén "MERMAS" por sucursal (None = no tiene esa bodega configurada en SR)
MERMAS_ALMACEN = {
    "Hacienda del Río": "1",
    "Villas del Rey":   None,
    "San Marcos":       None,
    "Cine Curto":       "10",
    "L Montejano":      None,
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


def datos_sucursal(nombre, ref, fecha):
    port = resolver_puerto(ref["server"])
    if port is None:
        return None
    conn = pymssql.connect(server=ref["server"], port=port, user=ref["user"],
                            password=ref["password"], database=ref["database"],
                            tds_version=ref["tds_version"], timeout=15)
    cur = conn.cursor()

    idalmacen_mermas = MERMAS_ALMACEN.get(nombre)
    merma_notas = []
    ajuste_n = 0
    if idalmacen_mermas:
        cur.execute("""
            SELECT nota FROM traspasosalmacen
            WHERE almacendestino = %s AND CAST(fecha AS DATE) = %s
              AND (cancelado IS NULL OR cancelado = 0)
        """, (idalmacen_mermas, fecha))
        rows = cur.fetchall()
        merma_n = 0
        for (nota,) in rows:
            nota_u = (nota or "").upper()
            # "AJUSTE" sin decir "MERMA" es una corrección de inventario, no merma real — se cuenta aparte.
            if "AJUSTE" in nota_u and "MERMA" not in nota_u:
                ajuste_n += 1
                continue
            merma_n += 1
            if nota:
                merma_notas.append(nota)
    else:
        merma_n = 0
    # No se encontró tabla de detalle con costo/cantidad ligada al folio de traspaso —
    # merma_total queda en 0 (no hay valor en pesos disponible), merma_n/notas sí son reales.
    merma_total = 0

    cur.execute("""
        SELECT COALESCE(SUM(totalcortesias), 0)
        FROM vwrepventascheques
        WHERE CAST(cierre AS DATE) = %s
    """, (fecha,))
    (cortesias_total,) = cur.fetchone()

    conn.close()
    return {"merma": float(merma_total), "merma_n": int(merma_n), "merma_notas": merma_notas,
            "ajuste_n": int(ajuste_n), "cortesias": float(cortesias_total)}


def datos_dia(fecha):
    resultado = {}
    for nombre, archivo in SUCURSALES:
        ref = json.loads((CREDS_DIR / archivo).read_text())
        try:
            resultado[nombre] = datos_sucursal(nombre, ref, fecha)
        except Exception as e:
            resultado[nombre] = {"_error": str(e)[:150]}
    return resultado


def texto(desglose):
    lineas = ["Cortesías y mermas por carreta:"]
    tot_cort = 0.0
    tot_n = 0
    for suc, d in desglose.items():
        if not d or "_error" in d:
            lineas.append(f"  {suc}: sin datos" + (f" ({d['_error']})" if d and '_error' in d else ""))
            continue
        tot_cort += d["cortesias"]
        tot_n += d["merma_n"]
        lineas.append(f"  {suc}: cortesías ${d['cortesias']:,.0f} · merma {d['merma_n']} traspaso(s)")
        for nota in d.get("merma_notas", []):
            lineas.append(f"      · {nota}")
    lineas.append("")
    lineas.append(f"TOTAL cortesías: ${tot_cort:,.0f}")
    lineas.append(f"TOTAL merma: {tot_n} traspaso(s)")
    return "\n".join(lineas)


if __name__ == "__main__":
    import sys, datetime
    fecha = datetime.date.today() - datetime.timedelta(days=1)
    if len(sys.argv) > 1:
        fecha = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    d = datos_dia(fecha)
    print(texto(d))
