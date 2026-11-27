#!/usr/bin/env python3
"""nomina_flaguear.py — post-procesa la nómina con la lógica de Rafael:

  DÍAS DE PAGO = HORARIO de Félix (lo que estaba programado a trabajar).
  SESAME = solo VERIFICA / FLAGUEA (si no fichó un día programado -> amarillo).
  No fichar ≠ faltar: se le paga el día y conserva su bono.

Por cada empleado:
  1. Pone "1" en cada día con código 'T' en el horario (o donde sí checó) -> días correctos.
  2. Pinta AMARILLO el día que estaba programado pero NO checó en SESAME (con "1", se paga).
  3. Restaura el bono puntual (V=H) si se lo habían borrado por no fichar.
  4. Escribe color + nota en la columna TOTAL (AJ): 🟢 checó completo / 🟡 no checó X días.
  5. DEDUPLICA en Drive (deja el archivo más nuevo, manda copias a papelera).

Se corre después de generar/regenerar la nómina.  --sheet <id> | --semana <N> | --horario <p>
"""
import json, argparse, unicodedata, sys, glob, re
from pathlib import Path
import openpyxl
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE = Path.home()/".openclaw"
TOK = BASE/"credentials/google/oauth/tito_tokens.json"
APODOS = BASE/"data/nomina/horarios/apodos.json"
FOLDER = "1qBpjmHZr_-F-bBo793J_7I6Q1yPWEHnU"

VERDE    = {"red":0.72,"green":0.88,"blue":0.72}
AMARILLO = {"red":1.0,"green":0.92,"blue":0.55}
WHITE    = {"red":1,"green":1,"blue":1}
ALWAYS_VERDE = {"FELIX","BUBU"}
SKIP_ALL     = {"RALLITO","AMERICA"}          # ni días, ni bono, ni flag automático
DAYS = ['L','M','N','O','P','Q','R']
COL1 = {c:12+i for i,c in enumerate(DAYS)}    # L=12..R=18 (1-based)
AJ0, V1, H1 = 35, 22, 8                        # AJ 0-based ; V,H 1-based


def norm(s):
    s=unicodedata.normalize('NFD',str(s)); s=''.join(c for c in s if unicodedata.category(c)!='Mn')
    return set(w for w in s.upper().replace('.',' ').split() if len(w)>2)

def a1(col1, row):
    s=""; i=col1
    while i: i,r=divmod(i-1,26); s=chr(65+r)+s
    return f"{s}{row}"

def clients():
    t=json.loads(TOK.read_text())
    c=Credentials(token=t["token"],refresh_token=t["refresh_token"],token_uri=t["token_uri"],
                  client_id=t["client_id"],client_secret=t["client_secret"],scopes=t["scopes"])
    if not c.valid: c.refresh(Request()); t["token"]=c.token; TOK.write_text(json.dumps(t,indent=2))
    return build("sheets","v4",credentials=c), build("drive","v3",credentials=c)

def num(x):
    x=str(x).replace('$','').strip()
    return 0.0 if x in('','-') else float(x.replace('.','').replace(',','.'))

def buscar_sheet(drv, semana):
    prefijo=f"Nómina - Semana {semana} ("
    q=(f"name contains 'Semana {semana}' and trashed=false and '{FOLDER}' in parents "
       "and mimeType='application/vnd.google-apps.spreadsheet'")
    fs=drv.files().list(q=q, fields="files(id,name,createdTime)", orderBy="createdTime desc").execute().get('files',[])
    fs=[f for f in fs if f['name'].startswith(prefijo)]
    if not fs: sys.exit(f"No encontré Sheet no-en-papelera para Semana {semana}")
    for dup in fs[1:]:
        drv.files().update(fileId=dup['id'], body={"trashed":True}).execute()
        print(f"🗑️  duplicado a papelera: {dup['id']}")
    return fs[0]['id']

def semana_actual(drv):
    q=("name contains 'Nómina - Semana' and trashed=false "
       f"and '{FOLDER}' in parents and mimeType='application/vnd.google-apps.spreadsheet'")
    fs=drv.files().list(q=q, fields="files(name,createdTime)", orderBy="createdTime desc").execute().get('files',[])
    for f in fs:
        m=re.search(r"Semana (\d+)", f['name'])
        if m: return int(m.group(1))
    sys.exit("No pude detectar la semana actual.")

def cargar_sesame(semana):
    """Devuelve {nombre_norm(frozenset): set(dias '13'..)}."""
    p=BASE/f"data/nomina/sesame_export_sem{semana}.xlsx"
    if not p.exists(): return None
    wb=openpyxl.load_workbook(p, data_only=True)
    ws=wb[wb.sheetnames[0]]
    ses={}
    for r in ws.iter_rows(min_row=2, values_only=True):
        emp,tipo,ident,fecha,act,grupo,ent,*_=(list(r)+[None]*8)[:8]
        if not emp or str(emp).strip() in ('TOTAL',''): continue
        if not ent or str(ent).strip() in ('','-'): continue
        d=str(fecha).split('/')[0].lstrip('0')
        ses.setdefault(str(emp).strip(), set()).add(d)
    return ses


def flaguear(sheet_id, horario, sesame):
    sh = clients()[0]
    apodos = json.loads(APODOS.read_text())
    meta = sh.spreadsheets().get(spreadsheetId=sheet_id).execute()
    tp = next(s['properties'] for s in meta['sheets'] if s['properties']['title'].strip()=='NOMINA')
    title, sid = tp['title'], tp['sheetId']

    grid = sh.spreadsheets().values().get(spreadsheetId=sheet_id,
        range=f"'{title}'!F8:AJ60", valueRenderOption="FORMATTED_VALUE").execute().get('values',[])
    hdr = (grid[0] if grid else [])+['']*40
    # fechas de encabezado -> {dia_num: letra}
    daymap={}
    for k in range(7):
        m=re.search(r"(\d+)", str(hdr[6+k]))
        if m: daymap[m.group(1).lstrip('0')]=DAYS[k]

    val_updates=[]; reqs=[]; resumen={"verde":[],"nocheco":[],"aparte":[]}
    for gi,row in enumerate(grid[1:], start=9):
        row=row+['']*40
        nombre=str(row[0]).strip()
        if not nombre: continue
        tgt=norm(nombre); apodo=None; bs=0
        for ap,full in apodos.items():
            if not full: continue
            sc=len(norm(full)&tgt)
            if sc>bs: bs=sc; apodo=ap
        if bs<2: apodo=None
        # checadas SESAME de esta persona -> letras
        checked=set()
        if sesame:
            bn=0; best=None
            for e in sesame:
                sc=len(norm(e)&tgt)
                if sc>bn: bn=sc; best=e
            if best and bn>=2:
                checked={daymap[d] for d in sesame[best] if d in daymap}

        if apodo in SKIP_ALL:
            nota = "✅ Bryan (medio tiempo — captura manual)" if apodo=="RALLITO" else "✅ América (incapacidad — no aplica checador)"
            reqs.append(_paint(sid, gi, AJ0, VERDE, bold=True)); reqs.append(_note(sid, gi, AJ0, nota))
            resumen["aparte"].append(nombre); continue

        if apodo and apodo in horario:
            codes=horario[apodo]
            av = apodo in ALWAYS_VERDE            # Félix/Bubu: días por horario pero SIN flag (no fichan a propósito)
            nofiche=[]
            for k,day in enumerate(DAYS):
                worked = (codes[k] in ('T','P','S')) or (day in checked)   # P=día pagado · S=sin app (trabajó, no flag)
                cur = str(row[6+k]).strip()
                col=COL1[day]
                if worked and cur!='1':
                    val_updates.append({"range":f"'{title}'!{a1(col,gi)}","values":[[1]]})
                elif not worked and cur=='1':
                    val_updates.append({"range":f"'{title}'!{a1(col,gi)}","values":[[""]]})
                if (not av) and codes[k] in ('T','S') and day not in checked:   # programado (T o S) pero NO fichó
                    nofiche.append(day); reqs.append(_paint(sid, gi, col-1, AMARILLO))
                elif worked:                                            # día trabajado -> sin flag
                    reqs.append(_paint(sid, gi, col-1, WHITE))
            # Regla Don Titi (S29+): si NO checó un día programado (T o S) -> se le QUITA el bono puntual.
            # Si checó todo, se restaura el bono si se lo habían borrado. Félix/Bubu (av) exentos.
            H=num(row[2]); V=num(row[16]) if len(row)>16 else 0
            if nofiche and not av:
                if V!=0: val_updates.append({"range":f"'{title}'!{a1(V1,gi)}","values":[[0]]})
            elif H>0 and V<H:
                val_updates.append({"range":f"'{title}'!{a1(V1,gi)}","values":[[H]]})
            if av:
                nota = "✅ Patrón — no ficha" if apodo=="FELIX" else "✅ Captura manual — bono completo"
                reqs.append(_paint(sid, gi, AJ0, VERDE, bold=True)); reqs.append(_note(sid, gi, AJ0, nota))
                resumen["verde"].append(nombre)
            elif nofiche:
                dias=", ".join(str(hdr[6+DAYS.index(d)]) for d in nofiche)
                nota=f"🟡 NO checó en SESAME: {dias} ({len(nofiche)} día(s)). Se le QUITA el bono puntual (regla Don Titi: no se perdona)."
                reqs.append(_paint(sid, gi, AJ0, AMARILLO, bold=True)); reqs.append(_note(sid, gi, AJ0, nota))
                resumen["nocheco"].append(f"{nombre} ({','.join(nofiche)})")
            else:
                trab=sum(1 for c in codes if c in ('T','P','S'))
                reqs.append(_paint(sid, gi, AJ0, VERDE, bold=True))
                reqs.append(_note(sid, gi, AJ0, f"✅ Trabajó completo ({trab} días)"))
                resumen["verde"].append(nombre)
        elif apodo in ALWAYS_VERDE:
            nota = "✅ Patrón — no ficha" if apodo=="FELIX" else "✅ Captura manual — bono completo"
            reqs.append(_paint(sid, gi, AJ0, VERDE, bold=True)); reqs.append(_note(sid, gi, AJ0, nota))
            resumen["verde"].append(nombre)
        else:
            # fuera del horario (David, Nancy): restaurar bono si se lo borraron (solo falta real lo quita)
            H=num(row[2]); V=num(row[16]) if len(row)>16 else 0
            if H>0 and V<H:
                val_updates.append({"range":f"'{title}'!{a1(V1,gi)}","values":[[H]]})
            reqs.append(_paint(sid, gi, AJ0, VERDE, bold=True))
            reqs.append(_note(sid, gi, AJ0, "✅ Fuera de horario de carreta (oficina/admvo)"))
            resumen["verde"].append(nombre)

    if val_updates:
        sh.spreadsheets().values().batchUpdate(spreadsheetId=sheet_id,
            body={"valueInputOption":"USER_ENTERED","data":val_updates}).execute()
    if reqs:
        sh.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests":reqs}).execute()
    return resumen


def _paint(sid,row,col0,color,bold=None):
    fmt={"backgroundColor":color}
    fields="userEnteredFormat.backgroundColor"
    if bold is not None:
        fmt["textFormat"]={"bold":bold}; fields="userEnteredFormat(backgroundColor,textFormat)"
    return {"repeatCell":{"range":{"sheetId":sid,"startRowIndex":row-1,"endRowIndex":row,
            "startColumnIndex":col0,"endColumnIndex":col0+1},"cell":{"userEnteredFormat":fmt},"fields":fields}}

def _note(sid,row,col0,note):
    return {"updateCells":{"range":{"sheetId":sid,"startRowIndex":row-1,"endRowIndex":row,
            "startColumnIndex":col0,"endColumnIndex":col0+1},"rows":[{"values":[{"note":note}]}],"fields":"note"}}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--sheet"); ap.add_argument("--semana", type=int); ap.add_argument("--horario")
    a=ap.parse_args()
    _, drv = clients()
    if not a.semana:
        a.semana=semana_actual(drv); print(f"Semana auto-detectada: {a.semana}")
    sheet_id = a.sheet or buscar_sheet(drv, a.semana)
    hp = a.horario or (glob.glob(str(BASE/f"data/nomina/horarios/s{a.semana}_*.json"))+[None])[0]
    if not hp or not Path(hp).exists(): sys.exit(f"No hay horario para la semana {a.semana}")
    horario=json.loads(Path(hp).read_text())
    sesame=cargar_sesame(a.semana)
    if sesame is None: print("⚠️  sin export SESAME — flageo por horario, sin verificación de fichaje")
    print(f"Flagueando {sheet_id}\n  horario: {hp}  · SESAME: {'sí' if sesame else 'no'}")
    r=flaguear(sheet_id, horario, sesame)
    print(f"\n🟢 verde ({len(r['verde'])}) · 🟡 no checó ({len(r['nocheco'])}) · ⚪ aparte ({len(r['aparte'])})")
    for x in r['nocheco']: print("   🟡", x)


if __name__=="__main__":
    main()
