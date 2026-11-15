// Map tab: a pannable, zoomable US map of every state-level number on the board.
// Reads /api/geo (pre-projected state outlines), /api/map (NASS history, season context, state-level
// backtest predictions) and the /api/board payload already loaded by page.html (D, MODELS, BT, CAT, S).
"use strict";
const SEQ = ["#0d366b", "#104281", "#1c5cab", "#2a78d6", "#5598e7", "#86b6ef", "#cde2fb"];           // blue, low -> high
const SEQ2 = ["#4a2412", "#6b3018", "#8f3f1e", "#b84d23", "#d95926", "#ef8a5f", "#f8c2a6"];          // orange, low -> high
const DIV = ["#184f95", "#3987e5", "#86b6ef", "#383835", "#f2a3a3", "#e66767", "#b83a3a"];          // down <- 0 -> up
const NODATA = "#1b2029";
const NAMES = {};
const VB = {x: -10, y: -58, w: 995, h: 690};   // room for the controls above the map
let GEO = null, MAP = null, EXT = null, CTY = null, M = {layer: "forecast", crop: "silage", fcModel: {}, errModel: {}, year: 2025, signal: "drought", wx: "rain", cyear: null, wyear: null, myear: null,
  sel: null, k: 1, tx: 0, ty: 0, playing: null, built: false};

// Layers, grouped by the question they answer. "explain" is shown under the map in plain words.
const LAYER_GROUPS = [
  ["Our forecast", [
    ["forecast", "Acres we expect in 2026", "Each state is colored by how many acres one of our models expects to be harvested in 2026. Lighter means more acres. Pick a different model in the next box."],
    ["change", "2026 compared with last year", "Red states are expected to harvest more acres than last year, blue states fewer. Gray means about the same."],
    ["disagree", "Where our models disagree", "How far apart our models' 2026 numbers are in each state. Lighter means the models disagree more, so the number there is less certain."]]],
  ["What happened before", [
    ["history", "Acres harvested each year", "The official USDA (NASS) count of acres harvested, year by year. Press Play to watch it change."]]],
  ["Why acres change", [
    ["dairy", "Where the dairy cows are (counties)", "Milk cows per county from the USDA census. Silage is cow feed, so it is grown close to dairies: compare with the next layer."],
    ["silage_county", "Where silage is grown (counties)", "Acres of corn chopped for silage per county from the USDA census. Notice how it follows the dairy map."],
    ["weather", "This season's rain and heat (counties)", "Rain or heat from May to September compared with that county's normal. A dry, hot year can push farmers to chop failing grain corn for silage."],
    ["frost", "First fall frost (counties)", "The date of the first fall frost in each county. An early frost ends the season and can change what farmers harvest."],
    ["context", "Drought, crop condition and losses (states)", "Season signals by state: drought, corn rated poor, insurance weather losses, rain, heat and milk cows."],
    ["harvest", "When silage gets chopped", "The usual date by which half of a state's silage is chopped. Some states are half done by late August, others not until October, so one harvest calendar does not fit every state."],
    ["money", "What the corn crop is worth", "Corn harvested for grain times the price farmers received: the dollar value of each state's grain crop."],
    ["price", "Corn price farmers got", "The average price per bushel farmers received over the marketing year."]]],
  ["Satellite", [
    ["satellite", "Where the satellite looks", "Highlighted states are where the satellite sample is being drawn: the 15 states with the most silage. Dots mark the fields with known answers used to test the satellite model."]]],
  ["How good are the models", [
    ["error", "How far off each model was, by state", "For each state, how far a model's past forecasts were from the official count, on average. Darker means closer, so darker is better."]]],
];
const LAYERS = LAYER_GROUPS.flatMap(g => g[1]);
const COUNTY_LAYERS = new Set(["dairy", "silage_county", "weather", "frost"]);
const doyDate = d => d == null ? "\u2014" : new Date(2026, 0, d).toLocaleDateString("en-US", {month: "short", day: "numeric"});
const money = v => v == null ? "\u2014" : v >= 1e9 ? "$" + (v / 1e9).toFixed(2) + "B" : v >= 1e6 ? "$" + Math.round(v / 1e6) + "M" : "$" + Math.round(v).toLocaleString("en-US");
const SIGNALS = {
  drought: {label: "Drought, share of state D2+", fmt: v => (100 * v).toFixed(0) + "%", ramp: SEQ2},
  poor_condition: {label: "Corn rated poor or very poor", fmt: v => (100 * v).toFixed(0) + "%", ramp: SEQ2},
  loss_share: {label: "Insured corn with a weather loss", fmt: v => (100 * v).toFixed(0) + "%", ramp: SEQ2},
  rain_anom: {label: "Season rain vs the state's normal", fmt: v => (v >= 0 ? "+" : "") + (100 * v).toFixed(0) + "%", div: true},
  gdd_anom: {label: "Season heat vs the state's normal", fmt: v => (v >= 0 ? "+" : "") + (100 * v).toFixed(1) + "%", div: true},
  milk_cows: {label: "Milk cows", fmt: v => kfmt(v) + " head", ramp: SEQ},
};
const kfmt = v => v == null ? "—" : v >= 1e6 ? (v / 1e6).toFixed(2) + "M" : v >= 1e3 ? Math.round(v / 1e3).toLocaleString("en-US") + "k" : Math.round(v).toString();
const pfmt = v => v == null ? "—" : (v >= 0 ? "+" : "") + v.toFixed(1) + "%";

// ---------------------------------------------------------------- data helpers
function hist(code, year) { return MAP.history.find(r => r.state == code && r.year == year); }
function lastActualYear(crop) { return Math.max(...MAP.history.filter(r => r[crop] != null).map(r => r.year)); }
function fcModels(crop) { return Object.values(MODELS).filter(m => m.target == crop && m.has_forecast); }
function fcValue(id, code) { const r = D.forecast.find(r => r.model_id == id && r.state == code); return r || null; }
function usTotal(id, crop) {
  const rows = D.forecast.filter(r => r.model_id == id && r.target == crop); if (!rows.length) return null;
  const own = rows.find(r => r.state == "US");
  return own ? {v: own.predicted, lo: own.lo80, hi: own.hi80, how: "model's US row"}
             : {v: rows.reduce((a, r) => a + (r.predicted || 0), 0), lo: null, hi: null, how: `sum of ${rows.length} states`};
}
function errModels(crop) { return [...new Set(MAP.state_predictions.filter(r => r.target == crop).map(r => r.model_id))]; }
function stateErrors(id) {    // mean absolute % error per state over the board's year range and forecast date
  const acc = {};
  MAP.state_predictions.forEach(r => {
    if (r.model_id != id || r.year < S.y0 || r.year > S.y1 || (r.asof != null && r.asof != S.asof) || !r.actual) return;
    (acc[r.state] ??= []).push(100 * Math.abs(r.predicted - r.actual) / r.actual);
  });
  const out = {}; for (const k in acc) out[k] = {v: acc[k].reduce((a, b) => a + b, 0) / acc[k].length, n: acc[k].length}; return out;
}
function defaultModel(crop) {
  const tierPub = (CAT.models || []).filter(c => c.crop == crop).map(c => Object.values(MODELS).find(m => m.model == c.id && m.target == crop && m.has_forecast)).filter(Boolean);
  if (tierPub.length) return tierPub[0].model_id;
  const bench = (CAT.benchmarks || []).find(b => b.crop == crop && MODELS[b.model_id]?.has_forecast);
  return bench ? bench.model_id : fcModels(crop)[0]?.model_id;
}
function modelLabel(id) { const m = MODELS[id]; if (!m) return id; const b = (CAT.benchmarks || []).find(b => b.model_id == id);
  return b ? `${b.label} (${m.source})` : `${m.model} (${m.source})`; }

// ---------------------------------------------------------------- layer values
function layerValues() {
  const crop = M.crop, vals = {}; let fmt = kfmt, ramp = SEQ, div = false, title = "", note = "";
  if (M.layer == "forecast") {
    const id = M.fcModel[crop]; title = `2026 ${crop} acres · ${modelLabel(id)}`;
    D.forecast.filter(r => r.model_id == id && r.state != "US").forEach(r => vals[r.state] = r.predicted);
  } else if (M.layer == "change") {
    const id = M.fcModel[crop], y = lastActualYear(crop); title = `2026 forecast vs NASS ${y} · ${modelLabel(id)}`; div = true; fmt = pfmt;
    D.forecast.filter(r => r.model_id == id && r.state != "US").forEach(r => { const h = hist(r.state, y); if (h && h[crop]) vals[r.state] = 100 * (r.predicted / h[crop] - 1); });
  } else if (M.layer == "disagree") {
    title = `Spread of 2026 ${crop} forecasts across ${fcModels(crop).length} models (max − min, % of median)`; ramp = SEQ2; fmt = v => v.toFixed(1) + "%";
    const by = {}; fcModels(crop).forEach(m => D.forecast.filter(r => r.model_id == m.model_id && r.state != "US").forEach(r => (by[r.state] ??= []).push(r.predicted)));
    for (const k in by) if (by[k].length >= 2) { const a = by[k].sort((x, y) => x - y), med = a[Math.floor(a.length / 2)]; if (med > 0) vals[k] = 100 * (a.at(-1) - a[0]) / med; }
    note = "Where the models agree least is where the 2026 number is least settled.";
  } else if (M.layer == "history") {
    title = `NASS final ${crop} acres harvested, ${M.year}`;
    MAP.history.filter(r => r.year == M.year && r[crop] != null).forEach(r => vals[r.state] = r[crop]);
  } else if (M.layer == "error") {
    const id = M.errModel[crop]; ramp = SEQ2; fmt = v => v.toFixed(1) + "%";
    title = id ? `Mean miss by state, ${S.y0}–${S.y1} · ${MODELS[id] ? MODELS[id].model + " (" + MODELS[id].source + ")" : id}` : `No state-level backtest for ${crop} yet`;
    if (id) { const e = stateErrors(id); for (const k in e) vals[k] = e[k].v; }
    note = "Average |predicted − actual| / actual per state. Only folders that keep state-level predictions appear here.";
  } else if (M.layer == "context") {
    const sg = SIGNALS[M.signal]; title = `${sg.label}, ${M.year}`; fmt = sg.fmt; div = !!sg.div; ramp = sg.ramp || SEQ;
    MAP.history.filter(r => r.year == M.year && r[M.signal] != null).forEach(r => vals[r.state] = r[M.signal]);
  } else if (M.layer == "dairy" || M.layer == "silage_county") {
    const key = M.layer == "dairy" ? "milk_cows" : "silage", yrs = EXT.county.census_years; if (!yrs.includes(M.cyear)) M.cyear = yrs.at(-1);
    title = (M.layer == "dairy" ? "Milk cows per county, USDA census " : "Silage acres per county, USDA census ") + M.cyear; ramp = M.layer == "dairy" ? SEQ2 : SEQ;
    fmt = M.layer == "dairy" ? v => kfmt(v) + " cows" : v => kfmt(v) + " acres"; Object.assign(vals, EXT.county[key][M.cyear] || {});
    note = "Counties the census did not publish (to protect individual farms) show as no data.";
  } else if (M.layer == "weather") {
    const yrs = Object.keys(EXT.county.weather).map(Number); if (!yrs.includes(M.wyear)) M.wyear = Math.max(...yrs.filter(y => y < 2026));
    const i = M.wx == "rain" ? 0 : 1; div = true; var flip = M.wx == "rain"; fmt = v => (v >= 0 ? "+" : "") + (100 * v).toFixed(M.wx == "rain" ? 0 : 1) + "%";
    title = `${M.wx == "rain" ? "Rain" : "Heat (growing degree days)"} May\u2013Sep ${M.wyear}, vs the county's normal`;
    const w = EXT.county.weather[M.wyear] || {}; for (const f in w) if (w[f][i] != null) vals[f] = w[f][i];
  } else if (M.layer == "frost") {
    const yrs = Object.keys(EXT.county.weather).map(Number); if (!yrs.includes(M.wyear)) M.wyear = Math.max(...yrs.filter(y => y < 2026));
    title = `First fall frost, ${M.wyear}`; fmt = doyDate; ramp = SEQ;
    const w = EXT.county.weather[M.wyear] || {}; for (const f in w) if (w[f][2] != null) vals[f] = w[f][2];
    note = "Darker = earlier frost.";
  } else if (M.layer == "harvest") {
    title = "Usual date half the silage is chopped (5-year average)"; fmt = doyDate; ramp = SEQ;
    for (const st in EXT.harvest) if (EXT.harvest[st].typical_half_doy != null) vals[st] = EXT.harvest[st].typical_half_doy;
    note = "USDA tracks silage harvest progress in about 20 states; the rest show as no data. Click a state to see 2026 against its usual pace.";
  } else if (M.layer == "money" || M.layer == "price") {
    const yrs = [...new Set(Object.values(EXT.money).flatMap(o => Object.keys(o).map(Number)))].sort((a, b) => a - b);
    if (!yrs.includes(M.myear)) M.myear = yrs.filter(y => Object.values(EXT.money).some(o => o[y]?.value != null)).at(-1);
    const key = M.layer == "money" ? "value" : "price"; ramp = SEQ; fmt = M.layer == "money" ? money : v => "$" + v.toFixed(2) + "/bu";
    title = M.layer == "money" ? `Value of the corn-for-grain crop, ${M.myear}` : `Corn price received, ${M.myear} marketing year`;
    for (const st in EXT.money) { const r = EXT.money[st][M.myear]; if (r && r[key] != null) vals[st] = r[key]; }
  } else if (M.layer == "satellite") {
    title = "Where the satellite looks"; fmt = v => v ? "in the satellite sample" : ""; ramp = SEQ;
    (EXT.satellite.sample_states || []).forEach(st => vals[st] = 1);
    note = EXT.satellite.note;
  }
  return {vals, fmt, ramp, div, title, note, county: COUNTY_LAYERS.has(M.layer), flip: typeof flip != "undefined" && flip,
    explain: (LAYERS.find(l => l[0] == M.layer) || [])[2] || ""};
}
function classify(vals, ramp, div, flip) {
  const DV = flip ? [...DIV].reverse() : DIV;
  const xs = Object.values(vals).filter(v => v != null && isFinite(v));
  if (!xs.length) return {color: () => NODATA, bins: []};
  if (div) {
    const a = xs.map(Math.abs).sort((p, q) => p - q), m = a[Math.floor(0.95 * (a.length - 1))] || a.at(-1) || 1;
    const edges = [Math.min(...xs), -m * 0.6, -m * 0.25, -m * 0.05, m * 0.05, m * 0.25, m * 0.6, Math.max(...xs)];
    const color = v => v == null ? NODATA : DV[Math.min(6, Math.max(0, (v > edges.at(-1) ? 7 : edges.findIndex((e, i) => i > 0 && v <= e)) - 1))];
    return {color, bins: DV.map((c, i) => ({c, lo: edges[i], hi: edges[i + 1]}))};
  }
  const s = [...xs].sort((a, b) => a - b), q = i => s[Math.min(s.length - 1, Math.floor(i * s.length / 7))];
  const edges = [s[0], q(1), q(2), q(3), q(4), q(5), q(6), s.at(-1)];
  const color = v => { if (v == null) return NODATA; for (let i = 1; i < 8; i++) if (v <= edges[i]) return ramp[i - 1]; return ramp[6]; };
  return {color, bins: ramp.map((c, i) => ({c, lo: edges[i], hi: edges[i + 1]}))};
}

// ---------------------------------------------------------------- counties (TopoJSON decoded here, no library)
function topoPaths(topo, objName) {
  const [sx, sy] = topo.transform ? topo.transform.scale : [1, 1], [tx, ty] = topo.transform ? topo.transform.translate : [0, 0];
  const arcs = topo.arcs.map(a => { let x = 0, y = 0; return a.map(([dx, dy]) => { x += dx; y += dy; return [x * sx + tx, y * sy + ty]; }); });
  const ring = idx => { const pts = []; idx.forEach(i => { const a = i < 0 ? arcs[~i].slice().reverse() : arcs[i]; a.forEach((p, j) => { if (j || !pts.length) pts.push(p); }); });
    return "M" + pts.map(p => p[0].toFixed(1) + "," + p[1].toFixed(1)).join("L") + "Z"; };
  return topo.objects[objName].geometries.map(g => ({id: g.id, name: g.properties?.name,
    d: g.type == "Polygon" ? g.arcs.map(ring).join("") : g.type == "MultiPolygon" ? g.arcs.map(p => p.map(ring).join("")).join("") : ""}));
}
function buildCounties() {
  const g = svgEl("g", {id: "counties"}); $("#states").after(g);
  CTY.forEach(c => { const p = svgEl("path", {d: c.d, class: "cty", "data-fips": c.id});
    p.addEventListener("pointermove", e => hoverCounty(e, c.id)); p.addEventListener("pointerleave", () => { $("#tip").hidden = true; });
    p.addEventListener("click", () => { if (dragged) return; const st = stateOfFips(c.id); if (st) select(st); }); g.append(p); });
}
const FIPS = {"01":"AL","02":"AK","04":"AZ","05":"AR","06":"CA","08":"CO","09":"CT","10":"DE","11":"DC","12":"FL","13":"GA","15":"HI","16":"ID","17":"IL","18":"IN","19":"IA","20":"KS","21":"KY","22":"LA","23":"ME","24":"MD","25":"MA","26":"MI","27":"MN","28":"MS","29":"MO","30":"MT","31":"NE","32":"NV","33":"NH","34":"NJ","35":"NM","36":"NY","37":"NC","38":"ND","39":"OH","40":"OK","41":"OR","42":"PA","44":"RI","45":"SC","46":"SD","47":"TN","48":"TX","49":"UT","50":"VT","51":"VA","53":"WA","54":"WV","55":"WI","56":"WY","72":"PR"};
const stateOfFips = f => FIPS[String(f).slice(0, 2)];
function hoverCounty(e, f) {
  const v = CUR?.vals[f], t = $("#tip"), name = EXT.county.names[f] || CTY.find(c => c.id == f)?.name || f;
  t.replaceChildren(el("b", {textContent: name}), el("div", {textContent: v == null ? "No data" : CUR.fmt(v)}), el("div", {className: "muted", textContent: "Click to open the state"}));
  t.hidden = false; t.style.left = Math.min(e.clientX + 14, innerWidth - 260) + "px"; t.style.top = e.clientY + 14 + "px";
}
// Albers USA (lower 48), identical to d3.geoAlbersUsa().scale(1300).translate([487.5, 305]) used for the outlines
const ALB = (() => { const r = Math.PI / 180, y0 = 29.5 * r, y1 = 45.5 * r, n = (Math.sin(y0) + Math.sin(y1)) / 2, c = 1 + Math.sin(y0) * (2 * n - Math.sin(y0)), r0 = Math.sqrt(c) / n;
  const raw = (x, y) => { const rr = Math.sqrt(c - 2 * n * Math.sin(y)) / n; x *= n; return [rr * Math.sin(x), r0 - rr * Math.cos(x)]; };
  const k = 1300, cen = raw(-0.6 * r, 38.7 * r), dx = 487.5 - k * cen[0], dy = 305 + k * cen[1];
  return (lon, lat) => { const [x, y] = raw((lon + 96) * r, lat * r); return [dx + k * x, dy - k * y]; }; })();

// ---------------------------------------------------------------- map drawing, pan and zoom
const NS = "http://www.w3.org/2000/svg";
function svgEl(t, a = {}) { const n = document.createElementNS(NS, t); for (const k in a) n.setAttribute(k, a[k]); return n; }
function buildMap() {
  const svg = $("#usmap"); svg.setAttribute("viewBox", `${VB.x} ${VB.y} ${VB.w} ${VB.h}`);
  const g = svgEl("g", {id: "zoomg"}); svg.replaceChildren(g);
  g.append(svgEl("path", {d: GEO.nation, class: "nation"}));
  const states = svgEl("g", {id: "states"}); g.append(states);
  GEO.states.forEach(s => {
    const code = s.code; const p = svgEl("path", {d: s.d, class: "st", "data-code": code, tabindex: 0}); p.setAttribute("aria-label", s.name);
    p.addEventListener("pointermove", e => hover(e, code)); p.addEventListener("pointerleave", () => { $("#tip").hidden = true; });
    p.addEventListener("click", e => { if (dragged) return; select(code); });
    p.addEventListener("keydown", e => { if (e.key == "Enter") select(code); });
    states.append(p);
  });
  g.append(svgEl("path", {d: GEO.borders, class: "borders"}));
  const sel = svgEl("path", {id: "selpath", class: "selpath"}); g.append(sel);
  g.append(svgEl("g", {id: "markers"}));
  const labels = svgEl("g", {id: "labels"}); g.append(labels);
  GEO.states.forEach(s => { const t = svgEl("text", {x: s.c[0], y: s.c[1], "data-code": s.code, class: "lbl"}); t.textContent = s.code; labels.append(t); });
  wirePanZoom(svg); M.built = true;
}
let dragged = false;
function wirePanZoom(svg) {
  let start = null;
  const pt = e => { const q = svg.createSVGPoint(); q.x = e.clientX; q.y = e.clientY; const m = q.matrixTransform(svg.getScreenCTM().inverse()); return [m.x, m.y]; };
  svg.addEventListener("pointerdown", e => { start = {p: pt(e), tx: M.tx, ty: M.ty}; dragged = false; });
  addEventListener("pointermove", e => { if (!start) return; const p = pt(e), dx = p[0] - start.p[0], dy = p[1] - start.p[1];
    if (Math.abs(dx) + Math.abs(dy) > 3) { dragged = true; svg.classList.add("grabbing"); }
    if (dragged) { M.tx = start.tx + dx; M.ty = start.ty + dy; applyT(); } });
  addEventListener("pointerup", () => { start = null; svg.classList.remove("grabbing"); setTimeout(() => dragged = false, 0); });
  svg.addEventListener("wheel", e => { e.preventDefault(); zoomAt(pt(e), Math.exp(-e.deltaY * 0.0015)); }, {passive: false});
  svg.addEventListener("dblclick", e => { e.preventDefault(); zoomAt(pt(e), 2, true); });
}
function zoomAt([x, y], f, animate) {
  const k = Math.min(12, Math.max(1, M.k * f)), r = k / M.k;
  const target = {k, tx: x - (x - M.tx) * r, ty: y - (y - M.ty) * r};
  animate ? tween(target) : (Object.assign(M, target), applyT());
}
function applyT() {
  $("#zoomg").setAttribute("transform", `translate(${M.tx},${M.ty}) scale(${M.k})`);
  document.querySelectorAll("#labels text").forEach(t => {
    const s = GEO.states.find(s => s.code == t.dataset.code), w = (s.b[2] - s.b[0]) * M.k;
    t.style.fontSize = (10 / M.k) + "px"; t.style.display = w > 26 && hasValue(t.dataset.code) ? "" : "none"; });
  $("#selpath").setAttribute("stroke-width", 2.2 / M.k);
  document.querySelectorAll("#markers circle").forEach(c => { c.setAttribute("r", 6 / M.k); c.setAttribute("stroke-width", 2 / M.k); });
  document.querySelectorAll("#markers text").forEach(t => { t.style.fontSize = (11 / M.k) + "px"; t.setAttribute("dx", 9 / M.k); });
  document.querySelectorAll("#states .st").forEach(p => p.setAttribute("stroke-width", 0.5 / M.k));
  $("#zoomlvl").textContent = M.k.toFixed(1) + "×";
}
let CUR = null;
function hasValue(code) { return CUR && (CUR.county || CUR.vals[code] != null); }
function tween(target, ms = 260) {
  const from = {k: M.k, tx: M.tx, ty: M.ty}, t0 = performance.now(), reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce) { Object.assign(M, target); return applyT(); }
  const step = now => { const t = Math.min(1, (now - t0) / ms), e = 1 - Math.pow(1 - t, 3);
    for (const k of ["k", "tx", "ty"]) M[k] = from[k] + (target[k] - from[k]) * e; applyT(); if (t < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}
function zoomToState(code) {
  const s = GEO.states.find(s => s.code == code); if (!s) return;
  const [x0, y0, x1, y1] = s.b, k = Math.min(8, 0.5 * Math.min(VB.w / (x1 - x0), VB.h / (y1 - y0)));
  const kk = Math.max(1.6, k);
  tween({k: kk, tx: VB.x + VB.w * 0.45 - kk * (x0 + x1) / 2, ty: VB.y + VB.h * 0.52 - kk * (y0 + y1) / 2});
}
function resetView() { tween({k: 1, tx: 0, ty: 0}); }

function hover(e, code) {
  const v = CUR?.vals[code], name = NAMES[code] || code, t = $("#tip");
  const fc = M.fcModel[M.crop] ? fcValue(M.fcModel[M.crop], code) : null;
  t.replaceChildren(el("b", {textContent: name}), el("div", {textContent: v == null ? "No data for this layer" : CUR.fmt(v)}),
    M.layer != "forecast" && fc ? el("div", {className: "muted", textContent: `2026 forecast ${kfmt(fc.predicted)} acres`}) : null,
    el("div", {className: "muted", textContent: "Click for details"}));
  t.hidden = false; t.style.left = Math.min(e.clientX + 14, innerWidth - 260) + "px"; t.style.top = e.clientY + 14 + "px";
}

// ---------------------------------------------------------------- side panel
function miniLine(series, {height = 150, fmt = kfmt, xfmt = x => x, hiCap = null} = {}) {
  const W = 340, H = height, L = 44, R = 10, T = 10, B = 22;
  const pts = series.flatMap(s => s.pts), xs = pts.map(p => p[0]), ys = pts.flatMap(p => [p[1], p[2] ?? p[1], p[3] ?? p[1]]).filter(v => v != null);
  if (!pts.length) return el("p", {className: "note", textContent: "No history for this state."});
  const x0 = Math.min(...xs), x1 = Math.max(...xs); let lo = Math.min(...ys), hi = Math.max(...ys); const pad = (hi - lo) * 0.12 || hi * 0.1 || 1; lo = Math.max(0, lo - pad); hi += pad; if (hiCap != null) hi = Math.min(hi, hiCap);
  const X = x => L + (x1 == x0 ? 0.5 : (x - x0) / (x1 - x0)) * (W - L - R), Y = v => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  const svg = svgEl("svg", {viewBox: `0 0 ${W} ${H}`, width: "100%"});
  for (let i = 0; i <= 3; i++) { const v = lo + i * (hi - lo) / 3; svg.append(svgEl("line", {x1: L, x2: W - R, y1: Y(v), y2: Y(v), class: "grid"}));
    const t = svgEl("text", {x: L - 5, y: Y(v) + 3, "text-anchor": "end"}); t.textContent = fmt(v); svg.append(t); }
  [x0, Math.round((x0 + x1) / 2), x1].forEach(x => { const t = svgEl("text", {x: X(x), y: H - 6, "text-anchor": "middle"}); t.textContent = xfmt(x); svg.append(t); });
  series.forEach(s => {
    if (s.kind == "line") { svg.append(svgEl("path", {d: s.pts.map((p, i) => (i ? "L" : "M") + X(p[0]) + "," + Y(p[1])).join(""), fill: "none", stroke: s.color, "stroke-width": 2}));
      s.pts.forEach(p => svg.append(svgEl("circle", {cx: X(p[0]), cy: Y(p[1]), r: 2.5, fill: s.color}))); }
    else s.pts.forEach(p => { if (p[2] != null && p[3] != null) svg.append(svgEl("line", {x1: X(p[0]), x2: X(p[0]), y1: Y(p[2]), y2: Y(p[3]), stroke: s.color, "stroke-width": 2, "stroke-linecap": "round"}));
      svg.append(svgEl("circle", {cx: X(p[0]) + (s.dx || 0), cy: Y(p[1]), r: s.r || 4, fill: s.color, stroke: "var(--panel)", "stroke-width": 1.5})); });
  });
  return svg;
}
function extraBlocks(code) {
  const kids = [];
    const hv = EXT.harvest[code];
  if (hv) { kids.push(el("h3", {textContent: `Silage harvest pace, ${hv.latest_year}`}));
    const diff = hv.half_doy != null && hv.typical_half_doy != null ? hv.half_doy - hv.typical_half_doy : null;
    kids.push(el("p", {textContent: hv.half_doy != null ? `Half was chopped by ${doyDate(hv.half_doy)}` + (diff != null ? `, ${Math.abs(diff)} days ${diff < 0 ? "earlier" : diff > 0 ? "later" : "same as"} ${diff ? "than usual" : "usual"} (usually ${doyDate(hv.typical_half_doy)}).` : ".")
      : `${hv.latest_pct ?? "\u2014"}% chopped by ${hv.latest_week || "\u2014"}; usually half by ${doyDate(hv.typical_half_doy)}.`}),
      miniLine([{kind: "line", color: "var(--muted)", pts: hv.avg_curve}, {kind: "line", color: "var(--accent)", pts: hv.curve}], {height: 130, fmt: v => Math.round(v) + "%", xfmt: doyDate, hiCap: 100}),
      el("p", {className: "note", textContent: `Gold: ${hv.latest_year}. Gray: average of the ${hv.years_used} years before. Percent of silage chopped.`})); }
  const mo = EXT.money[code];
  if (mo) { const yrs = Object.keys(mo).map(Number).filter(y => mo[y].value != null).sort((a, b) => a - b);
    if (yrs.length) { kids.push(el("h3", {textContent: "What the corn-for-grain crop was worth"}),
      miniLine([{kind: "line", color: "var(--s3)", pts: yrs.map(y => [y, mo[y].value])}], {height: 120, fmt: money}),
      el("p", {className: "note", textContent: `${yrs.at(-1)}: ${money(mo[yrs.at(-1)].value)} at $${mo[yrs.at(-1)].price?.toFixed(2)}/bu.`})); } }
  if ((EXT.satellite.sample_states || []).includes(code)) kids.push(el("p", {className: "callout", textContent: "This state is in the satellite sample (one of the 15 states with the most silage)."}));
  return kids;
}
function panel() {
  const box = $("#sp"), crop = M.crop, code = M.sel, id = M.fcModel[crop];
  const kids = [];
  if (!code) {
    const years = [...new Set(MAP.history.map(r => r.year))].sort((a, b) => a - b);
    const us = years.map(y => [y, MAP.history.filter(r => r.year == y).reduce((a, r) => a + (r[crop] || 0), 0)]).filter(p => p[1] > 0);
    const tot = usTotal(id, crop);
    kids.push(el("div", {className: "eyebrow", textContent: "United States · " + crop}),
      el("div", {className: "hero", textContent: tot ? kfmt(tot.v) : "—"}),
      el("div", {className: "note", textContent: tot ? `2026 forecast, acres · ${modelLabel(id)} · ${tot.how}${tot.lo != null ? ` · 80% ${kfmt(tot.lo)}–${kfmt(tot.hi)}` : ""}` : "No forecast"}),
      el("h3", {textContent: "NASS final acres, all states shown"}),
      miniLine([{kind: "line", color: "var(--s1)", pts: us}, ...(tot ? [{kind: "dots", color: "var(--accent)", pts: [[2026, tot.v, tot.lo, tot.hi]]}] : [])]),
      el("p", {className: "note", textContent: "Blue: NASS finals. Gold: the 2026 forecast. Click any state for its own history and every model's forecast."}));
    const ranked = Object.entries(CUR.vals).filter(([, v]) => v != null).sort((a, b) => b[1] - a[1]).slice(0, 8);
    if (ranked.length) { kids.push(el("h3", {textContent: CUR.county ? "Top counties on this layer" : M.layer == "harvest" ? "Latest states to chop" : "Top states on this layer"}));
      const t = el("table", {className: "mini"}); ranked.forEach(([k, v]) => { const label = CUR.county ? (EXT.county.names[k] || k) : (NAMES[k] || k), st = CUR.county ? stateOfFips(k) : k;
      const tr = el("tr", {}, el("td", {textContent: label}), el("td", {className: "n", textContent: CUR.fmt(v)})); tr.onclick = () => select(st); t.append(tr); }); kids.push(t); }
  } else {
    const name = NAMES[code] || code; let v = CUR.vals[code];
    if (CUR.county && (M.layer == "dairy" || M.layer == "silage_county")) { v = 0; let n = 0; for (const f in CUR.vals) if (stateOfFips(f) == code) { v += CUR.vals[f]; n++; } if (!n) v = null; }
    const close = el("button", {className: "ghost", textContent: "← United States"}); close.onclick = () => { M.sel = null; draw(); resetView(); };
    const rows = MAP.history.filter(r => r.state == code && r[crop] != null).map(r => [r.year, r[crop]]);
    const fcs = fcModels(crop).map(m => ({m, r: fcValue(m.model_id, code)})).filter(x => x.r);
    kids.push(close, el("div", {className: "eyebrow", style: "margin-top:12px", textContent: `${name} · ${crop}`}),
      el("div", {className: "hero", textContent: v == null ? "—" : CUR.fmt(v)}), el("div", {className: "note", textContent: CUR.title}));
    const extrasFirst = ["harvest", "money", "price", "satellite"].includes(M.layer);
    if (extrasFirst) kids.push(...extraBlocks(code));
    kids.push(el("h3", {textContent: `${crop[0].toUpperCase() + crop.slice(1)} acres: history and 2026 forecasts`}),
      miniLine([{kind: "line", color: "var(--s1)", pts: rows},
        ...fcs.map((x, i) => ({kind: "dots", color: x.m.model_id == id ? "var(--accent)" : "var(--muted)", r: x.m.model_id == id ? 4.5 : 3, dx: (i - fcs.length / 2) * 2.2,
          pts: [[2026, x.r.predicted, x.m.model_id == id ? x.r.lo80 : null, x.m.model_id == id ? x.r.hi80 : null]]}))]),
      el("p", {className: "note", textContent: "Blue: NASS finals. Gold: the selected model with its 80% range. Gray: the other models."}));
    if (fcs.length) { kids.push(el("h3", {textContent: `2026 forecasts (${fcs.length} models)`}));
      const t = el("table", {className: "mini"}); fcs.sort((a, b) => a.r.predicted - b.r.predicted).forEach(x => {
        const tr = el("tr", {className: x.m.model_id == id ? "on" : ""}, el("td", {textContent: modelLabel(x.m.model_id)}),
          el("td", {className: "n", textContent: kfmt(x.r.predicted)}), el("td", {className: "n muted", textContent: x.r.lo80 != null ? `${kfmt(x.r.lo80)}–${kfmt(x.r.hi80)}` : ""}));
        tr.onclick = () => { M.fcModel[crop] = x.m.model_id; draw(); }; t.append(tr); }); kids.push(t); }
    const errs = errModels(crop).map(mid => ({mid, e: stateErrors(mid)[code]})).filter(x => x.e).sort((a, b) => a.e.v - b.e.v);
    if (errs.length) { kids.push(el("h3", {textContent: `Who has called ${code} best, ${S.y0}–${S.y1}`}));
      const t = el("table", {className: "mini"}); const mx = Math.max(...errs.map(x => x.e.v));
      errs.slice(0, 8).forEach(x => t.append(el("tr", {}, el("td", {textContent: MODELS[x.mid]?.model || x.mid}),
        el("td", {className: "barcell"}, el("i", {style: `width:${100 * x.e.v / mx}%`})), el("td", {className: "n", textContent: x.e.v.toFixed(1) + "%"}))));
      kids.push(t, el("p", {className: "note", textContent: "Average miss per year in this state. Only folders that keep state-level predictions appear."})); }
    if (!extrasFirst) kids.push(...extraBlocks(code));
    const h = hist(code, lastActualYear(crop));
    if (h) { kids.push(el("h3", {textContent: `Season signals, ${h.year}`}));
      const t = el("table", {className: "mini"}); Object.entries(SIGNALS).forEach(([k, sg]) => { if (h[k] != null) t.append(el("tr", {}, el("td", {textContent: sg.label}), el("td", {className: "n", textContent: sg.fmt(h[k])}))); }); kids.push(t); }
  }
  box.replaceChildren(...kids.filter(Boolean));
}

// ---------------------------------------------------------------- controls, KPIs, legend
function kpis() {
  const tiles = [];
  for (const crop of ["silage", "grain"]) { const id = M.fcModel[crop], t = usTotal(id, crop);
    tiles.push(el("div", {className: "kpi"}, el("div", {className: "eyebrow", textContent: `2026 ${crop}, US acres`}), el("div", {className: "big", textContent: t ? kfmt(t.v) : "—"}),
      el("div", {className: "note", textContent: t ? modelLabel(id) + (t.lo != null ? ` · 80% ${kfmt(t.lo)}–${kfmt(t.hi)}` : "") : "no forecast yet"}))); }
  const pub = (CAT.models || []).filter(c => Object.values(MODELS).some(m => m.model == c.id && m.target == c.crop)).length;
  tiles.push(el("div", {className: "kpi"}, el("div", {className: "eyebrow", textContent: "Models on the board"}), el("div", {className: "big", textContent: D.models.length}),
    el("div", {className: "note", textContent: `${new Set(D.models.map(m => m.source)).size} folders · ${D.field.length} field-model runs`})));
  tiles.push(el("div", {className: "kpi"}, el("div", {className: "eyebrow", textContent: "Tier A / B published"}), el("div", {className: "big", textContent: `${pub} / ${(CAT.models || []).length}`}),
    el("div", {className: "note", textContent: pub ? "filling in as results land" : "training · results to follow"})));
  const best = Object.values(MODELS).filter(m => m.target == "silage").map(m => ({m, s: stats(m.model_id)})).filter(x => x.s.state != null && x.s.years >= 8).sort((a, b) => a.s.state - b.s.state)[0];
  tiles.push(el("div", {className: "kpi"}, el("div", {className: "eyebrow", textContent: `Best silage backtest, ${S.y0}–${S.y1}`}), el("div", {className: "big", textContent: best ? best.s.state.toFixed(2) + "%" : "—"}),
    el("div", {className: "note", textContent: best ? `${best.m.model} (${best.m.source}) · ${best.s.years} years · avg state miss` : ""})));
  $("#kpis").replaceChildren(...tiles);
}
function controls() {
  const crop = M.crop;
  const cropSeg = el("span", {className: "seg"}, ["silage", "grain"].map(c => { const b = el("button", {textContent: c[0].toUpperCase() + c.slice(1)}); b.setAttribute("aria-pressed", crop == c); b.onclick = () => { M.crop = c; draw(); }; return b; }));
  const layer = el("select", {"aria-label": "Layer", className: "layersel"}, LAYER_GROUPS.map(([g, ls]) => { const og = el("optgroup"); og.label = g;
    ls.forEach(([k, l]) => og.append(el("option", {value: k, textContent: l, selected: k == M.layer}))); return og; }));
  layer.onchange = e => { stopPlay(); M.layer = e.target.value; draw(); if (COUNTY_LAYERS.has(M.layer) && !M.sel) resetView(); };
  const cropMatters = ["forecast", "change", "disagree", "history", "error"].includes(M.layer);
  const parts = [el("span", {className: "ask", textContent: "Show me"}), layer, cropMatters ? cropSeg : null].filter(Boolean);
  if (M.layer == "dairy" || M.layer == "silage_county") { const yrs = EXT.county.census_years;
    parts.push(el("span", {className: "seg"}, yrs.map(y => { const b = el("button", {textContent: "Census " + y}); b.setAttribute("aria-pressed", M.cyear == y); b.onclick = () => { M.cyear = y; draw(); }; return b; }))); }
  if (M.layer == "weather") parts.push(el("span", {className: "seg"}, [["rain", "Rain"], ["heat", "Heat"]].map(([k, l]) => { const b = el("button", {textContent: l}); b.setAttribute("aria-pressed", M.wx == k); b.onclick = () => { M.wx = k; draw(); }; return b; })));
  if (M.layer == "weather" || M.layer == "frost") { const yrs = Object.keys(EXT.county.weather).map(Number).filter(y => y < 2026).sort((a, b) => a - b);
    const r = el("input", {type: "range", min: yrs[0], max: yrs.at(-1), step: 1, value: M.wyear || yrs.at(-1), "aria-label": "Year"}); r.oninput = e => { M.wyear = +e.target.value; draw(); };
    parts.push(el("span", {className: "yr"}, r, el("b", {className: "mono", textContent: M.wyear}))); }
  if (M.layer == "money" || M.layer == "price") { const yrs = [...new Set(Object.values(EXT.money).flatMap(o => Object.keys(o).map(Number)))].sort((a, b) => a - b);
    const r = el("input", {type: "range", min: yrs[0], max: yrs.at(-1), step: 1, value: M.myear, "aria-label": "Year"}); r.oninput = e => { M.myear = +e.target.value; draw(); };
    parts.push(el("span", {className: "yr"}, r, el("b", {className: "mono", textContent: M.myear}))); }
  if (["forecast", "change"].includes(M.layer)) { const s = el("select", {"aria-label": "Model"}, fcModels(crop).map(m => el("option", {value: m.model_id, textContent: modelLabel(m.model_id), selected: m.model_id == M.fcModel[crop]})));
    s.onchange = e => { M.fcModel[crop] = e.target.value; draw(); }; parts.push(s); }
  if (M.layer == "error") { const ids = errModels(crop); if (!M.errModel[crop] || !ids.includes(M.errModel[crop])) M.errModel[crop] = ids[0];
    if (ids.length) { const s = el("select", {"aria-label": "Model"}, ids.map(id => el("option", {value: id, textContent: (MODELS[id]?.model || id) + " (" + (MODELS[id]?.source || "") + ")", selected: id == M.errModel[crop]})));
      s.onchange = e => { M.errModel[crop] = e.target.value; draw(); }; parts.push(s); } }
  if (M.layer == "context") { const s = el("select", {"aria-label": "Signal"}, Object.entries(SIGNALS).map(([k, sg]) => el("option", {value: k, textContent: sg.label, selected: k == M.signal})));
    s.onchange = e => { M.signal = e.target.value; draw(); }; parts.push(s); }
  if (["history", "context"].includes(M.layer)) {
    const years = [...new Set(MAP.history.filter(r => (M.layer == "history" ? r[crop] : r[M.signal]) != null).map(r => r.year))].sort((a, b) => a - b);
    if (!years.includes(M.year)) M.year = years.at(-1);
    const r = el("input", {type: "range", min: years[0], max: years.at(-1), step: 1, value: M.year, "aria-label": "Year"}); r.oninput = e => { M.year = +e.target.value; stopPlay(); draw(); };
    const play = el("button", {className: "ghost", textContent: M.playing ? "Pause" : "▶ Play"}); play.onclick = () => M.playing ? stopPlay() : startPlay(years);
    parts.push(el("span", {className: "yr"}, r, el("b", {className: "mono", textContent: M.year}), play));
  }
  $("#mapctl").replaceChildren(...parts);
}
function startPlay(years) { let i = years[0] == M.year || M.year == years.at(-1) ? 0 : years.indexOf(M.year); M.year = years[i];
  M.playing = setInterval(() => { i++; if (i >= years.length) return stopPlay(); M.year = years[i]; draw(); }, 900); draw(); }
function stopPlay() { if (M.playing) { clearInterval(M.playing); M.playing = null; } }
function legend(cls) {
  const box = $("#legend-map");
  if (!cls.bins.length) { box.replaceChildren(el("div", {className: "what"}, el("b", {textContent: "What am I looking at? "}), CUR.explain), el("span", {className: "note", textContent: "No data for this layer yet"})); return; }
  const ends = CUR.div ? (M.layer == "weather" ? (M.wx == "rain" ? ["drier", "normal", "wetter"] : ["cooler", "normal", "hotter"]) : ["less", "same", "more"]) : M.layer == "error" ? ["closer", "", "further off"]
    : ["harvest", "frost"].includes(M.layer) ? ["earlier", "", "later"] : ["less", "", "more"];
  box.replaceChildren(...[el("div", {className: "what"}, el("b", {textContent: "What am I looking at? "}), CUR.explain), el("div", {className: "lt", textContent: CUR.title}), el("div", {className: "ramp"}, cls.bins.map(b => el("i", {style: `background:${b.c}`, title: `${CUR.fmt(b.lo)} to ${CUR.fmt(b.hi)}`}))),
    M.layer == "satellite" ? null : el("div", {className: "rl"}, el("span", {textContent: `${CUR.fmt(cls.bins[0].lo)} (${ends[0]})`}), el("span", {textContent: ends[1]}), el("span", {textContent: `${CUR.fmt(cls.bins.at(-1).hi)} (${ends[2]})`})),
    el("div", {className: "nd"}, el("i", {style: `background:${NODATA}`}), "no data"), CUR.note ? el("div", {className: "note", textContent: CUR.note}) : null].filter(Boolean));
}
function select(code) { M.sel = code; draw(); zoomToState(code); }

// ---------------------------------------------------------------- entry
async function mapTab() {
  if (!GEO) { const q = FRESH ? "?fresh=1" : "";
    const [g, m, x] = await Promise.all([fetch("/api/geo").then(r => r.json()), fetch("/api/map" + q).then(r => r.json()), fetch("/api/extras" + q).then(r => r.json())]);
    GEO = g; MAP = m; EXT = x;
    GEO.states.forEach(s => { s.code = FIPS[s.fips] || s.fips; NAMES[s.code] = s.name; });
    M.year = lastActualYear("silage"); }
  for (const c of ["silage", "grain"]) if (!M.fcModel[c] || !MODELS[M.fcModel[c]]) M.fcModel[c] = defaultModel(c);
  if (!M.built || !$("#zoomg")) buildMap();
  CUR = layerValues();
  if (CUR.county && !CTY) { $("#legend-map").replaceChildren(el("span", {className: "note", textContent: "Loading 3,000 counties\u2026"}));
    CTY = topoPaths(await fetch("/api/counties").then(r => r.json()), "counties"); buildCounties(); }
  const cls = classify(CUR.vals, CUR.ramp, CUR.div, CUR.flip);
  const LIGHT = new Set([SEQ[5], SEQ[6], SEQ2[5], SEQ2[6], DIV[2], DIV[4]]);  // labels go dark on light fills
  const stage = $("#usmap"); stage.classList.toggle("countymode", !!CUR.county);
  if (CUR.county) document.querySelectorAll("#counties .cty").forEach(p => { const v = CUR.vals[p.dataset.fips]; p.style.fill = cls.color(v); });
  document.querySelectorAll("#states .st").forEach(p => { const v = CUR.county ? null : CUR.vals[p.dataset.code], c = CUR.county ? "transparent" : M.layer == "satellite" ? (v ? "#2a78d6" : NODATA) : cls.color(v);
    p.style.fill = c; p.classList.toggle("nodata", !CUR.county && v == null);
    const lbl = document.querySelector(`#labels text[data-code="${p.dataset.code}"]`); if (lbl) lbl.classList.toggle("dark", LIGHT.has(c)); });
  const mk = $("#markers"); mk.replaceChildren();
  if (M.layer == "satellite") (EXT.satellite.points || []).forEach(pt => { const [x, y] = ALB(pt.lon, pt.lat);
    const c = svgEl("circle", {cx: x, cy: y, class: "mk"}); c.addEventListener("pointermove", e => { const t = $("#tip"); t.replaceChildren(el("b", {textContent: pt.label}), el("div", {textContent: pt.detail})); t.hidden = false; t.style.left = e.clientX + 14 + "px"; t.style.top = e.clientY + 14 + "px"; });
    c.addEventListener("pointerleave", () => $("#tip").hidden = true); const t = svgEl("text", {x, y, class: "mkl", dy: 4}); t.textContent = pt.label; mk.append(c, t); });
  const s = GEO.states.find(s => s.code == M.sel); $("#selpath").setAttribute("d", s ? s.d : "");
  kpis(); controls(); legend(cls); panel(); applyT(); helpCard();
}
function helpCard() {
  let seen = false; try { seen = localStorage.getItem("board-help") == "1"; } catch (e) { seen = true; }
  if (seen || $("#help")) return;
  const ok = el("button", {className: "act", textContent: "Got it"});
  const card = el("div", {id: "help"}, el("b", {textContent: "How to use this map"}),
    el("ol", {}, el("li", {textContent: "Pick what to show in \u201cShow me\u201d (top left)."}), el("li", {textContent: "Drag to move, scroll or use + \u2212 to zoom."}),
      el("li", {textContent: "Click any state to see its history and every model's 2026 number."}), el("li", {textContent: "The box at the bottom left explains the colors in plain words."})), ok);
  ok.onclick = () => { card.remove(); try { localStorage.setItem("board-help", "1"); } catch (e) { /* storage off */ } };
  $(".stage").append(card);
}
