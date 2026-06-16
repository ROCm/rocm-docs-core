/**
 * AMD Instinct Design System — scroll reveal + theme toggle helper
 *
 * - IntersectionObserver-based fade-in for .reveal elements
 * - .no-transitions helper for flicker-free theme switching
 */
(function () {
    "use strict";

    // Scroll reveal: observe .reveal elements, add .visible when in view
    if ("IntersectionObserver" in window) {
        var observer = new IntersectionObserver(
            function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("visible");
                    }
                });
            },
            { threshold: 0.1 }
        );

        document.querySelectorAll(".reveal").forEach(function (el) {
            observer.observe(el);
        });
    }

    // Auto-reveal sections on content pages for progressive disclosure
    var sections = document.querySelectorAll(".bd-main section[id]");
    if (sections.length > 0 && "IntersectionObserver" in window) {
        var sectionObserver = new IntersectionObserver(
            function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = "1";
                        entry.target.style.transform = "translateY(0)";
                    }
                });
            },
            { threshold: 0.05 }
        );

        sections.forEach(function (section, index) {
            if (index === 0) return;
            section.style.opacity = "0";
            section.style.transform = "translateY(12px)";
            section.style.transition =
                "opacity 0.5s ease " + Math.min(index * 0.05, 0.3) + "s, " +
                "transform 0.5s ease " + Math.min(index * 0.05, 0.3) + "s";
            sectionObserver.observe(section);
        });
    }
})();
