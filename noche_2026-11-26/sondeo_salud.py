#!/usr/bin/env python3
"""SOLO LECTURA: que datos de salud puede ver el login tito en cada base."""
import datetime, time
from lib_lectura import conn, q, SUCS, REF
CONS = {
 "reloj": "SELECT GETDATE() ahora",
 "tamano_mb": "SELECT CAST(SUM(CAST(size AS bigint))*8/1024.0 AS decimal(10,1)) mb FROM sys.database_files WHERE type=0",
 "ultimo_ticket": "SELECT MAX(fecha) t FROM cheques",
 "ultimo_respaldo": "SELECT MAX(backup_finish_date) b FROM msdb.dbo.backupset WHERE database_name=DB_NAME()",
 "edicion": "SELECT CAST(SERVERPROPERTY('Edition') AS varchar(60)) e",
 "view_server_state": "SELECT HAS_PERMS_BY_NAME(NULL,NULL,'VIEW SERVER STATE') v",
}
for n, cf in [REF] + SUCS:
    out = {}
    try:
        t0 = time.time(); cn = conn(cf); cur = cn.cursor(); out["ms_conectar"] = int((time.time() - t0) * 1000)
        for k, sql in CONS.items():
            try: out[k] = list(q(cur, sql)[0].values())[0]
            except Exception as e: out[k] = f"SIN PERMISO/ERR {str(e)[:60]}"
        if isinstance(out.get("reloj"), datetime.datetime):
            out["desfase_seg"] = int((out["reloj"] - datetime.datetime.now()).total_seconds())
        cn.close()
    except Exception as e: out["error"] = str(e)[:100]
    print(n, {k: str(v) for k, v in out.items()})
