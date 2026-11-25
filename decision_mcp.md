# Paso 2 — MCP de solo lectura: decisión

## Candidatos evaluados
1. **oguzhanpisgin/mssql-readonly-mcp** (C#/.NET 10) — gate SELECT-only en código + audit log con hash-chain. Muy buen diseño, pero usa el cliente SqlClient moderno de .NET: **no logra conectar** a los SQL Server 2014 Express de las sucursales (error de pre-login / protocolo). Se probó con puerto dinámico resuelto manualmente y con varias combinaciones de Encrypt — siempre falla. Descartado por incompatibilidad real con nuestra infraestructura.
2. **RichardHan/mssql_mcp_server** (Python + pymssql) — **elegido**. Usa pymssql, la misma librería que ya usan en producción `merma_todas.py`, `sr_formaspago_dia_multi.py`, etc. contra estos mismos SQL Server 2014. Conecta sin problema. Tiene su propio gate de solo-lectura (`is_select_query`, vía `sqlglot`): verificado en vivo que bloquea DELETE/UPDATE/DROP/EXEC/sentencias múltiples y solo deja pasar SELECT/UNION/EXCEPT/INTERSECT.

Nota: instalado desde el repo de GitHub (no el paquete de PyPI), porque la versión de PyPI usa `pyodbc` (requiere drivers ODBC que no están instalados) y además está desactualizada con `mcp>=2.0.0` incompatible con su propio código.

## Setup
- Entorno aislado: `/home/tito/.openclaw/tools/mssql-mcp-venv` (venv dedicado, no toca el Python del sistema).
- Wrapper `/home/tito/.openclaw/tools/mcp-wrappers/lector_wrapper.sh <sucursal>`: resuelve el puerto dinámico de SQL Server (SQL Browser UDP 1434) en cada arranque — así no se rompe si el puerto cambia tras un reinicio del servidor.
- 5 servidores MCP registrados en Claude Code: `lector-montejano`, `lector-hacienda`, `lector-sanmarcos`, `lector-villas`, `lector-cinecurto` — los 5 conectados y en modo `read-only` confirmado en log.
- Usa el login `tito` (db_datareader) que YA EXISTÍA en cada sucursal — no se creó nada nuevo.
