// Upgrade banner links marked with `data-rocm-banner-latest-link` so they point
// at the same page on the latest version instead of a fixed docs root.
//
// The built-in "old version" / release-candidate / development banners (see
// theme._update_banner) ship a link with a fixed `.../en/latest/` href as a
// no-JS fallback. ROCm docs are served by Read the Docs under
// `.../en/<version>/<page>`, so when JS runs we rewrite the href to the same
// <page> under `latest`, preserving the project prefix. Missing pages fall back
// to Read the Docs' own 404 handling for the latest version.
//
// Only links carrying the `data-rocm-banner-latest-link` attribute are touched,
// so a project that overrides `announcement` with its own link is left alone
// unless it opts in by adding the attribute.

(function () {
    function matchingLatestUrl(loc) {
        const match = loc.pathname.match(/^(.*\/en\/)[^/]+(\/.*)?$/);
        if (!match) {
            return null;
        }
        const pagePath = match[2] || "/";
        return loc.origin + match[1] + "latest" + pagePath + loc.hash;
    }

    function rewriteBannerLatestLinks() {
        const url = matchingLatestUrl(window.location);
        if (!url) {
            return;
        }
        const links = document.querySelectorAll(
            "[data-rocm-banner-latest-link]"
        );
        links.forEach((link) => {
            link.href = url;
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded", rewriteBannerLatestLinks
        );
    } else {
        rewriteBannerLatestLinks();
    }
})();
