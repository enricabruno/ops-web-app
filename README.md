# ops-web-app

## OPS – Opificio Potenziale Semantico

**ops-web-app** è un'interfaccia web (Flask) per esplorare **[DeSMòS](https://github.com/enricabruno/desmos)**
(*Descriptive Semantic Model for Structured Texts*), un'ontologia OWL 2 che descrive le
costrizioni letterarie nella tradizione dell'Oulipo (*Ouvroir de Littérature Potentielle*)
e dell'Oplepo (*Opificio di Letteratura Potenziale*). Le costrizioni sono intese come
procedure generative delle opere letterarie.

L'app si collega a un triplestore **GraphDB** e recupera tutti i dati tramite query SPARQL.
Espone:

- **Corpus**: navigazione a faccette delle espressioni vincolate (autore, genere, tipo di
  costrizione, tradizione, operazioni, unità formali e semantiche);
- **Scheda espressione**: dettaglio di una singola opera, con costrizioni formali, visive e
  semantiche, frammenti paratestuali e collocazione bibliografica;
- **Spiegazione delle costrizioni**: definizione, esempio, gerarchia SKOS e collegamenti LOD
  per ogni concetto;
- **Matrice delle costrizioni**: incrocio tra operazioni e unità vincolate;
- **Riscritture**: allineamento a livello di token tra un'espressione vincolata e il suo
  testo sorgente;
- **Endpoint SPARQL** in sola lettura (query `SELECT` e `CONSTRUCT`), con editor, query di
  esempio e hub di query predefinite;
- **Chatbot**: interrogazione del knowledge graph in linguaggio naturale, basata su
  [QRAKEN](https://pypi.org/project/qraken-remote-chatbot/).

---

## Prerequisiti

- Python 3.9 o superiore
- Un'istanza di [GraphDB](https://graphdb.ontotext.com/) attiva su `localhost:7200`, con un
  repository chiamato `desmos` e ruleset **RDFS-Plus (Optimized)**
- Un tenant token QRAKEN e il nome del grafo TTQL, forniti dall'operatore QRAKEN
  (necessari: senza, l'app non si avvia; vedi passo 4)

---

## Avvio in locale

### 1. Clona il repository

```bash
git clone https://github.com/enricabruno/ops-web-app.git
cd ops-web-app
```

### 2. Crea e attiva il virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 3. Installa le dipendenze

```bash
pip install -r requirements.lock.txt
```

`requirements.lock.txt` fissa le versioni esatte di tutte le librerie (generato con
Python 3.9.6). `requirements.txt` elenca solo le dipendenze dirette.

### 4. Configura le variabili d'ambiente

```bash
cp .env.example .env
```

Modifica `.env` con i tuoi valori: sostituisci i valori d'esempio (`qrk_...`, `sk-ant-...`)
con i tuoi.

| Variabile | Obbligatoria | Descrizione |
|---|---|---|
| `GRAPHDB_URL` | no (default `http://localhost:7200/repositories`) | URL base di GraphDB |
| `REPOSITORY_ID` | no (default `desmos`) | Nome del repository GraphDB |
| `QRAKEN_TENANT_TOKEN` | **sì** | Client key fornita da chi gestisce il server QRAKEN. Segreto |
| `QRAKEN_TTQL` | **sì** | Nome del grafo di conoscenza da interrogare (es. `desmos.ttql`) |
| `QRAKEN_LLM_API_KEY` | consigliata | La tua chiave del provider LLM (con `anthropic`: chiave da [console.anthropic.com](https://console.anthropic.com)). Segreto |
| `QRAKEN_LLM_PROVIDER` | no (default `anthropic`) | `anthropic`, `openai`, `gemini`, `harvard_bedrock` o `lmstudio` |

> **Variabile facoltativa aggiuntiva.** `QRAKEN_LLM_MODEL` non è in `.env.example`: si può
> aggiungere a `.env` per scegliere il modello del provider; se omessa, il modello lo sceglie
> il server QRAKEN.

> **Test in locale senza costi.** Per provare il chatbot sul proprio computer si può usare
> una chiave Gemini del piano gratuito ([Google AI Studio](https://aistudio.google.com/apikey))
> con `QRAKEN_LLM_PROVIDER=gemini` e un modello incluso nel piano gratuito.

### 5. Avvia GraphDB e carica i dati RDF

Avvia GraphDB (desktop app, server standalone o Docker) e crea il repository `desmos` con
ruleset **RDFS-Plus (Optimized)**. Poi carica i tre file RDF nel default graph:

```bash
# Opzione A: GraphDB Workbench → Import → RDF → carica ciascun file
# Opzione B: script bulk_load.py
python scripts/bulk_load.py --file data/ontology/desmos.owl --format rdfxml
python scripts/bulk_load.py --file data/rdf/corpus.ttl --format turtle
python scripts/bulk_load.py --file data/rdf/concept.ttl --format turtle
```

### 6. Avvia l'applicazione

```bash
python app.py
```

Questo comando avvia il server di **sviluppo** di Flask, con debugger attivo: va usato solo
in locale. In un'installazione pubblica l'app va servita da un server WSGI (`app:app`).

### 7. Apri il browser

```
http://localhost:5001
```

---

## Endpoint SPARQL

L'endpoint è in sola lettura: accetta solo query `SELECT` e `CONSTRUCT`
(massimo 30 richieste al minuto per IP).

- **Dal browser:** `http://localhost:5001/sparql`, con editor e query di esempio.
- **Da programma:** inviare la query a `/sparql` con il parametro `query` (GET o POST),
  secondo il SPARQL 1.1 Protocol. I risultati sono in JSON per `SELECT` e in Turtle
  per `CONSTRUCT`.

```bash
curl -G "http://localhost:5001/sparql" \
     --data-urlencode "query=SELECT * WHERE { ?s ?p ?o } LIMIT 10"
```

---

## Struttura del progetto

```
ops-web-app/
├── app.py                    # applicazione Flask (route, query SPARQL, controllo di sola lettura)
├── requirements.txt          # dipendenze dirette
├── requirements.lock.txt     # versioni esatte di tutte le dipendenze
├── .env.example              # modello di configurazione (senza segreti)
├── data/
│   ├── ontology/desmos.owl   # ontologia DeSMòS (TBox)
│   └── rdf/                  # corpus.ttl (ABox) e concept.ttl (schemi SKOS)
├── scripts/                  # caricamento in GraphDB (bulk_load.py) e utilità
├── static/                   # CSS, JS (corpus, matrice, grafo dei concetti, SPARQL, riscritture), immagini
└── templates/                # template Jinja2
```

---

## Namespace e standard

| Prefisso | Namespace | Standard |
|---|---|---|
| `desmos:` | `https://w3id.org/desmos/` | DeSMòS |
| `crm:` | `http://www.cidoc-crm.org/cidoc-crm/` | CIDOC CRM |
| `lrmoo:` | `http://iflastandards.info/ns/lrm/lrmoo/` | LRMoo (IFLA LRM) |
| `intro:` | `https://w3id.org/lso/intro/beta202506#` | INTRO |
| `skos:` | `http://www.w3.org/2004/02/skos/core#` | SKOS |
| `prov:` | `http://www.w3.org/ns/prov#` | PROV-O |
| `dcterms:` | `http://purl.org/dc/terms/` | Dublin Core Terms |
| `schema:` | `http://schema.org/` | Schema.org |

---

## Crediti

- **DeSMòS, corpus e applicazione web:** Enrica Bruno (enrica.bruno2@unibo.it).
- **Chatbot:** basato su QRAKEN (`qraken-remote-chatbot`), sviluppato da Remo Grillo (remo.grillo@unibo.it).

## Licenza

CC BY 4.0.
