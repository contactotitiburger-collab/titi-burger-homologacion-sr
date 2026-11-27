#!/usr/bin/env python3
"""Salud de las cajas (SOLO LECTURA, login tito). NO manda mensajes: solo escribe un reporte.
Revisa por sucursal: ultimo respaldo registrado, ultimo ticket, reloj de la caja vs Z2, tamano de la base
(SQL Express topa en 10 GB) y si el catalogo cambio desde la ultima corrida (huella por tabla).
Salida: salud_cajas/ultimo.json, salud_cajas/ultimo.md y salud_cajas/historial.jsonl
Uso: python3 salud_cajas.py"""
import json, datetime, time, hashlib, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "noche_2026-11-26"))
from lib_lectura import conn, q, SUCS, REF

OUT = Path(__file__).parent / "salud_cajas"; OUT.mkdir(exist_ok=True)
LIMITE_EXPRESS_MB = 10240
# Tablas de catalogo vigiladas (las que Tito Editor podria tocar + las que definen el menu)
CATALOGO = {"productos": "idproducto", "productosdetalle": "idproducto", "costos": "idproducto", "modificadores": "idproducto",
            "insumos": "idinsumo", "insumosdetalle": "idinsumo", "insumospresentaciones": "idinsumospresentaciones",
            "insumospresentacionesdetalle": "idinsumospresentaciones", "formasdepago": "idformadepago", "almacen": "idalmacen"}

def huella_tabla(cur, tabla, orden):
    filas = q(cur, f"SELECT * FROM [{tabla}] ORDER BY [{orden}]")
    limpio = [{k: (str(v).strip() if v is not None and not isinstance(v, (bytes, bytearray)) else None)
               for k, v in r.items() if k.lower() != "workspaceid"} for r in filas]
    return {"filas": len(filas), "huella": hashlib.sha256(json.dumps(limpio, sort_keys=True).encode()).hexdigest()[:16]}

CRED = Path("/home/tito/.openclaw/credentials/sr_sql")

def red_tailscale():
    """Estado de cada nodo en la red (Online + cuando vence su llave). Distingue 'se cayo la red' de 'se cayo SQL'."""
    import subprocess
    try:
        d = json.loads(subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=15).stdout)
        return {p["TailscaleIPs"][0]: {"nodo": p.get("HostName"), "en_linea": p.get("Online"), "llave_vence": p.get("KeyExpiry")}
                for p in d.get("Peer", {}).values() if p.get("TailscaleIPs")}
    except Exception as e:
        return {"_error": str(e)[:100]}

def revisar(nombre, cf, red=None):
    r = {"sucursal": nombre, "avisos": []}
    ip = json.loads((CRED / f"{cf}.json").read_text())["server"]
    n = (red or {}).get(ip)
    if n:
        r["red"] = n
        if not n["en_linea"]: r["avisos"].append(("ROJO", "La compu no esta conectada a la red (Tailscale)"))
        if n.get("llave_vence"):
            dias = (datetime.datetime.fromisoformat(n["llave_vence"].replace("Z", "+00:00")).replace(tzinfo=None) - datetime.datetime.utcnow()).days
            r["red"]["dias_para_vencer"] = dias
            if dias < 30: r["avisos"].append(("ROJO" if dias < 7 else "AMARILLO", f"La llave de red vence en {dias} dias: desactivar el vencimiento en el panel de Tailscale"))
    t0 = time.time()
    cn = conn(cf); cur = cn.cursor(); r["ms_conexion"] = int((time.time() - t0) * 1000)
    v = q(cur, "SELECT CAST(SERVERPROPERTY('ProductVersion') AS varchar(30)) v, (SELECT state_desc FROM sys.databases WHERE name=DB_NAME()) estado")[0]
    r["version_sql"], r["estado_base"] = v["v"], v["estado"]
    if r["estado_base"] != "ONLINE": r["avisos"].append(("ROJO", f"La base no esta en linea ({r['estado_base']})"))
    ahora_caja = q(cur, "SELECT GETDATE() a")[0]["a"]
    r["desfase_reloj_seg"] = int((ahora_caja - datetime.datetime.now()).total_seconds())
    r["tamano_mb"] = float(q(cur, "SELECT CAST(SUM(CAST(size AS bigint))*8/1024.0 AS decimal(10,1)) mb FROM sys.database_files WHERE type=0")[0]["mb"])
    t = q(cur, "SELECT MAX(fecha) t FROM cheques")[0]["t"]; r["ultimo_ticket"] = t.isoformat(timespec="minutes") if t else None
    try:
        b = q(cur, "SELECT MAX(backup_finish_date) b FROM msdb.dbo.backupset WHERE database_name=DB_NAME()")[0]["b"]
        r["ultimo_respaldo"] = b.isoformat(timespec="minutes") if b else None
    except Exception: r["ultimo_respaldo"] = "sin permiso"
    r["catalogo"] = {t: huella_tabla(cur, t, o) for t, o in CATALOGO.items()}
    cn.close()
    # --- avisos (en palabras simples)
    if r["ultimo_respaldo"] is None: r["avisos"].append(("ROJO", "No hay ningun respaldo registrado de esta base"))
    elif r["ultimo_respaldo"] != "sin permiso":
        horas = (datetime.datetime.now() - datetime.datetime.fromisoformat(r["ultimo_respaldo"])).total_seconds() / 3600
        if horas > 36: r["avisos"].append(("ROJO", f"Ultimo respaldo hace {horas/24:.0f} dias"))
    if abs(r["desfase_reloj_seg"]) > 60: r["avisos"].append(("AMARILLO", f"Reloj de la caja desfasado {r['desfase_reloj_seg']} seg vs la oficina"))
    if r["tamano_mb"] > LIMITE_EXPRESS_MB * 0.8: r["avisos"].append(("ROJO", f"Base en {r['tamano_mb']:.0f} MB: cerca del tope de 10 GB de SQL Express"))
    return r

def main():
    previo = {}
    f_ult = OUT / "ultimo.json"
    if f_ult.exists(): previo = {x["sucursal"]: x for x in json.loads(f_ult.read_text()).get("sucursales", []) if "catalogo" in x}
    res = []; red = red_tailscale()
    for nombre, cf in SUCS + [REF]:
        try: r = revisar(nombre, cf, red)
        except Exception as e: r = {"sucursal": nombre, "error": str(e)[:150], "avisos": [("ROJO", "No se pudo leer la base")]}
        p = previo.get(nombre)
        if p and "catalogo" in r:
            cambios = [t for t, h in r["catalogo"].items() if p["catalogo"].get(t, {}).get("huella") != h["huella"]]
            r["catalogo_cambio_desde_ultima"] = cambios
            if cambios: r["avisos"].append(("AMARILLO", f"Cambio el catalogo desde la ultima revision: {', '.join(cambios)}"))
        res.append(r)
    doc = {"generado": datetime.datetime.now().isoformat(timespec="minutes"), "sucursales": res}
    f_ult.write_text(json.dumps(doc, ensure_ascii=False, indent=1, default=str))
    with (OUT / "historial.jsonl").open("a") as h:
        h.write(json.dumps({"generado": doc["generado"], "resumen": [{k: r.get(k) for k in ("sucursal", "ultimo_respaldo", "ultimo_ticket", "desfase_reloj_seg", "tamano_mb", "avisos")} for r in res]}, ensure_ascii=False, default=str) + "\n")
    lineas = [f"# Salud de las cajas — {doc['generado']}", "", "| Sucursal | Red | Llave de red | Último respaldo | Último ticket | Reloj | Tamaño | Avisos |", "|---|---|---|---|---|---|---|---|"]
    for r in res:
        av = "; ".join(f"{'🔴' if c == 'ROJO' else '🟠'} {m}" for c, m in r["avisos"]) or "✅"
        rd = r.get("red") or {}
        lineas.append(f"| {r['sucursal']} | {'en línea' if rd.get('en_linea') else '—'} | {str(rd.get('dias_para_vencer', '—')) + ' días'} | {r.get('ultimo_respaldo') or '—'} | {r.get('ultimo_ticket') or '—'} | {r.get('desfase_reloj_seg', '—')} s | {r.get('tamano_mb', '—')} MB | {av} |")
    (OUT / "ultimo.md").write_text("\n".join(lineas) + "\n")
    print("\n".join(lineas))

if __name__ == "__main__": main()
