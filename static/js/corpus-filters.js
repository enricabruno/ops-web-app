function applyFilters() {
    const authorVal         = document.getElementById('filterAuthor').value.toLowerCase();
    const genreVal          = document.getElementById('filterGenre').value.toLowerCase();
    const constraintTypeVal = document.getElementById('filterConstraintType').value.toLowerCase();
    const originVal         = document.getElementById('filterOrigin').value.toLowerCase();
    const operationVal      = document.getElementById('filterOperation').value.toLowerCase();
    const unitVal           = document.getElementById('filterUnit').value.toLowerCase();

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
}

function resetFilters() {
    document.getElementById('filterAuthor').value         = '';
    document.getElementById('filterGenre').value          = '';
    document.getElementById('filterConstraintType').value = '';
    document.getElementById('filterOrigin').value         = '';
    document.getElementById('filterOperation').value      = '';
    document.getElementById('filterUnit').value           = '';
    applyFilters();
}
