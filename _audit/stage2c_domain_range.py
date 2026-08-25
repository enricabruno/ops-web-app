import json
from collections import defaultdict
from rdflib import Graph, URIRef, BNode, Literal, RDF, RDFS, OWL
from rdflib.collection import Collection

g_owl = Graph(); g_owl.parse("data/ontology/desmos.owl", format="xml")
DATA = {
    "concept.ttl": Graph(),
    "corpus.ttl": Graph(),
    "examples.ttl": Graph(),
}
for name, g in DATA.items():
    g.parse(f"data/rdf/{name}", format="turtle")

# The deployed KG is the UNION of the three data files (all loaded into the same
# GraphDB repository) plus the ontology's own class/individual assertions if any.
# rdf:type membership must therefore be resolved against the MERGED graph, not
# the isolated per-file graph, otherwise every cross-file reference to a
# concept.ttl-defined skos:Concept from corpus.ttl/examples.ttl is a false
# "untyped object" positive.
MERGED = Graph()
for g in DATA.values():
    MERGED += g
MERGED += g_owl

def expand_class_expr(node):
    """Return set of named classes referenced by a domain/range value,
    unwrapping owl:unionOf if present."""
    if isinstance(node, URIRef):
        return {node}
    if isinstance(node, BNode):
        union = list(g_owl.objects(node, OWL.unionOf))
        if union:
            members = list(Collection(g_owl, union[0]))
            out = set()
            for m in members:
                out |= expand_class_expr(m)
            return out
        # intersectionOf or other complex expr: skip (rare / not expected here)
        inter = list(g_owl.objects(node, OWL.intersectionOf))
        if inter:
            members = list(Collection(g_owl, inter[0]))
            out = set()
            for m in members:
                out |= expand_class_expr(m)
            return out
        return set()
    return set()

domain_map = defaultdict(set)   # prop -> set of acceptable classes (union semantics)
range_map = defaultdict(set)
domain_multi = defaultdict(list)  # prop -> list of raw domain nodes (to detect multiple separate assertions)
range_multi = defaultdict(list)

for s, o in g_owl.subject_objects(RDFS.domain):
    domain_multi[s].append(o)
    domain_map[s] |= expand_class_expr(o)
for s, o in g_owl.subject_objects(RDFS.range):
    range_multi[s].append(o)
    range_map[s] |= expand_class_expr(o)

multi_domain_props = {str(k): [str(x) for x in v] for k, v in domain_multi.items() if len(v) > 1}
multi_range_props = {str(k): [str(x) for x in v] for k, v in range_multi.items() if len(v) > 1}

# subclass closure over ALL classes referenced anywhere (owl:Class subjects + anything appearing as domain/range/type)
subclass_of = defaultdict(set)
for s, o in g_owl.subject_objects(RDFS.subClassOf):
    if isinstance(o, URIRef):
        subclass_of[s].add(o)

def ancestors(cls, seen=None):
    if seen is None: seen = set()
    if cls in seen: return seen
    seen.add(cls)
    for parent in subclass_of.get(cls, ()):
        ancestors(parent, seen)
    return seen

XSD = "http://www.w3.org/2001/XMLSchema#"
RDF_LANGSTRING = str(RDF.langString)

def literal_satisfies_range(lit: Literal, expected_classes):
    # expected_classes are class URIs (as strings) that are datatypes (xsd:*) or rdfs:Literal
    dt = lit.datatype
    if dt is None:
        # plain literal: either langString (has lang) or xsd:string-ish plain literal
        eff_dt = RDF_LANGSTRING if lit.language else (XSD + "string")
    else:
        eff_dt = str(dt)
    for exp in expected_classes:
        if exp == eff_dt:
            return True
        if exp == str(RDFS.Literal):
            return True
        # treat xsd:string range as satisfiable by langString too? Per RDF 1.1, no - a langString is not a plain xsd:string.
    return False

violations = defaultdict(lambda: {"count": 0, "examples": []})

for fname, g in DATA.items():
    for s, p, o in g:
        if p == RDF.type:
            continue
        dom = domain_map.get(p)
        if dom:
            s_types = set(MERGED.objects(s, RDF.type))
            s_all_ancestor_types = set()
            for t in s_types:
                s_all_ancestor_types |= ancestors(t)
            if not (s_all_ancestor_types & dom):
                key = f"DOMAIN::{fname}::{p}"
                violations[key]["count"] += 1
                violations[key]["prop"] = str(p)
                violations[key]["file"] = fname
                violations[key]["kind"] = "domain"
                violations[key]["expected"] = sorted(str(x) for x in dom)
                violations[key]["actual_types"] = sorted(str(x) for x in s_types)
                if len(violations[key]["examples"]) < 3:
                    violations[key]["examples"].append({"subject": str(s), "object": str(o)})

        rng = range_map.get(p)
        if rng:
            if isinstance(o, Literal):
                if not literal_satisfies_range(o, {str(x) for x in rng}):
                    key = f"RANGE::{fname}::{p}"
                    violations[key]["count"] += 1
                    violations[key]["prop"] = str(p)
                    violations[key]["file"] = fname
                    violations[key]["kind"] = "range(literal-datatype)"
                    violations[key]["expected"] = sorted(str(x) for x in rng)
                    if len(violations[key]["examples"]) < 3:
                        eff = str(o.datatype) if o.datatype else (RDF_LANGSTRING if o.language else XSD+"string")
                        violations[key]["examples"].append({"subject": str(s), "object": str(o)[:60], "object_effective_datatype": eff})
            elif isinstance(o, URIRef):
                # only check if range is not itself a datatype set (i.e. expects an object/class)
                rng_str = {str(x) for x in rng}
                is_datatype_range = any(x.startswith(XSD) or x == str(RDFS.Literal) or x==RDF_LANGSTRING for x in rng_str)
                if is_datatype_range:
                    continue  # object used where literal expected -> different kind of issue, flagged separately if needed
                o_types = set(MERGED.objects(o, RDF.type))
                o_all_ancestor_types = set()
                for t in o_types:
                    o_all_ancestor_types |= ancestors(t)
                if not (o_all_ancestor_types & rng):
                    key = f"RANGE::{fname}::{p}"
                    violations[key]["count"] += 1
                    violations[key]["prop"] = str(p)
                    violations[key]["file"] = fname
                    violations[key]["kind"] = "range(object-type)"
                    violations[key]["expected"] = sorted(str(x) for x in rng)
                    violations[key]["actual_types"] = sorted(str(x) for x in o_types)
                    if len(violations[key]["examples"]) < 3:
                        violations[key]["examples"].append({"subject": str(s), "object": str(o)})

print(f"Proprietà con dominio dichiarato via owl:unionOf multipli (>1 asserzione rdfs:domain separata): {len(multi_domain_props)}")
print(json.dumps(multi_domain_props, indent=2))
print(f"Proprietà con range dichiarato via owl:unionOf multipli (>1 asserzione rdfs:range separata): {len(multi_range_props)}")
print(json.dumps(multi_range_props, indent=2))

print(f"\nTotale chiavi violazione (proprietà x file x tipo): {len(violations)}")
for k, v in sorted(violations.items(), key=lambda kv: -kv[1]["count"]):
    print(f"\n--- {k} --- count={v['count']}")
    print(json.dumps(v, indent=2, ensure_ascii=False)[:1500])

with open("_audit/stage2_domain_range.json", "w", encoding="utf-8") as f:
    json.dump({"multi_domain_props": multi_domain_props, "multi_range_props": multi_range_props,
               "violations": violations}, f, indent=2, ensure_ascii=False)
