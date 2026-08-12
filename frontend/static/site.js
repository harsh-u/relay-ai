// Shared, dependency-free page interactions: mouse-tilt cards and
// reveal-on-scroll - the two portable (CSS-transform-only) effects from
// convoxio-v2's marketing page, ported to vanilla JS since this frontend
// has no React/build step.

function initTiltCards() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  if (window.matchMedia("(pointer: coarse)").matches) return; // skip on touch

  document.querySelectorAll("[data-tilt]").forEach((card) => {
    const strength = Number(card.dataset.tilt) || 6;

    card.addEventListener("pointermove", (event) => {
      const rect = card.getBoundingClientRect();
      const px = (event.clientX - rect.left) / rect.width - 0.5;
      const py = (event.clientY - rect.top) / rect.height - 0.5;
      card.style.transform =
        `perspective(800px) rotateX(${(-py * strength).toFixed(2)}deg) ` +
        `rotateY(${(px * strength).toFixed(2)}deg) translateZ(4px)`;
    });

    card.addEventListener("pointerleave", () => {
      card.style.transform = "";
    });
  });
}

function initRevealOnScroll() {
  const targets = document.querySelectorAll("[data-reveal]");
  if (!targets.length) return;

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    targets.forEach((el) => el.classList.add("is-visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      }
    },
    { threshold: 0.15 }
  );

  targets.forEach((el) => observer.observe(el));
}

initTiltCards();
initRevealOnScroll();
