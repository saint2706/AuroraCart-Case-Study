/*
 * AuroraCart dashboard — horizontal scroll affordances.
 *
 * The data tables beneath each chart scroll inside their own box rather than
 * widening the page. On a phone that means the rightmost column can sit off the
 * edge with nothing to say so — the table just looks truncated.
 *
 * This marks any table scroller that is actually overflowing with
 * `is-scrollable`, and clears the mark once it fits (or once the user has
 * scrolled to the end). style.css turns that into a fade at the right edge plus
 * a one-line caption. The mark is only ever applied when the measurement says
 * the content really is wider than its box, so the hint can never lie.
 */
(function () {
  "use strict";

  var SCROLLER = ".table-wrap .dash-spreadsheet-container, .table-wrap .dash-table-container";
  var SLACK = 2;  /* sub-pixel layout rounding */

  function mark(el) {
    var overflowing = el.scrollWidth > el.clientWidth + SLACK;
    var atEnd = el.scrollLeft + el.clientWidth >= el.scrollWidth - SLACK;
    el.classList.toggle("is-scrollable", overflowing);
    el.classList.toggle("is-scrolled-end", overflowing && atEnd);

    /* Mark the wrapper too. CSS `:has()` could select it from here, but it is
       still missing on older Safari and Firefox — and this hint is exactly the
       kind of thing that must not depend on a recent selector. */
    var wrap = el.closest && el.closest(".table-wrap");
    if (wrap) {
      wrap.classList.toggle("has-overflow", overflowing && !atEnd);
    }

    if (overflowing && !el.dataset.scrollBound) {
      el.dataset.scrollBound = "1";
      el.addEventListener("scroll", function () { mark(el); }, { passive: true });
    }
  }

  function scan() {
    try {
      document.querySelectorAll(SCROLLER).forEach(mark);
    } catch (err) { /* nothing to hint at is not an error */ }
  }

  /* Tab switches and filter changes replace the tables wholesale, so re-measure
     whenever the rendered content changes rather than only on load. */
  var pending = null;
  function scheduleScan() {
    if (pending) window.clearTimeout(pending);
    pending = window.setTimeout(function () {
      pending = null;
      scan();
    }, 120);
  }

  function start() {
    scan();
    var root = document.getElementById("tab-content") || document.body;
    if (window.MutationObserver) {
      new MutationObserver(scheduleScan).observe(root, { childList: true, subtree: true });
    }
    window.addEventListener("resize", scheduleScan, { passive: true });
    window.addEventListener("orientationchange", scheduleScan, { passive: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
