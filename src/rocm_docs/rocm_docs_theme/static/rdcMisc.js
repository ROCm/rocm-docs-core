(function () {
    "use strict";

    function cssWidth(el) {
        const style = getComputedStyle(el);
        const paddingX =
            parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
        const borderX =
            parseFloat(style.borderLeftWidth) +
            parseFloat(style.borderRightWidth);
        return el.getBoundingClientRect().width - paddingX - borderX;
    }

    function cssHeight(el) {
        const style = getComputedStyle(el);
        const paddingY =
            parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
        const borderY =
            parseFloat(style.borderTopWidth) +
            parseFloat(style.borderBottomWidth);
        return el.getBoundingClientRect().height - paddingY - borderY;
    }

    function lines(el) {
        const lineHeight = parseFloat(getComputedStyle(el).lineHeight);
        return Math.round(cssHeight(el) / lineHeight);
    }

    function adjustLength(item, container, factor, getTextItem) {
        const textItem = getTextItem(item);
        if (!textItem) {
            return;
        }

        function getMaxWidth(container, itm) {
            const startLines = lines(container);
            const initialText = itm.textContent;
            let maxWidth = cssWidth(container);
            while (lines(container) === startLines) {
                itm.textContent = itm.textContent + "\u200B.";
                if (cssWidth(container) > maxWidth) {
                    maxWidth = cssWidth(container);
                }
            }
            itm.textContent = initialText;
            return maxWidth;
        }

        const containerMaxWidth =
            container.__maxWidth || getMaxWidth(container, textItem);
        container.__maxWidth = containerMaxWidth;
        const fullText = item.__fullText || textItem.textContent;
        item.__fullText = fullText;
        textItem.textContent = fullText;
        if (lines(item) === 1 && cssWidth(item) < containerMaxWidth * factor) {
            return;
        }
        const words = fullText.split(/\s/);
        let newText = words[0];
        for (let i = 1; i < words.length; i++) {
            textItem.textContent = newText + " " + words[i] + "...";
            if (
                lines(item) === 1 &&
                cssWidth(item) < containerMaxWidth * factor
            ) {
                newText += " " + words[i];
            } else {
                break;
            }
        }
        newText += "...";
        textItem.textContent = newText;
    }

    function fixBreadcrumbItems() {
        const breadcrumbItems = document.querySelectorAll(
            "li.breadcrumb-item:not(.breadcrumb-home, .active)"
        );
        const breadcrumbBox = document.querySelector("ul.bd-breadcrumbs");
        if (!breadcrumbBox) {
            return;
        }
        breadcrumbBox.__maxWidth = 0;
        breadcrumbItems.forEach((item) => {
            adjustLength(
                item,
                breadcrumbBox,
                0.82 * (breadcrumbItems.length <= 2 ? 1 : 0.5),
                (x) => x.querySelector(":scope > a")
            );
        });
        const activeItem = document.querySelector(
            "li.breadcrumb-item.active"
        );
        if (activeItem) {
            adjustLength(activeItem, breadcrumbBox, 0.95, (x) => x);
        }
        breadcrumbBox.__maxWidth = 0;
    }

    function init() {
        if (window.ResizeObserver) {
            document.body.addEventListener("bodyresize", (event) => {
                const { contentRect } = event.detail;
                const { width } = contentRect;
                if (
                    window.prevWidth &&
                    window.prevWidth > 960 &&
                    width < 960
                ) {
                    const primaryToggle = document.querySelector(
                        "input#__primary"
                    );
                    if (primaryToggle) {
                        primaryToggle.checked = false;
                    }
                }
                window.prevWidth = width;
                fixBreadcrumbItems();
            });

            const onResizeCallback = (() => {
                let initial = true;
                let timeout;
                return (entries) => {
                    if (initial) {
                        initial = false;
                        return;
                    }
                    clearTimeout(timeout);
                    timeout = setTimeout(() => {
                        for (const entry of entries) {
                            const event = new CustomEvent("bodyresize", {
                                detail: entry,
                            });
                            entry.target.dispatchEvent(event);
                        }
                    }, 200);
                };
            })();

            window.resizeObserver = new ResizeObserver(onResizeCallback);
            window.resizeObserver.observe(document.body);
        } else {
            console.error("ResizeObserver not supported.");
        }
        fixBreadcrumbItems();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
