#!/usr/bin/env python3
"""Consolida el Catálogo de Gastos agregando SOLO los rubros que faltan (del Presupuesto Mayo).
Sin hojas adicionales — todo en la única hoja del Catálogo.

Rubros nuevos que se agregan (de las notas del Presupuesto Mayo 2026):
- Aguinaldo / vacaciones / prima (Ley) — en SUELDOS
- Mesada Don Titi — en GASTOS PERSONALES
"""
import json
from pathlib import Path
from copy import copy

from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

CATALOGO_SRC = Path("/home/tito/.openclaw/data/Catálogo de Gastos - Titi Burger.xlsx")
OUT = Path("/home/tito/.openclaw/workspace/apps_delivery/Catálogo de Gastos - Titi Burger.xlsx")


def insertar_fila_con_estilo(ws, fila_ref: int, fila_destino: int, valores: dict):
    """Inserta una fila copiando el estilo de fila_ref y poniendo valores {col_num: valor}."""
    ws.insert_rows(fila_destino)
    for c in range(1, ws.max_column + 1):
        ref = ws.cell(fila_ref + 1, c) if fila_ref + 1 == fila_destino else ws.cell(fila_ref, c)
        # copiar estilo desde fila_ref (que ahora quedó una fila arriba porque insertamos)
        src = ws.cell(fila_ref, c) if fila_destino > fila_ref else ws.cell(fila_ref + 1, c)
        dst = ws.cell(fila_destino, c)
        if src.has_style:
            dst.font = copy(src.font)
            dst.fill = copy(src.fill)
            dst.border = copy(src.border)
            dst.alignment = copy(src.alignment)
            dst.number_format = src.number_format
        val = valores.get(c)
        if val is not None:
            dst.value = val


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb = load_workbook(CATALOGO_SRC)
    ws = wb.active  # única hoja "Catálogo de Gastos"

    # Encontrar filas de secciones para insertar el rubro nuevo al final de cada una
    # SUELDOS empieza en fila 14 y termina en fila 21 (Vacaciones Toro final)
    # PROVEEDORES empieza en 22
    # GASTOS PERSONALES empieza en 78 y termina en 85 (Luz CFE Casa)
    # OTROS empieza en 86

    # Insertar "Aguinaldo / vacaciones / prima (Ley)" en fila 22 (antes de PROVEEDORES)
    # Insertar "Mesada Don Titi" en fila 87 (antes de OTROS - pero al final de GASTOS PERSONALES)

    # Ojo: al insertar UNA fila, todo se recorre +1. Hago las inserciones de abajo hacia arriba.

    # Primero: Mesada Don Titi (fila objetivo 86, antes de "OTROS" que está en 86)
    ws.insert_rows(86)
    # copiar estilo desde una fila de GASTOS PERSONALES (85 = Luz CFE Casa)
    ref = 85 + 1 if 85 + 1 <= ws.max_row else 85  # después de la inserción, la ref se recorrió +1
    for c in range(1, ws.max_column + 1):
        src = ws.cell(86, c)  # la fila que quedó vacía
        # copiamos estilo de una fila "normal" — la que estaba en 85 ahora está en 85 (no se movió porque insertamos en 86)
        # Wait: insert_rows(86) recorre fila 86 y en adelante → así que la ref "Luz CFE Casa" ahora está en 85 aún
        modelo = ws.cell(85, c)  # Luz CFE Casa (todavía en 85, no se movió)
        if modelo.has_style:
            src.font = copy(modelo.font)
            src.fill = copy(modelo.fill)
            src.border = copy(modelo.border)
            src.alignment = copy(modelo.alignment)
            src.number_format = modelo.number_format
    # llenar valores
    fila_mesada = 86
    ws.cell(fila_mesada, 1, "Mesada Don Titi")
    ws.cell(fila_mesada, 2, "Cuadro semanal — pendiente confirmar")
    ws.cell(fila_mesada, 3, None)
    ws.cell(fila_mesada, 4, "Semanal")
    ws.cell(fila_mesada, 5, None)
    ws.cell(fila_mesada, 6, "PENDIENTE")
    ws.cell(fila_mesada, 7, "PENDIENTE")
    ws.cell(fila_mesada, 8, "Monto exacto pendiente confirmar — de las notas del Presupuesto Mayo")

    # Ahora: Aguinaldo (fila objetivo 22, antes de PROVEEDORES)
    ws.insert_rows(22)
    for c in range(1, ws.max_column + 1):
        src = ws.cell(22, c)
        modelo = ws.cell(21, c)  # Vacaciones Toro final — sección SUELDOS
        if modelo.has_style:
            src.font = copy(modelo.font)
            src.fill = copy(modelo.fill)
            src.border = copy(modelo.border)
            src.alignment = copy(modelo.alignment)
            src.number_format = modelo.number_format
    ws.cell(22, 1, "Aguinaldo / vacaciones / prima (Ley)")
    ws.cell(22, 2, "Prestaciones de ley")
    ws.cell(22, 3, None)
    ws.cell(22, 4, "Anual (aguinaldo dic) + variable")
    ws.cell(22, 5, None)
    ws.cell(22, 6, "PERIÓDICO")
    ws.cell(22, 7, "PENDIENTE")
    ws.cell(22, 8, "Presupuesto Mayo lo incluye en 'Nómina + IMSS + Fonacot + Infonavit + Ley' — pendiente calcular monto")

    wb.save(OUT)
    print(f"Guardado: {OUT}")
    print(f"Filas ahora: {ws.max_row}")
    return OUT


def subir_a_drive(archivo):
    print("=== SUBIENDO A DRIVE ===")
    TOK = json.loads(Path("/home/tito/.openclaw/credentials/google/oauth/tito_tokens.json").read_text())
    creds = Credentials(token=TOK["token"], refresh_token=TOK["refresh_token"], token_uri=TOK["token_uri"],
        client_id=TOK["client_id"], client_secret=TOK["client_secret"], scopes=TOK["scopes"])
    if not creds.valid:
        creds.refresh(Request())
    svc = build("drive", "v3", credentials=creds)

    FOLDER = "1Bql9OzXtZ_OBNikYF3KEr0qJUA83f-U2"  # Titi Burger · Titiburger las originales
    NAME = "Catálogo de Gastos - Titi Burger"

    q = f"'{FOLDER}' in parents and name = '{NAME}' and trashed=false"
    r = svc.files().list(q=q, fields="files(id)").execute()
    for f in r.get("files", []):
        svc.files().update(fileId=f["id"], body={"trashed": True}).execute()
        print(f"  papelera: {f['id']}")

    media = MediaFileUpload(str(archivo),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    meta = {"name": NAME, "parents": [FOLDER],
            "mimeType": "application/vnd.google-apps.spreadsheet"}
    f = svc.files().create(body=meta, media_body=media, fields="id,webViewLink,name").execute()
    print(f"OK Drive: {f['webViewLink']}")
    return f["webViewLink"]


if __name__ == "__main__":
    archivo = main()
    link = subir_a_drive(archivo)
    print(f"\nLINK: {link}")
