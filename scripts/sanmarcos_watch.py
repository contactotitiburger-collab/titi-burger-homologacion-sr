#!/usr/bin/env python3
"""Vigilante de San Marcos — Titi Burger.

San Marcos (100.101.205.89) suele estar apagada. Este cron la checa cada rato.
Cuando PRENDE (responde el SQL):
  1) investiga cómo registra merma (almacén de mermas dedicado o traspaso con nota),
  2) la agrega al reporte visual de merma por carreta (merma_suc_extra.json),
  3) regenera el reporte,
  4) avisa a Rafael por correo (WhatsApp está apagado),
  5) se borra a sí mismo del crontab (marcador SANMARCOS-MERMA-WATCH).

Si sigue apagada, sale calladito y el cron lo reintenta luego.
"""
import pymssql, socket, json, subprocess, sys
from pathlib import Path

HOST = "100.101.205.89"
NOMBRE = "San Marcos"
U, P, DB, TDS = "tito", os.environ.get("SR_SQL_PASS",""), "softrestaurant11", "7.0"
BASE = Path.home() / ".openclaw/workspace/titi-inventario-demo"
EXTRA = BASE / "merma_suc_extra.json"
SCRIPTS = Path.home() / ".openclaw/scripts"
MARCADOR = "SANMARCOS-MERMA-WATCH"
EXC = ("ERROR", "AJUSTE", "TRANSFER", "TRANFER", "TRAPAS", "TRASPAS", "FAC")

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

def conectar():
    pt = puerto(HOST)
    if not pt: return None
    return pymssql.connect(server=HOST, port=pt, user=U, password=P, database=DB,
                           tds_version=TDS, timeout=15, login_timeout=10)

def investigar(c):
    """Devuelve (alm, dedicado, resumen) de cómo San Marcos registra merma."""
    cur = c.cursor()
    # 1) ¿almacén con 'MERMA' en el nombre? -> dedicado
    cur.execute("SELECT idalmacen, nombre FROM almacen WHERE UPPER(nombre) LIKE '%MERMA%'")
    row = cur.fetchone()
    if row:
        return (str(row[0]).strip(), True, f"almacén dedicado '{str(row[0]).strip()}' ({row[1].strip()})")
    # 2) ¿traspasos de carreta '2' a '1' con notas de merma? -> compartido (no dedicado)
    cur.execute("""SELECT ISNULL(LTRIM(RTRIM(nota)),''), COUNT(*) FROM traspasosalmacen
                   WHERE almacenorigen='2' AND almacendestino='1' GROUP BY ISNULL(LTRIM(RTRIM(nota)),'')""")
    notas = cur.fetchall()
    con_merma = sum(n for nota, n in notas if nota and not any(x in nota.upper() for x in EXC))
    if con_merma > 0:
        return ("1", False, f"traspasos a cocina '1' con nota de merma ({con_merma} movs)")
    return (None, None, "no se encontró registro de merma (no tiene cajón ni notas de merma)")

def quitar_del_cron():
    try:
        out = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if out.returncode != 0: return
        lineas = [l for l in out.stdout.splitlines() if MARCADOR not in l]
        subprocess.run(["crontab", "-"], input="\n".join(lineas) + "\n", text=True)
    except Exception as e:
        print("no pude quitar el cron:", e)

def avisar(msg):
    try:
        subprocess.run([sys.executable, str(SCRIPTS / "tito_recordatorio_correo.py"),
                        "--asunto", "San Marcos ya prendió 🍔 (merma)", "--mensaje", msg], timeout=60)
    except Exception as e:
        print("no pude enviar correo:", e)

def main():
    try:
        c = conectar()
    except Exception as e:
        print("San Marcos sigue apagada / sin SQL:", e); return
    if c is None:
        print("San Marcos sigue apagada (no responde el SQL)."); return
    # ¡Prendió!
    alm, dedicado, resumen = investigar(c)
    c.close()
    if alm is None:
        avisar(f"San Marcos ya está prendida, pero {resumen}. No la agregué al reporte de merma; "
               f"hay que configurarle el cajón de mermas en su Soft Restaurant. Cuando lo tenga, se suma sola.")
        quitar_del_cron()
        print("San Marcos prendió pero no registra merma. Avisé y quité el cron.")
        return
    # agregar a la config extra del reporte por carreta
    extra = []
    if EXTRA.exists():
        try: extra = json.loads(EXTRA.read_text())
        except Exception: extra = []
    if NOMBRE not in [e["nombre"] for e in extra]:
        extra.append({"nombre": NOMBRE, "host": HOST, "alm": alm, "dedicado": dedicado})
        EXTRA.write_text(json.dumps(extra, ensure_ascii=False, indent=1))
    # regenerar reporte visual
    subprocess.run([sys.executable, str(SCRIPTS / "merma_carretas.py")])
    avisar(f"San Marcos ya prendió y la agregué al reporte de merma por carreta ({resumen}). "
           f"Ya sale en https://tito-z2.tail2fb4b3.ts.net/merma_carretas.html")
    quitar_del_cron()
    print(f"San Marcos agregada ({resumen}). Avisé y quité el cron.")

if __name__ == "__main__":
    main()
