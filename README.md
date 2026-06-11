# ops-web-app - Opificio Potenziale Semantico

## Abstract

**DeSMòS** (Descriptive Semantic Model for Structured Texts) is an OWL 2 ontology
for the formal description of literary constraints understood as generative devices:
rule-governed procedures that orient the writing process and yield textually
identifiable forms. Drawing on the theoretical legacy of the Oulipo and Oplepo
traditions, the ontology operationalises the constraint not as a stylistic descriptor
applied a posteriori but as a productive principle reconstructible from textual
evidence. Three modelling layers articulate this approach: (i) a **procedural layer**,
in which constraints are reified as instances of `crm:E29_Design_or_Procedure`
employed within an `lrmoo:F28_Expression_Creation` event; (ii) a **typological layer**,
in which the nature, origin (tradition vs. authorial invention), constituent operations
and affected formal/semantic units of each constraint are qualified through
SKOS-encoded controlled vocabularies; and (iii) an **evidential layer**, in which the
identifiability of a constraint is grounded in two complementary kinds of evidence —
intratextual textual features and Genettian paratextual declarations (epitextual or
peritextual), modelled respectively as `desmos:TextualFeature` and
`crm:E33_Linguistic_Object`. DeSMòS is designed to support documentation, comparative
analysis and SPARQL-based querying of constrained writing practices across
heterogeneous corpora, and is aligned by reference with CIDOC CRM, LRMoo, PROV-O,
SKOS, INTRO and Dublin Core Terms.

**[IT]** DeSMòS (Descriptive Semantic Model for Structured Texts) è un'ontologia
OWL 2 per la descrizione formale delle costrizioni letterarie intese come dispositivi
generativi: procedure regolate che orientano il processo di scrittura e determinano
la genesi di forme testualmente identificabili. Muovendo dall'eredità teorica delle
tradizioni oulipiana e oplepiana, l'ontologia operativizza la costrizione non come
descrittore stilistico applicato a posteriori ma come principio produttivo
ricostruibile a partire da evidenze testuali. Tre piani di modellazione articolano
questo approccio: (i) un piano procedurale, in cui le costrizioni sono reificate come
istanze di `crm:E29_Design_or_Procedure` impiegate in un evento di
`lrmoo:F28_Expression_Creation`; (ii) un piano tipologico, in cui la natura,
l'origine (tradizione vs. invenzione autoriale), le operazioni costitutive e le unità
formali o semantiche su cui ciascuna costrizione opera sono qualificate attraverso
vocabolari controllati SKOS; e (iii) un piano evidenziale, in cui l'identificabilità
della costrizione si fonda su due ordini di evidenze complementari, caratteristiche
intratestuali e dichiarazioni paratestuali genettiane (epitestuali o peritestuali),
modellati rispettivamente come `desmos:TextualFeature` e `crm:E33_Linguistic_Object`.
DeSMòS è progettata per supportare la documentazione, l'analisi comparativa e
l'interrogazione SPARQL delle pratiche di scrittura vincolata su corpora eterogenei,
ed è allineata per riferimento a CIDOC CRM, LRMoo, PROV-O, SKOS, INTRO e Dublin
Core Terms.

---

## Project Description

**ops-web-app** is a Flask-based web interface for exploring the DeSMòS knowledge
graph. It exposes a navigable, queryable view of the Oplepo corpus: constrained
literary expressions, their formal and semantic constraints, SKOS-encoded constraint
vocabularies, and intertextual alignment data.

The application connects to a local GraphDB triplestore and routes all data retrieval
through SPARQL queries, with no intermediate database layer. The frontend provides:

- **Corpus browser** — faceted navigation of constrained expressions with filtering by
  author, constraint type, tradition of origin, operations involved and formal/semantic
  units
- **Expression detail** — per-expression view with constraints, source fragments,
  bibliographic provenance and intertextual derivation links
- **Constraint explanation** — definition, example, and linked-open-data annotations
  for each SKOS concept
- **Intertextual alignment (Anagrafia)** — token-level visualisation of the textual
  relationship between a constrained expression and its source text, modelled via INTRO
- **SPARQL access** — free query editor, predefined query hub, and visual query builder

### Ontology: DeSMòS v2.0.0

| Property | Value |
|---|---|
| Base IRI | `https://w3id.org/desmos/` |
| Version IRI | `https://w3id.org/desmos/v2.0.0` |
| Corpus namespace | `https://w3id.org/desmos/oplepiana/` |
| Author | [ORCID 0009-0007-5620-3834](https://orcid.org/0009-0007-5620-3834) |
| Alignment pattern | *alignment by reference* — classes and properties from CIDOC CRM, LRMoo, PROV-O, SKOS, INTRO and Dublin Core Terms are re-declared locally without `owl:imports` |

---

## Repository Structure

```
ops-web-app/
├── app.py                      # Flask application (routes + SPARQL queries)
├── requirements.txt            # flask, sparqlwrapper, rdflib, python-dotenv, requests
├── setup.sh                    # local setup script (venv + dependencies)
├── .env.example                # GraphDB configuration template
├── data/
│   ├── ontology/
│   │   └── desmos.owl          # DeSMòS ontology v2.0.0 (809 triples, 29 classes)
│   └── rdf/
│       ├── corpus.ttl          # corpus (expressions, works, constraints — 2,146 triples)
│       └── concept.ttl         # SKOS vocabularies (89 concepts, 8 schemes — 777 triples)
├── scripts/
│   └── bulk_load.py            # bulk data loading into GraphDB
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── anagrafia.js        # intertextual alignment visualisation
│       ├── corpus-filters.js   # corpus faceted filtering
│       ├── puzzle.js           # constraint puzzle interaction
│       ├── sparql-engine.js    # SPARQL query interface
│       └── visual-query.js     # visual query builder
└── templates/                  # Jinja2 HTML templates
    ├── base.html
    ├── index.html
    ├── anagrafia.html          # intertextual alignment view
    ├── corpus.html             # constrained works browser
    ├── expression.html         # single expression detail
    ├── explain.html            # constraint explanation
    ├── project.html            # project description
    ├── query_hub.html          # predefined SPARQL queries
    ├── sparql.html             # free SPARQL editor
    └── visual_query.html       # visual query interface
```

---

## Prerequisites

- Python 3.12
- A running [GraphDB](https://www.ontotext.com/products/graphdb/) instance on
  `localhost:7200` with a repository named `desmos`
- The three RDF files must be loaded into that repository:
  `data/ontology/desmos.owl`, `data/rdf/corpus.ttl`, `data/rdf/concept.ttl`

---

## Quick Start (Local)

```bash
# 1. Clone the repository
git clone https://github.com/enricabruno/ops-web-app.git
cd ops-web-app

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env if your GraphDB instance uses a different URL or repository name

# 5. Load RDF data into GraphDB
#    Option A — GraphDB Workbench: Import → RDF → upload each file
#    Option B — bulk_load.py script:
python scripts/bulk_load.py --file data/ontology/desmos.owl --format rdfxml
python scripts/bulk_load.py --file data/rdf/corpus.ttl --format turtle
python scripts/bulk_load.py --file data/rdf/concept.ttl --format turtle

# 6. Run the application
python app.py

# 7. Open in browser
#    http://localhost:5001
```

---

## Namespaces and Standards

| Prefix | Namespace | Standard |
|---|---|---|
| `desmos:` | `https://w3id.org/desmos/` | DeSMòS ontology |
| `crm:` | `http://www.cidoc-crm.org/cidoc-crm/` | CIDOC CRM |
| `lrmoo:` | `http://iflastandards.info/ns/lrm/lrmoo/` | LRMoo (IFLA LRM) |
| `prov:` | `http://www.w3.org/ns/prov#` | PROV-O |
| `skos:` | `http://www.w3.org/2004/02/skos/core#` | SKOS |
| `intro:` | `https://w3id.org/lso/intro/beta202506#` | INTRO |
| `dct:` | `http://purl.org/dc/terms/` | Dublin Core Terms |
