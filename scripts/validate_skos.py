#!/usr/bin/env python3
"""Valida data/rdf/concept.ttl contro un set di vincoli SKOS.

Uso:
    python3 scripts/validate_skos.py

Esce con codice 1 se almeno un check (1-8) fallisce. Il check 9 e' un
report informativo e non incide sul codice di uscita.
"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import rdflib
from rdflib import RDF

SKOS = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")
OWL = rdflib.Namespace("http://www.w3.org/2002/07/owl#")

REPO_ROOT = Path(__file__).resolve().parent.parent
CONCEPT_TTL = REPO_ROOT / "data" / "rdf" / "concept.ttl"


def load_graph():
    g = rdflib.Graph()
    g.parse(str(CONCEPT_TTL), format="turtle")
    return g


def local_name(uri):
    return str(uri).rsplit("/", 1)[-1].rsplit("#", 1)[-1]


def qname(uri):
    s = str(uri)
    if s.startswith("https://w3id.org/desmos/"):
        return "desmos:" + local_name(uri)
    return s


# ---------------------------------------------------------------------------
# Check 1 — simmetria broader/narrower
# ---------------------------------------------------------------------------
def check_broader_narrower_symmetry(g):
    broader = set(g.subject_objects(SKOS.broader))
    narrower = set(g.subject_objects(SKOS.narrower))

    missing_narrower = [(a, b) for a, b in broader if (b, a) not in narrower]
    missing_broader = [(a, b) for a, b in narrower if (b, a) not in broader]

    details = []
    for a, b in missing_narrower:
        details.append(f"{qname(a)} skos:broader {qname(b)} ma manca {qname(b)} skos:narrower {qname(a)}")
    for a, b in missing_broader:
        details.append(f"{qname(a)} skos:narrower {qname(b)} ma manca {qname(b)} skos:broader {qname(a)}")

    ok = not details
    return ok, f"{len(details)} asimmetrie", details


# ---------------------------------------------------------------------------
# Check 2 — simmetria related (owl:SymmetricProperty)
# ---------------------------------------------------------------------------
def check_related_symmetry(g):
    related = set(g.subject_objects(SKOS.related))
    missing = [(a, b) for a, b in related if (b, a) not in related]
    pairs = {frozenset((a, b)) for a, b in related}

    details = [f"{qname(a)} skos:related {qname(b)} senza l'inversa" for a, b in missing]
    ok = not details
    return ok, f"{len(pairs)} coppie, {len(details)} asimmetrie", details


# ---------------------------------------------------------------------------
# Check 3 — archi gerarchici ridondanti (qSKOS Redundant Hierarchical Relation)
# ---------------------------------------------------------------------------
def check_redundant_broader(g):
    edges = defaultdict(set)  # concept -> set of direct broader parents
    for c, p in g.subject_objects(SKOS.broader):
        edges[c].add(p)

    details = []
    for c, parents in edges.items():
        for p in parents:
            # BFS da c usando tutti gli archi *tranne* c->p: p e' ridondante
            # se resta comunque raggiungibile per un'altra via.
            seen = {c}
            frontier = [q for q in edges.get(c, ()) if q != p]
            seen.update(frontier)
            found = False
            while frontier:
                nxt = []
                for node in frontier:
                    if node == p:
                        found = True
                        break
                    for q in edges.get(node, ()):
                        if q not in seen:
                            seen.add(q)
                            nxt.append(q)
                if found:
                    break
                frontier = nxt
            if found:
                details.append(f"{qname(c)} skos:broader {qname(p)} e' derivabile per skos:broaderTransitive")

    ok = not details
    return ok, f"{len(details)} archi ridondanti", details


# ---------------------------------------------------------------------------
# Check 4 — SKOS S27: related e broaderTransitive disgiunti
# ---------------------------------------------------------------------------
def check_related_broader_disjoint(g):
    edges = defaultdict(set)
    for c, p in g.subject_objects(SKOS.broader):
        edges[c].add(p)

    def ancestors(c):
        seen = set()
        frontier = list(edges.get(c, ()))
        while frontier:
            nxt = []
            for node in frontier:
                if node not in seen:
                    seen.add(node)
                    nxt.extend(edges.get(node, ()))
            frontier = nxt
        return seen

    ancestor_cache = {}

    def get_ancestors(c):
        if c not in ancestor_cache:
            ancestor_cache[c] = ancestors(c)
        return ancestor_cache[c]

    related_pairs = {frozenset((a, b)) for a, b in g.subject_objects(SKOS.related) if a != b}

    details = []
    for pair in related_pairs:
        a, b = tuple(pair)
        if b in get_ancestors(a) or a in get_ancestors(b):
            details.append(f"{qname(a)} skos:related {qname(b)} ma sono anche sulla stessa catena skos:broaderTransitive")

    ok = not details
    return ok, f"{len(details)} violazioni S27", details


# ---------------------------------------------------------------------------
# Check 5 — cicli in skos:broader
# ---------------------------------------------------------------------------
def check_cycles(g):
    edges = defaultdict(set)
    for c, p in g.subject_objects(SKOS.broader):
        edges[c].add(p)

    WHITE, GRAY, BLACK = 0, 1, 2
    color = defaultdict(int)
    cycles = []

    def dfs(node, path):
        color[node] = GRAY
        path.append(node)
        for nxt in edges.get(node, ()):
            if color[nxt] == GRAY:
                start = path.index(nxt)
                cycles.append(path[start:] + [nxt])
            elif color[nxt] == WHITE:
                dfs(nxt, path)
        path.pop()
        color[node] = BLACK

    for node in list(edges):
        if color[node] == WHITE:
            dfs(node, [])

    details = [" -> ".join(qname(n) for n in cyc) for cyc in cycles]
    ok = not details
    return ok, f"{len(details)} cicli", details


# ---------------------------------------------------------------------------
# Check 6 — concetti senza skos:inScheme
# ---------------------------------------------------------------------------
def check_in_scheme(g):
    concepts = set(g.subjects(RDF.type, SKOS.Concept))
    with_scheme = set(g.subjects(SKOS.inScheme, None))
    missing = sorted(concepts - with_scheme, key=str)

    details = [qname(c) for c in missing]
    ok = not details
    return ok, f"{len(details)} concetti senza inScheme", details


# ---------------------------------------------------------------------------
# Check 7 — prefLabel: presenza it/en e unicita' per lingua (SKOS S14)
# ---------------------------------------------------------------------------
def check_pref_labels(g):
    concepts = set(g.subjects(RDF.type, SKOS.Concept))
    details = []

    for c in sorted(concepts, key=str):
        labels = list(g.objects(c, SKOS.prefLabel))
        by_lang = defaultdict(list)
        for lbl in labels:
            lang = getattr(lbl, "language", None) or "(nessuna lingua)"
            by_lang[lang].append(str(lbl))

        if not by_lang.get("it"):
            details.append(f"{qname(c)}: manca skos:prefLabel@it")
        if not by_lang.get("en"):
            details.append(f"{qname(c)}: manca skos:prefLabel@en")
        for lang, vals in by_lang.items():
            if len(vals) > 1:
                details.append(f"{qname(c)}: {len(vals)} skos:prefLabel@{lang} ({', '.join(vals)}) — viola S14")

    ok = not details
    return ok, f"{len(details)} anomalie", details


# ---------------------------------------------------------------------------
# Check 8 — prefissi dichiarati vs usati
# ---------------------------------------------------------------------------
_PREFIX_DECL_RE = re.compile(r"^@prefix\s+([\w-]*):\s*<[^>]+>\s*\.", re.MULTILINE)
# qname-like token: prefisso:localname, non preceduto da lettera/cifra/quote,
# e non seguito da "//" (per non intercettare gli IRI assoluti tra <>).
_QNAME_RE = re.compile(r'(?<![\w"/<])([a-zA-Z][\w-]*):(?!//)([a-zA-Z_][\w-]*)')


def check_prefixes():
    text = CONCEPT_TTL.read_text(encoding="utf-8")
    declared = set(_PREFIX_DECL_RE.findall(text))

    body = _PREFIX_DECL_RE.sub("", text)
    # Rimuove i letterali stringa (tra doppi apici) per non intercettare
    # falsi positivi tipo "e.g." o URL scritti nel testo delle definizioni.
    body_no_strings = re.sub(r'"(?:[^"\\]|\\.)*"', "", body)
    used = {m.group(1) for m in _QNAME_RE.finditer(body_no_strings)}

    undeclared = sorted(used - declared)
    unused = sorted(declared - used)

    details = []
    for p in undeclared:
        details.append(f"prefisso usato ma non dichiarato: {p}:")
    for p in unused:
        details.append(f"prefisso dichiarato ma mai usato: {p}:")

    # Solo l'uso di un prefisso non dichiarato e' un errore bloccante;
    # un prefisso dichiarato e mai usato e' segnalato ma non fa fallire il check.
    ok = not undeclared
    return ok, f"{len(undeclared)} non dichiarati, {len(unused)} inutilizzati", details


# ---------------------------------------------------------------------------
# Check 9 — report informativo per scheme (non bloccante)
# ---------------------------------------------------------------------------
def scheme_report(g):
    schemes = sorted(g.subjects(RDF.type, SKOS.ConceptScheme), key=str)
    edges = defaultdict(set)  # concept -> children (narrower via broader)
    for c, p in g.subject_objects(SKOS.broader):
        edges[p].add(c)

    rows = []
    for scheme in schemes:
        concepts = set(g.subjects(SKOS.inScheme, scheme))
        roots = [c for c in concepts if (c, SKOS.broader, None) not in g]
        isolated = [c for c in roots if not edges.get(c)]

        def depth(node, seen):
            children = [ch for ch in edges.get(node, ()) if ch in concepts and ch not in seen]
            if not children:
                return 0
            return 1 + max(depth(ch, seen | {ch}) for ch in children)

        max_depth = max((depth(r, {r}) for r in roots), default=0)
        rows.append({
            "scheme": qname(scheme),
            "concepts": len(concepts),
            "roots": len(roots),
            "isolated_roots": len(isolated),
            "max_depth": max_depth,
        })
    return rows


# ---------------------------------------------------------------------------
def run():
    if not CONCEPT_TTL.exists():
        print(f"ERRORE: {CONCEPT_TTL} non trovato.")
        sys.exit(1)

    g = load_graph()

    checks = [
        ("1. Simmetria skos:broader/narrower", check_broader_narrower_symmetry(g)),
        ("2. Simmetria skos:related", check_related_symmetry(g)),
        ("3. Archi skos:broader ridondanti", check_redundant_broader(g)),
        ("4. Disgiunzione related/broaderTransitive (S27)", check_related_broader_disjoint(g)),
        ("5. Cicli in skos:broader", check_cycles(g)),
        ("6. Concetti senza skos:inScheme", check_in_scheme(g)),
        ("7. prefLabel it/en e unicita' per lingua (S14)", check_pref_labels(g)),
        ("8. Prefissi dichiarati vs usati", check_prefixes()),
    ]

    print(f"Validazione SKOS — {CONCEPT_TTL.relative_to(REPO_ROOT)}")
    print("=" * 78)

    all_ok = True
    for name, (ok, summary, details) in checks:
        status = "OK  " if ok else "FAIL"
        print(f"[{status}] {name}: {summary}")
        if not ok:
            all_ok = False
        for line in details:
            print(f"         - {line}")

    print("-" * 78)
    print("9. Report per scheme (informativo)")
    rows = scheme_report(g)
    header = f"{'scheme':<32}{'concetti':>10}{'radici':>10}{'radici isolate':>16}{'profondita max':>18}"
    print(header)
    for r in rows:
        print(f"{r['scheme']:<32}{r['concepts']:>10}{r['roots']:>10}{r['isolated_roots']:>16}{r['max_depth']:>18}")

    print("=" * 78)
    if all_ok:
        print("Tutti i check bloccanti sono OK.")
    else:
        print("Almeno un check bloccante e' fallito.")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    run()
