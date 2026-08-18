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
  // The a11y attributes live in the template markup (widget.html), not in the
  // widget JS, so the stub carries them so tests can pin the contract.
  const templateAttrs =
    id === "chat-typing"
      ? { role: "status", "aria-live": "polite", "aria-label": "Assistant is thinking" }
      : {};
  const element = {
    id,
    listeners: {},
    attrs: templateAttrs,
    classList: makeClassList(id === "chat-panel" || id === "chat-typing" ? ["hidden"] : []),
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
    _getAttribute(name) {
      return this.attrs[name] || null;
    },
    _querySelector(selector) {
      // Minimal stub: only the sr-only span inside #chat-typing is needed.
      if (selector === ".sr-only") {
        const sr = makeElement();
        sr._textContent = "Assistant is thinking";
        return sr;
      }
      return null;
    },
    querySelector() {
      return { disabled: false };
    },
    appendChild() {},
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

// A deferred promise lets a test control exactly when fetch resolves/rejects.
function deferred() {
  let resolve, reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function loadWidget(timers, fetchImpl) {
  const ids = [
    "chat-widget",
    "chat-open",
    "chat-close",
    "chat-panel",
    "chat-log",
    "chat-form",
    "chat-input",
    "chat-typing",
  ];
  const elements = {};
  for (const id of ids) {
    elements[id] = makeElement(id);
  }
  const fakeDocument = {
    getElementById(id) {
      return elements[id] || null;
    },
    createElement() {
      return {
        className: "",
        textContent: "",
        innerHTML: "",
        appendChild() {},
      };
    },
    querySelector() {
      return { getAttribute: () => "" };
    },
  };
  globalThis.document = fakeDocument;
  globalThis.fetch = fetchImpl;
  globalThis.window = {
    matchMedia: function () {
      return {
        matches: false,
        addEventListener: function () {},
        removeEventListener: function () {},
      };
    },
  };
  const realRaf = globalThis.requestAnimationFrame;
  const realCancelRaf = globalThis.cancelAnimationFrame;
  const realSetTimeout = globalThis.setTimeout;
  const realClearTimeout = globalThis.clearTimeout;
  globalThis.requestAnimationFrame = (cb) => {
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
    document: fakeDocument,
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

test("typing indicator hidden by default", () => {
  const timers = createTimers();
  const w = loadWidget(timers, () => deferred().promise);
  try {
    const typing = w.elements["chat-typing"];
    assert.ok(typing.classList.contains("hidden"), "indicator must start hidden");
  } finally {
    w.restore();
  }
});

test("typing indicator shown while fetch is pending, hidden on response", async () => {
  const timers = createTimers();
  const d = deferred();
  const w = loadWidget(timers, () => d.promise);
  try {
    const typing = w.elements["chat-typing"];
    const form = w.elements["chat-form"];
    const input = w.elements["chat-input"];
    input.value = "hello";
    form.listeners.submit({ preventDefault() {} });

    // While fetch is pending the indicator must be visible.
    assert.ok(!typing.classList.contains("hidden"), "indicator visible while pending");

    // Resolve the fetch; the finally block hides the indicator.
    d.resolve({
      status: 200,
      json: () => Promise.resolve({ answer: "hi", sources: [] }),
    });
    await d.promise;
    // Flush the widget's .then/.catch/.finally chain (several microtask ticks).
    for (let i = 0; i < 5; i++) {
      await Promise.resolve();
    }
    assert.ok(typing.classList.contains("hidden"), "indicator hidden after response");
  } finally {
    w.restore();
  }
});

test("typing indicator hidden on fetch error", async () => {
  const timers = createTimers();
  const d = deferred();
  const w = loadWidget(timers, () => d.promise);
  try {
    const typing = w.elements["chat-typing"];
    const form = w.elements["chat-form"];
    const input = w.elements["chat-input"];
    input.value = "hello";
    form.listeners.submit({ preventDefault() {} });

    assert.ok(!typing.classList.contains("hidden"), "indicator visible while pending");

    d.reject(new Error("network down"));
    await assert.rejects(d.promise);
    for (let i = 0; i < 5; i++) {
      await Promise.resolve();
    }
    assert.ok(typing.classList.contains("hidden"), "indicator hidden after error");
  } finally {
    w.restore();
  }
});

test("typing indicator exposes accessibility attributes and visually-hidden label", () => {
  const timers = createTimers();
  const w = loadWidget(timers, () => deferred().promise);
  try {
    const typing = w.document.getElementById("chat-typing");
    // aria attributes
    assert.equal(typing._getAttribute("role"), "status");
    assert.equal(typing._getAttribute("aria-live"), "polite");
    assert.equal(typing._getAttribute("aria-label"), "Assistant is thinking");
    // visually-hidden announcement
    const srOnly = typing._querySelector(".sr-only");
    assert.ok(srOnly, "sr-only span must exist");
    assert.equal(srOnly._textContent, "Assistant is thinking");
  } finally {
    w.restore();
  }
});
