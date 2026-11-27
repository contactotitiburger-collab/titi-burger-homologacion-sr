#!/usr/bin/env python3
"""Parsear TODAS las liquidaciones de Uber Eats y extraer números."""
import email, re, json
from email.header import decode_header
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime

def decode_mime(s):
    if s is None: return ""
    parts = decode_header(s)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            try: text = text.decode(enc or "utf-8", errors="replace")
            except: text = text.decode("utf-8", errors="replace")
        out.append(text)
    return "".join(out)

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
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            text = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
            if msg.get_content_type() == "text/html":
                text = BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)
            parts.append(text)
    return "\n".join(parts)

def parse_money(s):
    return float(s.replace(",", "").replace("MX$", "").replace("$", "").strip())

files = sorted(Path("/home/tito/.openclaw/data/apps_correos/uber_resumen").glob("*.eml"))
print(f"Procesando {len(files)} correos\n")

resultados = []
for f in files:
    with open(f, "rb") as fh:
        msg = email.message_from_bytes(fh.read())
    asunto = decode_mime(msg.get("Subject"))
    fecha = msg.get("Date", "")
    body = extract_text(msg)
    body_clean = re.sub(r'\s+', ' ', body).strip()

    # Extraer sucursal del asunto
    # Patrones: "Titi Burger, Las Originales al Carbon" (sin parentesis) o "(SUCURSAL)"
    m_suc = re.search(r"Titi Burger,\s*Las Originales al Carbon?[ó]?n?\s*(?:\(([^)]+)\))?", asunto)
    sucursal = m_suc.group(1) if m_suc and m_suc.group(1) else "L Montejano (default)"

    # Extraer periodo del asunto
    m_per = re.search(r"semana del (\d+/\d+/\d+)\s*al\s*(\d+/\d+/\d+)", asunto)
    periodo_ini = m_per.group(1) if m_per else ""
    periodo_fin = m_per.group(2) if m_per else ""

    # Del body: extraer números
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
    ventas_net  = busca(r"Ventas netas\s+MX\$([\d,\.]+)")
    anuncios    = busca(r"Gasto total por anuncios[^-]*-\s*MX\$([\d,\.]+)")
    miscelaneos = busca(r"Misceláneos\s*-\s*MX\$([\d,\.]+)")
    ajustes     = busca(r"Ajustes por un error[^-]*-\s*MX\$([\d,\.]+)")

    resultados.append({
        "archivo": f.name,
        "fecha": fecha,
        "sucursal": sucursal,
        "periodo_ini": periodo_ini,
        "periodo_fin": periodo_fin,
        "pedidos": pedidos,
        "venta_bruta": ventas_tot,
        "tarifa_uber": tarifa,
        "iva_tarifa": iva_tarifa,
        "ventas_netas": ventas_net,
        "anuncios": anuncios or 0,
        "miscelaneos": miscelaneos or 0,
        "ajustes": ajustes or 0,
        "pago_neto": pago_total,
    })

# Calcular % de comisión efectiva
for r in resultados:
    if r["venta_bruta"] and r["tarifa_uber"]:
        r["comision_pct"] = r["tarifa_uber"] / r["venta_bruta"] * 100
        r["efectivo_pct"] = (r["tarifa_uber"] + (r["iva_tarifa"] or 0)) / r["venta_bruta"] * 100
        # % total descuentos vs venta bruta
        gastos_totales = (r["tarifa_uber"] + (r["iva_tarifa"] or 0) +
                          r["anuncios"] + r["miscelaneos"] + r["ajustes"])
        r["total_gastos_pct"] = gastos_totales / r["venta_bruta"] * 100

# Estadísticas por sucursal
por_suc = {}
for r in resultados:
    s = r["sucursal"]
    if s not in por_suc:
        por_suc[s] = {"n": 0, "venta_total": 0, "tarifa_total": 0, "iva_total": 0,
                      "anuncios_total": 0, "misc_total": 0, "ajustes_total": 0, "pago_total": 0,
                      "pedidos_total": 0}
    if r["venta_bruta"]:
        por_suc[s]["n"] += 1
        por_suc[s]["venta_total"] += r["venta_bruta"]
        por_suc[s]["tarifa_total"] += r["tarifa_uber"] or 0
        por_suc[s]["iva_total"] += r["iva_tarifa"] or 0
        por_suc[s]["anuncios_total"] += r["anuncios"] or 0
        por_suc[s]["misc_total"] += r["miscelaneos"] or 0
        por_suc[s]["ajustes_total"] += r["ajustes"] or 0
        por_suc[s]["pago_total"] += r["pago_neto"] or 0
        por_suc[s]["pedidos_total"] += r["pedidos"] or 0

print(f"{'Sucursal':<35} {'Sem':>4} {'Venta bruta':>15} {'Comisión %':>10} {'Efectivo %':>10} {'Neto':>15}")
print("-" * 100)
for s, d in por_suc.items():
    if d["n"] > 0:
        com_pct = d["tarifa_total"] / d["venta_total"] * 100
        efec_pct = (d["tarifa_total"] + d["iva_total"]) / d["venta_total"] * 100
        print(f"{s:<35} {d['n']:>4} ${d['venta_total']:>14,.2f} {com_pct:>9.2f}% {efec_pct:>9.2f}% ${d['pago_total']:>14,.2f}")

# Global
if resultados:
    v_total = sum(r["venta_bruta"] or 0 for r in resultados)
    t_total = sum(r["tarifa_uber"] or 0 for r in resultados)
    iva_total = sum(r["iva_tarifa"] or 0 for r in resultados)
    a_total = sum(r["anuncios"] for r in resultados)
    m_total = sum(r["miscelaneos"] for r in resultados)
    j_total = sum(r["ajustes"] for r in resultados)
    p_total = sum(r["pago_neto"] or 0 for r in resultados)
    print("-" * 100)
    print(f"{'TOTAL':<35} {len(resultados):>4} ${v_total:>14,.2f} {t_total/v_total*100:>9.2f}% {(t_total+iva_total)/v_total*100:>9.2f}% ${p_total:>14,.2f}")
    print()
    print(f"Venta bruta total (histórica): ${v_total:,.2f}")
    print(f"Comisión Uber:  ${t_total:,.2f} ({t_total/v_total*100:.2f}%)")
    print(f"IVA comisión:   ${iva_total:,.2f} ({iva_total/v_total*100:.2f}%)")
    print(f"Anuncios:       ${a_total:,.2f} ({a_total/v_total*100:.2f}%)")
    print(f"Misceláneos:    ${m_total:,.2f} ({m_total/v_total*100:.2f}%)")
    print(f"Ajustes error:  ${j_total:,.2f} ({j_total/v_total*100:.2f}%)")
    total_desc = t_total + iva_total + a_total + m_total + j_total
    print(f"TOTAL descuentos: ${total_desc:,.2f} ({total_desc/v_total*100:.2f}% del bruto)")
    print(f"Pago neto:      ${p_total:,.2f} (Titi recibe {p_total/v_total*100:.2f}% del bruto)")

# Guardar
Path("/home/tito/.openclaw/data/uber_liquidaciones.json").write_text(
    json.dumps({"resumen_por_sucursal": por_suc, "detalles": resultados}, indent=2, default=str, ensure_ascii=False)
)
print("\nGuardado: /home/tito/.openclaw/data/uber_liquidaciones.json")
