// Matrice operazione x unità: mappa tutte le costrizioni del corpus incrociando
// operazione procedurale (righe) e unità linguistica (colonne), evidenziando la
// costrizione della scheda corrente. Nessuna dipendenza esterna: l'SVG è generato
// a mano a partire da /api/constraint-matrix. Struttura a tre fasce (identità /
// matrice / risultati) a piena altezza di viewport: solo la colonna dei
// risultati scorre al suo interno.

const SVG_NS = 'http://www.w3.org/2000/svg';

const CELL_W = 51;
const CELL_H = 34;
const ROW_LABEL_W = 96;
const COL_LABEL_H = 64;
const COL_LABEL_GAP = 14; // distanza fra l'ancora dell'etichetta ruotata e il bordo superiore della griglia
const MARGIN = { top: 12, right: 8 };

// Confine fra operazioni dichiarate e riga di scarto: dopo l'ultima delle 8
// operazioni (indice 0-based 7). Confine fra unità formali e semantiche: dopo
// l'ultima delle 9 unità formali (indice 0-based 8).
const ROW_SEPARATOR_AFTER = 7;
const COL_SEPARATOR_AFTER = 8;

// Scala dimensionale GRADUATA (non continua): il range dei dati (1..28) eccede
// il range disponibile in una cella da 51px. Con lato = k*sqrt(n) la marca
// minima scenderebbe sotto i 5px, soglia sotto la quale quadrato e cerchio
// diventano indistinguibili. I cutoff seguono una progressione geometrica
// perché la distribuzione dei gruppi è a coda lunga.
const SIZE_CUTOFFS = [1, 3, 6, 12]; // classi: 1 | 2-3 | 4-6 | 7-12 | 13+
const SQUARE_SIDE = [8, 10.5, 13.5, 18, 22];
const CIRCLE_RATIO = 1.1284; // d = s * 2/sqrt(pi): cerchio di area pari al quadrato della stessa classe
const MARK_GAP = 3;

const CLASS_LABELS = { formal: 'Formale', semantic: 'Semantica', visual: 'Visuale' };

function sizeClassIndex(n) {
    let idx = 0;
    for (const cutoff of SIZE_CUTOFFS) {
        if (n > cutoff) idx += 1;
    }
    return idx;
}

function originShape(origin) {
    if (!origin) return 'diamond';
    const o = origin.toLowerCase();
    if (o.startsWith('orig')) return 'square';
    if (o.startsWith('stor')) return 'circle';
    return 'diamond';
}

let _measureCtx = null;
function measureText(text, font) {
    if (!_measureCtx) _measureCtx = document.createElement('canvas').getContext('2d');
    _measureCtx.font = font;
    return _measureCtx.measureText(text).width;
}

const ROW_LABEL_FONT = '10.5px Futura, "Century Gothic", "Trebuchet MS", sans-serif';

// Le etichette di riga troppo lunghe per ROW_LABEL_W vengono spezzate su più
// righe (greedy word-wrap) per non uscire dal bordo sinistro dell'SVG.
function wrapRowLabel(text, maxWidth) {
    if (measureText(text, ROW_LABEL_FONT) <= maxWidth) return [text];
    const words = text.split(' ');
    const lines = [];
    let current = '';
    words.forEach((word) => {
        const candidate = current ? current + ' ' + word : word;
        if (current && measureText(candidate, ROW_LABEL_FONT) > maxWidth) {
            lines.push(current);
            current = word;
        } else {
            current = candidate;
        }
    });
    if (current) lines.push(current);
    return lines;
}

function el(tag, attrs, ns) {
    const node = document.createElementNS(ns || SVG_NS, tag);
    if (attrs) {
        for (const k in attrs) node.setAttribute(k, attrs[k]);
    }
    return node;
}

async function loadData() {
    const res = await fetch('/api/constraint-matrix');
    if (!res.ok) throw new Error('Richiesta fallita: ' + res.status);
    return res.json();
}

// Legenda: solo i campioni (classe / origine / numerosità), senza bordo né
// intestazione — quelle vivono nel markup statico della colonna identità.
function buildLegend(container) {
    const classes = [
        { key: 'formal', label: 'Formale' },
        { key: 'semantic', label: 'Semantica' },
        { key: 'visual', label: 'Visuale' },
    ];
    const h1 = document.createElement('h6');
    h1.textContent = 'Classe';
    container.appendChild(h1);
    classes.forEach(c => {
        const row = document.createElement('div');
        row.className = 'constraint-matrix-legend-row';
        const sw = document.createElement('span');
        sw.className = 'constraint-matrix-legend-swatch matrix-mark--' + c.key;
        sw.style.background = `var(--matrix-${c.key})`;
        row.appendChild(sw);
        const lbl = document.createElement('span');
        lbl.textContent = c.label;
        row.appendChild(lbl);
        container.appendChild(row);
    });

    const h2 = document.createElement('h6');
    h2.textContent = 'Origine';
    container.appendChild(h2);
    [['square', 'Originale'], ['circle', 'Storica']].forEach(([shape, label]) => {
        const row = document.createElement('div');
        row.className = 'constraint-matrix-legend-row';
        const svg = el('svg', { width: 14, height: 14, viewBox: '0 0 14 14' });
        svg.classList.add('constraint-matrix-legend-swatch');
        if (shape === 'square') {
            svg.appendChild(el('rect', { x: 2, y: 2, width: 10, height: 10, fill: 'var(--color-text)' }));
        } else {
            svg.appendChild(el('circle', { cx: 7, cy: 7, r: 5.6, fill: 'var(--color-text)' }));
        }
        row.appendChild(svg);
        const lbl = document.createElement('span');
        lbl.textContent = label;
        row.appendChild(lbl);
        container.appendChild(row);
    });

    const h3 = document.createElement('h6');
    h3.textContent = 'Numero di costrizioni';
    container.appendChild(h3);
    const sizeLabels = ['1', '2–3', '4–6', '7–12', '13+'];
    sizeLabels.forEach((label, i) => {
        const row = document.createElement('div');
        row.className = 'constraint-matrix-legend-row';
        const s = SQUARE_SIDE[i];
        const box = 22;
        const svg = el('svg', { width: box, height: box, viewBox: `0 0 ${box} ${box}` });
        svg.classList.add('constraint-matrix-legend-swatch');
        svg.appendChild(el('rect', {
            x: (box - s) / 2, y: (box - s) / 2, width: s, height: s, fill: 'var(--color-text)',
        }));
        row.appendChild(svg);
        const lbl = document.createElement('span');
        lbl.textContent = label;
        row.appendChild(lbl);
        container.appendChild(row);
    });
}

function markElement(mark, cx, cy, side) {
    const shape = originShape(mark.origin);
    let node;
    if (shape === 'square') {
        node = el('rect', { x: cx - side / 2, y: cy - side / 2, width: side, height: side });
    } else if (shape === 'circle') {
        const d = side * CIRCLE_RATIO;
        node = el('circle', { cx, cy, r: d / 2 });
    } else {
        // diamond: origine non specificata nel modello
        const half = side * CIRCLE_RATIO / 2;
        node = el('polygon', {
            points: [
                `${cx},${cy - half}`,
                `${cx + half},${cy}`,
                `${cx},${cy + half}`,
                `${cx - half},${cy}`,
            ].join(' '),
        });
    }
    node.classList.add('matrix-mark', 'matrix-mark--' + mark.cls);
    node.setAttribute('tabindex', '0');
    node.setAttribute('role', 'button');
    const originLabel = mark.origin || 'origine non specificata';
    node.setAttribute('aria-label',
        `${CLASS_LABELS[mark.cls] || mark.cls}, ${originLabel}, ${mark.n} costrizion${mark.n === 1 ? 'e' : 'i'}`);
    return node;
}

function renderMatrix(containers, data, focusUri) {
    const { viz, legendSlot, resultsEl } = containers;
    viz.innerHTML = '';

    const rows = data.rows;
    const cols = data.cols;
    const gridX0 = ROW_LABEL_W;
    const gridY0 = MARGIN.top + COL_LABEL_H;
    const width = ROW_LABEL_W + cols.length * CELL_W + MARGIN.right;
    const height = MARGIN.top + COL_LABEL_H + rows.length * CELL_H;

    const svg = el('svg', {
        viewBox: `0 0 ${width} ${height}`,
        preserveAspectRatio: 'xMidYMid meet',
        role: 'img',
    });
    svg.appendChild(el('title', {}, SVG_NS)).textContent =
        'Matrice operazione per unità delle costrizioni del corpus DeSMòS';
    const desc = el('desc');
    desc.textContent = `${rows.length} operazioni (righe, inclusa la riga senza operazione) per `
        + `${cols.length} unità formali/semantiche (colonne). Ogni forma rappresenta un gruppo di costrizioni `
        + 'che condividono cella, classe e origine.';
    svg.appendChild(desc);

    // Bande di evidenziazione riga/colonna (sotto tutto il resto)
    const bandLayer = el('g');
    svg.appendChild(bandLayer);
    const rowBands = rows.map((_, r) => {
        const band = el('rect', {
            class: 'matrix-cell-band',
            x: gridX0, y: gridY0 + r * CELL_H, width: cols.length * CELL_W, height: CELL_H,
        });
        bandLayer.appendChild(band);
        return band;
    });
    const colBands = cols.map((_, c) => {
        const band = el('rect', {
            class: 'matrix-cell-band',
            x: gridX0 + c * CELL_W, y: gridY0, width: CELL_W, height: rows.length * CELL_H,
        });
        bandLayer.appendChild(band);
        return band;
    });

    // Griglia
    const gridLayer = el('g');
    svg.appendChild(gridLayer);
    for (let r = 0; r <= rows.length; r++) {
        gridLayer.appendChild(el('line', {
            x1: gridX0, x2: gridX0 + cols.length * CELL_W,
            y1: gridY0 + r * CELL_H, y2: gridY0 + r * CELL_H,
            stroke: 'var(--color-border)', 'stroke-width': 0.5,
        }));
    }
    for (let c = 0; c <= cols.length; c++) {
        gridLayer.appendChild(el('line', {
            x1: gridX0 + c * CELL_W, x2: gridX0 + c * CELL_W,
            y1: gridY0, y2: gridY0 + rows.length * CELL_H,
            stroke: 'var(--color-border)', 'stroke-width': 0.5,
        }));
    }

    // Separatori tratteggiati
    const sepY = gridY0 + (ROW_SEPARATOR_AFTER + 1) * CELL_H;
    gridLayer.appendChild(el('line', {
        class: 'matrix-separator', x1: gridX0, x2: gridX0 + cols.length * CELL_W, y1: sepY, y2: sepY,
    }));
    const sepX = gridX0 + (COL_SEPARATOR_AFTER + 1) * CELL_W;
    gridLayer.appendChild(el('line', {
        class: 'matrix-separator', x1: sepX, x2: sepX, y1: gridY0, y2: gridY0 + rows.length * CELL_H,
    }));

    // Tooltip (fuori dall'SVG)
    const tooltip = document.createElement('div');
    tooltip.className = 'constraint-matrix-tooltip';
    tooltip.style.display = 'none';
    tooltip.setAttribute('role', 'tooltip');
    document.body.appendChild(tooltip);

    function showTooltip(target, label, definition) {
        tooltip.innerHTML = '';
        const strong = document.createElement('strong');
        strong.textContent = label;
        tooltip.appendChild(strong);
        if (definition) {
            const p = document.createElement('span');
            p.textContent = definition;
            tooltip.appendChild(p);
        }
        const rect = target.getBoundingClientRect();
        tooltip.style.display = 'block';
        tooltip.style.left = Math.max(8, rect.left) + 'px';
        tooltip.style.top = (rect.bottom + 6) + 'px';
    }
    function hideTooltip() {
        tooltip.style.display = 'none';
    }
    document.addEventListener('click', (ev) => {
        if (!tooltip.contains(ev.target) && !ev.target.classList.contains('matrix-axis-label')) {
            hideTooltip();
            rowBands.forEach(b => b.classList.remove('matrix-cell-band--active'));
            colBands.forEach(b => b.classList.remove('matrix-cell-band--active'));
        }
    });

    // Etichette di riga
    const labelLayer = el('g');
    svg.appendChild(labelLayer);
    rows.forEach((row, r) => {
        const y = gridY0 + r * CELL_H + CELL_H / 2;
        const lines = wrapRowLabel(row.label, ROW_LABEL_W - 12);
        const labelClass = 'matrix-axis-label' + (row.kind === 'no_operation' ? ' matrix-axis-label--muted' : '');
        const text = el('text', {
            class: labelClass, x: ROW_LABEL_W - 8, y,
            'text-anchor': 'end', tabindex: '0',
        });
        if (lines.length === 1) {
            text.setAttribute('dominant-baseline', 'middle');
            text.textContent = lines[0];
        } else {
            const lineHeight = 12;
            const startDy = -((lines.length - 1) * lineHeight) / 2 + 3.5;
            lines.forEach((line, i) => {
                const tspan = el('tspan', { x: ROW_LABEL_W - 8, dy: i === 0 ? startDy : lineHeight });
                tspan.textContent = line;
                text.appendChild(tspan);
            });
        }
        const activate = (ev) => {
            ev.stopPropagation();
            showTooltip(text, row.label, row.definition);
            rowBands.forEach((b, i) => b.classList.toggle('matrix-cell-band--active', i === r));
            colBands.forEach(b => b.classList.remove('matrix-cell-band--active'));
        };
        text.addEventListener('mouseenter', activate);
        text.addEventListener('mouseleave', () => { rowBands[r].classList.remove('matrix-cell-band--active'); hideTooltip(); });
        text.addEventListener('click', activate);
        text.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') activate(ev); });
        labelLayer.appendChild(text);
    });

    // Etichette di colonna (ruotate)
    cols.forEach((col, c) => {
        const x = gridX0 + c * CELL_W + CELL_W / 2;
        const y = gridY0 - COL_LABEL_GAP;
        const text = el('text', {
            class: 'matrix-axis-label', x, y,
            'text-anchor': 'end', transform: `rotate(-45 ${x} ${y})`, tabindex: '0',
        });
        text.textContent = col.short || col.label;
        const activate = (ev) => {
            ev.stopPropagation();
            showTooltip(text, col.label, col.definition);
            colBands.forEach((b, i) => b.classList.toggle('matrix-cell-band--active', i === c));
            rowBands.forEach(b => b.classList.remove('matrix-cell-band--active'));
        };
        text.addEventListener('mouseenter', activate);
        text.addEventListener('mouseleave', () => { colBands[c].classList.remove('matrix-cell-band--active'); hideTooltip(); });
        text.addEventListener('click', activate);
        text.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') activate(ev); });
        labelLayer.appendChild(text);
    });

    // Marche, raggruppate per cella
    const markLayer = el('g');
    svg.appendChild(markLayer);
    const byCell = new Map();
    data.marks.forEach((mark, i) => {
        const key = mark.r + ':' + mark.c;
        if (!byCell.has(key)) byCell.set(key, []);
        byCell.get(key).push({ ...mark, index: i });
    });

    const focusIndices = new Set((focusUri && data.index[focusUri]) || []);

    byCell.forEach((groups) => {
        groups.sort((a, b) => b.n - a.n);
        const sized = groups.map(g => ({ mark: g, side: SQUARE_SIDE[sizeClassIndex(g.n)] }));
        const totalW = sized.reduce((s, g) => s + g.side, 0) + MARK_GAP * (sized.length - 1);
        const cx = gridX0 + sized[0].mark.c * CELL_W + CELL_W / 2;
        const cy = gridY0 + sized[0].mark.r * CELL_H + CELL_H / 2;
        let x = cx - totalW / 2;
        sized.forEach(({ mark, side }) => {
            const shapeCx = x + side / 2;
            const node = markElement(mark, shapeCx, cy, side);
            if (focusIndices.size) {
                node.classList.add(focusIndices.has(mark.index) ? 'matrix-mark--focus' : 'matrix-mark--dim');
            }
            node.addEventListener('click', () => selectMark(mark));
            node.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') selectMark(mark); });
            markLayer.appendChild(node);
            x += side + MARK_GAP;
        });
    });

    viz.appendChild(svg);

    legendSlot.innerHTML = '';
    buildLegend(legendSlot);

    // Colonna risultati: intestazione sticky con la coordinata selezionata,
    // sotto una lista verticale (una costrizione per riga).
    function renderResults(headerText, hintText, constraints) {
        resultsEl.innerHTML = '';

        const header = document.createElement('div');
        header.className = 'matrix-results-header';
        header.textContent = headerText;
        resultsEl.appendChild(header);

        if (hintText) {
            const hint = document.createElement('p');
            hint.className = 'matrix-results-hint';
            hint.textContent = hintText;
            resultsEl.appendChild(hint);
        }

        if (!constraints) return;

        if (!constraints.length) {
            const p = document.createElement('p');
            p.className = 'matrix-results-empty';
            p.textContent = 'Nessuna costrizione in questo gruppo.';
            resultsEl.appendChild(p);
            return;
        }

        const list = document.createElement('ul');
        list.className = 'matrix-results-list';
        constraints.forEach((c) => {
            const li = document.createElement('li');
            if (c.uri === focusUri) li.classList.add('matrix-results-current');
            const a = document.createElement('a');
            a.href = '/explain?uri=' + encodeURIComponent(c.uri);
            a.className = 'internal-link';
            a.textContent = c.label;
            li.appendChild(a);
            list.appendChild(li);
        });
        resultsEl.appendChild(list);
    }

    function selectMark(mark) {
        const rowLabel = rows[mark.r].label;
        const colLabel = cols[mark.c].label;
        const originLabel = (mark.origin || 'origine non specificata').toLowerCase();
        const classLabel = (CLASS_LABELS[mark.cls] || mark.cls).toLowerCase();
        const header = `${rowLabel} × ${colLabel} · ${classLabel} · ${originLabel} · `
            + `${mark.n} costrizion${mark.n === 1 ? 'e' : 'i'}`;
        renderResults(header, 'Clicca un\'altra cella della matrice per esplorare le altre costrizioni.', mark.constraints);
    }

    const focusMarks = focusUri && data.index[focusUri];
    if (focusMarks && focusMarks.length) {
        selectMark(data.marks[focusMarks[0]]);
    } else if (focusUri) {
        renderResults(
            'Questa scheda non è collocata nella matrice',
            'Il modello non le associa alcuna unità linguistica: clicca una cella per esplorare il sistema.',
            null,
        );
    } else {
        renderResults('Seleziona una cella', 'Clicca una forma nella matrice, o un\'etichetta per la sua definizione.', null);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const viz = document.getElementById('constraint-matrix-viz');
    if (!viz) return;
    const legendSlot = document.getElementById('constraint-matrix-legend');
    const resultsEl = document.getElementById('constraint-matrix-results');
    const focusUri = viz.dataset.focusUri || '';

    viz.innerHTML = '<p class="constraint-matrix-loading">Caricamento della matrice…</p>';
    try {
        const data = await loadData();
        renderMatrix({ viz, legendSlot, resultsEl }, data, focusUri);
    } catch (err) {
        viz.innerHTML = '';
        const p = document.createElement('p');
        p.className = 'constraint-matrix-error';
        p.textContent = 'Impossibile caricare la matrice delle costrizioni.';
        viz.appendChild(p);
        console.error(err);
    }
});
