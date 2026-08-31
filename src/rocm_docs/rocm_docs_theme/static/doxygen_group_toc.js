// Scrollspy for Doxygen group sidebar anchors.
//
// The doxygen_group_toc extension injects a nested list of Doxygen group
// links into the left sidebar, each pointing at an in-page anchor such as
// "functions.html#tagesmidimmstatistics". This script highlights the group
// that the reader is currently viewing, reusing the theme's own active
// styling ("current active" classes) so it looks like a selected page entry.
//
// Design notes:
//   * Group anchors are used directly as position markers. Their in-page
//     section nesting is inconsistent (some groups render as their own
//     <section>, at least one renders as a bare <span> under the page root),
//     so climbing to a containing <section> is unreliable. The anchor element
//     itself is a uniform, dependable marker.
//   * The sidebar order (from the Doxygen XML index) does not match the order
//     groups render on the page, so markers are sorted by actual document
//     position before being used for scroll comparisons.
//   * Highlighting is driven by live scroll position rather than an
//     IntersectionObserver, whose first callback can race the browser's
//     initial hash jump and latch onto the top of the page.
(function () {
  "use strict";

  // How far below the viewport top the "active" reference line sits, in px.
  var ACTIVE_OFFSET = 120;

  function init() {
    var navLinks = Array.prototype.slice.call(
      document.querySelectorAll("li.doxygen-group > a.reference.internal")
    );
    if (navLinks.length === 0) {
      return;
    }

    // Build markers: {li, top} for every group anchor present on this page.
    var markers = [];
    navLinks.forEach(function (link) {
      var href = link.getAttribute("href") || "";
      var hashIndex = href.indexOf("#");
      if (hashIndex === -1) {
        return;
      }
      var anchor = href.slice(hashIndex + 1);
      var target = anchor ? document.getElementById(anchor) : null;
      if (!target) {
        return;
      }
      markers.push({ li: link.parentElement, el: target, top: 0 });
    });

    if (markers.length === 0) {
      return;
    }

    function absoluteTop(el) {
      return el.getBoundingClientRect().top + window.pageYOffset;
    }

    function recomputePositions() {
      markers.forEach(function (m) {
        m.top = absoluteTop(m.el);
      });
      // Sort by real document position; sidebar order differs from page order.
      markers.sort(function (a, b) {
        return a.top - b.top;
      });
    }

    var currentLi = null;
    function setActive(li) {
      if (li === currentLi) {
        return;
      }
      if (currentLi) {
        currentLi.classList.remove("current", "active");
      }
      if (li) {
        li.classList.add("current", "active");
      }
      currentLi = li;
    }

    function update() {
      var line = window.pageYOffset + ACTIVE_OFFSET;
      // Active group = the last marker whose start is at or above the line.
      var active = markers[0];
      for (var i = 0; i < markers.length; i++) {
        if (markers[i].top <= line) {
          active = markers[i];
        } else {
          break;
        }
      }
      setActive(active.li);
    }

    var ticking = false;
    function onScroll() {
      if (ticking) {
        return;
      }
      ticking = true;
      window.requestAnimationFrame(function () {
        update();
        ticking = false;
      });
    }

    recomputePositions();
    update();

    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", function () {
      recomputePositions();
      update();
    });
    window.addEventListener("hashchange", function () {
      // Positions are stable; the browser has already scrolled to the hash.
      window.requestAnimationFrame(update);
    });

    // The browser jumps to an initial hash (e.g. a function anchor) after this
    // script runs; recompute once layout has settled so the first highlight is
    // correct rather than latched to the top of the page.
    window.addEventListener("load", function () {
      recomputePositions();
      update();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
