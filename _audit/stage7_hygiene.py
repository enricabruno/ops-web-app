import re, json
from collections import defaultdict
from rdflib import Graph, Literal

FILES = ["data/rdf/concept.ttl", "data/rdf/corpus.ttl", "data/rdf/examples.ttl"]

g = Graph()
for f in FILES:
    g.parse(f, format="turtle")

# whitespace hygiene
ws_issues = []
for s,p,o in g:
    if isinstance(o, Literal):
        v = str(o)
        if v != v.strip():
            ws_issues.append(("leading/trailing-space", str(s), str(p), v[:60]))
        if "  " in v:
            ws_issues.append(("double-space", str(s), str(p), v[:60]))
        if "\t" in v:
            ws_issues.append(("tab", str(s), str(p), v[:60]))

by_kind = defaultdict(int)
for k,_,_,_ in ws_issues: by_kind[k]+=1
print("Igiene whitespace:", dict(by_kind))
for x in ws_issues[:15]: print(" -", x)

# URI hygiene: duplicated segments, double underscore, mixed hyphen/underscore
uri_issues = []
seen_uris = set()
for s,p,o in g:
    for term in (s, o):
        u = str(term)
        if not u.startswith("http"):
            continue
        if u in seen_uris:
            continue
        seen_uris.add(u)
        local = u.rsplit("/",1)[-1]
        if "__" in local:
            uri_issues.append(("double-underscore", u))
        segs = u.rstrip("/").split("/")
        if len(segs) != len(set(segs)) and len(segs) > 3:
            uri_issues.append(("duplicated-path-segment", u))

print(f"\nAnomalie URI: {len(uri_issues)}")
for x in uri_issues[:20]: print(" -", x)

# apostrophe / quote mixing
apo_report = defaultdict(lambda: defaultdict(int))
for s,p,o in g:
    if isinstance(o, Literal):
        v = str(o)
        has_curly = "’" in v
        has_straight = re.search(r"[A-Za-z]'[A-Za-z]", v) is not None
        if has_curly:
            apo_report[str(p)]["curly_U+2019"] += 1
        if has_straight:
            apo_report[str(p)]["straight_ascii"] += 1
        if "«" in v or "»" in v:
            apo_report[str(p)]["caporali"] += 1
        if '"' in v:
            apo_report[str(p)]["straight_doublequote"] += 1
        if "“" in v or "”" in v:
            apo_report[str(p)]["curly_doublequote"] += 1

print("\nUso di apostrofi/virgolette per proprietà (proprietà con ENTRAMBE le varianti = incoerenza):")
mixed = {}
for p, counts in apo_report.items():
    has_curly_apo = counts.get("curly_U+2019",0) > 0
    has_straight_apo = counts.get("straight_ascii",0) > 0
    if has_curly_apo and has_straight_apo:
        mixed[p] = dict(counts)
print(json.dumps(mixed, indent=2, ensure_ascii=False))

out = {
    "whitespace_issues_count": dict(by_kind),
    "whitespace_issues_sample": ws_issues[:50],
    "uri_issues": uri_issues,
    "apostrophe_quote_report": {k: dict(v) for k,v in apo_report.items()},
    "mixed_apostrophe_properties": mixed,
}
with open("_audit/stage7_hygiene.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
