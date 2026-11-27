import json
from pathlib import Path
A = json.loads(Path("analisis_completo.json").read_text())
def J(x, n=2500): print(json.dumps(x, ensure_ascii=False, default=str)[:n])
for n in ["Hacienda del Rio", "Montecarlo", "Villas del Rey", "San Marcos"]:
    m = A["vs_montejano"][n]; print(f"\n######## {n} vs MONTEJANO")
    for dim in ["productos", "precios", "modificadores", "insumosdetalle", "almacen"]:
        if m[dim]["distintos"] or m[dim]["faltan"] or m[dim]["sobran"]: print(dim); J({"F": m[dim]["faltan"], "S": m[dim]["sobran"], "D": m[dim]["distintos"]}, 1200)
    print("usuarios"); J({"F": m["usuarios"]["faltan"], "S": m["usuarios"]["sobran"], "D": m["usuarios"]["distintos"]}, 800)
    print("config"); J(m["configuracion"], 1500)
c = A["vs_felix"]["Cine Curto"]; print("\n######## CINE CURTO vs FELIX")
for dim in ["insumos", "almacen", "formasdepago", "grupos", "gruposmodificadores"]:
    print(dim, "X:"); J(c[dim]["codigo_cruzado"], 1500); print(dim, "D (muestra):"); J(dict(list(c[dim]["distintos"].items())[:8]), 1500)
print("insumos F:"); J(c["insumos"]["faltan"], 1200); print("insumos S:"); J(c["insumos"]["sobran"], 800)
print("insumos por nombre otro codigo:"); J(c["insumos_por_nombre"]["mismo_nombre_otro_codigo"])
print("recetas D:"); J(c["recetas"]["distintos"])
mc = A["vs_montejano"]["Cine Curto"]; print("precios CC vs Montejano (muestra 25):"); J(dict(list(mc["precios"]["distintos"].items())[:25]), 3000)
print("productos X CC vs montejano:"); J(mc["productos"]["codigo_cruzado"], 2500)
