"""Helper compartido: conexion de solo lectura a cada sucursal (reusa creds ya existentes)."""
import json, socket, pymssql
from pathlib import Path

CRED_DIR = Path("/home/tito/.openclaw/credentials/sr_sql")
SUCS = [
    ("Montejano",       "montejano"),
    ("Hacienda del Río", "hacienda_del_rio"),
    ("San Marcos",       "san_marcos"),
    ("Villas del Rey",   "villas_del_rey"),
    ("Cine Curto",       "cine_curto"),
]

def _puerto(host):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(5)
    try:
        s.sendto(b"\x02", (host, 1434)); d, _ = s.recvfrom(65535)
        p = d[3:].decode("ascii", "replace").split(";")
        for i, x in enumerate(p):
            if x == "tcp":
                return int(p[i + 1])
    finally:
        s.close()
    return None

def conectar(credfile):
    cred = json.loads((CRED_DIR / f"{credfile}.json").read_text())
    pt = _puerto(cred["server"])
    return pymssql.connect(server=cred["server"], port=pt, user=cred["user"],
                            password=cred["password"], database=cred["database"],
                            tds_version=cred.get("tds_version", "7.0"),
                            timeout=25, login_timeout=12, as_dict=True)

def query(credfile, sql, params=None):
    c = conectar(credfile)
    try:
        cur = c.cursor()
        cur.execute(sql, params or ())
        return cur.fetchall()
    finally:
        c.close()
