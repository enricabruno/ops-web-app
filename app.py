from flask import Flask, render_template, request, jsonify, send_from_directory
from SPARQLWrapper import SPARQLWrapper, JSON, POST
from dotenv import load_dotenv
from urllib.parse import quote, unquote
from collections import defaultdict
import os
import re

load_dotenv()

_STRIP_PUNCT = re.compile(r'^[^\w]+|[^\w]+$', re.UNICODE)
_APOSTROPHE  = re.compile(r"['\u2018\u2019\u201B\u02BC]")

def _get_tokens(text):
    raw_tokens = text.split()
    normalized = []

    for i, t in enumerate(raw_tokens):
        clean = _STRIP_PUNCT.sub('', t).lower()
        if not clean:
            continue

        next_t  = _STRIP_PUNCT.sub('', raw_tokens[i+1]).lower() if i+1 < len(raw_tokens) else ""
        next2_t = _STRIP_PUNCT.sub('', raw_tokens[i+2]).lower() if i+2 < len(raw_tokens) else ""

        if t == "d'" or clean == "di":
            if next_t == "uomo" or (next_t in ("esser", "essere") and next2_t == "uomo"):
                target = "di_uomo_match"
            elif next_t == "salvezza" or ("aborrita" in next_t and next2_t == "salvezza"):
                target = "di_salvezza_match"
            else:
                target = "di_match"
        elif clean in ("esser", "essere"):
            target = "essere_match"
        elif clean == "uomo":
            target = "uomo_match"
        elif "aborrita" in clean or "abborrita" in clean:
            target = "aborrita_match"
        else:
            target = clean

        normalized.append(target)
    return normalized

app = Flask(__name__)

@app.template_filter('urlencode')
def urlencode_filter(s):
    return quote(str(s), safe='')

@app.template_filter('split_example')
def split_example_filter(text):
    if not text:
        return {'citation': '', 'excerpt': '', 'reading': ''}

    blocks = [b.strip() for b in text.split('\n\n', 2)]

    if len(blocks) >= 3:
        return {'citation': blocks[0], 'excerpt': blocks[1], 'reading': blocks[2]}
    if len(blocks) == 2:
        return {'citation': blocks[0], 'excerpt': '', 'reading': blocks[1]}
    return {'citation': '', 'excerpt': '', 'reading': blocks[0]}

GRAPHDB_URL = os.getenv('GRAPHDB_URL', 'http://localhost:7200/repositories')
REPOSITORY_ID = os.getenv('REPOSITORY_ID', 'desmos')
SPARQL_ENDPOINT = f"{GRAPHDB_URL}/{REPOSITORY_ID}"

def execute_sparql_query(query):
    """Esegue una query SPARQL su GraphDB e restituisce i risultati."""
    try:
        print(f"\n=== SPARQL QUERY DEBUG ===")
        print(f"Endpoint: {SPARQL_ENDPOINT}")
        print(f"Query:\n{query}\n")

        sparql = SPARQLWrapper(SPARQL_ENDPOINT)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        # POST: in GET la query viaggia nell'URL e le query lunghe sfondano il
        # limite di header di Tomcat ("Request header is too large").
        sparql.setMethod(POST)
        results = sparql.query().convert()

        print(f"✓ Query successful")
        print(f"Results count: {len(results.get('results', {}).get('bindings', []))} bindings")
        return {'success': True, 'data': results}
    except Exception as e:
        print(f"✗ SPARQL ERROR: {str(e)}")
        return {'success': False, 'error': str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    # I browser richiedono /favicon.ico automaticamente al primo
    # caricamento, prima ancora di leggere il <link rel="icon"> in <head>.
    # Servito con mimetype esplicito: senza, Flask dedurrebbe image/png
    # dall'estensione del file su disco, e WebKit (a differenza di Blink)
    # non fa MIME sniffing e ignora l'icona.
    return send_from_directory(
        os.path.join(app.root_path, 'static', 'img'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon',
    )

@app.route('/project')
def project():
    return render_template('project.html')

@app.route('/sparql')
def sparql():
    return render_template('sparql.html')

@app.route('/query_hub')
def query_hub():
    return render_template('query_hub.html')

@app.route('/visual_query')
def visual_endpoint():
    return render_template('visual_query.html')

@app.route('/query', methods=['POST'])
def query():
    """Riceve una query SPARQL dal frontend e la inoltra a GraphDB."""
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({'success': False, 'error': 'Nessuna query SPARQL fornita nel body della richiesta.'}), 400
    result = execute_sparql_query(data['query'])
    return jsonify(result)

@app.route('/corpus')
def corpus():
    query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX desmos: <https://w3id.org/desmos/>
    PREFIX lrmoo: <http://iflastandards.info/ns/lrm/lrmoo/>
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

    SELECT ?expression ?title
           (SAMPLE(?workType) AS ?workType)
           (SAMPLE(?_parentTitle) AS ?parentTitle)
           (SAMPLE(?_parentPlaquetteTitle) AS ?parentPlaquetteTitle)
           (SAMPLE(?_directMfTitle) AS ?directMfTitle)
           (SAMPLE(?_directMf) AS ?directMfUri)
           (SAMPLE(?_containerTitle) AS ?containerTitle)
           (SAMPLE(?_parentExpr) AS ?parentExpr)
           (SAMPLE(?_volTitle) AS ?volTitle)
           (GROUP_CONCAT(DISTINCT ?authorName; separator=", ") AS ?authors)
           (GROUP_CONCAT(DISTINCT CONCAT(STR(?constraint), "##", COALESCE(?constraintLabel, ""), "##", COALESCE(?constraintTypeLocal, ""), "##", COALESCE(?originLabel, "")); separator="||") AS ?constraintData)
           (GROUP_CONCAT(DISTINCT ?operationLabel; separator="||") AS ?operationLabels)
           (GROUP_CONCAT(DISTINCT ?formalUnitLabel; separator="||") AS ?formalUnitLabels)
           (GROUP_CONCAT(DISTINCT ?semanticUnitLabel; separator="||") AS ?semanticUnitLabels)
    WHERE {
      # 1. Identificazione dell'Espressione e del suo Titolo
      ?expression a lrmoo:F2_Expression ;
                  dct:title ?title .
      # crm:P2_has_type è OPTIONAL: i testi di riferimento (e_text_*) non lo possiedono
      OPTIONAL { ?expression crm:P2_has_type ?workType }

      # 2. Solo plaquette vincolate: l'evento di creazione deve avere almeno un usedConstraint
      ?creation lrmoo:R17_created ?expression ;
                crm:P14_carried_out_by ?author .
      ?author rdfs:label ?authorName .
      FILTER EXISTS { ?creation desmos:usedConstraint [] }

      # 3. Recupero dei Vincoli (Costrizioni) usati nella creazione
      OPTIONAL {
        ?creation desmos:usedConstraint ?constraint .

        OPTIONAL {
          ?constraint skos:prefLabel ?constraintLabel .
          FILTER(lang(?constraintLabel) = "it")
        }

        # Tipo di costrizione via gerarchia di classi (FormalConstraint / SemanticConstraint)
        OPTIONAL {
          ?constraint rdf:type ?constraintClass .
          FILTER(?constraintClass IN (desmos:FormalConstraint, desmos:SemanticConstraint))
          BIND(STRAFTER(STR(?constraintClass), "https://w3id.org/desmos/") AS ?constraintTypeLocal)
        }

        OPTIONAL {
          ?constraint desmos:constraintOrigin ?origin .
          ?origin skos:prefLabel ?originLabel .
          FILTER(lang(?originLabel) = "it")
        }

        OPTIONAL {
          ?constraint desmos:involvesOperation ?operation .
          ?operation skos:prefLabel ?operationLabel .
          FILTER(lang(?operationLabel) = "it")
        }

        OPTIONAL {
          ?constraint desmos:constrainsFormalUnit ?formalUnit .
          ?formalUnit skos:prefLabel ?formalUnitLabel .
          FILTER(lang(?formalUnitLabel) = "it")
        }

        OPTIONAL {
          ?constraint desmos:constrainsSemanticUnit ?semanticUnit .
          ?semanticUnit skos:prefLabel ?semanticUnitLabel .
          FILTER(lang(?semanticUnitLabel) = "it")
        }
      }

      # 4. Relazione con la Plaquette fisica: "In" vs "Plaquette"
      # SAMPLE() keeps these out of GROUP BY, preventing row multiplication.
      OPTIONAL {
        ?_parentExpr crm:P148_has_component ?expression ;
                     dct:title ?_parentTitle .
        OPTIONAL {
          ?_parentExpr lrmoo:R4i_is_embodied_in ?_parentF3 .
          ?_parentF3 dct:title ?_parentPlaquetteTitle .
        }
      }
      OPTIONAL {
        # Stop at the immediate F3_Manifestation — do NOT traverse crm:P148i_is_component_of.
        # L'inverso ^lrmoo:R4_embodies copre le espressioni che asseriscono solo quel verso.
        ?expression lrmoo:R4i_is_embodied_in|^lrmoo:R4_embodies ?_directMf .
        ?_directMf dct:title ?_directMfTitle .

        # Risalita al volume principale (es. "La Biblioteca Oplepiana, I volume")
        OPTIONAL {
          ?_directMf crm:P148i_is_component_of ?_mainVolume .
          ?_mainVolume dct:title ?_volTitle .
        }

        # Titolo "vero" della plaquette: viene dall'espressione contenitore (es. "Kafkiana"),
        # non dal dcterms:title della manifestazione (che è "Plaquette N. 55").
        OPTIONAL {
          ?_directMf lrmoo:R4_embodies|^lrmoo:R4i_is_embodied_in ?_containerExpr .
          FILTER NOT EXISTS { ?_anyParent crm:P148_has_component ?_containerExpr }
          ?_containerExpr dct:title ?_containerTitle .
        }
      }
    }
    GROUP BY ?expression ?title
    ORDER BY ?title
    """

    result = execute_sparql_query(query)

    print(f"\n=== CORPUS ROUTE DEBUG ===")
    print(f"Query success: {result['success']}")

    if not result['success']:
        print(f"ERROR: {result.get('error', 'Unknown error')}")
    else:
        bindings = result['data'].get('results', {}).get('bindings', [])
        print(f"Total bindings retrieved: {len(bindings)}")
        if bindings:
            print(f"First result sample: {bindings[0]}")

    expressions = []
    facets = {
        'authors': set(),
        'work_types': set(),
        'constraint_types': set(),
        'origins': set(),
        'operations': set(),
        'formal_units': set(),
        'semantic_units': set(),
    }

    if result['success']:
        for b in result['data']['results']['bindings']:

            raw_type = b.get('workType', {}).get('value', '')
            w_type = raw_type.split('/')[-1].split('#')[-1] if raw_type else ''

            constraints = []
            seen_constraint_uris = set()
            raw_data = b.get('constraintData', {}).get('value', '')

            if raw_data:
                for item in raw_data.split('||'):
                    if "##" in item:
                        parts = item.split('##')
                        if len(parts) >= 4:
                            constraint_uri = parts[0]
                            if constraint_uri not in seen_constraint_uris:
                                seen_constraint_uris.add(constraint_uri)
                                constraint_obj = {
                                    'uri': constraint_uri,
                                    'label': parts[1],
                                    'constraint_type': parts[2],
                                    'origin': parts[3]
                                }
                                constraints.append(constraint_obj)
                                if parts[2]:
                                    facets['constraint_types'].add(parts[2])
                                if parts[3]:
                                    facets['origins'].add(parts[3])

            operations_raw = b.get('operationLabels', {}).get('value', '')
            operations = [v.strip() for v in operations_raw.split('||') if v.strip()]

            formal_units_raw = b.get('formalUnitLabels', {}).get('value', '')
            formal_units = [v.strip() for v in formal_units_raw.split('||') if v.strip()]

            semantic_units_raw = b.get('semanticUnitLabels', {}).get('value', '')
            semantic_units = [v.strip() for v in semantic_units_raw.split('||') if v.strip()]

            for op in operations:
                facets['operations'].add(op)
            for fu in formal_units:
                facets['formal_units'].add(fu)
            for su in semantic_units:
                facets['semantic_units'].add(su)

            parent_title = b.get('parentTitle', {}).get('value', '')
            parent_plaquette_title = b.get('parentPlaquetteTitle', {}).get('value', '')
            direct_mf_title = b.get('directMfTitle', {}).get('value', '')
            if parent_title:
                contained_label = f"{parent_title} ({parent_plaquette_title})" if parent_plaquette_title else parent_title
                plaquette_rel = {'type': 'component', 'label': 'In', 'title': contained_label}
            elif direct_mf_title:
                plaquette_rel = {'type': 'direct', 'label': 'Plaquette', 'title': direct_mf_title}
            else:
                plaquette_rel = None

            volume_title = b.get('volTitle', {}).get('value', '').strip() or 'Plaquette singole'

            # Chiave di raggruppamento di secondo livello: la manifestazione (m_plaquette_NN),
            # condivisa dall'espressione contenitore e dai testi che contiene.
            mf_uri = b.get('directMfUri', {}).get('value', '')
            container_title = b.get('containerTitle', {}).get('value', '').strip()
            parent_expr = b.get('parentExpr', {}).get('value', '')
            plaq_match = re.search(r'm_plaquette_(\d+)', mf_uri)

            exp_data = {
                'uri': b['expression']['value'],
                'title': b['title']['value'],
                'author': b['authors']['value'],
                'type': w_type,
                'constraints': constraints,
                'constraint_types': list(set(c['constraint_type'] for c in constraints if c['constraint_type'])),
                'origins': list(set(c['origin'] for c in constraints if c['origin'])),
                'operations': operations,
                'units': sorted(set(formal_units + semantic_units)),
                'plaquette_rel': plaquette_rel,
                'volume': volume_title,
                'mf_uri': mf_uri,
                'plaquette_key': mf_uri,
                'plaquette_label': container_title or direct_mf_title or 'Plaquette senza titolo',
                'plaq_num': int(plaq_match.group(1)) if plaq_match else 999,
                'is_component': bool(parent_expr),
                'parent_expr': parent_expr,
                'is_container': False,  # calcolato dopo, su tutte le espressioni
            }
            expressions.append(exp_data)
            facets['authors'].add(b['authors']['value'])
            if w_type:
                facets['work_types'].add(w_type)

    # Merge formal and semantic units into a single dropdown facet
    facets['units'] = sorted(list(facets.pop('formal_units') | facets.pop('semantic_units')))
    facets = {k: sorted(list(v)) if isinstance(v, set) else v for k, v in facets.items()}

    # Un'espressione è "contenitore" se compare come padre (parentExpr) di almeno un'altra riga
    parent_uris = {e['parent_expr'] for e in expressions if e['parent_expr']}
    for exp_data in expressions:
        exp_data['is_container'] = exp_data['uri'] in parent_uris

    # Raggruppa le espressioni per volume (es. "Biblioteca Oplepiana, Volume I")
    volumes_map = {}
    for exp_data in expressions:
        volumes_map.setdefault(exp_data['volume'], []).append(exp_data)

    def build_plaquette_groups(vol_expressions):
        """Raggruppa le espressioni di un volume per plaquette: <titolo plaquette> → <testi>.

        Il gruppo nasce dalla chiave mf_uri (la manifestazione condivisa da contenitore e
        componenti), mai dalla riga del contenitore: per alcune plaquette (30, 50, 51, 56)
        l'espressione contenitore non compare tra i risultati della query.
        """
        groups_map = {}
        for exp_data in vol_expressions:
            key = exp_data['plaquette_key'] or exp_data['uri']
            group = groups_map.get(key)
            if group is None:
                group = groups_map[key] = {
                    'label': exp_data['plaquette_label'],
                    'num': exp_data['plaq_num'],
                    'container': None,
                    'texts': [],
                }
            if exp_data['is_component']:
                group['texts'].append(exp_data)
            else:
                # Contenitore di una collettanea oppure plaquette monografica: in entrambi
                # i casi la riga descrive la plaquette nel suo insieme.
                group['container'] = exp_data
        # Ordine di plaquette (= ordine fisico nel volume), non alfabetico.
        return sorted(groups_map.values(), key=lambda g: g['num'])

    # Ogni gruppo — i tre volumi e le plaquette autonome — ha lo stesso terzo livello:
    # <volume> → <titolo plaquette> → <testi contenuti>.
    volumes = [{'title': vol_title,
                'expressions': vol_expressions,
                'plaquettes': build_plaquette_groups(vol_expressions)}
               for vol_title, vol_expressions in sorted(volumes_map.items())]

    print(f"Total expressions processed: {len(expressions)}")
    print(f"Facets: {facets}\n")

    error_message = None if result['success'] else result.get('error', 'Unknown error connecting to GraphDB')

    return render_template('corpus.html', expressions=expressions, volumes=volumes, facets=facets, error=error_message)

@app.route('/test-connection')
def test_connection():
    """
    Simple endpoint to test basic GraphDB connectivity.
    Returns JSON with connection status and sample data.
    """
    print("\n=== CONNECTION TEST ===")

    simple_query = "SELECT * WHERE { ?s ?p ?o } LIMIT 1"
    result = execute_sparql_query(simple_query)

    response = {
        'endpoint': SPARQL_ENDPOINT,
        'repository_id': REPOSITORY_ID,
        'connection_test': {
            'success': result['success'],
            'error': result.get('error'),
            'has_data': False
        }
    }

    if result['success']:
        bindings = result['data'].get('results', {}).get('bindings', [])
        response['connection_test']['has_data'] = len(bindings) > 0
        response['connection_test']['sample_count'] = len(bindings)
        if bindings:
            response['connection_test']['sample_triple'] = bindings[0]

    print(f"Connection test result: {response}")
    return jsonify(response)

def _parse_lod_items(raw):
    items = []
    for item in [v for v in raw.split('||') if v]:
        parts = item.split('##', 1)
        label = parts[0]
        link = parts[1] if len(parts) > 1 and parts[1] else None
        items.append({'label': label, 'link': link})
    return items


def _parse_relation_items(raw):
    items = []
    for item in [v for v in raw.split('||') if v]:
        parts = item.split('##', 1)
        uri = parts[0]
        label = parts[1] if len(parts) > 1 and parts[1] else uri
        items.append({'uri': uri, 'label': label})
    return items


# Abbreviazione della fonte esterna, in ordine di verifica. I primi quattro sono
# vocabolari di autorità; id.loc.gov e il Nuovo Soggettario BNCF sono anch'essi dati
# collegati e restano 'LOD'. Tutto il resto (siti d'autore, oplepo.com) è 'WEB':
# risorse di approfondimento, non dati collegati.
_EXTERNAL_SOURCES = (
    ('viaf.org', 'VIAF'),
    ('id.sbn.it', 'SBN'),
    ('wikidata.org', 'WD'),
    ('oulipo.net', 'OULIPO'),
    ('id.loc.gov', 'LOD'),
    ('thes.bncf.firenze.sbn.it', 'LOD'),
    ('oplepo.com', 'Scheda Oplepo'),
)


def _external_source_abbr(link):
    for needle, abbr in _EXTERNAL_SOURCES:
        if needle in link:
            return abbr
    return 'WEB'


@app.route('/explain')
def explain():
    raw_uri = request.args.get('uri', '').strip()
    if not raw_uri:
        return render_template('explain.html', info=None, error="URI della costrizione mancante.")

    uri = unquote(raw_uri)

    query = f"""
    PREFIX desmos: <https://w3id.org/desmos/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?prefLabel ?definition ?example ?originLabel ?type ?scopeNote ?historyNote
           (GROUP_CONCAT(DISTINCT ?altLabel; separator="||") AS ?altLabels)
           (GROUP_CONCAT(DISTINCT CONCAT(STR(?operationLabel), "##", COALESCE(STR(?opMatch), "")); separator="||") AS ?operations)
           (GROUP_CONCAT(DISTINCT CONCAT(STR(?formalUnitLabel), "##", COALESCE(STR(?fuMatch), "")); separator="||") AS ?formalUnits)
           (GROUP_CONCAT(DISTINCT CONCAT(STR(?semanticUnitLabel), "##", COALESCE(STR(?suMatch), "")); separator="||") AS ?semanticUnits)
    WHERE {{
        BIND(<{uri}> AS ?constraint)
        ?constraint a skos:Concept ;
            skos:prefLabel ?prefLabel ;
            rdf:type ?type .
        FILTER(lang(?prefLabel) = "it")
        FILTER(?type IN (desmos:FormalConstraint, desmos:SemanticConstraint, desmos:VisualConstraint))

        OPTIONAL {{ ?constraint skos:definition ?definition . FILTER(lang(?definition) = "it") }}
        OPTIONAL {{ ?constraint skos:example ?example . FILTER(lang(?example) = "it") }}
        OPTIONAL {{ ?constraint skos:scopeNote ?scopeNote . FILTER(lang(?scopeNote) = "it") }}
        OPTIONAL {{ ?constraint skos:historyNote ?historyNote . FILTER(lang(?historyNote) = "it") }}
        OPTIONAL {{ ?constraint skos:altLabel ?altLabel . FILTER(lang(?altLabel) = "it") }}

        OPTIONAL {{ ?constraint desmos:constraintOrigin ?origin . ?origin skos:prefLabel ?originLabel . FILTER(lang(?originLabel) = "it") }}

        OPTIONAL {{
            ?constraint desmos:involvesOperation ?op .
            ?op skos:prefLabel ?operationLabel .
            FILTER(lang(?operationLabel) = "it")
            OPTIONAL {{ ?op skos:exactMatch ?opExact }}
            OPTIONAL {{ ?op skos:closeMatch ?opClose }}
            OPTIONAL {{ ?op skos:relatedMatch ?opRelated }}
            BIND(COALESCE(STR(?opExact), STR(?opClose), STR(?opRelated), "") AS ?opMatch)
        }}
        OPTIONAL {{
            ?constraint desmos:constrainsFormalUnit ?fu .
            ?fu skos:prefLabel ?formalUnitLabel .
            FILTER(lang(?formalUnitLabel) = "it")
            OPTIONAL {{ ?fu skos:exactMatch ?fuExact }}
            OPTIONAL {{ ?fu skos:closeMatch ?fuClose }}
            OPTIONAL {{ ?fu skos:relatedMatch ?fuRelated }}
            BIND(COALESCE(STR(?fuExact), STR(?fuClose), STR(?fuRelated), "") AS ?fuMatch)
        }}
        OPTIONAL {{
            ?constraint desmos:constrainsSemanticUnit ?su .
            ?su skos:prefLabel ?semanticUnitLabel .
            FILTER(lang(?semanticUnitLabel) = "it")
            OPTIONAL {{ ?su skos:exactMatch ?suExact }}
            OPTIONAL {{ ?su skos:closeMatch ?suClose }}
            OPTIONAL {{ ?su skos:relatedMatch ?suRelated }}
            BIND(COALESCE(STR(?suExact), STR(?suClose), STR(?suRelated), "") AS ?suMatch)
        }}
    }}
    GROUP BY ?prefLabel ?definition ?example ?originLabel ?type ?scopeNote ?historyNote
    """
    result = execute_sparql_query(query)

    if not result['success'] or not result['data']['results']['bindings']:
        return render_template('explain.html', info=None, error="Costrizione non trovata.")

    row = result['data']['results']['bindings'][0]

    full_type_uri = row.get('type', {}).get('value', '')
    class_name = full_type_uri.split('/')[-1]
    if 'Formal' in class_name:
        display_type = "Formale"
    elif 'Semantic' in class_name:
        display_type = "Semantica"
    elif 'Visual' in class_name:
        display_type = "Visuale"
    else:
        display_type = class_name

    info = {
        'uri': uri,
        'label': row.get('prefLabel', {}).get('value', ''),
        'definition': row.get('definition', {}).get('value', 'Definizione non disponibile.'),
        'example': row.get('example', {}).get('value', None),
        'class_type': class_name,
        'display_type': display_type,
        'origin': row.get('originLabel', {}).get('value', None),
        'scope_note': row.get('scopeNote', {}).get('value', None),
        'history_note': row.get('historyNote', {}).get('value', None),
        'alt_labels': [v.strip() for v in row.get('altLabels', {}).get('value', '').split('||') if v.strip()],
        'operations': _parse_lod_items(row.get('operations', {}).get('value', '')),
        'formal_units': _parse_lod_items(row.get('formalUnits', {}).get('value', '')),
        'semantic_units': _parse_lod_items(row.get('semanticUnits', {}).get('value', '')),
    }

    relations_query = f"""
    PREFIX desmos: <https://w3id.org/desmos/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

    SELECT
           (GROUP_CONCAT(DISTINCT CONCAT(STR(?broader), "##", ?broaderLabel); separator="||") AS ?broaderData)
           (GROUP_CONCAT(DISTINCT CONCAT(STR(?narrower), "##", ?narrowerLabel); separator="||") AS ?narrowerData)
           (GROUP_CONCAT(DISTINCT CONCAT(STR(?related), "##", ?relatedLabel); separator="||") AS ?relatedData)
           (GROUP_CONCAT(DISTINCT STR(?exactMatch); separator="||") AS ?exactMatches)
           (GROUP_CONCAT(DISTINCT STR(?closeMatch); separator="||") AS ?closeMatches)
    WHERE {{
        BIND(<{uri}> AS ?constraint)
        OPTIONAL {{
            ?constraint skos:broader ?broader .
            ?broader skos:prefLabel ?broaderLabel .
            FILTER(lang(?broaderLabel) = "it")
        }}
        OPTIONAL {{
            ?constraint skos:narrower ?narrower .
            ?narrower skos:prefLabel ?narrowerLabel .
            FILTER(lang(?narrowerLabel) = "it")
        }}
        OPTIONAL {{
            ?constraint skos:related ?related .
            ?related skos:prefLabel ?relatedLabel .
            FILTER(lang(?relatedLabel) = "it")
        }}
        OPTIONAL {{ ?constraint skos:exactMatch ?exactMatch }}
        OPTIONAL {{ ?constraint skos:closeMatch ?closeMatch }}
    }}
    """
    rel_result = execute_sparql_query(relations_query)
    info['broader'] = []
    info['narrower'] = []
    info['related'] = []
    info['exact_matches'] = []
    info['close_matches'] = []
    if rel_result['success'] and rel_result['data']['results']['bindings']:
        rel_row = rel_result['data']['results']['bindings'][0]
        info['broader'] = _parse_relation_items(rel_row.get('broaderData', {}).get('value', ''))
        info['narrower'] = _parse_relation_items(rel_row.get('narrowerData', {}).get('value', ''))
        info['related'] = _parse_relation_items(rel_row.get('relatedData', {}).get('value', ''))
        info['exact_matches'] = [
            {'uri': m, 'source': _external_source_abbr(m)}
            for m in rel_row.get('exactMatches', {}).get('value', '').split('||') if m
        ]
        info['close_matches'] = [
            {'uri': m, 'source': _external_source_abbr(m)}
            for m in rel_row.get('closeMatches', {}).get('value', '').split('||') if m
        ]

    occurrences_query = f"""
    PREFIX desmos:  <https://w3id.org/desmos/>
    PREFIX lrmoo:   <http://iflastandards.info/ns/lrm/lrmoo/>
    PREFIX crm:     <http://www.cidoc-crm.org/cidoc-crm/>
    PREFIX dcterms: <http://purl.org/dc/terms/>

    SELECT DISTINCT ?expr ?title ?year ?visible
    WHERE {{
      ?creation desmos:usedConstraint <{uri}> ;
                lrmoo:R17_created ?expr .
      OPTIONAL {{ ?expr dcterms:title ?title }}
      OPTIONAL {{ ?creation dcterms:created ?year }}
      OPTIONAL {{
        ?feat desmos:revealsConstraint <{uri}> ;
              desmos:isFeatureOf ?featTarget .
        {{ BIND(?expr AS ?featTarget) }}
        UNION
        {{ ?expr crm:P148_has_component ?featTarget }}
      }}
      BIND(BOUND(?feat) AS ?visible)
    }}
    ORDER BY ?year ?title
    """
    occ_result = execute_sparql_query(occurrences_query)
    occurrences = []
    if occ_result['success']:
        for b in occ_result['data']['results']['bindings']:
            occurrences.append({
                'uri': b.get('expr', {}).get('value', ''),
                'title': b.get('title', {}).get('value', ''),
                'year': b.get('year', {}).get('value', ''),
                'visible': b.get('visible', {}).get('value', '') == 'true',
            })
    info['occurrences'] = occurrences

    return render_template('explain.html', info=info, error=None)

@app.route('/expression')
def expression():
    raw_uri = request.args.get('uri', '').strip()
    if not raw_uri:
        return render_template('expression.html', expr=None,
                               error="URI dell'espressione mancante.")

    uri = unquote(raw_uri)

    query = """
    PREFIX desmos: <https://w3id.org/desmos/>
    PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX lrmoo: <http://iflastandards.info/ns/lrm/lrmoo/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX intro: <https://w3id.org/lso/intro/beta202506#>
    PREFIX schema: <http://schema.org/>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX prov: <http://www.w3.org/ns/prov#>

    SELECT ?title ?authorName ?year
           (GROUP_CONCAT(DISTINCT ?authorLinkRaw; separator="||") AS ?authorLinks)
           (GROUP_CONCAT(DISTINCT ?wtLabel; separator=", ") AS ?workTypeLabels)
           (SAMPLE(?_manifTitle) AS ?manifTitle)
           (SAMPLE(STR(?_parentExpr)) AS ?parentExprStr)
           (SAMPLE(?_parentTitle) AS ?parentTitle)
           (SAMPLE(?_volTitle) AS ?volTitle)
           (SAMPLE(?hasAlignment) AS ?alignment)
           (SAMPLE(?isHypotextRaw) AS ?isHypotext)
           (GROUP_CONCAT(DISTINCT ?childData; separator="||") AS ?childrenData)
           (GROUP_CONCAT(DISTINCT ?tfData; separator="||") AS ?featuresData)
           (GROUP_CONCAT(DISTINCT ?declPair; separator="||") AS ?declaredData)
           (GROUP_CONCAT(DISTINCT CONCAT(STR(?constraint), "##", STR(?constraintLabel), "##", STR(?scheme)); separator="||") AS ?constraintData)
           (GROUP_CONCAT(DISTINCT ?fragData; separator="|||") AS ?fragmentsConcat)
           (GROUP_CONCAT(DISTINCT ?exactMatch; separator="||") AS ?exactMatches)
           (GROUP_CONCAT(DISTINCT ?seeAlso; separator="||") AS ?seeAlsos)
           (GROUP_CONCAT(DISTINCT CONCAT(STR(?srcExpr), "##", STR(?srcTitle)); separator="||") AS ?derivedFrom)
    WHERE {
        BIND(<%s> AS ?uri)

        ?uri dct:title ?title .
        # Un ipotesto (fonte esterna, es. la Commedia) ha comunque una F3_Manifestation
        # per completezza del modello LRMoo, ma è un'entità-stub con lo stesso titolo
        # dell'espressione: non è una collocazione reale da mostrare in scheda.
        BIND(EXISTS { ?anyExpr lrmoo:R76_is_derivative_of ?uri } AS ?isHypotextRaw)
        # Forma testuale: etichette italiane dei concetti SKOS. Fuori dalla GROUP BY,
        # altrimenti un'espressione multi-tipo moltiplica le righe e se ne perde parte.
        OPTIONAL {
            ?uri crm:P2_has_type ?workType .
            ?workType skos:prefLabel ?wtLabel .
            FILTER(lang(?wtLabel) = "it")
        }
        OPTIONAL { ?uri rdfs:seeAlso ?seeAlso }

        ?creation lrmoo:R17_created ?uri ;
                  crm:P14_carried_out_by ?author .
        ?author rdfs:label ?authorName .
        # 10 autori su 51 non hanno owl:sameAs ma solo rdfs:seeAlso: servono entrambe.
        OPTIONAL { ?author owl:sameAs|rdfs:seeAlso ?authorLinkRaw }

        OPTIONAL { ?creation dct:created ?year }

        # 1. Recupero Manifestazione: property path cattura R4i_is_embodied_in e ^R4_embodies
        OPTIONAL {
            ?uri (lrmoo:R4i_is_embodied_in | ^lrmoo:R4_embodies) ?_manifNode .
            ?_manifNode dct:title ?_manifTitleRaw .
            BIND(STR(?_manifTitleRaw) AS ?_manifTitle)

            # Risalita al volume, per il breadcrumb
            OPTIONAL {
                ?_manifNode crm:P148i_is_component_of ?_vol .
                ?_vol dct:title ?_volTitle .
            }
        }
        # 1b. Espressione padre (plaquette contenitore) con titolo, per link e breadcrumb
        OPTIONAL {
            ?uri crm:P148i_is_component_of|^crm:P148_has_component ?_parentExpr .
            ?_parentExpr dct:title ?_parentTitle .
        }
        # 1c. Testi contenuti, se l'espressione è un contenitore
        OPTIONAL {
            ?uri crm:P148_has_component ?child .
            ?child dct:title ?childTitle .
            OPTIONAL {
                ?chCr lrmoo:R17_created ?child ;
                      crm:P14_carried_out_by ?chA .
                ?chA rdfs:label ?childAuthor .
            }
            BIND(CONCAT(STR(?child), "##", STR(?childTitle), "##", COALESCE(STR(?childAuthor), "")) AS ?childData)
        }

        # 2. Costrizioni
        OPTIONAL {
            ?creation desmos:usedConstraint ?constraint .
            ?constraint skos:prefLabel ?constraintLabel ;
                        skos:inScheme ?scheme .
            FILTER(lang(?constraintLabel) = "it")
        }

        # 3. Frammenti (Linguistic Objects) con risalita alla fonte bibliografica
        # Path: ling_obj → P67_refers_to → expression → R4i_is_embodied_in → plaquette
        #        plaquette → P148i_is_component_of → main_volume → dct:title
        #        plaquette → schema:pagination
        OPTIONAL {
            ?lingObj a crm:E33_Linguistic_Object ;
                     crm:P67_refers_to ?uri ;
                     crm:P3_has_note ?fragText .
            OPTIONAL { ?lingObj crm:P190_has_symbolic_content ?fragContent }
            # Costrizione dichiarata dal paratesto. Può essercene più d'una: la coppia
            # viene proiettata a parte e riagganciata al frammento in Python via URI.
            OPTIONAL {
                ?lingObj crm:P129_is_about ?declC .
                ?declC skos:prefLabel ?declCL .
                FILTER(lang(?declCL) = "it")
                BIND(CONCAT(STR(?lingObj), "§", STR(?declC), "§", STR(?declCL)) AS ?declPair)
            }
            # Voce che ha redatto la dichiarazione paratestuale: non è detto sia l'autore
            # letterario dell'espressione (crm:P14_carried_out_by, altro predicato).
            OPTIONAL {
                ?lingObj prov:wasAttributedTo ?loAuthor .
                ?loAuthor rdfs:label ?loAuthorLabel .
            }
            BIND("direct" AS ?fSource)
            OPTIONAL {
                ?uri lrmoo:R4i_is_embodied_in ?plaquette .
                ?plaquette dct:title ?fragManTitle .
                OPTIONAL { ?plaquette schema:pagination ?pageVal }
                OPTIONAL { ?plaquette dct:issued ?directYear }
                OPTIONAL {
                    ?plaquette crm:P148i_is_component_of ?mainVolume .
                    ?mainVolume dct:title ?volTitle ;
                                dct:issued ?volYear .
                }
            }

            BIND(COALESCE(STR(?fragManTitle), "") AS ?finalManTitle)
            BIND(COALESCE(STR(?volTitle), "") AS ?finalVolTitle)
            BIND(COALESCE(STR(?volYear), STR(?directYear), "") AS ?finalYear)
            BIND(COALESCE(STR(?pageVal), "") AS ?finalPage)
            BIND(COALESCE(STR(?fragContent), "") AS ?finalContent)
            BIND(COALESCE(STR(?loAuthorLabel), "") AS ?finalLoAuthor)
            BIND(CONCAT(STR(?lingObj), "##", STR(?fragText), "##", ?finalManTitle, "##", ?finalYear, "##", ?finalPage, "##", STR(?fSource), "##", ?finalContent, "##", ?finalLoAuthor, "##", ?finalVolTitle) AS ?fragData)
        }

        # 3b. Tratti testuali rivelatori (desmos:TextualFeature). Una feature può
        # rivelare più costrizioni: si proiettano coppie (feature, costrizione) e si
        # raggruppa per feature in Python, evitando una subquery correlata.
        OPTIONAL {
            ?tf a desmos:TextualFeature ;
                desmos:isFeatureOf ?uri ;
                crm:P3_has_note ?tfNote .
            OPTIONAL {
                ?tf desmos:revealsConstraint ?tfC .
                ?tfC skos:prefLabel ?tfCL .
                FILTER(lang(?tfCL) = "it")
            }
            BIND(CONCAT(STR(?tf), "§", STR(?tfNote), "§",
                        COALESCE(STR(?tfC), ""), "§", COALESCE(STR(?tfCL), "")) AS ?tfData)
        }

        OPTIONAL { ?uri lrmoo:R76_is_derivative_of ?srcExpr . ?srcExpr dct:title ?srcTitle . }

        # 4. Flag allineamento testuale (INTRO TextPassage)
        OPTIONAL {
            ?targetPassage a intro:INT21_TextPassage ;
                           intro:R30i_isTextPassageOf ?uri .
            BIND("true" AS ?hasAlignment)
        }
    }
    GROUP BY ?title ?authorName ?year ?hasAlignment
    """ % uri

    result = execute_sparql_query(query)
    if not result['success'] or not result['data']['results']['bindings']:
        return render_template('expression.html', expr=None, error="Dati non trovati.")

    b = result['data']['results']['bindings'][0]

    work_types = b.get('workTypeLabels', {}).get('value', '')

    constraints_formali, constraints_semantiche = [], []
    seen_uris = set()
    raw_constraints = b.get('constraintData', {}).get('value', '')
    if raw_constraints:
        for item in raw_constraints.split('||'):
            parts = item.split('##')
            if len(parts) >= 3 and parts[0] not in seen_uris:
                seen_uris.add(parts[0])
                obj = {'uri': parts[0], 'label': parts[1]}
                if 'FormalConstraintScheme' in parts[2]: constraints_formali.append(obj)
                elif 'SemanticConstraintScheme' in parts[2]: constraints_semantiche.append(obj)

    # Costrizioni dichiarate dal paratesto (P129_is_about), raggruppate per E33 di origine
    declared_by_obj = {}
    for pair in b.get('declaredData', {}).get('value', '').split('||'):
        bits = pair.split('§')
        if len(bits) == 3 and bits[1]:
            entry = {'uri': bits[1], 'label': bits[2]}
            bucket = declared_by_obj.setdefault(bits[0], [])
            if entry not in bucket:
                bucket.append(entry)

    fragments = []
    seen_frag_texts = set()
    raw_frags = b.get('fragmentsConcat', {}).get('value', '')
    if raw_frags:
        for entry in raw_frags.split('|||'):
            entry = entry.strip()
            if not entry:
                continue
            # 9-part concat: obj_uri ## text ## man_title ## year ## page ## source ## content ## lo_author ## vol_title
            parts = entry.split('##', 8)
            obj_uri = parts[0].strip()
            frag_text = parts[1].strip() if len(parts) > 1 else ''
            if not frag_text or frag_text in seen_frag_texts:
                continue
            seen_frag_texts.add(frag_text)
            fragments.append({
                'uri':       obj_uri,
                'text':      frag_text,
                'man_title': parts[2].strip() if len(parts) > 2 else '',
                'issued':    parts[3].strip() if len(parts) > 3 else '',
                'page':      parts[4].strip() if len(parts) > 4 else '',
                'source':    parts[5].strip() if len(parts) > 5 else 'direct',
                'content':   parts[6].strip() if len(parts) > 6 else '',
                'lo_author': parts[7].strip() if len(parts) > 7 and parts[7].strip() else None,
                'vol_title': parts[8].strip() if len(parts) > 8 and parts[8].strip() else None,
                'declared':  declared_by_obj.get(obj_uri, []),
            })
    # Ancora stabile per il rimando dell'asse bipolare al testo sotto: assegnata
    # sulla lista già filtrata/deduplicata, non sull'indice grezzo del ciclo.
    for i, frag in enumerate(fragments, start=1):
        frag['anchor'] = f'ev-decl-{i}'

    # Tratti testuali rivelatori: coppie (feature, costrizione) raggruppate per feature,
    # così una nota con più costrizioni rivelate resta una sola voce.
    features_by_uri = {}
    for pair in b.get('featuresData', {}).get('value', '').split('||'):
        bits = pair.split('§')
        if len(bits) != 4 or not bits[0]:
            continue
        feat = features_by_uri.setdefault(bits[0], {'note': bits[1], 'constraints': []})
        if bits[2]:
            entry = {'uri': bits[2], 'label': bits[3]}
            if entry not in feat['constraints']:
                feat['constraints'].append(entry)
    features = list(features_by_uri.values())
    for i, feat in enumerate(features, start=1):
        feat['anchor'] = f'ev-feat-{i}'

    # Testi contenuti (se l'espressione è una plaquette contenitore)
    children = []
    for item in b.get('childrenData', {}).get('value', '').split('||'):
        bits = item.split('##')
        if len(bits) >= 2 and bits[0]:
            children.append({'uri': bits[0], 'title': bits[1],
                             'author': bits[2] if len(bits) > 2 else ''})
    children.sort(key=lambda c: c['title'])

    # Statuto della costrizione: tassonomia 2×2 su dichiarazione paratestuale e
    # tratto testuale manifesto.
    has_declaration, has_features = bool(fragments), bool(features)
    if has_declaration and has_features:
        status_key, status_label = 'dichiarata-manifesta', 'Costrizione dichiarata e manifesta'
    elif has_declaration:
        status_key, status_label = 'dichiarata', 'Costrizione dichiarata'
    elif has_features:
        status_key, status_label = 'manifesta', 'Costrizione non dichiarata ma manifesta nel testo'
    else:
        status_key, status_label = 'implicita', 'Costrizione implicita'

    # Asse bipolare: a differenza di status_key/status_label sopra (vero se ALMENO UNA
    # dichiarazione/tratto esiste in tutta l'espressione), qui lo stato è per costrizione
    # — un'espressione con tre costrizioni può avere tre stati diversi. I dati vengono
    # dalle stesse due join già presenti nella query grande (P67_refers_to+P129_is_about
    # per il paratesto, isFeatureOf+revealsConstraint per il tratto), solo raggruppati
    # per costrizione invece che per oggetto di evidenza.
    decl_anchor_by_constraint = {}
    for frag in fragments:
        for c in frag['declared']:
            decl_anchor_by_constraint.setdefault(c['uri'], frag['anchor'])

    feat_anchor_by_constraint = {}
    for feat in features:
        for c in feat['constraints']:
            feat_anchor_by_constraint.setdefault(c['uri'], feat['anchor'])

    evidence = []
    for c in constraints_formali + constraints_semantiche:
        declared = c['uri'] in decl_anchor_by_constraint
        manifest = c['uri'] in feat_anchor_by_constraint
        if declared and manifest:
            ev_status_key, ev_status_label = 'dichiarata-manifesta', 'Costrizione dichiarata e manifesta'
        elif declared:
            ev_status_key, ev_status_label = 'dichiarata', 'Costrizione dichiarata'
        elif manifest:
            ev_status_key, ev_status_label = 'manifesta', 'Costrizione non dichiarata ma manifesta nel testo'
        else:
            ev_status_key, ev_status_label = 'implicita', 'Costrizione implicita'
        evidence.append({
            'uri': c['uri'],
            'label': c['label'],
            'declared': declared,
            'manifest': manifest,
            'status_key': ev_status_key,
            'status_label': ev_status_label,
            'decl_anchor': decl_anchor_by_constraint.get(c['uri']),
            'feat_anchor': feat_anchor_by_constraint.get(c['uri']),
        })

    def _link_list(raw):
        """Da stringa concatenata a lista deduplicata di {url, abbr}, ordine preservato."""
        out, seen = [], set()
        for url in (u.strip() for u in raw.split('||')):
            if url and url not in seen:
                seen.add(url)
                out.append({'url': url, 'abbr': _external_source_abbr(url)})
        return out

    author_links = _link_list(b.get('authorLinks', {}).get('value', ''))
    resources = _link_list(b.get('seeAlsos', {}).get('value', '') + '||' +
                           b.get('exactMatches', {}).get('value', ''))

    is_hypotext = b.get('isHypotext', {}).get('value', '') == 'true'
    # Un ipotesto ha comunque una F3_Manifestation per completezza del modello
    # (v. commento nella query): non è una collocazione dichiarata, va taciuta.
    manif_title = '' if is_hypotext else b.get('manifTitle', {}).get('value', '')
    parent_expr_str = b.get('parentExprStr', {}).get('value', '')
    parent_title = b.get('parentTitle', {}).get('value', '')
    parent = {'uri': parent_expr_str, 'title': parent_title} if parent_expr_str else None
    manif_label = 'In:' if parent else 'Plaquette:'

    expr = {
        'uri': uri,
        'title': b['title']['value'],
        'author': b['authorName']['value'],
        'author_links': author_links,
        'year': b.get('year', {}).get('value', ''),
        'work_types': work_types,
        'total_constraints': len(seen_uris),
        'constraints_formali': constraints_formali,
        'constraints_semantiche': constraints_semantiche,
        'fragments': fragments,
        'features': features,
        'evidence': evidence,
        'children': children,
        'parent': parent,
        'volume_title': b.get('volTitle', {}).get('value', ''),
        'status_key': status_key,
        'status_label': status_label,
        'sources': [{'uri': x.split('##')[0], 'title': x.split('##')[1]} for x in b.get('derivedFrom', {}).get('value', '').split('||') if '##' in x],
        'resources': resources,
        'manif_title': manif_title,
        'manif_label': manif_label,
        'has_alignment': b.get('alignment', {}).get('value', '') == 'true',
    }
    return render_template('expression.html', expr=expr, error=None)

@app.route('/anagrafia')
def anagrafia():
    raw_uri = request.args.get('uri', '').strip()
    if not raw_uri:
        return render_template('anagrafia.html', data=None, error="URI mancante.")
    
    uri = unquote(raw_uri) 

    query = f"""
    PREFIX desmos: <https://w3id.org/desmos/>
    PREFIX lrmoo: <http://iflastandards.info/ns/lrm/lrmoo/>
    PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
    PREFIX intro: <https://w3id.org/lso/intro/beta202506#>
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?exprTitle ?targetText ?sourceTitle ?sourceText ?authorName ?srcAuthorName
    WHERE {{
        BIND(<{uri}> AS ?expr)

        # 1. Titolo dell'ipertesto
        ?expr dct:title ?exprTitle .

        # 2. Testo dell'ipertesto via passaggio testuale INTRO
        ?targetPassage a intro:INT21_TextPassage ;
                       intro:R30i_isTextPassageOf ?expr ;
                       intro:R44_hasWording ?targetText .

        # 3. Relazione intertestuale: ipertesto → ipotesto
        ?rel a intro:INT31_IntertextualRelation ;
             intro:R13_hasReferringEntity ?expr ;
             intro:R12_hasReferredToEntity ?srcExpr .

        # 4. Titolo e testo dell'ipotesto via passaggio testuale INTRO
        ?srcExpr dct:title ?sourceTitle .
        ?srcPassage a intro:INT21_TextPassage ;
                    intro:R30i_isTextPassageOf ?srcExpr ;
                    intro:R44_hasWording ?sourceText .

        # 5. Autori
        OPTIONAL {{
            ?creation lrmoo:R17_created ?expr ;
                      crm:P14_carried_out_by ?auth .
            ?auth rdfs:label ?authorName .
        }}
        OPTIONAL {{
            ?srcCreation lrmoo:R17_created ?srcExpr ;
                         crm:P14_carried_out_by ?srcAuth .
            ?srcAuth rdfs:label ?srcAuthorName .
        }}
    }}
    """


    result = execute_sparql_query(query)

    if not result['success']:
        return render_template('anagrafia.html', data=None,
                               error=f"Errore di connessione a GraphDB: {result.get('error')}")

    bindings = result['data']['results']['bindings']
    if not bindings:
        return render_template('anagrafia.html', data=None,
                               error="Nessun dato di allineamento trovato per questa espressione.")

    b = bindings[0]
    source_text = b['sourceText']['value']
    target_text = b['targetText']['value']
    expr_title = b['exprTitle']['value']
    source_title = b.get('sourceTitle', {}).get('value', 'Ipotesto')

    src_display = [t for t in source_text.split() if _STRIP_PUNCT.sub('', t)]
    tgt_display = [t for t in target_text.split() if _STRIP_PUNCT.sub('', t)]
    
    src_match_keys = _get_tokens(source_text)
    tgt_match_keys = _get_tokens(target_text)

    src_pos_map = defaultdict(list)
    for i, tok in enumerate(src_match_keys):
        if tok:
            src_pos_map[tok].append(i)

    edges = []
    used_src_indices = set()

    for j, tok in enumerate(tgt_match_keys):
        if not tok:
            continue

        positions = src_pos_map.get(tok, [])
        next_tgt  = tgt_match_keys[j+1] if j+1 < len(tgt_match_keys) else None
        best_match = None

        for p in positions:
            if p in used_src_indices:
                continue
            next_src = src_match_keys[p+1] if p+1 < len(src_match_keys) else None
            if next_src == next_tgt:
                best_match = p
                break

        if best_match is None:
            for p in positions:
                if p not in used_src_indices:
                    best_match = p
                    break

        if best_match is not None:
            edges.append({'src': best_match, 'tgt': j, 'token': tok})
            used_src_indices.add(best_match)

    matched = len(edges)
    actual_words_tgt = sum(1 for t in tgt_match_keys if t)
    unmatched_tgt = actual_words_tgt - matched
    moved = sum(1 for e in edges if e['src'] != e['tgt'])

    viz_data = {
        'author': b.get('authorName', {}).get('value', 'Autore Ignoto'),
        'author_link': b.get('authorLink', {}).get('value', '#'),
        'src_author': b.get('srcAuthorName', {}).get('value', 'Autore Ignoto'),
        'src_author_link': b.get('srcAuthorLink', {}).get('value', '#'),
        'expr_title': expr_title,
        'expr_uri': uri,
        'source_title': source_title,
        'source_tokens': src_display,
        'target_tokens': tgt_display,
        'edges': edges,
        'stats': {
            'src_count': len(src_display),
            'tgt_count': len(tgt_display),
            'matched': matched,
            'unmatched_tgt': len(tgt_display) - matched,
            'moved': sum(1 for e in edges if e['src'] != e['tgt']),
        }
    }

    return render_template('anagrafia.html', data=viz_data, error=None)


if __name__ == '__main__':
    app.run(debug=True, port=5001)