// The "old version" announcement banner (see theme._update_banner) links to a
// fixed docs root, so clicking it drops the reader at the top of the latest
// docs instead of the page they were reading. ROCm docs are served by Read the
// Docs under `.../en/<version>/<page>`, so rewrite the banner link to the same
// <page> under `latest`, preserving the project prefix. Missing pages fall back
// to Read the Docs' own 404 handling for the latest version.

(function () {
    function matchingLatestUrl(loc) {
        const match = loc.pathname.match(/^(.*\/en\/)[^/]+(\/.*)?$/);
        if (!match) {
            return null;
        }
        const pagePath = match[2] || "/";
        return loc.origin + match[1] + "latest" + pagePath + loc.hash;
    }

    function fixBannerLink() {
        const link = document.getElementById("rocm-banner");
        if (!link) {
            return;
        }
        const url = matchingLatestUrl(window.location);
        if (url) {
            link.href = url;
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", fixBannerLink);
    } else {
        fixBannerLink();
    }
})();
