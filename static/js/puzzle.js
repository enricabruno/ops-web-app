/* puzzle.js — Genera la fila "OPS!" di 6 tessere SVG con incastri a forma di puzzle.*/

(function () {
  var cfgEl = document.getElementById('puzzle-config');
  var word = (cfgEl && JSON.parse(cfgEl.textContent).word) || 'OPS!';
  var letters = word.split('');

  var container = document.getElementById('puzzleContainer');
  if (!container) return;

  var SVGNS = 'http://www.w3.org/2000/svg';

  /* Pattern dei lati. Invariante: tiles[N].right e tiles[N+1].left
     sono sempre opposti (bump↔concave) → le tessere combaciano. */
  var tilePatterns = [
    { top: 'bump',    right: 'bump', bottom: 'concave', left: 'flat'    }, // O
    { top: 'concave', right: 'bump', bottom: 'bump',    left: 'concave' }, // P
    { top: 'bump',    right: 'bump', bottom: 'concave', left: 'concave' }, // L
    { top: 'concave', right: 'bump', bottom: 'bump',    left: 'concave' }, // E
    { top: 'bump',    right: 'bump', bottom: 'concave', left: 'concave' }, // P
    { top: 'concave', right: 'flat', bottom: 'bump',    left: 'concave' }  // O
  ];

  /* Curva canonica del lato TOP (0,0)→(100,0).
     dir = -1 → bump (esce, y negativi); dir = +1 → concave. */
  function edgeCommands(kind) {
    if (kind === 'flat') {
      return [{ c: 'L', p: [[100, 0]] }];
    }
    var d = kind === 'bump' ? -1 : 1;
    return [
      { c: 'L', p: [[35, 0]] },
      { c: 'C', p: [[35, 8 * d], [27.5, 12 * d], [27.5, 20 * d]] },
      { c: 'C', p: [[27.5, 30 * d], [72.5, 30 * d], [72.5, 20 * d]] },
      { c: 'C', p: [[72.5, 12 * d], [65, 8 * d], [65, 0]] },
      { c: 'L', p: [[100, 0]] }
    ];
  }

  /* Rotazioni attorno al centro corpo (50,50). La curva canonica
     va (0,0)→(100,0); ruotata diventa il lato corrispondente:
       top=0°, right=90°, bottom=180°, left=270°. */
  function rot(side, x, y) {
    switch (side) {
      case 'top':    return [x, y];
      case 'right':  return [100 - y, x];
      case 'bottom': return [100 - x, 100 - y];
      case 'left':   return [y, 100 - x];
    }
  }

  function fmt(n) {
    return (Math.round(n * 100) / 100).toString();
  }

  function buildPath(pattern) {
    // Punto di partenza: angolo (0,0) (= start del lato TOP).
    var d = 'M ' + fmt(0) + ',' + fmt(0);
    var sides = ['top', 'right', 'bottom', 'left'];
    for (var s = 0; s < sides.length; s++) {
      var side = sides[s];
      var cmds = edgeCommands(pattern[side]);
      for (var i = 0; i < cmds.length; i++) {
        var cmd = cmds[i];
        d += ' ' + cmd.c;
        for (var j = 0; j < cmd.p.length; j++) {
          var r = rot(side, cmd.p[j][0], cmd.p[j][1]);
          d += ' ' + fmt(r[0]) + ',' + fmt(r[1]);
        }
      }
    }
    return d + ' Z';
  }

  for (var n = 0; n < 6; n++) {
    var wrapper = document.createElement('div');
    wrapper.className = 'puzzle-piece-wrapper';
    wrapper.style.setProperty('--piece-index', String(n));
    wrapper.setAttribute('title', letters[n] || '');

    var svg = document.createElementNS(SVGNS, 'svg');
    svg.setAttribute('viewBox', '-20 -20 140 140');
    svg.setAttribute('aria-hidden', 'true');

    var path = document.createElementNS(SVGNS, 'path');
    path.setAttribute('d', buildPath(tilePatterns[n]));

    var text = document.createElementNS(SVGNS, 'text');
    text.setAttribute('x', '50');
    text.setAttribute('y', '50');
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('dominant-baseline', 'central');
    text.setAttribute('class', 'puzzle-letter');
    text.textContent = letters[n] || '';

    svg.appendChild(path);
    svg.appendChild(text);
    wrapper.appendChild(svg);
    container.appendChild(wrapper);
  }

  setTimeout(function () {
    container.classList.add('converged');
  }, 1500);
})();
