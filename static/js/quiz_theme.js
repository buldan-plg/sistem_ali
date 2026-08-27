/* ============================================================
   QUIZ THEME SWITCHER
   ============================================================ */
(function () {
  "use strict";

  var STORAGE_KEY = "quiz-theme";
  var root = document.documentElement;

  /* ---------- Helpers ---------- */

  function getSystemTheme() {
    return window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: light)").matches
      ? "light"
      : "dark";
  }

  function getStoredTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      return null;
    }
  }

  function storeTheme(theme) {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      /* ignore storage errors (incognito mode, etc) */
    }
  }

  /* ---------- Core Functions ---------- */

  function updateToggleUI(theme) {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;

    var isDark = theme === "dark";
    btn.setAttribute("aria-pressed", String(isDark));
    btn.setAttribute(
      "aria-label",
      isDark ? "Ganti ke light mode" : "Ganti ke dark mode",
    );

    if (!btn.hasAttribute("data-no-icon")) {
      btn.textContent = isDark ? "☀️" : "🌙";
    }
  }

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    updateToggleUI(theme);

    // Dispatch custom event untuk komponen lain (misal CodeMirror / Monaco Editor)
    document.dispatchEvent(
      new CustomEvent("quiz-theme-change", { detail: { theme: theme } }),
    );
  }

  function setTheme(theme, persist) {
    if (theme !== "dark" && theme !== "light") return;
    applyTheme(theme);
    if (persist !== false) storeTheme(theme);
  }

  function toggleTheme() {
    var current = root.getAttribute("data-theme") || getSystemTheme();
    setTheme(current === "dark" ? "light" : "dark");
  }

  function getTheme() {
    return root.getAttribute("data-theme") || getSystemTheme();
  }

  /* ---------- Initialization ---------- */

  function init() {
    var stored = getStoredTheme();
    var initial = stored || getSystemTheme();

    // Terapkan tema awal
    setTheme(initial, false);

    // Event Listener via Event Delegation (aman untuk dynamic DOM)
    document.addEventListener("click", function (e) {
      if (e.target && e.target.closest("#theme-toggle")) {
        toggleTheme();
      }
    });

    // Sync dengan OS Color Scheme jika user belum set preferensi manual
    if (window.matchMedia) {
      var mql = window.matchMedia("(prefers-color-scheme: light)");
      var handleSystemChange = function () {
        if (!getStoredTheme()) {
          setTheme(getSystemTheme(), false);
        }
      };

      if (mql.addEventListener) {
        mql.addEventListener("change", handleSystemChange);
      } else if (mql.addListener) {
        mql.addListener(handleSystemChange);
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  /* ---------- Public API ---------- */
  window.QuizTheme = {
    get: getTheme,
    set: function (theme) {
      setTheme(theme, true);
    },
    toggle: toggleTheme,
  };
})();
