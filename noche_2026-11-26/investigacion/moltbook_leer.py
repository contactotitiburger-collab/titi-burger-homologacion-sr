#!/usr/bin/env python3
"""Moltbook — SOLO LECTURA (GET). No publica, no comenta, no vota."""
import json, urllib.request, urllib.parse, sys
K = json.load(open("/home/tito/.openclaw/credentials/moltbook/api_key.json"))
KEY = K.get("api_key") or K.get("key") or next(iter(K.values()))
BASE = "https://www.moltbook.com/api/v1"
def get(path):
    r = urllib.request.Request(BASE + path, headers={"Authorization": f"Bearer {KEY}"})
    try:
        with urllib.request.urlopen(r, timeout=20) as h: return json.loads(h.read().decode())
    except Exception as e: return {"_error": str(e)[:200]}
def corto(p):
    return {k: (str(p.get(k))[:300] if p.get(k) else None) for k in ("title", "content", "author", "submolt", "upvotes", "created_at", "id")}
for q in sys.argv[1:]:
    res = get("/search?" + urllib.parse.urlencode({"q": q, "limit": 8}))
    items = res.get("results") or res.get("posts") or res.get("data") or res
    print(f"\n### {q}")
    if isinstance(items, dict): print(json.dumps(items, ensure_ascii=False)[:600]); continue
    for p in items[:8]:
        if isinstance(p, dict):
            a = p.get("author"); p["author"] = a.get("name") if isinstance(a, dict) else a
            s = p.get("submolt"); p["submolt"] = s.get("name") if isinstance(s, dict) else s
            print(json.dumps(corto(p), ensure_ascii=False))
