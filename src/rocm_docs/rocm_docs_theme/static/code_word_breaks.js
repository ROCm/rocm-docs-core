(function () {
    "use strict";

    function init() {
        const copy = async (element) => {
            return await navigator.clipboard.writeText(
                element.getAttribute("copydata")
            );
        };

        document.querySelectorAll(".table td code").forEach((el) => {
            const text = el.textContent;
            el.classList.add("hovertext");
            el.setAttribute("copydata", text);
            el.setAttribute("data-hover", "Click to copy.");
            const newText = text
                .replaceAll(/_([^\u200B])/g, "_\u200B$1")
                .replaceAll(/([a-z])([A-Z])/g, "$1\u200B$2");
            el.textContent = newText;
            el.addEventListener("click", (event) => {
                copy(event.target);
                event.target.setAttribute("data-hover", "Copied!");
                const onMouseLeave = () => {
                    event.target.setAttribute("data-hover", "Click to copy.");
                    event.target.removeEventListener(
                        "mouseleave",
                        onMouseLeave
                    );
                };
                event.target.addEventListener("mouseleave", onMouseLeave);
            });
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
