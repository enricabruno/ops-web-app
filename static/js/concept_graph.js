/* Rete concettuale (skos:broader / skos:narrower / skos:related) delle costrizioni */

import { el, measureText, wrapRowLabel, markElement, originShape } from './constraint_matrix.js';

const SQRT_PI = Math.sqrt(Math.PI);
const sideFor = (r) => r * SQRT_PI;

const FOCUS_R = 15;
const OUTER_R = 11; // genitore e correlati
const CHILD_R = 8;
const FOCUS_SIDE = sideFor(FOCUS_R);
const OUTER_SIDE = sideFor(OUTER_R);
const CHILD_SIDE = sideFor(CHILD_R);

const LABEL_FONT_FAMILY = '"Futura", "Century Gothic", "Trebuchet MS", sans-serif';
const EDGE_LABEL_FONT = '11px Futura, "Century Gothic", "Trebuchet MS", sans-serif';

const H_MARGIN = 26;
const CHILD_SLOT_W = 78;
const MIN_HALF_WIDTH = 170;

const MIN_VIEWBOX_WIDTH = 680;

const V_GAP_PARENT = 46;
const V_GAP_CHILDREN = 80;
const PARENT_LABEL_ABOVE_H = 15;
const RELATED_LABEL_ABOVE_H = 15;
const FOCUS_LABEL_H = 16;  
const FOCUS_LABEL_BELOW_H = 18;
const CHILD_LABEL_LINE_H = 13;
const CHILD_LABEL_GAP = 6;
const TOP_PAD = 6;
const BOTTOM_PAD = 6;

const DRAG_THRESHOLD = 4; // px sullo schermo: sotto questa soglia è un click, sopra è un trascinamento

const ARROW_LEN = 7;
const gapFor = (r) => Math.max(ARROW_LEN * 0.7, r * 0.45);

const FOCUS_STROKE_WIDTH = 1.6;

function commonPrefix(strings) {
    let prefix = strings[0] || '';
    for (let i = 1; i < strings.length && prefix; i++) {
        const s = strings[i];
        let j = 0;
        const max = Math.min(prefix.length, s.length);
        while (j < max && prefix[j] === s[j]) j++;
        prefix = prefix.slice(0, j);
    }
    return prefix;
}

function childLabelPrefix(children) {
    if (children.length < 2) return '';
    const raw = commonPrefix(children.map((c) => c.label));
    const cut = raw.lastIndexOf(' ');
    if (cut < 0) return '';
    const prefix = raw.slice(0, cut);
    if (prefix.length < 4) return '';
    if (children.some((c) => c.label.length <= prefix.length + 1)) return '';
    return prefix;
}

function computeLayout(data) {
    const { parent, children, related } = data;
    const hasParent = !!parent;
    const nChildren = children.length;
    const nRelated = related.length;

    const leftNodes = [];
    const rightNodes = [];
    related.forEach((node, i) => {
        (i % 2 === 0 ? rightNodes : leftNodes).push(node);
    });

    const relatedFont = `12px ${LABEL_FONT_FAMILY}`;
    const RELATED_EDGE_GAP = Math.max(60, measureText('correlato a', EDGE_LABEL_FONT) + 16);
    function layoutRelatedSide(nodes) {
        const items = [];
        let prevOuterEdge = FOCUS_R;
        nodes.forEach((node) => {
            const halfExtent = Math.max(OUTER_R, measureText(node.label, relatedFont) / 2);
            const innerFreeEdge = prevOuterEdge;
            const dist = innerFreeEdge + RELATED_EDGE_GAP + halfExtent;
            const outerFreeEdge = dist - halfExtent;
            const labelMid = (innerFreeEdge + outerFreeEdge) / 2;
            items.push({ node, dist, labelMid });
            prevOuterEdge = dist + halfExtent;
        });
        return { items, extent: prevOuterEdge };
    }
    const leftLayout = layoutRelatedSide(leftNodes);
    const rightLayout = layoutRelatedSide(rightNodes);
    const relatedPositions = [
        ...rightLayout.items.map((p) => ({ node: p.node, side: 1, dist: p.dist, labelMid: p.labelMid })),
        ...leftLayout.items.map((p) => ({ node: p.node, side: -1, dist: p.dist, labelMid: p.labelMid })),
    ];
    const leftExtent = leftNodes.length ? leftLayout.extent + 16 : 0;
    const rightExtent = rightNodes.length ? rightLayout.extent + 16 : 0;

    const childPrefix = childLabelPrefix(children);
    const childDisplayLabels = children.map((c) => (
        childPrefix ? c.label.slice(childPrefix.length + 1) : c.label
    ));
    const childFont = `12px ${LABEL_FONT_FAMILY}`;
    const childLabelMaxWidth = CHILD_SLOT_W - 6;
    const childLines = childDisplayLabels.map((label) => wrapRowLabel(label, childLabelMaxWidth));
    const maxChildLines = childLines.reduce((m, lines) => Math.max(m, lines.length), 1);

    const childrenHalfWidth = nChildren ? (nChildren * CHILD_SLOT_W) / 2 : 0;

    let childrenHalfExtent = 0;
    children.forEach((_, i) => {
        const offset = Math.abs((i - (nChildren - 1) / 2) * CHILD_SLOT_W);
        const maxLineW = childLines[i].reduce((m, line) => Math.max(m, measureText(line, childFont)), 0);
        childrenHalfExtent = Math.max(childrenHalfExtent, offset + maxLineW / 2);
    });

    const halfWidth = Math.max(leftExtent, rightExtent, childrenHalfWidth, childrenHalfExtent, MIN_HALF_WIDTH);
    const contentWidth = halfWidth * 2 + H_MARGIN * 2;
    const width = Math.max(contentWidth, MIN_VIEWBOX_WIDTH);
    const focusX = width / 2;

    let parentCy = null;
    let focusCy;
    if (hasParent) {
        parentCy = TOP_PAD + PARENT_LABEL_ABOVE_H + OUTER_R;
        focusCy = parentCy + OUTER_R + V_GAP_PARENT + FOCUS_R;
    } else {
        const topLabelH = nRelated ? RELATED_LABEL_ABOVE_H : 0;
        focusCy = TOP_PAD + topLabelH + FOCUS_R;
    }

    let childrenCy = null;
    let narrowerLabelCy = null;
    let fanStartY = null;
    if (nChildren) {
        childrenCy = focusCy + FOCUS_R + V_GAP_CHILDREN + CHILD_R;
        narrowerLabelCy = focusCy + FOCUS_R + V_GAP_CHILDREN * 0.62;
        fanStartY = focusCy + FOCUS_R + FOCUS_LABEL_H + 8;
    }

    let bottomLabelH;
    if (nChildren) {
        bottomLabelH = CHILD_LABEL_GAP + maxChildLines * CHILD_LABEL_LINE_H;
    } else {
        bottomLabelH = FOCUS_LABEL_BELOW_H;
    }

    const lastCy = nChildren ? childrenCy : focusCy;
    const lastR = nChildren ? CHILD_R : FOCUS_R;
    const height = lastCy + lastR + bottomLabelH + BOTTOM_PAD;

    return {
        width, height, focusX, focusCy, parentCy, childrenCy, narrowerLabelCy, fanStartY,
        relatedPositions, childLines,
    };
}

function nodeAriaLabel(node, roleLabel) {
    const originLabel = node.origin || 'origine non specificata';
    const clsLabel = { formal: 'Formale', semantic: 'Semantica', visual: 'Visuale' }[node.cls] || node.cls;
    return `${roleLabel}: ${node.label}, ${clsLabel}, ${originLabel}`;
}
function edgeRadius(node, nominalR, ux, uy) {
    const shape = originShape(node.origin);
    const ax = Math.abs(ux) || 1e-6;
    const ay = Math.abs(uy) || 1e-6;
    if (shape === 'square') {
        const half = sideFor(nominalR) / 2;
        return Math.min(half / ax, half / ay);
    }
    if (shape === 'diamond') {
        return nominalR / (ax + ay);
    }
    return nominalR; // circle
}

function shortenEdge(A, nodeA, rA, B, nodeB, rB) {
    const dx = B.x - A.x, dy = B.y - A.y;
    const len = Math.hypot(dx, dy) || 1;
    const ux = dx / len, uy = dy / len;
    const rAeff = edgeRadius(nodeA, rA, ux, uy);
    const rBeff = edgeRadius(nodeB, rB, ux, uy);
    const gapA = gapFor(rAeff);
    const gapB = gapFor(rBeff);
    return {
        start: { x: A.x + ux * (rAeff + gapA), y: A.y + uy * (rAeff + gapA) },
        end: { x: B.x - ux * (rBeff + gapB), y: B.y - uy * (rBeff + gapB) },
    };
}

function pushOut(point, center, amount) {
    const dx = point.x - center.x, dy = point.y - center.y;
    const len = Math.hypot(dx, dy) || 1;
    return { x: point.x + (dx / len) * amount, y: point.y + (dy / len) * amount };
}

function textEl(x, y, cls, content) {
    const t = el('text', { x, y, class: cls });
    t.textContent = content;
    return t;
}

function edgeLabelWithKnockout(cx, cy, cls, text, anchor) {
    const g = el('g', { class: 'concept-graph-edge-label-group' });
    const tw = measureText(text, EDGE_LABEL_FONT);
    const pad = 6;
    const rectW = tw + pad * 2;
    const rectX = anchor === 'start' ? cx - pad : cx - rectW / 2;
    g.appendChild(el('rect', {
        x: rectX, y: cy - 7, width: rectW, height: 14,
        class: 'concept-graph-edge-label-bg',
    }));
    g.appendChild(textEl(cx, cy + 3.5, cls, text));
    return g;
}

function multilineChildLabel(x, y, lines) {
    const t = el('text', { x, y, class: 'concept-graph-label concept-graph-label--child' });
    lines.forEach((line, i) => {
        const tspan = el('tspan', { x, dy: i === 0 ? 0 : CHILD_LABEL_LINE_H });
        tspan.textContent = line;
        t.appendChild(tspan);
    });
    return t;
}

function checkLabelCollisions(svg) {
    const labels = svg.querySelectorAll('.concept-graph-label');
    const edges = svg.querySelectorAll('.concept-graph-edge');
    labels.forEach((label) => {
        const box = label.getBBox();
        for (const edge of edges) {
            const len = edge.getTotalLength();
            for (let d = 0; d <= len; d += 4) {
                const p = edge.getPointAtLength(d);
                if (p.x > box.x && p.x < box.x + box.width && p.y > box.y && p.y < box.y + box.height) {
                    console.warn('Rete concettuale: un arco attraversa l\'etichetta "' + label.textContent + '"');
                    return;
                }
            }
        }
    });
}

function renderConceptGraph(container, data) {
    const layout = computeLayout(data);
    const {
        width, height, focusX, focusCy, parentCy, childrenCy, narrowerLabelCy, fanStartY,
        relatedPositions, childLines,
    } = layout;

    const svg = el('svg', {
        viewBox: `0 0 ${width} ${height}`,
        preserveAspectRatio: 'xMidYMin meet',
        role: 'img',
        'aria-label': `Rete concettuale di ${data.focus.label}`,
        class: 'concept-graph-svg viz',
    });
    svg.style.setProperty('--vb-w', width);
    svg.style.setProperty('--vb-h', height);
    svg.style.setProperty('--focus-stroke-width', FOCUS_STROKE_WIDTH);

    const desc = el('desc');
    const parts = [];
    if (data.parent) parts.push('1 termine più generale');
    if (data.related.length) parts.push(`${data.related.length} termin${data.related.length === 1 ? 'e correlato' : 'i correlati'}`);
    if (data.children.length) parts.push(`${data.children.length} termin${data.children.length === 1 ? 'e più specifico' : 'i più specifici'}`);
    desc.textContent = `${data.focus.label}: ${parts.join(', ')}.`;
    svg.appendChild(desc);

    const marker = el('marker', {
        id: 'concept-graph-arrow',
        markerUnits: 'userSpaceOnUse',
        markerWidth: '8', markerHeight: '7', refX: '7', refY: '3.5',
        orient: 'auto-start-reverse',
    });
    marker.appendChild(el('path', { d: 'M0,0 L7,3.5 L0,7 Z', fill: 'var(--color-text)' }));
    const defs = el('defs');
    defs.appendChild(marker);
    svg.appendChild(defs);

    const edgesLayer = el('g', { class: 'concept-graph-edges' });
    const labelsLayer = el('g', { class: 'concept-graph-edge-labels' });
    const nodesLayer = el('g', { class: 'concept-graph-nodes' });
    svg.appendChild(edgesLayer);
    svg.appendChild(labelsLayer);
    svg.appendChild(nodesLayer);

    const highlightEntries = [];
    function setHighlight(active) {
        highlightEntries.forEach((entry) => {
            const isActive = entry === active;
            const isDimmed = !isActive && !!active;
            const targets = [entry.groupEl, ...entry.edgeEls, ...entry.labelEls];
            targets.forEach((elTarget) => {
                elTarget.classList.toggle('is-active', isActive);
                elTarget.classList.toggle('is-dimmed', isDimmed);
            });
        });
    }

    let anyDragged = false;
    function onFirstDrag() {
        if (anyDragged) return;
        anyDragged = true;
        resetControl.hidden = false;
    }

    function makeDraggable(groupEl, origX, origY, onMove) {
        let dragging = false;
        let moved = false;
        let startPX = 0;
        let startPY = 0;

        function svgScale() {
            const rect = svg.getBoundingClientRect();
            const vb = svg.viewBox.baseVal;
            return vb.width ? rect.width / vb.width : 1;
        }

        function onPointerDown(ev) {
            if (ev.button !== undefined && ev.button !== 0 && ev.pointerType === 'mouse') return;
            dragging = true;
            moved = false;
            startPX = ev.clientX;
            startPY = ev.clientY;
        }
        function onPointerMove(ev) {
            if (!dragging) return;
            const scale = svgScale() || 1;
            const dxPx = ev.clientX - startPX;
            const dyPx = ev.clientY - startPY;
            if (!moved && Math.hypot(dxPx, dyPx) > DRAG_THRESHOLD) {
                moved = true;
                groupEl.__wasDragged = true;
                try { groupEl.setPointerCapture(ev.pointerId); } catch (e) { /* noop */ }
                onFirstDrag();
                setHighlight(highlightEntries.find((e) => e.groupEl === groupEl) || null);
            }
            if (moved) {
                ev.preventDefault();
                const dx = dxPx / scale;
                const dy = dyPx / scale;
                groupEl.setAttribute('transform', `translate(${dx},${dy})`);
                onMove(origX + dx, origY + dy);
            }
        }
        function onPointerUp() {
            dragging = false;
        }
        groupEl.addEventListener('pointerdown', onPointerDown);
        groupEl.addEventListener('pointermove', onPointerMove);
        groupEl.addEventListener('pointerup', onPointerUp);
        groupEl.addEventListener('pointercancel', onPointerUp);
        groupEl.addEventListener('click', (ev) => {
            if (groupEl.__wasDragged) {
                ev.preventDefault();
                ev.stopPropagation();
                groupEl.__wasDragged = false;
            }
        }, true);
    }

    function buildDraggableNode(node, cx, cy, side, roleLabel, extraClass, labelText, labelBuilder, onMove, titleText) {
        const shape = markElement({ cls: node.cls, origin: node.origin }, cx, cy, side);
        const link = el('a', {
            class: `concept-graph-node ${extraClass}`.trim(),
            href: '/explain?uri=' + encodeURIComponent(node.uri),
            tabindex: '0',
            'aria-label': nodeAriaLabel(node, roleLabel),
        });
        if (titleText) {
            const titleEl = el('title');
            titleEl.textContent = titleText;
            link.appendChild(titleEl);
        }
        link.appendChild(shape);
        link.addEventListener('keydown', (ev) => {
            if (ev.key === 'Enter') window.location.href = link.getAttribute('href');
        });

        const label = labelBuilder ? labelBuilder() : textEl(cx, cy, 'concept-graph-label', labelText);

        const group = el('g', { class: 'concept-graph-node-group' });
        group.appendChild(link);
        group.appendChild(label);
        nodesLayer.appendChild(group);

        makeDraggable(group, cx, cy, onMove);

        return { group, link, label };
    }

    if (data.parent) {
        const focusPt = { x: focusX, y: focusCy };
        const parentPt = { x: focusX, y: parentCy };
        const seg0 = shortenEdge(focusPt, data.focus, FOCUS_R, parentPt, data.parent, OUTER_R);
        const start0 = pushOut(seg0.start, focusPt, FOCUS_STROKE_WIDTH / 2);
        const edge = el('path', {
            d: `M${start0.x},${start0.y} L${seg0.end.x},${seg0.end.y}`,
            class: 'concept-graph-edge concept-graph-edge--parent',
            'marker-end': 'url(#concept-graph-arrow)',
        });
        edgesLayer.appendChild(edge);
        labelsLayer.appendChild(edgeLabelWithKnockout(
            focusX + 10, (start0.y + seg0.end.y) / 2,
            'concept-graph-edge-label concept-graph-edge-label--broader', 'termine più generale', 'start',
        ));

        const { group, label } = buildDraggableNode(
            data.parent, focusX, parentCy, OUTER_SIDE, 'Termine più generale', 'concept-graph-node--parent',
            data.parent.label,
            () => textEl(focusX, parentCy - OUTER_R - 6, 'concept-graph-label concept-graph-label--parent', data.parent.label),
            (nx, ny) => {
                const seg = shortenEdge(focusPt, data.focus, FOCUS_R, { x: nx, y: ny }, data.parent, OUTER_R);
                const start = pushOut(seg.start, focusPt, FOCUS_STROKE_WIDTH / 2);
                edge.setAttribute('d', `M${start.x},${start.y} L${seg.end.x},${seg.end.y}`);
            },
        );
        highlightEntries.push({ groupEl: group, edgeEls: [edge], labelEls: [label] });
    }

    relatedPositions.forEach(({ node, side, dist, labelMid }) => {
        const nx = focusX + side * dist;
        const focusPt = { x: focusX, y: focusCy };
        const relatedPt = { x: nx, y: focusCy };
        const seg0 = shortenEdge(focusPt, data.focus, FOCUS_R, relatedPt, node, OUTER_R);
        const start0 = pushOut(seg0.start, focusPt, FOCUS_STROKE_WIDTH / 2);
        const edge = el('line', {
            x1: start0.x, y1: start0.y, x2: seg0.end.x, y2: seg0.end.y,
            class: 'concept-graph-edge concept-graph-edge--related',
            'marker-start': 'url(#concept-graph-arrow)',
            'marker-end': 'url(#concept-graph-arrow)',
        });
        edgesLayer.appendChild(edge);

        const labelX = focusX + side * labelMid;
        labelsLayer.appendChild(edgeLabelWithKnockout(
            labelX, focusCy - 8,
            'concept-graph-edge-label concept-graph-edge-label--related', 'correlato a', 'middle',
        ));

        const { group, label } = buildDraggableNode(
            node, nx, focusCy, OUTER_SIDE, 'Termine correlato', 'concept-graph-node--related',
            node.label,
            () => textEl(nx, focusCy - OUTER_R - 6, 'concept-graph-label concept-graph-label--related', node.label),
            (px, py) => {
                const seg = shortenEdge(focusPt, data.focus, FOCUS_R, { x: px, y: py }, node, OUTER_R);
                const start = pushOut(seg.start, focusPt, FOCUS_STROKE_WIDTH / 2);
                edge.setAttribute('x1', start.x); edge.setAttribute('y1', start.y);
                edge.setAttribute('x2', seg.end.x); edge.setAttribute('y2', seg.end.y);
            },
        );
        highlightEntries.push({ groupEl: group, edgeEls: [edge], labelEls: [label] });
    });

    if (data.children.length) {
        const n = data.children.length;
        const startX = focusX - (n * CHILD_SLOT_W) / 2 + CHILD_SLOT_W / 2;

        labelsLayer.appendChild(edgeLabelWithKnockout(
            focusX, narrowerLabelCy,
            'concept-graph-edge-label concept-graph-edge-label--narrower', 'termini più specifici', 'middle',
        ));

        data.children.forEach((child, i) => {
            const cx = startX + i * CHILD_SLOT_W;
            const rEnd = edgeRadius(child, CHILD_R, 0, 1);
            const endY = childrenCy - (rEnd + gapFor(rEnd));
            const isCentral = Math.abs(cx - focusX) < 0.01;
            const d = isCentral
                ? `M${focusX},${fanStartY} L${cx},${endY}`
                : `M${focusX},${fanStartY} C${focusX},${(fanStartY + endY) / 2} ${cx},${(fanStartY + endY) / 2} ${cx},${endY}`;
            const edge = el('path', {
                d, class: 'concept-graph-edge concept-graph-edge--child',
                'marker-end': 'url(#concept-graph-arrow)',
            });
            edgesLayer.appendChild(edge);

            const { group, label } = buildDraggableNode(
                child, cx, childrenCy, CHILD_SIDE, 'Termine più specifico', 'concept-graph-node--child',
                null,
                () => multilineChildLabel(cx, childrenCy + CHILD_R + 12, childLines[i]),
                (nx, ny) => {
                    const end = { x: nx, y: ny - (rEnd + gapFor(rEnd)) };
                    const midY = (fanStartY + end.y) / 2;
                    edge.setAttribute('d', `M${focusX},${fanStartY} C${focusX},${midY} ${nx},${midY} ${end.x},${end.y}`);
                },
                child.label,
            );
            highlightEntries.push({ groupEl: group, edgeEls: [edge], labelEls: [label] });
        });
    }

    const focusShape = markElement({ cls: data.focus.cls, origin: data.focus.origin }, focusX, focusCy, FOCUS_SIDE);
    const focusGroup = el('g', { class: 'concept-graph-node--focus' });
    focusGroup.appendChild(focusShape);
    const focusLabel = textEl(focusX, focusCy + FOCUS_R + 16, 'concept-graph-label concept-graph-label--focus', data.focus.label);
    focusGroup.appendChild(focusLabel);
    nodesLayer.appendChild(focusGroup);
    highlightEntries.push({ groupEl: focusGroup, edgeEls: [], labelEls: [focusLabel] });

    highlightEntries.forEach((entry) => {
        entry.groupEl.addEventListener('mouseenter', () => setHighlight(entry));
        entry.groupEl.addEventListener('mouseleave', () => setHighlight(null));
        entry.groupEl.addEventListener('focusin', () => setHighlight(entry));
        entry.groupEl.addEventListener('focusout', () => setHighlight(null));
    });

    container.innerHTML = '';
    container.appendChild(svg);
    const resetControl = document.getElementById('concept-graph-reset');
    if (resetControl) {
        resetControl.hidden = true;
        resetControl.onclick = () => renderConceptGraph(container, data);
    }

    checkLabelCollisions(svg);
}

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('concept-graph');
    if (!container) return;
    const dataScript = document.getElementById('concept-graph-data');
    if (!dataScript) return;
    let data;
    try {
        data = JSON.parse(dataScript.textContent);
    } catch (err) {
        console.error('Dati della rete concettuale non validi', err);
        return;
    }
    renderConceptGraph(container, data);
});
