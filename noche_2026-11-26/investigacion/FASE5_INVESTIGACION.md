# Fase 5 — Investigación a fondo (noche 26→27 nov 2026)

Fuentes: 3 investigaciones en paralelo (GitHub, documentación oficial, artículos de investigación, foros y blogs de bases de datos; ~116 consultas en total) + Moltbook en solo lectura. No se instaló nada, no se abrieron cuentas y no se publicó nada.

## Lo que más importa (5 conclusiones)

1. **Soft Restaurant 12 trae su propia importación de productos e insumos por Excel** (*Herramientas para administradores → Importar productos / Importar insumos*). También trae *Exportar/importar datos → Catálogos* en ZIP, pero ese sobrescribe todo y no se puede revertir: **no usarlo a ciegas**. Lo mejor: que Tito Editor genere el Excel y Félix lo importe. Recetas y paquetes no se ven en la importación por Excel (sin verificar). [Manual SR12](https://softrestaurant.com/docs-manual-interactivo-soft-restaurant-12)
2. **Hay disparadores de Soft Restaurant en productos, precios y recetas** (los encontré esta noche en las 7 bases, en solo lectura). Cambiar esas tablas directo en SQL activaría lógica de SR que no conocemos, probablemente la sincronización con la nube. **Regla nueva en el Editor: esas tablas solo se cambian desde SR.**
3. **National Soft anunció en marzo 2026 una "administración web del menú" para varias sucursales a la vez**, con liberación gradual de 18 meses. Si ya está disponible para nuestras versiones, resolvería precios y productos sin tocar SQL. **Hay que preguntarle al distribuidor.** [InfoChannel 9-mar-2026](https://infochannel.info/soft_restaurant_actualiza_soluciones_digitales-_impulsar_restaurantes/)
4. **El que revisa no debe ser otra IA leyendo lo que concluyó la primera.** Los modelos fallan en lo mismo: cuando dos se equivocan, coinciden en la misma respuesta mala 60% de las veces ([Kim et al., ICML 2025](https://arxiv.org/abs/2506.07962)). Nuestro Verificador ya revisa con SQL y reglas fijas, en código; hay que mantenerlo así. Las firmas de Rafael y Félix son el único control realmente independiente: **que no se vuelvan firmas en automático** (lotes chicos, conteos claros).
5. **El chequeo de salud de cada 20 min solo pregunta a SQL Browser.** Eso no prueba que la base esté viva. Además, si la Z2 se apaga, nadie avisa (pasó del 14 al 16 de sep). Falta una "alarma de silencio" fuera de la Z2.

## Lo que ya tenemos bien (según la literatura)
Usuario de solo lectura, lista de columnas permitidas, solo UPDATE, todo o nada, lote para deshacer, aprobación atada a la huella del lote, ventana de horario, interruptor de emergencia y escritura directa apagada. Coincide con [OWASP LLM06:2025](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) y con lo que se aprendió del caso Replit (jul-2025: un agente borró la base de producción durante un congelamiento de código que solo existía en sus instrucciones, no en código ni en permisos. [Fortune](https://fortune.com/2025/07/23/ai-coding-tool-replit-wiped-database-called-it-a-catastrophic-failure/)).

## Mejoras aplicadas esta noche (Fase 6)
| Mejora | Fuente |
|---|---|
| Revisor de SQL por estructura (sqlglot): 1 sola sentencia, tabla/columna permitidas, WHERE = llave exacta, sin OR | [sql-guardrail](https://pypi.org/project/sql-guardrail/), caso [Datadog](https://securitylabs.datadoghq.com/articles/mcp-vulnerability-case-study-SQL-injection-in-the-postgresql-mcp-server/) |
| Huella de la fila completa ("sellar" antes de firmar) | Revisión optimista (literatura) |
| Ancla de la bitácora para guardarla fuera de la Z2 | [Crosby y Wallach, USENIX 2009](https://www.usenix.org/conference/usenixsecurity09/technical-sessions/presentation/efficient-data-structures-tamper-evident) |
| 40 rondas de pruebas al azar (aplicar → deshacer = idéntico; nunca fuera de la lista; si algo se movió, se salta) | [Hypothesis, pruebas con estado](https://hypothesis.readthedocs.io/en/latest/stateful.html) |
| Productos, precios y recetas solo desde SR (por los disparadores) | Revisión propia en solo lectura |
| Reporte de salud de cajas: respaldo, último ticket, reloj, tamaño, cambios de catálogo, red y vencimiento de llave | [Brent Ozar](https://www.brentozar.com/?p=16468), [Tailscale key expiry](https://tailscale.com/kb/1028/key-expiry), [ipnstate](https://pkg.go.dev/tailscale.com@v1.96.1/ipn/ipnstate) |

## Propuestas que NO hice (necesitan tu OK porque instalan algo, tocan las cajas o mandan mensajes)
1. **Respaldo diario en cada caja**: script de Ola Hallengren + Programador de tareas de Windows + `sqlcmd`, con `@CheckSum='Y'` y `@Verify='Y'`. **Sin compresión**: Express no la trae. Además, que la Z2 jale los respaldos por Tailscale (14 diarios + 8 semanales). [Ola Hallengren FAQ](https://ola.hallengren.com/frequently-asked-questions.html). *Toca las 6 cajas.*
2. **Prueba de restauración semanal en la Z2** con SQL Server 2022 Express en Docker: una versión nueva sí abre respaldos de 2014. Esto sustituye a la copia de prueba en SQLite, que da falsa confianza. [MS Learn](https://learn.microsoft.com/en-us/sql/linux/tutorial-restore-backup-in-sql-server-container). *Instala Docker y unos 2 GB; la Z2 tiene 7 GB de RAM.*
3. **Chequeo de salud con una consulta real** (un SELECT con tiempo límite de 5 s) en vez de solo SQL Browser. *Cambia los avisos que te llegan por WhatsApp.*
4. **Alarma de silencio externa** (tipo healthchecks.io): la Z2 manda una señal cada 20 min y, si deja de llegar, te avisa. *Cuenta nueva en un servicio externo.*
5. **Etiquetas de Tailscale para las cajas**: al etiquetarlas, su llave deja de vencer, y con reglas de acceso solo la Z2 llega al SQL. *Panel de Tailscale.*
6. **Consultar al distribuidor** si tenemos o podemos tener el módulo central, SR Enterprise o la administración web del menú.

## Lo que hay que evitar
- Abrir escritura con SQL libre, aunque sea "con candados" de un MCP: el caso Datadog demuestra que esos filtros se saltan. Si algún día se escribe directo, debe ser un usuario SQL con UPDATE **solo en las columnas permitidas**.
- Importar el ZIP de catálogos completo: sobrescribe todo, sin regreso.
- Disparadores, Change Tracking o cualquier cambio de estructura en la base de SR sin el visto bueno del proveedor.
- Paneles de varias IAs votando como si fueran revisores independientes.
- Pagar Redgate o dbForge (US$220–315 al año) o depender de data-diff (archivado en 2024) o reladiff (no soporta SQL Server).

## Datos de contexto
- **SQL Server 2014 ya no tiene soporte de Microsoft** desde el 9-jul-2024: ya no recibe parches de seguridad. Lo usan 5 de las 6 cajas. [MS](https://learn.microsoft.com/en-us/lifecycle/faq/sql-server-extended-security-updates)
- Moltbook: casi todo es ruido. Una sola idea útil: nombrar cada respaldo según el cambio que protege (ya lo hacemos por lote).
