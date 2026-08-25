import re, json, sys
from rdflib import Graph, URIRef, BNode, Literal
from collections import defaultdict, Counter

FILES = {
    "desmos.owl": ("data/ontology/desmos.owl", "xml"),
    "concept.ttl": ("data/rdf/concept.ttl", "turtle"),
    "corpus.ttl": ("data/rdf/corpus.ttl", "turtle"),
    "examples.ttl": ("data/rdf/examples.ttl", "turtle"),
}

results = {}

for name, (path, fmt) in FILES.items():
    g = Graph()
    try:
        g.parse(path, format=fmt)
        ntriples = len(g)
        err = None
    except Exception as e:
        ntriples = None
        err = str(e)
    results[name] = {"path": path, "format": fmt, "triples": ntriples, "parse_error": err}
    if ntriples is not None:
        globals()[f"g_{name.split('.')[0]}"] = g

print(json.dumps(results, indent=2, ensure_ascii=False))

# --- prefix census (declared vs used) ---
prefix_report = {}
for name, (path, fmt) in FILES.items():
    with open(path, encoding="utf-8") as f:
        text = f.read()
    declared = {}
    if fmt == "turtle":
        for m in re.finditer(r'@prefix\s+([a-zA-Z0-9_-]*):\s*<([^>]*)>\s*\.', text):
            declared[m.group(1)] = m.group(2)
    else:  # xml
        for m in re.finditer(r'xmlns:([a-zA-Z0-9_-]+)="([^"]*)"', text):
            declared[m.group(1)] = m.group(2)
        # default namespace
        m = re.search(r'xmlns="([^"]*)"', text)
        default_ns = m.group(1) if m else None
        declared["(default)"] = default_ns

    # used prefixes: for turtle, find "prefix:" tokens in triple positions (rough heuristic)
    used = set()
    if fmt == "turtle":
        for m in re.finditer(r'(?<![a-zA-Z0-9_:])([a-zA-Z][a-zA-Z0-9_-]*):[a-zA-Z_]', text):
            used.add(m.group(1))
    else:
        for m in re.finditer(r'<([a-zA-Z][a-zA-Z0-9_-]*):[a-zA-Z_][^>\s/]*[\s/>]', text):
            used.add(m.group(1))
        for m in re.finditer(r'</?([a-zA-Z][a-zA-Z0-9_-]*):[A-Za-z_]', text):
            used.add(m.group(1))

    declared_keys = set(k for k in declared if k != "(default)")
    unused_declared = declared_keys - used
    used_undeclared = used - declared_keys - {"xml", "rdf", "rdfs", "xmlns"}
    prefix_report[name] = {
        "declared": declared,
        "unused_declared": sorted(unused_declared),
        "used_undeclared": sorted(used_undeclared),
    }

with open("_audit/stage1_prefixes.json", "w", encoding="utf-8") as f:
    json.dump(prefix_report, f, indent=2, ensure_ascii=False)

print("\n\n=== PREFIX REPORT ===")
print(json.dumps(prefix_report, indent=2, ensure_ascii=False))

with open("_audit/stage1_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
