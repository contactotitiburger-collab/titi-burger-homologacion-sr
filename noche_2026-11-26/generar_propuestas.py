#!/usr/bin/env python3
"""FASE 1 -> lista de correcciones propuestas (propuestas.json), que es la ENTRADA de Tito Editor.
Cada propuesta: id, sucursal, tema, tabla, llave, campo, actual, propuesto, fuente, gravedad, decision.
decision: PROPUESTO (sale si Rafael/Felix aprueban) | REVISAR (necesita decision de negocio) | NO_TOCAR (riesgo/por diseno)
Solo lee archivos locales."""
import json
from pathlib import Path
from lib_lectura import SUCS
D = Path(__file__).parent
A = json.loads((D / "analisis_completo.json").read_text())
CINCO = [n for n, cf in SUCS if cf != "cine_curto"]
P = []
def add(**k):
    k["id"] = f"P{len(P)+1:04d}"; P.append(k)

for n in CINCO:
    vf = A["vs_felix"][n]
    # 1) costos de insumos: Felix tiene costos al dia; sucursales con 0 o viejos
    for llave, d in vf["insumosdetalle"]["distintos"].items():
        for campo, v in d.items():
            grav = "ALTA" if campo == "costo" and (v["suc"] in (0, 0.0, None)) else "MEDIA"
            add(sucursal=n, tema="Costo de insumo", tabla="insumosdetalle", llave={"idinsumo": llave}, campo=campo,
                actual=v["suc"], propuesto=v["ref"], fuente="Felix", gravedad=grav, decision="PROPUESTO",
                porque="El costo de Felix es el de cocina al dia; en la sucursal esta en 0 o desactualizado (afecta costo de receta / food cost, NO afecta ventas).")
    # 2) presentaciones: costo / rendimiento / descripcion
    for llave, d in vf["presentacionesdetalle"]["distintos"].items():
        for campo, v in d.items():
            add(sucursal=n, tema="Costo/proveedor de presentacion", tabla="insumospresentacionesdetalle", llave={"idinsumospresentaciones": llave},
                campo=campo, actual=v["suc"], propuesto=v["ref"], fuente="Felix", gravedad="MEDIA", decision="REVISAR",
                porque="Felix maneja la presentacion por paquete (ej. paquete de 12 panes); la sucursal por pieza. Cambiarlo afecta como se capturan compras/traspasos: va junto con el rendimiento.")
    for llave, d in vf["presentaciones"]["distintos"].items():
        for campo, v in d.items():
            grav = "ALTA" if campo == "rendimiento" else "BAJA"
            add(sucursal=n, tema="Presentacion de insumo", tabla="insumospresentaciones", llave={"idinsumospresentaciones": llave},
                campo=campo, actual=v["suc"], propuesto=v["ref"], fuente="Felix", gravedad=grav,
                decision="REVISAR" if campo == "rendimiento" else "PROPUESTO",
                porque=("Rendimiento = cuantas piezas trae el paquete. Si se cambia sin avisar, una compra de '1' se vuelve 12 piezas en inventario." if campo == "rendimiento"
                        else "Nombre mas claro en Felix (solo texto)."))
    # 3) insumos: nombre / unidad
    for llave, d in vf["insumos"]["distintos"].items():
        for campo, v in d.items():
            add(sucursal=n, tema="Insumo (nombre/unidad)", tabla="insumos", llave={"idinsumo": llave}, campo=campo,
                actual=v["suc"], propuesto=v["ref"], fuente="Felix", gravedad="ALTA" if campo == "unidad" else "BAJA",
                decision="REVISAR" if campo == "unidad" else "PROPUESTO",
                porque=("Cambiar la unidad (ej. GALON -> PZA) cambia el significado de la existencia actual; hay que ajustar inventario el mismo dia." if campo == "unidad" else "Nombre del insumo como lo tiene Felix."))
    # 4) insumos y presentaciones que Felix tiene y la sucursal no (altas nuevas)
    for llave, desc in vf["insumos"]["faltan"].items():
        add(sucursal=n, tema="Insumo nuevo", tabla="insumos", llave={"idinsumo": llave}, campo="(alta)", actual=None, propuesto=desc,
            fuente="Felix", gravedad="MEDIA", decision="REVISAR", porque="Felix lo da de alta; confirmar si la sucursal lo va a usar antes de crearlo.")
    for llave, desc in vf["presentaciones"]["faltan"].items():
        add(sucursal=n, tema="Presentacion nueva", tabla="insumospresentaciones", llave={"idinsumospresentaciones": llave}, campo="(alta)",
            actual=None, propuesto=desc, fuente="Felix", gravedad="MEDIA", decision="REVISAR", porque="Presentacion que existe en Felix (cocina) y no en la sucursal.")
    for llave, desc in vf["insumos"]["sobran"].items():
        add(sucursal=n, tema="Insumo que Felix ya no tiene", tabla="insumos", llave={"idinsumo": llave}, campo="(baja)", actual=desc, propuesto=None,
            fuente="Felix", gravedad="BAJA", decision="NO_TOCAR", porque="Nunca se borra: puede tener historial de recetas/movimientos. Si acaso, se marca inactivo despues.")
    # 5) configuracion
    for campo, v in vf["configuracion"].items():
        add(sucursal=n, tema="Configuracion de caja", tabla="configuracion", llave={}, campo=campo, actual=v["suc"], propuesto=v["ref"],
            fuente="Felix", gravedad="MEDIA", decision="REVISAR",
            porque="Cambia como se comporta la caja (cancelaciones, comandero, cierres). Es decision de operacion, no de datos.")
    # 6) MENU vs Felix: no se copia (codigos cruzados)
    for llave, v in vf["productos"]["codigo_cruzado"].items():
        add(sucursal=n, tema="Codigo de producto cruzado con Felix", tabla="productos", llave={"idproducto": llave}, campo="descripcion",
            actual=v["suc"], propuesto=v["ref"], fuente="Felix", gravedad="CRITICA", decision="NO_TOCAR",
            porque="Mismo codigo, cosa distinta (en Felix es un insumo de cocina). Copiarlo borraria un producto que se vende. El menu se homologa contra Montejano, no contra Felix.")

# 7) MENU entre sucursales (maestro Montejano)
for n in CINCO:
    if n == "Montejano": continue
    vm = A["vs_montejano"][n]
    for dim, tabla, tema in [("precios", "productosdetalle", "Precio de venta"), ("productos", "productos", "Producto (bandera)"), ("modificadores", "modificadores", "Modificador")]:
        for llave, d in vm[dim]["distintos"].items():
            for campo, v in d.items():
                if dim == "precios" and campo == "precio":
                    grav, dec, pq = "ALTA", "REVISAR", "Precio de venta distinto al de Montejano. Puede ser a proposito (promo/zona). Decide Rafael/Don Titi."
                elif dim == "modificadores":
                    grav, dec, pq = "MEDIA", "REVISAR", "Extra de combo con precio distinto a Montejano (puede ser bebida incluida a proposito)."
                else:
                    grav, dec, pq = "BAJA", "PROPUESTO", "Bandera de 'servicio rapido' distinta a Montejano en este producto."
                lk = dict(zip(("idproducto", "idmodificador"), llave.split("|")))
                add(sucursal=n, tema=tema, tabla=tabla, llave=lk, campo=campo, actual=v["suc"], propuesto=v["ref"],
                    fuente="Montejano", gravedad=grav, decision=dec, porque=pq)

# 8) Cine Curto: caso aparte
cc = A["vs_felix"]["Cine Curto"]
for llave, v in cc["insumos"]["codigo_cruzado"].items():
    add(sucursal="Cine Curto", tema="Codigo de insumo cruzado con Felix", tabla="insumos", llave={"idinsumo": llave}, campo="descripcion",
        actual=v["suc"], propuesto=v["ref"], fuente="Felix", gravedad="CRITICA", decision="NO_TOCAR",
        porque="El mismo codigo es otro insumo en Felix (ej. 001034 = CARNE en Cine Curto). Un traspaso de cocina por codigo mandaria el insumo equivocado. Requiere mapa de codigos aparte.")
for campo_ll, d in cc["formasdepago"]["distintos"].items():
    for campo, v in d.items():
        if campo == "idformapago_SAT":
            add(sucursal="Cine Curto", tema="Forma de pago sin clave SAT", tabla="formasdepago", llave={"idformadepago": campo_ll}, campo=campo,
                actual=v["suc"], propuesto=v["ref"], fuente="Felix", gravedad="ALTA", decision="REVISAR",
                porque="Sin clave SAT la factura sale con forma de pago incorrecta. Confirmar con el despacho.")
add(sucursal="Cine Curto", tema="Menu propio", tabla="productos/productosdetalle", llave={}, campo="(todo)", actual="164 productos, precios de cine",
    propuesto="(sin cambio)", fuente="Montejano", gravedad="BAJA", decision="NO_TOCAR", porque="Menu y precios distintos a proposito (sucursal de cine).")
# 9) Usuarios: el Editor no toca usuarios
for n in [x for x, _ in SUCS]:
    u = A["vs_montejano"].get(n, {}).get("usuarios") if n != "Montejano" else A["vs_felix"][n]["usuarios"]
    if u and (u["faltan"] or u["sobran"] or u["distintos"]):
        add(sucursal=n, tema="Usuarios de caja", tabla="usuarios", llave={}, campo="(varios)", actual=f"{u['suc_total']} usuarios",
            propuesto="Nomenclatura comun CAJERO 1..N", fuente="Montejano", gravedad="MEDIA", decision="NO_TOCAR",
            porque="Usuarios y contrasenas los maneja Felix a mano en la caja. Tito Editor no toca accesos.")

(D / "propuestas.json").write_text(json.dumps(P, ensure_ascii=False, indent=1, default=str))
from collections import Counter
print("TOTAL", len(P))
print("por decision:", Counter(p["decision"] for p in P))
print("por gravedad:", Counter(p["gravedad"] for p in P))
print("por sucursal x decision:")
for (s, d), c in sorted(Counter((p["sucursal"], p["decision"]) for p in P).items()): print(f"  {s:18} {d:10} {c}")
print("por tema:")
for t, c in Counter(p["tema"] for p in P).most_common(): print(f"  {t:40} {c}")
