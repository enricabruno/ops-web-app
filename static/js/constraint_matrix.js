/* Matrice operazione x unità: mappa tutte le costrizioni del corpus */

const SVG_NS = 'http://www.w3.org/2000/svg';

// CELL_W, CELL_H, ROW_LABEL_W e COL_LABEL_H non sono più costanti fisse:
// dipendono dallo spazio disponibile (vedi layoutFor più sotto), perché il
// drawer di approfondimento può restringere la matrice in regime push.
const COL_LABEL_TICK = 10; // distanza fra il bordo inferiore della griglia e l'ancora dell'etichetta
const MARGIN = { top: 16, right: 12 };

/* Scala dimensionale GRADUATA (non continua) */
const SIZE_CUTOFFS = [1, 3, 6, 12]; // classi: 1 | 2-3 | 4-6 | 7-12 | 13+
const SQUARE_SIDE = [8, 10.5, 13.5, 18, 22]; // riferimento "comodo": usato anche dalla legenda
const CIRCLE_RATIO = 1.1284; // d = s * 2/sqrt(pi): cerchio di area pari al quadrato della stessa classe
const MARK_GAP = 4;

const CLASS_LABELS = { formal: 'Formale', semantic: 'Semantica', visual: 'Visuale' };

// Soglia pura usata da layoutFor(). L'isteresi che la circonda (comodo -> compatto
// solo sotto questa soglia, compatto -> comodo solo molto più sopra) vive in
// applyLayout(), non qui: vedi LAYOUT_SWITCH_UP e il commento su applyLayout.
const LAYOUT_SWITCH_DOWN = 1080;

/* Due preset di layout, scelti in base alla larghezza disponibile per il
   grafico (non del viewport: quella del contenitore #constraint-matrix-viz,
   che si restringe quando il drawer è aperto in regime push). L'SVG usa
   preserveAspectRatio="xMidYMid meet" e si scala uniformemente: sotto la
   soglia "comodo" le etichette rimpicciolirebbero sotto la leggibilità
   recuperata ingrandendo il grafico, quindi si passa a un preset con una
   griglia nativamente più stretta invece di lasciar rimpicciolire quella
   larga.
   Il preset "compatto" scala anche SQUARE_SIDE, ma non con un fattore unico
   per tutte e cinque le classi: le tre classi più grandi (indici 2-4: 4-6,
   7-12, 13+) restano al fattore 0,74, non lo 0,78 "di massima", perché con
   CELL_W: 48 il caso peggiore - 3 marche delle classi più grandi nella
   stessa cella (Senza operazione × Lettera), che sommano 22 + 18 + 13,5
   unità - sborderebbe anche solo rimpicciolendo la griglia. 0,74 è il
   fattore più alto che fa rientrare quel caso: 53,5 × 0,74 + 2 ×
   MARK_GAP(4) = 47,59 <= 48 (0,78 darebbe 49,73, sopra il limite).

   Le due classi più piccole (indici 0-1: 1, 2-3) NON seguono lo stesso
   fattore: 0,74 le porterebbe a 5,92 e 7,77 unità di viewBox (~6px resi),
   sotto la soglia di percettibilità per una marca al 20% di opacità (resa
   delle marche non evidenziate) - e sono le celle più frequenti della
   matrice, quelle con una sola costrizione. Il vincolo che ha determinato
   0,74 dipende SOLO dalle tre classi più grandi (il caso peggiore sopra
   non usa mai le classi 1 o 2-3 insieme alle altre due più grandi in
   numero sufficiente da sommarsi a un quarto elemento), quindi le due
   classi piccole possono essere alzate a un pavimento di leggibilità (7 e 9
   unità) senza toccarlo. Verifica dei tre vincoli (MARK_GAP = 4, CELL_W
   compatto = 48):
     a) sequenza strettamente crescente: 7 < 9 < 9,99 < 13,32 < 16,28
     b) caso peggiore (16,28 + 13,32 + 9,99) + 2×4 = 47,59 <= 48 (invariato)
     c) tre marche tutte della classe minima: 3×7 + 2×4 = 29 <= 48

   Trade-off: comprimere la scala riduce la distanza percettiva fra classi
   contigue nella parte bassa (1 vs 2-3). Accettabile perché quella
   distinzione si legge comunque dal tooltip al passaggio del mouse, mentre
   la percettibilità della marca è una condizione di esistenza - una marca
   invisibile non comunica nulla, a prescindere da quanto accuratamente
   distingua 1 da 3 costrizioni. */
function layoutFor(availableWidth) {
    if (availableWidth >= LAYOUT_SWITCH_DOWN) {
        return {
            name: 'comodo',
            CELL_W: 64, CELL_H: 44, ROW_LABEL_W: 110, COL_LABEL_H: 66,
            SQUARE_SIDE,
        };
    }
    const COMPACT_FACTOR = 0.74;
    const COMPACT_FLOOR = [7, 9]; // indici 0 (classe 1) e 1 (classe 2-3)
    return {
        name: 'compatto',
        CELL_W: 48, CELL_H: 36, ROW_LABEL_W: 92, COL_LABEL_H: 56,
        SQUARE_SIDE: SQUARE_SIDE.map((s, i) => (
            i < COMPACT_FLOOR.length ? COMPACT_FLOOR[i] : Math.round(s * COMPACT_FACTOR * 100) / 100
        )),
    };
}

const PALETTE_ICON_SVG = `
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 2.5C6.8 2.5 2.5 6.4 2.5 11.4c0 3.6 2.6 6.3 6 6.3.9 0 1.6-.7 1.6-1.6 0-.4-.2-.7-.4-1-.2-.3-.4-.6-.4-1 0-.8.7-1.4 1.5-1.4h1.8c2.9 0 5.1-2.1 5.1-4.7 0-3-3-5.1-6.7-5.1Z"/>
    <circle cx="7.6" cy="10.3" r="0.9" fill="currentColor" stroke="none"/>
    <circle cx="9.8" cy="6.9" r="0.9" fill="currentColor" stroke="none"/>
    <circle cx="13.6" cy="6.6" r="0.9" fill="currentColor" stroke="none"/>
    <circle cx="15.4" cy="9.9" r="0.9" fill="currentColor" stroke="none"/>
    <path d="M13.3 9.2c1.7-1.6 4.6-4.4 5.9-5.7.7-.7 1.9-.7 2.6.1.7.7.6 1.9-.1 2.6-1.3 1.3-4.1 4.1-5.7 5.8" stroke-width="1.3"/>
    <path d="M12.6 8.4c-1.4 1.4-3 3.7-3.6 5.2-.2.6.3 1.1.9.9 1.5-.6 3.8-2.2 5.2-3.6.9-.9.9-2.5-.1-3.4-.9-.9-2.5-1-3.4-.1z" fill="currentColor" stroke="none"/>
</svg>`.trim();

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

/* Legenda: solo i campioni (classe / origine / numerosità) */
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
        sw.className = 'constraint-matrix-legend-swatch constraint-matrix-legend-icon';
        sw.style.color = `var(--matrix-${c.key})`;
        sw.innerHTML = PALETTE_ICON_SVG;
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
        const svg = el('svg', { width: 18, height: 18, viewBox: '0 0 18 18' });
        svg.classList.add('constraint-matrix-legend-swatch');
        if (shape === 'square') {
            svg.appendChild(el('rect', { x: 2.6, y: 2.6, width: 12.9, height: 12.9, fill: 'var(--color-text)' }));
        } else {
            svg.appendChild(el('circle', { cx: 9, cy: 9, r: 7.2, fill: 'var(--color-text)' }));
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
    const sizeBox = 28;
    const sizeGap = 8;
    sizeLabels.forEach((label, i) => {
        const row = document.createElement('div');
        row.className = 'constraint-matrix-legend-row';
        const s = SQUARE_SIDE[i];
        const d = s * CIRCLE_RATIO;
        const svgW = sizeBox * 2 + sizeGap;
        const svg = el('svg', { width: svgW, height: sizeBox, viewBox: `0 0 ${svgW} ${sizeBox}` });
        svg.classList.add('constraint-matrix-legend-swatch');
        svg.style.width = svgW + 'px';
        svg.style.height = sizeBox + 'px';
        const cx1 = sizeBox / 2;
        const cx2 = sizeBox + sizeGap + sizeBox / 2;
        const cy = sizeBox / 2;
        svg.appendChild(el('rect', {
            x: cx1 - s / 2, y: cy - s / 2, width: s, height: s, fill: 'var(--color-text)',
        }));
        svg.appendChild(el('circle', { cx: cx2, cy, r: d / 2, fill: 'var(--color-text)' }));
        row.appendChild(svg);
        const lbl = document.createElement('span');
        lbl.textContent = label;
        row.appendChild(lbl);
        container.appendChild(row);
    });
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

/* Singleton a livello di modulo: un solo nodo per l'intera vita della pagina,
   creato pigramente al primo utilizzo. Un renderMatrix() che ne creasse uno
   proprio a ogni chiamata lascerebbe nodi orfani agganciati a document.body
   a ogni re-render (es. al cambio di preset su resize, intervento 4). */
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

    // Il tooltip è condiviso fra i render: se uno precedente lo aveva
    // lasciato visibile su una marca ora distrutta, va nascosto subito.
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
    // Etichette: tooltip di definizione riga/colonna (comportamento invariato)
    const { rowBands: labelRowBands, colBands: labelColBands } = makeBandSet();
    // Selezione fissata su una marca (clic): persiste fino alla prossima selezione
    const { rowBands: selectionRowBands, colBands: selectionColBands } = makeBandSet();
    // Anteprima al passaggio del mouse su una marca: più leggera, transitoria
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

    // Marche, raggruppate per cella
    const markLayer = el('g');
    svg.appendChild(markLayer);
    const ringLayer = el('g'); // sopra le marche: l'anello di selezione non deve restare coperto
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
                // Destinazione univoca: vero link, niente scelta da fare.
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

    // Esposto a chi chiama: un re-render (cambio di preset su resize) deve
    // poter leggere la selezione fissata corrente e riapplicarla dopo aver
    // ricostruito l'SVG, così l'utente non la perde.
    return {
        setFixedSelection,
        getFixedMark: () => fixedMark,
    };
}

/* Drawer di approfondimento: apertura/chiusura, backdrop, Esc, e la marca
   che indica "c'è altro da aprire qui" tramite inert sul pannello chiuso
   (non solo opacity/transform, altrimenti resterebbe raggiungibile da
   tastiera e screen reader a pannello nascosto). */
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

    // Stato iniziale: chiuso e non raggiungibile da tastiera/screen reader.
    panel.setAttribute('inert', '');

    handle.addEventListener('click', () => setOpen(!isOpen()));
    document.addEventListener('keydown', (ev) => {
        if (ev.key === 'Escape' && isOpen()) setOpen(false);
    });
    if (backdrop) {
        backdrop.addEventListener('click', () => setOpen(false));
    }

    // Richiamo all'arrivo: una sola volta per sessione di navigazione, non a
    // ogni scheda - l'utente che passa da una costrizione all'altra in
    // sequenza non deve rivederlo a ripetizione. sessionStorage (non
    // localStorage) perché al ritorno dopo giorni il promemoria torna utile.
    let alreadySeen = false;
    try {
        alreadySeen = sessionStorage.getItem('ops.drawerSeen') === '1';
    } catch (e) {
        // storage non disponibile (modalità privata, cookie bloccati): niente
        // richiamo, ma il drawer resta pienamente funzionante.
    }
    if (!alreadySeen) {
        handle.classList.add('matrix-drawer--calling');
        callingTimer = setTimeout(stopCalling, 6000);
        handle.addEventListener('focus', stopCalling, { once: true });
        try { sessionStorage.setItem('ops.drawerSeen', '1'); } catch (e) { /* ignore */ }
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    initDrawer();

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

    // Isteresi sulla soglia di layoutFor(): comodo -> compatto sotto
    // LAYOUT_SWITCH_DOWN (soglia unica, già in layoutFor), compatto -> comodo
    // solo sopra LAYOUT_SWITCH_UP. Una soglia secca sola farebbe oscillare il
    // preset - e quindi un re-render completo - a ogni piccola variazione
    // della larghezza disponibile attorno ad essa (un resize lento, la
    // comparsa di una scrollbar). La banda morta [1080, 1120] vive qui, non
    // in layoutFor(), che resta pura e testabile con la sua sola soglia.
    const LAYOUT_SWITCH_UP = 1120;

    function shouldSwitchPreset(nextName, availableWidth) {
        if (nextName === currentPreset) return false;
        if (currentPreset === 'compatto' && nextName === 'comodo') {
            return availableWidth > LAYOUT_SWITCH_UP;
        }
        return true;
    }

    // Ri-renderizza SOLO quando l'isteresi accetta il cambio di preset
    // (comodo/compatto), non a ogni pixel di variazione durante il
    // trascinamento o l'animazione del drawer: un re-render per frame su una
    // matrice da ~90 nodi SVG sarebbe inaccettabile. La selezione fissata
    // sopravvive al cambio.
    function applyLayout(availableWidth) {
        const layout = layoutFor(availableWidth);
        if (!shouldSwitchPreset(layout.name, availableWidth)) return;
        currentPreset = layout.name;
        const previousFixedMark = matrixApi ? matrixApi.getFixedMark() : null;
        matrixApi = renderMatrix({ viz, legendSlot, resultsEl, hintEl }, data, focusUri, layout);
        if (previousFixedMark) matrixApi.setFixedSelection(previousFixedMark);
    }

    applyLayout(viz.getBoundingClientRect().width);

    let resizeTimer = null;
    const observer = new ResizeObserver((entries) => {
        const width = entries[entries.length - 1].contentRect.width;
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => applyLayout(width), 150);
    });
    observer.observe(viz);
});
