/* ===========================================================
   RiskGuard Pro — Presentation Engine
   Navigation + self-contained SVG charts (no external libs)
   =========================================================== */

const SVGNS = "http://www.w3.org/2000/svg";
const C = {
  gold: "#ffd700", goldDeep: "#e6b800", navy: "#0a1238",
  white: "#ffffff", muted: "#aab4e0", grid: "rgba(255,255,255,0.10)",
  green: "#2ecc71", yellow: "#f1c40f", orange: "#e67e22", red: "#e74c3c",
  blue: "#3949ab", blueLight: "#5c6bc0"
};

function el(tag, attrs = {}, parent = null) {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}
function txt(parent, x, y, str, opts = {}) {
  const t = el("text", {
    x, y, fill: opts.fill || C.muted,
    "font-size": opts.size || 11,
    "font-family": "Poppins, sans-serif",
    "font-weight": opts.weight || 400,
    "text-anchor": opts.anchor || "start"
  }, parent);
  t.textContent = str;
  return t;
}
function clear(svg) { while (svg.firstChild) svg.removeChild(svg.firstChild); }

/* ---------- Charts ---------- */

// SLIDE 3 — rising defaults line chart
function ctxChart() {
  const s = document.getElementById("ctxChart"); if (!s) return; clear(s);
  const W = 360, H = 240, pad = 34;
  const data = [22, 28, 26, 35, 41, 52, 63, 78];
  const years = ["18","19","20","21","22","23","24","25"];
  const max = 90;
  for (let i = 0; i <= 4; i++) {
    const y = pad + (H - pad * 2) * i / 4;
    el("line", { x1: pad, y1: y, x2: W - 10, y2: y, stroke: C.grid, "stroke-width": 1 }, s);
  }
  const xs = i => pad + (W - pad - 10) * i / (data.length - 1);
  const ys = v => H - pad - (H - pad * 2) * v / max;
  let d = "", area = `M ${xs(0)} ${H - pad} `;
  data.forEach((v, i) => { d += `${i ? "L" : "M"} ${xs(i)} ${ys(v)} `; area += `L ${xs(i)} ${ys(v)} `; });
  area += `L ${xs(data.length - 1)} ${H - pad} Z`;
  const grad = el("linearGradient", { id: "ctxg", x1: 0, y1: 0, x2: 0, y2: 1 }, s);
  el("stop", { offset: 0, "stop-color": C.gold, "stop-opacity": .45 }, grad);
  el("stop", { offset: 1, "stop-color": C.gold, "stop-opacity": 0 }, grad);
  el("path", { d: area, fill: "url(#ctxg)" }, s);
  el("path", { d, fill: "none", stroke: C.gold, "stroke-width": 3, "stroke-linejoin": "round" }, s);
  data.forEach((v, i) => {
    el("circle", { cx: xs(i), cy: ys(v), r: 3.5, fill: C.navy, stroke: C.gold, "stroke-width": 2 }, s);
    txt(s, xs(i), H - pad + 16, "'" + years[i], { anchor: "middle", size: 9 });
  });
  txt(s, pad, pad - 12, "Défaillances (indice)", { fill: C.muted, size: 10 });
}

// SLIDE 5 — class imbalance bars
function imbChart() {
  const s = document.getElementById("imbChart"); if (!s) return; clear(s);
  const W = 320, H = 240, base = 200;
  const bars = [
    { l: "Sains (0)", v: 97, c: C.blue },
    { l: "Faillite (1)", v: 3, c: C.red }
  ];
  bars.forEach((b, i) => {
    const bw = 80, x = 60 + i * 130;
    const h = (base - 30) * b.v / 100;
    el("rect", { x, y: base - h, width: bw, height: h, rx: 8, fill: b.c }, s);
    txt(s, x + bw / 2, base - h - 8, b.v + " %", { anchor: "middle", fill: C.white, weight: 700, size: 16 });
    txt(s, x + bw / 2, base + 20, b.l, { anchor: "middle", size: 11 });
  });
  el("line", { x1: 40, y1: base, x2: W - 10, y2: base, stroke: C.grid }, s);
}

// SLIDE 6 — feature reduction
function cleanChart() {
  const s = document.getElementById("cleanChart"); if (!s) return; clear(s);
  const base = 110;
  const data = [{ l: "Avant", v: 96, c: C.blueLight }, { l: "Après", v: 65, c: C.gold }];
  data.forEach((b, i) => {
    const bw = 70, x = 50 + i * 130, h = 90 * b.v / 100;
    el("rect", { x, y: base - h, width: bw, height: h, rx: 8, fill: b.c }, s);
    txt(s, x + bw / 2, base - h - 6, b.v, { anchor: "middle", fill: C.white, weight: 700, size: 15 });
    txt(s, x + bw / 2, base + 18, b.l, { anchor: "middle", size: 11 });
  });
  el("path", { d: "M 130 60 L 175 60", stroke: C.gold, "stroke-width": 2, "marker-end": "url(#ar)" }, s);
  const m = el("marker", { id: "ar", markerWidth: 8, markerHeight: 8, refX: 6, refY: 3, orient: "auto" }, s);
  el("path", { d: "M0,0 L6,3 L0,6 Z", fill: C.gold }, m);
}

// confusion matrix renderer
function confusion(svgId, m, labels) {
  const s = document.getElementById(svgId); if (!s) return; clear(s);
  const size = 60, ox = 38, oy = 14;
  const flat = m.flat(); const max = Math.max(...flat);
  for (let r = 0; r < 2; r++) for (let c = 0; c < 2; c++) {
    const v = m[r][c];
    const correct = r === c;
    const inten = 0.25 + 0.65 * (v / max);
    const col = correct ? `rgba(46,204,113,${inten})` : `rgba(231,76,60,${inten})`;
    el("rect", { x: ox + c * size, y: oy + r * size, width: size - 3, height: size - 3, rx: 6, fill: col }, s);
    txt(s, ox + c * size + size / 2 - 1, oy + r * size + size / 2 + 4, v, { anchor: "middle", fill: C.white, weight: 700, size: 14 });
  }
  txt(s, ox - 6, oy + size / 2, "Réel 0", { anchor: "end", size: 8 });
  txt(s, ox - 6, oy + size + size / 2, "Réel 1", { anchor: "end", size: 8 });
  txt(s, ox + size / 2, oy + 2 * size + 14, "Préd 0", { anchor: "middle", size: 8 });
  txt(s, ox + size + size / 2, oy + 2 * size + 14, "Préd 1", { anchor: "middle", size: 8 });
}

// SLIDE 8 — SMOTE interpolation
function smoteChart() {
  const s = document.getElementById("smoteChart"); if (!s) return; clear(s);
  const pts = [[60, 120], [110, 60], [180, 100], [230, 50], [150, 130]];
  // connect line between two
  el("line", { x1: pts[0][0], y1: pts[0][1], x2: pts[1][0], y2: pts[1][1], stroke: C.gold, "stroke-dasharray": "4 3", "stroke-width": 1.5 }, s);
  el("line", { x1: pts[1][0], y1: pts[1][1], x2: pts[3][0], y2: pts[3][1], stroke: C.gold, "stroke-dasharray": "4 3", "stroke-width": 1.5 }, s);
  // synthetic points on segments
  [[0, 1, .4], [0, 1, .7], [1, 3, .5]].forEach(([a, b, t]) => {
    const x = pts[a][0] + (pts[b][0] - pts[a][0]) * t;
    const y = pts[a][1] + (pts[b][1] - pts[a][1]) * t;
    el("circle", { cx: x, cy: y, r: 5, fill: C.gold, opacity: .9 }, s);
  });
  // original minority points
  pts.forEach(p => el("circle", { cx: p[0], cy: p[1], r: 6, fill: C.red, stroke: C.white, "stroke-width": 1.5 }, s));
  txt(s, 15, 158, "● réels", { fill: C.red, size: 10 });
  txt(s, 90, 158, "● synthétiques (SMOTE)", { fill: C.gold, size: 10 });
}

// SLIDE 8 — gaussian curve
function gaussChart() {
  const s = document.getElementById("gaussChart"); if (!s) return; clear(s);
  const W = 300, H = 110, cx = W / 2, base = 92, A = 70, sig = 38;
  let d = "";
  for (let x = 20; x <= W - 20; x += 3) {
    const y = base - A * Math.exp(-Math.pow(x - cx, 2) / (2 * sig * sig));
    d += `${x === 20 ? "M" : "L"} ${x} ${y} `;
  }
  el("line", { x1: 20, y1: base, x2: W - 20, y2: base, stroke: C.grid }, s);
  el("line", { x1: cx, y1: 20, x2: cx, y2: base, stroke: C.grid, "stroke-dasharray": "3 3" }, s);
  el("path", { d, fill: "none", stroke: C.gold, "stroke-width": 2.5 }, s);
  txt(s, cx, base + 14, "μ = 0", { anchor: "middle", size: 10 });
  txt(s, W - 24, base + 14, "ε", { anchor: "end", size: 11, fill: C.gold });
}

// SLIDE 9 — gradient bar
function gradientBar() {
  const s = document.getElementById("gradientBar"); if (!s) return; clear(s);
  const grad = el("linearGradient", { id: "rg", x1: 0, y1: 0, x2: 1, y2: 0 }, s);
  [[0, C.green], [.33, C.yellow], [.66, C.orange], [1, C.red]].forEach(([o, c]) =>
    el("stop", { offset: o, "stop-color": c }, grad));
  el("rect", { x: 0, y: 4, width: 900, height: 18, rx: 9, fill: "url(#rg)" }, s);
}

// SLIDE 10 — F1 bar chart
function benchChart() {
  const s = document.getElementById("benchChart"); if (!s) return; clear(s);
  const data = [
    { l: "Rég. Log.", v: .72 }, { l: "RF", v: .86 }, { l: "SVM", v: .78 },
    { l: "KNN", v: .75 }, { l: "XGBoost", v: .93, best: true }, { l: "LightGBM", v: .91 }
  ];
  const W = 340, base = 210, bw = 38, gap = 14, ox = 20;
  for (let i = 0; i <= 4; i++) {
    const y = base - (base - 20) * i / 4;
    el("line", { x1: ox, y1: y, x2: W, y2: y, stroke: C.grid }, s);
  }
  data.forEach((b, i) => {
    const x = ox + i * (bw + gap), h = (base - 20) * b.v;
    el("rect", { x, y: base - h, width: bw, height: h, rx: 5, fill: b.best ? C.gold : C.blueLight }, s);
    txt(s, x + bw / 2, base - h - 6, b.v.toFixed(2), { anchor: "middle", fill: b.best ? C.gold : C.white, weight: b.best ? 700 : 500, size: 10 });
    txt(s, x + bw / 2, base + 14, b.l, { anchor: "middle", size: 8.5 });
  });
}

// SLIDE 11 — boosting sequential trees
function boostChart() {
  const s = document.getElementById("boostChart"); if (!s) return; clear(s);
  const ys = 50;
  for (let i = 0; i < 4; i++) {
    const x = 30 + i * 75;
    el("circle", { cx: x, cy: ys, r: 14, fill: i === 3 ? C.gold : C.blueLight }, s);
    txt(s, x, ys + 4, "T" + (i + 1), { anchor: "middle", fill: C.navy, weight: 700, size: 11 });
    txt(s, x, ys + 36, i === 0 ? "base" : "+ erreur", { anchor: "middle", size: 8 });
    if (i < 3) el("path", { d: `M ${x + 16} ${ys} L ${x + 57} ${ys}`, stroke: C.gold, "stroke-width": 2, "marker-end": "url(#bar2)" }, s);
  }
  const m = el("marker", { id: "bar2", markerWidth: 8, markerHeight: 8, refX: 6, refY: 3, orient: "auto" }, s);
  el("path", { d: "M0,0 L6,3 L0,6 Z", fill: C.gold }, m);
  txt(s, 160, 100, "Σ prédiction finale", { anchor: "middle", fill: C.gold, size: 11, weight: 600 });
}

// SLIDE 12 — Optuna convergence
function optunaChart() {
  const s = document.getElementById("optunaChart"); if (!s) return; clear(s);
  const W = 360, H = 250, pad = 34;
  const trials = [];
  let best = .70;
  const raw = [.70,.66,.74,.71,.78,.76,.81,.79,.84,.80,.86,.85,.88,.87,.89,.88,.905,.90,.91,.905,.915,.91,.92,.918,.925,.92,.928,.925,.93,.929];
  raw.forEach(v => { best = Math.max(best, v); trials.push({ v, best }); });
  const xs = i => pad + (W - pad - 10) * i / (trials.length - 1);
  const ys = v => H - pad - (H - pad * 2) * (v - .6) / .4;
  for (let i = 0; i <= 4; i++) { const y = pad + (H - pad * 2) * i / 4; el("line", { x1: pad, y1: y, x2: W - 10, y2: y, stroke: C.grid }, s); }
  trials.forEach((t, i) => el("circle", { cx: xs(i), cy: ys(t.v), r: 2.5, fill: C.blueLight, opacity: .7 }, s));
  let d = "";
  trials.forEach((t, i) => d += `${i ? "L" : "M"} ${xs(i)} ${ys(t.best)} `);
  el("path", { d, fill: "none", stroke: C.gold, "stroke-width": 2.5 }, s);
  txt(s, pad, pad - 12, "AUC-ROC", { size: 10 });
  txt(s, W - 10, H - pad + 16, "30 essais", { anchor: "end", size: 9 });
  txt(s, xs(29), ys(.93) - 8, "0.93", { anchor: "end", fill: C.gold, size: 10, weight: 700 });
}

// SLIDE 16 — final confusion 4x ... use binary real numbers
function cmFinal() {
  const s = document.getElementById("cmFinal"); if (!s) return; clear(s);
  // real numbers from model_config.json
  confusionLarge(s, [[1577, 43], [33, 311]]);
}
function confusionLarge(s, m) {
  const size = 78, ox = 50, oy = 16;
  const flat = m.flat(); const max = Math.max(...flat);
  for (let r = 0; r < 2; r++) for (let c = 0; c < 2; c++) {
    const v = m[r][c], correct = r === c;
    const inten = 0.25 + 0.7 * (v / max);
    el("rect", { x: ox + c * size, y: oy + r * size, width: size - 4, height: size - 4, rx: 7, fill: correct ? `rgba(46,204,113,${inten})` : `rgba(231,76,60,${inten})` }, s);
    txt(s, ox + c * size + size / 2 - 2, oy + r * size + size / 2 + 5, v, { anchor: "middle", fill: C.white, weight: 700, size: 15 });
  }
  txt(s, ox - 6, oy + size / 2, "Sain", { anchor: "end", size: 9 });
  txt(s, ox - 6, oy + size + size / 2, "Faillite", { anchor: "end", size: 9 });
  txt(s, ox + size / 2, oy + 2 * size + 12, "Préd. Sain", { anchor: "middle", size: 9 });
  txt(s, ox + size + size / 2, oy + 2 * size + 12, "Préd. Faillite", { anchor: "middle", size: 9 });
}

// SLIDE 16 — ROC curve
function rocChart() {
  const s = document.getElementById("rocChart"); if (!s) return; clear(s);
  const pad = 26, sz = 148;
  el("rect", { x: pad, y: pad, width: sz, height: sz, fill: "none", stroke: C.grid }, s);
  el("line", { x1: pad, y1: pad + sz, x2: pad + sz, y2: pad, stroke: C.muted, "stroke-dasharray": "4 4", "stroke-width": 1 }, s);
  // strong ROC near top-left (AUC ~0.97)
  const pts = [[0,0],[.02,.55],[.04,.78],[.08,.88],[.15,.94],[.3,.97],[.6,.99],[1,1]];
  let d = "";
  pts.forEach((p, i) => { const x = pad + p[0] * sz, y = pad + sz - p[1] * sz; d += `${i ? "L" : "M"} ${x} ${y} `; });
  el("path", { d, fill: "none", stroke: C.gold, "stroke-width": 2.5 }, s);
  txt(s, pad + sz / 2, pad + sz + 18, "Taux faux positifs", { anchor: "middle", size: 9 });
  txt(s, pad + 8, pad + 14, "AUC = 0.97", { fill: C.gold, size: 11, weight: 700 });
}

// SLIDE 16 — feature importance (real values)
function featChart() {
  const s = document.getElementById("featChart"); if (!s) return; clear(s);
  const data = [
    { l: "Debt Ratio %", v: .39 },
    { l: "ROA (Net Inc/Assets)", v: .30 },
    { l: "Current Ratio", v: .19 },
    { l: "Working Cap/Assets", v: .12 },
    { l: "Retained Earn/Assets", v: .10 }
  ];
  const max = .4, ox = 130, bh = 24, gap = 12;
  data.forEach((b, i) => {
    const y = 14 + i * (bh + gap), w = (300 - ox) * b.v / max;
    el("rect", { x: ox, y, width: w, height: bh, rx: 5, fill: i === 0 ? C.gold : C.blueLight }, s);
    txt(s, ox - 6, y + bh / 2 + 4, b.l, { anchor: "end", size: 9.5, fill: C.white });
    txt(s, ox + w + 5, y + bh / 2 + 4, b.v.toFixed(2), { size: 9, fill: C.muted });
  });
}

// SLIDE 19 — decorative QR placeholder
function qrCode() {
  const s = document.getElementById("qrCode"); if (!s) return; clear(s);
  const seed = [
    "1111111 0 1111111", "1000001 1 1000001", "1011101 0 1011101",
    "1011101 1 1011101", "1011101 0 1011101", "1000001 1 1000001",
    "1111111 0 1111111", "0000000 0 0000000", "1010110 1 0110101",
    "0110101 0 1011010", "1011010 1 0101101", "0101101 1 1010110",
    "1111111 0 1010101", "1000001 1 0101010", "1011101 0 1100110",
    "1011101 1 0011001", "1000001 0 1010101"
  ];
  const n = 17, cell = 100 / n;
  el("rect", { x: 0, y: 0, width: 100, height: 100, fill: "#fff" }, s);
  for (let r = 0; r < n; r++) {
    const row = seed[r].replace(/ /g, "");
    for (let c = 0; c < n && c < row.length; c++) {
      if (row[c] === "1") el("rect", { x: c * cell, y: r * cell, width: cell + .3, height: cell + .3, fill: C.navy }, s);
    }
  }
}

function renderAllCharts() {
  ctxChart(); imbChart(); cleanChart();
  confusion("cmBefore", [[97, 0], [3, 0]]);
  confusion("cmAfter", [[88, 9], [1, 12]]);
  smoteChart(); gaussChart(); gradientBar();
  benchChart(); boostChart(); optunaChart();
  cmFinal(); rocChart(); featChart(); qrCode();
}

/* ---------- Navigation ---------- */
const slides = Array.from(document.querySelectorAll(".slide"));
const total = slides.length;
let current = 0;
let charted = false;

const progress = document.getElementById("progress");
const counter = document.getElementById("counter");
const pageNum = document.getElementById("pageNum");
const dotsWrap = document.getElementById("dots");
const hint = document.getElementById("hint");

slides.forEach((_, i) => {
  const dot = document.createElement("div");
  dot.className = "dot";
  dot.addEventListener("click", () => goTo(i));
  dotsWrap.appendChild(dot);
});
const dots = Array.from(dotsWrap.children);

function pad2(n) { return String(n).padStart(2, "0"); }

function goTo(i) {
  i = Math.max(0, Math.min(total - 1, i));
  slides[current].classList.remove("active");
  dots[current].classList.remove("active");
  current = i;
  slides[current].classList.add("active");
  dots[current].classList.add("active");
  progress.style.width = ((current + 1) / total * 100) + "%";
  counter.textContent = pad2(current + 1) + " / " + total;
  pageNum.textContent = current + 1;
  // render charts once (after first paint so layout exists)
  if (!charted) { charted = true; requestAnimationFrame(renderAllCharts); }
}
function next() { goTo(current + 1); }
function prev() { goTo(current - 1); }

document.getElementById("nextBtn").addEventListener("click", next);
document.getElementById("prevBtn").addEventListener("click", prev);

document.addEventListener("keydown", e => {
  if (["ArrowRight", "PageDown", " "].includes(e.key)) { e.preventDefault(); next(); }
  else if (["ArrowLeft", "PageUp"].includes(e.key)) { e.preventDefault(); prev(); }
  else if (e.key === "Home") goTo(0);
  else if (e.key === "End") goTo(total - 1);
  else if (e.key === "f" || e.key === "F") toggleFs();
});

function toggleFs() {
  if (!document.fullscreenElement) document.documentElement.requestFullscreen?.();
  else document.exitFullscreen?.();
}

// touch swipe
let tx = 0;
document.addEventListener("touchstart", e => tx = e.changedTouches[0].clientX, { passive: true });
document.addEventListener("touchend", e => {
  const dx = e.changedTouches[0].clientX - tx;
  if (Math.abs(dx) > 60) (dx < 0 ? next() : prev());
}, { passive: true });

// hide hint after a while
setTimeout(() => { if (hint) hint.style.opacity = "0"; }, 5000);

// init
goTo(0);
// also render charts on resize for crispness
let rt;
window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(renderAllCharts, 200); });
