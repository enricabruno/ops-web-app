document.addEventListener('DOMContentLoaded', function () {
    function initEvidencePopover(btn, triggerValue, extraOptions) {
        var options = Object.assign({
            html: true,
            sanitize: false,
            trigger: triggerValue,
            placement: btn.dataset.bsPlacement || 'top',
            customClass: 'evidence-popover',
            content: function () {
                var src = document.getElementById(btn.dataset.provSource);
                return src ? src.innerHTML : '';
            },
        }, extraOptions || {});
        return new bootstrap.Popover(btn, options);
    }

    var instancePopovers = [];

    document.querySelectorAll('.evidence-arm-icon-btn').forEach(function (btn) {
        var popover = initEvidencePopover(btn, 'click');
        btn.addEventListener('click', function () {
            if (document.activeElement !== btn) btn.focus();
        });
        btn.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') popover.hide();
        });
        btn.addEventListener('show.bs.popover', function () {
            instancePopovers.forEach(function (p) { if (p !== popover) p.hide(); });
        });
        instancePopovers.push(popover);
    });
});
