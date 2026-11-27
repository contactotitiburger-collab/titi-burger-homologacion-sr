import json, sys
from pathlib import Path
A = json.loads(Path("analisis_completo.json").read_text())
F = {cf: json.loads(Path(f"fotos/{cf}.json").read_text()) for cf in ["felix", "montejano", "cine_curto"]}
def J(x, n=4000): print(json.dumps(x, ensure_ascii=False, default=str)[:n])
m = A["vs_felix"]["Montejano"]
print("### FELIX grupos:"); J([(g["idgrupo"], g["descripcion"]) for g in F["felix"]["grupos"]])
print("### MONTEJANO grupos:"); J([(g["idgrupo"], g["descripcion"]) for g in F["montejano"]["grupos"]])
print("### FELIX productos (95):"); J([(p["idproducto"], p["descripcion"], p["idgrupo"]) for p in F["felix"]["productos"]], 6000)
for dim in ["productos", "precios"]:
    print(f"### {dim} faltan:"); J(m[dim]["faltan"], 800)
    print(f"### {dim} distintos:"); J(m[dim]["distintos"], 3500)
print("### productos codigo cruzado:"); J(m["productos"]["codigo_cruzado"], 3000)
print("### recetas faltan (en felix, no en montejano):"); J(m["recetas"]["faltan"], 2500)
for dim in ["insumos", "insumosdetalle", "almacen", "usuarios", "gruposi"]:
    print(f"### {dim}: faltan / sobran / distintos"); J(m[dim]["faltan"], 1000); J(m[dim]["sobran"], 600); J(m[dim]["distintos"], 3000)
print("### presentaciones faltan:"); J(m["presentaciones"]["faltan"], 1500)
print("### presentaciones distintos (muestra):"); J(dict(list(m["presentaciones"]["distintos"].items())[:12]), 2500)
print("### presentacionesdetalle distintos (muestra):"); J(dict(list(m["presentacionesdetalle"]["distintos"].items())[:10]), 1500)
print("### configuracion vs felix:"); J(m["configuracion"], 2500)
print("### FELIX almacenes:"); J(F["felix"]["almacen"]); print("### MONTEJANO almacenes:"); J(F["montejano"]["almacen"])
print("### insumos x nombre no existen en montejano:"); J(m["insumos_por_nombre"]["nombre_no_existe"])
print("### stockinsumos felix muestra:"); J(F["felix"]["stockinsumos"][:5]); print("montejano:"); J(F["montejano"]["stockinsumos"][:5])
