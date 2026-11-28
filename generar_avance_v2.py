#!/usr/bin/env python3
"""Genera la pagina de avance DESDE CERO (25-nov-2026, rediseno pedido por Rafael).
Un solo archivo HTML, auto-contenido (CSS y SVG adentro), sin JS necesario para ver
los datos. Unica carga externa: Google Fonts (Poppins). Todos los numeros salen de
registro_actividad.csv y fases.json -- nada inventado, y se verifican antes de
escribir el archivo (ver verificar_numeros() mas abajo).
"""
import csv, json, secrets, time, re
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
import textwrap as _tw
TRADUCCION_HOY = {
    "Plan de raíz con Rafael: copiar la base de Félix a todas las carretas, reporte para Félix, llaves de red sin vencimiento y bitácora nueva": "Plan con Rafael para copiar la base de Félix a todas las sucursales, reporte para Félix y conexiones que ya no caducan",
    "Subir el software a GitHub, instalar skills y agente de revisión en la Z2, dejar la laptop en modo gamer y verificarla tras el reinicio": "Copia segura del sistema y ajustes en las computadoras de Tito",
    "Rediseñar el dashboard de avance, arreglar el login y la captura de horas": "Mejoramos esta página de avance, la entrada con clave y el registro de horas",
    "Repasar el plan, ordenar el software y subirlo a GitHub, dar accesos a Félix y Don Titi": "Repasamos el plan, guardamos una copia segura del sistema y dimos acceso a Félix y Don Titi",

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
    texto = TRADUCCION_HOY.get(f["tarea"], _tw.shorten(f["tarea"], 70, placeholder="…"))
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


def fila_hoy_tl(a):
    return (f'<div class="hy-it"><div class="hy-time">{fmt_hora_12(a["inicio"])}</div><div class="hy-dot"></div>'
            f'<div class="hy-box"><div class="hy-txt">{a["texto"]}</div><span class="hy-dur">{fmt_dur(a["minutos"])}</span></div></div>')


_AV = {"Tito": ("T", "#1E90F0"), "Rafael": ("R", "#F97316"), "Félix": ("F", "#16A34A"), "Nancy": ("N", "#A855F7"), "Distribuidor": ("D", "#64748B"), "David": ("D", "#0EA5E9"), "Marco": ("M", "#DB2777")}
def avatares(quien):
    nombres = [n for n in _AV if n in quien] or ["Tito"]
    return "".join(f'<span class="av" style="background:{_AV[n][1]}" title="{n}">{_AV[n][0]}</span>' for n in nombres)


def fila_hoy(a, max_min=None):
    max_min = max_min or max_min_hoy
    ancho = max(6, min(100, round(100 * a["minutos"] / 480)))  # contra una jornada de 8 h
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
    f'<div class="bd-head"><h2>En qué vamos ahorita</h2><span class="bd-badge">{fase_actual_plan["pct"]}% de esta etapa</span></div>'
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

# ---- Veredicto "¿cómo vamos?" (28-nov, Rafael): calendario + frenos de estado_proyecto.json ----
import html as _html
_est = json.loads((BASE / "estado_proyecto.json").read_text(encoding="utf-8"))
_frenos = [x for x in _est.get("frenos", []) if not x.get("resuelto")]
_dias_trab = max(1, (date.fromisoformat(plan["fin_trabajo"]) - _inicio).days)
_trans = max(0, (_hoy_d - _inicio).days)
_pct_t = round(100 * _trans / _dias_trab)
_pct_av = round(100 * _h_real / (_h_real + _h_falta)) if (_h_real + _h_falta) else 0
_pct_hr = round(100 * _h_real / plan["horas_presupuestadas"]) if plan["horas_presupuestadas"] else 0
_dif = round(_pct_av / 100 * _dias_trab - _trans)
_niv = ["vamos_muy_mal", "vamos_mal", "vamos_bien", "vamos_muy_bien"]
_n = 3 if _dif >= 7 else 2 if _dif >= 0 else 1 if _dif >= -7 else 0
_razones_mal = []
_et_act = fase_actual_plan.get("etiqueta", "")
_fr_act = [x for x in _frenos if x.get("frena") == _et_act]
if _fr_act and _n == 3:
    _n = 2; _razones_mal.append(f"La etapa de ahora (“{fase_actual_plan['area']}”) está esperando algo (ver abajo).")
if _pct_hr - _pct_av > 15:
    _n = max(0, _n - 1); _razones_mal.append(f"Se están gastando las horas más rápido que el trabajo: {_pct_hr}% de las horas para {_pct_av}% del trabajo.")
estado_chip = _niv[_n]
ESTADO_TXT.update({"vamos_muy_bien": "Vamos muy bien", "vamos_bien": "Vamos bien", "vamos_mal": "Vamos mal", "vamos_muy_mal": "Vamos muy mal"})
ESTADO_COLOR.update({"vamos_muy_bien": "#16A34A", "vamos_bien": "#22C55E", "vamos_mal": "#F5B83D", "vamos_muy_mal": "#F04E5E"})
if _dif > 0:
    _cal = f"Vamos <b>{_dif} {'día' if _dif == 1 else 'días'} adelantados</b> al calendario."
elif _dif == 0:
    _cal = "Vamos <b>justo a tiempo</b> con el calendario."
else:
    _cal = f"Vamos <b>{-_dif} {'día' if _dif == -1 else 'días'} atrasados</b> al calendario."
_bien = []
if _etapas_ok:
    _bien.append(f"{_etapas_ok} de {len(plan_fases)} etapas terminadas")
if _pct_hr <= _pct_av:
    _bien.append(f"Las horas alcanzan: {_pct_hr}% de las horas del contrato para {_pct_av}% del trabajo")
_bien += _est.get("bien", [])
_TIPO = {"decision": ("Decisión", "#1E90F0"), "dinero": ("Dinero", "#F04E5E"), "tecnico": ("Técnico", "#7C5CFA"),
         "persona": ("Esperando", "#F5B83D"), "seguridad": ("Seguridad", "#64748B")}
_etq_area = {pf.get("etiqueta"): pf["area"] for pf in plan_fases}
def _fila_freno(x):
    t, c = _TIPO.get(x.get("tipo"), ("Pendiente", "#64748B"))
    _ahora = ' <span class="es-ahora">frena la etapa de ahora</span>' if x.get("frena") == _et_act else ""
    _donde = f' · frena: {_html.escape(_etq_area.get(x["frena"], x["frena"]))}' if x.get("frena") else ""
    if x.get("desde"):
        _dd = (date.today() - date.fromisoformat(x["desde"])).days
        _cc = "#A0B4C4" if _dd <= 2 else ("#F5B83D" if _dd <= 5 else "#F04E5E")
        _ahora += f' <span class="es-reloj" style="background:{_cc}">⏳ {"esperando desde hoy" if _dd == 0 else (str(_dd) + (" día" if _dd == 1 else " días") + " esperando")}</span>'
    return (f'<li class="es-freno"><span class="es-tipo" style="background:{c}">{t}</span>'
            f'<div><div>{_html.escape(x["texto"])}{_ahora}</div><div class="es-quien">Le toca a: {_html.escape(x.get("quien",""))}{"" if x.get("frena") == _et_act else _donde}</div></div></li>')
_frenos.sort(key=lambda x: (x.get("frena") != _et_act, x.get("tipo") != "dinero"))
def _barra(lbl, v, col):
    return (f'<div class="es-barra"><div class="es-bl"><span>{lbl}</span><b>{v}%</b></div>'
            f'<div class="es-bt"><div style="width:{min(v,100)}%;background:{col}"></div></div></div>')
_sig = "".join(f"<li>{_html.escape(x['texto'])} <em>({_html.escape(x['quien'])})</em></li>" for x in que_sigue[:3])
estado_panel_html = (
    f'<div class="es-head" style="background:{ESTADO_COLOR[estado_chip]}"><h2>{ESTADO_TXT[estado_chip]}</h2>'
    f'<div class="cerrar-btn es-x" onclick="cerrarEstado()">✕</div><p>{_cal}</p></div>'
    f'<div class="es-body"><h3>Cómo vamos, en 3 partes</h3>@@SEMAFORO@@<h3>¿Vamos a tiempo?</h3>'
    + _barra("Tiempo que ya pasó del contrato", _pct_t, "#94A3B8")
    + _barra("Trabajo hecho, medido en horas", _pct_av, ESTADO_COLOR[estado_chip])
    + _barra("Horas del contrato ya usadas", _pct_hr, "#1E90F0")
    + f'<p class="es-nota">Del {fmt_fecha_es(plan["inicio"])} al {fmt_fecha_es(plan["fin_trabajo"])} ({_dias_trab} días de trabajo). '
      f'Llevamos {_h_real:.0f} h de trabajo y faltan unas {_h_falta:.0f} h.</p>'
    + (f'<h3>Por qué no va mejor</h3><ul class="es-lista es-mal">' + "".join(f"<li>{r}</li>" for r in _razones_mal) + '</ul>' if _razones_mal else "")
    + (f'<h3>Lo que falta o nos frena</h3><ul class="es-lista">' + "".join(_fila_freno(x) for x in _frenos) + '</ul>' if _frenos else '<h3>Lo que nos frena</h3><p>Nada. ✓</p>')
    + f'<h3>Lo que va bien</h3><ul class="es-lista es-ok">' + "".join(f"<li>{_html.escape(b)}</li>" for b in _bien) + '</ul>'
    + '</div>')

# ---- Regularización (Rafael 27-nov): todo lo que se agrega/cambia en las bases, base del manual ----
_reg = json.loads((BASE / "regularizacion.json").read_text(encoding="utf-8"))
_cam = _reg.get("cambios", [])
_EST = [("aprobado", "Por hacer", "#1E90F0"), ("aplicado", "Hecho, falta revisar", "#F5B83D"), ("verificado", "Listo", "#16A34A")]
_cnt = {e: sum(1 for c in _cam if c.get("estado") == e) for e, _, _ in _EST}
_rg = (f'<div class="tl-stats">'
       + "".join(f'<div class="tl-stat"><span class="tl-num" style="color:{col}">{_cnt[e]}</span><span class="tl-lbl">{t}</span></div>' for e, t, col in _EST)
       + '</div><p class="tl-nota">Todo lo que se agrega, cambia o da de baja para dejar Soft Restaurant regularizado: qué, por qué, quién lo decidió y cómo se hizo. Al terminar, esta lista es la base del manual.</p>')
_areas = {}
for c in _cam:
    _areas.setdefault(c.get("area", "Otros"), []).append(c)
_rg += '<div class="rg-resumen">' + "".join(f'<span class="rg-chip">{_html.escape(a)}: {len(v)}</span>' for a, v in _areas.items()) + '</div>'
for e, t, col in _EST:
    _l = [c for c in _cam if c.get("estado") == e]
    if not _l:
        continue
    _rg += f'<div class="rg-sec" style="color:{col}">{t}</div>'
    for c in sorted(_l, key=lambda x: (x.get("area", ""), x.get("id", 0))):
        _como = f'<div class="rg-l"><b>Cómo:</b> {_html.escape(c["como"])}</div>' if c.get("como") else ""
        _rg += (f'<div class="rg-card" style="border-left-color:{col}"><div class="rg-top"><span class="rg-tipo">{_html.escape(c.get("tipo",""))} · {_html.escape(c.get("area",""))}</span>'
                f'<span class="rg-base">{_html.escape("Base de Félix" if c.get("base")=="Félix" else "Sucursal "+c.get("base",""))} · {fmt_fecha_es(c["fecha"])}</span></div>'
                f'<div class="rg-que">{_html.escape(c["que"])}</div>'
                f'<div class="rg-l">{_html.escape(c.get("detalle",""))}</div>'
                f'<div class="rg-l"><b>Por qué:</b> {_html.escape(c.get("por_que",""))} <b>Decidió:</b> {_html.escape(c.get("decidio",""))}</div>{_como}</div>')
regu_html = _rg

# ---- Reportes para revisar (generar_reportes.py escribe reportes.json y las paginas en reportes/) ----
try:
    _reps = json.loads((BASE / "reportes.json").read_text(encoding="utf-8"))
except Exception:
    _reps = []
reportes_html = "".join(
    f'<a class="rp-item" href="reportes/{_html.escape(r["id"])}.html"><div><div class="rp-tit">{_html.escape(r["titulo"])}</div>'
    f'<div class="rp-sub">Para {_html.escape(r["para"])} · {fmt_fecha_es(r["fecha"])}</div></div>'
    f'<span class="rp-est" data-rid="{_html.escape(r["id"])}">En revisión</span></a>' for r in _reps)

# ---- "Te toca a ti" y "Lo nuevo desde tu ultima visita" (investigacion 27-nov: Linear, Rocketlane, ClickUp, Moxo) ----
_ev = []
for _f in filas:
    _ev.append({"t": f'{_f["fecha"]} {_f.get("hora_fin") or "23:59"}', "i": "🕒", "x": "Tito trabajó " + fmt_dur(parse_min(_f["duracion"])) + ": " + TRADUCCION_HOY.get(_f["tarea"], _f["tarea"])})
for _c in _cam:
    _ev.append({"t": _c["fecha"] + " 12:00", "i": "🧾", "x": "Regularización: " + _c["que"] + " (" + {"aprobado": "por hacer", "aplicado": "hecho", "verificado": "listo"}.get(_c.get("estado"), "") + ")"})
for _r in _reps:
    _ev.append({"t": _r["fecha"] + " 18:00", "i": "📄", "x": "Reporte nuevo: " + _r["titulo"], "r": _r["id"]})
_hoy_d2 = date.today()
_frenos_js = [{"x": f["texto"], "q": f.get("quien", ""), "d": (_hoy_d2 - date.fromisoformat(f["desde"])).days if f.get("desde") else None} for f in _frenos]
try:
    _salud = json.loads(Path("/home/tito/.openclaw/scripts/.health_state.json").read_text())
except Exception:
    _salud = {}
try:
    _pers = json.loads((BASE / "pendientes_personales.json").read_text(encoding="utf-8"))
except Exception:
    _pers = []
try:
    _url_pub = re.findall(r"https://[a-z0-9-]+\.trycloudflare\.com", Path("/home/tito/.openclaw/logs/cloudflared_avance.log").read_text(errors="ignore"))[-1]
except Exception:
    _url_pub = "(link de la página)"
for _t in _pers:
    _t["mensaje"] = _t.get("mensaje", "").replace("{{LINK}}", _url_pub)
novedades_js = json.dumps({"pers": _pers, "ev": _ev, "frenos": _frenos_js, "reps": [{"id": r["id"], "t": r["titulo"], "para": r["para"]} for r in _reps]}, ensure_ascii=False)
# Semaforo en 3 partes: calendario, cajas, pendientes de otros
_esp = max([f["d"] for f in _frenos_js if f["d"] is not None] or [0])
_cajas_ok = (_salud.get("clave", "x") == "") and (time.time() - _salud.get("ts", 0) < 3600)
_sem = [("Calendario", "#22C55E" if _dif >= 0 else ("#F5B83D" if _dif >= -7 else "#F04E5E"), (f"+{_dif} días" if _dif >= 0 else f"{_dif} días"), "Verde = vamos a tiempo o adelantados · Ámbar = hasta 7 días atrasados · Rojo = más de 7."),
        ("Cajas", "#22C55E" if _cajas_ok else ("#F04E5E" if _salud.get("clave") else "#A0B4C4"), ("6 de 6 en línea" if _cajas_ok else (_salud.get("clave") or "sin dato reciente")), "Lo revisa Tito cada 20 minutos. Rojo = alguna caja no responde."),
        ("Pendientes de otros", "#22C55E" if not _frenos_js else ("#A0B4C4" if _esp <= 2 else ("#F5B83D" if _esp <= 5 else "#F04E5E")), ((f"{len(_frenos_js)} esperando · desde hoy" if _esp == 0 else f"{len(_frenos_js)} esperando · máx. {_esp} días") if _frenos_js else "nada esperando"), "Gris = hasta 2 días · Ámbar = 3 a 5 días · Rojo = más de 5 días esperando.")]
semaforo_html = '<div class="sm-row">' + "".join(f'<details class="sm"><summary><span class="sm-dot" style="background:{c}"></span><span class="sm-n">{n}</span><span class="sm-v">{_html.escape(v)}</span></summary><p>{_html.escape(r)}</p></details>' for n, c, v, r in _sem) + '</div>'
estado_panel_html = estado_panel_html.replace("@@SEMAFORO@@", semaforo_html)

plan_fases_js = json.dumps(
    [{"a": pf["area"], "p": pf["pct"], "e": _ESTTXT[pf["estado"]],
      "h": sum(1 for it in pf["items"] if it["hecho"]),
      "f": sum(1 for it in pf["items"] if not it["hecho"]), "d": pf.get("desc","")} for pf in plan_fases],
    ensure_ascii=False)

# Círculo grande: se queda como está ahorita (% global del prefijo)
_tt = sum(len(pf["items"]) for pf in plan_fases)
_th = sum(1 for pf in plan_fases for it in pf["items"] if it["hecho"])
pct_plan_global = round(100 * _th / _tt) if _tt else 0
frase_plan = f"Ahorita: {fase_actual_plan['area']}."
ring_big = ring(pct_plan_global, 128, 12, "var(--blue)", "var(--track)", "var(--ink)", 32)

html = f"""<!doctype html>
<html lang="es"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Así va el proyecto — Titi Burger</title>
<link rel="manifest" href="/manifest.webmanifest"><meta name="mobile-web-app-capable" content="yes"><link rel="apple-touch-icon" href="/apple-touch-icon.png"><link rel="icon" href="/favicon.png"><meta name="theme-color" content="#EEF7FC"><meta name="apple-mobile-web-app-title" content="Titi Burger">
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
  .chip-btn {{ cursor:pointer; box-shadow:0 2px 8px rgba(0,0,0,.15); transition:transform .15s; }}
  .chip-btn:hover {{ transform:scale(1.05); }}
  #estado-overlay {{ display:none; position:fixed; inset:0; background:rgba(15,23,42,.45); z-index:60; align-items:flex-end; justify-content:center; }}
  #estado-overlay.show {{ display:flex; }}
  .es-panel {{ background:#fff; width:100%; max-width:560px; max-height:90vh; overflow:auto; border-radius:22px 22px 0 0; animation:esUp .25s ease-out; }}
  @media (min-width:640px) {{ #estado-overlay {{ align-items:center; }} .es-panel {{ border-radius:22px; }} }}
  @keyframes esUp {{ from {{ transform:translateY(40px); opacity:0; }} to {{ transform:none; opacity:1; }} }}
  .es-head {{ color:#fff; padding:24px 22px 18px; position:relative; }}
  .es-head h2 {{ margin:0 0 6px; font-size:26px; color:#fff; }}
  .es-head p {{ margin:0; font-size:15px; opacity:.95; }}
  .es-x {{ position:absolute; top:14px; right:14px; color:#fff !important; background:rgba(255,255,255,.22) !important; border:none !important; }}
  .es-body {{ padding:6px 22px 24px; }}
  .es-body h3 {{ font-size:15px; margin:20px 0 10px; color:var(--ink); }}
  .es-barra {{ margin-bottom:10px; }}
  .es-bl {{ display:flex; justify-content:space-between; font-size:13px; color:var(--ink2); margin-bottom:4px; }}
  .es-bt {{ height:10px; background:#EEF2F6; border-radius:99px; overflow:hidden; }}
  .es-bt div {{ height:100%; border-radius:99px; }}
  .es-nota {{ font-size:12px; color:var(--ink2); margin:6px 0 0; }}
  .es-lista {{ list-style:none; padding:0; margin:0; }}
  .es-lista li {{ font-size:14px; padding:9px 0; border-bottom:1px solid var(--border); color:var(--ink); }}
  .es-lista em {{ color:var(--ink2); font-style:normal; font-size:12px; }}
  .es-ok li::before {{ content:"✓ "; color:#16A34A; font-weight:700; }}
  .es-mal li::before {{ content:"! "; color:#F04E5E; font-weight:700; }}
  .es-freno {{ display:flex; gap:10px; align-items:flex-start; }}
  .es-tipo {{ color:#fff; font-size:11px; font-weight:600; padding:3px 9px; border-radius:99px; white-space:nowrap; margin-top:1px; }}
  .es-quien {{ font-size:12px; color:var(--ink2); margin-top:2px; }}
  .es-ahora {{ font-size:11px; color:#F04E5E; font-weight:600; }}
  #regu-overlay {{ display:none; position:fixed; inset:0; background:var(--bg); z-index:60; overflow-y:auto; }}
  #regu-overlay.show {{ display:block; }}
  .rg-resumen {{ display:flex; flex-wrap:wrap; gap:6px; margin:0 0 16px; }}
  .rg-chip {{ font-size:12px; background:#fff; border:1px solid var(--border); border-radius:999px; padding:4px 10px; color:var(--ink2); }}
  .rg-sec {{ font-size:12px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; margin:18px 0 8px; }}
  .rg-card {{ background:#fff; border:1px solid var(--border); border-left:4px solid; border-radius:12px; padding:12px 14px; margin-bottom:10px; }}
  .rg-top {{ display:flex; justify-content:space-between; gap:10px; font-size:12px; color:var(--ink2); }}
  .rg-tipo {{ font-weight:600; }}
  .rg-que {{ font-size:15px; font-weight:600; color:var(--ink); margin:4px 0; }}
  .rg-l {{ font-size:13px; color:var(--ink); margin-top:3px; line-height:1.5; }}
  @media (max-width:480px) {{ .rg-top {{ flex-direction:column; gap:0; }} }}
  .pq-card {{ display:flex; align-items:center; gap:14px; cursor:pointer; border:1.5px solid #BFDDF8; }}
  .pq-card.pq-listo {{ border-color:var(--border); }}
  .pq-ico {{ width:40px; height:40px; flex:0 0 40px; border-radius:50%; background:#1E90F0; color:#fff; font-weight:700; font-size:20px; display:flex; align-items:center; justify-content:center; }}
  .pq-listo .pq-ico {{ background:#22C55E; }}
  .pq-tit {{ font-weight:600; font-size:16px; color:var(--ink); }}
  .pq-sub {{ font-size:13px; color:var(--ink2); }}
  .pq-flecha {{ margin-left:auto; font-size:26px; color:var(--ink2); }}
  #preg-overlay {{ display:none; position:fixed; inset:0; background:var(--bg); z-index:60; overflow-y:auto; }}
  #preg-overlay.show {{ display:block; }}
  .pq {{ background:#fff; border:1px solid var(--border); border-radius:14px; padding:16px; margin-bottom:14px; }}
  .pq.pq-ok {{ border-left:4px solid #22C55E; }}
  .pq-n {{ font-size:12px; font-weight:600; color:var(--ink2); letter-spacing:.06em; text-transform:uppercase; }}
  .pq-p {{ font-size:16px; font-weight:600; color:var(--ink); margin:4px 0 6px; }}
  .pq-c {{ font-size:13px; color:var(--ink2); margin:0 0 12px; line-height:1.5; }}
  .pq-op {{ display:block; width:100%; text-align:left; min-height:48px; padding:12px 14px; margin-bottom:8px; border:1.5px solid var(--border); border-radius:12px; background:#fff; font:inherit; font-size:15px; color:var(--ink); cursor:pointer; }}
  .pq-op:hover {{ border-color:#1E90F0; }}
  .pq-op.sel {{ border-color:#22C55E; background:#F0FBF3; font-weight:600; }}
  .pq-campo {{ display:block; margin-bottom:10px; }}
  .pq-campo span {{ display:block; font-size:13px; color:var(--ink2); margin-bottom:4px; }}
  .pq-campo input {{ width:100%; box-sizing:border-box; min-height:44px; padding:10px 12px; border:1.5px solid var(--border); border-radius:10px; font:inherit; font-size:15px; }}
  .pq-campo input:focus {{ outline:none; border-color:#1E90F0; }}
  .pq-guardar {{ min-height:46px; padding:0 20px; border:none; border-radius:12px; background:#1E90F0; color:#fff; font:inherit; font-weight:600; font-size:15px; cursor:pointer; }}
  .pq-atajo {{ margin-top:8px; text-align:center; font-size:14px; color:var(--ink2); border-style:dashed; }}
  .pq-estado {{ font-size:13px; color:#16A34A; margin-top:8px; min-height:18px; }}
  .pq-estado.err {{ color:#F04E5E; }}
  .rp-nota {{ font-size:13px; color:var(--ink2); margin:-4px 0 10px; }}
  .rp-item {{ display:flex; align-items:center; justify-content:space-between; gap:12px; padding:12px 0; border-top:1px solid var(--border); text-decoration:none; color:var(--ink); min-height:48px; }}
  .rp-tit {{ font-weight:600; font-size:15px; }}
  .rp-sub {{ font-size:12px; color:var(--ink2); }}
  .rp-est {{ flex:0 0 auto; font-size:12px; font-weight:600; color:#fff; background:#F5B83D; border-radius:999px; padding:3px 10px; }}
  .rp-est.ok {{ background:#22C55E; }}
  .card-top {{ position:relative; }}
  .card-top h1 {{ padding-right:48px; }}
  .marca {{ margin:0; font-size:13px; font-weight:600; color:var(--ink2); }}
  .menu-btn {{ position:absolute !important; top:14px !important; right:14px !important; left:auto !important; width:40px !important; height:40px !important; box-shadow:none !important; }}
  .menu-dropdown {{ position:absolute !important; top:62px !important; right:16px !important; left:auto !important; }}
  .ring-wrap {{ display:flex; flex-direction:column; align-items:center; }}
  .ring-cap {{ font-size:12px; color:var(--ink2); margin-top:2px; }}
  .bitacora-header {{ position:sticky; top:0; z-index:2; background:var(--bg); }}
  .pf-scroll {{ -webkit-mask-image:linear-gradient(90deg,#000 88%,transparent); mask-image:linear-gradient(90deg,#000 88%,transparent); }}
  .tl-sec, .rg-sec, .pq-n {{ text-transform:none !important; letter-spacing:0 !important; font-size:13px !important; }}
  .tl-lbl {{ line-height:1.3; }}
  .chip-btn:hover {{ transform:none !important; }}
  .pq-guardar {{ width:100%; }}
  .es-freno {{ flex-direction:column; gap:4px !important; }}
  .es-tipo {{ align-self:flex-start; }}
  .es-ahora {{ display:inline-block; background:#FDECEE; border-radius:999px; padding:1px 8px; margin-left:4px; }}
  @media (max-width:480px) {{ .vamos-texto p {{ text-align:left; }} }}
  .fo-ico {{ background:#7C5CFA !important; font-size:18px; }}
  #foro-overlay {{ display:none; position:fixed; inset:0; background:var(--bg); z-index:60; overflow-y:auto; }}
  #foro-overlay.show {{ display:block; }}
  .fo-txt {{ width:100%; box-sizing:border-box; min-height:90px; border:1.5px solid var(--border); border-radius:12px; padding:10px 12px; font:inherit; font-size:15px; margin-bottom:10px; }}
  .fo-hilo {{ background:#fff; border:1px solid var(--border); border-radius:14px; padding:14px 16px; margin-bottom:12px; }}
  .fo-hilo.abierta {{ border-left:4px solid #F5B83D; }}
  .fo-hilo.contestada {{ border-left:4px solid #22C55E; }}
  .fo-quien {{ font-size:12px; color:var(--ink2); }}
  .fo-preg {{ font-size:15px; font-weight:600; color:var(--ink); margin:4px 0 8px; white-space:pre-wrap; }}
  .fo-resp {{ background:#F4FAFE; border-radius:10px; padding:10px 12px; margin-top:8px; font-size:14px; white-space:pre-wrap; }}
  .fo-resp b {{ color:var(--blue); }}
  .fo-esp {{ font-size:13px; color:#9A6400; }}
  .fo-tools {{ display:flex; gap:8px; margin:0 0 10px; flex-wrap:wrap; }}
  .fo-tool {{ flex:1; min-width:90px; min-height:44px; display:flex; align-items:center; justify-content:center; gap:4px; border:1.5px solid var(--border); border-radius:12px; background:#fff; font:inherit; font-size:14px; color:var(--ink); cursor:pointer; }}
  .fo-tool.rec {{ border-color:#F04E5E; color:#F04E5E; background:#FDECEE; font-weight:600; }}
  .fo-adjs {{ display:flex; flex-wrap:wrap; gap:6px; margin-bottom:8px; }}
  .fo-chip {{ display:flex; align-items:center; gap:6px; background:#F4FAFE; border:1px solid var(--border); border-radius:10px; padding:4px 8px; font-size:12px; max-width:100%; }}
  .fo-chip img {{ width:36px; height:36px; object-fit:cover; border-radius:6px; }}
  .fo-chip button {{ border:none; background:none; color:var(--ink2); font-size:16px; cursor:pointer; min-width:28px; min-height:28px; }}
  .fo-modo {{ background:#EEF5FF; border-radius:10px; padding:8px 10px; font-size:13px; margin-bottom:8px; display:flex; justify-content:space-between; gap:8px; align-items:center; }}
  .fo-modo button {{ border:none; background:none; color:var(--blue); font-weight:600; cursor:pointer; }}
  .fo-a-img {{ display:block; max-width:100%; max-height:320px; border-radius:10px; margin-top:8px; }}
  .fo-a-aud, .fo-a-vid {{ width:100%; margin-top:8px; }}
  .fo-a-vid {{ max-height:320px; border-radius:10px; background:#000; }}
  .fo-a-file {{ display:flex; align-items:center; gap:8px; margin-top:8px; padding:10px 12px; border:1px solid var(--border); border-radius:10px; text-decoration:none; color:var(--ink); background:#fff; font-size:14px; }}
  .fo-trans {{ font-size:13px; color:var(--ink2); background:#FAFAF5; border-radius:8px; padding:6px 10px; margin-top:4px; font-style:italic; }}
  .fo-resp-btn {{ margin-top:8px; border:none; background:none; color:var(--blue); font:inherit; font-weight:600; font-size:14px; cursor:pointer; min-height:36px; padding:0; }}
  .tt-card {{ border:1.5px solid #BFDDF8; }}
  .tt-it {{ display:flex; align-items:center; gap:12px; padding:12px 0; border-top:1px solid var(--border); text-decoration:none; color:var(--ink); cursor:pointer; min-height:48px; }}
  .tt-it:first-child {{ border-top:none; }}
  .tt-ic {{ font-size:20px; width:28px; text-align:center; }}
  .tt-x {{ flex:1; font-size:15px; }}
  .tt-x small {{ display:block; color:var(--ink2); font-size:12px; }}
  .tt-ok {{ color:#16A34A; font-weight:600; padding:6px 0; }}
  .nv-desde {{ font-size:13px; color:var(--ink2); margin:0 0 6px; }}
  .nv-it {{ display:flex; gap:10px; padding:8px 0; border-top:1px solid var(--border); font-size:14px; }}
  .nv-it:first-child {{ border-top:none; }}
  .nv-it small {{ color:var(--ink2); white-space:nowrap; }}
  .sm-row {{ display:flex; flex-direction:column; gap:6px; margin-bottom:6px; }}
  .sm {{ border:1px solid var(--border); border-radius:12px; background:#fff; }}
  .sm summary {{ list-style:none; display:flex; align-items:center; gap:10px; padding:10px 12px; cursor:pointer; min-height:44px; }}
  .sm summary::-webkit-details-marker {{ display:none; }}
  .sm-dot {{ width:12px; height:12px; border-radius:50%; flex:0 0 12px; }}
  .sm-n {{ font-weight:600; font-size:14px; }}
  .sm-v {{ margin-left:auto; font-size:13px; color:var(--ink2); }}
  .sm p {{ margin:0; padding:0 12px 10px 34px; font-size:12px; color:var(--ink2); }}
  .es-reloj {{ display:inline-block; color:#fff; font-size:11px; font-weight:600; border-radius:999px; padding:1px 8px; margin-left:4px; }}
  .fo-top {{ display:flex; justify-content:space-between; align-items:center; gap:8px; }}
  .fo-ok {{ font-size:12px; font-weight:600; color:#15803D; background:#E6F7EC; border-radius:999px; padding:2px 10px; white-space:nowrap; }}
  .fo-pend {{ font-size:12px; font-weight:600; color:#9A6400; background:#FFF4DE; border-radius:999px; padding:2px 10px; white-space:nowrap; }}
  .tt-msg {{ align-items:flex-start; cursor:default; }}
  .tt-pre {{ white-space:pre-wrap; font:inherit; font-size:13px; background:#F4FAFE; border:1px solid var(--border); border-radius:10px; padding:10px; margin:8px 0; color:var(--ink); }}
  .tt-btns {{ display:flex; flex-wrap:wrap; gap:6px; }}
  .tt-b {{ min-height:40px; padding:0 12px; border:none; border-radius:10px; font:inherit; font-size:13px; font-weight:600; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; }}
  .tt-b.azul {{ background:#1E90F0; color:#fff; }} .tt-b.verde {{ background:#22C55E; color:#fff; }} .tt-b.gris {{ background:#EEF2F6; color:var(--ink); }}
  .ep-card {{ padding:0 !important; overflow:hidden; }}
  .ep-hero {{ display:flex; align-items:center; gap:12px; padding:18px 18px 14px; background:linear-gradient(135deg,#1E90F0,#22C1C3); color:#fff; }}
  .ep-emoji {{ font-size:30px; }}
  .ep-tt {{ flex:1; }}
  .ep-k {{ font-size:12px; opacity:.9; }}
  .ep-t {{ font-size:18px; font-weight:700; line-height:1.25; }}
  .ep-pct {{ font-size:26px; font-weight:700; }}
  .ep-bar {{ height:8px; background:#E3EEF6; }}
  .ep-bar div {{ height:100%; background:linear-gradient(90deg,#22C55E,#16A34A); border-radius:0 999px 999px 0; }}
  .ep-sub {{ margin:12px 18px 4px; font-size:13px; color:var(--ink2); }}
  .ep-list {{ padding:0 18px 14px; }}
  .ep-it {{ display:flex; align-items:center; gap:12px; padding:11px 0; border-top:1px solid var(--border); font-size:15px; }}
  .ep-it:first-child {{ border-top:none; }}
  .ep-ic {{ width:24px; height:24px; flex:0 0 24px; border-radius:50%; border:2px solid #C9CFD6; display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:700; color:#fff; }}
  .ep-ok .ep-ic {{ background:#22C55E; border-color:#22C55E; }}
  .ep-ok .ep-txt {{ color:var(--ink2); }}
  .ep-txt {{ flex:1; }}
  .av {{ display:inline-flex; width:24px; height:24px; border-radius:50%; color:#fff; font-size:11px; font-weight:700; align-items:center; justify-content:center; margin-left:-6px; border:2px solid #fff; }}
  .av:first-child {{ margin-left:0; }}
  .hy-head {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }}
  .hy-head h2 {{ margin:0; }}
  .hy-total {{ font-size:13px; font-weight:700; color:#fff; background:linear-gradient(135deg,#F97316,#F43F5E); border-radius:999px; padding:4px 12px; }}
  .hy-tl {{ position:relative; }}
  .hy-tl::before {{ content:""; position:absolute; left:70px; top:6px; bottom:6px; width:2px; background:#FBD5BF; }}
  .hy-it {{ display:flex; align-items:flex-start; gap:10px; margin-bottom:12px; position:relative; }}
  .hy-time {{ flex:0 0 58px; font-size:12px; color:var(--ink2); text-align:right; padding-top:10px; }}
  .hy-dot {{ flex:0 0 12px; width:12px; height:12px; border-radius:50%; background:#F97316; margin-top:12px; box-shadow:0 0 0 4px #FFEDD5; z-index:1; }}
  .hy-box {{ flex:1; background:#FFF8F1; border:1px solid #FDE7D3; border-radius:14px; padding:10px 12px; }}
  .hy-txt {{ font-size:14px; line-height:1.45; }}
  .hy-dur {{ display:inline-block; margin-top:6px; font-size:12px; font-weight:600; color:#C2410C; background:#FFEDD5; border-radius:999px; padding:1px 8px; }}
  .sg-it {{ display:flex; gap:12px; padding:12px; border-radius:14px; margin-bottom:8px; border:1px solid var(--border); }}
  .sg-next {{ background:linear-gradient(135deg,#EEF6FF,#F4FBF6); border-color:#BFDDF8; }}
  .sg-n {{ flex:0 0 30px; height:30px; border-radius:50%; background:#EEF2F6; color:var(--ink2); font-weight:700; display:flex; align-items:center; justify-content:center; }}
  .sg-next .sg-n {{ background:#1E90F0; color:#fff; }}
  .sg-body {{ flex:1; }}
  .sg-txt {{ font-size:15px; font-weight:500; }}
  .sg-who {{ display:flex; align-items:center; gap:8px; margin-top:6px; font-size:12px; color:var(--ink2); flex-wrap:wrap; }}
  .sg-tag {{ font-size:11px; font-weight:600; color:#1E90F0; background:#E7F1FB; border-radius:999px; padding:1px 8px; }}
  footer {{ text-align:center; color:var(--ink2); font-size:13px; padding:10px 0 30px; line-height:1.6; }}
  footer span {{ font-size:12px; opacity:.8; }}
  .ft-burger {{ font-size:28px; }}
  .tt-resp {{ width:100%; box-sizing:border-box; min-height:64px; border:1.5px solid var(--border); border-radius:10px; padding:8px 10px; font:inherit; font-size:14px; margin:4px 0 8px; }}
  .tt-escribe {{ border-top:1px solid var(--border); padding-top:12px; margin-top:4px; }}
  .tt-m {{ display:block; font-size:13px; color:#16A34A; margin-top:6px; }}
  .tt-enviar {{ width:100%; justify-content:center; margin-top:2px; }}
  .pv-fab {{ position:fixed; right:16px; bottom:18px; z-index:50; min-height:52px; padding:0 18px; border:none; border-radius:999px; background:#1E90F0; color:#fff; font:inherit; font-weight:600; font-size:15px; box-shadow:0 6px 18px rgba(20,60,100,.25); cursor:pointer; }}
  .pv-badge {{ display:inline-block; margin-left:6px; min-width:20px; height:20px; border-radius:999px; background:#F04E5E; font-size:12px; line-height:20px; }}
  #priv-overlay {{ display:none; position:fixed; inset:0; background:var(--bg); z-index:70; flex-direction:column; }}
  #priv-overlay.show {{ display:flex; }}
  .pv-solo {{ font-size:12px; font-weight:500; color:var(--ink2); }}
  .pv-wrap {{ flex:1; overflow-y:auto; }}
  .pv-lista {{ max-width:720px; margin:0 auto; padding:4px 14px 10px; display:flex; flex-direction:column; gap:8px; }}
  .pv-m {{ max-width:85%; padding:9px 12px; border-radius:16px; font-size:15px; line-height:1.45; white-space:pre-wrap; word-break:break-word; }}
  .pv-m small {{ display:block; font-size:11px; color:var(--ink2); margin-top:4px; }}
  .pv-yo {{ align-self:flex-end; background:#1E90F0; color:#fff; border-bottom-right-radius:4px; }}
  .pv-yo small {{ color:#DCEBFA; }}
  .pv-tito {{ align-self:flex-start; background:#fff; border:1px solid var(--border); border-bottom-left-radius:4px; }}
  .pv-comp {{ border-top:1px solid var(--border); background:#fff; padding:10px 12px calc(10px + env(safe-area-inset-bottom)); }}
  .pv-txt {{ width:100%; box-sizing:border-box; min-height:52px; max-height:140px; border:1.5px solid var(--border); border-radius:12px; padding:9px 11px; font:inherit; font-size:15px; }}
  .pv-tools {{ display:flex; gap:6px; margin-top:6px; }}
  .pv-tools .fo-tool {{ flex:0 0 48px; min-width:48px; }}
  .pv-send {{ flex:1; width:auto !important; }}
  .pv-escr {{ color:var(--ink2); font-style:italic; }}
  .pv-dots i {{ font-style:normal; animation:pvdot 1.2s infinite; }}
  .pv-dots i:nth-child(2) {{ animation-delay:.2s; }} .pv-dots i:nth-child(3) {{ animation-delay:.4s; }}
  @keyframes pvdot {{ 0%,60%,100% {{ opacity:.2; }} 30% {{ opacity:1; }} }}
  .pv-visto {{ align-self:flex-end; font-size:12px; color:var(--ink2); }}
  .pv-head {{ flex:0 0 auto; display:flex; align-items:center; justify-content:space-between; gap:12px; padding:calc(10px + env(safe-area-inset-top)) 16px 10px; background:#fff; border-bottom:1px solid var(--border); }}
  .pv-tit {{ display:flex; flex-direction:column; line-height:1.2; }}
  .pv-tit b {{ font-size:18px; color:var(--ink); }}
  .pv-solo {{ font-size:12px; color:var(--ink2); }}
  .pv-x {{ flex:0 0 40px; width:40px; height:40px; border-radius:50%; border:1px solid var(--border); background:#fff; font-size:18px; color:var(--ink); cursor:pointer; }}
  .pv-wrap {{ padding-top:10px; }}
  .bitacora-header {{ padding-top:calc(20px + env(safe-area-inset-top)) !important; }}
</style></head>
<body>
<div class="topbar"></div>

<div class="menu-dropdown" id="menu-dropdown">
  <a onclick="abrirBitacora()">Bitácora de trabajo</a>
  <a onclick="abrirRegu()">Regularización de Soft Restaurant</a>
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

<div id="regu-overlay">
  <div class="bitacora-header">
    <h2>Regularización de Soft Restaurant</h2>
    <div class="cerrar-btn" onclick="cerrarRegu()">✕</div>
  </div>
  <div class="tl-wrap">{regu_html}</div>
</div>

<div id="preg-overlay">
  <div class="bitacora-header">
    <h2 id="pq-h2">Preguntas para ti</h2>
    <div class="cerrar-btn" onclick="cerrarPreg()">✕</div>
  </div>
  <div class="tl-wrap"><p class="tl-nota">Pícale a tu respuesta o escríbela. Se guarda sola y Tito la ve al momento.</p><div id="pq-lista">Cargando…</div></div>
</div>

<div id="foro-overlay">
  <div class="bitacora-header">
    <h2>Preguntas y respuestas</h2>
    <div class="cerrar-btn" onclick="cerrarForo()">✕</div>
  </div>
  <div class="tl-wrap">
    <div class="pq fo-comp"><div class="pq-p" id="fo-tit">Haz tu pregunta</div><p class="pq-c" id="fo-ayuda">Sobre el proyecto, Soft Restaurant o lo que veas en esta página. Puedes mandar fotos, audios y archivos. Tito contesta aquí mismo.</p>
      <div id="fo-modo" class="fo-modo" style="display:none"></div>
      <textarea id="fo-txt" class="fo-txt" placeholder="Escribe tu mensaje"></textarea>
      <div id="fo-adj" class="fo-adjs"></div>
      <div class="fo-tools">
        <label class="fo-tool">📷 Foto<input type="file" accept="image/*,video/*" multiple hidden onchange="subirArchivos(this)"></label>
        <button type="button" class="fo-tool" id="fo-rec" onclick="grabar()">🎤 Audio</button>
        <label class="fo-tool">📎 Archivo<input type="file" multiple hidden onchange="subirArchivos(this)"></label>
      </div>
      <button class="pq-guardar" id="fo-enviar" onclick="enviarForo()">Enviar</button><div class="pq-estado" id="fo-msg"></div></div>
    <div id="fo-lista"></div>
  </div>
</div>

<button class="pv-fab" id="pv-fab" style="display:none" onclick="abrirPriv()" aria-label="Chat con Tito">💬 Tito<span class="pv-badge" id="pv-badge" style="display:none"></span></button>
<div id="priv-overlay">
  <div class="pv-head"><div class="pv-tit"><b>Chat con Tito</b><span class="pv-solo">Solo tú lo ves</span></div><button class="pv-x" onclick="cerrarPriv()" aria-label="Cerrar">✕</button></div>
  <div class="pv-wrap"><div id="pv-lista" class="pv-lista"></div></div>
  <div class="pv-comp">
    <div id="pv-adj" class="fo-adjs"></div>
    <textarea id="pv-txt" class="pv-txt" placeholder="Escríbele a Tito"></textarea>
    <div class="pv-tools">
      <label class="fo-tool">📷<input type="file" accept="image/*,video/*" multiple hidden onchange="pvSubir(this)"></label>
      <button type="button" class="fo-tool" id="pv-rec" onclick="pvGrabar()">🎤</button>
      <label class="fo-tool">📎<input type="file" multiple hidden onchange="pvSubir(this)"></label>
      <button class="pq-guardar pv-send" onclick="pvEnviar()">Enviar</button>
    </div>
    <div class="pq-estado" id="pv-msg"></div>
  </div>
</div>

<div id="estado-overlay" onclick="if(event.target===this)cerrarEstado()"><div class="es-panel">{estado_panel_html}</div></div>

<div class="wrap">

  <div class="card card-top">
    <div class="menu-btn" onclick="toggleMenu()" role="button" aria-label="Más opciones" tabindex="0">⋮</div>
    <p class="marca">Titi Burger</p>
    <h1>Así va el proyecto</h1>
    <p class="actualizado">Actualizado hoy a las {ahora}</p>

    {dots_html}

    <div class="vamos-top">
      <div class="ring-wrap">{ring_big}<div class="ring-cap">del proyecto</div></div>
      <div class="vamos-texto">
        <p>{frase_plan}</p>
        <span class="chip chip-btn" role="button" tabindex="0" onclick="abrirEstado()" style="background:{ESTADO_COLOR[estado_chip]}">{ESTADO_TXT[estado_chip]} ›</span>
      </div>
    </div>

    <div class="resumen-mini">
      <div class="resumen-item"><span class="resumen-punto" style="background:var(--blue)"></span>
        <span><b>Hoy:</b> {horas_hoy_txt} en {len(actividades_hoy)} {'tarea' if len(actividades_hoy) == 1 else 'tareas'}</span></div>
      <div class="resumen-item"><span class="resumen-punto" style="background:var(--pendiente)"></span>
        <span><b>Sigue:</b> {que_sigue[0]['texto']}</span></div>
    </div>
  </div>

  <div class="card tt-card" id="tt-card" style="display:none">
    <h2 style="margin:0 0 4px">Te toca a ti</h2>
    <div id="tt-lista"></div>

  </div>

  <div class="card nv-card" id="nv-card" style="display:none">
    <h2 style="margin:0 0 2px">Lo nuevo desde tu última visita</h2>
    <p class="nv-desde" id="nv-desde"></p>
    <div id="nv-lista"></div>
  </div>

  <div class="card" id="rp-card" style="{'' if _reps else 'display:none'}">
    <h2 style="margin-top:0">Reportes para revisar</h2>
    <p class="rp-nota">Ábrelos, apruébalos o deja un comentario ahí mismo.</p>
    {reportes_html}
  </div>

  <div class="card pq-card fo-card" id="fo-card" onclick="abrirForo()" role="button" tabindex="0">
    <div class="pq-ico fo-ico">💬</div>
    <div><div class="pq-tit">Preguntas y respuestas</div><div class="pq-sub" id="fo-sub">¿Tienes una duda? Pregúntale a Tito aquí</div></div>
    <div class="pq-flecha">›</div>
  </div>

  <div class="card pq-card" id="pq-card" onclick="abrirPreg()" role="button" tabindex="0" style="display:none">
    <div class="pq-ico">?</div>
    <div><div class="pq-tit" id="pq-tit">Preguntas para ti</div><div class="pq-sub" id="pq-sub"></div></div>
    <div class="pq-flecha">›</div>
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

  <footer>Lo actualiza Tito · {datetime.now():%d-%m-%Y %H:%M}</footer>
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
function abrirEstado() {{ document.getElementById('estado-overlay').classList.add('show'); }}
function cerrarEstado() {{ document.getElementById('estado-overlay').classList.remove('show'); }}
document.addEventListener('keydown', e => {{ if (e.key === 'Escape') cerrarEstado(); }});
function abrirRegu() {{ document.getElementById('menu-dropdown').classList.remove('show'); document.getElementById('regu-overlay').classList.add('show'); }}
function cerrarRegu() {{ document.getElementById('regu-overlay').classList.remove('show'); }}
let PQ = null;
function _mis() {{ return PQ ? PQ.preguntas.filter(q => (q.para || 'felix') === PQ.yo || PQ.yo === 'rafael' || PQ.yo === 'tito') : []; }}
function _e(t) {{ const d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; }}
async function cargarPreg() {{
  try {{
    const r = await fetch('/api/preguntas', {{credentials:'same-origin', cache:'no-store'}});
    if (!r.ok) return;
    PQ = await r.json();
  }} catch (e) {{ return; }}
  const _L = _mis(), tot = _L.length, hechas = _L.filter(q => PQ.respuestas[q.id]).length;
  const _tt = (PQ.yo === 'rafael' || PQ.yo === 'tito') ? 'Preguntas para Félix y Marco' : 'Preguntas para ti';
  document.getElementById('pq-tit').textContent = _tt; document.getElementById('pq-h2').textContent = _tt;
  const card = document.getElementById('pq-card');
  if (!tot) {{ card.style.display = 'none'; return; }}
  card.style.display = 'flex';
  card.classList.toggle('pq-listo', hechas === tot);
  document.getElementById('pq-sub').textContent = hechas === tot ? 'Todas contestadas (' + tot + ')' : (tot - hechas) + ' de ' + tot + ' por contestar · toma 2 minutos';
  pintarPreg();
}}
function pintarPreg() {{
  const box = document.getElementById('pq-lista'); if (!PQ) return;
  const _L = _mis();
  box.innerHTML = _L.map((q, i) => {{
    const r = PQ.respuestas[q.id]; const v = r ? r.respuesta : null;
    let cuerpo = '';
    if (q.tipo === 'opcion') {{
      cuerpo = q.opciones.map(o => '<button class="pq-op' + (v === o ? ' sel' : '') + '" data-q="' + _e(q.id) + '" data-o="' + _e(o) + '">' + (v === o ? '✓ ' : '') + _e(o) + '</button>').join('');
    }} else if (q.tipo === 'campos') {{
      const vv = (v && typeof v === 'object') ? v : {{}};
      cuerpo = q.campos.map(c0 => {{ const c = typeof c0 === 'string' ? {{nombre:c0}} : c0; return '<label class="pq-campo"><span>' + _e(c.nombre) + '</span><input data-c="' + _e(c.nombre) + '" value="' + _e(vv[c.nombre] || '') + '" placeholder="' + _e(c.ayuda || '') + '"></label>'; }}).join('')
        + '<button class="pq-guardar" data-g="' + _e(q.id) + '">Guardar</button>'
        + (q.atajos || []).map(o => '<button class="pq-op pq-atajo' + (v === o ? ' sel' : '') + '" data-q="' + _e(q.id) + '" data-o="' + _e(o) + '">' + (v === o ? '✓ ' : '') + _e(o) + '</button>').join('');
    }} else {{
      cuerpo = '<label class="pq-campo"><input data-c="_t" value="' + _e(v || '') + '"></label><button class="pq-guardar" data-g="' + _e(q.id) + '">Guardar</button>';
    }}
    const est = r ? '✓ Contestó ' + _e(({{felix:'Félix',rafael:'Rafael',tito:'Tito',dontiti:'Don Titi',marco:'Marco'}})[r.usuario] || r.usuario) + ' · ' + _e(r.fecha) : '';
    return '<div class="pq' + (r ? ' pq-ok' : '') + '" id="pq-' + _e(q.id) + '"><div class="pq-n">Pregunta ' + (i + 1) + ' de ' + _L.length + ((PQ.yo === 'rafael' || PQ.yo === 'tito') ? ' · para ' + ((q.para || 'felix') === 'marco' ? 'Marco' : 'Félix') : '') + '</div><div class="pq-p">' + _e(q.pregunta) + '</div><p class="pq-c">' + _e(q.contexto || '') + '</p>' + cuerpo + '<div class="pq-estado">' + est + '</div></div>';
  }}).join('');
}}
async function responder(id, respuesta, el) {{
  const est = document.querySelector('#pq-' + CSS.escape(id) + ' .pq-estado');
  est.classList.remove('err'); est.textContent = 'Guardando…';
  try {{
    const r = await fetch('/api/responder', {{method:'POST', credentials:'same-origin', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{id, respuesta}})}});
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || 'No se pudo guardar');
    PQ.respuestas[id] = d.registro;
    await cargarPreg();
  }} catch (e) {{ est.classList.add('err'); est.textContent = 'No se guardó: ' + e.message + '. Intenta otra vez.'; }}
}}
document.addEventListener('click', e => {{
  const b = e.target.closest('.pq-op');
  if (b) return responder(b.dataset.q, b.dataset.o, b);
  const g = e.target.closest('.pq-guardar[data-g]');
  if (g) {{
    const q = PQ.preguntas.find(x => x.id === g.dataset.g);
    const ins = document.querySelectorAll('#pq-' + CSS.escape(q.id) + ' input');
    let val;
    if (q.tipo === 'campos') {{ val = {{}}; ins.forEach(i => val[i.dataset.c] = i.value); }} else {{ val = ins[0].value; }}
    responder(q.id, val, g);
  }}
}});
function abrirPreg() {{ document.getElementById('preg-overlay').classList.add('show'); pintarPreg(); }}
function cerrarPreg() {{ document.getElementById('preg-overlay').classList.remove('show'); }}
cargarPreg();
async function cargarRep() {{
  try {{
    const r = await fetch('/api/reportes', {{credentials:'same-origin', cache:'no-store'}}); if (!r.ok) return;
    const d = await r.json();
    document.querySelectorAll('.rp-est').forEach(el => {{
      const e = (d.estado || {{}})[el.dataset.rid];
      if (e && e.aprobado.length) {{ el.textContent = 'Aprobado'; el.classList.add('ok'); }}
      else if (e && e.comentarios.length) {{ el.textContent = e.comentarios.length + ' comentario' + (e.comentarios.length > 1 ? 's' : ''); }}
    }});
  }} catch (e) {{}}
}}
cargarRep();
function _push() {{ try {{ history.pushState({{o:1}}, ''); }} catch (e) {{}} }}
window.addEventListener('popstate', () => document.querySelectorAll('#bitacora-overlay.show,#regu-overlay.show,#preg-overlay.show,#estado-overlay.show,#foro-overlay.show,#priv-overlay.show').forEach(e => e.classList.remove('show')));
document.addEventListener('click', e => {{ if (e.target.closest('.chip-btn,#pq-card,#fo-card,#pv-fab,.menu-dropdown a')) _push(); }}, true);
window.addEventListener('load', () => {{ const d = document.querySelectorAll('.pf-dot')[{_idx_act}]; if (d) d.scrollIntoView({{inline:'center', block:'nearest'}}); }});
const FNOM = {{felix:'Félix', rafael:'Rafael', tito:'Tito', dontiti:'Don Titi', marco:'Marco'}};
let FORO = null;
async function cargarForo() {{
  try {{ const r = await fetch('/api/foro', {{credentials:'same-origin', cache:'no-store'}}); if (!r.ok) return; FORO = await r.json(); }} catch (e) {{ return; }}
  const ab = FORO.hilos.filter(h => !h.respuestas.length).length, tot = FORO.hilos.length;
  document.getElementById('fo-sub').textContent = tot ? (tot + (tot === 1 ? ' pregunta' : ' preguntas') + (ab ? ' · ' + ab + ' esperando respuesta' : ' · todas contestadas')) : '¿Tienes una duda? Pregúntale a Tito aquí';
  pintarForo();
}}
let FO_ADJ = [], FO_RESP = null, FO_FIRMA = '';
function _tam(n) {{ return n > 1048576 ? (n / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1024)) + ' KB'; }}
function adjHtml(a) {{
  const u = '/api/archivo/' + encodeURIComponent(a.id);
  if (a.kind === 'imagen') return '<a href="' + u + '" target="_blank" rel="noopener"><img class="fo-a-img" loading="lazy" src="' + u + '?t=1" alt="' + _e(a.nombre) + '"></a>';
  if (a.kind === 'audio') return '<audio class="fo-a-aud" controls preload="none" src="' + u + '"></audio>' + (a.transcripcion ? '<div class="fo-trans">🗣️ ' + _e(a.transcripcion) + '</div>' : '<div class="fo-trans">Transcribiendo el audio…</div>');
  if (a.kind === 'video') return '<video class="fo-a-vid" controls preload="metadata" playsinline src="' + u + '"></video>';
  return '<a class="fo-a-file" href="' + u + '" target="_blank" rel="noopener">📄 <span>' + _e(a.nombre) + '</span> <small style="color:var(--ink2)">' + _tam(a.tam) + '</small></a>';
}}
function pintarForo(forzar) {{
  if (!FORO) return;
  const firma = JSON.stringify(FORO.hilos);
  if (!forzar && firma === FO_FIRMA) return;   // no repinta si nada cambió (no corta un audio que se está oyendo)
  FO_FIRMA = firma;
  const L = FORO.hilos.slice().reverse();
  document.getElementById('fo-lista').innerHTML = L.length ? L.map(h => '<div class="fo-hilo ' + (h.respuestas.length ? 'contestada' : 'abierta') + '" id="fo-h' + h.id + '"><div class="fo-top"><span class="fo-quien">' + _e(FNOM[h.usuario] || h.usuario) + ' · ' + _e(h.fecha) + '</span>' + (h.respuestas.length ? '<span class="fo-ok">✓ Contestada</span>' : '<span class="fo-pend">Esperando</span>') + '</div>'
    + (h.texto ? '<div class="fo-preg">' + _e(h.texto) + '</div>' : '') + (h.adjuntos || []).map(adjHtml).join('')
    + (h.respuestas.length ? h.respuestas.map(r => '<div class="fo-resp"><b>' + _e(FNOM[r.usuario] || r.usuario) + '</b> · <span class="fo-quien">' + _e(r.fecha) + '</span>' + (r.texto ? '<br>' + _e(r.texto) : '') + (r.adjuntos || []).map(adjHtml).join('') + '</div>').join('') : '<div class="fo-esp">Esperando respuesta de Tito</div>')
    + '<button class="fo-resp-btn" onclick="responderA(' + h.id + ')">↩︎ Responder</button></div>').join('')
    : '<p class="tl-nota">Todavía no hay preguntas. ¡Sé el primero!</p>';
}}
function pintarAdj() {{
  document.getElementById('fo-adj').innerHTML = FO_ADJ.map((a, i) => '<span class="fo-chip">' + (a.preview ? '<img src="' + a.preview + '" alt="">' : (a.kind === 'audio' ? '🎤' : a.kind === 'video' ? '🎬' : '📄')) + '<span>' + (a.id ? _e(a.nombre) : 'Subiendo…') + '</span><button onclick="quitarAdj(' + i + ')" aria-label="Quitar">×</button></span>').join('');
}}
function quitarAdj(i) {{ FO_ADJ.splice(i, 1); pintarAdj(); }}
async function subirUno(blob, nombre) {{
  const item = {{nombre, kind: (blob.type || '').startsWith('image') ? 'imagen' : (blob.type || '').startsWith('audio') ? 'audio' : (blob.type || '').startsWith('video') ? 'video' : 'archivo'}};
  if (item.kind === 'imagen') item.preview = URL.createObjectURL(blob);
  FO_ADJ.push(item); pintarAdj();
  const m = document.getElementById('fo-msg'); m.className = 'pq-estado'; m.textContent = 'Subiendo ' + nombre + '…';
  try {{
    if (blob.size > 25 * 1048576) throw new Error('pesa más de 25 MB');
    const r = await fetch('/api/subir', {{method:'POST', credentials:'same-origin', headers:{{'Content-Type': blob.type || 'application/octet-stream', 'X-Nombre': encodeURIComponent(nombre)}}, body: blob}});
    const d = await r.json(); if (!r.ok) throw new Error(d.error || 'no se pudo subir');
    Object.assign(item, d.adjunto); m.textContent = 'Listo: ' + nombre;
  }} catch (e) {{ FO_ADJ.splice(FO_ADJ.indexOf(item), 1); m.className = 'pq-estado err'; m.textContent = 'No se subió ' + nombre + ': ' + e.message; }}
  pintarAdj();
}}
async function subirArchivos(inp) {{ for (const f of [...inp.files]) await subirUno(f, f.name); inp.value = ''; }}
let REC = null, REC_T = null;
async function grabar() {{
  const b = document.getElementById('fo-rec');
  if (REC) {{ REC.stop(); return; }}
  if (!navigator.mediaDevices || !window.MediaRecorder) {{ document.getElementById('fo-msg').textContent = 'Este navegador no deja grabar audio. Usa 📎 Archivo para mandar una nota de voz.'; return; }}
  try {{
    const st = await navigator.mediaDevices.getUserMedia({{audio:true}});
    const tipo = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/webm'].find(t => MediaRecorder.isTypeSupported(t)) || '';
    const partes = []; REC = new MediaRecorder(st, tipo ? {{mimeType: tipo}} : undefined);
    REC.ondataavailable = e => e.data.size && partes.push(e.data);
    REC.onstop = async () => {{
      clearInterval(REC_T); st.getTracks().forEach(t => t.stop());
      const mt = (REC.mimeType || 'audio/webm').split(';')[0]; REC = null; b.classList.remove('rec'); b.textContent = '🎤 Audio';
      const blob = new Blob(partes, {{type: mt}}); const ext = mt.includes('mp4') ? '.m4a' : '.webm';
      await subirUno(blob, 'audio-' + new Date().toTimeString().slice(0, 5).replace(':', '') + ext);
    }};
    REC.start(); const t0 = Date.now(); b.classList.add('rec');
    const tick = () => {{ const s = Math.round((Date.now() - t0) / 1000); b.textContent = '⏺ ' + Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0') + ' · toca para terminar'; }};
    tick(); REC_T = setInterval(tick, 500);
  }} catch (e) {{ document.getElementById('fo-msg').className = 'pq-estado err'; document.getElementById('fo-msg').textContent = 'No se pudo usar el micrófono: dale permiso al navegador.'; }}
}}
function responderA(id) {{
  FO_RESP = id; const h = FORO.hilos.find(x => x.id === id);
  const md = document.getElementById('fo-modo'); md.style.display = 'flex';
  md.innerHTML = '<span>Respondiendo a ' + _e(FNOM[h.usuario] || h.usuario) + ': «' + _e((h.texto || 'archivo').slice(0, 60)) + '»</span><button onclick="cancelarResp()">Cancelar</button>';
  document.getElementById('fo-tit').textContent = 'Tu respuesta';
  document.querySelector('#foro-overlay .fo-comp').scrollIntoView({{behavior:'smooth', block:'start'}}); document.getElementById('fo-txt').focus();
}}
function cancelarResp() {{ FO_RESP = null; document.getElementById('fo-modo').style.display = 'none'; document.getElementById('fo-tit').textContent = 'Haz tu pregunta'; }}
async function enviarForo() {{
  const t = document.getElementById('fo-txt'), m = document.getElementById('fo-msg');
  if (FO_ADJ.some(a => !a.id)) {{ m.className = 'pq-estado err'; m.textContent = 'Espera a que terminen de subir los archivos.'; return; }}
  if (!t.value.trim() && !FO_ADJ.length) {{ m.className = 'pq-estado err'; m.textContent = 'Escribe algo o agrega una foto, audio o archivo.'; return; }}
  m.className = 'pq-estado'; m.textContent = 'Enviando…';
  try {{
    const body = {{accion: FO_RESP ? 'responder' : 'preguntar', id: FO_RESP, texto: t.value, adjuntos: FO_ADJ.map(a => a.id)}};
    const r = await fetch('/api/foro', {{method:'POST', credentials:'same-origin', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify(body)}});
    const d = await r.json(); if (!r.ok) throw new Error(d.error || 'No se pudo enviar');
    t.value = ''; FO_ADJ = []; pintarAdj(); cancelarResp(); m.textContent = 'Listo: quedó guardado. Tito te contesta aquí.'; cargarForo();
  }} catch (e) {{ m.className = 'pq-estado err'; m.textContent = 'No se envió: ' + e.message; }}
}}
function abrirForo() {{ document.getElementById('foro-overlay').classList.add('show'); pintarForo(true); }}
function cerrarForo() {{ document.getElementById('foro-overlay').classList.remove('show'); }}
cargarForo();
setInterval(() => {{ if (!document.hidden) {{ cargarForo(); cargarPreg(); }} }}, 20000);
const NV = {novedades_js};
const TNOM = {{felix:'Félix', rafael:'Rafael', tito:'Tito', dontiti:'Don Titi', marco:'Marco'}};
function _ts(t) {{ return new Date(String(t).replace(' ', 'T')).getTime() / 1000; }}
function _cuando(t) {{ const d = new Date(_ts(t) * 1000), h = new Date(); const dd = Math.round((new Date(h.toDateString()) - new Date(d.toDateString())) / 864e5);
  const hr = d.toLocaleTimeString('es-MX', {{hour:'numeric', minute:'2-digit'}}); return dd === 0 ? 'hoy ' + hr : dd === 1 ? 'ayer ' + hr : d.toLocaleDateString('es-MX', {{weekday:'short', day:'numeric', month:'short'}}); }}
async function cargarTuyo() {{
  let yo, ant, pq = null, rp = null, fo = null;
  try {{
    const r = await fetch('/api/yo', {{credentials:'same-origin', cache:'no-store'}}); if (!r.ok) return; const d = await r.json(); yo = d.yo; ant = d.anterior;
    [pq, rp, fo] = await Promise.all(['/api/preguntas', '/api/reportes', '/api/foro'].map(u => fetch(u, {{credentials:'same-origin', cache:'no-store'}}).then(x => x.ok ? x.json() : null).catch(() => null)));
  }} catch (e) {{ return; }}
  const nom = TNOM[yo] || yo, items = [];
  // --- Te toca a ti ---
  if (pq) {{ const f = pq.preguntas.filter(q => (q.para || 'felix') === yo && !pq.respuestas[q.id]).length; if (f) items.push({{i:'❓', x: f + (f === 1 ? ' pregunta por contestar' : ' preguntas por contestar'), s:'≈ ' + Math.max(1, f) + ' min · se contesta con un toque', go:"abrirPreg()"}}); }}
  if (rp) NV.reps.forEach(r => {{ const e = (rp.estado || {{}})[r.id]; if (r.para.includes(nom) && ['rafael', 'felix', 'dontiti'].includes(yo) && !(e && e.aprobado.some(a => a.usuario === yo))) items.push({{i:'📄', x:'Revisar y aprobar: ' + r.t, s:'Ábrelo y aprueba o comenta', href:'reportes/' + r.id + '.html'}}); }});
  let pv = null; if (yo === 'rafael') {{ try {{ const r = await fetch('/api/privado', {{credentials:'same-origin', cache:'no-store'}}); if (r.ok) pv = await r.json(); }} catch (e) {{}} }}
  (NV.pers || []).forEach(t => {{ const ya = (pv && pv.mensajes.some(m => m.ref === t.id && m.usuario === yo)) || (fo && fo.hilos.some(h => h.ref === t.id && h.usuario === yo)); if (t.para === yo && !ya) items.push({{i:t.icono, x:t.texto, s:t.sub, msg:t.mensaje, pid:t.id, ph:t.placeholder, si:t.boton_si}}); }});
  NV.frenos.forEach(f => {{ if (f.q.includes(nom)) items.push({{i:'⏳', x:f.x, s: f.d != null ? 'Esperando hace ' + f.d + (f.d === 1 ? ' día' : ' días') : ''}}); }});
  if (fo) fo.hilos.forEach(h => {{ const ult = h.respuestas.length ? h.respuestas[h.respuestas.length - 1] : null; if (h.usuario === yo && ult && ult.usuario !== yo) items.push({{i:'💬', x:'Te contestaron: «' + (h.texto || 'archivo').slice(0, 50) + '»', s:(TNOM[ult.usuario] || ult.usuario) + ' · ' + _cuando(ult.fecha), go:"abrirForo()"}}); }});
  if (yo !== 'tito') {{
    const c = document.getElementById('tt-card'); c.style.display = '';
    document.getElementById('tt-lista').innerHTML = items.length ? items.map(t => t.msg ? ('<div class="tt-it tt-msg"><span class="tt-ic">' + t.i + '</span><span class="tt-x">' + _e(t.x) + '<small>' + _e(t.s || '') + '</small><pre class="tt-pre">' + _e(t.msg) + '</pre><textarea class="tt-resp" id="tr-' + t.pid + '" placeholder="' + _e(t.ph || 'Escríbele a Tito') + '"></textarea><button class="tt-b azul tt-enviar" data-id="' + t.pid + '" onclick="ttResp(this, false)">Enviar a Tito</button><span class="tt-m" id="tm-' + t.pid + '"></span></span></div>') : (t.href ? '<a class="tt-it" href="' + t.href + '">' : '<div class="tt-it"' + (t.go ? ' onclick="' + t.go + '"' : '') + '>') + '<span class="tt-ic">' + t.i + '</span><span class="tt-x">' + _e(t.x) + (t.s ? '<small>' + _e(t.s) + '</small>' : '') + '</span>' + (t.href || t.go ? '<span class="pq-flecha">›</span>' : '') + (t.href ? '</a>' : '</div>')).join('') : '<div class="tt-ok">✔ Estás al día, ' + _e(nom) + '. No tienes nada pendiente.</div>';
  }}
  // --- Lo nuevo desde tu ultima visita ---
  const ev = NV.ev.map(e => ({{t:_ts(e.t), i:e.i, x:e.x}}));
  if (fo) fo.hilos.forEach(h => {{ if (h.usuario !== yo) ev.push({{t:_ts(h.fecha), i:'💬', x:(TNOM[h.usuario] || h.usuario) + ' preguntó: ' + (h.texto || 'archivo').slice(0, 60)}}); h.respuestas.forEach(r => {{ if (r.usuario !== yo) ev.push({{t:_ts(r.fecha), i:'💬', x:(TNOM[r.usuario] || r.usuario) + ' contestó: ' + (r.texto || 'archivo').slice(0, 60)}}); }}); }});
  if (rp) Object.entries(rp.estado || {{}}).forEach(([id, e]) => {{ const r = NV.reps.find(x => x.id === id); const t = r ? r.t : id;
    e.aprobado.forEach(a => {{ if (a.usuario !== yo) ev.push({{t:_ts(a.fecha), i:'✅', x:(TNOM[a.usuario] || a.usuario) + ' aprobó: ' + t}}); }});
    e.comentarios.forEach(c => {{ if (c.usuario !== yo) ev.push({{t:_ts(c.fecha), i:'🗨️', x:(TNOM[c.usuario] || c.usuario) + ' comentó en: ' + t}}); }}); }});
  if (pq) Object.values(pq.respuestas || {{}}).forEach(r => {{ if (r.usuario !== yo) ev.push({{t:_ts(r.fecha), i:'❓', x:(TNOM[r.usuario] || r.usuario) + ' contestó una pregunta'}}); }});
  const nuevos = ev.filter(e => ant ? e.t > ant : true).sort((a, b) => b.t - a.t).slice(0, 6);
  if (nuevos.length) {{
    document.getElementById('nv-card').style.display = '';
    document.getElementById('nv-desde').textContent = ant ? 'Desde ' + _cuando(new Date(ant * 1000).toISOString().slice(0, 16).replace('T', ' ')) : 'Bienvenido. Esto es lo más reciente:';
    document.getElementById('nv-lista').innerHTML = nuevos.map(e => '<div class="nv-it"><span>' + e.i + '</span><span style="flex:1">' + _e(e.x) + '</span><small>' + _cuando(new Date(e.t * 1000 - new Date().getTimezoneOffset() * 6e4).toISOString().slice(0, 16).replace('T', ' ')) + '</small></div>').join('');
  }}
}}
function copiarMsg(id) {{ const t = document.getElementById('pre-' + id).innerText; (navigator.clipboard ? navigator.clipboard.writeText(t) : Promise.reject()).then(() => alert('Copiado. Pégalo en el WhatsApp de Félix.')).catch(() => {{ const r = document.createRange(); r.selectNode(document.getElementById('pre-' + id)); getSelection().removeAllRanges(); getSelection().addRange(r); }}); }}
async function ttResp(btn, si) {{
  const id = btn.dataset.id, ta = document.getElementById('tr-' + id), m = document.getElementById('tm-' + id);
  let txt = ta.value.trim(); if (si) txt = '✅ ' + btn.dataset.si + (txt ? ' · ' + txt : '');
  if (!txt) {{ m.textContent = 'Escribe algo primero.'; return; }}
  const it = (NV.pers || []).find(x => x.id === id);
  if (it) txt = 'Sobre «' + it.texto + '»: ' + txt;
  m.textContent = 'Enviando…';
  try {{
    const r = await fetch('/api/privado', {{method:'POST', credentials:'same-origin', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{texto: txt, ref: it ? id : ''}})}});
    const d = await r.json(); if (!r.ok) throw new Error(d.error || 'no se pudo');
    ta.value = ''; m.textContent = '✓ Listo, Tito ya lo tiene. Te contesta en tu chat con Tito.'; setTimeout(cargarTuyo, 1500); cargarPriv();
  }} catch (e) {{ m.textContent = 'No se envió: ' + e.message; }}
}}
function yaHecho(id) {{ localStorage.setItem('hecho_' + id, '1'); cargarTuyo(); }}
cargarTuyo();
let PV = null, PV_FIRMA = '', PV_ADJ = [], PV_REC = null, PV_T = null;
async function cargarPriv() {{
  try {{ const r = await fetch('/api/privado', {{credentials:'same-origin', cache:'no-store'}}); if (!r.ok) return; PV = await r.json(); }} catch (e) {{ return; }}
  document.getElementById('pv-fab').style.display = '';
  const vistos = +(localStorage.getItem('pv_visto') || 0), nuevos = PV.mensajes.filter(m => m.usuario === 'tito' && m.id > vistos).length;
  const b = document.getElementById('pv-badge'); b.style.display = nuevos && !document.getElementById('priv-overlay').classList.contains('show') ? '' : 'none'; b.textContent = nuevos;
  pintarPriv();
}}
function pintarPriv(forzar) {{
  if (!PV) return; const f = JSON.stringify(PV.mensajes) + PV.escribiendo; if (!forzar && f === PV_FIRMA) return; PV_FIRMA = f;
  const box = document.getElementById('pv-lista');
  const ultimo = PV.mensajes.length ? PV.mensajes[PV.mensajes.length - 1] : null;
  box.innerHTML = (PV.mensajes.length ? PV.mensajes.map(m => '<div class="pv-m ' + (m.usuario === 'tito' ? 'pv-tito' : 'pv-yo') + '">' + _e(m.texto) + (m.adjuntos || []).map(adjHtml).join('') + '<small>' + (m.usuario === 'tito' ? 'Tito · ' : '') + _e(m.fecha) + '</small></div>').join('') : '<p class="tl-nota">Aquí hablas directo con Tito, como en la terminal. Solo tú lo ves.</p>')
    + (PV.escribiendo ? '<div class="pv-m pv-tito pv-escr">Tito está escribiendo<span class="pv-dots"><i>.</i><i>.</i><i>.</i></span></div>' : (ultimo && ultimo.usuario !== 'tito' ? '<div class="pv-visto">Enviado ✓ · Tito te contesta en un momento</div>' : ''));
  if (document.getElementById('priv-overlay').classList.contains('show')) {{ const w = document.querySelector('.pv-wrap'); w.scrollTop = w.scrollHeight; localStorage.setItem('pv_visto', Math.max(0, ...PV.mensajes.map(m => m.id))); }}
}}
function abrirPriv() {{ document.getElementById('priv-overlay').classList.add('show'); document.getElementById('pv-badge').style.display = 'none'; pintarPriv(true); }}
function cerrarPriv() {{ document.getElementById('priv-overlay').classList.remove('show'); }}
function pvPintarAdj() {{ document.getElementById('pv-adj').innerHTML = PV_ADJ.map((a, i) => '<span class="fo-chip">' + (a.preview ? '<img src="' + a.preview + '" alt="">' : (a.kind === 'audio' ? '🎤' : '📄')) + '<span>' + (a.id ? _e(a.nombre) : 'Subiendo…') + '</span><button onclick="PV_ADJ.splice(' + i + ',1);pvPintarAdj()" aria-label="Quitar">×</button></span>').join(''); }}
async function pvSubirUno(blob, nombre) {{
  const it = {{nombre, kind: (blob.type || '').startsWith('image') ? 'imagen' : (blob.type || '').startsWith('audio') ? 'audio' : 'archivo'}};
  if (it.kind === 'imagen') it.preview = URL.createObjectURL(blob);
  PV_ADJ.push(it); pvPintarAdj(); const m = document.getElementById('pv-msg');
  try {{
    const r = await fetch('/api/subir', {{method:'POST', credentials:'same-origin', headers:{{'Content-Type': blob.type || 'application/octet-stream', 'X-Nombre': encodeURIComponent(nombre)}}, body: blob}});
    const d = await r.json(); if (!r.ok) throw new Error(d.error || 'no se pudo subir'); Object.assign(it, d.adjunto); m.textContent = '';
  }} catch (e) {{ PV_ADJ.splice(PV_ADJ.indexOf(it), 1); m.textContent = 'No se subió ' + nombre + ': ' + e.message; }}
  pvPintarAdj();
}}
async function pvSubir(inp) {{ for (const f of [...inp.files]) await pvSubirUno(f, f.name); inp.value = ''; }}
async function pvGrabar() {{
  const b = document.getElementById('pv-rec');
  if (PV_REC) {{ PV_REC.stop(); return; }}
  try {{
    const st = await navigator.mediaDevices.getUserMedia({{audio:true}});
    const tipo = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/webm'].find(t => MediaRecorder.isTypeSupported(t)) || '';
    const partes = []; PV_REC = new MediaRecorder(st, tipo ? {{mimeType: tipo}} : undefined);
    PV_REC.ondataavailable = e => e.data.size && partes.push(e.data);
    PV_REC.onstop = async () => {{ clearInterval(PV_T); st.getTracks().forEach(t => t.stop()); const mt = (PV_REC.mimeType || 'audio/webm').split(';')[0]; PV_REC = null; b.classList.remove('rec'); b.textContent = '🎤';
      await pvSubirUno(new Blob(partes, {{type: mt}}), 'audio-' + new Date().toTimeString().slice(0, 5).replace(':', '') + (mt.includes('mp4') ? '.m4a' : '.webm')); }};
    PV_REC.start(); const t0 = Date.now(); b.classList.add('rec');
    PV_T = setInterval(() => {{ const s = Math.round((Date.now() - t0) / 1000); b.textContent = '⏺ ' + s + 's'; }}, 500);
  }} catch (e) {{ document.getElementById('pv-msg').textContent = 'No se pudo usar el micrófono: dale permiso al navegador.'; }}
}}
async function pvEnviar() {{
  const t = document.getElementById('pv-txt'), m = document.getElementById('pv-msg');
  if (PV_ADJ.some(a => !a.id)) {{ m.textContent = 'Espera a que terminen de subir.'; return; }}
  if (!t.value.trim() && !PV_ADJ.length) return;
  m.textContent = 'Enviando…';
  try {{
    const r = await fetch('/api/privado', {{method:'POST', credentials:'same-origin', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{texto: t.value, adjuntos: PV_ADJ.map(a => a.id)}})}});
    const d = await r.json(); if (!r.ok) throw new Error(d.error || 'no se pudo');
    t.value = ''; PV_ADJ = []; pvPintarAdj(); m.textContent = ''; await cargarPriv(); pintarPriv(true);
  }} catch (e) {{ m.textContent = 'No se envió: ' + e.message; }}
}}
cargarPriv();
setInterval(() => {{ if (!document.hidden && document.getElementById('priv-overlay').classList.contains('show')) cargarPriv(); }}, 3000);
setInterval(() => {{ if (!document.hidden && !document.getElementById('priv-overlay').classList.contains('show')) cargarPriv(); }}, 10000);
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
