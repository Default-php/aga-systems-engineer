const { test } = require("node:test");
const assert = require("node:assert");
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
    focus() {},
  };
  return element;
}

function loadWidget() {
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
  // The animated setOpen uses rAF to apply the open state and a 220ms timeout
  // to apply `hidden` on close. Run both synchronously so the toggle contract
  // stays assertable in tests, and restore the real globals afterwards.
  const realRaf = globalThis.requestAnimationFrame;
  const realCancelRaf = globalThis.cancelAnimationFrame;
  const realSetTimeout = globalThis.setTimeout;
  const realClearTimeout = globalThis.clearTimeout;
  globalThis.requestAnimationFrame = (cb) => {
    cb();
    return 0;
  };
  globalThis.cancelAnimationFrame = () => {};
  globalThis.setTimeout = (cb) => {
    cb();
    return 1;
  };
  globalThis.clearTimeout = () => {};
  delete require.cache[require.resolve(SCRIPT)];
  require(SCRIPT);
  return {
    elements,
    restore() {
      globalThis.document = undefined;
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

test("clicking the open button toggles the panel from hidden to visible", () => {
  const { elements, restore } = loadWidget();
  try {
    const panel = elements["chat-panel"];
    const open = elements["chat-open"];
    assert.ok(panel.classList.contains("hidden"), "panel starts hidden");
    open.listeners.click();
    assert.ok(!panel.classList.contains("hidden"), "panel visible after click");
  } finally {
    restore();
  }
});

test("clicking again toggles the panel back to hidden", () => {
  const { elements, restore } = loadWidget();
  try {
    const panel = elements["chat-panel"];
    const open = elements["chat-open"];
    open.listeners.click(); // open
    assert.ok(!panel.classList.contains("hidden"), "panel opened");
    open.listeners.click(); // close
    assert.ok(panel.classList.contains("hidden"), "panel hidden again");
  } finally {
    restore();
  }
});
