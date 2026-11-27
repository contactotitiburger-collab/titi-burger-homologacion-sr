#!/usr/bin/env python3
"""
Generador de Órdenes de Compra — Titi Burger (Rafael Cordova / Cocina).
Reproduce el formato del ejemplo "OC ISLAS.doc".

Uso: se define la lista ORDENES (proveedor, oc_numero, fecha, solicita, items)
y genera un .docx por cada una en la carpeta destino.

item = (cantidad, descripcion, precio_unitario_o_None)
"""
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROJO = RGBColor(0xC0, 0x1B, 0x1B)
GRIS = RGBColor(0x40, 0x40, 0x40)

# ---- datos fijos del cliente (Titi Burger) ----
CLIENTE = {
    "Razón Social": "RAFAEL CORDOVA NIEBLA",
    "Ciudad": "MEXICALI",
    "Contacto": "NANCY SERRANO",
}
ENCARGADO = "NANCY SERRANO"


def _set_cell_bg(cell, color_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), color_hex)
    tcPr.append(shd)


def _cell_text(cell, text, bold=False, size=10, color=None, align=None, white=False):
    cell.text = ""
    p = cell.paragraphs[0]
    if align:
        p.alignment = align
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    run.font.name = "Calibri"
    if white:
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    elif color:
        run.font.color.rgb = color


def _kv_block(doc, titulo, pares):
    """Bloque tipo 'DATOS DEL X' con encabezado y filas llave/valor en tabla 2 col."""
    # encabezado de sección
    t = doc.add_table(rows=1, cols=2)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    a = hdr[0].merge(hdr[1])
    _set_cell_bg(a, "C01B1B")
    _cell_text(a, titulo, bold=True, size=10.5, white=True)
    for k, v in pares:
        row = t.add_row().cells
        _set_cell_bg(row[0], "F2F2F2")
        _cell_text(row[0], k, bold=True, size=9.5, color=GRIS)
        _cell_text(row[1], v or "", size=9.5)
    t.columns[0].width = Cm(4.5)
    t.columns[1].width = Cm(12.5)
    doc.add_paragraph()
    return t


def generar_oc(proveedor, oc_numero, fecha, solicita, items, ruta_salida, total_override=None):
    doc = Document()
    for s in doc.sections:
        s.left_margin = Cm(2)
        s.right_margin = Cm(2)
        s.top_margin = Cm(1.5)

    # ---- Título ----
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("ORDEN DE COMPRA")
    r.bold = True
    r.font.size = Pt(20)
    r.font.color.rgb = ROJO
    r.font.name = "Calibri"
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rs = sub.add_run("TITI BURGER  🍔")
    rs.font.size = Pt(11)
    rs.font.color.rgb = GRIS
    doc.add_paragraph()

    # ---- Datos del cliente ----
    _kv_block(doc, "DATOS DEL CLIENTE", [
        ("Razón Social", CLIENTE["Razón Social"]),
        ("Ciudad", CLIENTE["Ciudad"]),
        ("Contacto", CLIENTE["Contacto"]),
        ("Fecha", fecha),
        ("Solicita", solicita),
        ("Teléfono", ""),
    ])

    # ---- Datos del proveedor ----
    _kv_block(doc, "DATOS DEL PROVEEDOR", [
        ("Razón Social", proveedor.get("razon_social", "")),
        ("Ciudad", proveedor.get("ciudad", "MEXICALI")),
        ("Contacto", proveedor.get("contacto", "")),
        ("OC Número", oc_numero),
        ("Dirección", proveedor.get("direccion", "")),
        ("Teléfono", proveedor.get("telefono", "")),
    ])

    # ---- Productos ----
    t = doc.add_table(rows=1, cols=4)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    heads = ["Cantidad", "Descripción del Producto", "Precio Unitario", "Precio Total"]
    for i, h in enumerate(heads):
        _set_cell_bg(t.rows[0].cells[i], "C01B1B")
        _cell_text(t.rows[0].cells[i], h, bold=True, size=10, white=True,
                   align=WD_ALIGN_PARAGRAPH.CENTER)
    subtotal = 0.0
    hay_precios = False
    for cant, desc, pu in items:
        row = t.add_row().cells
        _cell_text(row[0], str(cant), size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(row[1], desc, size=10)
        if pu is not None:
            hay_precios = True
            _cell_text(row[2], f"${pu:,.2f}", size=10, align=WD_ALIGN_PARAGRAPH.RIGHT)
            # total de línea = cantidad * pu si la cantidad es numérica
            try:
                total_linea = float(cant) * pu
                subtotal += total_linea
                _cell_text(row[3], f"${total_linea:,.2f}", size=10, align=WD_ALIGN_PARAGRAPH.RIGHT)
            except (ValueError, TypeError):
                _cell_text(row[3], "", size=10, align=WD_ALIGN_PARAGRAPH.RIGHT)
        else:
            _cell_text(row[2], "", size=10, align=WD_ALIGN_PARAGRAPH.RIGHT)
            _cell_text(row[3], "", size=10, align=WD_ALIGN_PARAGRAPH.RIGHT)
    # filas subtotal / total
    monto_final = total_override if total_override is not None else subtotal
    valores = {"SUBTOTAL": subtotal, "TOTAL": monto_final}
    for etiqueta in ("SUBTOTAL", "TOTAL"):
        row = t.add_row().cells
        lab = row[0].merge(row[1]).merge(row[2])
        _set_cell_bg(lab, "F2F2F2")
        _cell_text(lab, etiqueta, bold=True, size=10, align=WD_ALIGN_PARAGRAPH.RIGHT)
        _cell_text(row[3], f"${valores[etiqueta]:,.2f}" if hay_precios else "", size=10,
                   bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
    t.columns[0].width = Cm(2.2)
    t.columns[1].width = Cm(9.3)
    t.columns[2].width = Cm(2.8)
    t.columns[3].width = Cm(2.8)

    doc.add_paragraph()
    nota = doc.add_paragraph()
    rn = nota.add_run("* Precios a cotizar / llenar al recibir.")
    rn.font.size = Pt(8)
    rn.font.color.rgb = GRIS
    rn.italic = True

    # ---- Firma ----
    for _ in range(3):
        doc.add_paragraph()
    fp = doc.add_paragraph()
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rf = fp.add_run("ENCARGADO DE COMPRAS")
    rf.bold = True
    rf.font.size = Pt(10)
    rf.font.color.rgb = GRIS
    ln = doc.add_paragraph()
    ln.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ln.add_run("______________________________").font.size = Pt(11)
    nm = doc.add_paragraph()
    nm.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rnm = nm.add_run(ENCARGADO + "\nFirma")
    rnm.font.size = Pt(10)

    doc.save(ruta_salida)
    return ruta_salida


if __name__ == "__main__":
    import sys, os, json
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    destino = cfg["destino"]
    os.makedirs(destino, exist_ok=True)
    for o in cfg["ordenes"]:
        items = [(i[0], i[1], i[2] if len(i) > 2 else None) for i in o["items"]]
        ruta = os.path.join(destino, o["archivo"])
        generar_oc(o["proveedor"], o["oc_numero"], o["fecha"],
                   o.get("solicita", "COCINA"), items, ruta,
                   total_override=o.get("total_override"))
        print("OK", ruta)
