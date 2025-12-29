// HTMX Preload Extension - 预加载优化
(function() {
    htmx.defineExtension('preload', {
        onEvent: function(name, evt) {
            if (name === 'htmx:afterProcessNode') {
                const elt = evt.detail.elt;
                // 为所有带 preload 属性的链接添加预加载
                if (elt.querySelectorAll) {
                    elt.querySelectorAll('[preload]').forEach(function(link) {
                        addPreloadListeners(link);
                    });
                }
            }
        }
    });

    function addPreloadListeners(element) {
        const trigger = element.getAttribute('preload') || 'mouseenter';

        element.addEventListener(trigger, function() {
            preloadElement(element);
        }, { once: true });
    }

    function preloadElement(element) {
        const href = element.getAttribute('href') || element.getAttribute('hx-get');
        if (!href || element.dataset.preloaded) return;

        element.dataset.preloaded = 'true';

        fetch(href, {
            method: 'GET',
            credentials: 'same-origin',
            headers: { 'HX-Preload': 'true' }
        }).catch(function() {});
    }
})();
