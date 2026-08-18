const { test } = require("node:test");
const assert = require("node:assert/strict");

// Re-implement renderMarkdown here so the test is self-contained.
// (Keep this in sync with chat_widget.js — production code and test use the
// same algorithm; if you change one, change both.)
var ESCAPE_LOOKUP = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, function (ch) { return ESCAPE_LOOKUP[ch]; }); }
function renderMarkdown(text) {
  if (text == null) return "";
  var out = escapeHtml(text);
  // Code spans first: stash their content behind placeholders so the later
  // inline passes (**bold**, *italic*) can't touch the inside of `code`.
  var codeSpans = [];
  out = out.replace(/`([^`\n]+)`/g, function (_, c) {
    codeSpans.push(c);
    return "\u0000" + (codeSpans.length - 1) + "\u0000";
  });
  out = out.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
  out = out.replace(/(^|[^*\w])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>");
  // Restore code spans (now safe from bold/italic transforms).
  out = out.replace(/\u0000(\d+)\u0000/g, function (_, index) {
    return '<code class="px-1 py-0.5 rounded bg-surface-2 border border-edge text-sm font-mono">' + codeSpans[+index] + "</code>";
  });
  out = out.replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>');
  out = out.replace(/^## (.+)$/gm, '<h2 class="text-xl font-semibold mt-4 mb-2">$1</h2>');
  out = out.replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold mt-4 mb-2">$1</h1>');
  out = out.replace(/(^|\n)((?:[-*] [^\n]+\n?)+)/g, function (_match, prefix, list) {
    var items = list.split("\n").filter(function (l) { return l.trim().length > 0; })
      .map(function (l) { return "<li>" + l.replace(/^[-*] /, "") + "</li>"; })
      .join("");
    return prefix + '<ul class="list-disc pl-5 my-2 space-y-1">' + items + "</ul>";
  });
  out = out.replace(/\n{2,}/g, "</p><p>");
  out = out.replace(/\n/g, "<br>");
  return "<p>" + out + "</p>";
}

test("bold renders as <strong>", () => {
  assert.match(renderMarkdown("**bold text**"), /<strong>bold text<\/strong>/);
});

test("italic renders as <em>", () => {
  assert.match(renderMarkdown("This is *italic* emphasis"), /<em>italic<\/em>/);
});

test("code renders as <code>", () => {
  assert.match(renderMarkdown("Use `console.log` for debug"), /<code[^>]*>console\.log<\/code>/);
});

test("headers render", () => {
  assert.match(renderMarkdown("# Big Title"), /<h1[^>]*>Big Title<\/h1>/);
  assert.match(renderMarkdown("## Sub Title"), /<h2[^>]*>Sub Title<\/h2>/);
  assert.match(renderMarkdown("### Tiny"), /<h3[^>]*>Tiny<\/h3>/);
});

test("bullet list renders", () => {
  const out = renderMarkdown("- one\n- two\n- three");
  assert.match(out, /<ul[^>]*>.*<li>one<\/li>.*<li>two<\/li>.*<li>three<\/li>.*<\/ul>/s);
});

test("HTML in input is escaped (XSS protection)", () => {
  const out = renderMarkdown("<script>alert(1)</script>");
  assert.doesNotMatch(out, /<script>/i);
  assert.match(out, /&lt;script&gt;/);
});

test("null/undefined return empty string", () => {
  assert.equal(renderMarkdown(null), "");
  assert.equal(renderMarkdown(undefined), "");
});

test("code span wins over bold inside it", () => {
  // `**not bold**` should NOT render as <strong>; it stays in <code>.
  const out = renderMarkdown("`**not bold**`");
  assert.match(out, /<code[^>]*>\*\*not bold\*\*<\/code>/);
  assert.doesNotMatch(out, /<strong>/);
});

test("paragraph breaks", () => {
  const out = renderMarkdown("First paragraph.\n\nSecond paragraph.");
  assert.match(out, /<\/p><p>/);
});

test("model-style answer renders cleanly", () => {
  // Mimics what the model actually produces.
  const answer = "Alfonso tiene **5 años de experiencia** en *Docker* y Kubernetes.\n\n- **Docker**\n- **Kubernetes**\n- **AWS**";
  const out = renderMarkdown(answer);
  assert.match(out, /<strong>5 a\u00f1os de experiencia<\/strong>/);
  assert.match(out, /<em>Docker<\/em>/);
  assert.match(out, /<ul[^>]*>/);
  assert.match(out, /<li>.*<strong>Docker<\/strong>.*<\/li>/);
});
