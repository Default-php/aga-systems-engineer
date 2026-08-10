const { test } = require("node:test");
const assert = require("node:assert");
const path = require("node:path");

const SCRIPT = path.resolve(__dirname, "../../static/js/animations.js");

function loadWith({ reducedMotion = false, gsap } = {}) {
  delete require.cache[require.resolve(SCRIPT)];
  const queries = [];
  globalThis.window = {
    matchMedia: (query) => {
      queries.push(query);
      return { matches: reducedMotion };
    },
  };
  if (gsap === undefined) {
    delete globalThis.gsap;
  } else {
    globalThis.gsap = gsap;
  }
  require(SCRIPT);
  return { queries };
}

test("reduced motion: gsap.from is not called", () => {
  let called = 0;
  const gsap = {
    from() {
      called += 1;
    },
  };
  const { queries } = loadWith({ reducedMotion: true, gsap });
  assert.deepStrictEqual(queries, ["(prefers-reduced-motion: reduce)"]);
  assert.strictEqual(called, 0);
});

test("gsap undefined: loading does not throw", () => {
  let result;
  assert.doesNotThrow(() => {
    result = loadWith({ reducedMotion: false, gsap: undefined });
  });
  assert.deepStrictEqual(result.queries, ["(prefers-reduced-motion: reduce)"]);
});

test("normal path: gsap.from called once with hero entrance config", () => {
  const calls = [];
  const gsap = {
    from(...args) {
      calls.push(args);
    },
  };
  const { queries } = loadWith({ reducedMotion: false, gsap });
  assert.deepStrictEqual(queries, ["(prefers-reduced-motion: reduce)"]);
  assert.strictEqual(calls.length, 1);
  const [selector, config] = calls[0];
  assert.strictEqual(selector, "[data-anim]");
  assert.strictEqual(config.y, 16);
  assert.strictEqual(config.autoAlpha, 0);
  assert.strictEqual(config.duration, 0.6);
  assert.strictEqual(config.ease, "power2.out");
  assert.strictEqual(config.stagger, 0.08);
  assert.strictEqual(config.clearProps, "transform,opacity,visibility");
});
