import json
from collections import defaultdict, Counter
from rdflib import Graph, URIRef, RDF, RDFS
from rdflib.namespace import SKOS

g = Graph(); g.parse("data/rdf/concept.ttl", format="turtle")

concepts = set(g.subjects(RDF.type, SKOS.Concept))
schemes = set(g.subjects(RDF.type, SKOS.ConceptScheme))
print(f"skos:Concept: {len(concepts)}")
print(f"skos:ConceptScheme: {len(schemes)}")

# 1. Concept senza inScheme
no_scheme = sorted(str(c) for c in concepts if not list(g.objects(c, SKOS.inScheme)))
print(f"\nConcetti senza skos:inScheme: {len(no_scheme)}")
for c in no_scheme[:20]: print(" -", c)

# 2. broader/narrower simmetria + cross-scheme + cicli
broader = defaultdict(set)
narrower = defaultdict(set)
for s,o in g.subject_objects(SKOS.broader):
    broader[s].add(o)
for s,o in g.subject_objects(SKOS.narrower):
    narrower[s].add(o)

asym_broader = []  # A broader B but B not narrower A
for a, bs in broader.items():
    for b in bs:
        if a not in narrower.get(b, set()):
            asym_broader.append((str(a), str(b)))
asym_narrower = []
for a, bs in narrower.items():
    for b in bs:
        if a not in broader.get(b, set()):
            asym_narrower.append((str(a), str(b)))

print(f"\nAsimmetrie broader->narrower (A broader B, ma B non ha narrower A): {len(asym_broader)}")
for x in asym_broader[:10]: print(" -", x)
print(f"Asimmetrie narrower->broader (A narrower B, ma B non ha broader A): {len(asym_narrower)}")
for x in asym_narrower[:10]: print(" -", x)

# cross-scheme broader
scheme_of = defaultdict(set)
for c in concepts:
    for sch in g.objects(c, SKOS.inScheme):
        scheme_of[c].add(sch)

cross_scheme = []
for a, bs in broader.items():
    for b in bs:
        sa, sb = scheme_of.get(a, set()), scheme_of.get(b, set())
        if sa and sb and not (sa & sb):
            cross_scheme.append((str(a), str(sa), str(b), str(sb)))
print(f"\nRelazioni broader che attraversano ConceptScheme diversi: {len(cross_scheme)}")
for x in cross_scheme[:10]: print(" -", x)

# cycles in broader graph
def has_cycle():
    visited = {}
    cycles = []
    def dfs(node, stack):
        visited[node] = 1
        stack.append(node)
        for nxt in broader.get(node, ()):
            if visited.get(nxt) == 1:
                idx = stack.index(nxt) if nxt in stack else -1
                cycles.append(list(stack[idx:]) + [nxt] if idx>=0 else [node, nxt])
            elif visited.get(nxt) is None:
                dfs(nxt, stack)
        stack.pop()
        visited[node] = 2
    for n in list(broader.keys()):
        if visited.get(n) is None:
            dfs(n, [])
    return cycles

cycles = has_cycle()
print(f"\nCicli rilevati nella gerarchia broader: {len(cycles)}")
for c in cycles[:5]: print(" -", [str(x) for x in c])

# 3. target non-Concept
bad_targets = []
for rel in (SKOS.broader, SKOS.narrower, SKOS.related):
    for s,o in g.subject_objects(rel):
        if o not in concepts:
            bad_targets.append((str(rel), str(s), str(o)))
print(f"\nTarget di broader/narrower/related NON dichiarati skos:Concept: {len(bad_targets)}")
for x in bad_targets[:10]: print(" -", x)

# 4. prefLabel duplicati per lingua sullo stesso concetto (S14)
dup_preflabel = []
for c in concepts:
    labels = list(g.objects(c, SKOS.prefLabel))
    by_lang = defaultdict(list)
    for l in labels:
        by_lang[l.language].append(str(l))
    for lang, vals in by_lang.items():
        if len(vals) > 1:
            dup_preflabel.append((str(c), lang, vals))
print(f"\nConcetti con >1 skos:prefLabel nella stessa lingua (S14): {len(dup_preflabel)}")
for x in dup_preflabel[:10]: print(" -", x)

# 5. prefLabel/definition mancanti @it/@en; altre lingue
missing_label = defaultdict(list)
extra_langs = defaultdict(set)
for c in concepts:
    langs = set(l.language for l in g.objects(c, SKOS.prefLabel))
    for need in ("it","en"):
        if need not in langs:
            missing_label[need].append(str(c))
    for l in langs:
        if l not in ("it","en"):
            extra_langs[str(c)].add(l)

missing_def = defaultdict(list)
for c in concepts:
    langs = set(l.language for l in g.objects(c, SKOS.definition))
    for need in ("it","en"):
        if need not in langs:
            missing_def[need].append(str(c))

print(f"\nConcetti senza prefLabel@it: {len(missing_label['it'])}")
print(f"Concetti senza prefLabel@en: {len(missing_label['en'])}")
print(f"Concetti senza definition@it: {len(missing_def['it'])}")
print(f"Concetti senza definition@en: {len(missing_def['en'])}")
print(f"Concetti con label in lingue ulteriori: {len(extra_langs)} -> {dict(list(extra_langs.items())[:10])}")

# 6. prefLabel identici su concetti distinti (per lingua)
label_index = defaultdict(list)
for c in concepts:
    for l in g.objects(c, SKOS.prefLabel):
        label_index[(l.language, str(l))].append(str(c))
dup_across = {k: v for k, v in label_index.items() if len(v) > 1}
print(f"\nprefLabel identici su concetti DIVERSI: {len(dup_across)}")
for k,v in list(dup_across.items())[:10]: print(" -", k, v)

# 7. ConceptScheme senza hasTopConcept / concetti senza topConceptOf
scheme_top = defaultdict(set)
for s,o in g.subject_objects(SKOS.hasTopConcept):
    scheme_top[s].add(o)
top_of = set(g.subjects(SKOS.topConceptOf, None))
schemes_without_top = sorted(str(s) for s in schemes if s not in scheme_top)
concepts_with_topConceptOf = len(top_of)
print(f"\nConceptScheme senza skos:hasTopConcept: {len(schemes_without_top)}")
for s in schemes_without_top: print(" -", s)
print(f"Concetti con skos:topConceptOf: {concepts_with_topConceptOf}")

# 8. exactMatch / closeMatch domains
domains_used = defaultdict(int)
malformed = []
for rel in (SKOS.exactMatch, SKOS.closeMatch):
    for s,o in g.subject_objects(rel):
        u = str(o)
        if not (u.startswith("http://") or u.startswith("https://")):
            malformed.append((str(rel), str(s), u))
        else:
            # domain = scheme+host
            from urllib.parse import urlparse
            p = urlparse(u)
            domains_used[p.netloc] += 1
print(f"\nDomini esterni usati in exactMatch/closeMatch: {dict(domains_used)}")
print(f"URI malformate: {len(malformed)} -> {malformed[:5]}")

out = {
    "counts": {"concepts": len(concepts), "schemes": len(schemes)},
    "no_scheme": no_scheme,
    "asym_broader": asym_broader,
    "asym_narrower": asym_narrower,
    "cross_scheme_broader": cross_scheme,
    "cycles": [[str(x) for x in c] for c in cycles],
    "bad_targets": bad_targets,
    "dup_preflabel_same_lang": dup_preflabel,
    "missing_label_it": missing_label["it"], "missing_label_en": missing_label["en"],
    "missing_def_it": missing_def["it"], "missing_def_en": missing_def["en"],
    "extra_langs": {k: list(v) for k,v in extra_langs.items()},
    "dup_label_across_concepts": {str(k): v for k,v in dup_across.items()},
    "schemes_without_top_concept": schemes_without_top,
    "concepts_with_topConceptOf": concepts_with_topConceptOf,
    "exact_close_match_domains": dict(domains_used),
    "malformed_match_uris": malformed,
}
with open("_audit/stage3_skos.json","w",encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
