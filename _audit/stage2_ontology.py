import json
from rdflib import Graph, URIRef, RDF, RDFS, OWL
from collections import defaultdict

OWL_NS = "https://w3id.org/desmos/"

g_owl = Graph(); g_owl.parse("data/ontology/desmos.owl", format="xml")
g_concept = Graph(); g_concept.parse("data/rdf/concept.ttl", format="turtle")
g_corpus = Graph(); g_corpus.parse("data/rdf/corpus.ttl", format="turtle")
g_examples = Graph(); g_examples.parse("data/rdf/examples.ttl", format="turtle")

DATA_FILES = {"concept.ttl": g_concept, "corpus.ttl": g_corpus, "examples.ttl": g_examples}

# --- ontology inventory ---
classes = set(g_owl.subjects(RDF.type, OWL.Class))
object_props = set(g_owl.subjects(RDF.type, OWL.ObjectProperty))
datatype_props = set(g_owl.subjects(RDF.type, OWL.DatatypeProperty))
annotation_props = set(g_owl.subjects(RDF.type, OWL.AnnotationProperty))
all_declared_props = object_props | datatype_props | annotation_props

# domain/range
domain = defaultdict(set)
range_ = defaultdict(set)
for s, o in g_owl.subject_objects(RDFS.domain):
    domain[s].add(o)
for s, o in g_owl.subject_objects(RDFS.range):
    range_[s].add(o)

# subclass closure (child -> set of all ancestors incl self)
subclass_of = defaultdict(set)
for s, o in g_owl.subject_objects(RDFS.subClassOf):
    subclass_of[s].add(o)

def ancestors(cls, seen=None):
    if seen is None: seen = set()
    if cls in seen: return seen
    seen.add(cls)
    for parent in subclass_of.get(cls, ()):
        ancestors(parent, seen)
    return seen

closure = {c: ancestors(c) for c in classes}

print(f"Classi OWL dichiarate: {len(classes)}")
print(f"ObjectProperty: {len(object_props)}")
print(f"DatatypeProperty: {len(datatype_props)}")
print(f"AnnotationProperty: {len(annotation_props)}")
print(f"Proprietà con domain dichiarato: {len(domain)}")
print(f"Proprietà con range dichiarato: {len(range_)}")

# --- predicates used in data files not declared in ontology ---
report = {}
BUILTIN_OK = {
    str(RDF.type), str(RDFS.label), str(RDFS.comment), str(RDFS.seeAlso),
    str(OWL.sameAs),
}
for fname, g in DATA_FILES.items():
    used_preds = set(g.predicates())
    missing = sorted(str(p) for p in used_preds
                      if p not in all_declared_props
                      and str(p) not in BUILTIN_OK
                      and not str(p).startswith(str(RDF)) )
    # actual occurrence counts
    occ = defaultdict(int)
    for s,p,o in g:
        occ[str(p)] += 1
    report[fname] = {
        "undeclared_predicates": {m: occ[m] for m in missing}
    }

print(json.dumps(report, indent=2, ensure_ascii=False))

# --- classes used via rdf:type not declared as owl:Class ---
class_report = {}
KNOWN_SKOS_OWL_CLASSES = set()  # skos:Concept, skos:ConceptScheme are external, check separately
for fname, g in DATA_FILES.items():
    used_types = set(g.objects(None, RDF.type))
    missing_classes = sorted(str(c) for c in used_types if c not in classes)
    occ = defaultdict(int)
    for s,o in g.subject_objects(RDF.type):
        occ[str(o)] += 1
    class_report[fname] = {c: occ[c] for c in missing_classes}

print("\n=== CLASSI USATE MA NON DICHIARATE owl:Class IN desmos.owl ===")
print(json.dumps(class_report, indent=2, ensure_ascii=False))

# --- terms declared in ontology never used in any data file ---
all_used_preds_everywhere = set()
all_used_types_everywhere = set()
for g in DATA_FILES.values():
    all_used_preds_everywhere |= set(str(p) for p in g.predicates())
    all_used_types_everywhere |= set(str(o) for o in g.objects(None, RDF.type))

unused_props = sorted(str(p) for p in all_declared_props if str(p) not in all_used_preds_everywhere)
unused_classes = sorted(str(c) for c in classes if str(c) not in all_used_types_everywhere)

print(f"\nProprietà dichiarate mai usate nei dati: {len(unused_props)}")
print(f"Classi dichiarate mai usate nei dati: {len(unused_classes)}")

out = {
    "counts": {
        "classes": len(classes), "object_props": len(object_props),
        "datatype_props": len(datatype_props), "annotation_props": len(annotation_props),
    },
    "undeclared_predicates_by_file": report,
    "undeclared_classes_by_file": class_report,
    "unused_properties": unused_props,
    "unused_classes": unused_classes,
}
with open("_audit/stage2_ontology.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
