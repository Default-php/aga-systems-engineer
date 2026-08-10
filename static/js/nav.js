document.addEventListener("DOMContentLoaded", function () {
  var toggle = document.getElementById("nav-toggle");
  var menu = document.getElementById("nav-menu");
  if (!toggle || !menu) return;

  toggle.addEventListener("click", function () {
    var isHidden = menu.classList.toggle("hidden");
    toggle.setAttribute("aria-expanded", String(!isHidden));
  });
});
