#!/usr/bin/env python3
"""Parse Uber Eats correctamente por sucursal."""
import email, re, json
from email.header import decode_header
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime

def decode_mime(s):
    if s is None: return ""
    parts = decode_header(s)
    return "".join(t.decode(e or "utf-8", errors="replace") if isinstance(t, bytes) else t for t, e in parts)

def extract_text(msg):
    parts = []
    if msg.is_multipart():
        for p in msg.walk():
            ct = p.get_content_type()
            if ct in ("text/plain", "text/html"):
                payload = p.get_payload(decode=True)
                if payload:
                    text = payload.decode(p.get_content_charset() or "utf-8", errors="replace")
                    if ct == "text/html":
                        text = BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)
                    parts.append(text)
    return "\n".join(parts)

def parse_money(s):
    return float(s.replace(",", "").replace("MX$", "").replace("$", "").strip())

def parse_uber_date(date_str):
    try:
        # Ejemplo: "Mon, 05 Jan 2026 08:24:59 +0000"
        return datetime.strptime(date_str.strip()[:31].split(' +')[0].split(' -')[0].strip(),
                                 "%a, %d %b %Y %H:%M:%S").isoformat()
    except:
        return date_str

# Mapeo asunto → sucursal
def detectar_sucursal(asunto):
    # Buscar paréntesis
    m = re.search(r"\(([^)]+)\)", asunto)
    if m:
        sub = m.group(1).strip()
        # Normalizar
        norm = sub.upper()
        if "MONTECARLO" in norm: return "MONTECARLO"
        if "SAN MARCOS" in norm: return "SAN MARCOS"
        if "HDA" in norm or "HACIENDA" in norm: return "HACIENDA DEL RÍO"
        if "CURTO" in norm or "CINE" in norm: return "CURTO"
        if "VILLAS" in norm: return "VILLAS DEL REY"
        if "FOVISSSTE" in norm or "FOVISSTE" in norm: return "FOVISSTE"
        return sub  # devuelvo como está
    # Sin paréntesis = L Montejano / Fovissste (la principal)
    return "FOVISSTE"

files = sorted(Path("/home/tito/.openclaw/data/apps_correos/uber_resumen").glob("*.eml"))
print(f"Procesando {len(files)} correos\n")

resultados = []
for f in files:
    with open(f, "rb") as fh:
        msg = email.message_from_bytes(fh.read())
    asunto = decode_mime(msg.get("Subject"))
    fecha_raw = msg.get("Date", "")
    fecha_iso = parse_uber_date(fecha_raw)
    body = extract_text(msg)
    body_clean = re.sub(r'\s+', ' ', body).strip()

    sucursal = detectar_sucursal(asunto)

    # Periodo
    m_per = re.search(r"semana del (\d+/\d+/\d+)\s*al\s*(\d+/\d+/\d+)", asunto)
    periodo_ini = m_per.group(1) if m_per else ""
    periodo_fin = m_per.group(2) if m_per else ""

    def busca(patron):
        m = re.search(patron, body_clean)
        if m:
            try: return parse_money(m.group(1))
            except: return None
        return None

    pedidos     = busca(r"Pedidos\s+(\d+)\s+Pago total")
    pago_total  = busca(r"Pago total\s+MX\$([\d,\.]+)")
    ventas_tot  = busca(r"Total\s+\d+\s+MX\$([\d,\.]+)")
    tarifa      = busca(r"Tarifa de Uber Eats\s*-\s*MX\$([\d,\.]+)")
    iva_tarifa  = busca(r"IVA sobre la tarifa de Uber Eats\s*-\s*MX\$([\d,\.]+)")
    anuncios    = busca(r"Gasto total por anuncios[^-]*-\s*MX\$([\d,\.]+)")
    miscelaneos = busca(r"Misceláneos\s*-\s*MX\$([\d,\.]+)")

    resultados.append({
        "fecha_envio": fecha_iso,
        "sucursal": sucursal,
        "periodo_ini": periodo_ini,
        "periodo_fin": periodo_fin,
        "pedidos": pedidos,
        "venta_bruta": ventas_tot,
        "tarifa_uber": tarifa,
        "iva_tarifa": iva_tarifa,
        "anuncios": anuncios or 0,
        "miscelaneos": miscelaneos or 0,
        "pago_neto": pago_total,
    })

# Agrupar por sucursal
from collections import defaultdict
por_suc = defaultdict(lambda: {"n":0, "venta":0, "tarifa":0, "iva":0, "anuncios":0, "misc":0, "neto":0, "pedidos":0})
for r in resultados:
    if r["venta_bruta"]:
        d = por_suc[r["sucursal"]]
        d["n"] += 1
        d["venta"] += r["venta_bruta"]
        d["tarifa"] += r["tarifa_uber"] or 0
        d["iva"] += r["iva_tarifa"] or 0
        d["anuncios"] += r["anuncios"]
        d["misc"] += r["miscelaneos"]
        d["neto"] += r["pago_neto"] or 0
        d["pedidos"] += r["pedidos"] or 0

print(f"{'Sucursal':<25} {'Sem':>4} {'Venta':>15} {'Ped':>6} {'Com %':>7} {'Efect %':>8} {'Neto':>14} {'% Neto':>7}")
print("-"*100)
for s, d in sorted(por_suc.items(), key=lambda x: -x[1]["venta"]):
    com_pct = d["tarifa"]/d["venta"]*100
    efec_pct = (d["tarifa"]+d["iva"])/d["venta"]*100
    net_pct = d["neto"]/d["venta"]*100
    print(f"{s:<25} {d['n']:>4} ${d['venta']:>14,.2f} {d['pedidos']:>6} {com_pct:>6.2f}% {efec_pct:>7.2f}% ${d['neto']:>13,.2f} {net_pct:>6.2f}%")

# Calendario: día de la semana en que llega la liquidación
print("\n=== Calendario de liquidaciones Uber ===")
dow = defaultdict(int)
for r in resultados:
    if r["fecha_envio"] and r["fecha_envio"] != r["fecha_envio"].replace("T", " "):
        try:
            dt = datetime.fromisoformat(r["fecha_envio"])
            dias = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]
            dow[dias[dt.weekday()]] += 1
        except: pass
for d, n in sorted(dow.items(), key=lambda x: -x[1]):
    print(f"  {d}: {n} correos")

# Guardar json
Path("/home/tito/.openclaw/data/uber_por_sucursal.json").write_text(
    json.dumps({"por_sucursal": dict(por_suc), "detalles": resultados}, indent=2, default=str, ensure_ascii=False)
)
print(f"\nGuardado /home/tito/.openclaw/data/uber_por_sucursal.json")
