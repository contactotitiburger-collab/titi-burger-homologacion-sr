#!/usr/bin/env python3
"""Modifica TITI_BURGER_MAESTRO.xlsx col H (% Cocina) para que jale del Excel Cocina.

REGLAS (de memoria excel-maestro-costos):
- openpyxl.load_workbook + modificar solo lo necesario, NUNCA regenerar.
- NO renumerar IDs.
- Preservar fórmulas existentes en otras columnas.

Modifica solo las filas mapeadas a procesos del Excel Cocina:
  INS-029 (Boneless 1 orden)  → Excel Cocina fila 5 (PROC-001)
  INS-030 (Boneless ½ orden)  → Excel Cocina fila 5 (mismo %)
  INS-031 (Carne / patty)     → Excel Cocina fila 9 (PROC-005)
  INS-035 (Pollo)             → Excel Cocina fila 10 (PROC-006)
  INS-037 (Tocino x burger)   → Excel Cocina fila 8 (PROC-004)
"""
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.comments import Comment

MAESTRO_IN  = "/tmp/MAESTRO.xlsx"
MAESTRO_OUT = "/tmp/MAESTRO_linkeado.xlsx"

# Fórmula de referencia externa al Excel Cocina (funciona en Excel desktop)
# Cuando ambos archivos están en la misma carpeta.
COCINA_FILE = "TITI_BURGER_COCINA.xlsx"
COCINA_SHEET = "🥩 Costo Cocina"

# Mapeo: INS del Maestro → fila del Excel Cocina (donde está la col L con el % Final)
MAPEO = {
    "INS-029": 5,   # Boneless 1 orden  → PROC-001 (Boneless)
    "INS-030": 5,   # Boneless ½ orden  → PROC-001 (mismo proceso)
    "INS-031": 9,   # Carne paq         → PROC-005 (Patty)
    "INS-035": 10,  # Pollo             → PROC-006 (Pollo)
    "INS-037": 8,   # Tocino x burger   → PROC-004 (Tocino)
}

# Color para resaltar las celdas linkeadas (verde más fuerte = "viene del Excel Cocina")
fill_linked = PatternFill("solid", fgColor="A9D08E")
font_linked = Font(name="Calibri", size=11, bold=True, color="000000")
center      = Alignment(horizontal="center", vertical="center")


def main():
    wb = load_workbook(MAESTRO_IN)
    ws = wb.active
    print(f"Cargado: {MAESTRO_IN} → hoja '{ws.title}' ({ws.max_row} filas)")

    cambios = 0
    for r in range(5, ws.max_row + 1):
        id_ = ws.cell(row=r, column=1).value
        if id_ in MAPEO:
            cocina_row = MAPEO[id_]
            # Col H = '%Cocina' → fórmula referencia externa al Excel Cocina col L
            formula = f"='[{COCINA_FILE}]{COCINA_SHEET}'!$L${cocina_row}"
            cell = ws.cell(row=r, column=8)
            cell.value = formula
            cell.fill = fill_linked
            cell.font = font_linked
            cell.alignment = center
            cell.number_format = "0.0%"
            cell.comment = Comment(
                f"Linkeado a {COCINA_FILE} → '{COCINA_SHEET}' fila {cocina_row} col L.\n"
                f"Si el archivo Cocina no está abierto, Excel mostrará el último valor "
                f"calculado. Para refrescar, abra ambos en Excel desktop. "
                f"En Google Sheets convertir a IMPORTRANGE.",
                "Tito"
            )
            print(f"  ✓ {id_} (fila {r}) → Cocina fila {cocina_row}")
            cambios += 1

    wb.save(MAESTRO_OUT)
    print(f"\nGuardado: {MAESTRO_OUT}")
    print(f"Cambios: {cambios} filas linkeadas")


if __name__ == "__main__":
    main()
