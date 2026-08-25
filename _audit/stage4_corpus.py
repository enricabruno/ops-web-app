import json, re
from collections import defaultdict, Counter
from rdflib import Graph, URIRef, Literal, RDF, RDFS
from rdflib.namespace import Namespace, SKOS, OWL

LRMOO = Namespace("http://iflastandards.info/ns/lrm/lrmoo/")
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
DESMOS = Namespace("https://w3id.org/desmos/")
DCTERMS = Namespace("http://purl.org/dc/terms/")
PROV = Namespace("http://www.w3.org/ns/prov#")

g_corpus = Graph(); g_corpus.parse("data/rdf/corpus.ttl", format="turtle")
g_concept = Graph(); g_concept.parse("data/rdf/concept.ttl", format="turtle")
MERGED = g_corpus + g_concept

def typed(g, cls):
    return set(g.subjects(RDF.type, cls))

works = typed(MERGED, LRMOO.F1_Work)
expressions = typed(MERGED, LRMOO.F2_Expression)
manifestations = typed(MERGED, LRMOO.F3_Manifestation)
creations = typed(MERGED, LRMOO.F28_Expression_Creation)

print(f"F1_Work: {len(works)}  F2_Expression: {len(expressions)}  F3_Manifestation: {len(manifestations)}  F28_Expression_Creation: {len(creations)}")

# Work -> Expression via R3_is_realised_in
works_without_expr = [str(w) for w in works if not list(MERGED.objects(w, LRMOO.R3_is_realised_in))]
# Expression reachable as R3 target but not typed F2_Expression, or Work target not typed F1
r3_bad_targets = [(str(s), str(o)) for s,o in MERGED.subject_objects(LRMOO.R3_is_realised_in) if o not in expressions]

# Expression -> Manifestation: via R4i_is_embodied_in (expr->manif) or inverse R4_embodies (manif->expr)
expr_to_manif = defaultdict(set)
for s,o in MERGED.subject_objects(LRMOO.R4i_is_embodied_in):
    expr_to_manif[s].add(o)
for s,o in MERGED.subject_objects(LRMOO.R4_embodies):  # s=manifestation, o=expression
    expr_to_manif[o].add(s)
expressions_without_manif = [str(e) for e in expressions if not expr_to_manif.get(e)]

# Expression -> Creation event: via R17i_was_created_by (expr->creation) or inverse R17_created (creation->expr)
expr_to_creation = defaultdict(set)
for s,o in MERGED.subject_objects(LRMOO.R17i_was_created_by):
    expr_to_creation[s].add(o)
for s,o in MERGED.subject_objects(LRMOO.R17_created):  # s=creation, o=expression
    expr_to_creation[o].add(s)
expressions_without_creation = [str(e) for e in expressions if not expr_to_creation.get(e)]

print(f"\nF1_Work senza R3_is_realised_in: {len(works_without_expr)}")
for w in works_without_expr[:10]: print(" -", w)
print(f"R3_is_realised_in con target non tipizzato F2_Expression: {len(r3_bad_targets)}")
for x in r3_bad_targets[:10]: print(" -", x)
print(f"\nF2_Expression senza Manifestation collegata (R4i/R4): {len(expressions_without_manif)}")
for e in expressions_without_manif[:15]: print(" -", e)
print(f"\nF2_Expression senza F28_Expression_Creation collegato (R17i/R17): {len(expressions_without_creation)}")
for e in expressions_without_creation[:15]: print(" -", e)

# F28 has P14_carried_out_by and desmos:usedConstraint
creation_no_actor = [str(c) for c in creations if not list(MERGED.objects(c, CRM.P14_carried_out_by))]
creation_no_constraint = [str(c) for c in creations if not list(MERGED.objects(c, DESMOS.usedConstraint))]
print(f"\nF28_Expression_Creation senza crm:P14_carried_out_by: {len(creation_no_actor)}")
for c in creation_no_actor[:10]: print(" -", c)
print(f"F28_Expression_Creation senza desmos:usedConstraint: {len(creation_no_constraint)}")
for c in creation_no_constraint[:10]: print(" -", c)

# TextualFeature: isFeatureOf AND revealsConstraint
tfeatures = typed(MERGED, DESMOS.TextualFeature)
tf_no_isfeatureof = [str(t) for t in tfeatures if not list(MERGED.objects(t, DESMOS.isFeatureOf))]
tf_no_reveals = [str(t) for t in tfeatures if not list(MERGED.objects(t, DESMOS.revealsConstraint))]
print(f"\ndesmos:TextualFeature totali: {len(tfeatures)}")
print(f"...senza desmos:isFeatureOf: {len(tf_no_isfeatureof)} -> {tf_no_isfeatureof}")
print(f"...senza desmos:revealsConstraint: {len(tf_no_reveals)} -> {tf_no_reveals}")

# E39_Actor: rdfs:label + (owl:sameAs or rdfs:seeAlso), URI syntax check
actors = typed(MERGED, CRM.E39_Actor)
actor_no_label = [str(a) for a in actors if not list(MERGED.objects(a, RDFS.label))]
actor_no_align = [str(a) for a in actors if not (list(MERGED.objects(a, OWL.sameAs)) or list(MERGED.objects(a, RDFS.seeAlso)))]
print(f"\ncrm:E39_Actor totali: {len(actors)}")
print(f"...senza rdfs:label: {len(actor_no_label)} -> {actor_no_label}")
print(f"...senza owl:sameAs/rdfs:seeAlso: {len(actor_no_align)} -> {actor_no_align}")

viaf_re = re.compile(r"^https://viaf\.org/viaf/\d+/?$")
sbn_re = re.compile(r"^http://id\.sbn\.it/bid/[A-Za-z0-9]+$")
bad_viaf = []
bad_sbn = []
for a in actors:
    for o in MERGED.objects(a, OWL.sameAs):
        u = str(o)
        if "viaf.org" in u and not viaf_re.match(u):
            bad_viaf.append((str(a), u))
    for o in MERGED.objects(a, RDFS.seeAlso):
        u = str(o)
        if "id.sbn.it" in u and not sbn_re.match(u):
            bad_sbn.append((str(a), u))
print(f"URI VIAF malformate: {len(bad_viaf)} -> {bad_viaf}")
print(f"URI SBN malformate: {len(bad_sbn)} -> {bad_sbn}")

# Language tagging uniformity
def lang_tag_report(prop, ns_label):
    plain = 0; it = 0; en = 0; other = Counter()
    subjects_plain = []
    for s,o in g_corpus.subject_objects(prop):
        if not isinstance(o, Literal):
            continue
        if o.language == "it": it += 1
        elif o.language == "en": en += 1
        elif o.language is None:
            plain += 1
            if len(subjects_plain) < 5:
                subjects_plain.append((str(s), str(o)[:60]))
        else:
            other[o.language] += 1
    return {"plain_no_lang": plain, "it": it, "en": en, "other_langs": dict(other), "sample_plain": subjects_plain}

lang_report = {}
for prop, name in [(RDFS.label, "rdfs:label"), (DCTERMS.title, "dcterms:title"),
                    (CRM.P3_has_note, "crm:P3_has_note"), (DCTERMS.description, "dcterms:description")]:
    lang_report[name] = lang_tag_report(prop, name)

print("\n=== TAGGING LINGUISTICO ===")
print(json.dumps(lang_report, indent=2, ensure_ascii=False))

# Constraint typing double coverage: FormalConstraint/SemanticConstraint/VisualConstraint
# instances in corpus vs concept.ttl skos:Concept membership
for cls_name in ["FormalConstraint", "SemanticConstraint", "VisualConstraint"]:
    cls = DESMOS[cls_name]
    corpus_instances = typed(g_corpus, cls)
    concept_instances = set(g_concept.subjects(RDF.type, cls))
    as_skos_concept = set(g_concept.subjects(RDF.type, SKOS.Concept))
    missing_as_concept = sorted(str(x) for x in corpus_instances if x not in as_skos_concept)
    print(f"\n{cls_name}: istanze in corpus.ttl={len(corpus_instances)}, tipizzate anche come skos:Concept in concept.ttl={len(corpus_instances)-len(missing_as_concept)}")
    print(f"  ...tipizzate {cls_name} in corpus.ttl ma NON come skos:Concept in concept.ttl: {len(missing_as_concept)}")
    for m in missing_as_concept[:10]: print("   -", m)

# reverse: concepts in FormalConstraintScheme/SemanticConstraintScheme never used as a constraint type in corpus
for scheme_name, cls_name in [("FormalConstraintScheme","FormalConstraint"), ("SemanticConstraintScheme","SemanticConstraint")]:
    scheme = DESMOS[scheme_name]
    cls = DESMOS[cls_name]
    scheme_concepts = set(g_concept.subjects(SKOS.inScheme, scheme))
    corpus_instances = typed(g_corpus, cls)
    never_typed = sorted(str(c) for c in scheme_concepts if c not in corpus_instances)
    print(f"\n{scheme_name}: concetti={len(scheme_concepts)}, mai tipizzati {cls_name} in corpus.ttl: {len(never_typed)}")
    for n in never_typed[:15]: print("   -", n)

# unit/operation/origin scheme membership validation
def scheme_membership_check(prop, expected_scheme_name):
    scheme = DESMOS[expected_scheme_name]
    expected_members = set(g_concept.subjects(SKOS.inScheme, scheme))
    bad = []
    counts = 0
    for s,o in g_corpus.subject_objects(prop):
        counts += 1
        if o not in expected_members:
            bad.append((str(s), str(o)))
    return counts, bad

for prop, scheme in [(DESMOS.constrainsFormalUnit, "FormalUnitScheme"),
                      (DESMOS.constrainsSemanticUnit, "SemanticUnitScheme"),
                      (DESMOS.involvesOperation, "ProceduralOperationScheme"),
                      (DESMOS.constraintOrigin, "ConstraintOriginScheme")]:
    total, bad = scheme_membership_check(prop, scheme)
    print(f"\n{prop}: {total} usi totali, {len(bad)} con oggetto FUORI da {scheme}")
    for b in bad[:10]: print("   -", b)

# P2_has_type -> should be in LiteraryFormScheme or ArtisticFormScheme
lit_scheme_members = set(g_concept.subjects(SKOS.inScheme, DESMOS.LiteraryFormScheme))
art_scheme_members = set(g_concept.subjects(SKOS.inScheme, DESMOS.ArtisticFormScheme))
allowed = lit_scheme_members | art_scheme_members
total_p2 = 0; bad_p2 = []
for s,o in g_corpus.subject_objects(CRM.P2_has_type):
    total_p2 += 1
    if o not in allowed:
        bad_p2.append((str(s), str(o)))
print(f"\ncrm:P2_has_type: {total_p2} usi totali, {len(bad_p2)} con oggetto fuori da LiteraryFormScheme/ArtisticFormScheme")
for b in bad_p2[:10]: print("   -", b)

# Coverage: constraints without involvesOperation / constrains*Unit / constraintOrigin
all_formal = typed(g_corpus, DESMOS.FormalConstraint)
all_semantic = typed(g_corpus, DESMOS.SemanticConstraint)
all_constraints = all_formal | all_semantic
no_operation = [str(c) for c in all_constraints if not list(g_corpus.objects(c, DESMOS.involvesOperation))]
no_unit = [str(c) for c in all_constraints
           if not (list(g_corpus.objects(c, DESMOS.constrainsFormalUnit)) or list(g_corpus.objects(c, DESMOS.constrainsSemanticUnit)))]
no_origin = [str(c) for c in all_constraints if not list(g_corpus.objects(c, DESMOS.constraintOrigin))]
print(f"\nCostrizioni totali (Formal+Semantic) in corpus.ttl: {len(all_constraints)}")
print(f"...senza involvesOperation: {len(no_operation)}")
print(f"...senza constrains*Unit: {len(no_unit)}")
print(f"...senza constraintOrigin: {len(no_origin)}")

# Evidential coverage: constraints not reached by any TextualFeature nor E33_Linguistic_Object via P129_is_about
reached_by_tf = set()
for tf in tfeatures:
    for c in g_corpus.objects(tf, DESMOS.revealsConstraint):
        reached_by_tf.add(c)
reached_by_p129 = set()
for s,o in g_corpus.subject_objects(CRM.P129_is_about):
    reached_by_p129.add(o)
reached = reached_by_tf | reached_by_p129
no_evidence = sorted(str(c) for c in all_constraints if c not in reached)
print(f"\nCostrizioni SENZA alcuna evidenza (né TextualFeature né P129_is_about): {len(no_evidence)}")
for c in no_evidence[:20]: print("   -", c)
print(f"...totale: {len(no_evidence)} su {len(all_constraints)}")

out = {
    "counts": {"F1_Work": len(works), "F2_Expression": len(expressions),
               "F3_Manifestation": len(manifestations), "F28_Expression_Creation": len(creations),
               "TextualFeature": len(tfeatures), "E39_Actor": len(actors),
               "FormalConstraint": len(all_formal), "SemanticConstraint": len(all_semantic)},
    "works_without_expr": works_without_expr,
    "r3_bad_targets": r3_bad_targets,
    "expressions_without_manif": expressions_without_manif,
    "expressions_without_creation": expressions_without_creation,
    "creation_no_actor": creation_no_actor,
    "creation_no_constraint": creation_no_constraint,
    "tf_no_isfeatureof": tf_no_isfeatureof,
    "tf_no_reveals": tf_no_reveals,
    "actor_no_label": actor_no_label,
    "actor_no_align": actor_no_align,
    "bad_viaf": bad_viaf, "bad_sbn": bad_sbn,
    "lang_report": lang_report,
    "no_evidence_constraints": no_evidence,
    "no_operation": no_operation, "no_unit": no_unit, "no_origin": no_origin,
}
with open("_audit/stage4_corpus.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
