#!/usr/bin/env python3
"""
Cuentas por pagar PRO — versión que respeta EXACTO lo de Nancy:
- SALTA las filas OCULTAS del archivo de Nancy (facturas ya pagadas, ajustes) →
  el detalle muestra solo lo PENDIENTE, igual que su vista.
- Colores VERDES (como Nancy), NO rojo Titi.
- Secciones de préstamos con nombres + préstamos con interés (mafiosos, etc.).

Genera un .xlsx en scratch; el que sube a Drive es aparte (subir_cuentas.py).
"""
import openpyxl, datetime
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

SRC = "/tmp/claude-1000/-home-tito/2d223782-bb49-4f05-872f-da1c4c8de126/scratchpad/NANCY_cuentas.xlsx"
OUT = "/tmp/claude-1000/-home-tito/2d223782-bb49-4f05-872f-da1c4c8de126/scratchpad/cuentas_pro.xlsx"

SALDOS = {
    "QUEVEDO": 26638.60, "MC CAIN": 35620.00, "CARBONERO": 23877.18,
    "KOWI": 14589.32, "PERAFAN": 8385.00, "ISLAS": None,
    "ALIMENTOS PARRA": 10150.00, "PEPSI": 7888.00, "EDGAR FRANCO": None,
    "ROLLOS Y ETIQUETAS": None, "BIMBO": 7470.00, "EL HALCON": 14078.32,
    "NEPTUNO": 892.50, "AVANZA LLANTAS": 1512.00, "COMERCIO AZTECA": 20877.70,
    "SALOMON Y ASOCIADOS": 34800.00,
}
# préstamos con nombre + día de pago + monto
PRESTAMOS = [
    ("Santander - Préstamo Andy", 7, 45500.00),
    ("Compartamos Banco", 14, 15500.00),
    ("RAM", 14, 8300.00),
    ("ASP Nuevo", 20, 32035.00),
    ("Revolvente", 22, 85000.00),
    ("SUA de Andrónica", None, 43682.45),
    ("Andrónica - Imp. 4.25% Estatal 1er Trim", None, 42784.00),
]
# préstamos con interés (capital, tasa, periodo, dia)
PRESTAMOS_INT = [
    ("Mafioso 1", 1200000, 0.10, "Mensual", 19),
    ("Mafioso 2", 300000, 0.05, "Mensual", None),
    ("Nancy", 100000, 0.04, "Mensual", None),
    ("Carola", 180000, 0.04, "Anual", None),
]

# --- paleta VERDE (como Nancy) ---
VERDE = "C6D9A0"       # banda/encabezado
VERDE_CL = "E6EFD4"    # subtotal
GRIS = "404040"
thin = Side(style="thin", color="C8C8C8")
BORDE = Border(left=thin, right=thin, top=thin, bottom=thin)
FILL_V = PatternFill("solid", fgColor=VERDE)
FILL_VC = PatternFill("solid", fgColor=VERDE_CL)
F_TIT = Font(name="Calibri", size=16, bold=True, color="4C6B1F")
F_B = Font(name="Calibri", size=10, bold=True)
F_N = Font(name="Calibri", size=10)
CT = Alignment("center", vertical="center")
RT = Alignment("right", vertical="center")
LT = Alignment("left", vertical="center")
MXN = '"$"#,##0.00'


def txt(v): return "" if v is None else str(v).strip()
def norm(n): return n.upper().replace("  ", " ").strip()


def parse(src):
    wb = openpyxl.load_workbook(src)   # sin data_only para leer row_dimensions
    ws = wb.active
    wbv = openpyxl.load_workbook(src, data_only=True)
    wsv = wbv.active
    maxr = ws.max_row
    known = {norm(k) for k in SALDOS}
    # nombres de préstamos que NO son proveedores (para cortar el bloque de Salomón)
    fin_prov = ("SANTANDER", "COMPARTAMOS", "RAM", "ASP", "REVOLVENTE", "SUA", "ANDRONICA", "ANDRÓNICA")
    blocks = []; cur = None
    for r in range(1, maxr + 1):
        b = txt(wsv.cell(row=r, column=2).value)
        nb = norm(b)
        # cortar en cuanto empiece la zona de préstamos (para que Salomón no los absorba)
        if nb.startswith(fin_prov):
            cur = None
            continue
        if nb in known or b.lower().startswith("avanza"):
            cur = {"nombre": b, "rfc": "", "movs": []}; blocks.append(cur); continue
        if cur is None:
            continue
        # SALTAR filas ocultas de Nancy (pagadas / ajustes que ella esconde)
        if ws.row_dimensions[r].hidden:
            continue
        if b.upper().startswith(("RFC", "RFV")):
            cur["rfc"] = b.replace("RFC", "").replace("RFV", "").strip(); continue
        if b.upper().startswith("FECHA"):
            continue
        c3 = wsv.cell(row=r, column=3).value
        c4 = wsv.cell(row=r, column=4).value
        fecha = wsv.cell(row=r, column=2).value if isinstance(wsv.cell(row=r, column=2).value, datetime.datetime) else None
        concepto = c3 if c3 not in (None, "") else (b if not fecha else "")
        importe = c4 if isinstance(c4, (int, float)) else None
        if fecha is None and importe is None:
            continue
        etiqueta = f"{b} {txt(c3)}".lower()
        es_abono = (importe is not None and importe < 0) or ("abono" in etiqueta) or ("a favor" in etiqueta)
        cur["movs"].append({"fecha": fecha, "concepto": txt(concepto), "importe": importe, "abono": es_abono})
    return blocks


def _hdr(ws, r, cols, fill=FILL_V, font=F_B):
    for j, h in enumerate(cols, start=1):
        c = ws.cell(row=r, column=j, value=h)
        c.font = font; c.fill = fill; c.border = BORDE
        c.alignment = CT if j != 2 else LT


def build():
    blocks = parse(SRC)
    wb = openpyxl.Workbook()

    # ===== RESUMEN =====
    rs = wb.active; rs.title = "Resumen"; rs.sheet_view.showGridLines = False
    rs["A1"] = "CUENTAS POR PAGAR — TITI BURGER"; rs["A1"].font = F_TIT
    rs["A2"] = "Proveedores · corte 07 AGO 2026"; rs["A2"].font = Font(size=10, color=GRIS, italic=True)
    _hdr(rs, 4, ["#", "PROVEEDOR", "RFC", "SALDO PENDIENTE"])
    row = 5; n = 0
    for bl in blocks:
        n += 1; saldo = SALDOS.get(norm(bl["nombre"]))
        rs.cell(row=row, column=1, value=n).alignment = CT
        rs.cell(row=row, column=2, value=bl["nombre"].title()).font = F_B
        rs.cell(row=row, column=3, value=bl["rfc"]).font = F_N
        cc = rs.cell(row=row, column=4)
        if saldo is None:
            cc.value = "POR CONFIRMAR"; cc.font = Font(size=10, italic=True, color="B00000")
        else:
            cc.value = saldo; cc.number_format = MXN; cc.font = F_N
        cc.alignment = RT
        for j in range(1, 5): rs.cell(row=row, column=j).border = BORDE
        row += 1
    pf, pl = 5, row - 1
    rs.cell(row=row, column=2, value="SUBTOTAL PROVEEDORES").font = F_B
    t = rs.cell(row=row, column=4, value=f"=SUM(D{pf}:D{pl})"); t.number_format = MXN; t.font = F_B; t.fill = FILL_VC; t.alignment = RT
    rs.cell(row=row, column=2).fill = FILL_VC
    row += 2
    rs.cell(row=row, column=2, value="PRÉSTAMOS E IMPUESTOS").font = Font(size=11, bold=True, color="4C6B1F"); row += 1
    _hdr(rs, row, ["", "CONCEPTO", "DÍA PAGO", "MONTO"]); row += 1; f2 = row
    for con, dia, mon in PRESTAMOS:
        rs.cell(row=row, column=2, value=con).font = F_N
        rs.cell(row=row, column=3, value=(dia if dia else "")).alignment = CT
        m = rs.cell(row=row, column=4, value=mon); m.number_format = MXN; m.alignment = RT; m.font = F_N
        for j in range(1, 5): rs.cell(row=row, column=j).border = BORDE
        row += 1
    rs.cell(row=row, column=2, value="SUBTOTAL PRÉSTAMOS E IMPUESTOS").font = F_B
    t = rs.cell(row=row, column=4, value=f"=SUM(D{f2}:D{row-1})"); t.number_format = MXN; t.font = F_B; t.fill = FILL_VC; t.alignment = RT
    rs.cell(row=row, column=2).fill = FILL_VC
    row += 2
    rs.cell(row=row, column=2, value="PRÉSTAMOS CON INTERÉS (capital que se debe)").font = Font(size=11, bold=True, color="4C6B1F"); row += 1
    _hdr(rs, row, ["", "PRESTAMISTA", "CAPITAL", "TASA", "PERIODO", "DÍA", "INTERÉS"]); row += 1; f3 = row
    for nom, cap, tasa, per, dia in PRESTAMOS_INT:
        rs.cell(row=row, column=2, value=nom).font = F_N
        c = rs.cell(row=row, column=3, value=cap); c.number_format = MXN; c.alignment = RT; c.font = F_N
        ta = rs.cell(row=row, column=4, value=tasa); ta.number_format = "0%"; ta.alignment = CT
        rs.cell(row=row, column=5, value=per).alignment = CT
        rs.cell(row=row, column=6, value=(dia if dia else "")).alignment = CT
        it = rs.cell(row=row, column=7, value=f"=C{row}*D{row}"); it.number_format = MXN; it.alignment = RT; it.font = F_N
        for j in range(1, 8): rs.cell(row=row, column=j).border = BORDE
        row += 1
    rs.cell(row=row, column=2, value="CAPITAL TOTAL PRÉSTAMOS").font = F_B
    t = rs.cell(row=row, column=3, value=f"=SUM(C{f3}:C{row-1})"); t.number_format = MXN; t.font = F_B; t.fill = FILL_VC; t.alignment = RT
    rs.cell(row=row, column=2).fill = FILL_VC
    row += 1
    rs.cell(row=row, column=2, value="Nota: Carola es 4% ANUAL (≈$600/mes); los demás mensuales.").font = Font(size=8, italic=True, color=GRIS)
    for col, w in zip("ABCDEFG", [5, 34, 16, 10, 12, 8, 16]):
        rs.column_dimensions[col].width = w

    # ===== DETALLE =====
    dt = wb.create_sheet("Detalle"); dt.sheet_view.showGridLines = False
    dt["A1"] = "DETALLE POR PROVEEDOR"; dt["A1"].font = F_TIT
    r = 3
    for bl in blocks:
        dt.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
        cell = dt.cell(row=r, column=1, value=f"  {bl['nombre'].title()}    {('· RFC ' + bl['rfc']) if bl['rfc'] else ''}")
        cell.font = F_B; cell.fill = FILL_V
        for j in range(1, 6): dt.cell(row=r, column=j).fill = FILL_V
        r += 1
        _hdr(dt, r, ["FECHA", "FACTURA / CONCEPTO", "CARGO", "ABONO", ""]); r += 1
        for m in bl["movs"]:
            if m["fecha"]:
                dc = dt.cell(row=r, column=1, value=m["fecha"]); dc.number_format = "dd/mm/yyyy"; dc.alignment = CT
            dt.cell(row=r, column=2, value=m["concepto"]).font = F_N
            imp = m["importe"]
            if imp is not None:
                if m["abono"]:
                    a = dt.cell(row=r, column=4, value=abs(imp)); a.number_format = MXN; a.alignment = RT; a.font = Font(size=10, color="1B7A1B")
                else:
                    c = dt.cell(row=r, column=3, value=imp); c.number_format = MXN; c.alignment = RT; c.font = F_N
            for j in range(1, 5): dt.cell(row=r, column=j).border = BORDE
            r += 1
        saldo = SALDOS.get(norm(bl["nombre"]))
        dt.cell(row=r, column=2, value="SALDO PENDIENTE").font = F_B
        sc = dt.cell(row=r, column=4)
        if saldo is None:
            sc.value = "POR CONFIRMAR"; sc.font = Font(size=10, bold=True, italic=True, color="B00000")
        else:
            sc.value = saldo; sc.number_format = MXN; sc.font = F_B
        sc.alignment = RT
        for j in range(1, 5): dt.cell(row=r, column=j).fill = FILL_VC; dt.cell(row=r, column=j).border = BORDE
        r += 2

    # sección préstamos e impuestos
    dt.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
    dt.cell(row=r, column=1, value="  PRÉSTAMOS E IMPUESTOS").font = F_B
    for j in range(1, 6): dt.cell(row=r, column=j).fill = FILL_V
    r += 1
    _hdr(dt, r, ["", "CONCEPTO", "DÍA DE PAGO", "MONTO", ""]); r += 1; pfa = r
    for con, dia, mon in PRESTAMOS:
        dt.cell(row=r, column=2, value=con).font = F_N
        dt.cell(row=r, column=3, value=(dia if dia else "")).alignment = CT
        m = dt.cell(row=r, column=4, value=mon); m.number_format = MXN; m.alignment = RT; m.font = F_N
        for j in range(1, 5): dt.cell(row=r, column=j).border = BORDE
        r += 1
    dt.cell(row=r, column=2, value="SUBTOTAL PRÉSTAMOS E IMPUESTOS").font = F_B
    t = dt.cell(row=r, column=4, value=f"=SUM(D{pfa}:D{r-1})"); t.number_format = MXN; t.font = F_B; t.alignment = RT
    for j in range(1, 5): dt.cell(row=r, column=j).fill = FILL_VC
    r += 2

    # sección préstamos con interés
    dt.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
    dt.cell(row=r, column=1, value="  PRÉSTAMOS CON INTERÉS").font = F_B
    for j in range(1, 8): dt.cell(row=r, column=j).fill = FILL_V
    r += 1
    _hdr(dt, r, ["", "PRESTAMISTA", "CAPITAL", "TASA", "PERIODO", "DÍA DE PAGO", "INTERÉS"]); r += 1; pfi = r
    for nom, cap, tasa, per, dia in PRESTAMOS_INT:
        dt.cell(row=r, column=2, value=nom).font = F_N
        c = dt.cell(row=r, column=3, value=cap); c.number_format = MXN; c.alignment = RT; c.font = F_N
        ta = dt.cell(row=r, column=4, value=tasa); ta.number_format = "0%"; ta.alignment = CT
        dt.cell(row=r, column=5, value=per).alignment = CT
        dt.cell(row=r, column=6, value=(dia if dia else "")).alignment = CT
        it = dt.cell(row=r, column=7, value=f"=C{r}*D{r}"); it.number_format = MXN; it.alignment = RT; it.font = F_N
        for j in range(1, 8): dt.cell(row=r, column=j).border = BORDE
        r += 1
    dt.cell(row=r, column=2, value="CAPITAL TOTAL").font = F_B
    t = dt.cell(row=r, column=3, value=f"=SUM(C{pfi}:C{r-1})"); t.number_format = MXN; t.font = F_B; t.alignment = RT
    for j in range(1, 8): dt.cell(row=r, column=j).fill = FILL_VC
    r += 1
    dt.cell(row=r, column=2, value="Nota: Carola es 4% ANUAL (≈$600/mes). Los demás son mensuales.").font = Font(size=8, italic=True, color=GRIS)

    for col, w in zip("ABCDEFG", [13, 34, 15, 12, 12, 13, 15]):
        dt.column_dimensions[col].width = w

    wb.save(OUT)
    print("OK ->", OUT)
    return OUT


if __name__ == "__main__":
    build()
