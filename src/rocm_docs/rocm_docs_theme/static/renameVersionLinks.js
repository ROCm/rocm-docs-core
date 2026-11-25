(function () {
    "use strict";

    function renameVersionLinks() {
        document
            .querySelectorAll("div.rst-other-versions dl:first-child a")
            .forEach((el) => {
                const text = el.textContent;
                const versionRegEx = /^.*((?:[0-9]+\.){2}[0-9]+).*$/g;
                if (versionRegEx.test(text)) {
                    el.textContent = text.replace(versionRegEx, "$1");
                }
            });
    }

    function waitForSelector(selector, callback, backoff = 100, max = 15) {
        let tries = 0;
        const waitInterval = setInterval(() => {
            if (document.querySelector(selector)) {
                callback();
                clearInterval(waitInterval);
            } else if (tries++ > max) {
                clearInterval(waitInterval);
            }
        }, backoff);
    }

    function init() {
        waitForSelector("div.rst-versions", renameVersionLinks);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
