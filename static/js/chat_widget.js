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

  function setOpen(open) {
    panel.classList.toggle("hidden", !open);
    openButton.setAttribute("aria-expanded", String(open));
    if (open) {
      input.focus();
    }
  }

  openButton.addEventListener("click", function () {
    setOpen(!panel.classList.contains("hidden"));
  });
  closeButton.addEventListener("click", function () {
    setOpen(false);
  });

  function appendMessage(text, who) {
    var el = document.createElement("div");
    el.className =
      who === "user"
        ? "self-end rounded-md bg-surface-2 px-3 py-2 text-ink"
        : "self-start rounded-md bg-surface-2 px-3 py-2 text-ink";
    el.textContent = text;
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
        input.disabled = false;
        submitButton.disabled = false;
        input.focus();
      });
  });
})();
