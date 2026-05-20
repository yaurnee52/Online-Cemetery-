/**
 * Фон «созвездие» — точки и линии между близкими (аналог particles.js linked).
 */
(function () {
  "use strict";

  const canvas = document.getElementById("oc-particles-canvas");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const config = {
    density: 0.00018,
    minCount: 64,
    maxCount: 140,
    linkDistance: 145,
    linkWidth: 1.3,
    lineAlphaMax: 0.95,
    linkWidthCloseBonus: 0.35,
    dotRadius: 1.8,
    dotGlowRadius: 3.8,
    speed: 0.32,
    mouseRadius: 120,
  };

  let particles = [];
  let w = 0;
  let h = 0;
  let dpr = 1;
  let mouse = { x: null, y: null, active: false };
  let animationId = null;

  function themeColors() {
    const light = document.documentElement.getAttribute("data-theme") === "light";
    if (light) {
      return {
        dot: "rgba(0, 102, 204, 0.9)",
        line: "rgba(0, 82, 163, 0.45)",
        lineBright: "rgba(0, 102, 204, 0.55)",
        dotGlow: "rgba(0, 102, 204, 0.45)",
      };
    }
    return {
      dot: "rgba(108, 228, 255, 0.95)",
      line: "rgba(154, 130, 255, 0.42)",
      lineBright: "rgba(108, 228, 255, 0.55)",
      dotGlow: "rgba(108, 228, 255, 0.5)",
    };
  }

  function particleCount() {
    const n = Math.floor(w * h * config.density);
    return Math.max(config.minCount, Math.min(config.maxCount, n));
  }

  function createParticle() {
    return {
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * config.speed,
      vy: (Math.random() - 0.5) * config.speed,
    };
  }

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = window.innerWidth;
    h = window.innerHeight;
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const target = particleCount();
    while (particles.length < target) particles.push(createParticle());
    while (particles.length > target) particles.pop();
  }

  function tickParticle(p) {
    p.x += p.vx;
    p.y += p.vy;
    if (p.x < 0 || p.x > w) {
      p.vx *= -1;
      p.x = Math.max(0, Math.min(w, p.x));
    }
    if (p.y < 0 || p.y > h) {
      p.vy *= -1;
      p.y = Math.max(0, Math.min(h, p.y));
    }

    if (mouse.active && mouse.x != null) {
      const dx = mouse.x - p.x;
      const dy = mouse.y - p.y;
      const dist = Math.hypot(dx, dy);
      if (dist < config.mouseRadius && dist > 0) {
        const force = (config.mouseRadius - dist) / config.mouseRadius;
        p.x -= (dx / dist) * force * 1.2;
        p.y -= (dy / dist) * force * 1.2;
      }
    }
  }

  function draw() {
    const colors = themeColors();
    ctx.clearRect(0, 0, w, h);

    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const a = particles[i];
        const b = particles[j];
        const dist = Math.hypot(a.x - b.x, a.y - b.y);
        if (dist < config.linkDistance) {
          const t = 1 - dist / config.linkDistance;
          const alpha = t * config.lineAlphaMax;
          const close = t > 0.55;
          ctx.globalAlpha = alpha;
          ctx.strokeStyle = close ? colors.lineBright : colors.line;
          ctx.lineWidth = close ? config.linkWidth + config.linkWidthCloseBonus : config.linkWidth;
          ctx.lineCap = "round";
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
      }
    }

    for (const p of particles) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, config.dotGlowRadius, 0, Math.PI * 2);
      ctx.fillStyle = colors.dotGlow;
      ctx.fill();
      ctx.beginPath();
      ctx.arc(p.x, p.y, config.dotRadius, 0, Math.PI * 2);
      ctx.fillStyle = colors.dot;
      ctx.fill();
    }
  }

  function frame() {
    for (const p of particles) tickParticle(p);
    draw();
    animationId = requestAnimationFrame(frame);
  }

  function start() {
    resize();
    draw();
    if (!reducedMotion) animationId = requestAnimationFrame(frame);
  }

  function stop() {
    if (animationId) cancelAnimationFrame(animationId);
    animationId = null;
  }

  window.addEventListener("resize", () => {
    stop();
    resize();
    if (!reducedMotion) frame();
    else draw();
  });

  window.addEventListener("mousemove", (e) => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
    mouse.active = true;
  });
  window.addEventListener("mouseleave", () => {
    mouse.active = false;
  });

  const themeObserver = new MutationObserver(() => draw());
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop();
    else if (!reducedMotion) frame();
  });

  start();
})();
