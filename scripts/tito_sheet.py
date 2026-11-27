#!/usr/bin/env python3
"""
tito_sheet.py — escribe acciones al Google Sheet de horarios de Titi Burger.

Uso:
  tito_sheet.py cambiar_turno --persona NOMBRE --dia DIA --turno TURNO --sucursal SUCURSAL
  tito_sheet.py marcar_falta  --persona NOMBRE --dia DIA --sucursal SUCURSAL
  tito_sheet.py listar_personas --sucursal SUCURSAL

Salida: una línea
  OK: <descripcion>
  ERR: <detalle>
"""

import sys
import argparse
import unicodedata
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = '1fjaLXkP0RuWR7heu5V6qD1y6GvehNeLoRQFWFivz0RM'
SA_PATH  = '/home/tito/.openclaw/credentials/google/service-account.json'
SCOPES   = ['https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive']

SUCURSALES = {
    'a': '🏪 L Montejano',  'l montejano': '🏪 L Montejano',  'montejano': '🏪 L Montejano',
    'b': '🏪 Hacienda del Rio', 'hacienda': '🏪 Hacienda del Rio', 'hacienda del rio': '🏪 Hacienda del Rio',
    'c': '🏪 Montecarlo', 'montecarlo': '🏪 Montecarlo',
    'd': '🏪 Villas del Rey', 'villas': '🏪 Villas del Rey', 'villas del rey': '🏪 Villas del Rey',
    'e': '🏪 San Marcos (FRQ)', 'san marcos': '🏪 San Marcos (FRQ)',
    'cine': '🏪 Cine Curto', 'cine curto': '🏪 Cine Curto', 'curto': '🏪 Cine Curto',
}

DIAS = {
    'lun': 'C', 'lunes': 'C',
    'mar': 'D', 'martes': 'D',
    'mie': 'E', 'mier': 'E', 'miercoles': 'E',
    'jue': 'F', 'jueves': 'F',
    'vie': 'G', 'viernes': 'G',
    'sab': 'H', 'sabado': 'H',
    'dom': 'I', 'domingo': 'I',
}

TURNOS = {'T.M','T.T','T.C','T.P','T.N','DES','FALTA','INC'}

def norm(s: str) -> str:
    s = unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode().lower().strip()
    return ' '.join(s.split())

def open_sheet():
    creds = Credentials.from_service_account_file(SA_PATH, scopes=SCOPES)
    return gspread.authorize(creds).open_by_key(SHEET_ID)

def resolve_sucursal(name: str) -> str:
    key = norm(name)
    if key in SUCURSALES:
        return SUCURSALES[key]
    for k,v in SUCURSALES.items():
        if k in key or key in k:
            return v
    raise ValueError(f"sucursal '{name}' no reconocida")

def resolve_dia(name: str) -> str:
    key = norm(name)
    if key in DIAS:
        return DIAS[key]
    for k,v in DIAS.items():
        if key.startswith(k):
            return v
    raise ValueError(f"dia '{name}' no reconocido")

def resolve_turno(t: str) -> str:
    u = t.strip().upper().replace(' ','')
    if u in TURNOS: return u
    # aceptar mañana/tarde/etc
    n = norm(t)
    if n in ('manana','mañana','m'): return 'T.M'
    if n in ('tarde','t'): return 'T.T'
    if n in ('completo','c'): return 'T.C'
    if n in ('partido','p','medio','medio turno','medio-turno'): return 'T.P'
    if n in ('noche','n'): return 'T.N'
    if n in ('descanso','des','libre'): return 'DES'
    raise ValueError(f"turno '{t}' no reconocido. Validos: T.M T.T T.C T.P T.N DES (o sinonimos: manana/tarde/completo/partido o 'medio turno'/noche/descanso)")

PUESTOS_VALIDOS = ['Encargado(a)','Cajero(a)','Parrillero','Cocinero(a)','Ayudante de Cocina','Personal de Limpieza','Repartidor(a)']

def normalizar_puesto(puesto_input: str, puestos_en_pestana: list[str]) -> str | None:
    """Resuelve el puesto que escribió el usuario contra los que existen en la pestaña. Devuelve el string EXACTO de la pestaña, o None."""
    n = norm(puesto_input)
    sinonimos = {
        'encargado':'encargado','encargada':'encargado','encargado(a)':'encargado',
        'cajero':'cajero','cajera':'cajero','caja':'cajero','cajero(a)':'cajero',
        'parrillero':'parrillero','parrilla':'parrillero','parrilero':'parrillero',
        'cocinero':'cocinero','cocinera':'cocinero','cocina':'cocinero','cocinero(a)':'cocinero',
        'ayudante':'ayudante','ayudante de cocina':'ayudante','ayudita':'ayudante',
        'limpieza':'limpieza','personal de limpieza':'limpieza','aseo':'limpieza',
        'repartidor':'repartidor','repartidora':'repartidor','reparto':'repartidor','motociclista':'repartidor','repartidor(a)':'repartidor',
    }
    clave = sinonimos.get(n)
    if not clave:
        for k,v in sinonimos.items():
            if k.startswith(n) or n.startswith(k):
                clave = v; break
    if not clave:
        return None
    # Buscar el primer puesto en la pestaña cuyo norm() empiece con la clave
    for p in puestos_en_pestana:
        if not p.strip(): continue
        if norm(p).startswith(clave) or clave in norm(p):
            return p
    return None

def get_or_create_persona_row(ws, persona: str, puesto: str | None = None) -> tuple[int, bool]:
    """Devuelve (row, creada). Si la persona no existe, la crea en la fila libre del puesto pedido."""
    nombres = ws.col_values(2)
    puestos = ws.col_values(1)
    target = norm(persona)
    matches = []
    for i, n in enumerate(nombres, 1):
        if i < 5 or not n.strip():
            continue
        if norm(n) == target:
            return (i, False)
        if target in norm(n) or norm(n) in target:
            matches.append((i, n))
    if len(matches) == 1:
        return (matches[0][0], False)
    if len(matches) > 1:
        names = ", ".join(f"'{n}'" for _,n in matches)
        raise ValueError(f"'{persona}' ambiguo. Coincidencias: {names}. Usa el nombre completo.")
    # No existe — necesitamos puesto para colocarlo bien
    if not puesto:
        validos = ", ".join(PUESTOS_VALIDOS)
        raise ValueError(f"PUESTO_REQUERIDO: '{persona}' es empleado nuevo. Pide el puesto al usuario antes de continuar. Validos: {validos}")
    puesto_canonico = normalizar_puesto(puesto, puestos)
    if not puesto_canonico:
        validos = ", ".join(PUESTOS_VALIDOS)
        raise ValueError(f"PUESTO_INVALIDO: '{puesto}' no es un puesto valido en esta pestaña. Validos: {validos}")
    # Buscar primera fila vacía con ese puesto
    for i in range(5, len(puestos) + 1):
        a = puestos[i-1].strip()
        b = nombres[i-1].strip() if i-1 < len(nombres) else ''
        if a == puesto_canonico and not b:
            ws.update_acell(f'B{i}', persona)
            return (i, True)
    # Si no hay fila libre con ese puesto, agregar nueva fila al final con ese puesto
    last_used = 4
    for i in range(5, max(len(puestos), len(nombres)) + 1):
        a = puestos[i-1].strip() if i-1 < len(puestos) else ''
        b = nombres[i-1].strip() if i-1 < len(nombres) else ''
        if a or b:
            last_used = i
    new_row = last_used + 1
    ws.batch_update([
        {'range': f'A{new_row}', 'values': [[puesto_canonico]]},
        {'range': f'B{new_row}', 'values': [[persona]]},
    ], value_input_option='USER_ENTERED')
    return (new_row, True)

def log_bitacora(sh, accion: str, persona: str, sucursal_tab: str, detalle: str):
    """Formato: B=FECHA | C=SUCURSAL | D=EMPLEADO | E=TIPO(detalle). Header esta en R4; los datos empiezan en R5."""
    try:
        ws = sh.worksheet('📓 BITÁCORA')
        suc = sucursal_tab.replace('🏪 ','').replace('(FRQ)','').strip()
        fecha = datetime.now().strftime('%Y-%m-%d %H:%M')
        # Calcular primera fila vacía a partir de R5 leyendo col B
        col_b = ws.col_values(2)
        next_row = max(5, len(col_b) + 1)
        ws.update(values=[[fecha, suc, persona, f"{accion}: {detalle}"]],
                  range_name=f'B{next_row}:E{next_row}',
                  value_input_option='USER_ENTERED')
    except Exception:
        pass

def cmd_cambiar_turno(args):
    sh = open_sheet()
    tab = resolve_sucursal(args.sucursal)
    col = resolve_dia(args.dia)
    turno = resolve_turno(args.turno)
    ws = sh.worksheet(tab)
    puesto = getattr(args, 'puesto', None)
    row, creada = get_or_create_persona_row(ws, args.persona, puesto)
    cell = f"{col}{row}"
    prev = ws.acell(cell).value or '(vacio)'
    ws.update_acell(cell, turno)
    sufijo = " (NUEVO empleado, agregado a la pestaña)" if creada else f" (antes: {prev})"
    detalle = f"{args.persona} · {args.dia} · {turno} · {tab}{sufijo}"
    log_bitacora(sh, 'cambiar_turno', args.persona, tab, f"{args.dia} {turno}{' (NUEVO)' if creada else ''}")
    print(f"OK: {detalle}")

def cmd_marcar_falta(args):
    args.turno = 'FALTA'
    cmd_cambiar_turno(args)

def cmd_agregar_empleado(args):
    sh = open_sheet()
    tab = resolve_sucursal(args.sucursal)
    ws = sh.worksheet(tab)
    puesto = getattr(args, 'puesto', None)
    row, creada = get_or_create_persona_row(ws, args.persona, puesto)
    if creada:
        msg = f"{args.persona} agregado a {tab} (fila {row}"
        if puesto: msg += f", puesto {puesto}"
        msg += ")"
    else:
        msg = f"{args.persona} ya estaba en {tab} (fila {row}), no se duplica"
    log_bitacora(sh, 'agregar_empleado', args.persona, tab, f"puesto={puesto or '—'}")
    print(f"OK: {msg}")

def cmd_listar_personas(args):
    sh = open_sheet()
    tab = resolve_sucursal(args.sucursal)
    ws = sh.worksheet(tab)
    nombres = ws.col_values(2)[4:]
    nombres = [n for n in nombres if n.strip()]
    if not nombres:
        print(f"OK: (vacio) — no hay empleados cargados en {tab}")
    else:
        print(f"OK: {tab}: " + ", ".join(nombres))

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)

    c = sub.add_parser('cambiar_turno')
    c.add_argument('--persona', required=True)
    c.add_argument('--dia', required=True)
    c.add_argument('--turno', required=True)
    c.add_argument('--sucursal', required=True)
    c.add_argument('--puesto', required=False, help='Opcional. Si la persona es nueva, se le pone este puesto.')
    c.set_defaults(fn=cmd_cambiar_turno)

    f = sub.add_parser('marcar_falta')
    f.add_argument('--persona', required=True)
    f.add_argument('--dia', required=True)
    f.add_argument('--sucursal', required=True)
    f.add_argument('--puesto', required=False)
    f.set_defaults(fn=cmd_marcar_falta)

    l = sub.add_parser('listar_personas')
    l.add_argument('--sucursal', required=True)
    l.set_defaults(fn=cmd_listar_personas)

    a = sub.add_parser('agregar_empleado')
    a.add_argument('--persona', required=True)
    a.add_argument('--sucursal', required=True)
    a.add_argument('--puesto', required=False)
    a.set_defaults(fn=cmd_agregar_empleado)

    args = p.parse_args()
    try:
        args.fn(args)
    except Exception as e:
        print(f"ERR: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
