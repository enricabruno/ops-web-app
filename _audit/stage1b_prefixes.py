import json, re
from rdflib import Graph, URIRef
from collections import defaultdict

FILES = {
    "desmos.owl": ("data/ontology/desmos.owl", "xml"),
    "concept.ttl": ("data/rdf/concept.ttl", "turtle"),
    "corpus.ttl": ("data/rdf/corpus.ttl", "turtle"),
    "examples.ttl": ("data/rdf/examples.ttl", "turtle"),
}

def namespace_of(uri):
    # split on last # then last /
    if "#" in uri:
        return uri.rsplit("#", 1)[0] + "#"
    if "/" in uri:
        return uri.rsplit("/", 1)[0] + "/"
    return uri

graphs = {}
declared_per_file = {}
for name, (path, fmt) in FILES.items():
    g = Graph()
    g.parse(path, format=fmt)
    graphs[name] = g
    declared_per_file[name] = {p: str(ns) for p, ns in g.namespaces() if p}

report = {}
all_ns_by_prefix = defaultdict(dict)  # prefix -> {file: ns}

for name, g in graphs.items():
    declared = declared_per_file[name]
    for p, ns in declared.items():
        all_ns_by_prefix[p][name] = ns

    uris = set()
    for s, p, o in g:
        for term in (s, p, o):
            if isinstance(term, URIRef):
                uris.add(str(term))

    used_namespaces = set(namespace_of(u) for u in uris)

    unused_declared = []
    for p, ns in declared.items():
        if not any(u.startswith(ns) for u in uris):
            unused_declared.append(p)

    # namespaces present in data with no matching declared prefix
    undeclared_namespaces = defaultdict(int)
    for u in uris:
        ns = namespace_of(u)
        if not any(ns == dns or u.startswith(dns) for dns in declared.values()):
            undeclared_namespaces[ns] += 1

    report[name] = {
        "declared_prefixes": declared,
        "unused_declared_prefixes": unused_declared,
        "namespaces_in_data_without_declared_prefix": dict(undeclared_namespaces),
    }

# cross-file prefix URI divergence
divergence = {}
for p, filemap in all_ns_by_prefix.items():
    uniq = set(filemap.values())
    if len(uniq) > 1:
        divergence[p] = filemap

print(json.dumps({"per_file": report, "cross_file_divergence": divergence}, indent=2, ensure_ascii=False))

with open("_audit/stage1_prefixes_clean.json", "w", encoding="utf-8") as f:
    json.dump({"per_file": report, "cross_file_divergence": divergence}, f, indent=2, ensure_ascii=False)
