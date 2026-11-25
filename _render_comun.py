"""Funciones compartidas entre generar_avance_v2.py y generar_bitacora.py.
Un solo lugar para el formato del timeline — para que no se vuelvan a desincronizar
los dos generadores (eso fue justo el bug del 25-nov-2026)."""


def pct(lista):
    return round(100 * sum(1 for x in lista if x["hecho"]) / len(lista)) if lista else 0


def parse_min(dur):
    dur = dur.strip()
    try:
        if "min" in dur:
            return int(dur.replace("min", "").strip())
        if "h" in dur:
            partes = dur.replace("h", " ").replace("min", "").split()
            return int(partes[0]) * 60 + (int(partes[1]) if len(partes) > 1 else 0)
    except Exception:
        pass
    return 0


def render_timeline(pasos):
    """Linea de tiempo vertical: numero + titulo a la izquierda, minutos a la derecha."""
    items = []
    for p in pasos:
        items.append(f"""
        <div class="paso">
          <div class="paso-num">{p['parte']}</div>
          <div class="paso-linea"></div>
          <div class="paso-cuerpo">
            <div class="paso-top"><b>{p['titulo']}</b><span class="paso-tiempo">{p['minutos']} min</span></div>
            <div class="paso-detalle">{p.get('detalle', '')}</div>
          </div>
        </div>""")
    return f'<div class="timeline">{"".join(items)}</div>'


def render_meter(label, pct_val, hue_hex, size=168, stroke=15):
    """Anillo de progreso (donut) con % al centro — spec 'Meter' del skill dataviz:
    el relleno lleva el color de acento, la pista es el mismo tono mas tenue
    (nunca gris generico), el numero va en tinta primaria (blanco), nunca del
    color de la serie."""
    r = (size - stroke) / 2
    c = 2 * 3.14159265 * r
    offset = c * (1 - pct_val / 100)
    return f"""
    <div class="meter">
      <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
        <circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none"
          stroke="{hue_hex}22" stroke-width="{stroke}" />
        <circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none"
          stroke="{hue_hex}" stroke-width="{stroke}" stroke-linecap="round"
          stroke-dasharray="{c:.2f}" stroke-dashoffset="{offset:.2f}"
          transform="rotate(-90 {size/2} {size/2})" />
        <text x="50%" y="52%" text-anchor="middle" dominant-baseline="middle"
          class="meter-pct">{pct_val}%</text>
      </svg>
      <div class="meter-label">{label}</div>
    </div>"""


METER_CSS = """
.meters { display:flex; gap:2rem; justify-content:center; flex-wrap:wrap; }
.meter { text-align:center; }
.meter-pct { font: 700 1.5rem system-ui, -apple-system, "Segoe UI", sans-serif; fill:#ffffff; }
.meter-label { color:#c3c2b7; font-size:.78rem; letter-spacing:.06em; text-transform:uppercase;
  margin-top:.5rem; font-weight:600; }
"""

TIMELINE_CSS = """
.timeline { position:relative; padding-left:0; }
.paso { display:flex; gap:14px; position:relative; }
.paso-num { flex:0 0 32px; height:32px; border-radius:50%; background:#ff7a45; color:#0f1115;
  display:flex; align-items:center; justify-content:center; font-weight:700; font-size:.95rem; z-index:1; }
.paso-linea { position:absolute; left:15px; top:32px; bottom:-22px; width:2px; background:#2a2e37; }
.paso:last-child .paso-linea { display:none; }
.paso-cuerpo { flex:1; padding-bottom:22px; }
.paso-top { display:flex; justify-content:space-between; align-items:baseline; gap:10px; }
.paso-top b { font-size:.95rem; }
.paso-tiempo { color:#ffb347; font-size:.8rem; font-weight:600; white-space:nowrap; }
.paso-detalle { color:#aaa; font-size:.82rem; margin-top:3px; }
"""
