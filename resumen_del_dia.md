# Resumen del día — Tito Lector (24-nov-2026)

## Qué quedó
- Las 5 sucursales conectadas por Tailscale responden y su SQL responde (Montejano, Hacienda del Río, San Marcos, Villas del Rey, Cine Curto). Falta Montecarlo (sin equipo en el tailnet) y la compu de Félix (se conecta mañana).
- MCP de solo lectura instalado y probado (RichardHan/mssql_mcp_server, elegido sobre oguzhanpisgin/mssql-readonly-mcp porque este último no conecta con los SQL Server 2014 de las sucursales). 5 servidores registrados, uno por sucursal, usando el login `tito` (db_datareader) que ya existía — no se creó ni se tocó ninguna credencial.
- Mapa de la base de datos documentado (menú/precios, inventario/recetas, ventas/cortes, configuración).
- Los 4 lectores + verificador corrieron y encontraron cosas reales (ver abajo).
- Comparación completa entre las 5 sucursales guardada en `comparacion_sucursales.json`.
- Registro de actividad con horas armado.
- Página de avance construida y corriendo localmente (con clave) — **pendiente exponerla al público** (ver "Qué falló").

## Hallazgos principales
1. **Montejano, Hacienda del Río, San Marcos y Villas del Rey están 100% alineadas** en menú y precios entre sí. Cine Curto es la única realmente distinta — y es a propósito (menú de cine).
2. **Precios en $0 de combos de delivery en Cine Curto** — probablemente intencional (no vende por apps ahí) pero vale confirmarlo.
3. **El almacén con ID '10' significa "TRASPASO A OTRA SUCURSAL" en 4 sucursales pero "MERMAS" en Cine Curto** — mismo ID, significado distinto. Candidato real para homologar.
4. **Usuarios del sistema muy desparejos** entre sucursales (de 4 a 8 usuarios, nombres inconsistentes) y un usuario "MONTECARLO" raro dentro de la base de Montejano — revisar.
5. **Verificador: 2 de 5 sucursales NO cuadran** entre el reporte de ventas que se manda cada noche (fuente: portal en la nube) y lo que dice la base SQL local para el mismo día (Montejano y San Marcos). Esto es independiente de la homologación de catálogo — es sobre la confiabilidad de los reportes de ventas diarios.

## Qué falló / quedó a medias
- **Página de avance:** está construida y corriendo (con clave, usuario `felix` / clave `TitiLector2026`), pero el permiso para exponerla al público por Tailscale Funnel y para probarla con `curl` me lo bloqueó el clasificador de seguridad de Claude Code (acciones de red/exposición pública requieren tu autorización directa). Necesito que tú corras el comando o me des el ok explícito otra vez.
- **claude-office:** antes de instalarlo encontré que es un stack pesado (Next.js + FastAPI + WebSocket, dos servidores corriendo todo el tiempo) para una compu que es la columna de la operación (crons, bot de WhatsApp, tablero de inventario). Es solo un "nice to have" visual — lo dejé pendiente de tu ok antes de instalar algo que va a quedar corriendo permanentemente en la Z2.

## Qué falta para mañana
1. Tu ok para exponer la página de avance por Funnel (o la corres tú mismo).
2. Tu decisión sobre claude-office: ¿instalarlo de verdad, o algo más ligero que logre lo mismo (vista por piso) sin dos servidores nuevos corriendo siempre?
3. Conectar Montecarlo y la compu de Félix.
4. Comparar cada sucursal contra la base de Félix (la referencia real) y armar el análisis de brechas con prioridad.
5. Resolver las 2 verificaciones de ventas que no cuadraron (Montejano, San Marcos) — no es homologación de catálogo, es confiabilidad de reportes.
