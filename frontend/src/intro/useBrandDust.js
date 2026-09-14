// useBrandDust — canvas "solid text -> dust erosion" animation for the brand
// wordmark. Ported verbatim (behaviour-wise) from the original standalone
// intro HTML, wrapped as a reusable React hook so any component can attach it
// to a <canvas> ref. Self-contained: owns its own rAF loop and cleans up on
// unmount.
//
// Usage:
//   const canvasRef = useRef(null);
//   useBrandDust(canvasRef, { text: "OrionAI", split: 5 });
//   return <canvas ref={canvasRef} />;

import { useEffect } from "react";

const CSS_W = 1500;
// The canvas coordinate space is deliberately larger than the wordmark so that
// drifting dust fades out (alpha -> 0) BEFORE it can reach the canvas edge. The
// 2D context hard-clips anything drawn outside 0..CSS_W / 0..CSS_H, so without
// this headroom grains get sliced off at a straight edge ("caged in a square").
// The empty margin is fully transparent, so it does not look boxy.
const CSS_H = 900;
const TEXT_AREA_W = 1000;

// Full, unreduced timeline from the original piece.
const HOLD_MS = 650; // fully solid, static
const EROSION_SPAN_MS = 2300; // erosion front sweeps left -> right
const PARTICLE_LIFE_MS = 2600; // grain drift + fade after breaking free
const REST_MS = 1000; // pause on empty frame before looping
const TOTAL_MS = HOLD_MS + EROSION_SPAN_MS + PARTICLE_LIFE_MS + REST_MS;

const EMBER_COLORS = ["#ffffff", "#d8d8de", "#b9b0ff", "#8f8f96"];
const SPRITE_SIZE = 24;

function buildSprites() {
  return EMBER_COLORS.map((color) => {
    const c = document.createElement("canvas");
    c.width = SPRITE_SIZE;
    c.height = SPRITE_SIZE;
    const g = c.getContext("2d");
    const r = SPRITE_SIZE / 2;
    const grad = g.createRadialGradient(r, r, 0, r, r, r);
    grad.addColorStop(0, color);
    grad.addColorStop(0.45, color);
    grad.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = grad;
    g.beginPath();
    g.arc(r, r, r, 0, Math.PI * 2);
    g.fill();
    return c;
  });
}

export default function useBrandDust(canvasRef, options = {}) {
  const text = options.text ?? "OrionAI";
  const split = options.split ?? "Orion".length;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;

    // Respect reduced-motion: paint the solid wordmark once, no animation.
    const prefersReduced =
      typeof window !== "undefined" &&
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const ctx = canvas.getContext("2d");
    const sprites = buildSprites();
    const TEXT_Y = CSS_H / 2;

    let dpr = Math.min(window.devicePixelRatio || 1, 2);
    let particles = [];
    let textBounds = { minX: 0, maxX: 0 };
    let fontSize = 0;
    let rafId = 0;
    let cycleStart = 0;

    function sizeCanvas() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = CSS_W * dpr;
      canvas.height = CSS_H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function pickFontSize() {
      let size = 320;
      ctx.save();
      while (size > 15) {
        ctx.font = `600 ${size}px "Space Grotesk", sans-serif`;
        if (ctx.measureText(text).width <= TEXT_AREA_W * 1.15) break;
        size -= 4;
      }
      ctx.restore();
      return size;
    }

    // Draws the two-tone brand text (solid + dimmed tail) centred at (x, y).
    function paintBrand(targetCtx, x, y) {
      targetCtx.font = `600 ${fontSize}px "Space Grotesk", sans-serif`;
      targetCtx.textBaseline = "middle";
      const w1 = targetCtx.measureText(text.slice(0, split)).width;
      const fullW = targetCtx.measureText(text).width;
      const startX = x - fullW / 2;
      targetCtx.textAlign = "left";
      targetCtx.globalAlpha = 1;
      targetCtx.fillText(text.slice(0, split), startX, y);
      targetCtx.globalAlpha = 0.58;
      targetCtx.fillText(text.slice(split), startX + w1, y);
      targetCtx.globalAlpha = 1;
      return startX;
    }

    function buildParticles() {
      fontSize = pickFontSize();
      const off = document.createElement("canvas");
      off.width = CSS_W;
      off.height = CSS_H;
      const octx = off.getContext("2d");
      octx.fillStyle = "#fff";
      paintBrand(octx, CSS_W / 2, TEXT_Y);

      const img = octx.getImageData(0, 0, CSS_W, CSS_H).data;
      // Sampling step: larger => fewer particles => cheaper per frame. 4.5 keeps
      // the dust visually dense while roughly halving the particle count vs 3.1,
      // which removes the frame-rate hitch on lower-end machines.
      const STEP = 4.5;
      const pts = [];
      let minX = Infinity;
      let maxX = -Infinity;
      for (let y = 0; y < CSS_H; y += STEP) {
        for (let x = 0; x < CSS_W; x += STEP) {
          const px = Math.floor(x);
          const py = Math.floor(y);
          const alpha = img[(py * CSS_W + px) * 4 + 3];
          if (alpha > 120) {
            pts.push({
              x: x + (Math.random() - 0.5) * STEP,
              y: y + (Math.random() - 0.5) * STEP,
            });
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
          }
        }
      }
      if (pts.length === 0) {
        minX = 0;
        maxX = CSS_W;
      }
      textBounds = { minX: minX - 6, maxX: maxX + 6 };

      const spanX = Math.max(1, maxX - minX);
      particles = pts.map((p) => {
        const frontPos = (p.x - minX) / spanX;
        const jitter = (Math.random() - 0.5) * 0.22;
        let trigger = (frontPos + jitter) * EROSION_SPAN_MS;
        trigger = Math.max(0, Math.min(EROSION_SPAN_MS, trigger));

        const angle = (-90 + (Math.random() - 0.5) * 70) * (Math.PI / 180);
        // Speed capped so the fastest grain's drift stays inside the canvas
        // headroom (text sits at CSS_H/2) and fades before reaching the edge.
        const speed = 45 + Math.random() * 80;
        const accel = 1.0 + Math.random() * 0.7;
        const turbFreq = 1.3 + Math.random() * 2.2;
        const turbAmp = 14 + Math.random() * 30;
        const turbPhase = Math.random() * Math.PI * 2;
        const size = 2.2 + Math.random() * 3.2;
        const life = PARTICLE_LIFE_MS * (0.75 + Math.random() * 0.5);
        const spriteIdx = (Math.random() * sprites.length) | 0;
        const flicker = Math.random() * Math.PI * 2;

        return {
          ox: p.x,
          oy: p.y,
          trigger,
          angle,
          speed,
          accel,
          turbFreq,
          turbAmp,
          turbPhase,
          size,
          life,
          spriteIdx,
          flicker,
        };
      });
    }

    function drawSolidText(frac) {
      ctx.save();
      // A light shadow reads as a soft glow without the heavy per-frame cost of
      // a large blur radius (shadowBlur is one of the most expensive canvas ops).
      ctx.shadowColor = "rgba(185,176,255,0.35)";
      ctx.shadowBlur = 8;
      ctx.fillStyle = "#ffffff";
      if (frac > 0) {
        const span = Math.max(1, textBounds.maxX - textBounds.minX);
        const buffer = 0.14;
        const thresholdX =
          textBounds.minX + Math.min(1, frac + buffer) * span;
        ctx.beginPath();
        ctx.rect(thresholdX, 0, CSS_W - thresholdX, CSS_H);
        ctx.clip();
      }
      paintBrand(ctx, CSS_W / 2, TEXT_Y);
      ctx.restore();
    }

    function draw(now) {
      // Anchor the timeline to the first real frame, so the one-off
      // buildParticles() cost (a full getImageData read) at mount does not get
      // charged against the HOLD phase and show up as a stutter on appear.
      if (cycleStart === 0) cycleStart = now;
      const elapsed = now - cycleStart;

      if (elapsed > TOTAL_MS) {
        cycleStart = now;
        buildParticles();
        rafId = requestAnimationFrame(draw);
        return;
      }

      ctx.clearRect(0, 0, CSS_W, CSS_H);

      if (elapsed <= HOLD_MS) {
        drawSolidText(0);
      } else {
        const erosionElapsed = elapsed - HOLD_MS;
        const frac = Math.max(0, Math.min(1, erosionElapsed / EROSION_SPAN_MS));

        if (frac < 1) {
          drawSolidText(frac);
        }

        ctx.save();
        ctx.globalCompositeOperation = "lighter";
        for (const p of particles) {
          if (erosionElapsed < p.trigger) continue;
          const age = erosionElapsed - p.trigger;
          if (age > p.life) continue;

          const t = age / p.life;
          const ease = 1 - Math.pow(1 - t, p.accel);
          const dist = p.speed * (p.life / 1000) * ease;

          const dx = Math.cos(p.angle) * dist;
          const dy = Math.sin(p.angle) * dist;
          const wobble =
            Math.sin(t * p.turbFreq * Math.PI * 2 + p.turbPhase) *
            p.turbAmp *
            t;

          const x = p.ox + dx + wobble;
          const y = p.oy + dy - wobble * 0.3;

          const fadeStart = 0.45;
          const fadeT = t < fadeStart ? 0 : (t - fadeStart) / (1 - fadeStart);
          const alpha =
            (1 - Math.pow(fadeT, 1.7)) *
            (0.8 + 0.2 * Math.sin(t * 20 + p.flicker));
          if (alpha <= 0.02) continue;

          const size = p.size * (1 - t * 0.35);
          ctx.globalAlpha = Math.max(0, Math.min(1, alpha));
          ctx.drawImage(sprites[p.spriteIdx], x - size, y - size, size * 2, size * 2);
        }
        ctx.globalAlpha = 1;
        ctx.restore();
      }

      rafId = requestAnimationFrame(draw);
    }

    sizeCanvas();
    window.addEventListener("resize", sizeCanvas);

    if (prefersReduced) {
      fontSize = pickFontSize();
      textBounds = { minX: 0, maxX: CSS_W };
      ctx.clearRect(0, 0, CSS_W, CSS_H);
      drawSolidText(0);
      return () => window.removeEventListener("resize", sizeCanvas);
    }

    buildParticles();
    // Paint the solid wordmark immediately so the very first rendered frame is
    // the finished text (no blank canvas flash while rAF spins up).
    ctx.clearRect(0, 0, CSS_W, CSS_H);
    drawSolidText(0);
    cycleStart = 0; // set on the first frame inside draw()
    rafId = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener("resize", sizeCanvas);
    };
  }, [canvasRef, text, split]);
}
