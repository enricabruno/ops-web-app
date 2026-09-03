/* Matrice operazione x unità: mappa tutte le costrizioni del corpus */

const SVG_NS = 'http://www.w3.org/2000/svg';

const MARGIN = { top: 16, right: 12 };

/* Scala dimensionale GRADUATA (non continua) */
const SIZE_CUTOFFS = [1, 3, 6, 12]; 
const SQUARE_SIDE = [8, 10.5, 13.5, 18, 22]; 
const CIRCLE_RATIO = 1.1284; 
const MARK_GAP = 4;

const CLASS_LABELS = { formal: 'Formale', semantic: 'Semantica', visual: 'Visuale' };

const LAYOUT_SWITCH_DOWN = 1080;

// marca max 22 + anello 3+3 = 28, più 2 di aria. Coincide col valore fisso
// che il preset compatto usa oggi: non è una coincidenza, è lo stesso
// vincolo geometrico.
const CELL_H_MIN = 30;
// oltre, le celle si allungano in verticale e la matrice si sfilaccia
const CELL_H_MAX = 48;

function layoutFor(availableWidth, availableHeight, rowCount, colCount) {
    let base;
    if (availableWidth >= LAYOUT_SWITCH_DOWN) {
        base = {
            name: 'comodo',
            CELL_W: 64, CELL_H: 32, ROW_LABEL_W: 110, COL_LABEL_H: 66,
            SQUARE_SIDE,
        };
    } else {
        const COMPACT_FACTOR = 0.74;
        const COMPACT_FLOOR = [7, 9]; // indici 0 (classe 1) e 1 (classe 2-3)
        base = {
            name: 'compatto',
            CELL_W: 48, CELL_H: 30, ROW_LABEL_W: 92, COL_LABEL_H: 56,
            SQUARE_SIDE: SQUARE_SIDE.map((s, i) => (
                i < COMPACT_FLOOR.length ? COMPACT_FLOOR[i] : Math.round(s * COMPACT_FACTOR * 100) / 100
            )),
        };
    }

    if (Number.isFinite(availableHeight) && Number.isFinite(rowCount) && rowCount > 0 && Number.isFinite(colCount)) {
        // La scala è imposta dalla larghezza: preserveAspectRatio="meet" e il
        // viewBox è più largo che alto, quindi il vincolo attivo è orizzontale.
        const viewBoxW = base.ROW_LABEL_W + colCount * base.CELL_W + MARGIN.right;
        const scale = availableWidth / viewBoxW;
        // altezza di viewBox che riempie esattamente lo spazio verticale
        const targetViewBoxH = availableHeight / scale;
        let cellH = (targetViewBoxH - MARGIN.top - base.COL_LABEL_H) / rowCount;
        cellH = Math.max(CELL_H_MIN, Math.min(CELL_H_MAX, cellH));
        cellH = Math.round(cellH * 2) / 2; // a 0,5 unità: evita re-render sub-pixel
        base.CELL_H = cellH;
    }

    return base;
}

/* Campione "Classe": stessa coppia quadrato+cerchio del gruppo Origine, così
   la legenda usa un solo linguaggio di forme; qui il colore (non la forma)
   porta l'informazione, quindi le due forme sono affiancate per chiarire che
   il colore vale a prescindere dalla forma/origine. */
const CLASS_SWATCH_SQUARE = 12.9;
const CLASS_SWATCH_CIRCLE_D = CLASS_SWATCH_SQUARE * CIRCLE_RATIO;
const CLASS_SWATCH_GAP = 6;
const CLASS_SWATCH_PAD = 1.5;

function sizeClassIndex(n) {
    let idx = 0;
    for (const cutoff of SIZE_CUTOFFS) {
        if (n > cutoff) idx += 1;
    }
    return idx;
}

export function originShape(origin) {
    if (!origin) return 'diamond';
    const o = origin.toLowerCase();
    if (o.startsWith('orig')) return 'square';
    if (o.startsWith('stor')) return 'circle';
    return 'diamond';
}

let _measureCtx = null;
export function measureText(text, font) {
    if (!_measureCtx) _measureCtx = document.createElement('canvas').getContext('2d');
    _measureCtx.font = font;
    return _measureCtx.measureText(text).width;
}

const ROW_LABEL_FONT = '12px Futura, "Century Gothic", "Trebuchet MS", sans-serif';

export function wrapRowLabel(text, maxWidth) {
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

export function el(tag, attrs, ns) {
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

/* Legenda: tre gruppi ORIZZONTALI (classe, origine, numero di costrizioni) */
function legendGroup(titleText, extraClass) {
    const group = document.createElement('div');
    group.className = 'matrix-legend-group' + (extraClass ? ' ' + extraClass : '');
    const title = document.createElement('h2');
    title.className = 'matrix-legend-group__title';
    title.textContent = titleText;
    group.appendChild(title);
    const items = document.createElement('div');
    items.className = 'matrix-legend-group__items';
    group.appendChild(items);
    return { group, items };
}

function legendItem(swatchNode, labelText, extraClass) {
    const item = document.createElement('span');
    item.className = 'matrix-legend-item' + (extraClass ? ' ' + extraClass : '');
    const swatch = document.createElement('span');
    swatch.className = 'matrix-legend-item__swatch';
    swatch.appendChild(swatchNode);
    item.appendChild(swatch);
    const lbl = document.createElement('span');
    lbl.textContent = labelText;
    item.appendChild(lbl);
    return item;
}

function buildLegend(container) {
    const classes = [
        { key: 'formal', label: 'Formale' },
        { key: 'semantic', label: 'Semantica' },
        { key: 'visual', label: 'Visuale' },
    ];
    const { group: classGroup, items: classItems } = legendGroup('Classe');
    const classW = CLASS_SWATCH_PAD + CLASS_SWATCH_SQUARE + CLASS_SWATCH_GAP + CLASS_SWATCH_CIRCLE_D + CLASS_SWATCH_PAD;
    const classH = Math.max(CLASS_SWATCH_SQUARE, CLASS_SWATCH_CIRCLE_D) + CLASS_SWATCH_PAD * 2;
    classes.forEach(c => {
        const svg = el('svg', { width: classW, height: classH, viewBox: `0 0 ${classW} ${classH}` });
        svg.appendChild(el('rect', {
            x: CLASS_SWATCH_PAD, y: classH / 2 - CLASS_SWATCH_SQUARE / 2,
            width: CLASS_SWATCH_SQUARE, height: CLASS_SWATCH_SQUARE, fill: `var(--matrix-${c.key})`,
        }));
        svg.appendChild(el('circle', {
            cx: CLASS_SWATCH_PAD + CLASS_SWATCH_SQUARE + CLASS_SWATCH_GAP + CLASS_SWATCH_CIRCLE_D / 2,
            cy: classH / 2, r: CLASS_SWATCH_CIRCLE_D / 2, fill: `var(--matrix-${c.key})`,
        }));
        classItems.appendChild(legendItem(svg, c.label, 'matrix-legend-item--size'));
    });
    container.appendChild(classGroup);

    const { group: originGroup, items: originItems } = legendGroup('Origine');
    [['square', 'Originale'], ['circle', 'Storica']].forEach(([shape, label]) => {
        const svg = el('svg', { width: 17, height: 17, viewBox: '0 0 18 18' });
        if (shape === 'square') {
            svg.appendChild(el('rect', { x: 2.6, y: 2.6, width: 12.9, height: 12.9, fill: 'var(--color-text)' }));
        } else {
            svg.appendChild(el('circle', { cx: 9, cy: 9, r: 7.2, fill: 'var(--color-text)' }));
        }
        originItems.appendChild(legendItem(svg, label));
    });
    container.appendChild(originGroup);

    const { group: sizeGroup, items: sizeItems } = legendGroup('Numero di costrizioni', 'matrix-legend-group--size');
    const sizeLabels = ['1', '2–3', '4–6', '7–12', '13+'];
    const SWATCH_GAP = 6;
    const SWATCH_PAD = 1.5;
    const SWATCH_H = 30;
    sizeLabels.forEach((label, i) => {
        const s = SQUARE_SIDE[i];
        const d = s * CIRCLE_RATIO;
        const w = SWATCH_PAD + s + SWATCH_GAP + d + SWATCH_PAD;
        const cx = SWATCH_PAD + s + SWATCH_GAP + d / 2;
        console.assert((cx - d / 2) - (SWATCH_PAD + s) >= SWATCH_GAP - 0.01,
            'campione legenda: forme troppo vicine, classe ' + label);
        const svg = el('svg', { width: w, height: SWATCH_H, viewBox: `0 0 ${w} ${SWATCH_H}` });
        svg.appendChild(el('rect', {
            x: SWATCH_PAD, y: SWATCH_H / 2 - s / 2, width: s, height: s, fill: 'var(--color-text)',
        }));
        svg.appendChild(el('circle', { cx, cy: SWATCH_H / 2, r: d / 2, fill: 'var(--color-text)' }));
        sizeItems.appendChild(legendItem(svg, label, 'matrix-legend-item--size'));
    });
    container.appendChild(sizeGroup);
}

export function markElement(mark, cx, cy, side) {
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
    return node;
}

function markAriaLabel(mark) {
    const originLabel = mark.origin || 'origine non specificata';
    return `${CLASS_LABELS[mark.cls] || mark.cls}, ${originLabel}, ${mark.n} costrizion${mark.n === 1 ? 'e' : 'i'}`;
}

let _tooltip = null;
function getTooltip() {
    if (!_tooltip) {
        _tooltip = document.createElement('div');
        _tooltip.className = 'constraint-matrix-tooltip';
        _tooltip.style.display = 'none';
        _tooltip.setAttribute('role', 'tooltip');
        document.body.appendChild(_tooltip);
    }
    return _tooltip;
}

function renderMatrix(containers, data, focusUri, layout) {
    const { viz, legendSlot, resultsEl, hintEl } = containers;
    const { CELL_W, CELL_H, ROW_LABEL_W, COL_LABEL_H, SQUARE_SIDE } = layout;
    viz.innerHTML = '';

    const tooltip = getTooltip();
    hideTooltip();

    const rows = data.rows;
    const cols = data.cols;
    const gridX0 = ROW_LABEL_W;
    const gridTop = MARGIN.top;
    const gridBottom = gridTop + rows.length * CELL_H;
    const gridY0 = gridTop;
    const width = ROW_LABEL_W + cols.length * CELL_W + MARGIN.right;
    const height = gridBottom + COL_LABEL_H;

    const svg = el('svg', {
        viewBox: `0 0 ${width} ${height}`,
        preserveAspectRatio: 'xMinYMin meet',
        class: 'viz',
        role: 'img',
        'aria-label': 'Matrice operazione per unità delle costrizioni del corpus DeSMòS',
    });
    svg.style.setProperty('--vb-w', width);
    svg.style.setProperty('--vb-h', height);
    const desc = el('desc');
    desc.textContent = `${rows.length} operazioni (righe, inclusa la riga senza operazione) per `
        + `${cols.length} unità formali/semantiche (colonne). Ogni forma rappresenta un gruppo di costrizioni `
        + 'che condividono cella, classe e origine.';
    svg.appendChild(desc);

    const bandLayer = el('g');
    svg.appendChild(bandLayer);
    function makeBandSet() {
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
        return { rowBands, colBands };
    }
    const { rowBands: labelRowBands, colBands: labelColBands } = makeBandSet();
    const { rowBands: selectionRowBands, colBands: selectionColBands } = makeBandSet();
    const { rowBands: previewRowBands, colBands: previewColBands } = makeBandSet();

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
            labelRowBands.forEach(b => b.classList.remove('matrix-cell-band--active'));
            labelColBands.forEach(b => b.classList.remove('matrix-cell-band--active'));
        }
    });

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
            labelRowBands.forEach((b, i) => b.classList.toggle('matrix-cell-band--active', i === r));
            labelColBands.forEach(b => b.classList.remove('matrix-cell-band--active'));
        };
        text.addEventListener('mouseenter', activate);
        text.addEventListener('mouseleave', () => { labelRowBands[r].classList.remove('matrix-cell-band--active'); hideTooltip(); });
        text.addEventListener('click', activate);
        text.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') activate(ev); });
        labelLayer.appendChild(text);
    });
    // Trattini fra il bordo inferiore della griglia e le etichette di colonna ruotate
    const COL_LABEL_TICK = 12;
    const tickLayer = el('g');
    svg.appendChild(tickLayer);
    cols.forEach((col, c) => {
        const x = gridX0 + c * CELL_W + CELL_W / 2;
        const y = gridBottom + COL_LABEL_TICK;
        tickLayer.appendChild(el('line', {
            x1: x, x2: x, y1: gridBottom, y2: y - 4,
            stroke: 'var(--color-border)', 'stroke-width': 0.5,
        }));
        const text = el('text', {
            class: 'matrix-axis-label', x, y,
            'text-anchor': 'end', transform: `rotate(-45 ${x} ${y})`, tabindex: '0',
        });
        text.textContent = col.short || col.label;
        const activate = (ev) => {
            ev.stopPropagation();
            showTooltip(text, col.label, col.definition);
            labelColBands.forEach((b, i) => b.classList.toggle('matrix-cell-band--active', i === c));
            labelRowBands.forEach(b => b.classList.remove('matrix-cell-band--active'));
        };
        text.addEventListener('mouseenter', activate);
        text.addEventListener('mouseleave', () => { labelColBands[c].classList.remove('matrix-cell-band--active'); hideTooltip(); });
        text.addEventListener('click', activate);
        text.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') activate(ev); });
        labelLayer.appendChild(text);
    });

    const markLayer = el('g');
    svg.appendChild(markLayer);
    const ringLayer = el('g');
    svg.appendChild(ringLayer);
    const byCell = new Map();
    data.marks.forEach((mark, i) => {
        const key = mark.r + ':' + mark.c;
        if (!byCell.has(key)) byCell.set(key, []);
        byCell.get(key).push({ ...mark, index: i });
    });

    const focusIndices = new Set((focusUri && data.index[focusUri]) || []);
    const markGeometry = new Map();
    let fixedMark = null;
    let selectionRing = null;
    let previewRow = null;
    let previewCol = null;

    function ringGeometry(mark, cx, cy, side) {
        const shape = originShape(mark.origin);
        if (shape === 'circle') {
            return { tag: 'circle', attrs: { cx, cy, r: (side * CIRCLE_RATIO) / 2 + 3 } };
        }
        if (shape === 'square') {
            const s = side + 6;
            return { tag: 'rect', attrs: { x: cx - s / 2, y: cy - s / 2, width: s, height: s } };
        }
        const half = (side * CIRCLE_RATIO) / 2 + 3;
        return {
            tag: 'polygon',
            attrs: { points: [`${cx},${cy - half}`, `${cx + half},${cy}`, `${cx},${cy + half}`, `${cx - half},${cy}`].join(' ') },
        };
    }

    function clearRing() {
        if (selectionRing) { selectionRing.remove(); selectionRing = null; }
    }

    function setFixedSelection(mark) {
        fixedMark = mark;
        selectionRowBands.forEach((b, i) => b.classList.toggle('matrix-cell-band--active', i === mark.r));
        selectionColBands.forEach((b, i) => b.classList.toggle('matrix-cell-band--active', i === mark.c));
        clearRing();
        const geo = markGeometry.get(mark.index);
        if (geo) {
            const g = ringGeometry(mark, geo.cx, geo.cy, geo.side);
            const node = el(g.tag, g.attrs);
            node.classList.add('matrix-selection-ring');
            ringLayer.appendChild(node);
            selectionRing = node;
        }
        renderResults(null, null, mark.constraints, mark);
    }

    function clearPreviewBands() {
        if (previewRow !== null) previewRowBands[previewRow].classList.remove('matrix-cell-band--preview');
        if (previewCol !== null) previewColBands[previewCol].classList.remove('matrix-cell-band--preview');
        previewRow = null;
        previewCol = null;
    }

    function showPreview(mark) {
        clearPreviewBands();
        previewRow = mark.r;
        previewCol = mark.c;
        previewRowBands[mark.r].classList.add('matrix-cell-band--preview');
        previewColBands[mark.c].classList.add('matrix-cell-band--preview');
        renderResults(null, 'Clicca per fissare la selezione, o un nome per aprirlo', mark.constraints, mark);
    }

    function restoreFixedState() {
        clearPreviewBands();
        if (fixedMark) {
            renderResults(null, null, fixedMark.constraints, fixedMark);
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
    svg.addEventListener('mouseleave', restoreFixedState);

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
            markGeometry.set(mark.index, { cx: shapeCx, cy, side });
            if (focusIndices.size) {
                node.classList.add(focusIndices.has(mark.index) ? 'matrix-mark--focus' : 'matrix-mark--dim');
            }
            node.addEventListener('mouseenter', () => showPreview(mark));

            if (mark.n === 1) {
                const uri = mark.constraints[0].uri;
                const link = el('a', { href: '/explain?uri=' + encodeURIComponent(uri), role: 'link', tabindex: '0' });
                link.setAttribute('aria-label', markAriaLabel(mark));
                link.appendChild(node);
                markLayer.appendChild(link);
            } else {
                node.classList.add('matrix-mark--group');
                node.setAttribute('role', 'button');
                node.setAttribute('tabindex', '0');
                node.setAttribute('aria-label', markAriaLabel(mark));
                const select = () => setFixedSelection(mark);
                node.addEventListener('click', select);
                node.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') select(); });
                markLayer.appendChild(node);
            }
            x += side + MARK_GAP;
        });
    });

    viz.appendChild(svg);

    legendSlot.innerHTML = '';
    buildLegend(legendSlot);

    function groupHeading(mark, constraints) {
        if (focusUri) {
            const focusConstraint = constraints.find(c => c.uri === focusUri);
            if (focusConstraint) {
                return focusConstraint.label
                    ? `Altre costrizioni che condividono la posizione:`
                    : 'Altre costrizioni che condividono questa posizione';
            }
        }
        if (mark && rows[mark.r] && cols[mark.c]) {
            return `Costrizioni in ${rows[mark.r].label} × ${cols[mark.c].label}`;
        }
        return 'Altre costrizioni che condividono questa posizione';
    }

    function renderResults(headerText, hintText, constraints, mark) {
        resultsEl.innerHTML = '';
        hintEl.innerHTML = '';

        if (!constraints) {
            const header = document.createElement('div');
            header.className = 'matrix-results-header';
            header.textContent = headerText;
            resultsEl.appendChild(header);
            if (hintText) {
                const hint = document.createElement('p');
                hint.className = 'matrix-results-hint';
                hint.textContent = hintText;
                hintEl.appendChild(hint);
            }
            return;
        }

        if (!constraints.length) {
            const p = document.createElement('p');
            p.className = 'matrix-results-empty';
            p.textContent = 'Nessuna costrizione in questo gruppo.';
            resultsEl.appendChild(p);
            return;
        }

        const heading = document.createElement('p');
        heading.className = 'matrix-results-heading';
        heading.textContent = groupHeading(mark, constraints);
        resultsEl.appendChild(heading);

        const flow = document.createElement('p');
        flow.className = 'matrix-results-flow';
        constraints.forEach((c, i) => {
            if (c.uri === focusUri) {
                const span = document.createElement('span');
                span.className = 'matrix-results-current';
                span.textContent = c.label;
                flow.appendChild(span);
            } else {
                const a = document.createElement('a');
                a.href = '/explain?uri=' + encodeURIComponent(c.uri);
                a.className = 'internal-link';
                a.textContent = c.label;
                flow.appendChild(a);
            }
            if (i < constraints.length - 1) flow.appendChild(document.createTextNode(', '));
        });
        resultsEl.appendChild(flow);

        if (hintText) {
            const hint = document.createElement('p');
            hint.className = 'matrix-results-hint';
            hint.textContent = `(${hintText})`;
            hintEl.appendChild(hint);
        }
    }

    const focusMarks = focusUri && data.index[focusUri];
    if (focusMarks && focusMarks.length) {
        const idx = focusMarks[0];
        setFixedSelection({ ...data.marks[idx], index: idx });
    } else {
        restoreFixedState();
    }

    return {
        setFixedSelection,
        getFixedMark: () => fixedMark,
    };
}

/* Drawer di approfondimento */
function initDrawer() {
    const drawer = document.getElementById('matrix-drawer');
    if (!drawer) return;
    const handle = document.getElementById('matrix-drawer-handle');
    const panel = document.getElementById('matrix-drawer-panel');
    const backdrop = document.getElementById('matrix-drawer-backdrop');

    function isOpen() {
        return drawer.dataset.open === 'true';
    }

    let callingTimer = null;
    function stopCalling() {
        handle.classList.remove('matrix-drawer--calling');
        if (callingTimer) { clearTimeout(callingTimer); callingTimer = null; }
    }

    function setOpen(open) {
        drawer.dataset.open = open ? 'true' : 'false';
        handle.setAttribute('aria-expanded', open ? 'true' : 'false');
        if (open) {
            panel.removeAttribute('inert');
        } else {
            panel.setAttribute('inert', '');
        }
        stopCalling();
    }

    panel.setAttribute('inert', '');

    handle.addEventListener('click', () => setOpen(!isOpen()));
    document.addEventListener('keydown', (ev) => {
        if (ev.key === 'Escape' && isOpen()) setOpen(false);
    });
    if (backdrop) {
        backdrop.addEventListener('click', () => setOpen(false));
    }

    let alreadySeen = false;
    try {
        alreadySeen = sessionStorage.getItem('ops.drawerSeen') === '1';
    } catch (e) {

    }
    if (!alreadySeen) {
        handle.classList.add('matrix-drawer--calling');
        callingTimer = setTimeout(stopCalling, 6000);
        handle.addEventListener('focus', stopCalling, { once: true });
        try { sessionStorage.setItem('ops.drawerSeen', '1'); } catch (e) { /* ignore */ }
    }
}

/* Barra della legenda */
function initLegendBar(onChange) {
    const toggle = document.getElementById('matrix-legend-toggle');
    const panel = document.getElementById('matrix-legend-panel');
    if (!toggle || !panel) return;

    function setOpen(open) {
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        panel.hidden = !open;
        try { sessionStorage.setItem('ops.legendOpen', open ? '1' : '0'); } catch (e) { /* ignore */ }
        // Aprire/chiudere la legenda sposta la sezione della matrice sotto:
        // il grafico deve ricalcolare cellH sulla nuova altezza disponibile.
        if (onChange) onChange();
    }

    let startOpen = false;
    try {
        startOpen = sessionStorage.getItem('ops.legendOpen') === '1';
    } catch (e) {

    }
    if (startOpen) setOpen(true);

    toggle.addEventListener('click', () => setOpen(panel.hidden));
}

document.addEventListener('DOMContentLoaded', async () => {
    initDrawer();
    // initLegendBar() gira prima che triggerLayoutUpdate esista: il
    // wrapper cattura la variabile per riferimento, così la chiamata dal
    // toggle della legenda usa sempre la versione definitiva assegnata più
    // sotto, invece di restare legata a un no-op.
    let triggerLayoutUpdate = () => {};
    initLegendBar(() => triggerLayoutUpdate());

    const viz = document.getElementById('constraint-matrix-viz');
    if (!viz) return;
    const legendSlot = document.getElementById('constraint-matrix-legend');
    const resultsEl = document.getElementById('constraint-matrix-results');
    const hintEl = document.getElementById('constraint-matrix-hint');
    const focusUri = viz.dataset.focusUri || '';

    viz.innerHTML = '<p class="constraint-matrix-loading">Caricamento della matrice…</p>';
    let data;
    try {
        data = await loadData();
    } catch (err) {
        viz.innerHTML = '';
        const p = document.createElement('p');
        p.className = 'constraint-matrix-error';
        p.textContent = 'Impossibile caricare la matrice delle costrizioni.';
        viz.appendChild(p);
        console.error(err);
        return;
    }

    let matrixApi = null;
    let currentPreset = null;
    let lastCellH = null;

    const LAYOUT_SWITCH_UP = 1120;

    function shouldSwitchPreset(nextName, availableWidth) {
        if (nextName === currentPreset) return false;
        if (currentPreset === 'compatto' && nextName === 'comodo') {
            return availableWidth > LAYOUT_SWITCH_UP;
        }
        return true;
    }

    function applyLayout(availableWidth) {
        // vizTop misurato una volta sola, prima del render: cellH dipende da
        // vizTop, e un ricalcolo a render avvenuto potrebbe innescare un
        // anello di retroazione.
        const vizTop = viz.getBoundingClientRect().top;
        const BOTTOM_MARGIN = 24; // aria sotto le etichette
        const availableHeight = window.innerHeight - vizTop - BOTTOM_MARGIN;
        const rowCount = data.rows.length;
        const colCount = data.cols.length;
        const layout = layoutFor(availableWidth, availableHeight, rowCount, colCount);

        const presetChanged = shouldSwitchPreset(layout.name, availableWidth);
        const cellHChanged = lastCellH === null || Math.abs(layout.CELL_H - lastCellH) >= 1;
        if (!presetChanged && !cellHChanged) return;
        lastCellH = layout.CELL_H;
        currentPreset = layout.name;

        const previousFixedMark = matrixApi ? matrixApi.getFixedMark() : null;
        matrixApi = renderMatrix({ viz, legendSlot, resultsEl, hintEl }, data, focusUri, layout);
        if (previousFixedMark) matrixApi.setFixedSelection(previousFixedMark);
        syncHandleCenter();
    }

    function syncHandleCenter() {
        const layoutEl = document.querySelector('.matrix-layout');
        if (!layoutEl || !viz) return;
        const layoutBox = layoutEl.getBoundingClientRect();
        const chartBox = viz.getBoundingClientRect();
        const center = (chartBox.top + chartBox.height / 2) - layoutBox.top;
        layoutEl.style.setProperty('--handle-center', center + 'px');
    }

    triggerLayoutUpdate = () => {
        applyLayout(viz.getBoundingClientRect().width);
        syncHandleCenter();
    };

    triggerLayoutUpdate();

    const panel = document.querySelector('.matrix-drawer__panel');
    if (panel) {
        panel.addEventListener('transitionend', triggerLayoutUpdate);
    }

    let resizeTimer = null;
    function scheduleLayout(width) {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            applyLayout(width);
            syncHandleCenter();
        }, 150);
    }

    const observer = new ResizeObserver((entries) => {
        const width = entries[entries.length - 1].contentRect.width;
        scheduleLayout(width);
    });
    observer.observe(viz);

    // Il ResizeObserver osserva solo la larghezza del contenitore: un
    // ridimensionamento SOLO verticale della finestra non la cambia e non
    // farebbe scattare il ricalcolo di cellH.
    window.addEventListener('resize', () => {
        scheduleLayout(viz.getBoundingClientRect().width);
    });
});
