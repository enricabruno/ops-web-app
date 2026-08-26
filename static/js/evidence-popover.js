document.addEventListener('DOMContentLoaded', function () {
    function initEvidencePopover(btn, triggerValue, extraOptions) {
        var options = Object.assign({
            html: true,
            sanitize: false,
            trigger: triggerValue,
            placement: 'top',
            customClass: 'evidence-popover',
            content: function () {
                var src = document.getElementById(btn.dataset.provSource);
                return src ? src.innerHTML : '';
            },
        }, extraOptions || {});
        return new bootstrap.Popover(btn, options);
    }

    var categoryPopovers = [];
    var instancePopovers = [];

    document.querySelectorAll('.evidence-info-badge').forEach(function (btn) {
        var popover = initEvidencePopover(btn, 'hover focus', { delay: { show: 150, hide: 100 } });
        btn.addEventListener('show.bs.popover', function () {
            instancePopovers.forEach(function (p) { p.hide(); });
        });
        categoryPopovers.push(popover);
    });

    document.querySelectorAll('button.evidence-arm-line').forEach(function (btn) {
        var popover = initEvidencePopover(btn, 'hover focus');
        btn.addEventListener('click', function () {
            if (document.activeElement !== btn) btn.focus();
        });
        btn.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') popover.hide();
        });
        btn.addEventListener('show.bs.popover', function () {
            categoryPopovers.forEach(function (p) { p.hide(); });
        });
        instancePopovers.push(popover);
    });
});
