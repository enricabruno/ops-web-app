async function runVisualQuery() {
    const type = document.getElementById('selectType').value;
    const constraint = document.getElementById('selectConstraint').value;

    const resultsSection = document.getElementById('visual-results-section');
    const resultsBody = document.getElementById('visual-results-body');

    resultsSection.classList.remove('d-none');
    resultsBody.innerHTML = '<div class="p-5 text-center text-muted">Ricerca in corso...</div>';

    // Generazione dinamica della query in base alle scelte
    let sparql = `
        PREFIX desmos: <https://w3id.org/desmos/>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dct: <http://purl.org/dc/terms/>
        PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
    `;

    if (type === 'opere') {
        sparql += `
            SELECT DISTINCT ?Risultato ?Etichetta WHERE {
                ?Risultato a <http://iflastandards.info/ns/lrm/lrmoo/F2_Expression> ;
                          dct:title ?Etichetta .
                ?creation <http://iflastandards.info/ns/lrm/lrmoo/R17_created> ?Risultato ;
                          desmos:usedConstraint ?c .
                ?c skos:prefLabel ?clabel .
                ${constraint !== 'all' ? `FILTER(?clabel = "${constraint}"@it)` : ''}
            } LIMIT 50
        `;
    } else {
        sparql += `
            SELECT DISTINCT ?Risultato (SAMPLE(?name) AS ?Etichetta) WHERE {
                ?Risultato a crm:E39_Actor ; rdfs:label ?name .
                ?creation crm:P14_carried_out_by ?Risultato ;
                          desmos:usedConstraint ?c .
                ?c skos:prefLabel ?clabel .
                ${constraint !== 'all' ? `FILTER(?clabel = "${constraint}"@it)` : ''}
            } GROUP BY ?Risultato LIMIT 50
        `;
    }

    try {
        const response = await fetch('/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: sparql })
        });
        const data = await response.json();

        if (data.success && data.data.results.bindings.length > 0) {
            let html = '<ul class="list-group list-group-flush">';
            data.data.results.bindings.forEach(row => {
                html += `<li class="list-group-item p-3 d-flex justify-content-between align-items-center">
                            <span class="fw-semibold">${row.Etichetta.value}</span>
                            <code class="x-small text-muted">${row.Risultato.value}</code>
                         </li>`;
            });
            html += '</ul>';
            resultsBody.innerHTML = html;
        } else {
            resultsBody.innerHTML = '<div class="p-5 text-center">Nessun risultato trovato per questa combinazione.</div>';
        }
    } catch (e) {
        resultsBody.innerHTML = `<div class="p-5 text-danger">Errore: ${e.message}</div>`;
    }
}
