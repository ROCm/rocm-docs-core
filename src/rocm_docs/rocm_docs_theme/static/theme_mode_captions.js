(function () {
    "use strict";

    function modifyThemeModeCaptions() {
        const themeSwitchButtons = document.getElementsByClassName(
            "theme-switch-button"
        );
        for (let i = 0; i < themeSwitchButtons.length; i++) {
            themeSwitchButtons[i].setAttribute(
                "data-bs-original-title",
                document.documentElement.dataset.mode
            );
        }
    }

    function addModeListener() {
        const btn = document.getElementsByClassName(
            "theme-switch-button"
        )[0];
        if (btn) {
            btn.addEventListener("click", modifyThemeModeCaptions);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", addModeListener);
    } else {
        addModeListener();
    }
})();
