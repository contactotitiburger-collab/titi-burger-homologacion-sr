# Investigación 27-nov-2026 — Soft Restaurant al máximo + copiar la base + SQL 2014→2019
(Agente de investigación; fuentes abiertas al final. "sin verificar" = no hay documento oficial.)

## Versiones reales (leídas de las cajas, 27-nov)
| Base | Soft Restaurant | SQL |
|---|---|---|
| Félix | SR12 / 2019 | 2019 Express (15.0) |
| Montecarlo | SR12 | 2019 Express (15.0) |
| Montejano (FOVISSTE) | SR12 | **2014 SP1** Express (12.0.4100) |
| Hacienda, Villas, San Marcos, Cine Curto | **SR11** | **2014 SP1** Express (12.0.4100) |

## Hallazgos clave
1. **Un respaldo de SQL 2019 no se puede restaurar en 2014** (Microsoft, RESTORE). Al revés sí.
2. **Subir SQL 2014 en la misma máquina** solo desde SP2; las cajas están en SP1. Mejor camino: **subir las 4 sucursales SR11 a SR12 con el distribuidor** (el instalador de SR12 trae SQL 2019). Montejano ya es SR12 pero su SQL es 2014 → también hay que subir su SQL.
3. **SR11 → SR12**: con licencia en renta la licencia nueva no cuesta; instalación/servicios se cobran (referencia distribuidor syca: servidor $980, estación $680 + IVA). "Si tienes SR11 tienes derecho a actualización".
4. **La copia oficial de SR**: Mantenimiento → Base de datos → "Recuperar base de datos" acepta respaldos y tiene **"Seleccionar catálogos a recuperar"** (productos, grupos, insumos, recetas). Es la forma de hacer el copy paste del catálogo de Félix sin perder ventas, folios ni configuración de cada caja. "Recuperar sustituye la información actual… irreversible" → respaldo antes, siempre.
5. **Delivery integrado (Uber/Rappi/DiDi)**: archivo `nspfmsync.db`, servicios IntegratorWorker/NSPlatformWorker; si la base o catálogos son nuevos hay que llamar a **Soporte de Integraciones** de National Soft antes.
6. **Licencia**: una por sucursal, ligada al servidor; 1 cambio de servidor al año.
7. **Importar por Excel** (productos, insumos, proveedores, clientes): solo SR12. Recetas no.
8. **Manejo central de menú** (SR Analytics / Enterprise / "administración web del menú" anunciada mar-2026): no disponible en nuestro panel hoy (revisado 27-nov). Preguntar al distribuidor.
9. SQL Express 2019: 10 GB por base (Montejano hoy ~542 MB → sobrado).

## Menos clics (manual SR12; en SR11 sin verificar)
- **Combo = producto compuesto** (no paquete), grupos de modificadores en orden: Bebida (1 incluida, **forzar captura**) → Papas (1 incluida, forzar; agrandar con precio) → Extras (opcional). ≈ 4–6 clics: combo, bebida, papas, (extra), cobrar.
- Hamburguesa sola: compuesto con grupo "Extras" con precio, sin forzar.
- **Paquete** solo si el contenido es fijo (ej. promo 2 hamburguesas).
- Combos en **favoritos** + "Cargar productos favoritos predeterminadamente".
- Apagar "Solicitar cantidad de producto en cada captura"; "Usar pantalla pequeña con 1 modificador incluido".
- Armar un combo bien y usar "Replicar producto compuesto a otros productos".
- Insumos: "Porcentaje de merma", "Activar alerta de existencias"; recetas: "Captura masiva", "Copiar receta".

## Agentes de GitHub útiles (solo copiar el .md, sin instaladores; pendiente OK de Rafael)
sqlserver-backup (vince-winkintel), sql-expert (hmohamed01), powershell-5.1-expert, technical-writer, ux-microcopy-reviewer (VoltAgent), restaurant-menu (zubair-trabzada). No existe agente para copiar SR entre sucursales ni para subir SQL: scripts propios.

## Fuentes
- softrestaurant.com/docs-manual-interactivo-soft-restaurant-12
- softrestaurant.zohodesk.com (instalación manual SQL; actualizar revisión; cambio de PC con integraciones)
- softrestaurant.com/faqs · blog SR12 · blog fin SR10
- syca.com.mx/servicios/planes-soft-restaurant-11/
- infochannel.info (administración web del menú)
- learn.microsoft.com: supported upgrades 2019, editions 2019, RESTORE · support.microsoft.com KB2936603 (builds 2014)
