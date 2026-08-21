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
 * dell'intestazione che lo comanda.
 */
function setCollapsed(collapseDiv, heading, expanded) {
    if (collapseDiv) collapseDiv.classList.toggle('show', expanded);
    if (heading) heading.setAttribute('aria-expanded', expanded ? 'true' : 'false');
}

function applyFilters() {
    const authorVal         = document.getElementById('filterAuthor').value.toLowerCase();
    const genreVal          = document.getElementById('filterGenre').value.toLowerCase();
    const constraintTypeVal = document.getElementById('filterConstraintType').value.toLowerCase();
    const originVal         = document.getElementById('filterOrigin').value.toLowerCase();
    const operationVal      = document.getElementById('filterOperation').value.toLowerCase();
    const unitVal           = document.getElementById('filterUnit').value.toLowerCase();

    const anyFilter = FILTER_IDS.some(id => document.getElementById(id).value !== '');

    document.querySelectorAll('.expression-item').forEach(item => {
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

    // Livello intermedio: le plaquette singole. Nasconde le intestazioni rimaste vuote
    // e aggiorna il conteggio dei testi visibili accanto al titolo.
    document.querySelectorAll('.plaquette-block').forEach(block => {
        const items   = Array.from(block.querySelectorAll('.expression-item'));
        const visible = items.filter(isVisible);

        block.style.display = visible.length ? '' : 'none';

        const counter = block.querySelector('.plaquette-count');
        if (counter) {
            const total = Number(counter.dataset.total);
            const noun  = total === 1 ? 'testo' : 'testi';
            counter.textContent = anyFilter
                ? `${visible.length} di ${total} ${noun}`
                : `${total} ${noun}`;
        }

        setCollapsed(block.querySelector('.plaquette-collapse'),
                     block.querySelector('.plaquette-heading'),
                     anyFilter && visible.length > 0);
    });

    // Livello esterno: i volumi (e il gruppo "Plaquette singole").
    document.querySelectorAll('.volume-block').forEach(block => {
        const hasVisibleItem = Array.from(block.querySelectorAll('.expression-item')).some(isVisible);

        block.style.display = hasVisibleItem ? '' : 'none';

        setCollapsed(block.querySelector('.volume-collapse'),
                     block.querySelector('.volume-heading'),
                     anyFilter && hasVisibleItem);
    });
}

function resetFilters() {
    FILTER_IDS.forEach(id => { document.getElementById(id).value = ''; });
    applyFilters();
}
