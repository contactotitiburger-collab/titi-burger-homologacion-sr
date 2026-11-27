#!/usr/bin/env python3
"""FASE 1 (noche 26-nov-2026) — Extraccion SOLO LECTURA de las 6 sucursales + Felix.
Saca una "foto" completa de cada base (menu, precios, recetas, insumos, costos, almacenes,
config, usuarios sin contrasenas) a fotos/<cf>.json. No escribe nada en ninguna base.
"""
import json, sys, datetime, decimal
from pathlib import Path
from lib_lectura import conn, q, SUCS, REF

OUT = Path(__file__).parent / "fotos"; OUT.mkdir(exist_ok=True)

def norm(v):
    if isinstance(v, decimal.Decimal): return float(v)
    if isinstance(v, (datetime.datetime, datetime.date)): return v.isoformat()
    if isinstance(v, bytes): return None
    if isinstance(v, str): return v.strip()
    return v

def k(v): return str(v).strip() if v is not None else ""

def tabla(cur, sql):
    try: return [{kk: norm(vv) for kk, vv in r.items()} for r in q(cur, sql)]
    except Exception as e: return {"_error": str(e)[:200]}

CONSULTAS = {
  "grupos": "SELECT idgrupo, descripcion, clasificacion, prioridad FROM grupos",
  "productos": "SELECT idproducto, descripcion, idgrupo, nombrecorto, plu, usarcomedor, usardomicilio, usarrapido, nofacturable, idprodserv_SAT FROM productos",
  "precios": "SELECT idproducto, idempresa, precio, impuesto1, impuesto2, impuesto3, bloqueado, precioabierto FROM productosdetalle",
  "recetas": "SELECT idproducto, idinsumo, cantidad, idempresa FROM costos",
  "recetas_almacen": "SELECT idproducto, idarearestaurant, idalmacen, idinsumo FROM recetasalmacenes",
  "modificadores": "SELECT idproducto, idmodificador, precio, idgruposmodificadores FROM modificadores",
  "gruposmodificadores": "SELECT idgruposmodificadores, descripcion FROM gruposmodificadores",
  "insumos": "SELECT idinsumo, descripcion, idgruposi, unidad, elaborado, rendimientoelaborado FROM insumos",
  "insumosdetalle": "SELECT idinsumo, idempresa, inventariable, costo, costopromedio, costoestandar, impuesto1, merma, descargar, estatus FROM insumosdetalle",
  "presentaciones": "SELECT idinsumospresentaciones, descripcion, idinsumo, rendimiento, unidad FROM insumospresentaciones",
  "presentacionesdetalle": "SELECT idinsumospresentaciones, costo, costopromedio, idproveedor, estatus FROM insumospresentacionesdetalle",
  "elaborados": "SELECT idelaborado, idinsumo, cantidad FROM elaborados",
  "gruposi": "SELECT idgruposi, descripcion FROM gruposi",
  "almacen": "SELECT idalmacen, nombre, tipo FROM almacen",
  "stockinsumos": "SELECT idinsumo, idinsumospresentaciones, idalmacen, stockminimo, stockideal, stockmaximo FROM stockinsumos",
  "usuarios": "SELECT usuario, nombre, administrador, perfil, status FROM usuarios",
  "formasdepago": "SELECT idformadepago, descripcion, tipo, visible, comision, aceptapropina, idformapago_SAT FROM formasdepago",
  "areasrestaurant": "SELECT idarearestaurant, descripcion, idtiposervicio FROM areasrestaurant",
  "configuracion": "SELECT * FROM configuracion",
  "estaciones": "SELECT idestacion, descripcion FROM estaciones",
  "uso": "SELECT (SELECT COUNT(*) FROM cheques) cheques, (SELECT MIN(fecha) FROM cheques) primer_ticket, (SELECT MAX(fecha) FROM cheques) ultimo_ticket, (SELECT COUNT(*) FROM movsinv) movsinv",
}
SENSIBLES = ("contra", "password", "pass", "clave", "licencia", "token")

def foto(nombre, cf):
    cn = conn(cf); cur = cn.cursor()
    d = {"sucursal": nombre, "cf": cf, "leido": datetime.datetime.now().isoformat(timespec="seconds")}
    d["version"] = q(cur, "SELECT @@VERSION v, DB_NAME() db")[0]
    d["permisos"] = q(cur, "SELECT IS_ROLEMEMBER('db_datawriter') writer, IS_ROLEMEMBER('db_owner') owner, HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','UPDATE') upd")[0]
    d["bases_en_servidor"] = [r["name"] for r in tabla(cur, "SELECT name FROM sys.databases") if isinstance(r, dict)]
    for t, sql in CONSULTAS.items():
        d[t] = tabla(cur, sql)
    if isinstance(d["configuracion"], list) and d["configuracion"]:
        d["configuracion"] = [{kk: vv for kk, vv in d["configuracion"][0].items()
                               if not any(s in kk.lower() for s in SENSIBLES)}]
    cn.close()
    (OUT / f"{cf}.json").write_text(json.dumps(d, ensure_ascii=False, indent=0, default=str))
    return d

if __name__ == "__main__":
    objetivos = [REF] + SUCS
    if len(sys.argv) > 1: objetivos = [x for x in objetivos if x[1] in sys.argv[1:]]
    for nombre, cf in objetivos:
        try:
            d = foto(nombre, cf)
            print(f"OK {nombre}: prod={len(d['productos'])} recetas={len(d['recetas']) if isinstance(d['recetas'],list) else d['recetas']} insumos={len(d['insumos'])} bases={d['bases_en_servidor']} writer={d['permisos']}", flush=True)
        except Exception as e:
            print(f"ERROR {nombre}: {e}", flush=True)
