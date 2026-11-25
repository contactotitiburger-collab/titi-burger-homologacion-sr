#!/usr/bin/env python3
"""Agrega una fila a registro_actividad.csv de forma segura (csv.writer maneja
comas/comillas dentro del texto solo). Evita el bug del 25-nov donde `echo >>`
rompia columnas si el texto tenia una coma adentro.

Uso: python3 agregar_log.py FECHA HORA_INICIO HORA_FIN DURACION "TAREA" "RESULTADO"
Ejemplo: python3 agregar_log.py 2026-11-25 11:00 11:10 10min "Arreglo X" "OK, funciono"
"""
import csv, sys
from pathlib import Path

if len(sys.argv) != 7:
    sys.exit(__doc__)

fila = sys.argv[1:7]
archivo = Path(__file__).resolve().parent / "registro_actividad.csv"
with archivo.open("a", newline="", encoding="utf-8") as f:
    csv.writer(f).writerow(fila)
print("fila agregada:", fila)
