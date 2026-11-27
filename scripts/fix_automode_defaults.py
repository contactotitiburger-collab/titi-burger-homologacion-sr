import json
p = "/home/tito/.claude/settings.json"
d = json.load(open(p))
d["autoMode"]["allow"] = [
    "$defaults" if x == "" else x
    for x in d["autoMode"]["allow"]
]
json.dump(d, open(p, "w"), indent=2)
print("arreglado")
