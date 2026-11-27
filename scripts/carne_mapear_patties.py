#!/usr/bin/env python3
"""Mapea productos vendidos -> patties de carne de res -> kg -> $.
Periodo 1-15 ago 2026. Solo consumo TEORICO. NO inventa: lo dudoso se FLAGUEA."""
import re, glob, os
from collections import defaultdict

DIR = "/home/tito/.openclaw/data/carne_1a15ago"
G_CARNE = 0.115   # kg carne cruda por patty (115 g)
PRECIO = 113.0    # $/kg carne (costeo cocina)

FILES = {
    "Montejano": "Montejano_12764.txt",
    "Montecarlo": "Montecarlo_13056.txt",
    "Hacienda del Rio": "Hacienda_del_Rio_22980.txt",
    "San Marcos": "San_Marcos_22871.txt",
    "Cine Curto": "Cine_Curto_23032.txt",
    "Villas del Rey": "Villas_del_Rey_26983.txt",
}

def classify(desc):
    """Devuelve (patties_por_unidad, categoria, flag_text|None)."""
    d = desc.upper()
    # 1. Pollo -> 0 patties de res
    if "PECHUGA" in d or "POLLO" in d:
        return 0.0, "pollo (0 res)", None
    # 2. Extras/toppings -> 0
    if "EXTRA" in d:
        return 0.0, "extra/topping", None
    # 3. Cine Curto papas/nachos cargados y entradas (prefijo D.. / E..)
    if d.startswith("D..") or d.startswith("E."):
        return 0.0, "entrada/papas cargadas", None
    # 4. No-carne claros
    NOCARNE = ["PAPAS A LA","PAPAS ALA","PAPAS EN GAJO","PAPA EN GAJO","PAPAS PREPARADA",
               "PAPAS 1.5","AROS","ADEREZO","NACHOS","CHAROLA","BONELES","BONELESS",
               "HOT DOG","SIN PAPAS","DEDOS DE QUESO","SODAS","SODA","AGUA","TE",
               "JAMAICA","COCA","PEPSI","MANZANITA","SQUIRT","MIRINDA","7 UP",
               "ROOT BEER","DR PEPPER","ORAGE","CERO","LIGHT"]
    # match por palabra completa para no comer "WESTER" con "TE", etc.
    if any(re.search(r'\b'+re.escape(k), d) for k in NOCARNE):
        return 0.0, "no-carne (papa/bebida/boneless/etc)", None
    # 5. Slider
    if "SLIDE" in d or "SLIDER" in d:
        return 0.5, "slider (0.5 supuesto)", "SUPUESTO slider = 0.5 patty (gramaje real desconocido)"
    # 6. Hamburguesas de res con # de patties
    if "DOBLE CARNE" in d:
        return 2.0, "doble carne (2)", None
    if "PAREJA" in d:
        return 2.0, "combo pareja (2)", "SUPUESTO combo pareja = 2 patties (2 doble queso)"
    if "DUO" in d and "PROMOCION" in d:
        return 2.0, "promo duo (2 supuesto)", "SUPUESTO promo duo = 2 patties (2 hamburguesas)"
    if "TITI NIGHT" in d:
        return 1.0, "titi night (1 supuesto)", "SUPUESTO Titi Night = 1 patty (contenido no confirmado)"
    if "DOBLE QUESO" in d:
        return 1.0, "doble queso (1 supuesto)", "SUPUESTO doble queso = 1 patty (doble queso, no doble carne)"
    if "LOW CARB" in d:  # de carne (pollo ya filtrado arriba)
        return 1.0, "low carb carne (1)", None
    if any(k in d for k in ["CLASICA","CLASIA","TOCINO","CALIFORNIA","WESTER","HAWAIANA"]):
        return 1.0, "sencilla res (1)", None
    # 7. Generico "HAMBURGUESAS"/"HAMBURGUSA" sin tipo -> desconocido
    if "HAMBUR" in d:
        return 0.0, "hamburguesa generica (?)", "SIN MAPEAR: 'HAMBURGUESAS' generico, patties/tipo desconocido"
    # 8. Promos sin detalle
    if "2X1" in d or ("PROMOCION" in d and "CLASICA" not in d):
        return 0.0, "promo sin detalle (?)", "SIN MAPEAR: promo sin desglose de contenido"
    # 9. Nada -> flag
    return 0.0, "no reconocido (?)", "SIN MAPEAR: producto no reconocido"

resumen = []
flags = defaultdict(lambda: defaultdict(float))  # flag_text -> {branch: qty}
gran_patties = 0.0
detalle_por_suc = {}

for branch, fname in FILES.items():
    path = os.path.join(DIR, fname)
    txt = open(path).read()
    burger_units = 0.0
    patties = 0.0
    det = []
    for line in txt.split("\n"):
        m = re.match(r'^(\d{5})\t(.+?)\t([\d,]+)\.\d+\t', line)
        if not m:
            continue
        clave, desc, cant = m.group(1), m.group(2).strip(), int(m.group(3).replace(",", ""))
        ppu, cat, flag = classify(desc)
        if ppu > 0:
            burger_units += cant
            patties += cant * ppu
            det.append((clave, desc, cant, ppu, cant*ppu, cat))
        if flag:
            flags[flag][branch] += cant
    kg = patties * G_CARNE
    money = kg * PRECIO
    gran_patties += patties
    resumen.append((branch, burger_units, patties, kg, money))
    detalle_por_suc[branch] = sorted(det, key=lambda x: -x[4])

print("="*78)
print("CONSUMO TEORICO DE CARNE DE RES  ·  1 al 15 de agosto de 2026")
print("(patty = 115 g carne cruda ; carne = $113/kg ; costeo cocina)")
print("="*78)
print(f"{'Sucursal':<18}{'Uds hamb':>10}{'Patties':>12}{'Kg carne':>12}{'$ carne':>14}")
print("-"*66)
tot_u = tot_p = tot_kg = tot_m = 0
for b,u,p,kg,m in resumen:
    print(f"{b:<18}{u:>10.0f}{p:>12.1f}{kg:>12.1f}{'$'+format(m,',.0f'):>14}")
    tot_u+=u; tot_p+=p; tot_kg+=kg; tot_m+=m
print("-"*66)
print(f"{'TOTAL':<18}{tot_u:>10.0f}{tot_p:>12.1f}{tot_kg:>12.1f}{'$'+format(tot_m,',.0f'):>14}")

print("\n\n===== FLAGS / SIN MAPEAR (no incluidos en el conteo de patties) =====")
for flag, brs in flags.items():
    tot = sum(brs.values())
    detail = ", ".join(f"{b}:{int(q)}" for b,q in brs.items())
    print(f"- {flag}")
    print(f"    unidades: {int(tot)}  ({detail})")

print("\n\n===== DETALLE DE PRODUCTOS CONTADOS COMO CARNE, POR SUCURSAL =====")
for b in FILES:
    print(f"\n--- {b} ---")
    for clave,desc,cant,ppu,tp,cat in detalle_por_suc[b]:
        print(f"  {clave} {desc:<42.42} {cant:>4}u x{ppu:>3} = {tp:>6.1f}  [{cat}]")
