from flask import Flask, render_template, request, jsonify
from SPARQLWrapper import SPARQLWrapper, JSON
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
          ?_parentExpr lrmoo:R4_is_embodied_in ?_parentF3 .
          ?_parentF3 dct:title ?_parentPlaquetteTitle .
        }
      }
      OPTIONAL {
        # Stop at the immediate F3_Manifestation — do NOT traverse crm:P148i_is_component_of.
        ?expression lrmoo:R4_is_embodied_in ?_directMf .
        ?_directMf dct:title ?_directMfTitle .
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
            }
            expressions.append(exp_data)
            facets['authors'].add(b['authors']['value'])
            if w_type:
                facets['work_types'].add(w_type)

    # Merge formal and semantic units into a single dropdown facet
    facets['units'] = sorted(list(facets.pop('formal_units') | facets.pop('semantic_units')))
    facets = {k: sorted(list(v)) if isinstance(v, set) else v for k, v in facets.items()}

    print(f"Total expressions processed: {len(expressions)}")
    print(f"Facets: {facets}\n")

    error_message = None if result['success'] else result.get('error', 'Unknown error connecting to GraphDB')

    return render_template('corpus.html', expressions=expressions, facets=facets, error=error_message)

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

@app.route('/explain/<label>')
def explain(label):
    query = f"""
    PREFIX desmos: <https://w3id.org/desmos/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?definition ?example ?originLabel ?type
           (GROUP_CONCAT(DISTINCT CONCAT(STR(?operationLabel), "##", COALESCE(STR(?opMatch), "")); separator="||") AS ?operations)
           (GROUP_CONCAT(DISTINCT CONCAT(STR(?formalUnitLabel), "##", COALESCE(STR(?fuMatch), "")); separator="||") AS ?formalUnits)
           (GROUP_CONCAT(DISTINCT CONCAT(STR(?semanticUnitLabel), "##", COALESCE(STR(?suMatch), "")); separator="||") AS ?semanticUnits)
    WHERE {{
        ?constraint a skos:Concept ;
            skos:prefLabel "{label}"@it ;
            rdf:type ?type .
        FILTER(?type IN (desmos:FormalConstraint, desmos:SemanticConstraint))

        OPTIONAL {{ ?constraint skos:definition ?definition . FILTER(lang(?definition) = "it") }}
        OPTIONAL {{ ?constraint skos:example ?example . FILTER(lang(?example) = "it") }}

        OPTIONAL {{ ?constraint desmos:constraintScope ?scope . ?scope skos:prefLabel ?scopeLabel . FILTER(lang(?scopeLabel) = "it") }}
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
    GROUP BY ?definition ?example ?originLabel ?type
    """
    result = execute_sparql_query(query)

    def _parse_lod_items(raw):
        items = []
        for item in [v for v in raw.split('||') if v]:
            parts = item.split('##', 1)
            label = parts[0]
            link = parts[1] if len(parts) > 1 and parts[1] else None
            items.append({'label': label, 'link': link})
        return items

    info = {'label': label, 'operations': [], 'formal_units': [], 'semantic_units': []}
    if result['success'] and result['data']['results']['bindings']:
        row = result['data']['results']['bindings'][0]

        full_type_uri = row.get('type', {}).get('value', '')
        class_name = full_type_uri.split('/')[-1]
        info['definition'] = row.get('definition', {}).get('value', 'Definizione non disponibile.')
        info['example'] = row.get('example', {}).get('value', None)
        info['class_type'] = class_name
        info['display_type'] = "Formale" if "Formal" in class_name else "Semantico"
        info['origin'] = row.get('originLabel', {}).get('value', 'N/D')

        info['operations'] = _parse_lod_items(row.get('operations', {}).get('value', ''))
        info['formal_units'] = _parse_lod_items(row.get('formalUnits', {}).get('value', ''))
        info['semantic_units'] = _parse_lod_items(row.get('semanticUnits', {}).get('value', ''))

    return render_template('explain.html', info=info)

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

    SELECT ?title ?authorName ?authorLink ?year ?workType
           (SAMPLE(?_manifTitle) AS ?manifTitle)
           (SAMPLE(STR(?_parentExpr)) AS ?parentExprStr)
           (SAMPLE(?hasAlignment) AS ?alignment)
           (GROUP_CONCAT(DISTINCT CONCAT(STR(?constraint), "##", STR(?constraintLabel), "##", STR(?scheme)); separator="||") AS ?constraintData)
           (GROUP_CONCAT(DISTINCT ?fragData; separator="|||") AS ?fragmentsConcat)
           (GROUP_CONCAT(DISTINCT ?exactMatch; separator="||") AS ?exactMatches)
           (GROUP_CONCAT(DISTINCT ?seeAlso; separator="||") AS ?seeAlsos)
           (GROUP_CONCAT(DISTINCT CONCAT(STR(?srcExpr), "##", STR(?srcTitle)); separator="||") AS ?derivedFrom)
    WHERE {
        BIND(<%s> AS ?uri)

        ?uri dct:title ?title .
        OPTIONAL { ?uri crm:P2_has_type ?workType }
        OPTIONAL { ?uri owl:sameAs ?sameAs }
        OPTIONAL { ?uri rdfs:seeAlso ?seeAlso }

        ?creation lrmoo:R17_created ?uri ;
                  crm:P14_carried_out_by ?author .
        ?author rdfs:label ?authorName .
        OPTIONAL { ?author owl:sameAS ?authorLink }
        
        OPTIONAL { ?creation dct:created ?year }

        # 1. Recupero Manifestazione: property path cattura R4_is_embodied_in e ^R4_embodies
        OPTIONAL {
            ?uri (lrmoo:R4_is_embodied_in | ^lrmoo:R4_embodies) ?_manifNode .
            ?_manifNode dct:title ?_manifTitleRaw .
            BIND(STR(?_manifTitleRaw) AS ?_manifTitle)
        }
        # 1b. Verifica se l'espressione è componente di un'espressione padre
        OPTIONAL { ?uri crm:P148i_is_component_of ?_parentExpr }

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
            BIND("direct" AS ?fSource)

            OPTIONAL {
                ?uri lrmoo:R4i_is_embodied_in ?plaquette .
                ?plaquette schema:pagination ?pageVal .
                OPTIONAL {
                    ?plaquette crm:P148i_is_component_of ?mainVolume .
                    ?mainVolume dct:title ?volTitle ;
                                dct:issued ?volYear .
                }
            }

            BIND(COALESCE(STR(?volTitle), "Biblioteca Oplepiana") AS ?finalFullTitle)
            BIND(COALESCE(STR(?volYear), "") AS ?finalYear)
            BIND(COALESCE(STR(?pageVal), "") AS ?finalPage)
            BIND(CONCAT(STR(?fragText), "##", ?finalFullTitle, "##", ?finalYear, "##", ?finalPage, "##", STR(?fSource)) AS ?fragData)
        }

        OPTIONAL { ?uri lrmoo:R76_is_derivative_of ?srcExpr . ?srcExpr dct:title ?srcTitle . }

        # 4. Flag allineamento testuale (INTRO TextPassage)
        OPTIONAL {
            ?targetPassage a intro:INT21_TextPassage ;
                           intro:R30i_isTextPassageOf ?uri .
            BIND("true" AS ?hasAlignment)
        }
    }
    GROUP BY ?title ?authorName ?authorLink ?year ?workType ?hasAlignment
    """ % uri

    result = execute_sparql_query(query)
    if not result['success'] or not result['data']['results']['bindings']:
        return render_template('expression.html', expr=None, error="Dati non trovati.")

    b = result['data']['results']['bindings'][0]
    
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

    fragments = []
    seen_frag_texts = set()
    raw_frags = b.get('fragmentsConcat', {}).get('value', '')
    if raw_frags:
        for entry in raw_frags.split('|||'):
            entry = entry.strip()
            if not entry:
                continue
            # 5-part concat: text ## full_title ## year ## page ## source_type
            parts = entry.split('##', 4)
            frag_text = parts[0].strip()
            if not frag_text or frag_text in seen_frag_texts:
                continue
            seen_frag_texts.add(frag_text)
            fragments.append({
                'text':      frag_text,
                'man_title': parts[1].strip() if len(parts) > 1 else '',
                'issued':    parts[2].strip() if len(parts) > 2 else '',
                'page':      parts[3].strip() if len(parts) > 3 else '',
                'source':    parts[4].strip() if len(parts) > 4 else 'direct',
            })
    
    exact_matches = [m.strip() for m in b.get('exactMatches', {}).get('value', '').split('||') if m.strip()]
    see_alsos = [s.strip() for s in b.get('seeAlsos', {}).get('value', '').split('||') if s.strip()]

    manif_title = b.get('manifTitle', {}).get('value', '')
    parent_expr_str = b.get('parentExprStr', {}).get('value', '')
    manif_label = 'In:' if parent_expr_str else 'Plaquette:'

    expr = {
        'uri': uri,
        'title': b['title']['value'],
        'author': b['authorName']['value'],
        'author_link': b.get('authorLink', {}).get('value') or None,
        'year': b.get('year', {}).get('value', ''),
        'total_constraints': len(seen_uris),
        'constraints_formali': constraints_formali,
        'constraints_semantiche': constraints_semantiche,
        'fragments': fragments,
        'sources': [{'uri': x.split('##')[0], 'title': x.split('##')[1]} for x in b.get('derivedFrom', {}).get('value', '').split('||') if '##' in x],
        'exact_matches': exact_matches,
        'see_alsos': see_alsos,
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