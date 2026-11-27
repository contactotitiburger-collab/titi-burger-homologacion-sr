#!/usr/bin/env python3
"""nomina_flaguear_sesame.py — flaguea la nómina usando SOLO SESAME (sin horario).

Desde la semana 30 ya no hay archivo de horario s{N}_*.json (SESAME es la fuente).
Este script reemplaza a nomina_flaguear.py cuando NO hay horario:

  - DESCANSO de cada quién se calcula por PATRÓN de las 3 semanas de SESAME previas
    disponibles (el/los día(s) que casi nunca ficha = descanso). Así no se marca el
    descanso como "no checó" (evita falsas alarmas, ver lección 15-jul).
  - "DÍAS QUE SE FUE" = días laborables (no-descanso) SIN checada en SESAME esa semana.
  - REGLA DINERO (confirmada Rafael 21-jul): no checar ≠ faltar → se paga normal y
    CONSERVA el bono puntual. Solo una FALTA REAL confirmada por Nancy quita el bono.
    Por eso: si el generador dejó el bono en 0 (V<H), se RESTAURA V=H. No se quita nada.
  - Casos aparte (patrón, oficina/cocina, captura manual, incapacidad) → verde, sin flag.

  Colores (exactos):  🟢 verde rgb(0.72,0.88,0.72)  ·  🟡 khaki rgb(1,0.92,0.55)
  Nota + color en la columna TOTAL (AJ). Día no-checó: celda del día en khaki.

Uso:  python3 nomina_flaguear_sesame.py --sem 32 [--sheet <id>] [--dry]
"""
import json, argparse, unicodedata, sys, re
from pathlib import Path
from datetime import datetime
import openpyxl
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE = Path.home()/".openclaw"
TOK = BASE/"credentials/google/oauth/tito_tokens.json"
CAT = BASE/"data/nomina/catalogo_empleados_s27.json"
FOLDER = "1qBpjmHZr_-F-bBo793J_7I6Q1yPWEHnU"

VERDE = {"red":0.72,"green":0.88,"blue":0.72}
KHAKI = {"red":1.0,"green":0.92,"blue":0.55}
WHITE = {"red":1,"green":1,"blue":1}
DIAS_ABR = ["lun","mar","mié","jue","vie","sáb","dom"]
MESES = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"]

# Verde sin flag (no son carreta que fiche para el bono): patrón, oficina/cocina, manual, incapacidad
GREEN = {
    "MEJIA ORTEGA FELIX":     "✅ Patrón — no ficha",
    "FRANCISCO  JAVIER":      "✅ Captura manual (Bubu) — bono completo",
    "LEYLANI MARTINEZ":       "✅ Captura manual (Leylani) — bono completo",
    "GONZALEZ MONTOYA BRYAN": "✅ Medio tiempo (Bryan) — captura manual",
    "JIMENEZ SERRANO AMERICA":"✅ Incapacidad (América) — no aplica checador",
    "BAUTISTA GOMEZ ANDRONICA":"✅ Oficina/cocina — fuera de carreta",
    "DOMINGUEZ LOPEZ YAZMIN": "✅ Cocina — fuera de carreta",
    "RIOS OROZCO SANDRA":     "✅ Cocina — fuera de carreta",
    "AGUIRRE MEJIA DAVID":    "✅ Oficina/administrativo — fuera de carreta",
    "SERRANO CEDANO NANCY":   "✅ Oficina/administrativo — fuera de carreta",
    "CORDOVA OYARBIDE RAFAEL":"✅ Oficina/administrativo — fuera de carreta",
}


def normset(s):
    s=unicodedata.normalize('NFD',str(s)); s=''.join(c for c in s if unicodedata.category(c)!='Mn')
    return set(w for w in s.upper().replace('.',' ').split() if len(w)>2)

def norm(s):
    s=unicodedata.normalize('NFD',str(s)); return ''.join(c for c in s if unicodedata.category(c)!='Mn').upper()

def a1(col1,row):
    s=""; i=col1
    while i: i,r=divmod(i-1,26); s=chr(65+r)+s
    return f"{s}{row}"

def clients():
    t=json.loads(TOK.read_text())
    c=Credentials(token=t["token"],refresh_token=t["refresh_token"],token_uri=t["token_uri"],
                  client_id=t["client_id"],client_secret=t["client_secret"],scopes=t["scopes"])
    if not c.valid: c.refresh(Request()); t["token"]=c.token; TOK.write_text(json.dumps(t,indent=2))
    return build("sheets","v4",credentials=c), build("drive","v3",credentials=c)

def buscar_sheet(drv, sem):
    pref=f"Nómina - Semana {sem} ("
    q=(f"name contains 'Semana {sem}' and trashed=false and '{FOLDER}' in parents "
       "and mimeType='application/vnd.google-apps.spreadsheet'")
    fs=drv.files().list(q=q, fields="files(id,name,createdTime)", orderBy="createdTime desc").execute().get('files',[])
    fs=[f for f in fs if f['name'].startswith(pref)]
    if not fs: sys.exit(f"No encontré Sheet para Semana {sem}")
    for dup in fs[1:]:
        drv.files().update(fileId=dup['id'], body={"trashed":True}).execute()
        print(f"🗑️  duplicado a papelera: {dup['id']}")
    return fs[0]['id']

def sesame_weekdays(sem):
    """{emp_str: set(weekday 0..6)} de un export SESAME."""
    p=BASE/f"data/nomina/sesame_export_sem{sem}.xlsx"
    if not p.exists(): return {}
    wb=openpyxl.load_workbook(p, data_only=True); ws=wb[wb.sheetnames[0]]; d={}
    for r in ws.iter_rows(min_row=2, values_only=True):
        emp,tipo,ident,fecha,act,grupo,ent,*_=(list(r)+[None]*8)[:8]
        if not emp or str(emp).strip() in ('TOTAL',''): continue
        if not ent or str(ent).strip() in ('','-'): continue
        try: dt=datetime.strptime(str(fecha).strip(),'%d/%m/%Y')
        except: continue
        d.setdefault(str(emp).strip(),set()).add(dt.weekday())
    return d

def patron_descanso(sem):
    """Cuenta checadas por weekday en las 3 semanas previas disponibles."""
    cnt={}
    encontradas=0
    wk=sem-1
    while encontradas<3 and wk>=1:
        p=BASE/f"data/nomina/sesame_export_sem{wk}.xlsx"
        if p.exists():
            encontradas+=1
            for emp,wds in sesame_weekdays(wk).items():
                cnt.setdefault(emp,[0]*7)
                for w in wds: cnt[emp][w]+=1
        wk-=1
    return cnt

def descanso_de(emp, patron):
    c=patron.get(emp)
    if not c: return set()
    z={i for i in range(7) if c[i]==0}
    if z: return z
    m=min(c); return {c.index(m)}

def match(nom, universo):
    tgt=normset(nom); best=None; bs=0
    for e in universo:
        sc=len(normset(e)&tgt)
        if sc>bs: bs=sc; best=e
    return best if bs>=2 else None

def num(x):
    x=str(x).replace('$','').strip()
    if x in('','-'): return 0.0
    return float(x.replace('.','').replace(',','.'))

def _paint(sid,row,col0,color,bold=None):
    fmt={"backgroundColor":color}; fields="userEnteredFormat.backgroundColor"
    if bold is not None:
        fmt["textFormat"]={"bold":bold}; fields="userEnteredFormat(backgroundColor,textFormat)"
    return {"repeatCell":{"range":{"sheetId":sid,"startRowIndex":row-1,"endRowIndex":row,
            "startColumnIndex":col0,"endColumnIndex":col0+1},"cell":{"userEnteredFormat":fmt},"fields":fields}}

def _note(sid,row,col0,note):
    return {"updateCells":{"range":{"sheetId":sid,"startRowIndex":row-1,"endRowIndex":row,
            "startColumnIndex":col0,"endColumnIndex":col0+1},"rows":[{"values":[{"note":note}]}],"fields":"note"}}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--sem", type=int, required=True)
    ap.add_argument("--sheet")
    ap.add_argument("--dry", action="store_true")
    a=ap.parse_args()

    sh, drv = clients()
    sheet_id = a.sheet or buscar_sheet(drv, a.sem)
    meta = sh.spreadsheets().get(spreadsheetId=sheet_id).execute()
    tp = next(s['properties'] for s in meta['sheets'] if s['properties']['title'].strip()=='NOMINA')
    title, sid = tp['title'], tp['sheetId']

    grid = sh.spreadsheets().values().get(spreadsheetId=sheet_id,
        range=f"'{title}'!F8:AJ40", valueRenderOption="FORMATTED_VALUE").execute().get('values',[])
    hdr=(grid[0] if grid else [])+['']*40
    # columnas L..R = idx 6..12 dentro del grid (F=0). weekday por fecha del encabezado.
    col_wd={}   # idx_grid -> weekday
    for k in range(7):
        m=re.search(r"(\d+)-([a-z]+)", norm(str(hdr[6+k])).lower())
        if m:
            dd=int(m.group(1)); mm=MESES.index(m.group(2)[:3]) + 1 if m.group(2)[:3] in MESES else None
            if mm:
                try: col_wd[6+k]=datetime(2026,mm,dd).weekday()
                except: pass

    ses32=sesame_weekdays(a.sem)
    patron=patron_descanso(a.sem)

    reqs=[]; val_updates=[]; resumen={"verde":[],"nocheco":[],"aparte":[]}

    for gi,row in enumerate(grid[1:], start=9):
        row=row+['']*40
        nombre=str(row[0]).strip()
        if not nombre: continue
        nU=norm(nombre)

        # ¿verde sin flag?
        gkey=next((k for k in GREEN if k in nU), None)
        H=num(row[2]); V=num(row[16])   # H=bono puntual ref (col8) ; V=bono puntual real (col22)
        # Bryan (medio tiempo, captura manual) y América (incapacidad): NO tocar bono automático.
        NO_TOCAR_BONO = ("GONZALEZ MONTOYA BRYAN" in nU) or ("JIMENEZ SERRANO AMERICA" in nU)
        if gkey:
            # conservar bono si se lo borraron (oficina/cocina/manual-completo); Bryan/América aparte
            if H>0 and V<H and not NO_TOCAR_BONO and not a.dry:
                val_updates.append({"range":f"'{title}'!{a1(22,gi)}","values":[[H]]})
            reqs.append(_paint(sid, gi, 35, VERDE, bold=True)); reqs.append(_note(sid, gi, 35, GREEN[gkey]))
            resumen["aparte"].append(nombre);
            btxt = f"  [bono {int(V)}→{int(H)}]" if (H>0 and V<H and not NO_TOCAR_BONO) else (
                   "  [bono lo captura Nancy manual]" if (H>0 and V<H and NO_TOCAR_BONO) else "")
            print(f"  ⚪ {nombre[:28]:28} {GREEN[gkey]}{btxt}")
            continue

        # carreta: cruzar SESAME
        ses = match(nombre, ses32)
        checked = ses32.get(ses, set()) if ses else set()
        desc = descanso_de(ses, patron) if ses else set()
        nofiche=[]
        for gk,wd in col_wd.items():
            col1=6+gk+1   # columna real 1-based dentro del sheet (F=6): F idx0 -> col6 ; L idx6 -> col12
            if wd in checked:
                reqs.append(_paint(sid, gi, col1-1, WHITE))
            elif wd in desc:
                pass  # descanso: no flag
            else:
                nofiche.append(wd)
                reqs.append(_paint(sid, gi, col1-1, KHAKI))

        nd=len(nofiche)
        # bono: CONSERVAR solo en casos leves (≤2 días no-checó). Nunca quitar automático.
        # Casos pesados (≥3 días sin checar) huelen a vacaciones/incap/permiso/falta → lo decide Nancy.
        bono_txt=""
        if H>0 and V<H and nd<=2:
            if not a.dry: val_updates.append({"range":f"'{title}'!{a1(22,gi)}","values":[[H]]})
            bono_txt=f"  [bono {int(V)}→{int(H)}]"
        elif H>0 and V<H and nd>=3:
            bono_txt="  [bono PENDIENTE Nancy]"

        if not nofiche:
            n=len(checked)
            reqs.append(_paint(sid, gi, 35, VERDE, bold=True))
            reqs.append(_note(sid, gi, 35, f"✅ Checó completo ({n} días)"))
            resumen["verde"].append(nombre)
            print(f"  🟢 {nombre[:28]:28} checó completo ({n}){bono_txt}")
        else:
            fechas=", ".join(f"{DIAS_ABR[wd]} {str(hdr[6+[c for c,w in col_wd.items() if w==wd][0]-6]).strip()}" for wd in sorted(nofiche))
            if nd<=2:
                nota=(f"🟡 NO checó en SESAME: {fechas} ({nd} día(s)). "
                      f"Se le paga normal y conserva el bono; confirmar con Nancy si fue "
                      f"falta / vacaciones / permiso / incapacidad.")
                resumen["nocheco"].append(f"{nombre} — no checó {nd}: {fechas}")
            else:
                nota=(f"🟡 REVISAR con Nancy: NO checó {nd} días: {fechas}. "
                      f"¿Vacaciones / incapacidad / permiso o falta real? "
                      f"Bono y pago de esos días quedan PENDIENTES de su confirmación.")
                resumen["nocheco"].append(f"{nombre} — REVISAR, no checó {nd}: {fechas}")
            reqs.append(_paint(sid, gi, 35, KHAKI, bold=True)); reqs.append(_note(sid, gi, 35, nota))
            print(f"  🟡 {nombre[:28]:28} NO checó {nd}: {fechas}{bono_txt}")

    print(f"\n🟢 completo ({len(resumen['verde'])}) · 🟡 no checó ({len(resumen['nocheco'])}) · ⚪ aparte ({len(resumen['aparte'])})")
    if a.dry:
        print("\n(DRY-RUN — no se escribió nada al Sheet)")
        return
    if val_updates:
        sh.spreadsheets().values().batchUpdate(spreadsheetId=sheet_id,
            body={"valueInputOption":"USER_ENTERED","data":val_updates}).execute()
    if reqs:
        sh.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests":reqs}).execute()
    print("✅ Flagueo escrito en el Sheet.")


if __name__=="__main__":
    main()
