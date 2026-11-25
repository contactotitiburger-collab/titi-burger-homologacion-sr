# Paso 4 — Mapa de la base de datos Soft Restaurant (24-nov-2026)

Base de datos SQL Server `softrestaurant11` (4 sucursales) / `softrestaurant12` (Montejano). ~355-371 tablas totales — este mapa documenta solo las tablas que importan para la homologación; el resto es configuración interna de Soft Restaurant que no se va a tocar.

## MENÚ Y PRECIOS
| Tabla | Qué guarda | Campos clave | Relación |
|---|---|---|---|
| `grupos` | Categorías de productos (Hamburguesas, Bebidas, etc.) | `idgrupo`, `descripcion` | `productos.idgrupo` → `grupos.idgrupo` |
| `productos` | Catálogo de productos/combos | `idproducto`, `descripcion`, `idgrupo`, `plu` | — |
| `productosdetalle` | Precio y configuración por producto **por sucursal** (`idempresa`) | `idproducto`, `precio`, `impuesto1-3` | 1 fila por producto (73 columnas: horarios especiales, puntos, etc.) |
| `listadeprecios` / `listadepreciosdetalle` | Listas de precio alternativas (si existen) | `idlistaprecio`, `precio` | Poco usado hoy — la mayoría de sucursales usa solo el precio base de `productosdetalle` |
| `modificadores` / `gruposmodificadores` | Extras/modificadores de productos | `idmodificador` | — |

## INVENTARIO Y RECETAS
| Tabla | Qué guarda | Campos clave | Relación |
|---|---|---|---|
| `insumos` | Catálogo de insumos (materia prima) | `idinsumo`, `descripcion`, `unidad` | **Falta puente con IDs de cocina `INS-###`** (pendiente) |
| `almacen` | Almacenes/carretas de cada sucursal | `idalmacen`, `nombre`, `tipo` | OJO: mismo `idalmacen` significa cosas distintas entre sucursales (ver hallazgo almacén '10') |
| `recetasalmacenes` | Recetas (qué insumos usa cada producto) | — | No se profundizó hoy, queda para el mapa de cocina |
| `movsinv` / `movtosalmacen` | Movimientos de inventario (mermas, consumo) | — | Ya en uso por `merma_todas.py` en producción |
| `consumodiarioinsumos` | Consumo diario calculado | — | — |

## VENTAS Y CORTES
| Tabla | Qué guarda | Campos clave | Relación |
|---|---|---|---|
| `cheques` | Un registro por ticket/cuenta | `folio`, `fecha`, `total`, `cancelado`, `pagado`, `idmesero`, `idempresa` | Fuente que usé hoy para el Verificador |
| `cheqdet` | Líneas de detalle de cada ticket (qué productos) | `folio`, `idproducto`, cantidad | `cheqdet.folio` → `cheques.folio` |
| `formasdepago` / `formasdepagodetalle` | Catálogo y detalle de formas de pago por ticket | — | Ya en uso por `sr_formaspago_dia_multi.py` |
| `declaracioncorte` | Declaración de efectivo/corte de caja por turno | `idturno`, `denominacion` | — |
| `CorteCaja` | Solo existe en Montejano y Villas (versión más nueva) | — | Diferencia de esquema, no de datos |

## CONFIGURACIÓN
| Tabla | Qué guarda | Campos clave | Relación |
|---|---|---|---|
| `usuarios` | Logins del sistema por sucursal | `usuario`, `nombre`, `administrador` | Nomenclatura inconsistente entre sucursales (ver lector de configuración) |
| `impuestos` | Tasas de impuesto por insumo/región | `idinsumo`, `idregion`, `impuesto1-3` | No revisado a fondo hoy |
| `areas` / `areasrestaurant` / `mesas` | Áreas y mesas del restaurante | — | No revisado a fondo hoy |
| `comandosimpresion` | Configuración de impresoras de comanda | — | No revisado a fondo hoy |

## Diferencias de esquema (no de datos) entre sucursales
Montejano (SR12) y Villas del Rey tienen algunas tablas extra que Hacienda/San Marcos/Cine Curto no tienen (`CorteCaja`, `polizasgeneradas`, `paymentproviders`, etc.) — son de versiones de Soft Restaurant ligeramente distintas, no afectan la homologación de datos de negocio. Detalle completo en `diff_tablas.txt`.
