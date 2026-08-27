/* /hierarchy — dendrogramma radiale con hierarchical edge bundling (Holten
   2006) su skos:broader, con skos:related come corde bundlate opzionali.
   D3 v7 e' gia' caricato da base.html. */

(function () {
    var DEFAULT_SCHEME = 'https://w3id.org/desmos/FormalConstraintScheme';

    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    var tooltipEl = null;
    function getTooltip() {
        if (!tooltipEl) {
            tooltipEl = document.createElement('div');
            tooltipEl.className = 'ops-tooltip';
            tooltipEl.setAttribute('role', 'tooltip');
            tooltipEl.hidden = true;
            document.body.appendChild(tooltipEl);
        }
        return tooltipEl;
    }

    function showTooltip(event, nodeData) {
        var el = getTooltip();
        var html = '<strong>' + escapeHtml(nodeData.name || '') + '</strong>';
        if (nodeData.en) html += ' <em>(' + escapeHtml(nodeData.en) + ')</em>';
        html += '<br><code>' + escapeHtml(nodeData.uri || '') + '</code>';
        el.innerHTML = html;
        el.hidden = false;

        var x, y;
        if (event.type === 'focus') {
            var r = event.currentTarget.getBoundingClientRect();
            x = r.right;
            y = r.top;
        } else {
            x = event.clientX;
            y = event.clientY;
        }
        el.style.left = (x + 12) + 'px';
        el.style.top = y + 'px';
    }

    function hideTooltip() {
        if (tooltipEl) tooltipEl.hidden = true;
    }

    function pairKey(a, b) {
        return a < b ? a + '|' + b : b + '|' + a;
    }

    /* Disegna il dendrogramma dentro `container` a partire dall'albero
       {scheme,label,children:[...]} restituito da /api/hierarchy. Ritorna un
       piccolo handle per mostrare/nascondere le corde related senza ridisegnare. */
    function renderHierarchy(container, data, opts) {
        opts = opts || {};
        var showRelated = opts.showRelated !== false;

        container.innerHTML = '';
        if (!data || !data.children) return null;

        var rect = container.getBoundingClientRect();
        var size = Math.max(360, Math.min(rect.width || 720, 900));
        var radius = size / 2 - 100; // margine per le etichette esterne

        var root = d3.hierarchy({
            uri: data.scheme,
            name: data.label,
            en: data.label,
            related: [],
            children: data.children,
        });

        var cluster = d3.cluster()
            .size([360, radius])
            .separation(function (a, b) {
                return (a.parent === b.parent ? 1 : 2.4) / (a.depth || 1);
            });
        cluster(root);

        var byUri = new Map(root.descendants().map(function (d) { return [d.data.uri, d]; }));
        var seenPairs = new Set();
        var bundleLinks = [];
        root.descendants().forEach(function (d) {
            (d.data.related || []).forEach(function (relUri) {
                var target = byUri.get(relUri);
                if (!target || target === d) return;
                var key = pairKey(d.data.uri, relUri);
                if (seenPairs.has(key)) return;
                seenPairs.add(key);
                bundleLinks.push({ source: d, target: target, key: key });
            });
        });

        var svg = d3.select(container).append('svg')
            .attr('viewBox', [-size / 2, -size / 2, size, size])
            .attr('class', 'hierarchy-svg');

        var zoomLayer = svg.append('g');

        var zoomBehavior = d3.zoom()
            .scaleExtent([0.4, 6])
            .on('zoom', function (event) { zoomLayer.attr('transform', event.transform); });
        svg.call(zoomBehavior);

        var angle = function (d) { return (d.x / 180) * Math.PI; };
        var linkRadial = d3.linkRadial().angle(angle).radius(function (d) { return d.y; });
        var lineRadial = d3.lineRadial().curve(d3.curveBundle.beta(0.80)).angle(angle).radius(function (d) { return d.y; });

        var linkSel = zoomLayer.append('g')
            .attr('class', 'hierarchy-links')
            .attr('fill', 'none')
            .selectAll('path')
            .data(root.links())
            .join('path')
            .attr('class', 'hierarchy-link')
            .attr('d', linkRadial);

        var bundleGroup = zoomLayer.append('g')
            .attr('class', 'hierarchy-bundles')
            .attr('fill', 'none')
            .style('display', showRelated ? null : 'none');

        var bundleSel = bundleGroup.selectAll('path')
            .data(bundleLinks)
            .join('path')
            .attr('class', 'hierarchy-bundle')
            .attr('d', function (d) { return lineRadial(d.source.path(d.target)); });

        var nodeSel = zoomLayer.append('g')
            .attr('class', 'hierarchy-nodes')
            .selectAll('a')
            .data(root.descendants())
            .join('a')
            .attr('href', function (d) { return d.depth === 0 ? null : '/explain?uri=' + encodeURIComponent(d.data.uri); })
            .attr('class', function (d) {
                return 'hierarchy-node' +
                    (d.depth === 0 ? ' hierarchy-node--root' : '') +
                    (d.children ? ' hierarchy-node--internal' : ' hierarchy-node--leaf');
            })
            .attr('tabindex', function (d) { return d.depth === 0 ? null : '0'; })
            .attr('transform', function (d) {
                return d.depth === 0 ? 'translate(0,0)' : 'rotate(' + (d.x - 90) + ') translate(' + d.y + ',0)';
            });

        nodeSel.append('circle')
            .attr('r', function (d) { return d.depth === 0 ? 5 : (d.children ? 3.5 : 2.5); });

        nodeSel.append('text')
            .attr('class', 'hierarchy-label')
            .attr('dy', '0.31em')
            .attr('x', function (d) {
                if (d.depth === 0) return 0;
                return d.x < 180 ? 6 : -6;
            })
            .attr('text-anchor', function (d) {
                if (d.depth === 0) return 'middle';
                return d.x < 180 ? 'start' : 'end';
            })
            .attr('transform', function (d) {
                if (d.depth === 0) return null;
                return d.x >= 180 ? 'rotate(180)' : null;
            })
            .text(function (d) { return d.data.name; });

        function activate(d) {
            var activeUris = new Set(d.ancestors().concat(d.descendants()).map(function (n) { return n.data.uri; }));
            var activeBundleKeys = new Set();
            bundleLinks.forEach(function (bl) {
                if (bl.source === d || bl.target === d) activeBundleKeys.add(bl.key);
            });

            zoomLayer.classed('hierarchy-has-focus', true);
            nodeSel.classed('is-active', function (n) { return activeUris.has(n.data.uri); });
            linkSel.classed('is-active', function (l) {
                return activeUris.has(l.source.data.uri) && activeUris.has(l.target.data.uri);
            });
            bundleSel.classed('is-active', function (bl) { return activeBundleKeys.has(bl.key); });
        }

        function deactivate() {
            zoomLayer.classed('hierarchy-has-focus', false);
            nodeSel.classed('is-active', false);
            linkSel.classed('is-active', false);
            bundleSel.classed('is-active', false);
        }

        nodeSel
            .on('mouseenter', function (event, d) { activate(d); showTooltip(event, d.data); })
            .on('mousemove', function (event, d) { showTooltip(event, d.data); })
            .on('mouseleave', function () { deactivate(); hideTooltip(); })
            .on('focus', function (event, d) { activate(d); showTooltip(event, d.data); })
            .on('blur', function () { deactivate(); hideTooltip(); });

        return {
            setRelatedVisible: function (visible) {
                bundleGroup.style('display', visible ? null : 'none');
            },
        };
    }

    document.addEventListener('DOMContentLoaded', function () {
        var vizEl = document.getElementById('hierarchy-viz');
        var selectEl = document.getElementById('hierarchy-scheme-select');
        var toggleEl = document.getElementById('hierarchy-related-toggle');
        if (!vizEl || !selectEl || !toggleEl) return;

        var currentData = null;
        var currentViz = null;
        var resizeTimer = null;

        function loadAndRender(schemeUri) {
            fetch('/api/hierarchy?scheme=' + encodeURIComponent(schemeUri))
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    currentData = data;
                    currentViz = renderHierarchy(vizEl, data, { showRelated: toggleEl.checked });
                });
        }

        fetch('/api/schemes')
            .then(function (res) { return res.json(); })
            .then(function (schemes) {
                schemes.forEach(function (s) {
                    var opt = document.createElement('option');
                    opt.value = s.uri;
                    opt.textContent = s.label;
                    selectEl.appendChild(opt);
                });
                var hasDefault = schemes.some(function (s) { return s.uri === DEFAULT_SCHEME; });
                selectEl.value = hasDefault ? DEFAULT_SCHEME : (schemes[0] && schemes[0].uri);
                loadAndRender(selectEl.value);
            });

        selectEl.addEventListener('change', function () { loadAndRender(selectEl.value); });

        toggleEl.addEventListener('change', function () {
            if (currentViz) currentViz.setRelatedVisible(toggleEl.checked);
        });

        window.addEventListener('resize', function () {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function () {
                if (currentData) currentViz = renderHierarchy(vizEl, currentData, { showRelated: toggleEl.checked });
            }, 150);
        });
    });
})();
