const FILTER_IDS = [
    'filterAuthor',
    'filterGenre',
    'filterConstraintType',
    'filterOrigin',
    'filterOperation',
    'filterUnit',
];

function isVisible(el) {
    return el.style.display !== 'none';
}

/**
 * Espande o richiude un contenitore .collapse aggiornando l'aria-expanded
 * del bottone di disclosure che lo comanda.
 */
function setCollapsed(collapseDiv, toggle, expanded) {
    if (collapseDiv) collapseDiv.classList.toggle('show', expanded);
    if (toggle) toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
}

/**
 * Elementi con dati di filtro dentro `el`: normalmente i .text-row discendenti,
 * ma una plaquette monografica porta gli stessi data-* sulla propria riga, che
 * quindi va inclusa anche quando è `el` stesso (querySelectorAll non la vedrebbe).
 */
function dataItemsIn(el) {
    const items = Array.from(el.querySelectorAll('[data-author]'));
    if (el.matches('[data-author]')) items.unshift(el);
    return items;
}

function applyFilters() {
    const authorVal         = document.getElementById('filterAuthor').value.toLowerCase();
    const genreVal          = document.getElementById('filterGenre').value.toLowerCase();
    const constraintTypeVal = document.getElementById('filterConstraintType').value.toLowerCase();
    const originVal         = document.getElementById('filterOrigin').value.toLowerCase();
    const operationVal      = document.getElementById('filterOperation').value.toLowerCase();
    const unitVal           = document.getElementById('filterUnit').value.toLowerCase();

    const anyFilter = FILTER_IDS.some(id => document.getElementById(id).value !== '');

    document.querySelectorAll('[data-author]').forEach(item => {
        const matchesAuthor = !authorVal || item.dataset.author.toLowerCase().includes(authorVal);
        const matchesGenre  = !genreVal  || item.dataset.type.toLowerCase() === genreVal;

        const constraintTypes = item.dataset.constraintType
            ? item.dataset.constraintType.toLowerCase().split(',').map(s => s.trim())
            : [];
        const origins = item.dataset.origins
            ? item.dataset.origins.toLowerCase().split(',').map(o => o.trim())
            : [];
        const operations = item.dataset.operations
            ? item.dataset.operations.toLowerCase().split(',').map(s => s.trim())
            : [];
        const units = item.dataset.units
            ? item.dataset.units.toLowerCase().split(',').map(s => s.trim())
            : [];

        const matchesConstraintType = !constraintTypeVal || constraintTypes.some(t => t === constraintTypeVal);
        const matchesOrigin         = !originVal         || origins.some(o => o === originVal);
        const matchesOperation      = !operationVal      || operations.some(o => o === operationVal);
        const matchesUnit           = !unitVal           || units.some(u => u === unitVal);

        item.style.display = (matchesAuthor && matchesGenre && matchesConstraintType && matchesOrigin && matchesOperation && matchesUnit) ? '' : 'none';
    });

    // Livello intermedio: le plaquette. Nasconde le righe rimaste vuote e aggiorna
    // il conteggio dei testi visibili accanto al titolo (le monografiche non ne hanno).
    document.querySelectorAll('.plaquette-row').forEach(block => {
        const items   = dataItemsIn(block);
        const visible = items.filter(isVisible);

        block.style.display = visible.length ? '' : 'none';

        const counter = block.querySelector('.disclosure-count');
        if (counter) {
            const total = Number(counter.dataset.total);
            const noun  = total === 1 ? 'testo' : 'testi';
            counter.textContent = anyFilter
                ? `${visible.length} di ${total} ${noun}`
                : `${total} ${noun}`;
        }

        setCollapsed(block.querySelector('.disclosure-panel'),
                     block.querySelector('.disclosure-toggle'),
                     anyFilter && visible.length > 0);
    });

    // Livello esterno: i volumi.
    document.querySelectorAll('.volume-row').forEach(block => {
        const hasVisibleItem = Array.from(block.querySelectorAll('[data-author]')).some(isVisible);

        block.style.display = hasVisibleItem ? '' : 'none';

        setCollapsed(block.querySelector('.disclosure-panel'),
                     block.querySelector('.disclosure-toggle'),
                     anyFilter && hasVisibleItem);
    });
}

function resetFilters() {
    FILTER_IDS.forEach(id => { document.getElementById(id).value = ''; });
    applyFilters();
}
