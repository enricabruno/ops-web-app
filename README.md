# OPS – Opificio Potenziale Semantico

Interfaccia web in Flask per l'esplorazione semantica del corpus delle plaquette dell'Oplepo (*Opificio di Letteratura Potenziale*). I dati sono modellati con **[DeSMòS](https://github.com/enricabruno/desmos)** (*Descriptive Semantic Model for Structured Texts*), un'ontologia OWL 2 per la rappresentazione formale delle costrizioni letterarie, e sono interrogati via SPARQL su un triplestore GraphDB.

## Funzionalità

- **Corpus**: navigazione a faccette delle espressioni vincolate.
- **Schede delle opere**: costrizioni, frammenti paratestuali e collocazione bibliografica di ogni opera.
- **Costrizioni**: definizioni e gerarchia SKOS, con matrice operazioni/unità e grafo dei concetti.
- **Riscritture**: allineamento a livello di token tra testo vincolato e testo sorgente.
- **Endpoint SPARQL** in sola lettura (`SELECT` e `CONSTRUCT`), su `/sparql`.
- **Chatbot**: interrogazione in linguaggio naturale basata su [QRAKEN](https://pypi.org/project/qraken-remote-chatbot/).

## Requisiti

- Python 3.10+
- Docker con Docker Compose
- Token QRAKEN e nome del grafo TTQL
- Chiave API del fornitore del modello per il chatbot

## Avvio

```bash
# 1. Clonare il repository
git clone https://github.com/enricabruno/ops-web-app.git
cd ops-web-app

# 2. Creare e attivare l'ambiente virtuale
python3 -m venv venv
source venv/bin/activate

# 3. Installare le dipendenze
pip install -r requirements.lock.txt

# 4. Configurare l'ambiente: inserire i propri valori in .env
cp .env.example .env

# 5. Avviare GraphDB: crea il repository e carica i dati di data/
docker compose up -d

# 6. Avviare l'applicazione
gunicorn --workers 1 --threads 8 --timeout 200 --bind 0.0.0.0:5001 app:app

# 7. Aprire http://localhost:5001
```

## Fermare

- Applicazione: `Ctrl+C` nel terminale di gunicorn.
- GraphDB: `docker compose down`.

## Aggiornare i dati

1. Modificare i file in `data/`.
2. Ricaricarli in GraphDB con `docker compose restart graphdb`.
3. Riavviare l'applicazione.

## Struttura del progetto

```
ops-web-app/
├── app.py                  # applicazione Flask: route e query SPARQL
├── requirements.txt        # dipendenze dirette
├── requirements.lock.txt   # versioni esatte di tutte le dipendenze
├── .env.example            # modello di configurazione
├── docker-compose.yml      # servizio GraphDB
├── docker/graphdb/         # configurazione del repository e script di caricamento
├── data/
│   ├── ontology/           # ontologia DeSMòS (desmos.owl)
│   └── rdf/                # corpus (corpus.ttl) e schemi SKOS (concept.ttl)
├── scripts/                # script di utilità
├── static/                 # CSS, JavaScript e immagini
└── templates/              # template Jinja2
```

## Crediti

- **DeSMòS, corpus e applicazione web:** Enrica Bruno (enrica.bruno2@unibo.it).
- **Chatbot:** basato su QRAKEN (`qraken-remote-chatbot`): Remo Grillo (remo.grillo@unibo.it).

## Licenza

CC BY 4.0.
