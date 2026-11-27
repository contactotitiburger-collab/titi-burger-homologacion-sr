# Fase 1 — Las 6 sucursales comparadas contra la de Félix

**Noche del 26 al 27 de noviembre de 2026 · solo lectura, no se tocó ninguna sucursal**

---

## 1. Qué se hizo

1. Entré a las **7 bases** (las 6 sucursales y la de Félix) con el usuario de solo lectura `tito`. Antes de leer comprobé en cada base que ese usuario **no tiene permiso de escribir** (no puede insertar, cambiar ni borrar). Eso se cumplió en las 7.
2. Saqué una "foto" completa de cada base: menú, grupos, precios, recetas, extras (modificadores), insumos, costos, presentaciones (paquetes), almacenes, mínimos y máximos, usuarios (sin contraseñas), formas de pago, áreas y configuración de la caja.
3. Comparé cada sucursal **contra Félix** y, para el menú, **contra Montejano** (el maestro del menú según la Propuesta B).
4. Luego volví a leer directo de las bases los hallazgos más fuertes para confirmar que no fueran un error de mi comparación. **Los 14 chequeos salieron iguales a lo que dice el análisis.**

Archivos (en la Z2): `tito-lector/noche_2026-11-26/` → `fotos/*.json` (las 7 fotos), `analisis_completo.json` (todas las diferencias), `propuestas.json` (1,530 correcciones, cada una con su gravedad y decisión).

---

## 2. El hallazgo más importante: la de Félix NO es un menú, es la base de la COCINA

La base de Félix salió de una copia de una sucursal (tiene los mismos códigos, los mismos grupos y los mismos mínimos y máximos), pero **se convirtió en la base de la cocina**, la que le surte a las carretas:

- Su grupo principal se llama **"SURTIDO A SUCURSAL TITI BURGER"** (en las sucursales, "TITI BURGER").
- Sus almacenes son **TRASPASO CARRETA A, B, C, D, E, CINE CURTO, ELABORACIÓN DE INSUMO y EVENTOS**: es una bodega que reparte, no una caja que vende.
- Sus "productos" son en su mayoría **cosas que la cocina vende a la sucursal**: mostaza por galón, manteca, carbón, catsup, sal, jabón, papel de baño, pan por paquete…
- Casi no se ha usado: tiene **6 tickets en total** (11 y 28 de octubre de 2026) y **1 movimiento de inventario**. Es una base nueva que todavía se está armando.

**Por qué importa:** Félix **reusó los códigos** que en las sucursales son hamburguesas para darles otro uso. Ejemplos confirmados directo en las bases:

| Código | En las sucursales | En Félix |
|---|---|---|
| 01007 | TITI WESTERN ($185) | MOSTAZA GAL ($152.90) |
| 01038 | TITI COMBO PECHUGA DE POLLO | PAN PARRILLERO |
| 01055 | TITI DOBLE QUESOS (RAPPI) | JABÓN LÍQUIDO BOTELLA |
| 01060 | EXTRA PAPAS DIDI | JABÓN EN POLVO BOLSA |

Son **17 códigos de producto cruzados** en cada una de las 5 sucursales normales, y **19 en Cine Curto**.

> ⚠️ **Si a una sucursal se le copia "todo igual a Félix", se borran del menú hamburguesas que se venden todos los días y se convierten en jabón o mostaza.** Por eso la regla queda así:
> - **Menú, precios de venta, recetas y extras** → se igualan contra **Montejano** (como ya dice la Propuesta B).
> - **Insumos, costos, presentaciones (paquetes) y almacenes de cocina** → aquí Félix **sí** es el ejemplo a seguir.
> - **Configuración de caja** → Félix trae reglas más estrictas que valen la pena, pero se decide una por una.

Esto es lo que necesito que **Félix confirme** (va en su reporte, Fase 4).

---

## 3. Cómo está cada sucursal

### Las 5 sucursales normales (Montejano, Hacienda del Río, Montecarlo, Villas del Rey, San Marcos)

**Entre ellas están casi idénticas.** Mismo menú (233 productos), mismas recetas (485 renglones, ni una cantidad distinta), mismos insumos (113), mismas formas de pago (16). Lo único distinto entre ellas:

| Diferencia | Dónde | Gravedad | Qué hacer |
|---|---|---|---|
| **TITI JR a $69** (en Montejano, Hacienda y Montecarlo cuesta **$79**) | Villas del Rey y San Marcos | 🔴 Alta (dinero) | **Decide Rafael/Don Titi**: ¿promo a propósito o se sube a $79? |
| Refresco y Jumex dentro del **Combo Titi JR** en **$0** (en Montejano cuestan $40 y $25 extra) | Montecarlo | 🟠 Media | Confirmar si es a propósito |
| Costo del insumo 005002 en $0.99 (las demás $0.64) | Hacienda, Montecarlo, Villas, San Marcos | 🟢 Baja | Se iguala con el costo de Félix |
| "Combo clásica + papas + bebida Uber" sin marcar como servicio rápido | Hacienda, Montecarlo, Villas, San Marcos | 🟢 Baja | Igualar a Montejano |
| Cajeros con nombres distintos (CAJERO1 vs CAJERO 1 vs CAJERO), usuario "MONTECARLO" dentro de Montejano, LIZ es administradora en unas y en otras no | Todas | 🟠 Media | **No lo toca Tito**: los accesos los maneja Félix en la caja |
| Configuración de caja (comandero, tiempos, respaldar turno abierto) | Villas es la más distinta (15 ajustes) | 🟠 Media | Decidir una por una |

**Contra Félix, las 5 tienen las mismas diferencias** (porque vienen del mismo origen):

| Tema | Cuántas diferencias por sucursal | Gravedad | Explicación sencilla |
|---|---|---|---|
| Códigos de producto cruzados | 17 | 🔴 **Crítica** | Ver sección 2. **No se copian nunca.** |
| Costos de insumos | 24 | 🔴/🟠 | Félix tiene los costos de cocina al día. En Montejano **19 insumos están en $0** (Félix solo tiene 9 en $0). Esto descuadra el costo de cada hamburguesa (food cost), **no las ventas**. |
| Paquetes (presentaciones) | 62 distintas y 22 que no existen en la sucursal | 🔴 Alta | Félix maneja el **paquete** (ej. "PAQ PAN PARRILLERO 12 PZA", $84) y la sucursal la **pieza** ("PAN PARRILLERO", $4.83). Si se cambia sin avisar, una compra capturada como "1" se convierte en 12 panes en el inventario. |
| Nombre o unidad de insumo | 5 (1 de unidad: catsup **galón → botella**) | 🔴 unidad / 🟢 nombre | Cambiar la unidad cambia lo que significa la existencia de hoy. Se hace junto con un ajuste de inventario. |
| Insumos nuevos de Félix | 4 (tapa 2 oz, servilleta chica, plato de almeja, papas en gajo) | 🟠 Media | Confirmar si la sucursal los va a usar. |
| Almacenes | Félix tiene 6 de traspaso que la sucursal no; el '10' significa otra cosa | 🟠 Media | Los de traspaso son de la cocina: **no van en la sucursal**. |
| Configuración de caja | 7 a 16 ajustes | 🟠 Media | Félix tiene más candados: *obligar motivo al cancelar*, *no cerrar turno con cuentas abiertas*. Valen la pena, pero cambian cómo trabaja el cajero. |

### Cine Curto — caso aparte

Tiene **menú propio a propósito** (boneless, nachos, hot dog, charolas, sliders; precios de cine: Titi Clásica $220 vs $150). Eso **no se toca**. Pero salieron 3 cosas reales:

1. 🔴 **Códigos de insumo cruzados con Félix (10).** El más delicado: **la CARNE en Cine Curto es el código 001034**; en Félix la carne es **005001** y el 001034 es un insumo llamado solo "C". Si la cocina le manda carne a Cine Curto por código, le llegaría al insumo equivocado. Igual con el aderezo (001036 = PAN SLIDER en Cine Curto). **Necesita un mapa de códigos propio antes de tocar nada.**
2. 🔴 **5 formas de pago sin clave del SAT** (Didi, Rappi, Uber, tarjeta de crédito, tarjeta de débito). En las demás sí la tienen. Una factura con tarjeta puede salir con la forma de pago mal. **Confirmar con el despacho.**
3. 🟠 El almacén '10' es **MERMAS** en Cine Curto y **TRASPASO A OTRA SUCURSAL** en las demás (ya lo habían visto los lectores el 24-nov; sigue igual). Cuidado al sumar mermas de todas juntas.

---

## 4. Las 1,530 correcciones, ordenadas

Cada diferencia quedó como una corrección en `propuestas.json`, con una de 3 etiquetas:

| Etiqueta | Cuántas | Qué significa |
|---|---|---|
| **PROPUESTO** | 479 | Cambio seguro y claro (nombres, costos, banderas). Sale cuando Rafael y Félix den el visto bueno. |
| **REVISAR** | 939 | Necesita una decisión de negocio (paquetes, configuración, precios, altas nuevas). |
| **NO TOCAR** | 112 | Por diseño, Tito Editor **nunca** las hace (códigos cruzados, borrar insumos, usuarios, menú de Cine Curto). |

Por gravedad: **95 críticas** (todas en NO TOCAR), 290 altas, 785 medias y 360 bajas.

> Nota: 1,050 de las 1,530 son de **paquetes** (presentaciones): son ~110 cambios repetidos en 5 sucursales. Una sola decisión ("¿las sucursales manejan paquete o pieza?") resuelve 1,000 de ellas de golpe.

---

## 5. Orden recomendado para corregir

1. **Primero lo que no se discute:** costos de insumos en $0 → costo de Félix. No cambia ventas ni tickets; solo arregla el costo de las recetas.
2. **Nombres de insumos y banderas** (texto). Bajo riesgo.
3. **Decisiones de dinero:** Titi JR en Villas y San Marcos; extras del Combo JR en Montecarlo.
4. **Paquetes y unidades**, sucursal por sucursal, **el mismo día que se hace conteo físico**.
5. **Configuración de caja**, con Félix presente y en horario sin venta.
6. **Cine Curto al final**, con su mapa de códigos aparte.

Sucursal piloto sugerida: **Villas del Rey** (la de menos movimiento: 10,225 tickets desde ene-2025; base SQL 2014 igual que Hacienda, San Marcos y Cine Curto).

---

## 6. Re-lectura y autocrítica

- **¿Estoy seguro de que la de Félix es la cocina?** Sí, por 4 pruebas independientes: el nombre del grupo, los almacenes de traspaso, los productos (jabón, carbón, manteca) y que casi no tiene ventas. Pero **no sé si ya está terminada**: tiene 9 insumos con costo en $0 y nombres a medias ("C", "B"). **Félix debe decir qué partes ya son definitivas.**
- **¿Algo que se pudo escapar?** No comparé horarios de precio por día (promos lunes–domingo), impresoras por estación ni las comandas. Son configuración fina; quedan para una segunda pasada.
- **Herramientas de GitHub:** busqué si convenía instalar algo para comparar bases (data-diff de Datafold, schema compare de Microsoft, Redgate SQL Data Compare). **No hizo falta**: data-diff está archivado desde 2024, el de Microsoft compara estructura y no datos, y Redgate es de paga y para Windows. La comparación propia hizo el trabajo y no metió nada nuevo al sistema. En la Fase 5 se investiga más a fondo.
