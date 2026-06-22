/**
 * AMD Instinct Design System — scroll reveal helper
 *
 * IntersectionObserver-based progressive fade-in for content-page sections.
 * Respects prefers-reduced-motion: when the user asks for reduced motion,
 * sections render immediately with no animation.
 */
(function () {
    "use strict";

    const prefersReducedMotion =
        window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Auto-reveal sections on content pages for progressive disclosure
    const sections = document.querySelectorAll(".bd-main section[id]");
    if (
        !prefersReducedMotion &&
        sections.length > 0 &&
        "IntersectionObserver" in window
    ) {
        const sectionObserver = new IntersectionObserver(
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
