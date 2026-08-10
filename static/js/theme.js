(function () {
  "use strict";

  var STORAGE_KEY = "theme";
  var MODES = ["light", "dark", "system"];
  var DEFAULT_MODE = "system";

  var currentMode = DEFAULT_MODE;

  function readStoredMode() {
    var stored;
    try {
      stored = window.localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      /* Storage unavailable (private browsing, disabled): use system for the session. */
      return DEFAULT_MODE;
    }
    if (MODES.indexOf(stored) !== -1) {
      return stored;
    }
    return DEFAULT_MODE;
  }

  function persistMode(mode) {
    try {
      window.localStorage.setItem(STORAGE_KEY, mode);
    } catch (e) {
      /* Failed write: keep the session-only mode; theme still applies. */
    }
  }

  function isDark(mode) {
    return (
      mode === "dark" ||
      (mode === "system" &&
        window.matchMedia("(prefers-color-scheme: dark)").matches)
    );
  }

  function apply() {
    document.documentElement.dataset.theme = isDark(currentMode)
      ? "dark"
      : "light";
  }

  function syncIcons() {
    var icons = document.querySelectorAll("[data-theme-icon]");
    for (var i = 0; i < icons.length; i++) {
      icons[i].classList.toggle(
        "hidden",
        icons[i].getAttribute("data-theme-icon") !== currentMode
      );
    }
  }

  function nextMode(mode) {
    if (mode === "light") {
      return "dark";
    }
    if (mode === "dark") {
      return "system";
    }
    return "light";
  }

  function init() {
    currentMode = readStoredMode();
    apply();
    syncIcons();

    var toggle = document.querySelector("[data-theme-toggle]");
    if (toggle) {
      toggle.addEventListener("click", function () {
        currentMode = nextMode(currentMode);
        persistMode(currentMode);
        apply();
        syncIcons();
      });
    }

    var mq = window.matchMedia("(prefers-color-scheme: dark)");
    function onPrefersColorSchemeChange() {
      if (currentMode === "system") {
        apply();
      }
    }
    if (mq.addEventListener) {
      mq.addEventListener("change", onPrefersColorSchemeChange);
    } else if (mq.addListener) {
      mq.addListener(onPrefersColorSchemeChange); /* legacy Safari */
    }
  }

  init();
})();
