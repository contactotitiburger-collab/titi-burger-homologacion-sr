import json, re, collections, unicodedata
S = "/tmp/claude-0/-root/7bae264f-3009-4fda-bb5d-2b2ac7ee692b/scratchpad/"
D = json.load(open(S + "datos.json")); V = json.load(open(S + "datos2.json"))
def ventas(base):
    v = V.get(base, {}).get("ventas") or []
    return {str(r[0]).strip(): int(r[1]) for r in v if isinstance(r, list)}
def sa(t): return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
TYPO = [(r"\bWESTER\b", "WESTERN"), (r"\bCLASIA\b", "CLASICA"), (r"\bQUESOS\b", "QUESO"), (r"\bCOMBMO\b", "COMBO"), (r"\bORDE\b", "ORDEN"),
        (r"\bQUSO\b", "QUESO"), (r"\bVEDURA\b", "VERDURA"), (r"\bINGRDIENTES\b", "INGREDIENTES"), (r"\bBRAWNIE\b", "BROWNIE"), (r"\bPROMIOCION\b", "PROMOCION"),
        (r"\bORAGE\b", "ORANGE"), (r"\bADOMICILIO\b", "A DOMICILIO"), (r"\bALA FRANCESA\b", "A LA FRANCESA"), (r"\bRET HOT\b", "RED HOT"), (r"\bTERIYAQUI\b", "TERIYAKI"),
        (r"\bKECHUT\b", "KETCHUP"), (r"\bABANERO\b", "HABANERO"), (r"\bMAGO\b", "MANGO"), (r"\bPARILLERO\b", "PARRILLERO"), (r"\bBROCHE\b", "BRIOCHE"), (r"\bHAMBURGUSA\b", "HAMBURGUESA"), (r"\bBONELES\b", "BONELESS")]
def corrige(d):
    x = re.sub(r"\s+", " ", d).strip()
    for a, b in TYPO: x = re.sub(a, b, x)
    return x
def canal(d):
    u = sa(d.upper())
    multi = sum(bool(re.search(p, u)) for p in [r"DIDI|\(DI\)|\bDI\b", r"UBER|\(UB\)|\bUB\b|\bUBE\b", r"RAPPI|\(RA\)|\(RAP\)|\(PAP\)|\bRAPI\b|\bRAP\b"])
    if multi > 1: return "APPS"
    if re.search(r"DIDI|\(DI\)|\bDI\b", u): return "DIDI"
    if re.search(r"UBER|\(UB\)|\bUB\b|\bUBE\b", u): return "UBER"
    if re.search(r"RAPPI|\(RA\)|\(RAP\)|\(PAP\)|\bRAPI\b|\bRAP\b", u): return "RAPPI"
    return "CAJA"
def nucleo(d):
    u = corrige(sa(d.upper()))
    u = re.sub(r"\((DI|UB|RA|RAP|PAP)\)|,|\b(DIDI|UBER|UBE|RAPPI|RAPI|RAP|DI|UB)\b", " ", u)
    u = re.sub(r"\bPACK\b", "COMBO", u)
    u = re.sub(r"\b(DE|LA|EL|A)\b", " ", u)
    return re.sub(r"\s+", " ", u).strip()
BEB = r"\b(SODAS?|TE|JAMAICA|PEPSI|COCA|NARANJA|ROOT ?BEER|MANZANITA|AGUA|JUGO|SQUIRT|MIRINDA|7 UP|DR PEPPER|CRUSH)\b"
def familia(cod, d, grp):
    u = sa(d.upper())
    if cod.startswith("101") or u.startswith("MERMA"): return "MERMA"
    if cod.startswith("100"): return "MODIF"
    if "+" in u: return "COMBO"
    if "BONELESS" in u: return "BONELESS"
    if re.search(r"COMBO|COMBMO|\bPACK\b|PROMOCION|PROMIOCION", u): return "COMBO"
    if u.startswith("TITI"): return "HAMB"
    if re.search(BEB, u) and "EXTRA" not in u.replace("EXTRA AGUA", "").replace("EXTRA TE", "").replace("EXTRA SODA", ""): return "BEBIDA"
    return "EXTRA"
FAM = {"HAMB": ("1", "Hamburguesas"), "COMBO": ("2", "Combos y promociones"), "EXTRA": ("3", "Extras y acompañantes"), "BEBIDA": ("4", "Bebidas"), "BONELESS": ("5", "Boneless")}
CAN = {"CAJA": ("0", "Caja"), "DIDI": ("2", "DiDi"), "UBER": ("3", "Uber"), "RAPPI": ("4", "Rappi"), "APPS": ("6", "Todas las apps"), "CURTO": ("7", "Cine Curto")}
GN = {"01": "TITI BURGER", "03": "EXTRAS", "04": "BEBIDAS", "05": "BONELESS", "100": "MODIFICADORES", "101": "MERMA DE SUCURSAL"}

def proponer():
    m = D["Montejano"]["productos"]; vm = ventas("Montejano")
    filas = []
    for cod, desc, grp, *_ in m:
        cod = cod.strip(); c = canal(desc); f = familia(cod, desc, grp)
        filas.append(dict(cod=cod, desc=desc.strip(), grupo=grp.strip(), canal=c, fam=f, nuc=nucleo(desc), lineas=vm.get(cod, 0)))
    # numeracion por familia: orden de primera aparicion, caja primero
    num = {}
    for f in FAM:
        orden = []
        for x in sorted([x for x in filas if x["fam"] == f], key=lambda x: (x["canal"] != "CAJA", x["cod"])):
            if x["nuc"] not in orden: orden.append(x["nuc"])
        for i, n in enumerate(orden, 1): num[(f, n)] = i
    usados = collections.Counter()
    for x in filas:
        if x["fam"] in FAM:
            n = num[(x["fam"], x["nuc"])]
            x["nuevo"] = f"{CAN[x['canal']][0]}{FAM[x['fam']][0]}{n:03d}"
            x["grupo_nuevo"] = FAM[x["fam"]][1] if x["canal"] == "CAJA" else CAN[x["canal"]][1]
        else:
            x["nuevo"] = x["cod"]; x["grupo_nuevo"] = "Modificadores" if x["fam"] == "MODIF" else "Merma de sucursal"
        usados[(x["nuevo"])] += 1
    # repetidos: mismo codigo nuevo => misma cosa varias veces
    for x in filas:
        x["repetido"] = usados[x["nuevo"]] > 1
        x["ortografia"] = corrige(x["desc"]) if corrige(x["desc"]) != re.sub(r"\s+", " ", x["desc"]).strip() else ""
        x["mal_grupo"] = (x["fam"] in FAM and x["cod"][:2] != {"HAMB": "01", "COMBO": "01", "EXTRA": "03", "BEBIDA": "04", "BONELESS": "05"}[x["fam"]]) or (x["cod"][:2] in ("01","03","04","05") and x["cod"][:2] != x["grupo"].zfill(2)[:2])
    return filas

def felix():
    out = []
    mm = {p[0].strip(): p[1].strip() for p in D["Montejano"]["productos"]}
    pref = {"01": "90", "03": "93", "04": "94"}
    cnt = collections.Counter()
    for cod, desc, grp, *_ in sorted(D["Felix"]["productos"]):
        cod = cod.strip(); grp = grp.strip()
        choca = cod in mm and nucleo(mm[cod]) != nucleo(desc)
        igual = cod in mm and not choca
        if grp in pref:
            cnt[grp] += 1; nuevo = f"{pref[grp]}{cnt[grp]:03d}"
        else: nuevo = cod
        out.append(dict(cod=cod, desc=desc.strip(), grupo=grp, nuevo=nuevo, choca=choca, en_sucursal=mm.get(cod, "") if choca else ("igual" if igual else "")))
    return out
def curto(F):
    vc = ventas("CineCurto"); base = {(x["fam"], x["nuc"], x["canal"]): x["nuevo"] for x in F}
    out = []; n = collections.Counter()
    for cod, desc, grp, *_ in sorted(D["CineCurto"]["productos"]):
        cod = cod.strip(); c = canal(desc); f = familia(cod, desc, grp.strip()); k = (f, nucleo(desc), c)
        if k in base: nuevo, como = base[k], "Igual que en las sucursales"
        elif f in FAM:
            n[f] += 1; nuevo, como = f"7{FAM[f][0]}{n[f]:03d}", "Propio de Cine Curto"
        else: nuevo, como = cod, "Se queda"
        out.append(dict(cod=cod, desc=desc.strip(), fam=f, canal=c, nuevo=nuevo, como=como, lineas=vc.get(cod, 0)))
    return out
if __name__ == "__main__":
    F = proponer(); X = felix()
    C = curto(F)
    json.dump({"sucursales": F, "felix": X, "curto": C}, open("codigos_propuesta.json", "w"), ensure_ascii=False, indent=1)
    c = collections.Counter((x["canal"], x["fam"]) for x in F); print(sorted(c.items()))
    print("repetidos:", sum(x["repetido"] for x in F), " ortografia:", sum(bool(x["ortografia"]) for x in F), " mal grupo:", sum(x["mal_grupo"] for x in F))
    for x in F:
        if x["fam"] in ("HAMB","COMBO") or x["repetido"]: print(x["cod"], "->", x["nuevo"], x["canal"], x["fam"], "|", x["desc"], "| R" if x["repetido"] else "", x["lineas"])
    print("curto:", collections.Counter(x["como"] for x in C)); print("sin ventas suc:", sum(1 for x in F if x["lineas"]==0)); print("felix choques:", sum(x["choca"] for x in X), "de", len(X))
