#!/usr/bin/env python3
"""FASE 1 — Compara las fotos (fotos/*.json) de cada sucursal contra Felix y contra Montejano.
Solo trabaja con archivos locales. Salida: analisis_completo.json"""
import json, re, unicodedata
from pathlib import Path
from lib_lectura import SUCS, REF

D = Path(__file__).parent
F = {cf: json.loads((D / "fotos" / f"{cf}.json").read_text()) for _, cf in [REF] + SUCS}

def s(v): return "" if v is None else str(v).strip()
def nd(t):
    t = unicodedata.normalize("NFKD", s(t).upper()); t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+", " ", t).strip()
def num(v):
    try: return round(float(v), 4)
    except Exception: return s(v)

# dimension -> (llave, campos a comparar, campo de descripcion)
DIM = {
 "grupos": (("idgrupo",), ("descripcion", "clasificacion"), "descripcion"),
 "productos": (("idproducto",), ("descripcion", "idgrupo", "usarcomedor", "usardomicilio", "usarrapido", "nofacturable", "idprodserv_SAT"), "descripcion"),
 "precios": (("idproducto",), ("precio", "impuesto1", "impuesto2", "impuesto3", "bloqueado", "precioabierto"), None),
 "recetas": (("idproducto", "idinsumo"), ("cantidad",), None),
 "modificadores": (("idproducto", "idmodificador"), ("precio", "idgruposmodificadores"), None),
 "gruposmodificadores": (("idgruposmodificadores",), ("descripcion",), "descripcion"),
 "insumos": (("idinsumo",), ("descripcion", "idgruposi", "unidad", "elaborado", "rendimientoelaborado"), "descripcion"),
 "insumosdetalle": (("idinsumo",), ("inventariable", "costo", "costoestandar", "impuesto1", "merma", "descargar", "estatus"), None),
 "presentaciones": (("idinsumospresentaciones",), ("descripcion", "idinsumo", "rendimiento", "unidad"), "descripcion"),
 "presentacionesdetalle": (("idinsumospresentaciones",), ("costo", "idproveedor", "estatus"), None),
 "elaborados": (("idelaborado", "idinsumo"), ("cantidad",), None),
 "gruposi": (("idgruposi",), ("descripcion",), "descripcion"),
 "almacen": (("idalmacen",), ("nombre", "tipo"), "nombre"),
 "stockinsumos": (("idinsumo", "idinsumospresentaciones", "idalmacen"), ("stockminimo", "stockideal", "stockmaximo"), None),
 "usuarios": (("usuario",), ("nombre", "administrador", "perfil", "status"), "nombre"),
 "formasdepago": (("idformadepago",), ("descripcion", "tipo", "visible", "comision", "aceptapropina", "idformapago_SAT"), "descripcion"),
 "areasrestaurant": (("idarearestaurant",), ("descripcion", "idtiposervicio"), "descripcion"),
}
NUM = {"precio", "cantidad", "costo", "costoestandar", "impuesto1", "impuesto2", "impuesto3", "rendimiento",
       "rendimientoelaborado", "stockminimo", "stockideal", "stockmaximo", "comision", "merma"}

def indexar(rows, llave):
    if not isinstance(rows, list): return {}
    return {"|".join(s(r.get(c)) for c in llave): r for r in rows}

def comparar(ref, suc, dim):
    llave, campos, dcampo = DIM[dim]
    A, B = indexar(ref.get(dim), llave), indexar(suc.get(dim), llave)
    falt = {k: s(A[k].get(dcampo)) if dcampo else A[k] for k in sorted(set(A) - set(B))}
    sobr = {k: s(B[k].get(dcampo)) if dcampo else B[k] for k in sorted(set(B) - set(A))}
    dif, cruz = {}, {}
    for k in sorted(set(A) & set(B)):
        d = {}
        for c in campos:
            va, vb = A[k].get(c), B[k].get(c)
            if c in NUM: eq = num(va) == num(vb)
            elif c in ("descripcion", "nombre"): eq = nd(va) == nd(vb)
            else: eq = s(va) == s(vb)
            if not eq: d[c] = {"ref": va, "suc": vb}
        if d:
            dif[k] = d
            if dcampo and dcampo in d:
                a, b = set(nd(A[k].get(dcampo)).split()), set(nd(B[k].get(dcampo)).split())
                if not (a & b): cruz[k] = {"ref": s(A[k].get(dcampo)), "suc": s(B[k].get(dcampo))}
    return {"ref_total": len(A), "suc_total": len(B), "comunes": len(set(A) & set(B)),
            "faltan": falt, "sobran": sobr, "distintos": dif, "codigo_cruzado": cruz}

def comparar_config(ref, suc):
    a = (ref.get("configuracion") or [{}])[0]; b = (suc.get("configuracion") or [{}])[0]
    ignorar = {"ultimatransferencia", "reindexado", "respaldo", "WorkspaceId"}
    out = {}
    for c in sorted(set(a) | set(b)):
        if c in ignorar or "fecha" in c.lower() or "ultimo" in c.lower() or "folio" in c.lower(): continue
        if s(a.get(c)) != s(b.get(c)): out[c] = {"ref": a.get(c), "suc": b.get(c)}
    return out

def nombre_match(ref, suc, dim, dcampo):
    """Empata por DESCRIPCION (no por codigo): cuantos de la ref existen en la sucursal con otro codigo."""
    A = {nd(r.get(dcampo)): s(r.get(DIM[dim][0][0])) for r in ref.get(dim, []) if isinstance(r, dict)}
    B = {nd(r.get(dcampo)): s(r.get(DIM[dim][0][0])) for r in suc.get(dim, []) if isinstance(r, dict)}
    mismo = sum(1 for n in A if n in B and A[n] == B[n])
    otro = {n: {"ref": A[n], "suc": B[n]} for n in A if n in B and A[n] != B[n]}
    nada = [n for n in A if n not in B]
    return {"mismo_nombre_mismo_codigo": mismo, "mismo_nombre_otro_codigo": otro, "nombre_no_existe": nada}

out = {"referencias": {"felix": "Felix", "montejano": "Montejano (maestro de menu)"}, "vs_felix": {}, "vs_montejano": {}, "uso": {}, "version": {}}
for n, cf in [REF] + SUCS:
    out["uso"][n] = F[cf].get("uso"); out["version"][n] = F[cf]["version"]["v"].split("\n")[0] + " / " + F[cf]["version"]["db"]
for n, cf in SUCS:
    out["vs_felix"][n] = {dim: comparar(F["felix"], F[cf], dim) for dim in DIM}
    out["vs_felix"][n]["configuracion"] = comparar_config(F["felix"], F[cf])
    out["vs_felix"][n]["insumos_por_nombre"] = nombre_match(F["felix"], F[cf], "insumos", "descripcion")
    out["vs_felix"][n]["productos_por_nombre"] = nombre_match(F["felix"], F[cf], "productos", "descripcion")
    if cf != "montejano":
        out["vs_montejano"][n] = {dim: comparar(F["montejano"], F[cf], dim) for dim in DIM}
        out["vs_montejano"][n]["configuracion"] = comparar_config(F["montejano"], F[cf])
(D / "analisis_completo.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))

# ---- resumen en pantalla
def fila(r): return f"F{len(r['faltan']):>4} S{len(r['sobran']):>4} D{len(r['distintos']):>4} X{len(r['codigo_cruzado']):>3}"
for ref in ("vs_felix", "vs_montejano"):
    print(f"\n==== {ref}  (F=faltan S=sobran D=distintos X=codigo cruzado) ====")
    for n, dims in out[ref].items():
        print(f"\n## {n}")
        for dim in DIM: print(f"  {dim:22} {fila(dims[dim])}   (ref {dims[dim]['ref_total']} / suc {dims[dim]['suc_total']})")
        print(f"  configuracion          {len(dims['configuracion'])} campos distintos")
        if "insumos_por_nombre" in dims:
            x = dims["insumos_por_nombre"]; print(f"  insumos x nombre: igual={x['mismo_nombre_mismo_codigo']} otro_codigo={len(x['mismo_nombre_otro_codigo'])} no_existe={len(x['nombre_no_existe'])}")
print("\nUSO:", json.dumps(out["uso"], default=str, ensure_ascii=False))
