// ── Namespace → prefix map ──────────────────────────────────────────────────
const NS_MAP = [
  ['https://w3id.org/desmos/', 'desmos:'],
  ['https://w3id.org/desmos/oplepiana/',     'base:'],
  ['http://iflastandards.info/ns/lrm/lrmoo/',  'lrmoo:'],
  ['http://www.cidoc-crm.org/cidoc-crm/',       'crm:'],
  ['http://purl.org/dc/terms/',                 'dcterms:'],
  ['http://www.w3.org/2004/02/skos/core#',      'skos:'],
  ['http://www.w3.org/2000/01/rdf-schema#',     'rdfs:'],
  ['http://www.w3.org/1999/02/22-rdf-syntax-ns#', 'rdf:'],
  ['https://w3id.org/lso/intro/beta202506#',    'intro:'],
  ['http://www.w3.org/2002/07/owl#',            'owl:'],
  ['http://www.w3.org/2001/XMLSchema#',         'xsd:'],
];

const DEFAULT_CONTENT =
`PREFIX desmos: <https://w3id.org/desmos/>
PREFIX lrmoo:  <http://iflastandards.info/ns/lrm/lrmoo/>
PREFIX crm:    <http://www.cidoc-crm.org/cidoc-crm/>
PREFIX intro:  <https://w3id.org/lso/intro/beta202506#>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX dcterms:    <http://purl.org/dc/terms/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?constraint ?label
WHERE {
  ?constraint a desmos:FormlaConstraint ;
              skos:prefLabel ?label .
  FILTER(lang(?label) = "it")
}
ORDER BY ?label`;

// ── Template Queries ────────────────────────────────────────────────────────
const TEMPLATES = {
  expressions:
`PREFIX lrmoo:  <http://iflastandards.info/ns/lrm/lrmoo/>
PREFIX crm:    <http://www.cidoc-crm.org/cidoc-crm/>
PREFIX dcterms:    <http://purl.org/dc/terms/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?expressionTitle ?authorName
WHERE {
  ?expression a lrmoo:F2_Expression ;
              dcterms:title ?expressionTitle .
  ?creation lrmoo:R17_created ?expression ;
            crm:P14_carried_out_by ?author .
  ?author rdfs:label ?authorName .
}
ORDER BY ?authorName ?expressionTitle`,

  constraints:
`PREFIX desmos: <https://w3id.org/desmos/>
PREFIX lrmoo:  <http://iflastandards.info/ns/lrm/lrmoo/>
PREFIX crm:    <http://www.cidoc-crm.org/cidoc-crm/>
PREFIX dcterms:    <http://purl.org/dc/terms/>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?scopeLabel ?constraintLabel ?expressionTitle
WHERE {
  ?creation lrmoo:R17_created ?expression ;
            desmos:usedConstraint ?constraint .
  ?expression dcterms:title ?expressionTitle .
  OPTIONAL {
    ?constraint skos:prefLabel ?constraintLabel .
    FILTER(lang(?constraintLabel) = "it")
  }
  OPTIONAL {
    ?constraint desmos:constraintScope ?scope .
    ?scope skos:prefLabel ?scopeLabel .
    FILTER(lang(?scopeLabel) = "it")
  }
}
ORDER BY ?scopeLabel ?constraintLabel`,

  derivatives:
`PREFIX lrmoo:  <http://iflastandards.info/ns/lrm/lrmoo/>
PREFIX crm:    <http://www.cidoc-crm.org/cidoc-crm/>
PREFIX dcterms:    <http://purl.org/dc/terms/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?derivedTitle ?sourceTitle ?authorName
WHERE {
  ?derived lrmoo:R76_is_derivative_of ?source .
  ?derived dcterms:title ?derivedTitle .
  ?source  dcterms:title ?sourceTitle .
  OPTIONAL {
    ?creation lrmoo:R17_created ?derived ;
              crm:P14_carried_out_by ?author .
    ?author rdfs:label ?authorName .
  }
}
ORDER BY ?derivedTitle`,
};

// ── CodeMirror editor init ───────────────────────────────────────────────────
const editor = CodeMirror(document.getElementById('sparql-editor-host'), {
  mode: 'application/sparql-query',
  theme: 'neo',
  lineNumbers: true,
  lineWrapping: false,
  tabSize: 2,
  indentWithTabs: false,
  autofocus: true,
  matchBrackets: true,
  extraKeys: {
    'Ctrl-Enter': executeQuery,
    'Cmd-Enter':  executeQuery,
  },
});

// ── UI helpers ───────────────────────────────────────────────────────────────
function resetEditor() {
  editor.setValue(DEFAULT_CONTENT);
  editor.focus();
}

function loadTemplate(name) {
  if (TEMPLATES[name]) {
    editor.setValue(TEMPLATES[name]);
    document.getElementById('results-section').classList.add('d-none');
    document.getElementById('results-count-badge').textContent = '';
    editor.focus();
  }
}

function clearEditor() {
  document.getElementById('results-section').classList.add('d-none');
  document.getElementById('query-results').innerHTML = '';
  document.getElementById('results-count-badge').textContent = '';
  resetEditor();
}

// ── Query execution ─────────────────────────────────────────────────────────
async function executeQuery() {
  const query = editor.getValue().trim();
  const resultsSection = document.getElementById('results-section');
  const resultsDiv     = document.getElementById('query-results');

  if (!query) {
    resultsSection.classList.remove('d-none');
    resultsDiv.innerHTML = '<div class="alert alert-warning mb-0">Inserisci una query SPARQL valida prima di procedere.</div>';
    return;
  }

  setLoading(true);
  resultsSection.classList.remove('d-none');
  resultsDiv.innerHTML = `
    <div class="text-center py-4 text-muted">
      <span class="spinner-border spinner-border-sm me-2"></span>Interrogazione del Knowledge Graph in corso…
    </div>`;
  setBadge('', 'bg-secondary');

  try {
    const response = await fetch('/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      displayError(data.error || `Errore HTTP ${response.status}`);
    } else {
      displayResults(data.data);
    }
  } catch (err) {
    displayError('Impossibile raggiungere il server. Verificare che GraphDB sia avviato.\n\n' + err.message);
  } finally {
    setLoading(false);
  }
}

function setLoading(on) {
  document.getElementById('btn-text').classList.toggle('d-none', on);
  document.getElementById('btn-spinner').classList.toggle('d-none', !on);
  document.getElementById('execute-btn').disabled = on;
}

function setBadge(text, cls = 'bg-secondary') {
  const b = document.getElementById('results-count-badge');
  b.textContent = text;
  b.className = `badge ${cls}`;
}

// ── Result rendering ────────────────────────────────────────────────────────
function displayResults(data) {
  const resultsDiv = document.getElementById('query-results');

  // ASK query response
  if (data.boolean !== undefined) {
    const val = data.boolean;
    setBadge('ASK', val ? 'bg-success' : 'bg-warning text-dark');
    resultsDiv.innerHTML = `
      <div class="alert ${val ? 'alert-success' : 'alert-warning'} mb-0">
        Risultato ASK: <strong>${val ? 'TRUE' : 'FALSE'}</strong>
      </div>`;
    return;
  }

  const bindings  = data.results?.bindings ?? [];
  const variables = data.head?.vars ?? [];

  if (bindings.length === 0) {
    setBadge('0 risultati', 'bg-warning text-dark');
    resultsDiv.innerHTML = '<div class="alert alert-warning mb-0">La query è valida, ma non ha restituito risultati nel repository.</div>';
    return;
  }

  setBadge(`${bindings.length} risultat${bindings.length === 1 ? 'o' : 'i'}`, 'bg-success');

  let rows = '';
  for (const binding of bindings) {
    rows += '<tr>' + variables.map(v => renderCell(binding[v])).join('') + '</tr>';
  }

  resultsDiv.innerHTML = `
    <div class="results-table-wrap">
      <table class="table table-hover table-bordered table-sm align-middle bg-white mb-0">
        <thead class="table-light">
          <tr>${variables.map(v => `<th class="text-primary small fw-semibold">${escapeHtml(v)}</th>`).join('')}</tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function renderCell(item) {
  if (!item) return '<td class="text-muted fst-italic">—</td>';

  if (item.type === 'uri') {
    const short = shortenUri(item.value);
    if (short) {
      return `<td><span class="uri-badge" title="${escapeHtml(item.value)}">${escapeHtml(short)}</span></td>`;
    }
    const display = item.value.length > 70 ? item.value.slice(0, 67) + '…' : item.value;
    return `<td><a href="${escapeHtml(item.value)}" target="_blank" rel="noopener"
                   class="text-break small" title="${escapeHtml(item.value)}">${escapeHtml(display)}</a></td>`;
  }

  if (item.type === 'literal' || item.type === 'typed-literal') {
    const dt   = item.datatype || '';
    const lang = item['xml:lang'] || '';
    let inner  = escapeHtml(item.value);

    if (lang) {
      inner += `<span class="lang-tag">[${escapeHtml(lang)}]</span>`;
    } else if (dt.includes('date')) {
      inner = `<span class="text-secondary">${inner}</span>`;
    } else if (/integer|decimal|float|double/.test(dt)) {
      inner = `<span class="text-info fw-semibold">${inner}</span>`;
    } else if (dt.includes('boolean')) {
      inner = `<span class="badge ${item.value === 'true' ? 'bg-success' : 'bg-danger'}">${inner}</span>`;
    }
    return `<td>${inner}</td>`;
  }

  // blank node
  return `<td class="text-muted small fst-italic" title="blank node">${escapeHtml(item.value)}</td>`;
}

function shortenUri(uri) {
  for (const [ns, prefix] of NS_MAP) {
    if (uri.startsWith(ns)) return prefix + uri.slice(ns.length);
  }
  return null;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Error rendering ─────────────────────────────────────────────────────────
function displayError(msg) {
  const resultsDiv = document.getElementById('query-results');

  let title = 'Errore SPARQL';
  if (/MalformedQuery|Parse error|Lexical error|Syntax error/i.test(msg)) {
    title = 'Errore di sintassi SPARQL';
  } else if (/Connection refused|raggiungere il server|ECONNREFUSED/i.test(msg)) {
    title = 'Errore di connessione a GraphDB';
  } else if (/HTTP [45]\d\d/.test(msg)) {
    title = 'Errore HTTP dal server';
  }

  setBadge('Errore', 'bg-danger');
  resultsDiv.innerHTML = `
    <div class="alert alert-danger mb-0">
      <strong><i class="fa fa-exclamation-triangle me-2"></i>${escapeHtml(title)}</strong>
      <pre class="error-pre mt-2">${escapeHtml(msg)}</pre>
    </div>`;
}

// ── Init ─────────────────────────────────────────────────────────────────────
resetEditor();
