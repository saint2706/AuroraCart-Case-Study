/*
 * AuroraCart dashboard — browser environment detection.
 *
 * Dash auto-loads everything in assets/. This file does three jobs:
 *
 *   1. Measures the real browser (viewport tier, pointer type, engine, feature
 *      support) and stamps the result onto <html> as `env-*` classes plus a few
 *      CSS custom properties, so style.css can target things a media query
 *      cannot express — touch pointers, iOS Safari's viewport quirks, the
 *      absence of a feature we would otherwise rely on.
 *   2. Exposes `window.auroracartEnv.profile()` so a Dash clientside callback
 *      can seed the `env-store` on page load.
 *   3. Watches for resize / orientation / pointer changes and pushes an updated
 *      profile into that same store, but ONLY when something the server would
 *      actually render differently has changed — so a slow drag of a desktop
 *      window does not fire a callback per pixel.
 *
 * Everything here is progressive enhancement. With JavaScript disabled the
 * dashboard still lays out correctly from the CSS media queries alone; the
 * server just falls back to its default (desktop-shaped) profile.
 */
(function () {
  "use strict";

  /* Bootstrap 5 grid tiers. Mirrors TIERS in responsive.py — keep both in sync. */
  var TIERS = [
    ["xxl", 1400],
    ["xl", 1200],
    ["lg", 992],
    ["md", 768],
    ["sm", 576],
    ["xs", 0]
  ];

  var STORE_ID = "env-store";
  var RESIZE_DEBOUNCE_MS = 150;

  var lastSignature = null;
  var appliedClasses = [];
  var resizeTimer = null;

  /* ------------------------------------------------------------- detection */

  function mq(query) {
    try {
      return !!(window.matchMedia && window.matchMedia(query).matches);
    } catch (err) {
      return false;
    }
  }

  function cssSupports(prop, value) {
    try {
      return !!(window.CSS && window.CSS.supports && window.CSS.supports(prop, value));
    } catch (err) {
      return false;
    }
  }

  /* visualViewport is the only accurate read on mobile Safari/Chrome once the
     URL bar collapses or the on-screen keyboard opens; innerWidth is the
     fallback and clientWidth the fallback's fallback. */
  function viewportSize() {
    var vv = window.visualViewport;
    var width = (vv && vv.width) || window.innerWidth ||
      (document.documentElement && document.documentElement.clientWidth) || 1024;
    var height = (vv && vv.height) || window.innerHeight ||
      (document.documentElement && document.documentElement.clientHeight) || 768;
    return { width: Math.round(width), height: Math.round(height) };
  }

  function tierFor(width) {
    for (var i = 0; i < TIERS.length; i++) {
      if (width >= TIERS[i][1]) {
        return TIERS[i][0];
      }
    }
    return "xs";
  }

  function platformOf(ua) {
    var hinted = (navigator.userAgentData && navigator.userAgentData.platform) || "";
    var haystack = (hinted + " " + ua + " " + (navigator.platform || "")).toLowerCase();
    var touchPoints = navigator.maxTouchPoints || 0;

    if (/iphone|ipod|ipad/.test(haystack)) return "ios";
    /* iPadOS 13+ identifies itself as a Mac; the touch-point count is the tell. */
    if (/mac/.test(haystack) && touchPoints > 1) return "ios";
    if (/android/.test(haystack)) return "android";
    if (/mac/.test(haystack)) return "mac";
    if (/win/.test(haystack)) return "windows";
    if (/linux|cros|x11/.test(haystack)) return "linux";
    return "unknown";
  }

  /* Order matters: Edge, Opera and Samsung Internet all carry "Chrome" in their
     UA string, and every iOS browser carries "Safari". Most specific first. */
  function browserOf(ua) {
    if (/Edg[A-Z]?\//.test(ua)) return "edge";
    if (/OPR\/|Opera[ /]/.test(ua)) return "opera";
    if (/SamsungBrowser/.test(ua)) return "samsung";
    if (/Firefox\/|FxiOS\//.test(ua)) return "firefox";
    if (/CriOS\/|Chrome\/|Chromium\//.test(ua)) return "chrome";
    if (/Safari\//.test(ua)) return "safari";
    return "unknown";
  }

  /* The engine, not the brand — this is what CSS bug workarounds key off.
     Every browser on iOS is WebKit underneath regardless of its badge. */
  function engineOf(ua, platform) {
    if (platform === "ios") return "webkit";
    if (/Firefox\/|FxiOS\/|Gecko\/\d/.test(ua)) return "gecko";
    if (/Edg[A-Z]?\/|OPR\/|SamsungBrowser|Chrome\/|Chromium\//.test(ua)) return "blink";
    if (/Safari\//.test(ua) && /Apple/.test(navigator.vendor || "")) return "webkit";
    return "unknown";
  }

  /* Feature probes for the handful of things this dashboard's CSS would
     otherwise silently depend on. Each one has an explicit fallback in
     style.css, keyed off the matching `no-*` class. */
  function featureSupport() {
    return {
      dvh: cssSupports("height", "100dvh"),
      clamp: cssSupports("width", "clamp(1px, 2vw, 3px)"),
      flex_gap: cssSupports("gap", "1px"),
      safe_area: cssSupports("padding", "env(safe-area-inset-bottom)"),
      scrollbar_gutter: cssSupports("scrollbar-gutter", "stable"),
      overscroll: cssSupports("overscroll-behavior", "contain")
    };
  }

  function profile() {
    var ua = navigator.userAgent || "";
    var size = viewportSize();
    var platform = platformOf(ua);
    var touch = (navigator.maxTouchPoints || 0) > 0 || "ontouchstart" in window;

    return {
      tier: tierFor(size.width),
      width: size.width,
      height: size.height,
      orientation: size.height >= size.width ? "portrait" : "landscape",
      touch: touch,
      /* `pointer: coarse` is the standards-track question — "is the primary
         pointer imprecise?" — and is what tap-target sizing should key off,
         not the mere presence of a touchscreen on a laptop. */
      coarse: mq("(pointer: coarse)"),
      hover: mq("(hover: hover)") && mq("(pointer: fine)"),
      dpr: Math.round((window.devicePixelRatio || 1) * 100) / 100,
      reduced_motion: mq("(prefers-reduced-motion: reduce)"),
      platform: platform,
      browser: browserOf(ua),
      engine: engineOf(ua, platform),
      standalone: mq("(display-mode: standalone)") || navigator.standalone === true,
      supports: featureSupport()
    };
  }

  /* ---------------------------------------------------------------- apply */

  function classesFor(p) {
    var classes = [
      "env-" + p.tier,
      "env-" + p.platform,
      "env-" + p.browser,
      "env-" + p.engine,
      "env-" + p.orientation,
      p.coarse || (p.touch && !p.hover) ? "env-touch" : "env-mouse",
      p.hover ? "env-hover" : "env-nohover"
    ];
    if (p.tier === "xs" || p.tier === "sm") classes.push("env-narrow");
    if (p.tier === "xs" || p.tier === "sm" || p.tier === "md") classes.push("env-compact");
    if (p.standalone) classes.push("env-standalone");
    if (p.reduced_motion) classes.push("env-reduced-motion");

    Object.keys(p.supports).forEach(function (key) {
      if (!p.supports[key]) classes.push("no-" + key.replace(/_/g, "-"));
    });
    return classes;
  }

  function applyEnv(p) {
    var root = document.documentElement;
    if (!root) return;

    var next = classesFor(p);
    var keep = {};
    next.forEach(function (name) {
      keep[name] = true;
    });

    /* Drop every stale "env-" or "no-" class, including the provisional ones
       the inline snippet in <head> stamps before first paint. */
    Array.prototype.slice.call(root.classList).forEach(function (name) {
      if ((name.indexOf("env-") === 0 || name.indexOf("no-") === 0) && !keep[name]) {
        root.classList.remove(name);
      }
    });
    next.forEach(function (name) {
      root.classList.add(name);
    });
    appliedClasses = next;

    /* The classic iOS 100vh problem: `vh` is measured against the *expanded*
       viewport, so a 100vh element sits partly under the collapsing URL bar.
       --vh is the real, current 1% and style.css prefers it over `vh` wherever
       `dvh` is unavailable. */
    root.style.setProperty("--vh", p.height / 100 + "px");
    root.style.setProperty("--env-width", p.width + "px");
  }

  /* ---------------------------------------------------------------- store */

  /* Only these fields change what the server renders. Width alone does not —
     Plotly graphs are `responsive: true` and resize themselves in the browser —
     so resizing within a tier must not trigger a server round-trip. */
  function signatureOf(p) {
    return [
      p.tier, p.orientation, p.touch, p.coarse, p.hover,
      p.platform, p.browser, p.engine, p.standalone, p.reduced_motion
    ].join("|");
  }

  function pushToStore(p) {
    var dc = window.dash_clientside;
    if (!dc || typeof dc.set_props !== "function") return false;
    try {
      dc.set_props(STORE_ID, { data: p });
      return true;
    } catch (err) {
      return false;
    }
  }

  function refresh(force) {
    var p = profile();
    applyEnv(p);

    var signature = signatureOf(p);
    if (!force && signature === lastSignature) return;
    lastSignature = signature;
    pushToStore(p);
  }

  function onResize() {
    if (resizeTimer) window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(function () {
      resizeTimer = null;
      refresh(false);
    }, RESIZE_DEBOUNCE_MS);
  }

  /* ----------------------------------------------------------- public API */

  window.auroracartEnv = {
    /* Called by the Dash clientside callback that seeds env-store on load. */
    profile: function () {
      var p = profile();
      applyEnv(p);
      lastSignature = signatureOf(p);
      return p;
    },
    refresh: function () {
      refresh(true);
    }
  };

  /* Stamp the classes as early as possible so styling never flashes, then
     again on DOMContentLoaded in case this ran before <html> was styled. */
  applyEnv(profile());
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      refresh(true);
    });
  }

  window.addEventListener("resize", onResize, { passive: true });
  window.addEventListener("orientationchange", onResize, { passive: true });
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", onResize, { passive: true });
  }

  /* Pointer type genuinely changes mid-session: a Surface being undocked, an
     iPad gaining a trackpad, a desktop switching to a touch monitor. */
  ["(pointer: coarse)", "(hover: hover)", "(prefers-reduced-motion: reduce)",
   "(display-mode: standalone)"].forEach(function (query) {
    try {
      var list = window.matchMedia(query);
      if (list.addEventListener) {
        list.addEventListener("change", onResize);
      } else if (list.addListener) {
        list.addListener(onResize);  /* Safari < 14 */
      }
    } catch (err) { /* matchMedia unavailable — CSS fallbacks still apply */ }
  });
})();
