(function () {
  // 1. Questa riga è FONDAMENTALE: recupera i dati passati dal server
  const _d = JSON.parse(document.getElementById('anag-data').textContent);
  
  const sourceTokens = _d.sourceTokens;
  const targetTokens = _d.targetTokens;
  const edges        = _d.edges;

  const containerWidth = document.getElementById('anag-wrapper').clientWidth;

  /* ── Layout constants (Compatti e Fluidi) ──────────────────── */
  const SRC_Y  = 100;         // Asse superiore (Ipotesto)
  const TGT_Y  = 250;         // Asse inferiore (Rigrafia)
  const SVG_H  = 350;         // Altezza totale ridotta
  const ML     = 95;         // Margine per etichette
  const MR     = 50;          // Margine destro
  const MT     = 400;         // Margine superiore per evitare sovrapposizioni con il testo

  const nSrc = sourceTokens.length;
  const nTgt = targetTokens.length;
  const nMax = Math.max(nSrc, nTgt);

  const SVG_W  = containerWidth; // Larghezza fluida basata sulla finestra
  const innerW = SVG_W - ML - MR;

  // Funzioni X: ora distribuiscono i token su tutta la larghezza
  function srcX(i) { return ML + (nSrc > 1 ? (i / (nSrc - 1)) * innerW : innerW / 2); }
  function tgtX(j) { return ML + (nTgt > 1 ? (j / (nTgt - 1)) * innerW : innerW / 2); }

  /* ── SVG setup ─────────────────────────────────────────────── */
  const svg = d3.select('#anag-svg')
    .attr('width',  SVG_W)
    .attr('height', SVG_H);

  svg.append('rect')
    .attr('width', SVG_W).attr('height', SVG_H)
    .attr('fill', '#fafafa');

  /* ── Axis lines ────────────────────────────────────────────── */
  [SRC_Y, TGT_Y].forEach(y => {
    svg.append('line')
      .attr('x1', ML - 10).attr('x2', SVG_W - MR + 10)
      .attr('y1', y).attr('y2', y)
      .attr('stroke', '#dde1e7').attr('stroke-width', 1);
  });

  /* ── Axis labels (left side) ───────────────────────────────── */
  const axisLabelAttrs = {
    'text-anchor': 'end', 'dominant-baseline': 'middle',
    'font-size': '9px', 'font-weight': '700',
    'letter-spacing': '1.5px', 'fill': '#6c757d',
    'font-family': 'Inter, sans-serif'
  };
  const srcLabel = svg.append('text').attr('x', ML - 30).attr('y', SRC_Y).text('IPOTESTO');
  const tgtLabel = svg.append('text').attr('x', ML - 30).attr('y', TGT_Y).text('IPERTESTO');
  [srcLabel, tgtLabel].forEach(el => {
    Object.entries(axisLabelAttrs).forEach(([k, v]) => el.attr(k, v));
  });

  /* ── Color scale (by normalised displacement) ──────────────── */
  function dispNorm(e) {
    const sn = nSrc > 1 ? e.src / (nSrc - 1) : 0;
    const tn = nTgt > 1 ? e.tgt / (nTgt - 1) : 0;
    return Math.abs(sn - tn);
  }
  const maxDisp = edges.length ? Math.max(...edges.map(dispNorm)) || 1 : 1;
  const cScale = d3.scaleSequential()
    .domain([0, maxDisp])
    .interpolator(d3.interpolateRgb('#c8d6e5', '#0097B2'));

  /* ── Bezier path ───────────────────────────────────────────── */
  function mkPath(e) {
    const sx = srcX(e.src), tx = tgtX(e.tgt);
    const cy = (SRC_Y + TGT_Y) / 2;
    return `M ${sx} ${SRC_Y} C ${sx} ${cy}, ${tx} ${cy}, ${tx} ${TGT_Y}`;
  }

  /* ── Draw edges ────────────────────────────────────────────── */
  const eGroup = svg.append('g').attr('class', 'edges');
  const ePaths = eGroup.selectAll('path')
    .data(edges).join('path')
    .attr('d', mkPath)
    .attr('fill', 'none')
    .attr('stroke', e => cScale(dispNorm(e)))
    .attr('stroke-width', 1.5)
    .attr('opacity', 0.65)
    .style('cursor', 'pointer');

  /* ── Draw source nodes ─────────────────────────────────────── */
  const srcG = svg.append('g');
  const srcNodes = srcG.selectAll('g').data(sourceTokens).join('g')
    .attr('transform', (d, i) => `translate(${srcX(i)},${SRC_Y})`);

  srcNodes.append('circle')
    .attr('r', 4).attr('fill', '#2c3e50')
    .attr('stroke', '#fafafa').attr('stroke-width', 1.5);

  srcNodes.append('text')
    .attr('y', -10)               // Distanza verticale fissa dal cerchio
    .attr('transform', 'rotate(-45)') // Ruota ESATTAMENTE sul punto di origine
    .attr('text-anchor', 'start') // Cambia da 'end' a 'start' per aprirsi verso l'alto
    .attr('dx', '5px')            // Piccolo distanziamento per non toccare il pallino
    .attr('font-size', '10px')
    .attr('fill', '#2c3e50')
    .attr('font-family', 'Inter, sans-serif')
    .text(d => d);

  /* ── Draw target nodes ─────────────────────────────────────── */
  const tgtG = svg.append('g');
  const tgtNodes = tgtG.selectAll('g').data(targetTokens).join('g')
    .attr('transform', (d, j) => `translate(${tgtX(j)},${TGT_Y})`);

  tgtNodes.append('circle')
    .attr('r', 4).attr('fill', '#2c3e50')
    .attr('stroke', '#fafafa').attr('stroke-width', 1.5);

  tgtNodes.append('text')
    .attr('y', 10)
    .attr('transform', 'rotate(45)')
    .attr('text-anchor', 'start')
    .attr('dx', '5px')
    .attr('font-size', '10px')
    .attr('fill', '#2c3e50')
    .attr('font-family', 'Inter, sans-serif')
    .text(d => d);

  /* ── Tooltip ───────────────────────────────────────────────── */
  const tip = d3.select('body').append('div')
    .style('position', 'fixed')
    .style('background', 'rgba(26,35,50,0.93)')
    .style('color', '#fff')
    .style('padding', '8px 14px')
    .style('border-radius', '4px')
    .style('font-size', '12px')
    .style('font-family', 'Inter, sans-serif')
    .style('pointer-events', 'none')
    .style('opacity', '0')
    .style('z-index', '9999')
    .style('line-height', '1.6');

  /* ── Helpers for text-block sync ───────────────────────────── */
  function highlightTextToken(cls, idx, on) {
    const span = document.querySelector(`.${cls}[data-idx="${idx}"]`);
    if (!span) return;
    span.style.backgroundColor = on ? 'rgba(231,76,60,0.18)' : '';
    span.style.color            = on ? '#c0392b' : '';
    span.style.fontWeight       = on ? '700' : '';
    span.style.borderRadius     = on ? '2px' : '';
  }

  /* ── Hover interactions ────────────────────────────────────── */
  function resetAll() {
    ePaths
      .attr('stroke', e => cScale(dispNorm(e)))
      .attr('opacity', 0.65)
      .attr('stroke-width', 1.5);
    srcNodes.select('circle').attr('fill', '#2c3e50').attr('r', 4);
    srcNodes.select('text').attr('fill', '#2c3e50').attr('font-weight', 'normal');
    tgtNodes.select('circle').attr('fill', '#2c3e50').attr('r', 4);
    tgtNodes.select('text').attr('fill', '#2c3e50').attr('font-weight', 'normal');
    // reset text block highlights
    document.querySelectorAll('.src-tok, .tgt-tok').forEach(s => {
      s.style.backgroundColor = '';
      s.style.color = '';
      s.style.fontWeight = '';
      s.style.borderRadius = '';
    });
    tip.style('opacity', '0');
  }

  ePaths
    .on('mouseover', function (event, d) {
      // dim all, then highlight this one
      ePaths.attr('stroke', '#dde1e7').attr('opacity', 0.12).attr('stroke-width', 1.5);
      d3.select(this)
        .attr('stroke', '#e74c3c').attr('opacity', 1).attr('stroke-width', 2.5);

      // source node
      srcNodes.filter((t, i) => i === d.src)
        .select('circle').attr('fill', '#e74c3c').attr('r', 6);
      srcNodes.filter((t, i) => i === d.src)
        .select('text').attr('fill', '#e74c3c').attr('font-weight', '700');

      // target node
      tgtNodes.filter((t, j) => j === d.tgt)
        .select('circle').attr('fill', '#e74c3c').attr('r', 6);
      tgtNodes.filter((t, j) => j === d.tgt)
        .select('text').attr('fill', '#e74c3c').attr('font-weight', '700');

      // text block highlights
      highlightTextToken('src-tok', d.src, true);
      highlightTextToken('tgt-tok', d.tgt, true);

      // tooltip
      const disp = Math.abs(d.src - d.tgt);
      tip.style('opacity', '1')
        .html(
          `<strong style="font-size:13px">${d.token}</strong><br>` +
          `<span style="opacity:.85;font-size:11px">` +
          `pos. ipotesto: ${d.src + 1} &nbsp;→&nbsp; pos. ipertesto: ${d.tgt + 1}<br>` +
          `spostamento: ${disp} ${disp === 1 ? 'posizione' : 'posizioni'}` +
          `</span>`
        )
        .style('left', (event.clientX + 14) + 'px')
        .style('top',  (event.clientY - 18) + 'px');
    })
    .on('mousemove', function (event) {
      tip.style('left', (event.clientX + 14) + 'px')
         .style('top',  (event.clientY - 18) + 'px');
    })
    .on('mouseout', resetAll);

  /* ── Drag-to-scroll on the wrapper ────────────────────────── */
  const wrapper = document.getElementById('anag-wrapper');
  let isDragging = false, startX = 0, scrollLeft = 0;
  wrapper.addEventListener('mousedown', e => {
    isDragging = true;
    startX = e.pageX - wrapper.offsetLeft;
    scrollLeft = wrapper.scrollLeft;
  });
  wrapper.addEventListener('mouseleave', () => { isDragging = false; });
  wrapper.addEventListener('mouseup',    () => { isDragging = false; });
  wrapper.addEventListener('mousemove',  e => {
    if (!isDragging) return;
    e.preventDefault();
    wrapper.scrollLeft = scrollLeft - (e.pageX - wrapper.offsetLeft - startX);
  });

  /* ── Clean up tooltip on unload ────────────────────────────── */
  window.addEventListener('beforeunload', () => tip.remove());
})();