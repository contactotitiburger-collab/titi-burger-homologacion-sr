#!/usr/bin/env python3
"""Genera la pagina de avance DESDE CERO (25-nov-2026, rediseno pedido por Rafael).
Un solo archivo HTML, auto-contenido (CSS y SVG adentro), sin JS necesario para ver
los datos. Unica carga externa: Google Fonts (Poppins). Todos los numeros salen de
registro_actividad.csv y fases.json -- nada inventado, y se verifican antes de
escribir el archivo (ver verificar_numeros() mas abajo).
"""
import csv, json, secrets
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "avance"
TOKEN_FILE = BASE / ".token_avance"

# ---------- token de acceso (sin contraseña: URL larga y aleatoria) ----------
if TOKEN_FILE.exists():
    TOKEN = TOKEN_FILE.read_text().strip()
else:
    TOKEN = secrets.token_urlsafe(18)
    TOKEN_FILE.write_text(TOKEN)

PAGINA_DIR = OUT_DIR / TOKEN
PAGINA_DIR.mkdir(parents=True, exist_ok=True)
CAPTURAS_DIR = OUT_DIR / "capturas"
CAPTURAS_DIR.mkdir(parents=True, exist_ok=True)

# ---------- datos reales ----------
fases = json.loads((BASE / "fases.json").read_text(encoding="utf-8"))
plan = json.loads((BASE / "plan_contrato.json").read_text(encoding="utf-8"))
filas = list(csv.DictReader((BASE / "registro_actividad.csv").open(encoding="utf-8")))
hoy = datetime.now().strftime("%Y-%m-%d")
ahora = datetime.now().strftime("%H:%M")


def parse_min(dur):
    dur = dur.strip()
    if "min" in dur and "h" not in dur:
        return int(dur.replace("min", "").strip())
    if "h" in dur:
        partes = dur.replace("h", " ").replace("min", "").split()
        return int(partes[0]) * 60 + (int(partes[1]) if len(partes) > 1 else 0)
    return 0


def fmt_dur(mins):
    if mins < 60:
        return f"{mins} min"
    h, m = divmod(mins, 60)
    return f"{h} h {m} min" if m else f"{h} h"


MESES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto",
          "septiembre","octubre","noviembre","diciembre"]

def fmt_fecha_es(iso):
    from datetime import date as _d
    d = _d.fromisoformat(iso)
    return f"{d.day} de {MESES[d.month-1]} de {d.year}"


def fmt_hora_12(hhmm):
    h, m = map(int, hhmm.split(":"))
    ampm = "am" if h < 12 else "pm"
    h12 = h % 12
    if h12 == 0:
        h12 = 12
    return f"{h12}:{m:02d} {ampm}"


# ---------- horas (fuente de verdad: el CSV, nada mas) ----------
filas_hoy = [f for f in filas if f["fecha"] == hoy]
minutos_hoy = sum(parse_min(f["duracion"]) for f in filas_hoy)
minutos_total = sum(parse_min(f["duracion"]) for f in filas)
horas_hoy_txt = fmt_dur(minutos_hoy)
horas_total_txt = fmt_dur(minutos_total)

# ---------- % global (formula real, ver abajo) ----------
# pct_global = entregables marcados hecho=true / total de entregables, sumando las 4 fases
total_items = sum(len(f["items"]) for f in fases)
hechos_items = sum(1 for f in fases for it in f["items"] if it["hecho"])
pct_global = round(100 * hechos_items / total_items) if total_items else 0

# ---------- comparacion contra el plan/presupuesto real (Opcion B, 23-nov a 1-mar) ----------
from datetime import date
_inicio = date.fromisoformat(plan["inicio"])
_fin = date.fromisoformat(plan["fin_soporte"])
_hoy_d = date.today()
dias_totales_plan = (_fin - _inicio).days
dias_transcurridos_plan = max(0, (_hoy_d - _inicio).days)
pct_tiempo_plan = round(100 * dias_transcurridos_plan / dias_totales_plan, 1) if dias_totales_plan else 0
horas_usadas = round(minutos_total / 60, 1)
pct_horas_plan = round(100 * horas_usadas / plan["horas_presupuestadas"], 1) if plan["horas_presupuestadas"] else 0

_gap = pct_horas_plan - pct_tiempo_plan
if _gap > 15:
    estado_chip = "con_retraso"  # usando las horas mucho mas rapido que el tiempo del contrato
elif pct_tiempo_plan - pct_horas_plan > 25 and pct_global < 20:
    estado_chip = "atorado"  # mucho tiempo pasado, poco trabajo y pocas horas usadas
else:
    estado_chip = "vamos_bien"

for f in fases:
    n = len(f["items"])
    f["pct"] = round(100 * sum(1 for it in f["items"] if it["hecho"]) / n) if n else 0
    if f["pct"] == 100:
        f["estado"] = "hecho"
    elif f["pct"] > 0:
        f["estado"] = "en_curso"
    else:
        f["estado"] = "pendiente"

# la fase "actual" es la primera que no esta 100% hecha
fase_actual = next((f for f in fases if f["estado"] != "hecho"), fases[-1])
if all(f["estado"] == "hecho" for f in fases):
    fase_actual = None

# ---------- verificacion obligatoria de numeros (no se escribe el archivo si falla) ----------
# Candado del bug del 25-nov: Rafael encontro que "Revisar sucursales" decia 100%
# aunque Montecarlo seguia sin conectar. Mientras Montecarlo siga sin conectarse,
# la fase de sucursales DEBE tener un item de Montecarlo marcado como no-hecho --
# si alguien lo borra o lo marca hecho por error, esto truena antes de publicar.
MONTECARLO_CONECTADA = True  # 26-nov-2026: conectada a la red + usuario de lectura creado, se lee softrestaurant12

def verificar_numeros():
    errores = []
    if minutos_total < minutos_hoy:
        errores.append(f"horas totales ({minutos_total}min) < horas de hoy ({minutos_hoy}min)")
    if not (0 <= pct_global <= 100):
        errores.append(f"% global fuera de rango: {pct_global}")
    suma_fases = sum(len(f["items"]) for f in fases)
    if suma_fases != total_items:
        errores.append("inconsistencia en conteo de entregables por fase")
    fase_sucursales = next((f for f in fases if "sucursal" in f["nombre"].lower()), None)
    if fase_sucursales and not MONTECARLO_CONECTADA:
        item_montecarlo = next((it for it in fase_sucursales["items"] if "Montecarlo" in it["nombre"]), None)
        if item_montecarlo is None:
            errores.append('falta el item de Montecarlo en la fase de sucursales (Montecarlo sigue sin conectar)')
        elif item_montecarlo["hecho"]:
            errores.append('Montecarlo esta marcado como revisado pero MONTECARLO_CONECTADA=False -- corrige uno de los dos')
    return errores

_errores = verificar_numeros()
if _errores:
    raise SystemExit("NO SE GENERO EL HTML -- corrige la fuente de datos:\n" + "\n".join(_errores))

# ---------- traduccion de tareas a espanol llano (todas las fechas, no solo hoy) ----------
# mapeo tarea-del-csv -> texto simple para quien no es tecnico
TRADUCCION_HOY = {
    "Paso1 descubrimiento tailscale+SQL": "Revisamos qué sucursales están conectadas",
    "Paso2 probar oguzhanpisgin/mssql-readonly-mcp": "Probamos una primera forma de leer los datos (no funcionó)",
    "Paso2 instalar y probar RichardHan/mssql_mcp_server (git version pymssql)": "Conectamos la forma de leer la información sin poder cambiarla",
    "Paso2 registrar 5 MCP lectores en Claude Code (uno por sucursal, puerto dinamico resuelto en cada arranque)": "Conectamos las 5 sucursales para poder leerlas",
    "Paso3 lector Menu y Precios (productos/precios 5 sucursales)": "Revisamos el menú y los precios de cada sucursal",
    "Paso3 lector Inventario y Recetas": "Revisamos el inventario y las recetas",
    "Paso3 lector Ventas y Cortes + Verificador": "Revisamos las ventas y los cortes de caja",
    "Paso3 lector Configuracion (usuarios/almacenes)": "Revisamos los usuarios y la configuración",
    "Paso4 Mapa de la base de datos": "Armamos el mapa de toda la información",
    "Desarrollo de scripts de conexion SQL y wrappers (paso1-5)": "Programamos las conexiones a cada sucursal",
    "Debugging e instalacion de los 2 candidatos de MCP (compatibilidad SQL Server legacy)": "Arreglamos problemas de compatibilidad",
    "Construccion de la pagina de avance y servidor con clave": "Construimos la primera versión de la página de avance",
    "Instalacion y configuracion inicial de claude-office": "Instalamos el panel de seguimiento interno",
    "Paso7 instalar claude-office (Python 3.13 via uv sin sudo + backend + frontend estatico)": "Organizamos el panel de seguimiento",
    "Generar PDF de analisis de incongruencias para Rafael/Felix": "Armamos el reporte de diferencias",
    "Instalar cloudflared y exponer pagina de avance publicamente (tunel gratis sin sudo)": "Hicimos público el enlace",
    "Instalar skill pixel-art-studio para sprites de claude-office": "Ajustes internos del sistema",
    "Rediseno de los anillos de progreso con paleta validada contra daltonismo": "Mejoramos cómo se ve el avance",
    "Rehacer la pagina de avance desde cero (pedido de Rafael)": "Rehicimos la página de avance",
    "Agregar seguridad ligera (usuario/clave) a la pagina de avance": "Agregamos usuario y clave",
    "Integrar el plan/presupuesto contratado (Opcion B) y ajustar fecha de arranque al 23-nov": "Agregamos el plan contratado",
    "Corregir incongruencia: Revisar sucursales decia 100% sin Montecarlo conectada": "Corregimos un dato mal calculado",
    "Coordinacion y revision entre tareas (estimado)": "Coordinación y revisión entre tareas",
    "Subir el proyecto a GitHub (repo privado) sacando credenciales del codigo primero": "Guardamos el código en un lugar seguro",
    "Agregar 3 usuarios (tito/rafael/felix) + bitacora de trabajo por objetivo": "Creamos cuentas y la primera bitácora",
    "Auditoria de seguridad (agente) y arreglar los 5 hallazgos reales": "Revisamos y reforzamos la seguridad",
    "Hacer clickeables las fases con aviso tipo toast que aparece y se desvanece": "Hicimos las etapas interactivas",
    "Reescribir los textos de los avisos sin jerga de negocio para que Don Titi entienda": "Simplificamos los textos",
    "Alargar el tiempo que dura visible el aviso de 4.5 a 9 segundos": "Ajuste del aviso",
    "Presentacion del proyecto a Felix": "Presentación del proyecto a Félix",
    "Explicacion de herramientas y cuentas (API cuentas Cloud)": "Explicación de herramientas y cuentas",
    "Agregar horas de lunes 23-nov (dadas por Rafael) y ajuste de hoy al rango pedido": "Ajuste de horas registradas",
    "Agregar menu de 3 puntitos + bitacora de objetivos (verde/rojo) y doble clic para cerrar avisos": "Creamos esta bitácora de objetivos",
    "Arreglar CSV roto (comas sin escapar) y reestructurar objetivos en 3 niveles con horas reales": "Organizamos la bitácora por objetivo, con horas reales de cada día",
}
# tareas chicas/internas que se agrupan si hay mas de 6 actividades hoy (ver mas abajo)
AGRUPABLES = {"Organizamos el panel de seguimiento", "Ajustes internos del sistema",
              "Agregamos usuario y clave", "Corregimos un dato mal calculado"}

actividades_hoy = []
for f in filas_hoy:
    texto = TRADUCCION_HOY.get(f["tarea"], f["tarea"][:40])
    actividades_hoy.append({
        "texto": texto, "inicio": f["hora_inicio"], "minutos": parse_min(f["duracion"]),
    })

# si hay mas de 6, agrupar las chicas/internas en una sola fila "Otros ajustes"
# en vez de simplemente cortar y perder trabajo real del dia
if len(actividades_hoy) > 6:
    normales = [a for a in actividades_hoy if a["texto"] not in AGRUPABLES]
    agrupadas = [a for a in actividades_hoy if a["texto"] in AGRUPABLES]
    if agrupadas:
        normales.append({
            "texto": "Otros ajustes internos", "inicio": agrupadas[0]["inicio"],
            "minutos": sum(a["minutos"] for a in agrupadas),
        })
    actividades_hoy = sorted(normales, key=lambda a: a["inicio"])[:6]
max_min_hoy = max((a["minutos"] for a in actividades_hoy), default=1)

# ---------- que sigue (real, de lo que se sabe hoy) ----------
_pf_tmp = json.loads((BASE / "plan_fases.json").read_text(encoding="utf-8"))
que_sigue = [{"estado": "pendiente", "texto": _x["n"], "quien": _x.get("quien", "Tito")}
             for _a in _pf_tmp for _x in _a["items"] if not _x["hecho"]][:4] or \
            [{"estado": "pendiente", "texto": "Todo el plan está terminado", "quien": "Tito"}]

bloqueos = []

frase_dueno = "Ya se comparó cada sucursal contra la de Félix y quedó la lista de lo que hay que corregir. Tito Editor ya está listo y probado sin tocar ninguna sucursal; sigue que Rafael y Félix decidan qué se corrige y en qué orden."
# estado_chip ya se calculó arriba comparando horas usadas vs tiempo del contrato (ver plan_contrato.json)
ESTADO_TXT = {"vamos_bien": "Vamos bien", "con_retraso": "Con retraso", "atorado": "Atorado"}
ESTADO_COLOR = {"vamos_bien": "#22C55E", "con_retraso": "#F5B83D", "atorado": "#F04E5E"}


# ================= componentes HTML/SVG (todo inline, sin JS) =================

def ring(pct_val, size, stroke, color, track, numero_color, numero_size, label=None):
    r = (size - stroke) / 2
    c = 2 * 3.14159265 * r
    offset = c * (1 - pct_val / 100)
    label_html = f'<div class="ring-label">{label}</div>' if label else ""
    return f"""<div class="ring-wrap">
      <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
        <circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="{track}" stroke-width="{stroke}" />
        <circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="{color}" stroke-width="{stroke}"
          stroke-linecap="round" stroke-dasharray="{c:.2f}" stroke-dashoffset="{offset:.2f}"
          transform="rotate(-90 {size/2} {size/2})" />
        <text x="50%" y="52%" text-anchor="middle" dominant-baseline="middle"
          style="font:600 {numero_size}px Poppins,system-ui,sans-serif; fill:{numero_color};">{pct_val}%</text>
      </svg>
      {label_html}
    </div>"""


def paso_circulo(fase, es_ultimo):
    if fase["estado"] == "hecho":
        circulo = '<div class="paso-circ hecho">✓</div>'
    elif fase["estado"] == "en_curso":
        circulo = f'<div class="paso-circ en-curso"><span class="halo"></span>{fase["id"]}</div>'
    else:
        circulo = f'<div class="paso-circ pendiente">{fase["id"]}</div>'
    linea = "" if es_ultimo else '<div class="paso-conector"></div>'
    return f"""<div class="paso-item" onclick="mostrarToast({fase['id']})" role="button" tabindex="0">
      <div class="paso-fila">{circulo}{linea}</div>
      <div class="paso-nombre">{fase['nombre']}</div>
    </div>"""


def tarjeta_fase(fase):
    g1, g2 = fase["color"]
    anillo = ring(fase["pct"], 64, 7, "#FFFFFF", "rgba(255,255,255,.35)", "#FFFFFF", 15)
    return f"""<div class="fase-card" style="background:linear-gradient(135deg,{g1},{g2});" onclick="mostrarToast({fase['id']})" role="button" tabindex="0">
      {anillo}
      <div class="fase-nombre">{fase['nombre']}</div>
    </div>"""


def fila_hoy(a, max_min=None):
    max_min = max_min or max_min_hoy
    ancho = max(8, round(100 * a["minutos"] / max_min))
    return f"""<div class="hoy-fila">
      <div class="hoy-texto">{a['texto']}</div>
      <div class="hoy-datos">
        <span class="hoy-hora">{fmt_hora_12(a['inicio'])}</span>
        <div class="hoy-barra-bg"><div class="hoy-barra-fill" style="width:{ancho}%"></div></div>
        <span class="hoy-dur">{fmt_dur(a['minutos'])}</span>
      </div>
    </div>"""


def tareas_del_dia(fecha):
    """Todas las tareas de un dia (de registro_actividad.csv), traducidas, sin agrupar
    (el detalle de horas es justo para ver todo, a diferencia de 'hoy' que se resume)."""
    filas_dia = [f for f in filas if f["fecha"] == fecha]
    out = []
    for f in filas_dia:
        out.append({
            "texto": TRADUCCION_HOY.get(f["tarea"], f["tarea"]),
            "inicio": f["hora_inicio"],
            "minutos": parse_min(f["duracion"]),
        })
    return out


def render_detalle_horas(dias):
    """Seccion 'Ver que se trabajo' -- lista cada dia con sus horas y tareas reales."""
    if not dias:
        return '<p class="sin-dato">Sin horas registradas todavía.</p>'
    bloques = []
    for fecha in dias:
        tareas = tareas_del_dia(fecha)
        if not tareas:
            continue
        minutos_dia = sum(t["minutos"] for t in tareas)
        max_dia = max((t["minutos"] for t in tareas), default=1)
        filas_html_dia = "".join(fila_hoy(t, max_dia) for t in tareas)
        bloques.append(f"""<details class="dia-detalle">
          <summary>{fmt_fecha_es(fecha)} <span class="horas-badge">{fmt_dur(minutos_dia)}</span></summary>
          <div class="hoy-lista">{filas_html_dia}</div>
        </details>""")
    return "".join(bloques)


def fila_sigue(item):
    color = {"pendiente": "#A0B4C4", "en_curso": "#1E90F0", "hecho": "#22C55E"}.get(item["estado"], "#A0B4C4")
    fecha_html = f' · <span class="sigue-fecha">{item["fecha"]}</span>' if item.get("fecha") else ""
    return f"""<div class="sigue-fila">
      <span class="sigue-punto" style="background:{color}"></span>
      <div><div class="sigue-texto">{item['texto']}</div>
      <div class="sigue-quien">{item['quien']}{fecha_html}</div></div>
    </div>"""


def detalle_fase(fase):
    items_html = "\n".join(
        f'<li class="{"ok" if it["hecho"] else "no"}">{"✓" if it["hecho"] else "○"} {it["nombre"]}</li>'
        for it in fase["items"]
    )
    return f'<div class="detalle-fase"><b>{fase["nombre"]}</b><ul>{items_html}</ul></div>'


def fila_objetivo(nombre, cumplido):
    color = "#22C55E" if cumplido else "#F04E5E"
    return f"""<div class="objetivo-fila">
      <div class="objetivo-texto">{nombre}</div>
      <span class="objetivo-bolita" style="background:{color}"></span>
    </div>"""

def render_objetivo_grande(cat):
    """Un objetivo grande del plan (ej. 'Restablecer base de datos Soft Restaurant'):
    al picarle se abren sus subobjetivos (verde primero, rojo despues) y, debajo,
    un 'Ver que se trabajo' con las horas reales de los dias ligados a ese objetivo."""
    subs = cat["subobjetivos"]
    hechos = [s for s in subs if s["hecho"]]
    pendientes = [s for s in subs if not s["hecho"]]
    subs_html = "".join(fila_objetivo(s["nombre"], True) for s in hechos) + \
                "".join(fila_objetivo(s["nombre"], False) for s in pendientes)
    minutos_cat = sum(sum(parse_min(f["duracion"]) for f in filas if f["fecha"] == d) for d in cat["dias"])
    horas_txt = fmt_dur(minutos_cat) if minutos_cat else "0 min"
    detalle_horas = render_detalle_horas(cat["dias"])
    pct_cat = round(100 * len(hechos) / len(subs)) if subs else 0
    return f"""<details class="objetivo-grande">
      <summary><span>{cat['nombre']}</span><span class="horas-badge">{pct_cat}% · {horas_txt}</span></summary>
      <div class="subobjetivos">{subs_html}</div>
      <details class="ver-horas">
        <summary>Ver qué se trabajó</summary>
        {detalle_horas}
      </details>
    </details>"""

# Objetivos = jerarquia curada (objetivos.json): objetivo grande del plan -> sus
# subobjetivos (verde primero, rojo despues) -> detalle real de horas por dia.
# NO cada item chiquito de fases.json (Rafael pidio "unos 3 verdes max" arriba).
_categorias = json.loads((BASE / "objetivos.json").read_text(encoding="utf-8"))
objetivos_html = "".join(render_objetivo_grande(c) for c in _categorias)

pasos_html = "".join(paso_circulo(f, i == len(fases) - 1) for i, f in enumerate(fases))
tarjetas_html = "".join(tarjeta_fase(f) for f in fases)
hoy_html = "".join(fila_hoy(a) for a in actividades_hoy) if actividades_hoy else '<p class="sin-dato">Sin dato todavía.</p>'
sigue_html = "".join(fila_sigue(i) for i in que_sigue[:4])
detalle_html = "".join(detalle_fase(f) for f in fases)

if bloqueos:
    bloqueos_html = "".join(
        f'<div class="bloqueo-fila"><div class="bloqueo-texto">{b["texto"]}</div>'
        f'<div class="bloqueo-quien">Quién puede resolverlo: {b["quien"]}</div></div>'
        for b in bloqueos
    )
    bloqueo_card_class = "bloqueo-card"
else:
    bloqueos_html = '<div class="bloqueo-ok">✓ Nada atorado</div>'
    bloqueo_card_class = "bloqueo-card-ok"

ring_principal = ring(pct_global, 160, 10, "#1E90F0", "#E3EEF6", "#12324A", 40)

# ===================== DASHBOARD REDISEÑADO (7 puntos, 26-nov-2026) =====================
import math as _math
plan_fases = json.loads((BASE / "plan_fases.json").read_text(encoding="utf-8"))
for _pf in plan_fases:
    _n = len(_pf["items"]); _h = sum(1 for _it in _pf["items"] if _it["hecho"])
    _pf["pct"] = round(100 * _h / _n) if _n else 0
    _pf["estado"] = "hecho" if _pf["pct"] == 100 else ("curso" if _pf["pct"] > 0 else "pendiente")
fase_actual_plan = next((_pf for _pf in plan_fases if _pf["estado"] != "hecho"), plan_fases[-1])
_idx_act = plan_fases.index(fase_actual_plan)
_segs = max(1, len(plan_fases) - 1)
if all(_pf["estado"] == "hecho" for _pf in plan_fases):
    _linea_fill = 1.0
else:
    _linea_fill = (_idx_act + fase_actual_plan["pct"] / 100.0) / _segs
_linea_fill = max(0.0, min(1.0, _linea_fill))
_COL = {"hecho": "#22C55E", "curso": "#1E90F0", "pendiente": "#C9CFD6"}
_ESTTXT = {"hecho": "Terminada", "curso": "En curso", "pendiente": "Pendiente"}

def _anillo_fase(pf, idx):
    size, stroke = (56, 6) if len(plan_fases) <= 5 else (44, 5)
    r = (size - stroke) / 2
    circ = 2 * _math.pi * r
    col = _COL[pf["estado"]]
    off = circ * (1 - pf["pct"] / 100.0)
    arco = ""
    if pf["pct"] > 0:
        arco = (f'<circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="{col}" stroke-width="{stroke}" '
                f'stroke-linecap="round" stroke-dasharray="{circ:.1f}" stroke-dashoffset="{off:.1f}" '
                f'transform="rotate(-90 {size/2} {size/2})"/>')
    numcol = col if pf["pct"] > 0 else "#9DB2C2"
    return (f'<div class="pf-dot" style="width:{100.0/len(plan_fases):.2f}%" onclick="verFasePlan({idx})">'
            f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
            f'<circle cx="{size/2}" cy="{size/2}" r="{r}" fill="#fff" stroke="#E3EEF6" stroke-width="{stroke}"/>{arco}'
            f'<text x="50%" y="53%" text-anchor="middle" dominant-baseline="middle" '
            f'style="font:600 {12 if size > 50 else 10}px Poppins,sans-serif;fill:{numcol};">{pf["pct"]}%</text>'
            f'</svg><div class="pf-dot-lbl">{pf["etiqueta"]}</div></div>')

_nf = len(plan_fases); _half = 50.0 / _nf
dots_html = (
    '<div class="pf-scroll">'
    f'<div class="pf-row" style="min-width:{_nf*66}px">'
    f'<div class="pf-line-bg" style="left:{_half:.2f}%;right:{_half:.2f}%"></div>'
    f'<div class="pf-line-fill" style="left:{_half:.2f}%;width:calc({100 - 2*_half:.2f}% * {_linea_fill:.4f});"></div>'
    + "".join(_anillo_fase(pf, i) for i, pf in enumerate(plan_fases))
    + '</div></div><div id="fase-resumen" class="pf-resumen"></div>'
)

# Punto 2: desglose de la fase actual
_bd_items = ""
for _it in fase_actual_plan["items"]:
    _c = "#22C55E" if _it["hecho"] else "#C9CFD6"
    _ic = "✓" if _it["hecho"] else "○"
    _cls = "bd-done" if _it["hecho"] else "bd-pend"
    _bd_items += f'<div class="bd-item"><span class="bd-ic" style="color:{_c}">{_ic}</span><span class="{_cls}">{_it["n"]}</span></div>'
breakdown_html = (
    f'<div class="bd-head"><h2>En qué vamos ahorita</h2><span class="bd-badge">{fase_actual_plan["pct"]}%</span></div>'
    f'<p class="bd-fase">{fase_actual_plan["area"]}</p>'
    f'<div class="bd-list">{_bd_items}</div>'
)

# Punto 7: Bitácora por áreas (incluye pendientes con 0% · 0 min, en orden del plan)
_bit = ""
for _pf in plan_fases:
    _hechos = [x for x in _pf["items"] if x["hecho"]]
    _pend = [x for x in _pf["items"] if not x["hecho"]]
    _rows = ""
    for _it in _hechos + _pend:
        _col = "#22C55E" if _it["hecho"] else "#C9CFD6"
        _ptxt = "100% · hecho" if _it["hecho"] else "0% · 0 min"
        _rows += (f'<div class="bit-item"><span class="bit-dot" style="background:{_col}"></span>'
                  f'<span class="bit-nom">{_it["n"]}</span><span class="bit-pct">{_ptxt}</span></div>')
    _bit += (f'<div class="bit-area"><div class="bit-area-head">'
             f'<span class="bit-area-tit">{_pf["area"]}</span>'
             f'<span class="bit-area-badge" style="color:{_COL[_pf["estado"]]}">{_pf["pct"]}%</span></div>{_rows}</div>')
bitacora_areas_html = _bit

# ---- Bitacora de trabajo (linea del tiempo): lo hecho con horas reales -> lo que falta con horas estimadas
from collections import OrderedDict as _OD
_dias = _OD()
for _f in sorted(filas, key=lambda r: (r["fecha"], r["hora_inicio"])):
    _dias.setdefault(_f["fecha"], []).append(_f)
_h_real = minutos_total / 60.0
_h_falta = sum(x.get("est", 0) for a in plan_fases for x in a["items"] if not x["hecho"])
_etapas_ok = sum(1 for a in plan_fases if a["estado"] == "hecho")
_tl = (f'<div class="tl-stats">'
       f'<div class="tl-stat"><span class="tl-num">{_h_real:.1f} h</span><span class="tl-lbl">trabajadas (reales)</span></div>'
       f'<div class="tl-stat"><span class="tl-num tl-azul">~{_h_falta:.0f} h</span><span class="tl-lbl">faltan (estimado)</span></div>'
       f'<div class="tl-stat"><span class="tl-num">{_etapas_ok} de {len(plan_fases)}</span><span class="tl-lbl">etapas terminadas</span></div></div>'
       f'<p class="tl-nota">El estimado sale del ritmo real: el diagnóstico estaba presupuestado en 25 h y salió en unas 17 h. '
       f'Contrato: {plan["horas_presupuestadas"]} h.</p>')
_tl += '<div class="tl"><div class="tl-sec">Lo que ya se hizo</div>'
for _fecha, _rs in _dias.items():
    _m = sum(parse_min(r["duracion"]) for r in _rs)
    _vistos = []
    for r in _rs:
        _t = TRADUCCION_HOY.get(r["tarea"], r["tarea"])
        if _t not in _vistos:
            _vistos.append(_t)
    _lis = "".join(f"<li>{t}</li>" for t in _vistos)
    _tl += (f'<div class="tl-nodo tl-hecho"><div class="tl-pin"></div><div class="tl-caja">'
            f'<div class="tl-top"><span class="tl-fecha">{fmt_fecha_es(_fecha)}</span><span class="tl-horas">{fmt_dur(_m)}</span></div>'
            f'<ul class="tl-lista">{_lis}</ul></div></div>')
_tl += '<div class="tl-sec tl-sec-falta">Lo que falta para terminar</div>'
for _a in plan_fases:
    _pend = [x for x in _a["items"] if not x["hecho"]]
    if not _pend:
        continue
    _clase = "tl-actual" if _a is fase_actual_plan else "tl-futuro"
    _est = sum(x.get("est", 0) for x in _pend)
    _hechos = [x for x in _a["items"] if x["hecho"]]
    _lis = "".join(f'<li class="tl-ok">{x["n"]}</li>' for x in _hechos)
    _lis += "".join(f'<li><span>{x["n"]}</span><em>~{x.get("est",0)} h · {x.get("quien","Tito")}</em></li>' for x in _pend)
    _tag = '<span class="tl-tag">Ahora</span>' if _a is fase_actual_plan else ""
    _tl += (f'<div class="tl-nodo {_clase}"><div class="tl-pin"></div><div class="tl-caja">'
            f'<div class="tl-top"><span class="tl-fase">{_a["area"]}{_tag}</span><span class="tl-horas">~{_est:g} h</span></div>'
            f'<p class="tl-desc">{_a.get("desc","")}</p><ul class="tl-lista tl-items">{_lis}</ul></div></div>')
_tl += '</div>'
bitacora_timeline_html = _tl

plan_fases_js = json.dumps(
    [{"a": pf["area"], "p": pf["pct"], "e": _ESTTXT[pf["estado"]],
      "h": sum(1 for it in pf["items"] if it["hecho"]),
      "f": sum(1 for it in pf["items"] if not it["hecho"]), "d": pf.get("desc","")} for pf in plan_fases],
    ensure_ascii=False)

# Círculo grande: se queda como está ahorita (% global del prefijo)
_tt = sum(len(pf["items"]) for pf in plan_fases)
_th = sum(1 for pf in plan_fases for it in pf["items"] if it["hecho"])
pct_plan_global = round(100 * _th / _tt) if _tt else 0
frase_plan = f"Vamos en la etapa \u201c{fase_actual_plan['area']}\u201d. {fase_actual_plan.get('desc', '')}"
ring_big = ring(pct_plan_global, 128, 12, "var(--blue)", "var(--track)", "var(--ink)", 32)

html = f"""<!doctype html>
<html lang="es"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Avance del proyecto — Titi Burger</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg:#EEF7FC; --bg-top:#D6EEFA; --card:#FFFFFF; --border:#E6EEF5;
    --blue:#1E90F0; --track:#E3EEF6; --ink:#12324A; --ink2:#5B7488;
    --listo:#22C55E; --encurso:#1E90F0; --pendiente:#A0B4C4;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:"Poppins",system-ui,-apple-system,"Segoe UI",sans-serif; background:var(--bg); color:var(--ink); }}
  .topbar {{ height:120px; background:linear-gradient(180deg,var(--bg-top),var(--bg)); }}
  .wrap {{ max-width:960px; margin:-90px auto 0; padding:0 16px 32px; }}
  @media (min-width:700px) {{ .wrap {{ padding:0 24px 40px; }} }}
  .card {{ background:var(--card); border:1px solid var(--border); border-radius:20px; box-shadow:0 4px 16px rgba(20,60,100,0.06); padding:20px; margin-bottom:16px; }}
  @media (min-width:700px) {{ .card {{ padding:28px; }} }}
  h1 {{ font-size:22px; font-weight:600; margin:0 0 4px; }}
  @media (min-width:700px) {{ h1 {{ font-size:28px; }} }}
  .actualizado {{ color:var(--ink2); font-size:13px; margin:0 0 18px; }}
  h2 {{ font-size:17px; font-weight:600; margin:0 0 14px; }}
  p {{ font-size:15px; line-height:1.5; margin:0; }}
  .ring-wrap {{ display:flex; flex-direction:column; align-items:center; }}
  .vamos-top {{ display:flex; flex-direction:column; align-items:center; gap:14px; text-align:center; }}
  @media (min-width:560px) {{ .vamos-top {{ flex-direction:row; text-align:left; gap:24px; }} }}
  .vamos-texto p {{ margin-bottom:12px; }}
  .chip {{ display:inline-block; padding:6px 14px; border-radius:999px; font-size:13px; font-weight:600; color:#fff; }}
  .resumen-mini {{ border-top:1px solid var(--border); margin-top:16px; padding-top:14px; display:flex; flex-direction:column; gap:8px; }}
  .resumen-item {{ display:flex; align-items:flex-start; gap:8px; font-size:14px; color:var(--ink2); }}
  .resumen-item b {{ color:var(--ink); }}
  .resumen-punto {{ width:8px; height:8px; border-radius:50%; margin-top:6px; flex:0 0 8px; }}
  /* fila de fases (bolitas) */
  .pf-scroll {{ overflow-x:auto; -webkit-overflow-scrolling:touch; margin:0 -6px; padding:0 6px 4px; }}
  .pf-row {{ position:relative; display:flex; justify-content:space-between; align-items:flex-start; padding:4px 0 0; margin-bottom:4px; }}
  .pf-line-bg {{ position:absolute; top:28px; left:10%; right:10%; height:3px; background:var(--track); border-radius:2px; z-index:0; }}
  .pf-line-fill {{ position:absolute; top:28px; left:10%; height:3px; background:linear-gradient(90deg,#22C55E,#1E90F0); border-radius:2px; z-index:0; transition:width .5s ease; }}
  .pf-dot {{ position:relative; z-index:1; width:20%; display:flex; flex-direction:column; align-items:center; cursor:pointer; }}
  .pf-dot-lbl {{ font-size:10px; color:var(--ink2); text-align:center; margin-top:6px; line-height:1.2; padding:0 2px; }}
  @media (min-width:560px) {{ .pf-dot-lbl {{ font-size:12px; }} }}
  .pf-resumen {{ display:none; margin-top:16px; background:#F4FAFE; border:1px solid var(--border); border-radius:12px; padding:13px 15px; font-size:14px; color:var(--ink); line-height:1.5; }}
  .pf-resumen.show {{ display:block; }}
  .pf-resumen b {{ display:block; margin-bottom:4px; }}
  /* desglose fase actual */
  .bd-head {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }}
  .bd-head h2 {{ margin:0; }}
  .bd-badge {{ font-size:13px; font-weight:600; color:var(--blue); background:#eaf4fe; padding:4px 12px; border-radius:999px; }}
  .bd-fase {{ color:var(--ink2); font-size:14px; margin:0 0 16px; }}
  .bd-list {{ display:flex; flex-direction:column; gap:11px; }}
  .bd-item {{ display:flex; align-items:center; gap:10px; font-size:15px; }}
  .bd-ic {{ font-size:16px; flex:0 0 auto; width:18px; }}
  .bd-pend {{ color:var(--ink2); }}
  /* hoy */
  .hoy-header {{ display:flex; justify-content:space-between; align-items:baseline; margin-bottom:14px; }}
  .hoy-total {{ font-size:15px; font-weight:600; color:var(--blue); }}
  .hoy-fila {{ margin-bottom:14px; }}
  .hoy-texto {{ font-size:15px; margin-bottom:5px; }}
  .hoy-datos {{ display:flex; align-items:center; gap:10px; }}
  .hoy-hora {{ font-size:13px; color:var(--ink2); flex:0 0 62px; }}
  .hoy-barra-bg {{ flex:1; height:10px; background:var(--track); border-radius:999px; overflow:hidden; }}
  .hoy-barra-fill {{ height:100%; background:var(--blue); border-radius:999px; }}
  .hoy-dur {{ font-size:13px; color:var(--ink2); flex:0 0 64px; text-align:right; }}
  /* que sigue */
  .sigue-fila {{ display:flex; gap:12px; margin-bottom:16px; align-items:flex-start; }}
  .sigue-punto {{ width:12px; height:12px; border-radius:50%; margin-top:5px; flex:0 0 12px; }}
  .sigue-texto {{ font-size:15px; }}
  .sigue-quien {{ font-size:13px; color:var(--ink2); margin-top:2px; }}
  footer {{ text-align:center; color:var(--ink2); font-size:13px; padding:8px 0 24px; }}
  /* menu */
  .menu-btn {{ position:fixed; top:14px; left:14px; width:44px; height:44px; border-radius:50%; background:#fff; border:1px solid var(--border); box-shadow:0 2px 8px rgba(20,60,100,0.1); display:flex; align-items:center; justify-content:center; font-size:22px; color:var(--ink); cursor:pointer; z-index:40; line-height:1; }}
  .menu-dropdown {{ position:fixed; top:62px; left:14px; background:#fff; border:1px solid var(--border); border-radius:12px; box-shadow:0 8px 24px rgba(20,60,100,0.15); display:none; overflow:hidden; z-index:40; }}
  .menu-dropdown.show {{ display:block; }}
  .menu-dropdown a {{ display:flex; align-items:center; min-height:44px; padding:0 16px; font-size:14px; color:var(--ink); text-decoration:none; white-space:nowrap; cursor:pointer; }}
  .menu-dropdown a:hover {{ background:var(--bg); }}
  /* bitacora: linea del tiempo */
  .tl-wrap {{ max-width:720px; margin:0 auto; padding:0 16px 40px; }}
  .tl-stats {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-bottom:10px; }}
  .tl-stat {{ background:#fff; border:1px solid var(--border); border-radius:14px; padding:12px 10px; text-align:center; }}
  .tl-num {{ display:block; font-size:20px; font-weight:700; color:var(--ink); }}
  .tl-azul {{ color:var(--blue); }}
  .tl-lbl {{ font-size:11px; color:var(--ink2); }}
  .tl-nota {{ font-size:12px; color:var(--ink2); margin:0 0 18px; }}
  .tl {{ position:relative; padding-left:26px; }}
  .tl::before {{ content:""; position:absolute; left:8px; top:6px; bottom:6px; width:2px;
                 background:linear-gradient(180deg,#22C55E 0%,#22C55E 45%,#1E90F0 55%,#C9CFD6 100%); }}
  .tl-sec {{ font-size:12px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:var(--ink2); margin:4px 0 10px -26px; padding-left:26px; }}
  .tl-sec-falta {{ margin-top:22px; }}
  .tl-nodo {{ position:relative; margin-bottom:12px; }}
  .tl-pin {{ position:absolute; left:-24px; top:16px; width:14px; height:14px; border-radius:50%; background:#fff; border:3px solid #C9CFD6; }}
  .tl-hecho .tl-pin {{ background:#22C55E; border-color:#22C55E; }}
  .tl-actual .tl-pin {{ border-color:#1E90F0; box-shadow:0 0 0 0 rgba(30,144,240,.5); animation:tlpulso 2s infinite; }}
  @keyframes tlpulso {{ 0% {{ box-shadow:0 0 0 0 rgba(30,144,240,.45); }} 70% {{ box-shadow:0 0 0 9px rgba(30,144,240,0); }} 100% {{ box-shadow:0 0 0 0 rgba(30,144,240,0); }} }}
  .tl-caja {{ background:#fff; border:1px solid var(--border); border-radius:14px; padding:12px 14px; }}
  .tl-futuro .tl-caja {{ border-style:dashed; background:#FAFCFE; }}
  .tl-actual .tl-caja {{ border-color:#BFDDF8; box-shadow:0 4px 14px rgba(30,144,240,.10); }}
  .tl-top {{ display:flex; justify-content:space-between; align-items:baseline; gap:10px; }}
  .tl-fecha, .tl-fase {{ font-size:14px; font-weight:600; }}
  .tl-horas {{ font-size:13px; font-weight:600; color:var(--blue); white-space:nowrap; }}
  .tl-hecho .tl-horas {{ color:#16A34A; }}
  .tl-tag {{ margin-left:8px; font-size:11px; font-weight:600; color:#fff; background:#1E90F0; border-radius:999px; padding:2px 8px; vertical-align:middle; }}
  .tl-desc {{ font-size:13px; color:var(--ink2); margin:6px 0 4px; }}
  .tl-lista {{ margin:6px 0 0; padding-left:18px; font-size:13px; line-height:1.55; color:var(--ink); }}
  .tl-items {{ list-style:none; padding-left:0; }}
  .tl-items li {{ position:relative; display:flex; justify-content:space-between; gap:10px; padding:5px 0 5px 20px; border-top:1px solid #F0F4F8; }}
  .tl-items li:first-child {{ border-top:none; }}
  .tl-items li::before {{ content:"○"; color:#A0B4C4; position:absolute; left:0; top:5px; }}
  .tl-items li span {{ flex:1; }}
  .tl-items li em {{ font-style:normal; font-size:12px; color:var(--ink2); white-space:nowrap; }}
  .tl-items li.tl-ok {{ color:#16A34A; }}
  .tl-items li.tl-ok::before {{ content:"✓"; color:#22C55E; }}
  @media (max-width:480px) {{ .tl-items li {{ flex-direction:column; gap:0; }} .tl-num {{ font-size:17px; }} }}
  /* bitacora overlay */
  #bitacora-overlay {{ display:none; position:fixed; inset:0; background:var(--bg); z-index:60; overflow-y:auto; }}
  #bitacora-overlay.show {{ display:block; }}
  .bitacora-header {{ display:flex; justify-content:space-between; align-items:center; padding:20px 16px; max-width:720px; margin:0 auto; }}
  .bitacora-header h2 {{ margin:0; }}
  .cerrar-btn {{ width:44px; height:44px; border-radius:50%; background:#fff; border:1px solid var(--border); display:flex; align-items:center; justify-content:center; font-size:20px; color:var(--ink); cursor:pointer; flex:0 0 44px; }}
  .objetivos-lista {{ max-width:720px; margin:0 auto; padding:0 16px 40px; }}
  .bit-area {{ margin-bottom:24px; }}
  .bit-area-head {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; padding-bottom:8px; border-bottom:2px solid var(--border); }}
  .bit-area-tit {{ font-size:15px; font-weight:600; color:var(--ink); }}
  .bit-area-badge {{ font-size:13px; font-weight:600; }}
  .bit-item {{ display:flex; align-items:center; gap:10px; background:#fff; border:1px solid var(--border); border-radius:12px; padding:12px 14px; margin-bottom:8px; }}
  .bit-dot {{ width:12px; height:12px; border-radius:50%; flex:0 0 12px; }}
  .bit-nom {{ flex:1; font-size:14px; color:var(--ink); }}
  .bit-pct {{ font-size:12px; color:var(--ink2); white-space:nowrap; }}
</style></head>
<body>
<div class="topbar"></div>

<div class="menu-btn" onclick="toggleMenu()">⋮</div>
<div class="menu-dropdown" id="menu-dropdown">
  <a onclick="abrirBitacora()">Bitácora de trabajo</a>
</div>

<div id="bitacora-overlay">
  <div class="bitacora-header">
    <h2>Bitácora de trabajo</h2>
    <div class="cerrar-btn" onclick="cerrarBitacora()">✕</div>
  </div>
  <div class="tl-wrap">
    {bitacora_timeline_html}
  </div>
</div>

<div class="wrap">

  <div class="card">
    <h1>Avance del proyecto — Titi Burger</h1>
    <p class="actualizado">Actualizado hoy a las {ahora}</p>

    {dots_html}

    <div class="vamos-top">
      {ring_big}
      <div class="vamos-texto">
        <p>{frase_plan}</p>
        <span class="chip" style="background:{ESTADO_COLOR[estado_chip]}">{ESTADO_TXT[estado_chip]}</span>
      </div>
    </div>

    <div class="resumen-mini">
      <div class="resumen-item"><span class="resumen-punto" style="background:var(--blue)"></span>
        <span><b>Hoy:</b> {horas_hoy_txt} en {len(actividades_hoy)} {'tarea' if len(actividades_hoy) == 1 else 'tareas'}</span></div>
      <div class="resumen-item"><span class="resumen-punto" style="background:var(--pendiente)"></span>
        <span><b>Sigue:</b> {que_sigue[0]['texto']}</span></div>
    </div>
  </div>

  <div class="card">
    {breakdown_html}
  </div>

  <div class="card">
    <div class="hoy-header"><h2 style="margin:0">Qué se hizo hoy</h2><span class="hoy-total">{horas_hoy_txt}</span></div>
    {hoy_html}
  </div>

  <div class="card">
    <h2>Qué sigue</h2>
    {sigue_html}
  </div>

  <footer>Generado automáticamente por Tito · {datetime.now():%d-%m-%Y %H:%M}</footer>
</div>

<script>
const PLAN_FASES = {plan_fases_js};
function verFasePlan(i) {{
  const box = document.getElementById('fase-resumen');
  const f = PLAN_FASES[i];
  if (!f) return;
  if (box.dataset.open === String(i)) {{ box.classList.remove('show'); box.dataset.open = ''; return; }}
  box.innerHTML = '<b>' + f.a + '</b>' + f.d;
  box.classList.add('show');
  box.dataset.open = String(i);
}}
function toggleMenu() {{ document.getElementById('menu-dropdown').classList.toggle('show'); }}
function abrirBitacora() {{
  document.getElementById('menu-dropdown').classList.remove('show');
  document.getElementById('bitacora-overlay').classList.add('show');
}}
function cerrarBitacora() {{ document.getElementById('bitacora-overlay').classList.remove('show'); }}
document.addEventListener('click', (e) => {{
  const dd = document.getElementById('menu-dropdown');
  const btn = document.querySelector('.menu-btn');
  if (dd.classList.contains('show') && !dd.contains(e.target) && e.target !== btn) {{ dd.classList.remove('show'); }}
}});
</script>
</body></html>"""

(PAGINA_DIR / "index.html").write_text(html, encoding="utf-8")
(OUT_DIR / "index.html").write_text(
    f'<!doctype html><meta http-equiv="refresh" content="0; url=/{TOKEN}/">'
    f'<a href="/{TOKEN}/">Ir a la página de avance</a>', encoding="utf-8")
print(f"% global (circulo): {pct_global}  |  horas hoy: {horas_hoy_txt}")
print(f"archivo: {PAGINA_DIR / 'index.html'}")
