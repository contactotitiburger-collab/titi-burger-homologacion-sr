#!/usr/bin/env python3
"""Genera resumen legible de ventas mensuales por carreta desde el JSON."""
import json
from pathlib import Path

IN = Path("/home/tito/.openclaw/data/ventas_mensual_3anios.json")
OUT = Path("/home/tito/.openclaw/data/ventas_mensual_3anios_resumen.txt")

# Nombre corto por empresa (para columnas)
EMPRESAS = ["FOVISSTE", "MONTECARLO", "SAN MARCOS", "HACIENDA DEL RÍO", "CURTO", "VILLAS DEL REY"]
SHORT = {
    "FOVISSTE": "Montejano",
    "MONTECARLO": "Montecarlo",
    "SAN MARCOS": "SanMarcos",
    "HACIENDA DEL RÍO": "Hacienda",
    "CURTO": "CineCurto",
    "VILLAS DEL REY": "Villas",
}

data = json.loads(IN.read_text())
meses = data.get("meses", {})
anios_disp = data.get("anios_disponibles", [])

def total_de(cell):
    """Devuelve el total float, o None si no hay dato / sucursal sin operacion.
    total==0 con tickets==0 => la carreta no existia / sin operacion ese mes."""
    if isinstance(cell, dict) and "total" in cell:
        if cell.get("total", 0) == 0 and cell.get("tickets", 0) == 0:
            return None
        return cell["total"]
    return None

lineas = []
lineas.append("VENTA MENSUAL POR CARRETA - Titi Burger (Soft Restaurant)")
lineas.append(f"Anios disponibles en selector SR: {', '.join(anios_disp)}")
lineas.append("Fuente: reporte Consultar/3. Cifra = 'total' (con impuestos, sin propina).")
lineas.append("'sin op' = sucursal sin operacion / no existia ese mes. 'ERR' = mes fallido.")
lineas.append("")

# Encabezado
cols = [SHORT[e] for e in EMPRESAS]
header = f"{'Mes':<9}" + "".join(f"{c:>12}" for c in cols) + f"{'TOTAL':>14}"
lineas.append(header)
lineas.append("-" * len(header))

# Acumuladores anuales por empresa
anual = {}  # anual[year][empresa] = suma

meses_ordenados = sorted(meses.keys())
for key in meses_ordenados:
    mes = meses[key]
    year = key.split("-")[0]
    if isinstance(mes, dict) and mes.get("status") == "anio_no_disponible":
        continue  # no lo mostramos (no hay selector)
    if isinstance(mes, dict) and "error" in mes and len(mes) == 1:
        lineas.append(f"{key:<9}" + f"{'ERROR mes: '+str(mes['error'])[:40]}")
        continue
    fila = f"{key:<9}"
    suma_mes = 0.0
    hay_algo = False
    for e in EMPRESAS:
        cell = mes.get(e, {})
        t = total_de(cell)
        if t is None:
            fila += f"{'sin op':>12}"
        else:
            fila += f"{t:>12,.0f}"
            suma_mes += t
            hay_algo = True
            anual.setdefault(year, {}).setdefault(e, 0.0)
            anual[year][e] += t
    fila += f"{suma_mes:>14,.0f}" if hay_algo else f"{'-':>14}"
    lineas.append(fila)

# Totales anuales por carreta
lineas.append("")
lineas.append("=" * len(header))
lineas.append("TOTALES ANUALES POR CARRETA (suma de meses con dato real)")
lineas.append("=" * len(header))
lineas.append(f"{'Anio':<9}" + "".join(f"{c:>12}" for c in cols) + f"{'TOTAL':>14}")
lineas.append("-" * len(header))
for year in sorted(anual.keys()):
    fila = f"{year:<9}"
    suma = 0.0
    for e in EMPRESAS:
        v = anual[year].get(e, 0.0)
        if v == 0.0:
            fila += f"{'sin op':>12}"
        else:
            fila += f"{v:>12,.0f}"
            suma += v
    fila += f"{suma:>14,.0f}"
    if year == "2026":
        fila += "  (YTD)"
    lineas.append(fila)

txt = "\n".join(lineas) + "\n"
OUT.write_text(txt)
print(txt)
print(f"[guardado] {OUT}")
