(function () {
  "use strict";

  var widget = document.getElementById("chat-widget");
  if (!widget) {
    return;
  }

  var openButton = document.getElementById("chat-open");
  var closeButton = document.getElementById("chat-close");
  var panel = document.getElementById("chat-panel");
  var log = document.getElementById("chat-log");
  var form = document.getElementById("chat-form");
  var input = document.getElementById("chat-input");
  var submitButton = form.querySelector('button[type="submit"]');

  var chatUrl = widget.getAttribute("data-chat-url");

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  // ---- Inline safe markdown renderer ----
  var ESCAPE_LOOKUP = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  };

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (ch) {
      return ESCAPE_LOOKUP[ch];
    });
  }

  /**
   * Render a small subset of markdown safely:
   *   - `code` spans
   *   - **bold** and *italic* (italic via single asterisk, not underscore — keep simple)
   *   - # ## ### headers
   *   - - and * bullet lists
   *   - [text](url) — kept as markdown link (citation extraction already runs on raw text)
   *   - paragraphs and <br>
   *
   * Input is HTML-escaped FIRST, then markdown patterns are applied. This makes
   * the renderer safe to use with `innerHTML` (no XSS surface).
   */
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

    // Bold: **text**
    out = out.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");

    // Italic: *text* (single asterisk; require non-greedy boundaries to avoid
    // matching across words). Run AFTER bold so **bold** doesn't get caught.
    out = out.replace(/(^|[^*\w])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>");

    // Restore code spans (now safe from bold/italic transforms).
    out = out.replace(/\u0000(\d+)\u0000/g, function (_, index) {
      return (
        '<code class="px-1 py-0.5 rounded bg-surface-2 border border-edge text-sm font-mono">' +
        codeSpans[+index] +
        "</code>"
      );
    });

    // Headers (small subset: # ## ###).
    out = out.replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>');
    out = out.replace(/^## (.+)$/gm, '<h2 class="text-xl font-semibold mt-4 mb-2">$1</h2>');
    out = out.replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold mt-4 mb-2">$1</h1>');

    // Bullet lists: lines starting with `-` or `*`. Group consecutive bullets.
    out = out.replace(/(^|\n)((?:[-*] [^\n]+\n?)+)/g, function (_match, prefix, list) {
      var items = list
        .split("\n")
        .filter(function (l) {
          return l.trim().length > 0;
        })
        .map(function (l) {
          return "<li>" + l.replace(/^[-*] /, "") + "</li>";
        })
        .join("");
      return prefix + '<ul class="list-disc pl-5 my-2 space-y-1">' + items + "</ul>";
    });

    // Paragraphs and line breaks.
    out = out.replace(/\n{2,}/g, "</p><p>");
    out = out.replace(/\n/g, "<br>");
    return "<p>" + out + "</p>";
  }

  // Track open state so the timeout-based close can re-check, and so clicks
  // during the close animation resolve correctly (the panel is not "hidden"
  // again until the timeout fires).
  var isOpen = false;
  var closeTimer = null;
  var openRaf = null;

  function setOpen(open) {
    if (open === isOpen) return;
    isOpen = open;
    if (closeTimer !== null) {
      clearTimeout(closeTimer);
      closeTimer = null;
    }
    if (openRaf !== null) {
      cancelAnimationFrame(openRaf);
      openRaf = null;
    }
    if (open) {
      openButton.setAttribute("aria-expanded", "true");
      panel.classList.remove("hidden");
      // Force a layout flush so the browser registers the closed state before
      // we apply the open state (which is what makes the transition animate).
      openRaf = requestAnimationFrame(function () {
        openRaf = null;
        panel.classList.add("is-open");
        var input = document.getElementById("chat-input");
        if (input) input.focus();
      });
    } else {
      openButton.setAttribute("aria-expanded", "false");
      panel.classList.remove("is-open");
      // After the 200ms transition completes, hide the panel entirely.
      closeTimer = setTimeout(function () {
        if (!isOpen) panel.classList.add("hidden");
        closeTimer = null;
      }, 220);
    }
  }

  openButton.addEventListener("click", function () {
    setOpen(!isOpen);
  });
  closeButton.addEventListener("click", function () {
    setOpen(false);
  });

  function setTyping(visible) {
    var el = document.getElementById("chat-typing");
    if (!el) return;
    if (visible) {
      el.classList.remove("hidden");
    } else {
      el.classList.add("hidden");
    }
  }

  function appendMessage(text, who) {
    var el = document.createElement("div");
    el.className =
      who === "user"
        ? "self-end rounded-md bg-surface-2 px-3 py-2 text-ink"
        : "self-start rounded-md bg-surface-2 px-3 py-2 text-ink";
    if (who === "assistant") {
      el.innerHTML = renderMarkdown(text);
    } else {
      el.textContent = text;
    }
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var message = input.value.trim();
    if (!message) {
      return;
    }

    appendMessage(message, "user");
    input.value = "";
    input.disabled = true;
    submitButton.disabled = true;

    setTyping(true);
    fetch(chatUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(),
      },
      body: JSON.stringify({ message: message }),
    })
      .then(function (response) {
        if (response.status === 429) {
          return { error: "Rate limit exceeded. Please try again later." };
        }
        return response.json();
      })
      .then(function (data) {
        if (data && data.error) {
          appendMessage(data.error, "assistant");
          return;
        }
        appendMessage(data.answer || "", "assistant");
        if (data.sources && data.sources.length) {
          data.sources.forEach(function (source) {
            var link = document.createElement("a");
            link.className = "block text-accent hover:underline";
            link.href = source.url;
            link.textContent = "Source: " + source.title;
            log.appendChild(link);
          });
          log.scrollTop = log.scrollHeight;
        }
      })
      .catch(function () {
        appendMessage("Sorry, something went wrong. Please try again.", "assistant");
      })
      .finally(function () {
        setTyping(false);
        input.disabled = false;
        submitButton.disabled = false;
        input.focus();
      });
  });
})();
