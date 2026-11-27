#!/usr/bin/env python3
"""
Rellena la PLANTILLA real de Rafael (OC Islas, exportada a plantilla_oc.docx)
por cada orden de compra, preservando su formato, y actualiza los Google Docs.
"""
import json, copy
from pathlib import Path
from docx import Document
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCRATCH = "/tmp/claude-1000/-home-tito/2d223782-bb49-4f05-872f-da1c4c8de126/scratchpad"
TPL = f"{SCRATCH}/plantilla_oc.docx"
FECHA = "10 AGO 2026"
FOL = "1oRQGoi6GcJbsnfCo0rOmBlnnXnnjxrvw"

# (clave_en_nombre, proveedor, [ (cant, desc, precio_unit|None) ], total_override)
ORDENES = [
    ("Peñafiel", "PEÑAFIEL", [(6,"ROOT BEER",None),(6,"DR PEPPER",None),(2,"SQUIRT",None),(4,"AGUA NATURAL",None)], None),
    ("Verdura", "VERDURA", [(3,"LECHUGA (CAJAS)",None),(2,"TOMATE (CAJAS)",None),(1,"CEBOLLA (SACO)",None),
        (15,"CHILE VERDE (KG)",None),(4,"CHILE CALIFORNIA (KG)",None),(1,"AZÚCAR (SACO)",None)], None),
    ("Coca Cola", "COCA COLA", [(48,"COCA COLA CERO",None),(24,"COCA COLA LIGHT",None),("8x24","COCA COLA",None)], None),
    ("Tapanosa", "TAPANOSA", [(3,"BOTELLAS (PAQUETES)",None),(2,"GARRAFONES",None)], None),
    ("Kowi", "KOWI", [(20,"TOCINO (KG)",None)], None),
    ("Dina", "DINA", [(60,"GRASA",12.00)], None),
    ("Ferretería", "FERRETERÍA", [(2,'COPLES HUB 4"',486.00),(1,"HOJA DE SEGUETA",45.00),(1,"TAPE NEGRO",46.00)], 1062.00),
]


def set_cell(cell, text):
    """Cambia el texto de una celda conservando su formato."""
    p = cell.paragraphs[0]
    if p.runs:
        p.runs[0].text = text
        for r in p.runs[1:]:
            r.text = ""
    else:
        p.add_run(text)


def money(x):
    return f"${x:,.2f}"


def rellenar(proveedor, items, total_override, salida):
    doc = Document(TPL)
    t_cli, t_prov, t_prod = doc.tables[0], doc.tables[1], doc.tables[2]
    # cliente: fecha en (1,3)
    set_cell(t_cli.rows[1].cells[3], FECHA)
    # proveedor: razón social (0,1), OC numero (1,3)
    set_cell(t_prov.rows[0].cells[1], proveedor)
    set_cell(t_prov.rows[1].cells[3], "0001")
    # productos: filas 1..12 disponibles (fila0 encabezado, 13-15 son subtotal/iva/total)
    subtotal = 0.0; hay_precio = False
    for i, (cant, desc, pu) in enumerate(items, start=1):
        row = t_prod.rows[i]
        set_cell(row.cells[0], str(cant))
        set_cell(row.cells[1], desc)
        if pu is not None:
            hay_precio = True
            set_cell(row.cells[2], money(pu))
            try:
                tot = float(cant) * pu; subtotal += tot
                set_cell(row.cells[3], money(tot))
            except (ValueError, TypeError):
                pass
    # limpiar filas de producto sobrantes (2..12) que traía el ejemplo
    for i in range(len(items) + 1, 13):
        for c in range(4):
            set_cell(t_prod.rows[i].cells[c], "")
    # subtotal / total
    if hay_precio:
        final = total_override if total_override is not None else subtotal
        set_cell(t_prod.rows[13].cells[3], money(subtotal))   # SUBTOTAL
        set_cell(t_prod.rows[15].cells[3], money(final))      # TOTAL
    doc.save(salida)
    return salida


def main():
    T = Path.home()/".openclaw/credentials/google/oauth/tito_tokens.json"
    tk = json.loads(T.read_text())
    creds = Credentials(token=tk["token"], refresh_token=tk["refresh_token"], token_uri=tk["token_uri"],
                        client_id=tk["client_id"], client_secret=tk["client_secret"], scopes=tk["scopes"])
    if not creds.valid:
        creds.refresh(Request()); tk["token"] = creds.token; T.write_text(json.dumps(tk, indent=2))
    drive = build("drive", "v3", credentials=creds)
    # docs existentes en la carpeta
    existentes = drive.files().list(q=f"'{FOL}' in parents and trashed=false and mimeType='application/vnd.google-apps.document'",
                                    fields="files(id,name)").execute().get("files", [])
    for clave, prov, items, tov in ORDENES:
        out = f"{SCRATCH}/oc_{clave}.docx"
        rellenar(prov, items, tov, out)
        destino = next((f for f in existentes if clave.lower() in f["name"].lower() and "PLANTILLA" not in f["name"]), None)
        if not destino:
            print("!! no encontré doc para", clave); continue
        media = MediaFileUpload(out, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        drive.files().update(fileId=destino["id"], media_body=media,
                             body={"mimeType": "application/vnd.google-apps.document"}).execute()
        print("Actualizado:", destino["name"])


if __name__ == "__main__":
    main()
