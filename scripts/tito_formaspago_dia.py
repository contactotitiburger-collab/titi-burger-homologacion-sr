#!/usr/bin/env python3
"""
Desglose de FORMAS DE PAGO de un día, agregado sobre TODAS las carretas.

Fuente: SQL local de Soft Restaurant (tabla chequespagos + formasdepago) por carreta,
vía Tailscale. La nube de SR NO expone forma de pago, por eso vamos al SQL de cada una.

Categorías del pastel: Efectivo, Tarjeta, Rappi, DiDi, Uber, Otros.

Devuelve dict con:
  agg      -> {categoria: monto}
  cubiertas-> [(carreta, monto)]
  faltantes-> [carreta, ...]   (sin SQL o apagadas)
  total_sql-> suma de lo cubierto
"""
import pymssql, socket, json
from collections import defaultdict
from pathlib import Path

U, P, DB, TDS = "tito", os.environ.get("SR_SQL_PASS",""), "softrestaurant11", "7.0"
CACHE_DIR = Path("/home/tito/.openclaw/data/reportes_diarios")


def _ruta_cache(fecha_iso):
    return CACHE_DIR / f"formaspago_{fecha_iso}.json"

# carreta -> host Tailscale del servidor SR.  None = aún NO conectada al SQL.
SUCS_SQL = {
    "L Montejano":      "100.68.233.59",   # tbfovi (conectada 17-sep; corre SR12)
    "Montecarlo":       None,              # pendiente conectar Tailscale+SQL en sitio
    "Hacienda del Río": "100.80.102.110",
    "San Marcos":       "100.101.205.89",
    "Cine Curto":       "100.94.218.56",
    "Villas del Rey":   "100.66.22.9",
}

# Override de base por carreta. L Montejano corre Soft Restaurant 12 -> base 'softrestaurant12'
# (las demás son SR11 -> 'softrestaurant11', el default DB de arriba).
DB_POR_CARRETA = {
    "L Montejano": "softrestaurant12",
}

# idformadepago (catálogo SR) -> categoría del pastel
CAT = {
    "EF": "Efectivo", "DLL": "Efectivo",
    "TC": "Tarjeta", "TD": "Tarjeta", "VISA": "Tarjeta", "MC": "Tarjeta",
    "AMEX": "Tarjeta", "CR": "Tarjeta",
    "RA": "Rappi", "DI": "DiDi", "UB": "Uber",
}
CATS = ["Efectivo", "Tarjeta", "Rappi", "DiDi", "Uber", "Otros"]


def _puerto(h):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(5)
    try:
        s.sendto(b"\x02", (h, 1434)); d, _ = s.recvfrom(65535)
        p = d[3:].decode("ascii", "replace").split(";")
        for i, x in enumerate(p):
            if x == "tcp": return int(p[i + 1])
    finally:
        s.close()
    return None


def _dia_carreta(host, fecha_iso, db=DB):
    pt = _puerto(host)
    if not pt:
        return None
    c = pymssql.connect(server=host, port=pt, user=U, password=P, database=db,
                        tds_version=TDS, timeout=25, login_timeout=12)
    cur = c.cursor()
    # Agrupar por la fecha de APERTURA DEL TURNO (no por ch.fecha calendario):
    # así cuadra EXACTO con la venta de la nube. La nube usa el corte de turno,
    # y las carretas que cierran pasada la medianoche (ej. Montejano) recorren
    # tickets de día si se agrupa por fecha calendario. Verificado 17-sep-2026:
    # Villas/Cine Curto/Montejano cuadran al peso con la nube usando t.apertura.
    cur.execute("""
        SELECT cp.idformadepago, SUM(cp.importe)
        FROM chequespagos cp
        JOIN cheques ch ON ch.folio = cp.folio
        JOIN turnos t ON t.idturno = ch.idturno
        WHERE CONVERT(date, t.apertura) = %s AND ch.cancelado = 0
        GROUP BY cp.idformadepago
    """, (fecha_iso,))
    res = {}
    for idfp, monto in cur.fetchall():
        res[(idfp or "").strip()] = float(monto or 0)
    c.close()
    return res


def _calcular(fecha_iso):
    """Consulta EN VIVO el SQL de cada carreta alcanzable para ese día."""
    agg = defaultdict(float)
    cubiertas, sin_sql, apagadas = [], [], []
    for carreta, host in SUCS_SQL.items():
        if not host:
            sin_sql.append(carreta)          # nunca conectada a Tailscale+SQL
            continue
        try:
            r = _dia_carreta(host, fecha_iso, DB_POR_CARRETA.get(carreta, DB))
        except Exception:
            r = None
        if r is None:
            apagadas.append(carreta)         # conectada, pero apagada al medir
            continue
        sub = 0.0
        for idfp, monto in r.items():
            agg[CAT.get(idfp, "Otros")] += monto
            sub += monto
        cubiertas.append((carreta, sub))
    total_sql = sum(m for _, m in cubiertas)
    return {
        "agg": {k: agg.get(k, 0.0) for k in CATS},
        "cubiertas": cubiertas,
        "sin_sql": sin_sql,
        "apagadas": apagadas,
        "faltantes": sin_sql + apagadas,     # unión (compatibilidad)
        "total_sql": total_sql,
    }


def snapshot(fecha_iso):
    """Calcula EN VIVO y guarda la foto de formas de pago del día en caché.
    Pensado para correr ~23:30, cuando las carretas siguen prendidas."""
    d = _calcular(fecha_iso)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _ruta_cache(fecha_iso).write_text(json.dumps(d, ensure_ascii=False, indent=1))
    return d


def formas_pago_dia(fecha_iso, prefer_cache=True):
    """Devuelve formas de pago del día. Si hay foto guardada (snapshot de las 23:30)
    la usa — así el reporte de medianoche no depende de que las compus sigan prendidas.
    Si no hay caché, consulta en vivo."""
    if prefer_cache:
        rc = _ruta_cache(fecha_iso)
        if rc.exists():
            try:
                return json.loads(rc.read_text())
            except Exception:
                pass
    return _calcular(fecha_iso)


if __name__ == "__main__":
    import sys
    from datetime import datetime, timedelta
    args = sys.argv[1:]
    modo_snapshot = "--snapshot" in args
    args = [a for a in args if not a.startswith("--")]

    if modo_snapshot:
        # Captura de HOY (el día que está por cerrar), corre ~23:30
        fecha = args[0] if args else datetime.now().strftime("%Y-%m-%d")
        d = snapshot(fecha)
        print(f"SNAPSHOT guardado: {_ruta_cache(fecha)}")
    else:
        fecha = args[0] if args else (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        d = formas_pago_dia(fecha)
    print(f"FECHA {fecha}")
    print("Cubiertas:", ", ".join(f"{n} (${m:,.0f})" for n, m in d["cubiertas"]) or "ninguna")
    print("Faltantes:", ", ".join(d["faltantes"]) or "ninguna")
    print("Total SQL: ${:,.2f}".format(d["total_sql"]))
    for k in CATS:
        v = d["agg"][k]
        pct = v / d["total_sql"] * 100 if d["total_sql"] else 0
        print(f"   {k:<10} ${v:,.2f}  {pct:4.1f}%")
