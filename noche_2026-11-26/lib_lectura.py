"""Conexion SOLO LECTURA a las sucursales + Felix. Reusa las creds existentes (login tito = db_datareader)."""
import json, socket, pymssql
from pathlib import Path
CRED=Path("/home/tito/.openclaw/credentials/sr_sql")
REF=("Felix","felix")
SUCS=[("Montejano","montejano"),("Hacienda del Rio","hacienda_del_rio"),("Montecarlo","montecarlo"),
      ("Villas del Rey","villas_del_rey"),("San Marcos","san_marcos"),("Cine Curto","cine_curto")]
def puerto(h):
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.settimeout(6)
    try:
        s.sendto(b"\x02",(h,1434));d,_=s.recvfrom(65535)
        p=d[3:].decode("ascii","replace").split(";")
        for i,x in enumerate(p):
            if x=="tcp":return int(p[i+1])
    finally:s.close()
def conn(cf):
    c=json.loads((CRED/f"{cf}.json").read_text()); pt=puerto(c["server"]); err=None
    for t in dict.fromkeys([c.get("tds_version",c.get("tds","7.0")),"7.4","7.0"]):
        try: return pymssql.connect(server=c["server"],port=pt,user=c["user"],password=c["password"],database=c["database"],tds_version=t,timeout=60,login_timeout=12)
        except Exception as e: err=e
    raise err
def q(cur,sql,params=None):
    s=sql.lstrip().upper()
    assert s.startswith("SELECT") or s.startswith("WITH"), "lib_lectura solo permite SELECT"
    cur.execute(sql,params); cols=[d[0] for d in cur.description]
    return [dict(zip(cols,r)) for r in cur.fetchall()]
