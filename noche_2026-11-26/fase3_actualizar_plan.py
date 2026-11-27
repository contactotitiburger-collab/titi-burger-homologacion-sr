#!/usr/bin/env python3
"""FASE 3 — Mejora (no reescribe) el plan escrito: fases.json, plan_fases.json, plan_contrato.json, objetivos.json
y la frase del dueno en generar_avance_v2.py. Respaldo .bak_noche de cada archivo antes de tocarlo."""
import json, shutil
from pathlib import Path
B = Path("/home/tito/.openclaw/workspace/tito-lector")
def cargar(n): return json.loads((B / n).read_text(encoding="utf-8"))
def guardar(n, d):
    shutil.copy2(B / n, B / f"{n}.bak_noche"); (B / n).write_text(json.dumps(d, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
def item(lista, nombre, hecho, clave="nombre"):
    for x in lista:
        if x[clave] == nombre: x["hecho"] = hecho; return x
    x = {clave: nombre, "hecho": hecho}; lista.append(x); return x

# ---- fases.json (las 4 fases de la pagina de avance)
f = cargar("fases.json")
f3 = next(x for x in f if x["id"] == 3)
f3["descripcion"] = ("Aquí se corrige lo que esté distinto, sucursal por sucursal, siempre con copia de seguridad y con tu aprobación. "
    "Regla aprendida en el análisis: el menú, los precios y las recetas se igualan contra Montejano; los insumos, costos y paquetes contra la de Félix "
    "(su base es la de la cocina y usa los mismos códigos para otras cosas, así que no se copia completa).")
nuevos = [("Comparar cada sucursal contra la de Félix", True),
          ("Félix confirma qué partes de su base ya son definitivas", False),
          ("Aprobar qué se corrige y en qué orden", False),
          ("Preparar la forma de corregir con respaldo", True),
          ("Probar la corrección en una copia local, no en vivo", True),
          ("Probar la corrección en una copia real de la base (respaldo restaurado)", False),
          ("Corregir la primera sucursal (con tu aprobación)", False),
          ("Corregir el resto, una por una (con tu aprobación)", False),
          ("Cine Curto: mapa de códigos propio antes de corregir", False)]
viejo = {x["nombre"]: x for x in f3["items"]}
f3["items"] = []
for n, h in nuevos:
    if n == "Probar la corrección en una copia local, no en vivo" and "Probar la corrección en una copia, no en vivo" in viejo: pass
    f3["items"].append({"nombre": n, "hecho": h})
guardar("fases.json", f)

# ---- plan_fases.json (plan del contrato)
p = cargar("plan_fases.json")
cat = next(x for x in p if x["etiqueta"] == "Catálogo")
cat["desc"] = ("Dejar que las 6 sucursales manejen el mismo menú, con los mismos precios y los mismos códigos, tomando Montejano como la base del menú "
               "y la de Félix como la base de insumos, costos y paquetes.")
cat["items"] = [{"n": "Comparar cada sucursal contra la base", "hecho": True},
                {"n": "Lista de correcciones con gravedad (1,530: 479 seguras, 939 por decidir, 112 que no se tocan)", "hecho": True},
                {"n": "Tito Editor creado y probado en seco (sin conexión a sucursales)", "hecho": True},
                {"n": "Decisiones de Rafael y Félix sobre lo que hay que decidir", "hecho": False},
                {"n": "Corregir las diferencias encontradas", "hecho": False},
                {"n": "Dejar las 6 sucursales con el mismo catálogo", "hecho": False}]
cop = next(x for x in p if x["etiqueta"] == "Copiar")
cop["desc"] = ("Pasar los cambios a cada sucursal con Tito Editor: lote chico, respaldo completo antes, aprobación de Rafael y de Félix, "
               "de madrugada (3 a 10 am) y nunca en diciembre; después los lectores verifican y, si algo sale mal, se deshace.")
cop["items"] = [{"n": "Probar en una copia real de la base (respaldo restaurado)", "hecho": False},
                {"n": "Respaldar e importar en cada sucursal", "hecho": False},
                {"n": "Probar 10 tickets y firma de Félix por sucursal", "hecho": False},
                {"n": "Inventario global y reporte de mermas de carne", "hecho": False}]
guardar("plan_fases.json", p)

# ---- plan_contrato.json
c = cargar("plan_contrato.json")
c["descripcion_plan"] = (c["descripcion_plan"].rstrip(".") + ". Actualizado 27-nov-2026: el menú se iguala contra Montejano y los insumos/costos/paquetes contra Félix "
    "(la base de Félix es la de la cocina y reusa códigos). Las correcciones las prepara Tito Editor (respaldo, aprobación, deshacer y verificación con los lectores); "
    "mientras no haya login de escritura, Félix las captura en SR con la hoja que arma el Editor.")
next(x for x in c["fases_plan"] if x["nombre"].startswith("Catalogo"))["estado"] = "curso"
guardar("plan_contrato.json", c)

# ---- objetivos.json
o = cargar("objetivos.json")
r = next(x for x in o if x["nombre"].startswith("Restablecer"))
if "2026-11-27" not in r["dias"]: r["dias"].append("2026-11-27")
subs = r["subobjetivos"]; idx = next(i for i, x in enumerate(subs) if x["nombre"] == "Corregir las diferencias encontradas")
for n in ["Lista de correcciones con gravedad, sucursal por sucursal", "Crear a Tito Editor y probarlo en seco"][::-1]:
    if not any(x["nombre"] == n for x in subs): subs.insert(idx, {"nombre": n, "hecho": True})
guardar("objetivos.json", o)

# ---- frase del dueno (texto fijo en el generador)
g = B / "generar_avance_v2.py"; t = g.read_text(encoding="utf-8")
vieja = 'frase_dueno = "Ya quedaron conectadas las 6 sucursales y la compu de Félix, y el tablero de inventario las muestra en vivo. Sigue revisar Montecarlo a fondo y comparar cada sucursal contra la de Félix para corregir lo que esté distinto."'
nueva = 'frase_dueno = "Ya se comparó cada sucursal contra la de Félix y quedó la lista de lo que hay que corregir. Tito Editor ya está listo y probado sin tocar ninguna sucursal; sigue que Rafael y Félix decidan qué se corrige y en qué orden."'
if vieja in t:
    shutil.copy2(g, B / "generar_avance_v2.py.bak_noche"); g.write_text(t.replace(vieja, nueva), encoding="utf-8"); print("frase actualizada")
else: print("AVISO: no encontre la frase vieja; no se toco el generador")
print("ok")
