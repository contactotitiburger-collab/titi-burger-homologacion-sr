#!/usr/bin/env python3
"""Paso 1 — Descubrimiento. Solo lectura: ping, puerto SQL Browser, SELECT trivial."""
import json, socket, subprocess, sys
import pymssql
from pathlib import Path

CRED_DIR = Path("/home/tito/.openclaw/credentials/sr_sql")
SUCS = [
    ("Montejano",        "tbfovi-servidor", "100.68.233.59", "montejano"),
    ("Hacienda del Río",  "tbhrio-servidor", "100.80.102.110", "hacienda_del_rio"),
    ("San Marcos",        "tbsm-servidor",   "100.101.205.89", "san_marcos"),
    ("Villas del Rey",    "tbvir-servidor",  "100.66.22.9",    "villas_del_rey"),
    ("Cine Curto",        "tbcurt-servidor", "100.94.218.56",  "cine_curto"),
]

def ping(host):
    r = subprocess.run(["ping", "-c1", "-W2", host], capture_output=True)
    return r.returncode == 0

def puerto_dinamico(host):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(5)
    try:
        s.sendto(b"\x02", (host, 1434)); d, _ = s.recvfrom(65535)
        p = d[3:].decode("ascii", "replace").split(";")
        for i, x in enumerate(p):
            if x == "tcp":
                return int(p[i + 1])
    except Exception:
        return None
    finally:
        s.close()
    return None

filas = []
for nombre, hostname, ip, credfile in SUCS:
    en_linea = ping(ip)
    pt = puerto_dinamico(ip) if en_linea else None
    sql_ok, db_name, nota = "NO", "-", ""
    if pt:
        try:
            cred = json.loads((CRED_DIR / f"{credfile}.json").read_text())
            c = pymssql.connect(server=ip, port=pt, user=cred["user"], password=cred["password"],
                                 database=cred["database"], tds_version=cred.get("tds_version", "7.0"),
                                 timeout=15, login_timeout=10)
            cur = c.cursor()
            cur.execute("SELECT DB_NAME()")
            db_name = cur.fetchone()[0]
            sql_ok = "SI"
            c.close()
        except Exception as e:
            nota = f"error SQL: {e}"[:120]
    elif en_linea:
        nota = "no respondió SQL Browser (puerto dinámico)"
    filas.append((nombre, hostname, "SI" if en_linea else "NO", sql_ok, db_name, nota))

print(f"{'Sucursal':<18}{'Equipo':<18}{'En línea':<10}{'SQL responde':<14}{'Base':<20}Notas")
for f in filas:
    print(f"{f[0]:<18}{f[1]:<18}{f[2]:<10}{f[3]:<14}{f[4]:<20}{f[5]}")
