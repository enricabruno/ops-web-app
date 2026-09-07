# ops-web-app

## OPS - Opificio Potenziale Semantico

**ops-web-app** è un'interfaccia web (Flask) per esplorare **[DeSMòS](https://github.com/enricabruno/desmos)**
(*Descriptive Semantic Model for Structured Texts*), un'ontologia OWL 2 che
descrive le costrizioni nella tradizione dell'Oulipo (*Ouvroir de Littérature Potentielle*) e dell'Oplepo (Opificio Potenziale Semantico). Le costrizioni sono intese come procedure generative delle opere letterarie.

L'app si collega direttamente ad un triplestore
**GraphDB** e recupera tutti i dati tramite query SPARQL. 
Espone:

- **Corpus browser**: navigazione a faccette delle espressioni vincolate
  (autore, tipo di costrizione, tradizione, operazioni, unità formali/semantiche)
- **Scheda espressione**: dettaglio di una singola opera con costrizioni, 
  frammenti sorgente e provenienza bibliografica;
- **Spiegazione delle costrizioni**: definizione, esempio e annotazioni LOD per ogni concetto SKOS;
- **Anagrafia**: visualizzazione a livello di token dell'allineamento
  intertestuale tra un'espressione vincolata e il suo testo sorgente;
- **Accesso SPARQL**: editor libero, hub di query predefinite e query builder
  visuale;
- **Chatbot (QRAKEN)**: assistente in linguaggio naturale per interrogare il
  knowledge graph.

---

## Prerequisiti

- Python 3.9 o superiore
- Un'istanza di [GraphDB](https://www.ontotext.com/products/graphdb/) attiva
  su `localhost:7200`, con un repository chiamato `desmos`
- Un tenant token QRAKEN e il nome del grafo TTQL (necessari: senza questi
  l'app non si avvia — vedi step 4)

---

## Avvio in locale

```bash
# 1. Clona il repository
git clone https://github.com/enricabruno/ops-web-app.git
cd ops-web-app

# 2. Crea e attiva il virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# 3. Installa le dipendenze
pip install -r requirements.txt
```

### 4. Configura le variabili d'ambiente

```bash
cp .env.example .env
```

Modifica `.env` con i tuoi valori:

| Variabile | Obbligatoria | Descrizione |
|---|---|---|
| `GRAPHDB_URL` | no (default `http://localhost:7200/repositories`) | URL base di GraphDB |
| `REPOSITORY_ID` | no (default `desmos`) | Nome del repository GraphDB |
| `QRAKEN_TENANT_TOKEN` | **sì** | Client key del server QRAKEN — l'app fallisce all'avvio se manca |
| `QRAKEN_TTQL` | **sì** | Nome del grafo di conoscenza da interrogare (`desmos.ttql`) — l'app fallisce all'avvio se manca |
| `QRAKEN_LLM_API_KEY` | consigliata | Chiave Anthropic ([console.anthropic.com](https://console.anthropic.com)), usata dal chatbot per rispondere |
| `QRAKEN_LLM_PROVIDER` | no (default `anthropic`) | Provider LLM usato dal chatbot |

### 5. Avvia GraphDB e carica i dati RDF

Avvia GraphDB (desktop app, standalone server o Docker) e assicurati che
esista un repository `desmos`. Poi carica i tre file RDF:

```bash
# Opzione A: GraphDB Workbench: Import → RDF → carica ciascun file
# Opzione B: script bulk_load.py:
python scripts/bulk_load.py --file data/ontology/desmos.owl --format rdfxml
python scripts/bulk_load.py --file data/rdf/corpus.ttl --format turtle
python scripts/bulk_load.py --file data/rdf/concept.ttl --format turtle
```

### 6. Avvia l'applicazione

```bash
python app.py
```

### 7. Apri il browser

```
http://localhost:5001
```

---

## Struttura del progetto

```
ops-web-app/
├── app.py                # applicazione Flask (route + query SPARQL)
├── requirements.txt       # flask, sparqlwrapper, rdflib, python-dotenv, requests, qraken-remote-chatbot
├── setup.sh               # script di setup locale (venv + dipendenze)
├── .env.example            # template di configurazione
├── data/
│   ├── ontology/desmos.owl  # ontologia DeSMòS
│   └── rdf/                 # corpus.ttl, concept.ttl (dati da caricare in GraphDB)
├── scripts/bulk_load.py     # caricamento bulk dei file RDF in GraphDB
├── static/                  # CSS e JS (filtri corpus, SPARQL engine, anagrafia, ecc.)
└── templates/                # template Jinja2
```

---

## Namespace e standard

| Prefisso | Namespace | Standard |
|---|---|---|
| `desmos:` | `https://w3id.org/desmos/` | DeSMòS ontology |
| `crm:` | `http://www.cidoc-crm.org/cidoc-crm/` | CIDOC CRM |
| `lrmoo:` | `http://iflastandards.info/ns/lrm/lrmoo/` | LRMoo (IFLA LRM) |
| `prov:` | `http://www.w3.org/ns/prov#` | PROV-O |
| `skos:` | `http://www.w3.org/2004/02/skos/core#` | SKOS |
| `intro:` | `https://w3id.org/lso/intro/beta202506#` | INTRO |
| `dct:` | `http://purl.org/dc/terms/` | Dublin Core Terms |
