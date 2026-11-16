// Map tab: a pannable, zoomable US map of every state-level number on the board.
// Reads /api/geo (pre-projected state outlines), /api/map (NASS history, season context, state-level
// backtest predictions) and the /api/board payload already loaded by page.html (D, MODELS, BT, CAT, S).
"use strict";
const SEQ = ["#0d366b", "#104281", "#1c5cab", "#2a78d6", "#5598e7", "#86b6ef", "#cde2fb"];           // blue, low -> high
const SEQ2 = ["#4a2412", "#6b3018", "#8f3f1e", "#b84d23", "#d95926", "#ef8a5f", "#f8c2a6"];          // orange, low -> high
const DIV = ["#184f95", "#3987e5", "#86b6ef", "#383835", "#f2a3a3", "#e66767", "#b83a3a"];          // down <- 0 -> up
const NODATA = "#1b2029";
const NAMES = {};
const VB = {x: -10, y: -14, w: 995, h: 640};   // a little room around the outlines
let GEO = null, MAP = null, EXT = null, CTY = null, M = {layer: "forecast", crop: "silage", fcModel: {}, errModel: {}, year: 2025, signal: "drought", wx: "rain", cyear: null, wyear: null, myear: null,
  sel: null, k: 1, tx: 0, ty: 0, playing: null, built: false, loc: null, nearMi: 50, satDay: 0, satT: null, satOpen: false, satOff: new Set(),
  wi: {mode: "custom", pct: 25, where: "ALL"}, fyear: null};
const MAXK = 40;                               // deep enough to read single counties
const GROUP_ICON = {"Our forecast": "\u{1F4C8}", "What happened before": "\u{1F4DC}", "Why acres change": "\u{1F33D}", "Satellite": "\u{1F6F0}️", "How good are the models": "\u{1F3AF}"};

// Layers, grouped by the question they answer. "explain" is shown under the map in plain words.
const LAYER_GROUPS = [
  ["Our forecast", [
    ["forecast", "Acres we expect in 2026", "Each state is colored by how many acres one of our models expects to be harvested in 2026. Lighter means more acres. Pick a different model in the next box."],
    ["change", "2026 compared with last year", "Red states are expected to harvest more acres than last year, blue states fewer. Gray means about the same."],
    ["whatif", "What if a drought hits?", "Drag the slider or replay a real drought year: the headline silage model adds the acres farmers chop when their corn fails. Red states gain the most silage, and those acres come out of the grain harvest."],
    ["disagree", "Where our models disagree", "How far apart our models' 2026 numbers are in each state. Lighter means the models disagree more, so the number there is less certain."]]],
  ["What happened before", [
    ["history", "Acres harvested each year", "The official USDA (NASS) count of acres harvested, year by year. Press Play to watch it change."]]],
  ["Why acres change", [
    ["dairy", "Where the dairy cows are (counties)", "Milk cows per county from the USDA Census of Agriculture. Silage is cow feed, so it is grown close to dairies: compare with the next layer. Many counties really do have only a handful of milk cows: a few small farms."],
    ["silage_county", "Where silage is grown (counties)", "Acres of corn chopped for silage per county from the USDA Census of Agriculture. Notice how it follows the dairy map."],
    ["feed", "Feed stress watch (counties)", "Milk cows in counties that had a dry growing season. When pasture and corn suffer, dairies run short of feed and more grain corn gets chopped for silage: these are the places to watch. Gray counties had a normal season."],
    ["weather", "This season's rain and heat (counties)", "Rain or heat from May to September compared with that county's normal. A dry, hot year can push farmers to chop failing grain corn for silage."],
    ["frost", "First fall frost (counties)", "The date of the first fall frost in each county. An early frost ends the season and can change what farmers harvest."],
    ["context", "Drought, crop condition and losses (states)", "Season signals by state: drought, corn rated poor, insurance weather losses, rain, heat and milk cows."],
    ["harvest", "When silage gets chopped", "The usual date by which half of a state's silage is chopped. Some states are half done by late August, others not until October, so one harvest calendar does not fit every state."],
    ["money", "What the corn crop is worth", "Corn harvested for grain times the price farmers received: the dollar value of each state's grain crop."],
    ["price", "Corn price farmers got", "The average price per bushel farmers received over the marketing year."],
    ["milk", "Milk price farmers got (latest month)", "What dairy farmers were paid for milk, in dollars per 100 pounds, in the latest month USDA has published. A better milk price can mean more cows to feed, and more silage."]]],
  ["Satellite", [
    ["satellite", "Where the satellite looks", "Highlighted states are where the satellite sample is being drawn: the 15 states with the most silage. Dots mark the fields with known answers used to test the satellite model."]]],
  ["How good are the models", [
    ["error", "How far off each model was, by state", "For each state, how far a model's past forecasts were from the official count, on average. Darker means closer, so darker is better."]]],
];
const LAYERS = LAYER_GROUPS.flatMap(g => g[1]);
const COUNTY_LAYERS = new Set(["dairy", "silage_county", "weather", "frost", "feed"]);
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
  const head = (CAT.models || []).find(c => c.crop == crop && c.headline);
  const headM = head && Object.values(MODELS).find(m => m.model == head.id && m.target == crop && m.has_forecast);
  if (headM) return headM.model_id;
  const tierPub = (CAT.models || []).filter(c => c.crop == crop).map(c => Object.values(MODELS).find(m => m.model == c.id && m.target == crop && m.has_forecast)).filter(Boolean);
  if (tierPub.length) return tierPub[0].model_id;
  const bench = (CAT.benchmarks || []).find(b => b.crop == crop && MODELS[b.model_id]?.has_forecast);
  return bench ? bench.model_id : fcModels(crop)[0]?.model_id;
}
function modelLabel(id) { const m = MODELS[id]; if (!m) return id; const b = (CAT.benchmarks || []).find(b => b.model_id == id);
  return b && b.label != m.label ? `${m.label}: ${b.label}` : `${m.label} \u00b7 ${m.source_label}`; }

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
    title = id ? `Average miss by state, ${S.y0}–${S.y1} · ${MODELS[id] ? MODELS[id].label + " (" + MODELS[id].source_label + ")" : id}` : `No state-level backtest for ${crop} yet`;
    if (id) { const e = stateErrors(id); for (const k in e) vals[k] = e[k].v; }
    note = "Average |predicted − actual| / actual per state. Only folders that keep state-level predictions appear here.";
  } else if (M.layer == "context") {
    const sg = SIGNALS[M.signal]; title = `${sg.label}, ${M.year}`; fmt = sg.fmt; div = !!sg.div; ramp = sg.ramp || SEQ;
    MAP.history.filter(r => r.year == M.year && r[M.signal] != null).forEach(r => vals[r.state] = r[M.signal]);
  } else if (M.layer == "dairy" || M.layer == "silage_county") {
    const key = M.layer == "dairy" ? "milk_cows" : "silage", yrs = EXT.county.census_years; if (!yrs.includes(M.cyear)) M.cyear = yrs.at(-1);
    title = (M.layer == "dairy" ? "Milk cows per county, USDA census " : "Silage acres per county, USDA census ") + M.cyear; ramp = M.layer == "dairy" ? SEQ2 : SEQ;
    fmt = M.layer == "dairy" ? v => kfmt(v) + " cows" : v => kfmt(v) + " acres"; Object.assign(vals, EXT.county[key][M.cyear] || {});
    var est = new Set(EXT.county.estimated?.[key]?.[M.cyear] || []);
    note = est.size ? `USDA withholds ${est.size.toLocaleString("en-US")} counties to protect individual farms. Those are estimated (marked ≈) from ${M.layer == "dairy" ? "how many farms of each herd size the county has" : "their dairy herds"}, scaled to the state's Census total.`
      : "Counties the census did not publish (to protect individual farms) show as no data.";
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
  } else if (M.layer == "milk") {
    const latest = Object.values(EXT.milk).map(a => a.at(-1)?.[0]).filter(Boolean).sort().at(-1); ramp = SEQ; fmt = v => "$" + v.toFixed(2) + "/cwt";
    title = `Milk price received, ${latest ? new Date(latest + "-15").toLocaleDateString("en-US", {month: "long", year: "numeric"}) : ""}`;
    for (const st in EXT.milk) { const r = EXT.milk[st].find(x => x[0] == latest); if (r) vals[st] = r[1]; }
    note = "USDA publishes monthly milk prices for the main dairy states only; the rest show as no data.";
  } else if (M.layer == "whatif") {
    const w = whatIf(); ramp = SEQ2; fmt = v => "+" + (v < 10 ? v.toFixed(1) : Math.round(v)) + "%";
    title = "Extra silage acres vs our 2026 forecast, by state";
    if (w) for (const st in w.states) if (w.states[st].pct > 0.05) vals[st] = w.states[st].pct;
    var stateFill = (cls, code) => vals[code] != null ? cls.color(vals[code]) : w?.states[code] ? "#383835" : NODATA;
    note = DR ? "" : "Drought data not loaded.";
  } else if (M.layer == "feed") {
    const yrs = feedYears(); if (!yrs.includes(M.fyear)) M.fyear = yrs.at(-1);
    const st = feedStats(M.fyear), cows = EXT.county.milk_cows[st.cy] || {}, w = EXT.county.weather[M.fyear] || {};
    for (const f in st.lvl) if (cows[f] > 0) vals[f] = cows[f];
    ramp = SEQ2; fmt = v => kfmt(v) + " cows"; title = `Milk cows in dry counties, ${M.fyear} season (cows: ${st.cy} Census)`;
    var est = new Set(EXT.county.estimated?.milk_cows?.[st.cy] || []);
    var fillFor = (cls, f) => vals[f] != null ? cls.color(vals[f]) : st.lvl[f] ? "#3a2418" : w[f] ? "#232b35" : NODATA;
    var feed = st;
    note = `${(st.watch / 1e6).toFixed(2)} million milk cows (${Math.round(100 * st.watch / Math.max(1, st.total))}% of the herd) are in dry counties; ${(st.severe / 1e6).toFixed(2)} million in very dry ones. Dry = May\u2013Sep rain at least 20% below normal, or 10% below in a hot summer; very dry = 30% below, or 20% below and hot. Mostly irrigated counties, where summer rain is normally under ${FEED_MIN_RAIN_MM} mm (much of the West), are not judged on rain.`;
  } else if (M.layer == "satellite") {
    title = "Where the satellite looks"; fmt = v => v ? "in the satellite sample" : ""; ramp = SEQ;
    (EXT.satellite.sample_states || []).forEach(st => vals[st] = 1);
    note = EXT.satellite.note;
  }
  return {vals, fmt, ramp, div, title, note, county: COUNTY_LAYERS.has(M.layer), flip: typeof flip != "undefined" && flip,
    est: typeof est != "undefined" ? est : new Set(), stateFill: typeof stateFill != "undefined" ? stateFill : null, fillFor: typeof fillFor != "undefined" ? fillFor : null, feed: typeof feed != "undefined" ? feed : null, explain: (LAYERS.find(l => l[0] == M.layer) || [])[2] || ""};
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
  const ringPts = idx => { const pts = []; idx.forEach(i => { const a = i < 0 ? arcs[~i].slice().reverse() : arcs[i]; a.forEach((p, j) => { if (j || !pts.length) pts.push(p); }); }); return pts; };
  const dOf = pts => "M" + pts.map(p => p[0].toFixed(1) + "," + p[1].toFixed(1)).join("L") + "Z";
  return topo.objects[objName].geometries.map(g => {
    const rings = g.type == "Polygon" ? g.arcs.map(ringPts) : g.type == "MultiPolygon" ? g.arcs.flatMap(p => p.map(ringPts)) : [];
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, best = null, bestA = 0;
    rings.forEach(r => { let a = 0, cx = 0, cy = 0;
      r.forEach((p, i) => { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]);
        const q = r[(i + 1) % r.length], c = p[0] * q[1] - q[0] * p[1]; a += c; cx += (p[0] + q[0]) * c; cy += (p[1] + q[1]) * c; });
      if (Math.abs(a) > bestA) { bestA = Math.abs(a); best = [cx / (3 * a), cy / (3 * a)]; } });
    return {id: g.id, name: g.properties?.name, d: rings.map(dOf).join(""), rings, b: [x0, y0, x1, y1], c: best || [(x0 + x1) / 2, (y0 + y1) / 2]};
  });
}
function inRings(rings, x, y) {          // even-odd rule over every ring: handles islands and holes
  let inside = false;
  for (const r of rings) for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
    const [xi, yi] = r[i], [xj, yj] = r[j];
    if ((yi > y) != (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside; }
  return inside;
}
function countyAt(x, y) { return (CTY || []).find(c => x >= c.b[0] && x <= c.b[2] && y >= c.b[1] && y <= c.b[3] && inRings(c.rings, x, y)) || null; }
async function loadCounties() {
  if (!CTY) { CTY = topoPaths(await fetch("/api/counties").then(r => r.json()), "counties"); CTY.forEach(c => CTYBY[c.id] = c); }
  if (!$("#counties")) buildCounties();
}
const CTYBY = {};
function buildCounties() {
  const g = svgEl("g", {id: "counties"}); $("#states").after(g);
  CTY.forEach(c => { const p = svgEl("path", {d: c.d, class: "cty", "data-fips": c.id});
    p.addEventListener("pointermove", e => hoverCounty(e, c.id)); p.addEventListener("pointerleave", () => { $("#tip").hidden = true; });
    p.addEventListener("click", () => { if (dragged) return; const st = stateOfFips(c.id); if (st) select(st); }); g.append(p); });
  g.after(svgEl("g", {id: "ctylabels"}));
}
function countyName(f) { return EXT.county.names[f] || (CTYBY[f]?.name ? CTYBY[f].name + ", " + stateOfFips(f) : f); }
const FIPS = {"01":"AL","02":"AK","04":"AZ","05":"AR","06":"CA","08":"CO","09":"CT","10":"DE","11":"DC","12":"FL","13":"GA","15":"HI","16":"ID","17":"IL","18":"IN","19":"IA","20":"KS","21":"KY","22":"LA","23":"ME","24":"MD","25":"MA","26":"MI","27":"MN","28":"MS","29":"MO","30":"MT","31":"NE","32":"NV","33":"NH","34":"NJ","35":"NM","36":"NY","37":"NC","38":"ND","39":"OH","40":"OK","41":"OR","42":"PA","44":"RI","45":"SC","46":"SD","47":"TN","48":"TX","49":"UT","50":"VT","51":"VA","53":"WA","54":"WV","55":"WI","56":"WY","72":"PR"};
const stateOfFips = f => FIPS[String(f).slice(0, 2)];
function hoverCounty(e, f) {
  const v = CUR?.vals[f], t = $("#tip"), name = countyName(f), est = CUR?.est?.has(f);
  const farms = M.layer == "dairy" ? EXT.county.farms?.[M.cyear]?.[f] : null;
  t.replaceChildren(...[el("b", {textContent: name}), el("div", {textContent: v == null ? "No data" : (est ? "≈ " : "") + CUR.fmt(v)}),
    farms != null ? el("div", {textContent: `${farms.toLocaleString("en-US")} dairy farm${farms == 1 ? "" : "s"}` + (v != null && farms ? ` · about ${kfmt(v / farms)} cows each` : "")}) : null,
    est ? el("div", {className: "muted", textContent: "Estimated: USDA withheld the exact number to protect individual farms."}) : null,
    el("div", {className: "muted", textContent: "Click to open the state"})].filter(Boolean));
  t.hidden = false; t.style.left = Math.min(e.clientX + 14, innerWidth - 300) + "px"; t.style.top = e.clientY + 14 + "px";
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
  const defs = svgEl("defs"), cp = svgEl("clipPath", {id: "usclip"});     // lower 48 only: Alaska and Hawaii are insets
  cp.append(svgEl("path", {d: GEO.states.filter(s => !["02", "15", "72"].includes(String(s.fips).padStart(2, "0"))).map(s => s.d).join("")})); defs.append(cp); g.append(defs);
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
  g.append(svgEl("g", {id: "overlays"}));
  const sel = svgEl("path", {id: "selpath", class: "selpath"}); g.append(sel);
  g.append(svgEl("g", {id: "markers"}));
  g.append(svgEl("g", {id: "locg"}));
  const labels = svgEl("g", {id: "labels"}); g.append(labels);
  GEO.states.forEach(s => { const t = svgEl("text", {x: s.c[0], y: s.c[1], "data-code": s.code, class: "lbl"}); t.textContent = s.code; labels.append(t); });
  wirePanZoom(svg); M.built = true; STP = null;
  svg.addEventListener("click", e => { if (typeof fieldMapClick == "function") fieldMapClick(e); }, true);
}
let dragged = false;
function svgPt(svg, e) { const q = svg.createSVGPoint(); q.x = e.clientX; q.y = e.clientY; const m = q.matrixTransform(svg.getScreenCTM().inverse()); return [m.x, m.y]; }
function wirePanZoom(svg) {
  // One finger / mouse drags, two fingers pinch, shift-drag draws a box to zoom into, wheel or trackpad pinch zooms at the pointer.
  const ptrs = new Map(); let start = null, pinch = null, box = null;
  const pt = e => svgPt(svg, e);
  svg.addEventListener("pointerdown", e => {
    if (e.button > 0) return;
    ptrs.set(e.pointerId, pt(e));
    if (ptrs.size == 2) { const [a, b] = [...ptrs.values()]; pinch = {d: Math.hypot(a[0] - b[0], a[1] - b[1]) || 1, k: M.k, tx: M.tx, ty: M.ty, c: [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]}; start = null; dragged = true; return; }
    if (e.shiftKey) { const p = pt(e); box = {p0: p, r: svgEl("rect", {class: "zbox", x: p[0], y: p[1], width: 0, height: 0})}; svg.append(box.r); dragged = true; return; }
    start = {p: pt(e), tx: M.tx, ty: M.ty}; dragged = false;
  });
  addEventListener("pointermove", e => {
    if (!ptrs.has(e.pointerId)) return; const p = pt(e); ptrs.set(e.pointerId, p);
    if (pinch && ptrs.size >= 2) { const [a, b] = [...ptrs.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]), c = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
      const k = Math.min(MAXK, Math.max(1, pinch.k * d / pinch.d)), cx = (pinch.c[0] - pinch.tx) / pinch.k, cy = (pinch.c[1] - pinch.ty) / pinch.k;
      Object.assign(M, clampT({k, tx: c[0] - cx * k, ty: c[1] - cy * k})); applyT(); return; }
    if (box) { const x = Math.min(p[0], box.p0[0]), y = Math.min(p[1], box.p0[1]); box.r.setAttribute("x", x); box.r.setAttribute("y", y);
      box.r.setAttribute("width", Math.abs(p[0] - box.p0[0])); box.r.setAttribute("height", Math.abs(p[1] - box.p0[1])); return; }
    if (!start) return; const dx = p[0] - start.p[0], dy = p[1] - start.p[1];
    if (Math.abs(dx) + Math.abs(dy) > 3) { dragged = true; svg.classList.add("grabbing"); }
    if (dragged) { Object.assign(M, clampT({k: M.k, tx: start.tx + dx, ty: start.ty + dy})); applyT(); } });
  const up = e => {
    ptrs.delete(e.pointerId); if (ptrs.size < 2) pinch = null;
    if (box) { const w = +box.r.getAttribute("width"), h = +box.r.getAttribute("height");
      if (w > 8 && h > 8) { const x = +box.r.getAttribute("x"), y = +box.r.getAttribute("y");
        zoomToRect([(x - M.tx) / M.k, (y - M.ty) / M.k, (x + w - M.tx) / M.k, (y + h - M.ty) / M.k], 1); }
      box.r.remove(); box = null; }
    start = null; svg.classList.remove("grabbing"); setTimeout(() => dragged = false, 0); };
  addEventListener("pointerup", up); addEventListener("pointercancel", up);
  svg.addEventListener("wheel", e => { e.preventDefault();
    const dy = e.deltaY * (e.deltaMode == 1 ? 16 : e.deltaMode == 2 ? 400 : 1);
    zoomAt(pt(e), Math.exp(-dy * (e.ctrlKey ? 0.012 : 0.0022))); }, {passive: false});   // ctrlKey = trackpad pinch
  svg.addEventListener("dblclick", e => { e.preventDefault(); zoomAt(pt(e), e.shiftKey ? 0.5 : 2.2, true); });
}
function clampT(t) {        // keep at least a fifth of the map on screen so it can't get lost off the edge
  const k = t.k, ax = VB.x + VB.w * 0.2, bx = VB.x + VB.w * 0.8, ay = VB.y + VB.h * 0.2, by = VB.y + VB.h * 0.8;
  t.tx = Math.min(bx - k * VB.x, Math.max(ax - k * (VB.x + VB.w), t.tx));
  t.ty = Math.min(by - k * VB.y, Math.max(ay - k * (VB.y + VB.h), t.ty)); return t;
}
function zoomAt([x, y], f, animate) {
  const k = Math.min(MAXK, Math.max(1, M.k * f)), r = k / M.k;
  const target = clampT({k, tx: x - (x - M.tx) * r, ty: y - (y - M.ty) * r});
  animate ? tween(target) : (Object.assign(M, target), applyT());
}
function zoomToRect([x0, y0, x1, y1], fill = 0.8, maxk = MAXK) {
  const k = Math.min(maxk, Math.max(1, fill * Math.min(VB.w / Math.max(1, x1 - x0), VB.h / Math.max(1, y1 - y0))));
  tween(clampT({k, tx: VB.x + VB.w / 2 - k * (x0 + x1) / 2, ty: VB.y + VB.h / 2 - k * (y0 + y1) / 2}));
}
const kToSlider = k => Math.round(100 * Math.log(k) / Math.log(MAXK)), sliderToK = v => Math.exp(v / 100 * Math.log(MAXK));
function applyT() {
  $("#zoomg").setAttribute("transform", `translate(${M.tx},${M.ty}) scale(${M.k})`);
  document.querySelectorAll("#labels text").forEach(t => {
    const s = GEO.states.find(s => s.code == t.dataset.code), w = (s.b[2] - s.b[0]) * M.k;
    t.style.fontSize = (10 / M.k) + "px"; t.style.display = w > 26 && hasValue(t.dataset.code) && !(CUR?.county && M.k >= 5) ? "" : "none"; });
  $("#selpath").setAttribute("stroke-width", 2.2 / M.k);
  const zs = $("#zslider"); if (zs && document.activeElement != zs) zs.value = kToSlider(M.k);
  document.querySelectorAll("#locg .scale").forEach(n => { for (const [a, k] of [["r", "r"], ["dy", "dy"]]) if (n.dataset[k]) n.setAttribute(a, n.dataset[k] / M.k);
    if (n.dataset.fontSize) { n.style.fontSize = n.dataset.fontSize / M.k + "px"; n.style.strokeWidth = 3 / M.k + "px"; }
    if (n.dataset.strokeWidth) n.style.strokeWidth = n.dataset.strokeWidth / M.k + "px"; });
  $("#usmap").classList.toggle("zoomed", M.k >= 3.5);
  clearTimeout(applyT.lbl); applyT.lbl = setTimeout(countyLabels, 90);
  document.querySelectorAll("#markers circle").forEach(c => { c.setAttribute("r", 6 / M.k); c.setAttribute("stroke-width", 2 / M.k); });
  document.querySelectorAll("#markers text").forEach(t => { t.style.fontSize = (11 / M.k) + "px"; t.setAttribute("dx", 9 / M.k); });
  $("#usmap").classList.toggle("z2", M.k >= 2.5);
  if (typeof scheduleLOD == "function") scheduleLOD();
  document.querySelectorAll("#ov-trade .river").forEach(p => p.setAttribute("stroke-width", 3 / M.k));
  document.querySelectorAll("#ov-trade .flow").forEach(p => p.setAttribute("stroke-width", 2.5 / M.k));
  document.querySelectorAll("#ov-trade .port").forEach(c => { c.setAttribute("r", 7 / M.k); c.setAttribute("stroke-width", 2 / M.k); });
  document.querySelectorAll("#ov-trade .flowl").forEach(t => t.style.fontSize = (11.5 / M.k) + "px");
  document.querySelectorAll("#ov-sats .sat").forEach(c => { c.setAttribute("r", 6 / M.k); c.setAttribute("stroke-width", 2 / M.k); });
  document.querySelectorAll("#ov-sats .satl, #ov-sats .passl").forEach(t => { t.style.fontSize = (11 / M.k) + "px"; t.style.strokeWidth = (3 / M.k) + "px"; t.setAttribute("dy", -8 / M.k); });
  $("#zoomlvl").textContent = (M.k < 10 ? M.k.toFixed(1) : Math.round(M.k)) + "×";
}
function countyLabels() {     // county names appear once you zoom in far enough to read them
  const g = $("#ctylabels"); if (!g) return;
  if (!CTY || M.k < (CUR?.county ? 4 : 9) || !$("#counties")) { g.replaceChildren(); return; }
  const x0 = (VB.x - M.tx) / M.k, x1 = (VB.x + VB.w - M.tx) / M.k, y0 = (VB.y - M.ty) / M.k, y1 = (VB.y + VB.h - M.ty) / M.k;
  const kids = [];
  for (const c of CTY) { if (c.c[0] < x0 || c.c[0] > x1 || c.c[1] < y0 || c.c[1] > y1 || (c.b[2] - c.b[0]) * M.k < 34) continue;
    const t = svgEl("text", {x: c.c[0], y: c.c[1], class: "ctyl", style: `font-size:${10 / M.k}px;stroke-width:${2.2 / M.k}px`}); t.textContent = c.name || ""; kids.push(t);
    if (M.k >= 7 && CUR.county) { const v = CUR.vals[c.id]; if (v != null) { const t2 = svgEl("text", {x: c.c[0], y: c.c[1] + 11 / M.k, class: "ctyl sub", style: `font-size:${9 / M.k}px;stroke-width:${1.2 / M.k}px`}); t2.textContent = (CUR.est.has(c.id) ? "≈" : "") + CUR.fmt(v); kids.push(t2); } }
    if (kids.length > 700) break; }
  g.replaceChildren(...kids); $("#usmap").classList.toggle("ctyvals", kids.some(k => k.classList.contains("sub")));
}
let CUR = null;
function hasValue(code) { return CUR && (CUR.county || CUR.vals[code] != null); }
function tween(target, ms = 260) {
  const from = {k: M.k, tx: M.tx, ty: M.ty}, t0 = performance.now(), reduce = matchMedia("(prefers-reduced-motion: reduce)").matches, id = (tween.id = (tween.id || 0) + 1);
  if (reduce) { Object.assign(M, target); return applyT(); }
  const step = now => { const t = Math.max(0, Math.min(1, (now - t0) / ms)), e = 1 - Math.pow(1 - t, 3);   // rAF time can be a hair before t0
    if (id != tween.id) return; for (const k of ["k", "tx", "ty"]) M[k] = from[k] + (target[k] - from[k]) * e; applyT(); if (t < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}
function zoomToState(code) {
  const s = GEO.states.find(s => s.code == code); if (!s) return;
  const [x0, y0, x1, y1] = s.b, k = Math.min(10, 0.7 * Math.min(VB.w / (x1 - x0), VB.h / (y1 - y0)));
  const kk = Math.max(1.6, k);
  tween(clampT({k: kk, tx: VB.x + VB.w * 0.5 - kk * (x0 + x1) / 2, ty: VB.y + VB.h * 0.5 - kk * (y0 + y1) / 2}));
}
function resetView() { tween({k: 1, tx: 0, ty: 0}); }

function hover(e, code) {
  const v = CUR?.vals[code], name = NAMES[code] || code, t = $("#tip");
  const fc = M.fcModel[M.crop] ? fcValue(M.fcModel[M.crop], code) : null;
  t.replaceChildren(...[el("b", {textContent: name}), el("div", {textContent: v == null ? (M.layer == "whatif" && whatIf()?.states[code] ? "No extra chopping: yield still within 10% of normal" : "No data for this layer") : M.layer == "whatif" ? `${CUR.fmt(v)} silage (+${kfmt(whatIf().states[code].extra)} acres)` : CUR.fmt(v)}),
    M.layer != "forecast" && fc ? el("div", {className: "muted", textContent: `2026 forecast ${kfmt(fc.predicted)} acres`}) : null,
    el("div", {className: "muted", textContent: "Click for details"})].filter(Boolean));
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
  const kids = [...locBlock(), ...satBlock(), ...tradeBlock()];
  if (!code && M.layer == "whatif") kids.push(...whatIfBlock());
  if (!code && M.layer == "feed" && CUR.feed) { const st = CUR.feed;
    kids.push(el("div", {className: "wibox"}, el("div", {className: "eyebrow", textContent: `Feed stress watch \u00b7 ${M.fyear} season`}), el("div", {className: "hero", textContent: (st.watch / 1e6).toFixed(2) + "M"}),
      el("div", {className: "note", textContent: `milk cows in dry counties, ${Math.round(100 * st.watch / Math.max(1, st.total))}% of the US herd \u00b7 ${(st.severe / 1e6).toFixed(2)}M in very dry counties`}))); }
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
      const tr = el("tr", {}, el("td", {textContent: label}), el("td", {className: "n", textContent: (CUR.est.has(k) ? "≈ " : "") + CUR.fmt(v)})); tr.onclick = () => select(st); t.append(tr); }); kids.push(t); }
  } else {
    const name = NAMES[code] || code; let v = CUR.vals[code];
    if (CUR.county && (M.layer == "dairy" || M.layer == "silage_county")) { v = 0; let n = 0; for (const f in CUR.vals) if (stateOfFips(f) == code) { v += CUR.vals[f]; n++; } if (!n) v = null; }
    const close = el("button", {className: "ghost", textContent: "← United States"}); close.onclick = () => { M.sel = null; draw(); resetView(); };
    const brief = stateBriefButton(code);
    const rows = MAP.history.filter(r => r.state == code && r[crop] != null).map(r => [r.year, r[crop]]);
    const fcs = fcModels(crop).map(m => ({m, r: fcValue(m.model_id, code)})).filter(x => x.r);
    kids.push(el("div", {className: "satrow", style: "justify-content:space-between;margin-top:0"}, close, brief), el("div", {className: "eyebrow", style: "margin-top:12px", textContent: `${name} · ${crop}`}),
      el("div", {className: "hero", textContent: v == null ? "—" : CUR.fmt(v)}), el("div", {className: "note", textContent: CUR.title}));
    const extrasFirst = ["harvest", "money", "price", "milk", "satellite"].includes(M.layer);
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
      errs.slice(0, 8).forEach(x => t.append(el("tr", {}, el("td", {textContent: MODELS[x.mid]?.label || x.mid}),
        el("td", {className: "barcell"}, el("i", {style: `width:${100 * x.e.v / mx}%`})), el("td", {className: "n", textContent: x.e.v.toFixed(1) + "%"}))));
      kids.push(t, el("p", {className: "note", textContent: "Average miss per year in this state. Only folders that keep state-level predictions appear."})); }
    if (M.layer == "whatif" && whatIf()?.states[code]) { const w = whatIf().states[code];
      kids.unshift(el("div", {className: "wibox"}, el("div", {className: "eyebrow", textContent: `What if \u00b7 ${name}`}), el("div", {className: "hero", textContent: "+" + kfmt(Math.max(0, w.extra))}),
        el("div", {className: "note", textContent: `extra silage acres with corn yield ${Math.round(100 * w.sf)}% below normal (our 2026 forecast: ${kfmt(w.base)}). ${DR.worst[code] ? `Worst year here: ${DR.worst[code].year}, ${Math.round(100 * DR.worst[code].shortfall)}% below.` : ""}`}))); }
    if (!extrasFirst) kids.push(...extraBlocks(code));
    const h = hist(code, lastActualYear(crop));
    if (h) { kids.push(el("h3", {textContent: `Season signals, ${h.year}`}));
      const t = el("table", {className: "mini"}); Object.entries(SIGNALS).forEach(([k, sg]) => { if (h[k] != null) t.append(el("tr", {}, el("td", {textContent: sg.label}), el("td", {className: "n", textContent: sg.fmt(h[k])}))); }); kids.push(t); }
  }
  box.replaceChildren(...kids.filter(Boolean));
  if ($("#satpanel") && OVDATA.satrecs) { const now = satClock(); $("#satpanel").replaceChildren(...satPanelKids(now, passesFor(M.satDay).filter(p => !M.satOff.has(p.sat)))); }
}

// ---------------------------------------------------------------- controls, KPIs, legend
function kpis() {
  const tiles = [];
  for (const crop of ["silage", "grain"]) { const id = M.fcModel[crop], t = usTotal(id, crop);
    tiles.push(el("div", {className: "kpi"}, el("div", {className: "eyebrow", textContent: `2026 ${crop}, US acres`}), el("div", {className: "big", textContent: t ? kfmt(t.v) : "—"}),
      el("div", {className: "note", title: t ? modelLabel(id) : "", textContent: t ? modelLabel(id) + (t.lo != null ? ` · 80% ${kfmt(t.lo)}–${kfmt(t.hi)}` : "") : "no forecast yet"}))); }
  const pub = (CAT.models || []).filter(c => Object.values(MODELS).some(m => m.model == c.id && m.target == c.crop)).length;
  tiles.push(el("div", {className: "kpi"}, el("div", {className: "eyebrow", textContent: "Models on the board"}), el("div", {className: "big", textContent: D.models.length}),
    el("div", {className: "note", textContent: `${new Set(D.models.map(m => m.source)).size} folders · ${D.field.length} field-model runs`})));
  tiles.push(el("div", {className: "kpi"}, el("div", {className: "eyebrow", textContent: "Tier A / B published"}), el("div", {className: "big", textContent: `${pub} / ${(CAT.models || []).length}`}),
    el("div", {className: "note", textContent: pub ? "filling in as results land" : "training · results to follow"})));
  const best = Object.values(MODELS).filter(m => m.target == "silage").map(m => ({m, s: stats(m.model_id)})).filter(x => x.s.state != null && x.s.years >= 8).sort((a, b) => a.s.state - b.s.state)[0];
  tiles.push(el("div", {className: "kpi"}, el("div", {className: "eyebrow", textContent: `Best silage backtest, ${S.y0}–${S.y1}`}), el("div", {className: "big", textContent: best ? best.s.state.toFixed(2) + "%" : "—"}),
    el("div", {className: "note", textContent: best ? `${best.m.label} (${best.m.source_label}) · ${best.s.years} years · avg state miss` : ""})));
  $("#kpis").replaceChildren(...tiles);
}
function ctlField(label, node, hint) {   // a control with a small label above it, so every box says what it does
  return node ? el("label", {className: "ctl", title: hint || ""}, el("span", {className: "ctl-l", textContent: label}), node) : null;
}
function segOf(opts, cur, set) { return el("span", {className: "seg"}, opts.map(([k, l]) => { const b = el("button", {textContent: l, type: "button"}); b.setAttribute("aria-pressed", cur == k); b.onclick = e => { e.preventDefault(); set(k); draw(); }; return b; })); }
function yearRange(years, cur, set, extra) {
  const r = el("input", {type: "range", min: years[0], max: years.at(-1), step: 1, value: cur, "aria-label": "Year"}); r.oninput = e => { set(+e.target.value); draw(); };
  const prev = el("button", {className: "ghost tiny", type: "button", textContent: "\u2039", title: "Previous year", "aria-label": "Previous year"}); prev.onclick = e => { e.preventDefault(); const i = years.indexOf(cur); if (i > 0) { set(years[i - 1]); draw(); } };
  const next = el("button", {className: "ghost tiny", type: "button", textContent: "\u203a", title: "Next year", "aria-label": "Next year"}); next.onclick = e => { e.preventDefault(); const i = years.indexOf(cur); if (i < years.length - 1) { set(years[i + 1]); draw(); } };
  return el("span", {className: "yr"}, prev, r, next, el("b", {className: "mono", textContent: cur}), extra || null);
}
function controls() {
  const crop = M.crop, parts = [layerButton()];
  const cropMatters = ["forecast", "change", "disagree", "history", "error"].includes(M.layer);
  if (cropMatters) parts.push(ctlField("Crop", segOf([["silage", "Silage"], ["grain", "Grain"]], crop, c => M.crop = c), "Silage = whole plant chopped for cow feed. Grain = kernels only."));
  if (["forecast", "change"].includes(M.layer)) { const s = el("select", {"aria-label": "Model"}, fcModels(crop).map(m => el("option", {value: m.model_id, textContent: modelLabel(m.model_id), selected: m.model_id == M.fcModel[crop]})));
    s.onchange = e => { M.fcModel[crop] = e.target.value; draw(); }; parts.push(ctlField("Whose forecast", s, "Each of the team's models makes its own 2026 forecast. The first one is the team's headline model.")); }
  if (M.layer == "error") { const ids = errModels(crop); if (!M.errModel[crop] || !ids.includes(M.errModel[crop])) M.errModel[crop] = ids[0];
    if (ids.length) { const s = el("select", {"aria-label": "Model"}, ids.map(id => el("option", {value: id, textContent: (MODELS[id]?.label || id) + " \u00b7 " + (MODELS[id]?.source_label || ""), selected: id == M.errModel[crop]})));
      s.onchange = e => { M.errModel[crop] = e.target.value; draw(); }; parts.push(ctlField("Which model", s, "Pick a model to see how far off it was in each state.")); } }
  if (M.layer == "whatif") whatIfControls(parts);
  if (M.layer == "feed") { const yrs = feedYears(); parts.push(ctlField("Growing season", yearRange(yrs, M.fyear || yrs.at(-1), y => M.fyear = y), "May to September of that year, against the county's 2016\u20132025 normal.")); }
  if (M.layer == "dairy" || M.layer == "silage_county") parts.push(ctlField("Census year", segOf(EXT.county.census_years.map(y => [y, String(y)]), M.cyear, y => M.cyear = y), "USDA counts every farm once every five years."));
  if (M.layer == "weather") parts.push(ctlField("Show", segOf([["rain", "Rain"], ["heat", "Heat"]], M.wx, k => M.wx = k)));
  if (M.layer == "weather" || M.layer == "frost") { const yrs = Object.keys(EXT.county.weather).map(Number).filter(y => y < 2026).sort((a, b) => a - b);
    parts.push(ctlField("Season", yearRange(yrs, M.wyear || yrs.at(-1), y => M.wyear = y))); }
  if (M.layer == "money" || M.layer == "price") { const yrs = [...new Set(Object.values(EXT.money).flatMap(o => Object.keys(o).map(Number)))].sort((a, b) => a - b);
    parts.push(ctlField("Year", yearRange(yrs, M.myear, y => M.myear = y))); }
  if (M.layer == "context") { const s = el("select", {"aria-label": "Signal"}, Object.entries(SIGNALS).map(([k, sg]) => el("option", {value: k, textContent: sg.label, selected: k == M.signal})));
    s.onchange = e => { M.signal = e.target.value; draw(); }; parts.push(ctlField("Signal", s)); }
  if (["history", "context"].includes(M.layer)) {
    const years = [...new Set(MAP.history.filter(r => (M.layer == "history" ? r[crop] : r[M.signal]) != null).map(r => r.year))].sort((a, b) => a - b);
    if (!years.includes(M.year)) M.year = years.at(-1);
    const play = el("button", {className: "ghost tiny", type: "button", textContent: M.playing ? "\u275a\u275a Pause" : "\u25b6 Play"}); play.onclick = e => { e.preventDefault(); M.playing ? stopPlay() : startPlay(years); };
    parts.push(ctlField("Year", yearRange(years, M.year, y => { M.year = y; stopPlay(); }, play)));
  }
  $("#mapctl").replaceChildren(...parts.filter(Boolean));
}

// ---------------------------------------------------------------- "Show me" picker: every map with a one-line description
function layerButton() {
  const cur = LAYERS.find(l => l[0] == M.layer), grp = LAYER_GROUPS.find(g => g[1].some(l => l[0] == M.layer))[0];
  const b = el("button", {className: "lpick", type: "button", "aria-haspopup": "listbox", "aria-expanded": "false", id: "lpick"},
    el("span", {className: "lpick-ico", textContent: GROUP_ICON[grp] || "\u25a6"}),
    el("span", {className: "lpick-txt"}, el("span", {className: "lpick-g", textContent: "Show me \u00b7 " + grp}), el("span", {className: "lpick-t", textContent: cur[1]})),
    el("span", {className: "caret", textContent: "\u25be"}));
  b.onclick = e => { e.stopPropagation(); $("#lmenu") ? closeLayerMenu() : openLayerMenu(); };
  return b;
}
const firstSentence = s => (s.match(/^[^.]*\./) || [s])[0];
function openLayerMenu() {
  closeLayerMenu(); const btn = $("#lpick"); if (!btn) return; btn.setAttribute("aria-expanded", "true");
  const q = el("input", {type: "search", placeholder: "Search maps: cows, rain, forecast\u2026", "aria-label": "Search maps"});
  const list = el("div", {className: "lm-list", role: "listbox"});
  const menu = el("div", {id: "lmenu", className: "lmenu"}, el("div", {className: "lm-head"}, el("b", {textContent: "What should the map show?"}), el("span", {className: "muted", textContent: "\u2191\u2193 to move, Enter to pick"})), q, list);
  const render = () => { const term = q.value.trim().toLowerCase(); list.replaceChildren();
    LAYER_GROUPS.forEach(([g, ls]) => { const hit = ls.filter(l => !term || (l[1] + " " + l[2] + " " + g).toLowerCase().includes(term)); if (!hit.length) return;
      list.append(el("div", {className: "lm-g", textContent: (GROUP_ICON[g] || "") + "  " + g}));
      hit.forEach(([k, l, ex]) => { const it = el("button", {className: "lm-i" + (k == M.layer ? " on" : ""), type: "button", role: "option", "aria-selected": String(k == M.layer)},
        el("span", {className: "lm-t", textContent: l + (COUNTY_LAYERS.has(k) ? "" : "")}), el("span", {className: "lm-d", textContent: firstSentence(ex)}));
        it.dataset.k = k; it.onclick = () => pickLayer(k); list.append(it); }); });
    if (!list.children.length) list.append(el("div", {className: "note", style: "padding:10px", textContent: "No map matches that. Try \u201ccows\u201d, \u201crain\u201d or \u201cforecast\u201d."})); };
  render(); q.oninput = render;
  q.onkeydown = e => { const items = [...list.querySelectorAll(".lm-i")]; let i = items.findIndex(x => x.classList.contains("kb"));
    if (e.key == "ArrowDown" || e.key == "ArrowUp") { e.preventDefault(); items.forEach(x => x.classList.remove("kb")); i = e.key == "ArrowDown" ? Math.min(items.length - 1, i + 1) : Math.max(0, i - 1); items[i]?.classList.add("kb"); items[i]?.scrollIntoView({block: "nearest"}); }
    else if (e.key == "Enter") { e.preventDefault(); const it = items[Math.max(0, i)]; if (it) pickLayer(it.dataset.k); }
    else if (e.key == "Escape") { closeLayerMenu(); $("#lpick")?.focus(); } };
  document.body.append(menu); const r = btn.getBoundingClientRect();
  menu.style.left = Math.max(8, Math.min(r.left, innerWidth - 470)) + "px"; menu.style.top = r.bottom + 6 + scrollY + "px";
  setTimeout(() => q.focus(), 0);
}
function closeLayerMenu() { $("#lmenu")?.remove(); $("#lpick")?.setAttribute("aria-expanded", "false"); }
function pickLayer(k) { closeLayerMenu(); stopPlay(); M.layer = k; if (k == "satellite" && !OV.sats) { OV.sats = true; M.satOpen = true; drawOverlays(); } draw(); if (COUNTY_LAYERS.has(M.layer) && !M.sel && !M.loc) resetView(); }
addEventListener("pointerdown", e => { const m = $("#lmenu"); if (m && !m.contains(e.target) && !e.target.closest?.("#lpick")) closeLayerMenu(); });
function startPlay(years) { let i = years[0] == M.year || M.year == years.at(-1) ? 0 : years.indexOf(M.year); M.year = years[i];
  M.playing = setInterval(() => { i++; if (i >= years.length) return stopPlay(); M.year = years[i]; draw(); }, 900); draw(); }
function stopPlay() { if (M.playing) { clearInterval(M.playing); M.playing = null; } }
function legend(cls) {
  const box = $("#legend-map"), ex = $("#explain");
  ex.replaceChildren(...[el("b", {textContent: "What am I looking at? "}), CUR.explain, CUR.note ? el("span", {className: "note", textContent: CUR.note}) : null].filter(Boolean));
  if (!cls.bins.length) { box.replaceChildren(el("span", {className: "note", textContent: "No data for this layer yet"})); return; }
  const ends = M.layer == "whatif" ? ["less", "", "more"] : CUR.div ? (M.layer == "weather" ? (M.wx == "rain" ? ["drier", "normal", "wetter"] : ["cooler", "normal", "hotter"]) : ["less", "same", "more"]) : M.layer == "error" ? ["closer", "", "further off"]
    : ["harvest", "frost"].includes(M.layer) ? ["earlier", "", "later"] : ["less", "", "more"];
  if (M.layer == "satellite") { box.replaceChildren(el("div", {className: "lt", textContent: "Blue states: in the satellite sample"}), el("div", {className: "nd"}, el("i", {style: "background:var(--accent);border-radius:50%"}), "test fields with known answers")); return; }
  box.replaceChildren(...[el("div", {className: "lt", textContent: CUR.title}), el("div", {className: "ramp"}, cls.bins.map(b => el("i", {style: `background:${b.c}`, title: `${CUR.fmt(b.lo)} to ${CUR.fmt(b.hi)}`}))),
    el("div", {className: "rl"}, el("span", {textContent: `${CUR.fmt(cls.bins[0].lo)} (${ends[0]})`}), el("span", {textContent: ends[1]}), el("span", {textContent: `${CUR.fmt(cls.bins.at(-1).hi)} (${ends[2]})`})),
    M.layer == "feed" ? el("div", {className: "nd"}, el("i", {style: "background:#232b35"}), "normal season", el("i", {style: "background:#3a2418;margin-left:8px"}), "dry, no dairy") : null,
    M.layer == "whatif" ? el("div", {className: "nd"}, el("i", {style: "background:#383835"}), "no extra chopping") : null,
    el("div", {className: "nd"}, el("i", {style: `background:${NODATA}`}), "no data")].filter(Boolean));
}
function select(code) { M.sel = code; draw(); zoomToState(code); }

// ---------------------------------------------------------------- entry
async function mapTab() {
  if (!GEO) { const q = FRESH ? "?fresh=1" : "";
    const opt = u => fetch(u).then(r => r.ok ? r.json() : null).catch(() => null);
    const [g, m, x, dr, tm] = await Promise.all([fetch("/api/geo").then(r => r.json()), fetch("/api/map" + q).then(r => r.json()), fetch("/api/extras" + q).then(r => r.json()), opt("/api/drought" + q), opt("/api/team")]);
    GEO = g; MAP = m; EXT = x; DR = dr; TEAM = tm;
    GEO.states.forEach(s => { s.code = FIPS[s.fips] || s.fips; NAMES[s.code] = s.name; });
    M.year = lastActualYear("silage"); }
  for (const c of ["silage", "grain"]) if (!M.fcModel[c] || !MODELS[M.fcModel[c]]) M.fcModel[c] = defaultModel(c);
  const rebuilt = !M.built || !$("#zoomg"); if (rebuilt) buildMap();
  CUR = layerValues();
  if (CUR.county && !$("#counties")) { $("#legend-map").replaceChildren(el("span", {className: "note", textContent: "Loading 3,000 counties\u2026"})); await loadCounties(); }
  const cls = classify(CUR.vals, CUR.ramp, CUR.div, CUR.flip);
  const LIGHT = new Set([SEQ[5], SEQ[6], SEQ2[5], SEQ2[6], DIV[2], DIV[4]]);  // labels go dark on light fills
  const stage = $("#usmap"); stage.classList.toggle("countymode", !!CUR.county);
  if (CUR.county) document.querySelectorAll("#counties .cty").forEach(p => { const f = p.dataset.fips; p.style.fill = CUR.fillFor ? CUR.fillFor(cls, f) : cls.color(CUR.vals[f]); });
  document.querySelectorAll("#states .st").forEach(p => { const v = CUR.county ? null : CUR.vals[p.dataset.code], c = CUR.county ? "transparent" : M.layer == "satellite" ? (v ? "#2a78d6" : NODATA) : CUR.stateFill ? CUR.stateFill(cls, p.dataset.code) : cls.color(v);
    p.style.fill = c; p.classList.toggle("nodata", !CUR.county && v == null && !CUR.stateFill);
    const lbl = document.querySelector(`#labels text[data-code="${p.dataset.code}"]`); if (lbl) lbl.classList.toggle("dark", LIGHT.has(c)); });
  const mk = $("#markers"); mk.replaceChildren();
  if (M.layer == "satellite") (EXT.satellite.points || []).forEach(pt => { const [x, y] = ALB(pt.lon, pt.lat);
    const c = svgEl("circle", {cx: x, cy: y, class: "mk"}); c.addEventListener("pointermove", e => { const t = $("#tip"); t.replaceChildren(el("b", {textContent: pt.label}), el("div", {textContent: pt.detail})); t.hidden = false; t.style.left = e.clientX + 14 + "px"; t.style.top = e.clientY + 14 + "px"; });
    c.addEventListener("pointerleave", () => $("#tip").hidden = true); const t = svgEl("text", {x, y, class: "mkl", dy: 4}); t.textContent = pt.label; mk.append(c, t); });
  const s = GEO.states.find(s => s.code == M.sel); $("#selpath").setAttribute("d", s ? s.d : "");
  kpis(); controls(); legend(cls); panel(); drawLoc(); applyT(); locControls(); guideButton(); fieldButton(); teamFooter();
  if (!mapTab.guided) { mapTab.guided = true; let seen = false; try { seen = localStorage.getItem("board-guide") == "1"; } catch (e) { seen = true; }
    if (!seen) setTimeout(() => startGuide(), 600);
    try { const saved = JSON.parse(localStorage.getItem("board-loc") || "null"); if (saved && !M.loc) setLocation(saved, {quiet: true}); } catch (e) { /* storage off */ } }
  if (!mapTab.ovStarted || rebuilt) { mapTab.ovStarted = true; drawOverlays(); } else overlayControls();
}
// ---------------------------------------------------------------- guided tour: points at each control in turn
const GUIDE = [
  ["#lpick", "1 · Pick a map", "Click here to choose what the colors show: our 2026 forecast, where the dairy cows are, this season's rain, frost, prices and more. Type in the search box to find one fast."],
  ["#mapctl .ctl", "2 · Fine-tune it", "The boxes next to it change with the map you picked: silage or grain, whose forecast, which year. Each one is labeled; hover it for a hint."],
  ["#explain", "3 · Read the colors", "This line explains the map in plain words. The legend in the bottom-left corner gives the scale."],
  ["#locbox", "4 · Find your area", "Type a town, ZIP code or county, or press \u{1F4CD} to use your location. The map zooms there and the side panel shows the cows, silage, weather and next satellite picture around you."],
  [".zoom", "5 · Zoom and move", "Scroll or pinch to zoom, drag to move, double-click to zoom in. Drag the slider, or hold Shift and drag a box to zoom straight into it. Zoom in on a county map to read county names."],
  ["#ovctl", "6 · Overlays", "Lay highways, grain export routes or today's satellite pictures on top of any map. “Satellites” shows every strip Sentinel-2 and Landsat photograph today."],
  ["#sp", "7 · Details", "Click any state (or county) to see its history, every model's 2026 number and how well each model has called it. Press 0 or ↺ to go back to the whole country."],
];
function startGuide(i = 0) {
  endGuide(false);
  let step = i; while (step < GUIDE.length && !$(GUIDE[step][0])) step++;
  if (step >= GUIDE.length) return endGuide(true);
  const [sel, title, body] = GUIDE[step], target = $(sel); target.scrollIntoView({block: "nearest", behavior: "smooth"});
  const r = target.getBoundingClientRect(), pad = 6;
  const spot = el("div", {className: "gspot"}); Object.assign(spot.style, {left: r.left - pad + "px", top: r.top - pad + scrollY + "px", width: r.width + 2 * pad + "px", height: r.height + 2 * pad + "px"});
  const back = el("button", {className: "ghost", type: "button", textContent: "Back", disabled: step == 0}); back.onclick = () => startGuide(step - 1);
  const next = el("button", {className: "act", type: "button", textContent: step == GUIDE.length - 1 ? "Done" : "Next"}); next.onclick = () => step == GUIDE.length - 1 ? endGuide(true) : startGuide(step + 1);
  const skip = el("button", {className: "linkish", type: "button", textContent: "Skip the tour"}); skip.onclick = () => endGuide(true);
  const dots = el("div", {className: "gdots"}, GUIDE.map((_, j) => el("i", {className: j == step ? "on" : ""})));
  const bub = el("div", {className: "gbub", role: "dialog", "aria-label": title}, el("b", {textContent: title}), el("p", {textContent: body}), el("div", {className: "grow"}, dots, skip, back, next));
  document.body.append(spot, bub);
  const bw = Math.min(380, innerWidth - 24), below = r.bottom + 14 + 190 < innerHeight || r.top < 220;
  bub.style.width = bw + "px"; bub.style.left = Math.max(12, Math.min(r.left, innerWidth - bw - 12)) + "px";
  if (r.width > innerWidth * 0.5 && r.height > 300) { bub.style.left = Math.max(12, r.left - bw - 16) + "px"; bub.style.top = r.top + 20 + scrollY + "px"; }
  else bub.style.top = (below ? r.bottom + 14 : r.top - 14 - bub.offsetHeight) + scrollY + "px";
  next.focus();
  startGuide.key = e => { if (e.key == "Escape") endGuide(true); else if (e.key == "ArrowRight") next.click(); else if (e.key == "ArrowLeft" && step) back.click(); };
  addEventListener("keydown", startGuide.key);
}
function endGuide(done) {
  document.querySelectorAll(".gspot,.gbub").forEach(n => n.remove()); if (startGuide.key) removeEventListener("keydown", startGuide.key);
  if (done) try { localStorage.setItem("board-guide", "1"); } catch (e) { /* storage off */ }
}
function guideButton() {
  if ($("#guidebtn")) return;
  const b = el("button", {id: "guidebtn", className: "ghost", type: "button", title: "Show me around", textContent: "? How to use"}); b.onclick = () => startGuide(0);
  $(".toolbar")?.append(b);
}

// ---------------------------------------------------------------- overlays: highways, export routes, live satellites
const OV = {farms: false, cities: true, roads: false, trade: false, sats: false}, OVDATA = {roads: null, tle: null, satrecs: null, trade: null};
let satTimer = null;
const US_BOX = {lon0: -125, lon1: -66, lat0: 24, lat1: 50};
const inUS = (lon, lat) => lon > US_BOX.lon0 && lon < US_BOX.lon1 && lat > US_BOX.lat0 && lat < US_BOX.lat1;
const KM_PX = 1300 / 6371;                     // Albers USA scale: map units per km, near the middle of the map
const SWATH = {"Sentinel-2": 290, "Landsat": 185};

function overlayControls() {
  const box = $("#ovctl"); if (!box) return;
  const items = [["farms", "\u{1F69C} Farms"], ["cities", "\u{1F3D9}\uFE0F Cities"], ["roads", "\u{1F6E3}\uFE0F Highways"], ["trade", "\u{1F6A2} Export routes"], ["sats", "\u{1F6F0}\uFE0F Satellites"]];
  box.replaceChildren(el("div", {className: "ovt", textContent: "Overlays"}), ...items.map(([k, l]) => {
    const b = el("button", {className: "chip", textContent: l}); b.setAttribute("aria-pressed", OV[k]);
    b.onclick = () => { OV[k] = !OV[k]; if (k == "sats" && OV.sats) M.satOpen = true; drawOverlays(); }; return b; }));
}
async function drawOverlays() {
  overlayControls();
  const g = $("#overlays"); if (!g) return;
  // highways
  if (OV.roads && !OVDATA.roads) OVDATA.roads = await fetch("/api/roads").then(r => r.json());
  let rg = $("#ov-roads");
  if (OV.roads && !rg) { rg = svgEl("g", {id: "ov-roads"}); g.prepend(rg);
    OVDATA.roads.roads.sort((a, b) => (a.c == "interstate") - (b.c == "interstate")).forEach(r => {
      const p = svgEl("path", {d: r.d, class: "road " + r.c});
      p.addEventListener("pointermove", e => { const t = $("#tip"); t.replaceChildren(el("b", {textContent: r.n}), el("div", {className: "muted", textContent: r.c == "interstate" ? "Interstate: the main truck corridors" : "US highway"}));
        t.hidden = false; t.style.left = e.clientX + 14 + "px"; t.style.top = e.clientY + 14 + "px"; });
      p.addEventListener("pointerleave", () => $("#tip").hidden = true); rg.append(p); }); }
  if (OV.roads && rg && !rg.dataset.decor) { rg.dataset.decor = 1; decorateRoads(rg); }
  if (rg) rg.style.display = OV.roads ? "" : "none";
  $("#states").classList.toggle("dim", OV.trade || OV.farms);
  // export routes: barge rivers, export ports, where the corn goes
  if (OV.trade && !OVDATA.trade) OVDATA.trade = await fetch("/api/trade").then(r => r.json());
  let tg = $("#ov-trade");
  if (OV.trade && !tg) { tg = svgEl("g", {id: "ov-trade"}); g.prepend(tg); drawTrade(tg); }
  if (tg) tg.style.display = OV.trade ? "" : "none";
  tradeCard();
  // satellites: every strip photographed today, plus where each satellite is right now
  clearInterval(satTimer); let sg = $("#ov-sats");
  if (OV.sats) {
    await ensureSats();
    if (!sg) { sg = svgEl("g", {id: "ov-sats"}); g.append(sg); }
    sg.style.display = ""; drawSats(); satTimer = setInterval(() => { if (M.satT == null && S.tab == "map") drawSats(); }, 5000);
  } else { if (sg) sg.style.display = "none"; const card = $("#satcard"); if (card) card.hidden = true; }
  await drawLiveOverlays();
  if (CUR) panel(); applyT();
}

function drawTrade(tg) {
  const T = OVDATA.trade, defs = svgEl("defs"), mk = svgEl("marker", {id: "arrowhead", viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse"});
  mk.append(svgEl("path", {d: "M0,0L10,5L0,10z", fill: "#8fd19e"})); defs.append(mk); tg.append(defs);
  T.rivers.forEach(rv => { const p = svgEl("path", {d: rv.d, class: "river"}); p.addEventListener("pointermove", e => tipText(e, rv.n + " River", "Barge route: grain floats down to the Gulf ports"));
    p.addEventListener("pointerleave", () => $("#tip").hidden = true); tg.append(p); });
  T.ports.forEach(pt => { const [x, y] = ALB(pt.lon, pt.lat), [ex, ey] = [x + pt.to[0], y + pt.to[1]];
    const a = svgEl("path", {d: `M${x},${y}Q${(x + ex) / 2 + pt.to[1] * 0.25},${(y + ey) / 2 - pt.to[0] * 0.25} ${ex},${ey}`, class: "flow", "marker-end": "url(#arrowhead)"}); tg.append(a);
    const c = svgEl("circle", {cx: x, cy: y, class: "port"}); c.addEventListener("pointermove", e => tipText(e, pt.name, pt.detail)); c.addEventListener("pointerleave", () => $("#tip").hidden = true); tg.append(c);
    if (pt.label) { const lx = pt.lx != null ? x + pt.lx : ex, ly = pt.ly != null ? y + pt.ly : ey + (pt.to[1] > 0 ? 14 : -8);
      const t = svgEl("text", {x: lx, y: ly, class: "flowl", "text-anchor": pt.anchor || "middle"}); t.textContent = pt.label; tg.append(t); } });
}
function tipText(e, title, body) { const t = $("#tip"); t.replaceChildren(el("b", {textContent: title}), el("div", {textContent: body})); t.hidden = false; t.style.left = Math.min(e.clientX + 14, innerWidth - 300) + "px"; t.style.top = e.clientY + 14 + "px"; }
function tradeCard() { $("#states").classList.toggle("dim", OV.trade || OV.farms); if (CUR) panel(); }
function tradeBlock() {
  if (!OV.trade || !OVDATA.trade) return [];
  return [el("div", {className: "tradebox"}, el("div", {className: "eyebrow", textContent: "Export routes · where US corn goes"}),
    el("ul", {}, OVDATA.trade.facts.map(f => el("li", {}, f.text, " ", el("a", {href: f.url, target: "_blank", rel: "noopener", className: "src", textContent: "(" + f.src + ")"})))),
    el("div", {className: "note", textContent: "On the map: blue lines are the rivers barges use; green arrows are the main export gateways. Hover a port for details. The US imports very little corn, so only exports are shown."}))];
}
// ---------------------------------------------------------------- satellites: today's picture strips, not just one line
const SATCOL = {"Sentinel-2A": "#7fd1ff", "Sentinel-2B": "#5fe3b4", "Sentinel-2C": "#c7a8ff", "Landsat 9": "#ffb86b", "Landsat 8": "#ff8fa3"};
const SATSHORT = n => n.replace("Sentinel-", "S").replace("Landsat ", "L");
const swathKm = n => n.startsWith("Landsat") ? SWATH.Landsat : SWATH["Sentinel-2"];
const RAD = Math.PI / 180;
const hhmm = d => d.toLocaleTimeString("en-US", {hour: "numeric", minute: "2-digit"});
const dayName = off => off == 0 ? "today" : off == -1 ? "yesterday" : off == 1 ? "tomorrow" : dayStart(off).toLocaleDateString("en-US", {weekday: "long"});
function satPos(rec, d) {
  const pv = satellite.propagate(rec, d); if (!pv || !pv.position) return null;
  const gd = satellite.eciToGeodetic(pv.position, satellite.gstime(d));
  return [satellite.degreesLong(gd.longitude), satellite.degreesLat(gd.latitude)];
}
function epochOf(l1) { const yy = +l1.slice(18, 20), doy = parseFloat(l1.slice(20, 32)); return Date.UTC(2000 + yy, 0, 1) + (doy - 1) * 864e5; }
async function ensureSats() {
  if (OVDATA.satrecs) return;
  OVDATA.tle = await fetch("/api/tle").then(r => r.json());
  OVDATA.satrecs = (typeof satellite == "undefined") ? [] : OVDATA.tle.sats.map(s => ({...s, rec: satellite.twoline2satrec(s.l1, s.l2)}));
}
function dayStart(off) { const d = new Date(); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() + off); return d; }
function dest(lat, lon, brg, km) {        // point km away from (lat, lon) on a bearing, on a sphere
  const d = km / 6371, p1 = lat * RAD, l1 = lon * RAD, t = brg * RAD;
  const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(t));
  const l2 = l1 + Math.atan2(Math.sin(t) * Math.sin(d) * Math.cos(p1), Math.cos(d) - Math.sin(p1) * Math.sin(p2));
  return [l2 / RAD, p2 / RAD];
}
function bearing(a, b) { const y = Math.sin((b.lon - a.lon) * RAD) * Math.cos(b.lat * RAD), x = Math.cos(a.lat * RAD) * Math.sin(b.lat * RAD) - Math.sin(a.lat * RAD) * Math.cos(b.lat * RAD) * Math.cos((b.lon - a.lon) * RAD); return Math.atan2(y, x) / RAD; }
function swathPoly(ps) {
  const hw = swathKm(ps.sat) / 2, L = [], R = [];
  ps.pts.forEach((p, i) => { const a = ps.pts[Math.max(0, i - 1)], b = ps.pts[Math.min(ps.pts.length - 1, i + 1)], brg = bearing(a, b);
    L.push(ALB(...dest(p.lat, p.lon, brg - 90, hw))); R.push(ALB(...dest(p.lat, p.lon, brg + 90, hw))); });
  return "M" + [...L, ...R.reverse()].map(q => q[0].toFixed(1) + "," + q[1].toFixed(1)).join("L") + "Z";
}
let STP = null;
function stateAt(x, y) {
  STP ??= [...document.querySelectorAll("#states .st")].map(p => [p, GEO.states.find(s => s.code == p.dataset.code)]).filter(x => x[1] && !["AK", "HI", "PR"].includes(x[1].code));  // insets are not where they are drawn
  for (const [p, s] of STP) { if (x < s.b[0] || x > s.b[2] || y < s.b[1] || y > s.b[3]) continue;
    try { if (p.isPointInFill(new DOMPoint(x, y))) return s.code; } catch (e) { return null; } }
  return null;
}
const PASSES = {};
function passesFor(off) {        // daytime (descending) passes over the lower 48 on one local day
  const d0 = dayStart(off), key = d0.toDateString(); if (PASSES[key]) return PASSES[key];
  const out = [];
  (OVDATA.satrecs || []).forEach(s => {
    let cur = null;
    const fin = () => {
      if (cur && cur.pts.length >= 3 && cur.pts.at(-1).lat < cur.pts[0].lat) {
        cur.t0 = cur.pts[0].t; cur.t1 = cur.pts.at(-1).t; cur.xy = cur.pts.map(q => ALB(q.lon, q.lat)); cur.poly = swathPoly(cur);
        cur.states = [...new Set(cur.xy.map(q => stateAt(...q)).filter(Boolean))];
        const land = cur.xy.map((q, i) => [q, i]).filter(([q]) => stateAt(...q)); const mid = land.length ? land[Math.floor(land.length / 2)][1] : Math.floor(cur.xy.length / 2);
        cur.tm = cur.pts[mid].t; cur.top = land.length ? land[0][0] : cur.xy[0];      // label at the northern edge, where strips are far apart
        if (cur.states.length) out.push(cur); }
      cur = null; };
    for (let m = -15; m <= 1455; m += 0.5) { const t = new Date(+d0 + m * 6e4), q = satPos(s.rec, t);
      if (q && q[0] > -130 && q[0] < -60 && q[1] > 20 && q[1] < 53) (cur ??= {sat: s.name, pts: []}).pts.push({t, lon: q[0], lat: q[1]}); else fin(); }
    fin(); });
  return PASSES[key] = out.filter(p => p.tm >= d0 && p.tm < +d0 + 864e5).sort((a, b) => a.tm - b.tm);
}
function satClock() { const d0 = dayStart(M.satDay); return M.satT == null ? (M.satDay == 0 ? new Date() : new Date(+d0 + 12 * 36e5)) : new Date(+d0 + M.satT * 6e4); }
function drawSats() {
  const sg = $("#ov-sats"); if (!sg || !OVDATA.satrecs) return;
  const now = satClock(), passes = passesFor(M.satDay).filter(p => !M.satOff.has(p.sat));
  const strips = svgEl("g", {"clip-path": "url(#usclip)", class: "strips"}), labels = svgEl("g"), kids = [strips, labels], placed = [];
  passes.forEach(ps => {
    const state = ps.t1 < now ? "done" : ps.t0 > now ? "soon" : "now", col = SATCOL[ps.sat] || "#7fd1ff";
    const band = svgEl("path", {d: ps.poly, class: "strip " + state, fill: col, stroke: col});
    band.addEventListener("pointermove", e => tipText(e, `${ps.sat} · ${hhmm(ps.tm)} ${dayName(M.satDay)}`,
      `${state == "done" ? "Photographed" : state == "now" ? "Photographing now:" : "Will photograph"} this ${swathKm(ps.sat)} km strip over ${ps.states.join(", ")}. ${state == "soon" ? "" : "Fields here have a fresh picture, unless it was cloudy."}`));
    band.addEventListener("pointerleave", () => $("#tip").hidden = true);
    strips.append(band, svgEl("path", {d: "M" + ps.xy.map(q => q[0].toFixed(1) + "," + q[1].toFixed(1)).join("L"), class: "track " + state, stroke: col}));
    let ly = ps.top[1]; const lw = 70 / M.k, lh = 13 / M.k;
    while (placed.some(([x, y]) => Math.abs(x - ps.top[0]) < lw && Math.abs(y - ly) < lh)) ly += lh;
    placed.push([ps.top[0], ly]);
    const t = svgEl("text", {x: ps.top[0], y: ly, class: "passl " + state, fill: col}); t.textContent = `${SATSHORT(ps.sat)} ${hhmm(ps.tm)}`; labels.append(t);
  });
  (OVDATA.satrecs || []).forEach(s => { if (M.satOff.has(s.name)) return; const p = satPos(s.rec, now); if (!p || !inUS(...p)) return;
    const tail = []; for (let sec = -480; sec <= 0; sec += 30) { const q = satPos(s.rec, new Date(+now + sec * 1000)); if (q) tail.push(ALB(...q)); }
    const [x, y] = ALB(...p), col = SATCOL[s.name];
    kids.push(svgEl("path", {d: "M" + tail.map(q => q[0].toFixed(1) + "," + q[1].toFixed(1)).join("L"), class: "tail", stroke: col}),
      svgEl("circle", {cx: x, cy: y, class: "sat", fill: col}));
    const t = svgEl("text", {x, y, class: "satl"}); t.textContent = s.name; kids.push(t); });
  sg.replaceChildren(...kids); applyT(); satCard(now, passes);
}
function passWindow(all, d0) {      // the stretch of the day when passes happen, padded, in minutes since midnight
  if (!all.length) return [6 * 60, 14 * 60];
  const a = Math.floor(((all[0].t0 - d0) / 6e4 - 40) / 30) * 30, b = Math.ceil(((all.at(-1).t1 - d0) / 6e4 + 40) / 30) * 30;
  return [Math.max(0, a), Math.min(1440, b)];
}
function satCard(now, passes) {
  // a slim bar on the map, the full controls in the side panel
  let card = $("#satcard"); if (!card) { card = el("div", {id: "satcard"}); $(".stage").append(card); } card.hidden = false;
  const next = passes.find(p => p.t1 >= now), done = passes.filter(p => p.t1 < now).length;
  const more = el("button", {className: "ghost tiny", type: "button", textContent: M.satOpen ? "Hide details" : "Details →"});
  more.onclick = () => { M.satOpen = !M.satOpen; panel(); drawSats(); if (M.satOpen) $("#satpanel")?.scrollIntoView({block: "nearest", behavior: "smooth"}); };
  card.className = "mini";
  card.replaceChildren(el("div", {className: "sathead"}, el("span", {}, el("b", {textContent: "\u{1F6F0}️ "}), `${dayName(M.satDay)[0].toUpperCase() + dayName(M.satDay).slice(1)}: ${passes.length} picture strips` +
    (M.satDay == 0 ? ` · ${done} taken` : "") + (next && M.satDay == 0 ? ` · next ${SATSHORT(next.sat)} at ${hhmm(next.tm)} over ${next.states.slice(0, 3).join(", ")}` : M.satDay == 0 ? " · all done for today" : "")), more));
  const box = $("#satpanel"); if (box) { const top = box.querySelector(".satscroll")?.scrollTop || 0; box.replaceChildren(...satPanelKids(now, passes)); const sc = box.querySelector(".satscroll"); if (sc) sc.scrollTop = top; }
}
function satPanelKids(now, passes) {
  const all = passesFor(M.satDay), d0 = dayStart(M.satDay), [wa, wb] = passWindow(all, d0);
  const days = segOf([[-1, "Yesterday"], [0, "Today"], [1, "Tomorrow"]], M.satDay, d => { M.satDay = d; M.satT = null; });
  days.querySelectorAll("button").forEach(b => b.addEventListener("click", () => setTimeout(drawSats, 0)));
  const chips = el("div", {className: "satchips"}, (OVDATA.satrecs || []).map(s => { const b = el("button", {className: "schip", type: "button"}, el("i", {style: `background:${SATCOL[s.name]}`}), s.name);
    b.setAttribute("aria-pressed", !M.satOff.has(s.name)); b.onclick = () => { M.satOff.has(s.name) ? M.satOff.delete(s.name) : M.satOff.add(s.name); drawSats(); }; return b; }));
  // timeline over the hours when passes happen: one bar per pass, a line for the time shown
  const W = 340, H = 40, X = t => 22 + (W - 44) * (((t - d0) / 6e4 - wa) / (wb - wa));
  const tl = svgEl("svg", {viewBox: `0 0 ${W} ${H}`, width: "100%", class: "satline"});
  for (let m = Math.ceil(wa / 60) * 60; m <= wb; m += 60) { const x = X(+d0 + m * 6e4); tl.append(svgEl("line", {x1: x, x2: x, y1: 4, y2: 26, class: "grid"}));
    const t = svgEl("text", {x, y: 37, "text-anchor": "middle"}); t.textContent = hhmm(new Date(+d0 + m * 6e4)).replace(":00", ""); tl.append(t); }
  passes.forEach(p => tl.append(svgEl("rect", {x: X(p.t0), y: 7, width: Math.max(3, X(p.t1) - X(p.t0)), height: 16, rx: 2, fill: SATCOL[p.sat], opacity: p.t1 < now ? 1 : 0.4})));
  const nx = X(now); if (nx >= 0 && nx <= W) tl.append(svgEl("line", {x1: nx, x2: nx, y1: 2, y2: 28, stroke: "var(--text)", "stroke-width": 2}));
  const mins = Math.round((now - d0) / 6e4);
  const scrub = el("input", {type: "range", min: wa, max: wb, step: 1, value: Math.max(wa, Math.min(wb, mins)), "aria-label": "Time of day"});
  scrub.oninput = e => { M.satT = +e.target.value; stopSatPlay(); drawSats(); };
  const play = el("button", {className: "ghost tiny", type: "button", textContent: satPlay ? "❚❚ Pause" : "▶ Play", title: "Watch the satellites sweep across"}); play.onclick = () => satPlay ? stopSatPlay() : startSatPlay(wa, wb);
  const live = el("button", {className: "ghost tiny", type: "button", textContent: "Now", title: "Back to the live time"}); live.disabled = M.satT == null && M.satDay == 0;
  live.onclick = () => { stopSatPlay(); M.satDay = 0; M.satT = null; drawSats(); };
  const clock = el("span", {className: "mono satclock", textContent: hhmm(now) + (M.satT == null && M.satDay == 0 ? " · live" : "")});
  const list = el("table", {className: "mini satlist"}, all.filter(p => !M.satOff.has(p.sat)).map(p => {
    const st = p.t1 < now ? "✓ taken" : p.t0 > now ? (M.satDay == 0 ? "in " + until(p.t0 - now) : "") : "now";
    const tr = el("tr", {className: p.t1 < now ? "" : "fut"}, el("td", {className: "mono", textContent: hhmm(p.tm)}), el("td", {}, el("i", {className: "dot", style: `background:${SATCOL[p.sat]}`}), SATSHORT(p.sat)),
      el("td", {textContent: p.states.join(" · ")}), el("td", {className: "muted n", textContent: st}));
    tr.onclick = () => { const xs = p.xy.map(q => q[0]), ys = p.xy.map(q => q[1]); zoomToRect([Math.min(...xs) - 60, Math.min(...ys), Math.max(...xs) + 60, Math.max(...ys)], 0.95); };
    tr.title = "Click to zoom to this strip"; return tr; }));
  if (!all.length) list.append(el("tr", {}, el("td", {className: "muted", textContent: "No passes over the lower 48 this day."})));
  const age = Math.max(...(OVDATA.satrecs || []).map(s => Math.round((Date.now() - epochOf(s.l1)) / 864e5)));
  return [el("div", {className: "eyebrow", textContent: "\u{1F6F0}️ Satellite pictures"}),
    el("div", {className: "satrow"}, days, clock), chips, tl, el("div", {className: "satrow"}, scrub), el("div", {className: "satrow"}, play, live, el("span", {className: "note", textContent: "Drag to replay the day"})),
    el("div", {className: "satscroll"}, list),
    el("p", {className: "note", textContent: `Each colored band on the map is the strip one satellite photographs on one pass: ${SWATH["Sentinel-2"]} km wide for Sentinel-2, ${SWATH.Landsat} km for Landsat. Solid = already photographed, dashed = still to come. They all pass in the morning, local time (about 10:30), so the light is the same in every picture. A field gets a new Sentinel-2 picture every few days; clouds can hide it. Times are in your time zone.` + (age > 10 ? ` Orbit data is ${age} days old, so times may be off by a few minutes.` : "")})];
}
function satBlock() {
  if (!OV.sats || !M.satOpen) return [];
  return [el("div", {id: "satpanel", className: "satpanel"}, el("div", {className: "note", textContent: "Working out today's passes…"}))];
}
const until = ms => { const m = Math.round(ms / 6e4); if (m < 60) return m + " min"; if (m < 36 * 60) return Math.floor(m / 60) + " h" + (m % 60 && m < 600 ? " " + (m % 60) + " min" : "");
  const d = Math.round(m / 1440); return d + " day" + (d == 1 ? "" : "s"); };
let satPlay = null;
function startSatPlay(wa, wb) { if (M.satT == null || M.satT >= wb - 2 || M.satT < wa) M.satT = wa;
  satPlay = setInterval(() => { M.satT += 2; if (M.satT >= wb) { M.satT = wb; stopSatPlay(); } drawSats(); }, 70); drawSats(); }
function stopSatPlay() { if (satPlay) { clearInterval(satPlay); satPlay = null; } }

// ---------------------------------------------------------------- your location: search, pin, cows and pictures around you
function locControls() {
  const slot = $("#locslot"); if (!slot || $("#locbox")) return syncLocBox();
  const inp = el("input", {id: "locq", type: "search", placeholder: "Your town, ZIP or county", "aria-label": "Find a place", autocomplete: "off"});
  const go = el("button", {className: "act", type: "submit", textContent: "Go"});
  const me = el("button", {className: "ghost", type: "button", title: "Use my location", "aria-label": "Use my location", textContent: "\u{1F4CD}"});
  const form = el("form", {id: "locbox", role: "search"}, el("span", {className: "ctl-l", textContent: "Find your area"}), el("div", {className: "locrow"}, inp, go, me), el("span", {id: "locmsg", className: "locmsg"}));
  form.onsubmit = e => { e.preventDefault(); findPlace(inp.value); };
  me.onclick = useMyLocation; slot.replaceChildren(form); syncLocBox();
}
function syncLocBox() { const z = $("#zme"); if (z) z.hidden = !M.loc; }
function setMsg(t, bad) { const m = $("#locmsg"); if (m) { m.textContent = t || ""; m.classList.toggle("bad", !!bad); } }
const normCounty = s => s.toLowerCase().replace(/\b(county|parish|borough|census area|city and borough)\b/g, "").replace(/[^a-z, ]/g, "").replace(/\s+/g, " ").trim();
function matchCounty(q) {
  const [name, st] = normCounty(q).split(",").map(x => x.trim());
  const hits = Object.entries(EXT.county.names).filter(([f, n]) => { const [cn, cs] = n.split(","); return normCounty(cn) == name && (!st || cs.trim().toLowerCase() == st); });
  return hits.length == 1 || (hits.length && st) ? hits[0][0] : null;
}
async function geocode(q) {
  const tries = [
    async () => { const j = await fetch("https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=us&q=" + encodeURIComponent(q)).then(r => r.json());
      return j[0] && {lat: +j[0].lat, lon: +j[0].lon, label: j[0].display_name.split(",").slice(0, 2).join(",")}; },
    async () => { const j = await fetch("https://photon.komoot.io/api/?limit=1&q=" + encodeURIComponent(q + ", United States")).then(r => r.json()); const f = j.features?.find(f => f.properties.countrycode == "US");
      return f && {lon: f.geometry.coordinates[0], lat: f.geometry.coordinates[1], label: [f.properties.name, f.properties.state].filter(Boolean).join(", ")}; }];
  for (const t of tries) { try { const r = await t(); if (r) return r; } catch (e) { /* try the next lookup */ } }
  return null;
}
async function findPlace(q) {
  q = (q || "").trim(); if (!q) return; setMsg("Looking it up…");
  const ll = q.match(/^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/);
  if (ll) return setLocation({lat: +ll[1], lon: +ll[2], label: q});
  await loadCounties();
  const county = () => { const f = matchCounty(q); return f && CTYBY[f] ? {x: CTYBY[f].c[0], y: CTYBY[f].c[1], label: countyName(f)} : null; };
  const explicit = /county|parish|borough/i.test(q);
  const hit = (explicit && county()) || await geocode(q) || county();
  if (hit) return setLocation(hit);
  setMsg("Couldn't find that. Try a ZIP code or a county, like “Yolo County, CA”.", true);
}
function useMyLocation() {
  if (!navigator.geolocation) return setMsg("This browser can't share its location. Type a town instead.", true);
  setMsg("Asking your browser…");
  navigator.geolocation.getCurrentPosition(p => setLocation({lat: p.coords.latitude, lon: p.coords.longitude, label: "Your location"}),
    () => setMsg("Location is blocked. Type a town or ZIP instead.", true), {timeout: 12000, maximumAge: 6e5});
}
async function setLocation(p, opt = {}) {
  if (p.x == null) {
    if (!(p.lat > 24 && p.lat < 50 && p.lon > -125 && p.lon < -66)) return setMsg("That's outside the lower 48 states, which is all this map covers.", true);
    [p.x, p.y] = ALB(p.lon, p.lat); }
  await loadCounties();
  const c = countyAt(p.x, p.y); p.fips = c?.id || null;
  const label = (!p.label || /^[-\d.,\s]+$/.test(p.label)) && c ? countyName(c.id) : p.label;
  M.loc = {x: p.x, y: p.y, lat: p.lat, lon: p.lon, label, fips: p.fips}; M.sel = null;
  try { localStorage.setItem("board-loc", JSON.stringify(M.loc)); } catch (e) { /* storage off */ }
  setMsg(c ? "✓ " + countyName(c.id) : "✓ Found"); const q = $("#locq"); if (q && !opt.quiet) q.value = "";
  draw(); if (!opt.quiet) zoomToMe();
  ensureSats().then(() => setTimeout(fillLocSat, 30));
}
function zoomToMe() { if (!M.loc) return; const r = M.nearMi * 1.609 * KM_PX * 1.15; zoomToRect([M.loc.x - r, M.loc.y - r, M.loc.x + r, M.loc.y + r], 1, 16); }
function clearLocation() { M.loc = null; try { localStorage.removeItem("board-loc"); } catch (e) { /* storage off */ } setMsg(""); draw(); resetView(); }
function nearCounties(mi) {      // counties that reach within mi miles of the pin (distance to their nearest edge)
  if (!M.loc || !CTY) return [];
  const r = mi * 1.609 * KM_PX, {x, y} = M.loc, out = [];
  for (const c of CTY) {
    if (c.id == M.loc.fips) { out.push({c, d: 0, mi: 0}); continue; }
    if (x < c.b[0] - r || x > c.b[2] + r || y < c.b[1] - r || y > c.b[3] + r) continue;
    let d = Infinity;
    for (const ring of c.rings) for (let i = 1; i < ring.length; i++) { const [ax, ay] = ring[i - 1], [bx, by] = ring[i], dx = bx - ax, dy = by - ay, L = dx * dx + dy * dy || 1;
      const u = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / L)); d = Math.min(d, Math.hypot(ax + u * dx - x, ay + u * dy - y)); }
    if (d <= r) out.push({c, d, mi: d / KM_PX / 1.609});
  }
  return out;
}
function drawLoc() {
  const g = $("#locg"); if (!g) return; g.replaceChildren(); if (!M.loc) return;
  const {x, y} = M.loc, yr = EXT.county.census_years.at(-1), cows = EXT.county.milk_cows[yr] || {}, est = new Set(EXT.county.estimated?.milk_cows?.[yr] || []);
  const near = nearCounties(M.nearMi).filter(n => cows[n.c.id] > 0), R = M.nearMi * 1.609 * KM_PX;
  g.append(svgEl("circle", {cx: x, cy: y, r: R, class: "nearring"}));
  const mx = Math.max(1, ...near.map(n => cows[n.c.id])), rmax = Math.min(R * 0.22, 14);
  near.sort((a, b) => cows[b.c.id] - cows[a.c.id]).forEach((n, i) => {
    const v = cows[n.c.id], b = svgEl("circle", {cx: n.c.c[0], cy: n.c.c[1], r: Math.max(rmax * 0.12, rmax * Math.sqrt(v / mx)), class: "cowb"});
    b.addEventListener("pointermove", e => tipText(e, "\u{1F404} " + countyName(n.c.id), `${est.has(n.c.id) ? "about " : ""}${Math.round(v).toLocaleString("en-US")} milk cows` +
      (EXT.county.farms?.[yr]?.[n.c.id] ? ` on ${EXT.county.farms[yr][n.c.id]} farms` : "") + ` · ${n.mi < 1 ? "next door" : Math.round(n.mi) + " mi away"} (${yr} Census)`));
    b.addEventListener("pointerleave", () => $("#tip").hidden = true); g.append(b);
    if (i < 6) { const t = svgEl("text", {x: n.c.c[0], y: n.c.c[1], class: "cowl scale", "data-font-size": 10.5, "data-dy": 3.5}); t.textContent = "\u{1F404} " + kfmt(v); g.append(t); } });
  const halo = svgEl("circle", {cx: x, cy: y, class: "pinhalo scale", "data-r": 14}), pin = svgEl("circle", {cx: x, cy: y, class: "pin scale", "data-r": 6.5, "data-stroke-width": 2.5});
  const lab = svgEl("text", {x, y, class: "pinl scale", "data-font-size": 12, "data-dy": -14}); lab.textContent = M.loc.label || "You";
  g.append(halo, pin, lab);
}
function locBlock() {
  if (!M.loc || !EXT) return [];
  const p = M.loc, f = p.fips, yr = EXT.county.census_years.at(-1), C = EXT.county, cows = C.milk_cows[yr] || {}, sil = C.silage[yr] || {}, farms = C.farms?.[yr] || {};
  const estC = new Set(C.estimated?.milk_cows?.[yr] || []), estS = new Set(C.estimated?.silage?.[yr] || []);
  const near = nearCounties(M.nearMi), sum = o => near.reduce((a, n) => a + (o[n.c.id] || 0), 0), st = f ? stateOfFips(f) : null;
  const close = el("button", {className: "ghost tiny", type: "button", textContent: "✕", title: "Forget this place", "aria-label": "Forget this place"}); close.onclick = clearLocation;
  const radius = segOf([[25, "25 mi"], [50, "50 mi"], [100, "100 mi"]], M.nearMi, v => M.nearMi = v);
  radius.querySelectorAll("button").forEach(b => b.addEventListener("click", () => setTimeout(zoomToMe, 0)));
  const approx = (set, id) => set.has(id) ? "≈ " : "";
  const tile = (label, big, sub) => el("div", {className: "lt-tile"}, el("div", {className: "eyebrow", textContent: label}), el("div", {className: "lt-big", textContent: big}), sub ? el("div", {className: "note", textContent: sub}) : null);
  const kids = [el("div", {className: "lochead"}, el("div", {}, el("div", {className: "eyebrow", textContent: "\u{1F4CD} Around you"}), el("div", {className: "locname", textContent: f ? countyName(f) : (p.label || "Your spot")}),
    p.label && f && p.label != countyName(f) ? el("div", {className: "note", textContent: p.label}) : null), close)];
  if (f) {
    const top = near.filter(n => cows[n.c.id] > 0 && n.c.id != f).sort((a, b) => cows[b.c.id] - cows[a.c.id]).slice(0, 5);
    kids.push(el("div", {className: "lt-grid"},
      tile("Milk cows in this county", cows[f] != null ? approx(estC, f) + Math.round(cows[f]).toLocaleString("en-US") : "—", farms[f] ? `${farms[f]} dairy farm${farms[f] == 1 ? "" : "s"}` : "no dairy farms counted"),
      tile(`Milk cows within ${M.nearMi} mi`, kfmt(sum(cows)), `${near.filter(n => cows[n.c.id] > 0).length} counties`),
      tile("Silage acres, this county", sil[f] != null ? approx(estS, f) + kfmt(sil[f]) : "—"),
      tile(`Silage within ${M.nearMi} mi`, kfmt(sum(sil)) + " ac")),
      el("div", {className: "ctl inline"}, el("span", {className: "ctl-l", textContent: "Look within"}), radius),
      el("p", {className: "note", textContent: `${yr} USDA Census of Agriculture. ≈ = estimated where USDA withheld the exact number to protect individual farms.`}));
    if (top.length) { kids.push(el("h3", {textContent: "\u{1F404} Biggest dairy counties near you"}));
      const t = el("table", {className: "mini"}); top.forEach(n => { const tr = el("tr", {}, el("td", {textContent: countyName(n.c.id)}), el("td", {className: "n muted", textContent: n.mi < 1 ? "next door" : Math.round(n.mi) + " mi", title: "Distance to the nearest edge of the county"}), el("td", {className: "n", textContent: approx(estC, n.c.id) + kfmt(cows[n.c.id]) + " cows"}));
        tr.onclick = () => zoomToRect([n.c.b[0], n.c.b[1], n.c.b[2], n.c.b[3]], 0.6, 20); t.append(tr); }); kids.push(t); }
    const wy = Math.max(...Object.keys(C.weather).map(Number).filter(y => y < 2026)), w = C.weather[wy]?.[f];
    if (w) { kids.push(el("h3", {textContent: `Growing season ${wy} here`}), el("table", {className: "mini"},
      el("tr", {}, el("td", {textContent: "Rain, May–Sep"}), el("td", {className: "n", textContent: w[0] == null ? "—" : `${w[0] >= 0 ? "+" : ""}${Math.round(100 * w[0])}% vs normal`})),
      el("tr", {}, el("td", {textContent: "Heat (degree days)"}), el("td", {className: "n", textContent: w[1] == null ? "—" : `${w[1] >= 0 ? "+" : ""}${(100 * w[1]).toFixed(1)}% vs normal`})),
      el("tr", {}, el("td", {textContent: "First fall frost"}), el("td", {className: "n", textContent: doyDate(w[2])})))); }
  } else kids.push(el("p", {className: "note", textContent: "This spot isn't inside a county on the map (water, or outside the lower 48)."}));
  kids.push(el("h3", {textContent: "\u{1F6F0}️ Satellite pictures of your spot"}), el("div", {id: "locsat", className: "note", textContent: "Working out the next passes…"}));
  if (st) { const fcS = fcValue(M.fcModel.silage, st), fcG = fcValue(M.fcModel.grain, st), open = el("button", {className: "ghost tiny", type: "button", textContent: `Open ${NAMES[st] || st} →`}); open.onclick = () => select(st);
    kids.push(el("h3", {textContent: `${NAMES[st] || st}: 2026 forecast`}), el("table", {className: "mini"},
      el("tr", {}, el("td", {textContent: "Silage acres"}), el("td", {className: "n", textContent: fcS ? kfmt(fcS.predicted) : "—"})),
      el("tr", {}, el("td", {textContent: "Grain acres"}), el("td", {className: "n", textContent: fcG ? kfmt(fcG.predicted) : "—"}))), open); }
  setTimeout(fillLocSat, 0);
  return [el("div", {className: "locbox-panel"}, ...kids)];
}
function picturesAt(x, y, days = 8) {       // passes whose strip covers (x, y), from yesterday to a week out
  const out = [];
  for (let off = -1; off < days; off++) passesFor(off).forEach(ps => {
    const hw = swathKm(ps.sat) / 2 * KM_PX; let best = Infinity, bt = null;
    for (let i = 1; i < ps.xy.length; i++) { const [ax, ay] = ps.xy[i - 1], [bx, by] = ps.xy[i], dx = bx - ax, dy = by - ay, L = dx * dx + dy * dy || 1;
      const u = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / L)), d = Math.hypot(ax + u * dx - x, ay + u * dy - y);
      if (d < best) { best = d; bt = new Date(+ps.pts[i - 1].t + u * (ps.pts[i].t - ps.pts[i - 1].t)); } }
    if (best <= hw) out.push({sat: ps.sat, t: bt}); });
  return out.sort((a, b) => a.t - b.t);
}
function fillLocSat() {
  const box = $("#locsat"); if (!box || !M.loc || !OVDATA.satrecs) return;
  if (fillLocSat.key == M.loc.x + "," + M.loc.y && fillLocSat.html) { box.replaceChildren(...fillLocSat.html()); return; }
  const pics = picturesAt(M.loc.x, M.loc.y), now = new Date(), last = pics.filter(p => p.t < now).at(-1), next = pics.filter(p => p.t >= now).slice(0, 4);
  const when = d => d.toLocaleDateString("en-US", {weekday: "short", month: "short", day: "numeric"}) + ", " + hhmm(d);
  fillLocSat.key = M.loc.x + "," + M.loc.y;
  fillLocSat.html = () => [
    last ? el("div", {}, "Last picture: ", el("b", {textContent: last.sat}), ` · ${when(last.t)}`) : el("div", {textContent: "No picture since yesterday."}),
    next.length ? el("table", {className: "mini"}, next.map(p => el("tr", {}, el("td", {}, el("i", {className: "dot", style: `background:${SATCOL[p.sat]}`}), p.sat), el("td", {className: "n", textContent: when(p.t)}), el("td", {className: "n muted", textContent: "in " + until(p.t - now)}))))
      : el("div", {textContent: "No pass over this spot in the next week."}),
    el("div", {className: "note", textContent: "When a strip from the satellite map covers your spot. Clouds can still hide the ground."})];
  box.replaceChildren(...fillLocSat.html());
}
