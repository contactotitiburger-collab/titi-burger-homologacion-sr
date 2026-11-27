#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Busca estados financieros / documentos contables en los buzones del negocio
(Yahoo + Gmail), en TODAS las carpetas, desde 2023-09-01. Solo lectura (PEEK).
Estrategia liviana: 1 SEARCH SINCE por carpeta, luego FETCH de solo cabeceras
+ BODYSTRUCTURE (nombres de adjuntos) en lotes. Filtra en cliente. Solo baja
el cuerpo completo de los que hacen match, para guardar adjuntos.
Reconecta si el servidor tira la conexion.
"""
import imaplib, email, json, os, re, hashlib, time
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime

BASE = "/home/tito/.openclaw/data/estados_financieros"
os.makedirs(BASE, exist_ok=True)
SINCE = "01-Sep-2023"
imaplib._MAXLINE = 10_000_000

KEYWORDS = [
    "estado financiero", "estados financieros", "estado de resultados",
    "estado de resultado", "balance general", "balanza de comprobacion",
    "balanza", "posicion financiera", "flujo de efectivo", "declaracion anual",
    "cierre anual", "papeles de trabajo", "poliza", "auxiliar contable",
    "diot", "coeficiente de utilidad", "contabilidad", "estados de cuenta",
    "resultados del ejercicio", "cifras", "p&l", "estado de posicion",
]
FROM_TERMS = ["contador", "despacho", "contable", "contadores", "fiscal", "timsa"]
CLASS_KEYWORDS = {
    "Estados financieros": ["estados financieros", "estado financiero", "posicion financiera"],
    "Estado de resultados": ["estado de resultados", "estado de resultado", "resultados del ejercicio"],
    "Balance general": ["balance general"],
    "Balanza de comprobacion": ["balanza"],
    "Flujo de efectivo": ["flujo de efectivo"],
    "Declaracion anual/ISR": ["declaracion anual", "cierre anual", "coeficiente de utilidad"],
    "Poliza/Auxiliar/Papeles": ["poliza", "auxiliar", "papeles de trabajo"],
    "DIOT/Impuestos": ["diot", "impuestos"],
    "Contabilidad (gral)": ["contabilidad", "contable", "cifras", "p&l"],
}
DL_EXT = {".pdf", ".xlsx", ".xls", ".csv", ".xml", ".zip"}
NOISE_FROM = ["gnp", "no-reply", "noreply", "notificacion", "uber", "rappi",
              "didi", "mercadolibre", "amazon", "facebook", "linkedin", "clip.mx"]

def dh(s):
    if not s: return ""
    try: return str(make_header(decode_header(s)))
    except Exception: return s
def norm(s):
    return (s or "").lower().translate(str.maketrans("áéíóúñü", "aeiounu"))
def safe(s, n=45):
    return (re.sub(r"[^a-z0-9]+", "_", norm(s)).strip("_")[:n]) or "sin"

results = []

class Mailbox:
    def __init__(self, host, port, user, pw):
        self.host, self.port, self.user, self.pw = host, port, user, pw
        self.M = None; self.connect()
    def connect(self):
        if self.M:
            try: self.M.logout()
            except Exception: pass
        self.M = imaplib.IMAP4_SSL(self.host, self.port); self.M.login(self.user, self.pw)
    def folders(self):
        out = []
        typ, data = self.M.list()
        if typ != "OK": return out
        for raw in data or []:
            if raw is None: continue
            line = raw.decode(errors="replace") if isinstance(raw, bytes) else raw
            if "\\Noselect" in line: continue
            m = re.search(r'"([^"]*)"\s*$', line)
            out.append(m.group(1) if m else line.split()[-1])
        return out

def parse_filenames_from_bodystructure(bs):
    # extrae nombres de archivo de un dump de BODYSTRUCTURE
    names = []
    for m in re.finditer(r'"(?:NAME|FILENAME)"\s+"([^"]+)"', bs, re.I):
        names.append(m.group(1))
    # tambien patrones name= dentro de disposition
    return names

def process_account(name, host, port, user, pw):
    print(f"\n=== {name}: {host} / {user} ===", flush=True)
    try:
        mb = Mailbox(host, port, user, pw)
    except Exception as e:
        print(f"!!! LOGIN FALLO {name}: {e}", flush=True)
        results.append({"_login_error": f"{name}: {e}"}); return
    folders = mb.folders()
    print(f"Carpetas ({len(folders)}): {folders}", flush=True)
    seen = set()

    for folder in folders:
        # fresh connection por carpeta para evitar EOF acumulado
        for attempt in range(3):
            try:
                mb.connect()
                typ, _ = mb.M.select(f'"{folder}"', readonly=True)
                if typ != "OK":
                    typ, _ = mb.M.select(folder, readonly=True)
                if typ != "OK":
                    print(f"  [skip select] {folder}", flush=True); ids = []; break
                typ, d = mb.M.search(None, f'(SINCE "{SINCE}")')
                ids = d[0].split() if (typ == "OK" and d and d[0]) else []
                break
            except Exception as e:
                print(f"  [retry {folder} {attempt}] {e}", flush=True); time.sleep(2); ids = []
        if not ids:
            continue
        print(f"  {folder}: {len(ids)} mensajes desde {SINCE}", flush=True)

        # FETCH cabeceras + estructura en lotes
        cand = []  # (num, subject, frm, dstr, year, filenames)
        B = 200
        for i in range(0, len(ids), B):
            chunk = ids[i:i+B]
            idset = b",".join(chunk)
            for attempt in range(3):
                try:
                    typ, data = mb.M.fetch(idset, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)] BODYSTRUCTURE)")
                    break
                except Exception as e:
                    print(f"    [refetch hdr {folder} {i}] {e}", flush=True)
                    try: mb.connect(); mb.M.select(f'"{folder}"', readonly=True)
                    except Exception: pass
                    time.sleep(2); typ, data = "NO", None
            if typ != "OK" or not data:
                continue
            # emparejar respuestas: cada item tuple trae header; BODYSTRUCTURE en el prefijo bytes
            for item in data:
                if not isinstance(item, tuple): continue
                meta = item[0].decode(errors="replace") if isinstance(item[0], (bytes, bytearray)) else str(item[0])
                num_m = re.match(r"(\d+)", meta.strip())
                num = num_m.group(1).encode() if num_m else None
                hdr = item[1] or b""
                try: msg = email.message_from_bytes(hdr)
                except Exception: continue
                subject = dh(msg.get("Subject", "")); frm = dh(msg.get("From", ""))
                try:
                    dt = parsedate_to_datetime(msg.get("Date", "")); dstr = dt.strftime("%Y-%m-%d"); year = dt.year
                except Exception:
                    dstr = (msg.get("Date","") or "")[:10]; year = 0
                fns = parse_filenames_from_bodystructure(meta)
                cand.append((num, subject, frm, dstr, year, fns))

        # filtrar candidatos
        for num, subject, frm, dstr, year, fns in cand:
            hay = norm(subject + " " + frm + " " + " ".join(fns))
            tipos = [lbl for lbl, kws in CLASS_KEYWORDS.items() if any(k in hay for k in kws)]
            kw_hit = any(k in hay for k in KEYWORDS)
            frm_hit = any(t in norm(frm) for t in FROM_TERMS)
            folder_hit = norm(folder) in ("timsa", "timsa stefany", "sat")  # carpetas contables
            if not (kw_hit or frm_hit or folder_hit or tipos):
                continue
            if any(x in norm(frm) for x in NOISE_FROM) and not tipos and not frm_hit:
                continue
            key = (frm, subject, dstr)
            if key in seen: continue
            seen.add(key)

            # bajar cuerpo completo para adjuntos
            saved = []; att_all = list(fns)
            if num:
                for attempt in range(3):
                    try:
                        typ, mdata = mb.M.fetch(num, "(BODY.PEEK[])")
                        break
                    except Exception:
                        try: mb.connect(); mb.M.select(f'"{folder}"', readonly=True)
                        except Exception: pass
                        time.sleep(1); typ, mdata = "NO", None
                if typ == "OK" and mdata:
                    raw = b"".join(p[1] for p in mdata if isinstance(p, tuple) and p[1])
                    try: full = email.message_from_bytes(raw)
                    except Exception: full = None
                    if full:
                        att_all = []
                        ydir = os.path.join(BASE, str(year) if year else "sin_fecha")
                        for p in full.walk():
                            fn = p.get_filename()
                            if not fn: continue
                            fn = dh(fn); att_all.append(fn)
                            ext = os.path.splitext(fn)[1].lower()
                            if ext not in DL_EXT: continue
                            try: payload = p.get_payload(decode=True)
                            except Exception: payload = None
                            if not payload: continue
                            os.makedirs(ydir, exist_ok=True)
                            b = f"{dstr}_{safe(frm.split('<')[0],22)}_{safe(subject,32)}_{safe(os.path.splitext(fn)[0],22)}{ext}"
                            path = os.path.join(ydir, b)
                            if os.path.exists(path):
                                path = os.path.join(ydir, f"{os.path.splitext(b)[0]}_{hashlib.md5(payload).hexdigest()[:6]}{ext}")
                            try:
                                open(path, "wb").write(payload)
                                saved.append((os.path.basename(path), len(payload)))
                            except Exception as e:
                                saved.append((f"ERROR:{fn}:{e}", 0))
            results.append({"account": name, "folder": folder, "date": dstr, "year": year,
                            "from": frm, "subject": subject, "attachments": att_all,
                            "tipos": tipos or (["(remitente/carpeta contable)"] if (frm_hit or folder_hit) else ["(keyword)"]),
                            "saved": saved})
            print(f"    MATCH [{dstr}] {frm[:36]} | {subject[:46]} | adj={len(att_all)} sav={len(saved)} | {tipos}", flush=True)
    try: mb.M.logout()
    except Exception: pass

def main():
    y = json.load(open("/home/tito/.openclaw/credentials/yahoo/creds.json"))
    g = json.load(open("/home/tito/.openclaw/credentials/gmail/creds.json"))
    process_account("YAHOO", y["imap_host"], y["imap_port"], y["user"], y["password"])
    process_account("GMAIL", g["imap_host"], g["imap_port"], g["user"], g["password"])
    with open(os.path.join(BASE, "_resultados.json"), "w") as f:
        json.dump([r for r in results if "_login_error" not in r], f, ensure_ascii=False, indent=2, default=str)
    errs = [r["_login_error"] for r in results if "_login_error" in r]
    open(os.path.join(BASE, "_login_errors.txt"), "w").write("\n".join(errs))
    print(f"\n=== TOTAL matches: {len([r for r in results if '_login_error' not in r])} ; login errors: {errs}", flush=True)

if __name__ == "__main__":
    main()
