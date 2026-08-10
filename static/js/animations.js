(function () {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return;
  }

  if (typeof gsap === "undefined") {
    return;
  }

  // Phase 1: hero entrance only. Scroll-based reveals may arrive with ScrollTrigger in a later phase if ever needed.
  gsap.from("[data-anim]", {
    y: 16,
    autoAlpha: 0,
    duration: 0.6,
    ease: "power2.out",
    stagger: 0.08,
    clearProps: "transform,opacity,visibility",
  });
})();
