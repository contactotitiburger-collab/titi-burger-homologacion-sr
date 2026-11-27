#!/usr/bin/env python3
# SOLO LECTURA. Explora columnas de tablas clave + confirma permisos del login tito.
import json, socket, pymssql, sys
from pathlib import Path
CRED=Path("/home/tito/.openclaw/credentials/sr_sql")
def puerto(h):
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.settimeout(6)
    try:
        s.sendto(b"\x02",(h,1434));d,_=s.recvfrom(65535)
        p=d[3:].decode("ascii","replace").split(";")
        for i,x in enumerate(p):
            if x=="tcp":return int(p[i+1])
    finally:s.close()
def conn(cf):
    c=json.loads((CRED/f"{cf}.json").read_text()); pt=puerto(c["server"])
    for t in [c.get("tds_version",c.get("tds","7.0")),"7.4","7.0"]:
        try: return pymssql.connect(server=c["server"],port=pt,user=c["user"],password=c["password"],database=c["database"],tds_version=t,timeout=40,login_timeout=12)
        except Exception as e: err=e
    raise err
TABLAS=sys.argv[2].split(",")
cf=sys.argv[1]; cn=conn(cf); cur=cn.cursor()
cur.execute("SELECT @@VERSION, IS_ROLEMEMBER('db_datareader'), IS_ROLEMEMBER('db_datawriter'), IS_ROLEMEMBER('db_owner'), IS_SRVROLEMEMBER('sysadmin'), HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','INSERT'), HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','UPDATE')")
r=cur.fetchone(); print(cf, r[0].split("\n")[0], "reader",r[1],"writer",r[2],"owner",r[3],"sysadmin",r[4],"INS",r[5],"UPD",r[6])
for t in TABLAS:
    cur.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME=%s ORDER BY ORDINAL_POSITION",(t,))
    cols=[x[0] for x in cur.fetchall()]
    try:
        cur.execute(f"SELECT COUNT(*) FROM [{t}]"); n=cur.fetchone()[0]
    except Exception as e: n=f"ERR {e}"
    print(f"  {t} ({n} filas): {', '.join(cols[:45])}{' ...+'+str(len(cols)-45) if len(cols)>45 else ''}")
cn.close()
