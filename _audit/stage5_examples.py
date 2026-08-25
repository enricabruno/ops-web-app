import json, re
from collections import defaultdict, Counter
from rdflib import Graph, URIRef, Literal, RDF
from rdflib.namespace import Namespace, SKOS

DESMOS = Namespace("https://w3id.org/desmos/")
DCTERMS = Namespace("http://purl.org/dc/terms/")

g_ex = Graph(); g_ex.parse("data/rdf/examples.ttl", format="turtle")
g_concept = Graph(); g_concept.parse("data/rdf/concept.ttl", format="turtle")
g_corpus = Graph(); g_corpus.parse("data/rdf/corpus.ttl", format="turtle")

examples = set(g_ex.subjects(RDF.type, DESMOS.CorpusExample))
print(f"desmos:CorpusExample totali: {len(examples)}")

# constraint universe: concepts in FormalConstraintScheme + SemanticConstraintScheme
formal_constraints = set(g_concept.subjects(SKOS.inScheme, DESMOS.FormalConstraintScheme))
semantic_constraints = set(g_concept.subjects(SKOS.inScheme, DESMOS.SemanticConstraintScheme))
all_constraints = formal_constraints | semantic_constraints
print(f"Costrizioni nel vocabolario (Formal+Semantic): {len(all_constraints)}")

illustrates_map = defaultdict(list)  # constraint -> [examples]
for ex, c in g_ex.subject_objects(DESMOS.illustrates):
    illustrates_map[c].append(ex)

illustrated_constraints = set(illustrates_map.keys())

# 1. Coverage
constraints_without_example = sorted(str(c) for c in all_constraints if c not in illustrated_constraints)
examples_illustrating_unknown = sorted(str(c) for c in illustrated_constraints if c not in all_constraints)

# skos:example in concept.ttl
constraints_with_skos_example = set(g_concept.subjects(SKOS.example, None))
full_gap = sorted(str(c) for c in all_constraints
                   if c not in illustrated_constraints and c not in constraints_with_skos_example)

print(f"\nCostrizioni SENZA alcun CorpusExample: {len(constraints_without_example)}")
print(f"CorpusExample che illustrano un URI non presente tra le costrizioni: {len(examples_illustrating_unknown)}")
for x in examples_illustrating_unknown: print("  -", x)
print(f"Costrizioni SENZA skos:example NE' CorpusExample (lacuna piena): {len(full_gap)}")

# 2. uniqueness
multi_example = {str(c): [str(e) for e in exs] for c, exs in illustrates_map.items() if len(exs) > 1}
examples_no_illustrates = sorted(str(e) for e in examples if not list(g_ex.objects(e, DESMOS.illustrates)))
print(f"\nCostrizioni con PIU' di un CorpusExample: {len(multi_example)}")
for k,v in list(multi_example.items())[:10]: print("  -", k, v)
print(f"CorpusExample senza desmos:illustrates: {len(examples_no_illustrates)}")

# 3. naming convention: desmos:example_X must illustrate desmos:X
naming_mismatch = []
for ex in examples:
    local = str(ex).rsplit("/",1)[-1]
    if local.startswith("example_"):
        expected_target = str(DESMOS) + local[len("example_"):]
        targets = [str(t) for t in g_ex.objects(ex, DESMOS.illustrates)]
        if expected_target not in targets:
            naming_mismatch.append((str(ex), expected_target, targets))
print(f"\nDiscordanze di naming (example_X non illustra X): {len(naming_mismatch)}")
for x in naming_mismatch[:15]: print("  -", x)

# 4. bilingualism: rdf:value @it and @en
missing_it = []
missing_en = []
for ex in examples:
    langs = set(l.language for l in g_ex.objects(ex, RDF.value))
    if "it" not in langs: missing_it.append(str(ex))
    if "en" not in langs: missing_en.append(str(ex))
print(f"\nCorpusExample senza rdf:value@it: {len(missing_it)}")
for x in missing_it[:10]: print("  -", x)
print(f"CorpusExample senza rdf:value@en: {len(missing_en)}")
for x in missing_en[:10]: print("  -", x)

# 5. provenance
no_source = sorted(str(e) for e in examples if not list(g_ex.objects(e, DCTERMS.source)))
print(f"\nCorpusExample senza dcterms:source: {len(no_source)}")

corpus_subjects = set(g_corpus.subjects())
dangling_source = []
for e, src in g_ex.subject_objects(DCTERMS.source):
    if src not in corpus_subjects:
        dangling_source.append((str(e), str(src)))
print(f"dcterms:source che puntano a soggetti NON presenti in corpus.ttl: {len(dangling_source)}")
for x in dangling_source[:15]: print("  -", x)

# placeholder detection
placeholder_markers_it = ["placeholder", "segnaposto"]
placeholder_markers_en = ["placeholder"]
def is_placeholder(text, lang):
    t = text.lower()
    return "placeholder" in t or "segnaposto" in t

placeholders = []
real_examples = []
for ex in examples:
    vals = list(g_ex.objects(ex, RDF.value))
    if any(is_placeholder(str(v), v.language) for v in vals):
        placeholders.append(str(ex))
    else:
        real_examples.append(ex)
print(f"\nCorpusExample placeholder: {len(placeholders)}")
print(f"CorpusExample reali (non placeholder): {len(real_examples)}")

# placeholder structure check: type, illustrates, both langs present
ph_bad_structure = []
for ex_str in placeholders:
    ex = URIRef(ex_str)
    has_illustrates = bool(list(g_ex.objects(ex, DESMOS.illustrates)))
    langs = set(l.language for l in g_ex.objects(ex, RDF.value))
    ok = has_illustrates and "it" in langs and "en" in langs
    if not ok:
        ph_bad_structure.append({"example": ex_str, "has_illustrates": has_illustrates, "langs": list(langs)})
print(f"Placeholder con struttura incompleta (manca illustrates o una lingua): {len(ph_bad_structure)}")
for x in ph_bad_structure[:10]: print("  -", x)

# source: distinguish placeholder vs real for no_source
no_source_real = [s for s in no_source if URIRef(s) in real_examples]
no_source_placeholder = [s for s in no_source if URIRef(s) not in real_examples]
print(f"\n...di cui SENZA source e NON placeholder (reali): {len(no_source_real)}")
for x in no_source_real: print("  -", x)
print(f"...di cui SENZA source e placeholder: {len(no_source_placeholder)}")

# 6. block structure (double newline split) for real examples
def count_blocks(text):
    # mirror split_example: split on double newline
    parts = re.split(r'\n\s*\n', text.strip())
    return len(parts)

block_counts = Counter()
deviating = []
for ex in real_examples:
    for v in g_ex.objects(ex, RDF.value):
        n = count_blocks(str(v))
        block_counts[n] += 1
        if n != 3:
            deviating.append((str(ex), v.language, n))
print(f"\nDistribuzione numero blocchi (rdf:value non-placeholder, per singolo valore linguistico): {dict(block_counts)}")
print(f"Valori che deviano da 3 blocchi: {len(deviating)}")
for x in deviating[:25]: print("  -", x)

# 8. vocabulary check: rdf:value declared? illustrates domain/range coherent?
g_owl = Graph(); g_owl.parse("data/ontology/desmos.owl", format="xml")
from rdflib.namespace import RDF as RDFNS
rdf_value_declared = (URIRef(str(RDFNS)+"value"), None, None) in g_owl or list(g_owl.subjects(None, None))
rdf_value_as_prop = any(True for _ in g_owl.triples((URIRef(str(RDFNS)+"value"), RDF.type, None)))
print(f"\nrdf:value dichiarata come property in desmos.owl: {rdf_value_as_prop}")
corpusexample_declared = any(True for _ in g_owl.triples((DESMOS.CorpusExample, RDF.type, None)))
illustrates_declared = any(True for _ in g_owl.triples((DESMOS.illustrates, RDF.type, None)))
print(f"desmos:CorpusExample dichiarata come classe: {corpusexample_declared}")
print(f"desmos:illustrates dichiarata come property: {illustrates_declared}")
from rdflib.namespace import RDFS
print("illustrates domain/range:", list(g_owl.objects(DESMOS.illustrates, RDFS.domain)), list(g_owl.objects(DESMOS.illustrates, RDFS.range)))

# 9. URI minting: are example sources under oplepiana/ namespace consistently?
non_oplepiana_sources = []
for e, src in g_ex.subject_objects(DCTERMS.source):
    if not str(src).startswith("https://w3id.org/desmos/oplepiana/"):
        non_oplepiana_sources.append((str(e), str(src)))
print(f"\ndcterms:source NON nel sotto-namespace oplepiana/: {len(non_oplepiana_sources)}")
for x in non_oplepiana_sources[:10]: print("  -", x)

out = {
    "total_examples": len(examples),
    "total_constraints_vocab": len(all_constraints),
    "constraints_without_example": constraints_without_example,
    "examples_illustrating_unknown": examples_illustrating_unknown,
    "full_gap_no_skos_example_no_corpusexample": full_gap,
    "multi_example": multi_example,
    "examples_no_illustrates": examples_no_illustrates,
    "naming_mismatch": naming_mismatch,
    "missing_value_it": missing_it,
    "missing_value_en": missing_en,
    "no_source": no_source,
    "no_source_real": no_source_real,
    "no_source_placeholder": no_source_placeholder,
    "dangling_source": dangling_source,
    "placeholders": placeholders,
    "placeholder_bad_structure": ph_bad_structure,
    "block_count_distribution": dict(block_counts),
    "block_deviating": deviating,
    "non_oplepiana_sources": non_oplepiana_sources,
}
with open("_audit/stage5_examples.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
