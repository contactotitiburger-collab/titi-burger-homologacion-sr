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
MONTECARLO_CONECTADA = False

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
que_sigue = [
    {"estado": "pendiente", "texto": "Conectar la computadora de Félix y la sucursal Montecarlo", "quien": "Félix"},
    {"estado": "pendiente", "texto": "Comparar cada sucursal contra la de Félix", "quien": "Tito"},
    {"estado": "pendiente", "texto": "Corregir las diferencias, una sucursal a la vez", "quien": "Tito, con tu aprobación"},
    {"estado": "pendiente", "texto": "Dejar las 6 sucursales exactamente iguales", "quien": "Tito"},
]

bloqueos = [
    {"texto": "Falta conectar la computadora de Félix (es la referencia para comparar) y la sucursal Montecarlo.", "quien": "Félix / Rafael"},
]

frase_dueno = "Ya revisamos las 5 sucursales conectadas. Sigue comparar cada una contra la de Félix y corregir lo que esté distinto."
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
    return f"""<div class="paso-item" onclick="mostrarToast({fase['id']})" ondblclick="ocultarToast()" role="button" tabindex="0">
      <div class="paso-fila">{circulo}{linea}</div>
      <div class="paso-nombre">{fase['nombre']}</div>
    </div>"""


def tarjeta_fase(fase):
    g1, g2 = fase["color"]
    anillo = ring(fase["pct"], 64, 7, "#FFFFFF", "rgba(255,255,255,.35)", "#FFFFFF", 15)
    return f"""<div class="fase-card" style="background:linear-gradient(135deg,{g1},{g2});" onclick="mostrarToast({fase['id']})" ondblclick="ocultarToast()" role="button" tabindex="0">
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
      <div class="objetivo-texto"><div>{nombre}</div><div>&nbsp;</div></div>
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
    --listo:#22C55E; --encurso:#1E90F0; --pendiente:#A0B4C4; --atorado:#F04E5E; --retraso:#F5B83D;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:"Poppins",system-ui,-apple-system,"Segoe UI",sans-serif;
    background:var(--bg); color:var(--ink); }}
  .topbar {{ height:120px; background:linear-gradient(180deg,var(--bg-top),var(--bg)); }}
  .wrap {{ max-width:960px; margin:-90px auto 0; padding:0 16px 32px; }}
  @media (min-width:700px) {{ .wrap {{ padding:0 24px 40px; }} }}
  .card {{ background:var(--card); border:1px solid var(--border); border-radius:20px;
    box-shadow:0 4px 16px rgba(20,60,100,0.06); padding:20px; margin-bottom:16px; }}
  @media (min-width:700px) {{ .card {{ padding:28px; }} }}
  h1 {{ font-size:22px; font-weight:600; margin:0 0 4px; }}
  @media (min-width:700px) {{ h1 {{ font-size:28px; }} }}
  .actualizado {{ color:var(--ink2); font-size:13px; margin:0 0 18px; }}
  h2 {{ font-size:17px; font-weight:600; margin:0 0 14px; }}
  p {{ font-size:15px; line-height:1.5; margin:0; }}
  .ring-wrap {{ display:flex; flex-direction:column; align-items:center; }}
  .ring-label {{ font-size:15px; color:var(--ink2); margin-top:6px; text-align:center; }}
  .vamos-top {{ display:flex; flex-direction:column; align-items:center; gap:14px; text-align:center; }}
  @media (min-width:560px) {{ .vamos-top {{ flex-direction:row; text-align:left; gap:24px; }} }}
  .vamos-texto p {{ margin-bottom:12px; }}
  .chip {{ display:inline-block; padding:6px 14px; border-radius:999px; font-size:13px; font-weight:600; color:#fff; }}
  .resumen-mini {{ border-top:1px solid var(--border); margin-top:16px; padding-top:14px; display:flex;
    flex-direction:column; gap:8px; }}
  .resumen-item {{ display:flex; align-items:flex-start; gap:8px; font-size:14px; color:var(--ink2); }}
  .resumen-item b {{ color:var(--ink); }}
  .resumen-punto {{ width:8px; height:8px; border-radius:50%; margin-top:6px; flex:0 0 8px; }}
  .plan-grid {{ display:flex; gap:24px; flex-wrap:wrap; }}
  .plan-dato {{ display:flex; flex-direction:column; }}
  .plan-num {{ font-size:28px; font-weight:600; color:var(--blue); }}
  .plan-label {{ font-size:13px; color:var(--ink2); max-width:160px; }}
  .paso-item, .fase-card {{ cursor:pointer; }}
  .paso-item:hover .paso-nombre, .fase-card:hover {{ opacity:.85; }}
  #toast {{ position:fixed; left:50%; bottom:28px; transform:translateX(-50%) translateY(16px);
    background:var(--ink); color:#fff; padding:14px 18px; border-radius:14px; max-width:320px;
    width:calc(100% - 32px); box-shadow:0 8px 24px rgba(20,60,100,0.25); opacity:0; pointer-events:none;
    transition:opacity .25s, transform .25s; z-index:50; }}
  #toast.show {{ opacity:1; transform:translateX(-50%) translateY(0); pointer-events:auto; }}
  #toast b {{ display:block; font-size:14px; margin-bottom:4px; }}
  #toast span {{ font-size:13px; opacity:.9; line-height:1.4; }}
  /* pasos */
  .pasos {{ display:flex; justify-content:space-between; margin:4px 0 24px; }}
  .paso-item {{ display:flex; flex-direction:column; align-items:center; flex:1; }}
  .paso-fila {{ display:flex; align-items:center; width:100%; }}
  .paso-circ {{ width:36px; height:36px; border-radius:50%; flex:0 0 36px; display:flex; align-items:center;
    justify-content:center; font-size:15px; font-weight:600; position:relative; }}
  .paso-circ.hecho {{ background:var(--blue); color:#fff; }}
  .paso-circ.en-curso {{ background:#fff; color:var(--blue); border:2px solid var(--blue); }}
  .paso-circ.en-curso .halo {{ position:absolute; inset:-6px; border-radius:50%; border:2px solid var(--blue); opacity:.35; }}
  .paso-circ.pendiente {{ background:#fff; color:var(--pendiente); border:2px solid var(--pendiente); }}
  .paso-conector {{ height:2px; background:var(--track); flex:1; margin:0 2px; }}
  .paso-nombre {{ font-size:12px; color:var(--ink2); text-align:center; margin-top:6px; max-width:80px; }}
  /* tarjetas de fase */
  .fases-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
  @media (min-width:700px) {{ .fases-grid {{ grid-template-columns:repeat(4,1fr); }} }}
  .fase-card {{ border-radius:16px; padding:16px; display:flex; flex-direction:column; align-items:center;
    color:#fff; min-height:150px; justify-content:center; }}
  .fase-nombre {{ font-size:13px; font-weight:600; margin-top:8px; text-align:center; color:#fff; }}
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
  /* bloqueos */
  .bloqueo-card {{ border-left:4px solid var(--atorado); }}
  .bloqueo-card-ok {{ border-left:4px solid var(--listo); }}
  .bloqueo-fila {{ margin-bottom:10px; }}
  .bloqueo-texto {{ font-size:15px; }}
  .bloqueo-quien {{ font-size:13px; color:var(--ink2); margin-top:3px; }}
  .bloqueo-ok {{ font-size:15px; color:var(--listo); font-weight:600; }}
  /* detalle */
  details summary {{ cursor:pointer; font-size:15px; font-weight:600; color:var(--blue); padding:4px 0;
    min-height:44px; display:flex; align-items:center; }}
  .detalle-fase {{ margin:14px 0; }}
  .detalle-fase b {{ font-size:15px; }}
  .detalle-fase ul {{ list-style:none; padding:0; margin:8px 0 0; }}
  .detalle-fase li {{ font-size:14px; padding:4px 0; color:var(--ink2); }}
  .detalle-fase li.ok {{ color:var(--ink); }}
  .detalle-total {{ font-size:14px; color:var(--ink2); margin-top:16px; padding-top:16px; border-top:1px solid var(--border); }}
  .detalle-total a {{ color:var(--blue); text-decoration:none; font-weight:600; }}
  footer {{ text-align:center; color:var(--ink2); font-size:13px; padding:8px 0 24px; }}
  .sin-dato {{ color:var(--ink2); font-size:14px; }}

  /* menu de 3 puntitos */
  .menu-btn {{ position:fixed; top:14px; left:14px; width:44px; height:44px; border-radius:50%;
    background:#fff; border:1px solid var(--border); box-shadow:0 2px 8px rgba(20,60,100,0.1);
    display:flex; align-items:center; justify-content:center; font-size:22px; color:var(--ink);
    cursor:pointer; z-index:40; line-height:1; }}
  .menu-dropdown {{ position:fixed; top:62px; left:14px; background:#fff; border:1px solid var(--border);
    border-radius:12px; box-shadow:0 8px 24px rgba(20,60,100,0.15); display:none; overflow:hidden; z-index:40; }}
  .menu-dropdown.show {{ display:block; }}
  .menu-dropdown a {{ display:flex; align-items:center; min-height:44px; padding:0 16px; font-size:14px;
    color:var(--ink); text-decoration:none; white-space:nowrap; cursor:pointer; }}
  .menu-dropdown a:hover {{ background:var(--bg); }}

  /* bitacora de objetivos (overlay de pantalla completa) */
  #bitacora-overlay {{ display:none; position:fixed; inset:0; background:var(--bg); z-index:60;
    overflow-y:auto; }}
  #bitacora-overlay.show {{ display:block; }}
  .bitacora-header {{ display:flex; justify-content:space-between; align-items:center;
    padding:20px 16px; }}
  .bitacora-header h2 {{ margin:0; }}
  .cerrar-btn {{ width:44px; height:44px; border-radius:50%; background:#fff; border:1px solid var(--border);
    display:flex; align-items:center; justify-content:center; font-size:20px; color:var(--ink);
    cursor:pointer; flex:0 0 44px; }}
  .objetivos-lista {{ max-width:720px; margin:0 auto; padding:0 16px 32px; }}
  .objetivo-fila {{ background:#fff; border:1px solid var(--border); border-radius:16px; padding:14px 16px;
    margin-bottom:10px; display:flex; justify-content:space-between; align-items:center; gap:12px; }}
  .objetivo-texto {{ font-size:15px; line-height:1.6; }}
  .objetivo-bolita {{ width:14px; height:14px; border-radius:50%; flex:0 0 14px; }}

  /* objetivo grande (acordeon de nivel 1) */
  .objetivo-grande {{ background:#fff; border:1px solid var(--border); border-radius:16px;
    margin-bottom:12px; overflow:hidden; }}
  .objetivo-grande > summary {{ list-style:none; cursor:pointer; padding:16px; font-size:16px;
    font-weight:600; display:flex; justify-content:space-between; align-items:center; gap:10px;
    min-height:44px; }}
  .objetivo-grande > summary::-webkit-details-marker {{ display:none; }}
  .objetivo-grande > summary::after {{ content:"›"; font-size:20px; color:var(--ink2); margin-left:auto;
    transform:rotate(90deg); transition:transform .2s; }}
  .objetivo-grande[open] > summary::after {{ transform:rotate(270deg); }}
  .objetivo-grande > summary > span:first-child {{ flex:1; }}
  .horas-badge {{ font-size:12px; font-weight:600; color:var(--blue); background:#eaf4fe;
    padding:4px 10px; border-radius:999px; white-space:nowrap; }}
  .subobjetivos {{ padding:0 16px 14px; display:flex; flex-direction:column; gap:8px; }}
  .subobjetivos .objetivo-fila {{ margin-bottom:0; box-shadow:none; }}

  /* ver que se trabajo (acordeon de nivel 2, dentro del objetivo grande) */
  .ver-horas {{ margin:0 16px 16px; border-top:1px solid var(--border); padding-top:10px; }}
  .ver-horas > summary {{ list-style:none; cursor:pointer; font-size:14px; color:var(--blue);
    font-weight:600; min-height:44px; display:flex; align-items:center; }}
  .ver-horas > summary::-webkit-details-marker {{ display:none; }}

  /* detalle por dia (acordeon de nivel 3, dentro de ver-horas) */
  .dia-detalle {{ margin:10px 0; background:var(--bg); border-radius:12px; padding:4px 12px; }}
  .dia-detalle > summary {{ list-style:none; cursor:pointer; font-size:13px; font-weight:600;
    padding:10px 0; min-height:44px; display:flex; align-items:center; justify-content:space-between; }}
  .dia-detalle > summary::-webkit-details-marker {{ display:none; }}
  .hoy-lista {{ padding-bottom:10px; }}
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
  <div class="objetivos-lista">
    {objetivos_html}
  </div>
</div>
<div class="wrap">

  <div class="card">
    <h1>Avance del proyecto — Titi Burger</h1>
    <p class="actualizado">Actualizado hoy a las {ahora}</p>

    <div class="vamos-top">
      {ring_principal}
      <div class="vamos-texto">
        <p>{frase_dueno}</p>
        <span class="chip" style="background:{ESTADO_COLOR[estado_chip]}">{ESTADO_TXT[estado_chip]}</span>
      </div>
    </div>

    <div class="resumen-mini">
      <div class="resumen-item"><span class="resumen-punto" style="background:var(--blue)"></span>
        <span><b>Hoy:</b> {horas_hoy_txt} en {len(actividades_hoy)} tareas</span></div>
      <div class="resumen-item"><span class="resumen-punto" style="background:var(--pendiente)"></span>
        <span><b>Sigue:</b> {que_sigue[0]['texto']}</span></div>
    </div>
  </div>

  <div class="card">
    <h2>El plan contratado</h2>
    <p style="margin-bottom:14px;">Arrancamos el {fmt_fecha_es(plan['inicio'])} (el lunes que regresaste con Félix, no el 1 de diciembre como decía el plan original). Termina estimado: {fmt_fecha_es(plan['fin_soporte'])}.</p>
    <div class="plan-grid">
      <div class="plan-dato"><span class="plan-num">{pct_tiempo_plan}%</span><span class="plan-label">del tiempo contratado</span></div>
      <div class="plan-dato"><span class="plan-num">{pct_horas_plan}%</span><span class="plan-label">de las {plan['horas_presupuestadas']} horas (llevamos {horas_usadas} h)</span></div>
    </div>
  </div>

  <div class="card">
    <h2>Las 4 etapas</h2>
    <div class="pasos">{pasos_html}</div>
    <div class="fases-grid">{tarjetas_html}</div>
  </div>

  <div class="card">
    <div class="hoy-header"><h2 style="margin:0">Qué se hizo hoy</h2><span class="hoy-total">{horas_hoy_txt}</span></div>
    {hoy_html}
  </div>

  <div class="card">
    <h2>Qué sigue</h2>
    {sigue_html}
  </div>

  <div class="card {bloqueo_card_class}">
    <h2>Necesitamos de ti</h2>
    {bloqueos_html}
  </div>

  <div class="card">
    <details>
      <summary>Ver detalle</summary>
      {detalle_html}
      <div class="detalle-total">
        Horas totales del proyecto: <b>{horas_total_txt}</b><br>
        <a href="../Analisis_Incongruencias_Tito_Lector.pdf" target="_blank">Ver PDF de diferencias encontradas</a><br>
        <a href="bitacora.html">Ver bitácora completa del proyecto</a>
      </div>
    </details>
  </div>

  <footer>Generado automáticamente por Tito · {datetime.now():%d-%m-%Y %H:%M}</footer>
</div>

<div id="toast"><b></b><span></span></div>
<script>
const FASES_INFO = {json.dumps({f["id"]: {"nombre": f["nombre"], "pct": f["pct"], "descripcion": f.get("descripcion", "")} for f in fases}, ensure_ascii=False)};
let toastTimer = null;
function mostrarToast(id) {{
  const info = FASES_INFO[id];
  if (!info) return;
  const toast = document.getElementById('toast');
  toast.querySelector('b').textContent = info.nombre + ' — ' + info.pct + '%';
  toast.querySelector('span').textContent = info.descripcion;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 9000);
}}
function ocultarToast() {{
  clearTimeout(toastTimer);
  document.getElementById('toast').classList.remove('show');
}}
document.getElementById('toast').addEventListener('click', ocultarToast);

function toggleMenu() {{
  document.getElementById('menu-dropdown').classList.toggle('show');
}}
function abrirBitacora() {{
  document.getElementById('menu-dropdown').classList.remove('show');
  document.getElementById('bitacora-overlay').classList.add('show');
}}
function cerrarBitacora() {{
  document.getElementById('bitacora-overlay').classList.remove('show');
}}
document.addEventListener('click', (e) => {{
  const dd = document.getElementById('menu-dropdown');
  const btn = document.querySelector('.menu-btn');
  if (dd.classList.contains('show') && !dd.contains(e.target) && e.target !== btn) {{
    dd.classList.remove('show');
  }}
}});
</script>
</body></html>"""

(PAGINA_DIR / "index.html").write_text(html, encoding="utf-8")
(OUT_DIR / "index.html").write_text(
    f'<!doctype html><meta http-equiv="refresh" content="0; url=/{TOKEN}/">'
    f'<a href="/{TOKEN}/">Ir a la página de avance</a>', encoding="utf-8")
print(f"% global: {pct_global}  |  horas hoy: {horas_hoy_txt}  |  horas totales: {horas_total_txt}")
print(f"archivo: {PAGINA_DIR / 'index.html'}")
print(f"token: {TOKEN}")
