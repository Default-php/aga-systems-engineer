const { test } = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const SCRIPT = path.resolve(__dirname, "../../static/js/chat_widget.js");

function makeClassList(initial) {
  const classes = new Set(initial || []);
  return {
    contains: (c) => classes.has(c),
    toggle: (c, force) => {
      if (force === undefined) {
        if (classes.has(c)) {
          classes.delete(c);
        } else {
          classes.add(c);
        }
      } else if (force) {
        classes.add(c);
      } else {
        classes.delete(c);
      }
    },
    add: (c) => classes.add(c),
    remove: (c) => classes.delete(c),
  };
}

function makeElement(id) {
  const element = {
    id,
    listeners: {},
    attrs: {},
    classList: makeClassList(id === "chat-panel" ? ["hidden", "mt-2"] : []),
    addEventListener(event, fn) {
      this.listeners[event] = fn;
    },
    getAttribute(name) {
      if (id === "chat-widget" && name === "data-chat-url") {
        return "/chat/";
      }
      return this.attrs[name] || null;
    },
    setAttribute(name, value) {
      this.attrs[name] = value;
    },
    querySelector() {
      return { disabled: false };
    },
    focus() {
      this.focusCount = (this.focusCount || 0) + 1;
    },
  };
  return element;
}

// Controllable timer queue: the real widget schedules a 220ms close timeout,
// and each test decides when it fires (or whether it was cancelled).
function createTimers() {
  let queue = [];
  let id = 0;
  return {
    setTimeout(cb, ms) {
      queue.push({ id: ++id, cb, ms });
      return id;
    },
    clearTimeout(handle) {
      queue = queue.filter((t) => t.id !== handle);
    },
    runAll() {
      queue.splice(0).forEach((t) => t.cb());
    },
    pending() {
      return queue.length;
    },
  };
}

function loadWidget(timers) {
  const ids = [
    "chat-widget",
    "chat-open",
    "chat-close",
    "chat-panel",
    "chat-log",
    "chat-form",
    "chat-input",
  ];
  const elements = {};
  for (const id of ids) {
    elements[id] = makeElement(id);
  }
  globalThis.document = {
    getElementById(id) {
      return elements[id] || null;
    },
    querySelector() {
      return { getAttribute: () => "" };
    },
  };
  // Stub browser globals the widget may touch. The animation tests only call
  // setOpen (never fetch), but the stubs prevent a ReferenceError if the real
  // script ever calls fetch/window during init.
  globalThis.fetch = function () {
    return Promise.resolve({
      status: 200,
      json: function () {
        return Promise.resolve({ answer: "stub", sources: [] });
      },
    });
  };
  globalThis.window = {
    matchMedia: function () {
      return {
        matches: false,
        addEventListener: function () {},
        removeEventListener: function () {},
      };
    },
  };
  // rAF fires synchronously so the transition state stays assertable; timers
  // are routed to the controllable queue. Restore the real globals afterwards.
  const realRaf = globalThis.requestAnimationFrame;
  const realCancelRaf = globalThis.cancelAnimationFrame;
  const realSetTimeout = globalThis.setTimeout;
  const realClearTimeout = globalThis.clearTimeout;
  let rafCount = 0;
  globalThis.requestAnimationFrame = (cb) => {
    rafCount++;
    cb();
    return 0;
  };
  globalThis.cancelAnimationFrame = () => {};
  globalThis.setTimeout = (cb, ms) => timers.setTimeout(cb, ms);
  globalThis.clearTimeout = (handle) => timers.clearTimeout(handle);
  delete require.cache[require.resolve(SCRIPT)];
  require(SCRIPT);
  return {
    elements,
    rafCount: () => rafCount,
    restore() {
      globalThis.document = undefined;
      delete globalThis.fetch;
      delete globalThis.window;
      if (realRaf === undefined) {
        delete globalThis.requestAnimationFrame;
      } else {
        globalThis.requestAnimationFrame = realRaf;
      }
      if (realCancelRaf === undefined) {
        delete globalThis.cancelAnimationFrame;
      } else {
        globalThis.cancelAnimationFrame = realCancelRaf;
      }
      globalThis.setTimeout = realSetTimeout;
      globalThis.clearTimeout = realClearTimeout;
    },
  };
}

test("open: removes hidden, then adds is-open via rAF", () => {
  const timers = createTimers();
  const { elements, restore } = loadWidget(timers);
  try {
    const panel = elements["chat-panel"];
    const open = elements["chat-open"];
    assert.ok(panel.classList.contains("hidden"), "panel starts hidden");
    open.listeners.click();
    assert.ok(!panel.classList.contains("hidden"), "hidden removed first");
    assert.ok(panel.classList.contains("is-open"), "is-open added after rAF flush");
    assert.equal(open.attrs["aria-expanded"], "true", "aria-expanded syncs to true");
    assert.equal(elements["chat-input"].focusCount, 1, "input focused when panel opens");
  } finally {
    restore();
  }
});

test("close: removes is-open, then adds hidden after timeout", () => {
  const timers = createTimers();
  const { elements, restore } = loadWidget(timers);
  try {
    const panel = elements["chat-panel"];
    const open = elements["chat-open"];
    const close = elements["chat-close"];
    open.listeners.click(); // open
    close.listeners.click(); // close
    assert.ok(!panel.classList.contains("is-open"), "is-open removed immediately");
    assert.ok(!panel.classList.contains("hidden"), "hidden NOT added yet (wait for timeout)");
    assert.equal(open.attrs["aria-expanded"], "false", "aria-expanded syncs to false");
    timers.runAll();
    assert.ok(panel.classList.contains("hidden"), "hidden added after close timeout fires");
  } finally {
    restore();
  }
});

test("re-open during close animation cancels the timeout", () => {
  const timers = createTimers();
  const { elements, restore } = loadWidget(timers);
  try {
    const panel = elements["chat-panel"];
    const open = elements["chat-open"];
    const close = elements["chat-close"];
    open.listeners.click(); // open
    close.listeners.click(); // close — schedules close timer
    // Panel is NOT hidden yet (close animation in flight).
    assert.ok(!panel.classList.contains("hidden"), "close animation in flight");
    open.listeners.click(); // re-open — must use tracked state, not "hidden"
    assert.ok(panel.classList.contains("is-open"), "is-open present after re-open");
    timers.runAll(); // any pending close timer should have been cancelled
    assert.ok(!panel.classList.contains("hidden"), "hidden NOT added — re-open cancelled the close");
  } finally {
    restore();
  }
});

test("idempotent: clicking open while already open does not re-fire requestAnimationFrame", () => {
  const timers = createTimers();
  const { elements, rafCount, restore } = loadWidget(timers);
  try {
    const panel = elements["chat-panel"];
    const open = elements["chat-open"];
    const close = elements["chat-close"];
    open.listeners.click(); // initial open — exactly one rAF
    assert.equal(rafCount(), 1, "exactly one rAF for the initial open");
    const rafCountBefore = rafCount();
    open.listeners.click(); // already open — toggles closed without scheduling rAF
    assert.equal(rafCount(), rafCountBefore, "no extra rAF when already open");
    close.listeners.click(); // already closed → guard `open === isOpen` no-ops
    assert.equal(timers.pending(), 1, "redundant close must not schedule again");
    timers.runAll();
    assert.ok(panel.classList.contains("hidden"), "panel hidden after close completes");
  } finally {
    restore();
  }
});
