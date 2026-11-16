// Board extras for the briefing: feed stress, drought what-if, "silage or grain?" field checker,
// one-page state briefs and a full-screen briefing mode. Uses the globals of page.html and map.js.
"use strict";
let DR = null, FIELDS = null, TEAM = null;

// ---------------------------------------------------------------- feed stress watch
const FEED_MIN_RAIN_MM = 150;      // rain is only a signal where summer rain normally matters (not the irrigated West)
function feedLevel(f, w) {
  if (!w || w[0] == null || (EXT.county.rain_normal?.[f] ?? 0) < FEED_MIN_RAIN_MM) return 0;
  const r = w[0], h = w[1] ?? 0;
  if (r <= -0.30 || (r <= -0.20 && h >= 0.05)) return 2;
  if (r <= -0.20 || (r <= -0.10 && h >= 0.05)) return 1;
  return 0;
}
function feedYears() { return Object.keys(EXT.county.weather).map(Number).sort((a, b) => a - b); }
function feedCensus(year) { const ys = EXT.county.census_years; return ys.filter(y => y <= year).at(-1) || ys[0]; }
function feedStats(year) {
  const w = EXT.county.weather[year] || {}, cy = feedCensus(year), cows = EXT.county.milk_cows[cy] || {};
  const lvl = {}; let watch = 0, severe = 0, total = 0;
  for (const f in cows) total += cows[f];
  for (const f in w) { const l = feedLevel(f, w[f]); if (l) { lvl[f] = l; watch += cows[f] || 0; if (l == 2) severe += cows[f] || 0; } }
  return {lvl, watch, severe, total, cy};
}
const feedWord = l => l == 2 ? "Severe: very dry" : l == 1 ? "Watch: dry" : "Normal";

// ---------------------------------------------------------------- drought what-if (the drought term of B-S6)
function bs6Id() { return Object.values(MODELS).find(m => m.model == "B-S6" && m.target == "silage" && m.has_forecast)?.model_id || M.fcModel.silage; }
function ag9Id() { return Object.values(MODELS).find(m => m.model == "A-G9" && m.target == "grain" && m.has_forecast)?.model_id || M.fcModel.grain; }
function whatIf() {
  if (!DR) return null;
  const g = DR.gamma, base = bs6Id(), out = {states: {}, us0: 0, us1: 0, moved: 0, gamma: g};
  const past = M.wi.mode != "custom" ? DR.by_year[M.wi.mode] || {} : null;
  D.forecast.filter(r => r.model_id == base && r.state != "US").forEach(r => {
    const s = DR.states[r.state]; out.us0 += r.predicted;
    if (!s) { out.us1 += r.predicted; return; }
    const inScope = M.wi.where == "ALL" || M.wi.where == r.state;
    const sf = !inScope ? s.shortfall : Math.max(s.shortfall, past ? (past[r.state] ?? s.shortfall) : M.wi.pct / 100);   // a drought only adds: keep this year's if it is worse
    const extra = g * (Math.max(0, sf - DR.threshold) - Math.max(0, s.shortfall - DR.threshold)) * s.grain_last;
    out.states[r.state] = {base: r.predicted, extra, pct: 100 * extra / r.predicted, sf};
    out.us1 += r.predicted + extra; out.moved += extra;
  });
  return out;
}
function whatIfControls(parts) {
  const scen = el("select", {"aria-label": "Scenario"}, [["custom", "Pick how bad"], ...[2012, 2020, 2023, 2011, 2006].filter(y => DR?.by_year[y]).map(y => [y, `Repeat the ${y} season`])].map(([v, l]) => el("option", {value: v, textContent: l, selected: String(M.wi.mode) == String(v)})));
  scen.onchange = e => { M.wi.mode = e.target.value == "custom" ? "custom" : +e.target.value; draw(); };
  parts.push(ctlField("Drought", scen, "Replay a real bad year, or pick a yield loss yourself."));
  if (M.wi.mode == "custom") { const r = el("input", {type: "range", min: 0, max: 60, step: 5, value: M.wi.pct, "aria-label": "Yield below trend"});
    r.oninput = e => { M.wi.pct = +e.target.value; draw(); };
    parts.push(ctlField("Corn yield below normal", el("span", {className: "yr"}, r, el("b", {className: "mono", textContent: M.wi.pct + "%"})), "How far below its trend the corn yield falls. Farmers start chopping failed grain for silage past about 10%.")); }
  const where = el("select", {"aria-label": "Where"}, [["ALL", "Every state"], ...Object.keys(DR?.states || {}).sort().map(s => [s, NAMES[s] || s])].map(([v, l]) => el("option", {value: v, textContent: l, selected: M.wi.where == v})));
  where.onchange = e => { M.wi.where = e.target.value; draw(); };
  parts.push(ctlField("Where", where));
}
function whatIfBlock() {
  const w = whatIf(); if (!w) return [el("p", {className: "note", textContent: "The what-if needs the drought data (board/drought.py)."})];
  const top = Object.entries(w.states).filter(([, v]) => v.extra > 0.5).sort((a, b) => b[1].extra - a[1].extra).slice(0, 8);
  const desc = M.wi.mode == "custom" ? `corn yield ${M.wi.pct}% below normal in ${M.wi.where == "ALL" ? "every state" : NAMES[M.wi.where]}` : `the ${M.wi.mode} season again${M.wi.where == "ALL" ? "" : " in " + NAMES[M.wi.where]}`;
  const kids = [el("div", {className: "eyebrow", textContent: "What if a drought hits?"}),
    el("div", {className: "hero", textContent: (w.moved >= 0 ? "+" : "") + kfmt(w.moved)}),
    el("div", {className: "note", textContent: `extra acres chopped for silage with ${desc} · US silage ${kfmt(w.us0)} → ${kfmt(w.us1)} (${w.us0 ? (100 * (w.us1 / w.us0 - 1) >= 0 ? "+" : "") + (100 * (w.us1 / w.us0 - 1)).toFixed(1) : 0}%)`}),
    el("p", {className: "callout", textContent: `Those acres come out of the grain harvest: about ${kfmt(Math.max(0, w.moved))} fewer acres of corn for grain.`})];
  if (top.length) { kids.push(el("h3", {textContent: "Most extra silage"}));
    const t = el("table", {className: "mini"}); top.forEach(([s, v]) => { const tr = el("tr", {}, el("td", {textContent: NAMES[s] || s}), el("td", {className: "n muted", textContent: `yield ${Math.round(100 * v.sf)}% below`}), el("td", {className: "n", textContent: "+" + kfmt(v.extra)}));
      tr.onclick = () => select(s); t.append(tr); }); kids.push(t); }
  else kids.push(el("p", {className: "note", textContent: "No extra chopping: farmers only start chopping failed grain once the yield is more than 10% below normal."}));
  kids.push(el("p", {className: "note", textContent: `How it works: the headline silage model (B-S6) adds ${w.gamma} × (yield shortfall − 10%) × last year's grain acres. That share (${w.gamma}) was learned from 2005–2025 only. It is why 2012's drought pushed US silage from 6.0 to 7.4 million acres. Map colors: % more silage than our 2026 forecast.`}));
  return [el("div", {className: "wibox"}, ...kids)];
}

// ---------------------------------------------------------------- inverse of the map projection (map units -> lon, lat)
const UNALB = (() => { const r = Math.PI / 180, y0 = 29.5 * r, y1 = 45.5 * r, n = (Math.sin(y0) + Math.sin(y1)) / 2, c = 1 + Math.sin(y0) * (2 * n - Math.sin(y0)), r0 = Math.sqrt(c) / n;
  const raw = (x, y) => { const rr = Math.sqrt(c - 2 * n * Math.sin(y)) / n; x *= n; return [rr * Math.sin(x), r0 - rr * Math.cos(x)]; };
  const k = 1300, cen = raw(-0.6 * r, 38.7 * r), dx = 487.5 - k * cen[0], dy = 305 + k * cen[1];
  return (X, Y) => { const x = (X - dx) / k, y = (dy - Y) / k, rr = Math.hypot(x, r0 - y), lam = Math.atan2(x, r0 - y) / n, phi = Math.asin((c - rr * rr * n * n) / (2 * n));
    return [lam / r - 96, phi / r]; }; })();

// ---------------------------------------------------------------- "silage or grain?" field checker
const FC = {open: false, tab: "test", pick: null, sel: null, live: null, busy: false, year: new Date().getFullYear(), picking: false};
async function loadFields() { if (!FIELDS) FIELDS = await fetch("/api/fields_md").then(r => r.json()); return FIELDS; }
function fieldButton() {
  if ($("#fieldbtn")) return;
  const b = el("button", {id: "fieldbtn", className: "act", type: "button", title: "Pick a cornfield and see whether it was chopped for silage or harvested for grain", textContent: "\u{1F33D} Silage or grain?"});
  b.onclick = () => openFieldCard("test"); $(".tb-right")?.prepend(b);
}
async function openFieldCard(tab, sel) {
  FC.open = true; if (tab) FC.tab = tab; await loadFields();
  if (sel) FC.sel = sel; else if (!FC.sel) FC.sel = FIELDS.fields.find(f => f.id == "barc_280" && f.year == 2021) || FIELDS.fields[0];
  renderFieldCard();
}
function closeFieldCard() { FC.open = false; FC.picking = false; $("#fieldcard")?.remove(); $("#usmap")?.classList.remove("picking"); }
function renderFieldCard() {
  let card = $("#fieldcard"); if (!card) { card = el("div", {id: "fieldcard", role: "dialog", "aria-label": "Silage or grain?"}); $(".stage").append(card); }
  const x = el("button", {className: "ghost tiny", type: "button", textContent: "✕ Close"}); x.onclick = closeFieldCard;
  const tabs = el("span", {className: "seg"}, [["test", `USDA test fields (${FIELDS.correct}/${FIELDS.n} right)`], ["live", "Any field in the US (live)"]].map(([k, l]) => {
    const b = el("button", {type: "button", textContent: l}); b.setAttribute("aria-pressed", FC.tab == k); b.onclick = () => { FC.tab = k; renderFieldCard(); }; return b; }));
  const head = el("div", {className: "fchead"}, el("div", {}, el("b", {textContent: "\u{1F33D} Silage or grain? One field at a time, from space"}),
    el("div", {className: "note", textContent: "Silage is chopped in one pass, so the field's greenness drops off a cliff. Grain corn dries slowly first. The rule times the drop."})), x);
  card.replaceChildren(head, el("div", {className: "satrow"}, tabs), FC.tab == "test" ? testFieldBody() : liveFieldBody());
}
function testFieldBody() {
  const f = FC.sel, list = el("div", {className: "fclist"});
  [2021, 2022, 2023].forEach(y => { list.append(el("div", {className: "lm-g", textContent: y}));
    FIELDS.fields.filter(q => q.year == y).sort((a, b) => a.field - b.field).forEach(q => {
      const ok = q.call == q.truth, b = el("button", {className: "fcitem" + (q === f ? " on" : ""), type: "button", title: `USDA: ${q.truth} · rule: ${q.call}`},
        el("span", {textContent: "Field " + q.field}), el("span", {className: "tagt " + q.truth, textContent: q.truth}), el("span", {className: ok ? "pass" : "fail", textContent: ok ? "✓" : "✗"}));
      b.onclick = () => { FC.sel = q; renderFieldCard(); }; list.append(b); }); });
  return el("div", {className: "fcbody"}, list, el("div", {className: "fcmain"}, verdictBox(f, f.truth), ndviChart(f), aerial(f.lon, f.lat, f.outline),
    el("p", {className: "note", textContent: `Field ${f.field}, ${f.acres} acres, USDA's Beltsville research farm in Maryland, ${f.year}. Each dot is one Sentinel-2 picture (faint = mostly cloudy); the line is the smoothed greenness. ${FIELDS.correct} of ${FIELDS.n} test field-years are called right with a rule learned only on Quebec farms.`})));
}
function liveFieldBody() {
  const p = FC.pick, years = []; for (let y = new Date().getFullYear(); y >= 2019; y--) years.push(y);
  const ys = el("select", {"aria-label": "Season"}, years.map(y => el("option", {value: y, textContent: y, selected: y == FC.year}))); ys.onchange = e => { FC.year = +e.target.value; FC.live = null; renderFieldCard(); };
  const pickBtn = el("button", {className: FC.picking ? "act" : "ghost", type: "button", textContent: FC.picking ? "Click the map…" : "\u{1F5FA}️ Pick a spot on the map"});
  pickBtn.onclick = () => { FC.picking = !FC.picking; $("#usmap").classList.toggle("picking", FC.picking); renderFieldCard(); if (FC.picking) $("#fieldcard").classList.add("tucked"); };
  const go = el("button", {className: "act", type: "button", textContent: FC.busy ? "Reading pictures…" : "Check this field", disabled: !p || FC.busy}); go.onclick = runLive;
  const kids = [el("div", {className: "satrow"}, pickBtn, ctlField("Season", ys), go)];
  if (!p) kids.push(el("p", {className: "note", textContent: "Zoom the map to a corn area (for example Wisconsin or Iowa), press “Pick a spot”, then click. A satellite photo of that spot opens here: click inside one field to move the pin, then check it. The server reads every Sentinel-2 picture of that spot for the season, which takes 20–60 seconds."}));
  else {
    kids.push(el("div", {className: "note", textContent: `${p.lat.toFixed(5)}, ${p.lon.toFixed(5)}${p.fips ? " · " + countyName(p.fips) : ""} · click inside a single field on the photo to move the pin`}));
    const main = el("div", {className: "fcmain"});
    if (FC.busy) main.append(el("div", {className: "fcbusy"}, el("div", {className: "spin"}), el("div", {textContent: `Reading every Sentinel-2 picture of this spot for ${FC.year}…`}), el("div", {className: "note", textContent: "About 60–100 pictures, a few seconds each, read in parallel."})));
    else if (FC.live?.error) main.append(el("p", {className: "callout", textContent: FC.live.error}));
    else if (FC.live) main.append(verdictBox(FC.live), ndviChart(FC.live), el("p", {className: "note", textContent: `${FC.live.pictures} Sentinel-2 pictures, ${FC.live.clear} clear enough to use. Check the photo: the pin must sit inside one cornfield. Other crops, roads or woods give a meaningless answer.`}));
    main.append(aerial(p.lon, p.lat, null, (lon, lat) => { FC.pick = {...FC.pick, lon, lat}; FC.live = null; renderFieldCard(); }));
    kids.push(main);
  }
  return el("div", {className: "fcbody one"}, el("div", {}, ...kids));
}
async function runLive() {
  const p = FC.pick; if (!p || FC.busy) return; FC.busy = true; FC.live = null; renderFieldCard();
  try { const r = await fetch(`/api/field?lon=${p.lon}&lat=${p.lat}&year=${FC.year}&fips=${p.fips || ""}`); const j = await r.json(); FC.live = r.ok ? j : {error: j.error || "Lookup failed."}; }
  catch (e) { FC.live = {error: window.__SNAP ? "The live lookup needs the hosted board; this offline copy only has the USDA test fields." : "Couldn't reach the board's server."}; }
  FC.busy = false; if (FC.open) renderFieldCard();
}
async function fieldMapClick(e) {        // capture-phase click on the US map while picking
  if (!FC.picking || dragged) return; e.stopPropagation(); e.preventDefault();
  const [sx, sy] = svgPt($("#usmap"), e), x = (sx - M.tx) / M.k, y = (sy - M.ty) / M.k, [lon, lat] = UNALB(x, y);
  if (!(lat > 24 && lat < 50 && lon > -125 && lon < -66)) return;
  await loadCounties(); const c = countyAt(x, y);
  FC.pick = {lon, lat, fips: c?.id || null}; FC.live = null; FC.picking = false; FC.tab = "live"; $("#usmap").classList.remove("picking"); $("#fieldcard")?.classList.remove("tucked"); renderFieldCard();
}
function verdictBox(r, truth) {
  if (!r.call) return el("p", {className: "callout", textContent: r.why || "No answer."});
  const f = r.features || {};
  return el("div", {className: "verdict " + r.call}, el("div", {className: "vbig", textContent: r.call == "silage" ? "SILAGE" : "GRAIN"}),
    el("div", {}, el("div", {textContent: r.why}), truth ? el("div", {className: truth == r.call ? "pass" : "fail", textContent: `USDA's record: ${truth} ${truth == r.call ? "✓ right" : "✗ missed"}`}) : null,
      f.drop_days != null ? el("div", {className: "note", textContent: `Drop from 80% to 20% green: day ${f.drop_start} → day ${f.drop_end} (${doyDate(f.drop_start)} to ${doyDate(f.drop_end)}). Cut-off: ${r.cutoff} days.`}) : null));
}
function ndviChart(r) {
  const W = 560, H = 210, L = 34, R = 10, T = 10, B = 26, x0 = 60, x1 = 360, X = d => L + (d - x0) / (x1 - x0) * (W - L - R), Y = v => T + (1 - Math.max(0, Math.min(1, v))) * (H - T - B);
  const s = svgEl("svg", {viewBox: `0 0 ${W} ${H}`, width: "100%", class: "ndvi"}), f = r.features || {};
  [0, 0.25, 0.5, 0.75, 1].forEach(v => { s.append(svgEl("line", {x1: L, x2: W - R, y1: Y(v), y2: Y(v), class: "grid"})); const t = svgEl("text", {x: L - 5, y: Y(v) + 3, "text-anchor": "end"}); t.textContent = v.toFixed(2).replace(/0$/, ""); s.append(t); });
  [91, 152, 213, 274, 335].forEach(d => { const t = svgEl("text", {x: X(d), y: H - 8, "text-anchor": "middle"}); t.textContent = new Date(2026, 0, d).toLocaleDateString("en-US", {month: "short"}); s.append(t); });
  if (f.drop_start != null) { s.append(svgEl("rect", {x: X(f.drop_start), y: T, width: Math.max(2, X(f.drop_end) - X(f.drop_start)), height: H - T - B, class: "dropwin " + r.call}));
    const span = f.peak - f.low; [0.8, 0.2].forEach(q => s.append(svgEl("line", {x1: L, x2: W - R, y1: Y(f.low + q * span), y2: Y(f.low + q * span), class: "lvl"})));
    const t = svgEl("text", {x: (X(f.drop_start) + X(f.drop_end)) / 2, y: T + 12, "text-anchor": "middle", class: "droplab"}); t.textContent = `${f.drop_days} days`; s.append(t); }
  (r.points || []).forEach(([d, v, c]) => d >= x0 && d <= x1 && s.append(svgEl("circle", {cx: X(d), cy: Y(v), r: 2.6, class: "pt" + (c >= 0.4 ? "" : " cloudy")})));
  if (r.line?.length) s.append(svgEl("path", {d: "M" + r.line.filter(p => p[0] >= x0 && p[0] <= x1).map(p => X(p[0]).toFixed(1) + "," + Y(p[1]).toFixed(1)).join("L"), class: "ln"}));
  return el("div", {className: "ndvibox"}, el("div", {className: "note", textContent: "Greenness (NDVI) through the season · dashed lines: 80% and 20% of this field's range"}), s);
}
// Satellite photo of a spot (Esri World Imagery tiles), with the field outline or a pin. Click to move the pin.
function aerial(lon, lat, outline, onPick) {
  const z = 16, n = 2 ** z, wx = (lon + 180) / 360 * n * 256, wy = (1 - Math.log(Math.tan(lat * Math.PI / 180) + 1 / Math.cos(lat * Math.PI / 180)) / Math.PI) / 2 * n * 256;
  const W = 768, H = 512, ox = wx - W / 2, oy = wy - H / 2, box = el("div", {className: "aerial"});
  const tx0 = Math.floor(ox / 256), ty0 = Math.floor(oy / 256), tx1 = Math.floor((ox + W) / 256), ty1 = Math.floor((oy + H) / 256);
  let failed = false;
  for (let tx = tx0; tx <= tx1; tx++) for (let ty = ty0; ty <= ty1; ty++) {
    const img = el("img", {alt: "", src: `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${z}/${ty}/${tx}`, draggable: false});
    Object.assign(img.style, {left: (100 * (tx * 256 - ox) / W) + "%", top: (100 * (ty * 256 - oy) / H) + "%", width: (100 * 256 / W) + "%", height: (100 * 256 / H) + "%"});
    img.onerror = () => { img.remove(); if (!failed) { failed = true; box.append(el("div", {className: "aerr", textContent: "Satellite photo didn't load (no connection to the imagery service). The result above doesn't need it."})); } };
    box.append(img); }
  const ov = svgEl("svg", {viewBox: `0 0 ${W} ${H}`, class: "aov"}), P = (lo, la) => { const px = (lo + 180) / 360 * n * 256 - ox, py = (1 - Math.log(Math.tan(la * Math.PI / 180) + 1 / Math.cos(la * Math.PI / 180)) / Math.PI) / 2 * n * 256 - oy; return [px, py]; };
  if (outline) outline.forEach(ring => ov.append(svgEl("path", {d: "M" + ring.map(q => P(...q).map(v => v.toFixed(1)).join(",")).join("L") + "Z", class: "aoutline"})));
  else { ov.append(svgEl("circle", {cx: W / 2, cy: H / 2, r: 45 / (156543.03 * Math.cos(lat * Math.PI / 180) / n), class: "adisc"}), svgEl("circle", {cx: W / 2, cy: H / 2, r: 5, class: "apin"})); }
  box.append(ov, el("div", {className: "attr", textContent: "Imagery: Esri, Maxar, Earthstar Geographics"}));
  if (onPick) { box.classList.add("clickable"); box.onclick = e => { const b = box.getBoundingClientRect(), px = (e.clientX - b.left) / b.width * W + ox, py = (e.clientY - b.top) / b.height * H + oy;
    const lo = px / (n * 256) * 360 - 180, la = Math.atan(Math.sinh(Math.PI * (1 - 2 * py / (n * 256)))) * 180 / Math.PI; onPick(lo, la); }; }
  return box;
}

// ---------------------------------------------------------------- one-page state brief (opens a printable page)
function stateBriefButton(code) {
  const b = el("button", {className: "ghost tiny", type: "button", textContent: "\u{1F5A8}️ One-page brief"}); b.onclick = () => stateBrief(code); return b;
}
function stateBrief(code) {
  const name = NAMES[code] || code, esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
  const sid = bs6Id(), gid = ag9Id(), fs = fcValue(sid, code), fg = fcValue(gid, code), yr = Math.max(lastActualYear("silage"), lastActualYear("grain"));
  const h = (c, y) => hist(code, y)?.[c], chg = (v, b) => v != null && b ? `${v >= b ? "+" : ""}${(100 * (v / b - 1)).toFixed(1)}% vs ${yr}` : "";
  const C = EXT.county, cy = C.census_years.at(-1), inSt = f => stateOfFips(f) == code;
  const cows = Object.entries(C.milk_cows[cy] || {}).filter(([f]) => inSt(f)), cowSum = cows.reduce((a, [, v]) => a + v, 0);
  const farms = Object.entries(C.farms?.[cy] || {}).filter(([f]) => inSt(f)).reduce((a, [, v]) => a + v, 0);
  const silC = Object.entries(C.silage[cy] || {}).filter(([f]) => inSt(f)).reduce((a, [, v]) => a + v, 0);
  const topC = cows.sort((a, b) => b[1] - a[1]).slice(0, 5);
  const fy = feedYears().at(-1), fst = feedStats(fy), feedCows = Object.entries(fst.lvl).filter(([f]) => inSt(f)).reduce((a, [f]) => a + ((C.milk_cows[fst.cy] || {})[f] || 0), 0);
  const svg = briefChart(code, fs, fg), hv = EXT.harvest[code];
  const best = crop => errModels(crop).map(mid => ({mid, e: stateErrors(mid)[code]})).filter(x => x.e).sort((a, b) => a.e.v - b.e.v);
  const pickErr = (crop, head) => { const all = best(crop), h = all.find(x => x.mid == head); return [...(h ? [h] : []), ...all.filter(x => x.mid != head).slice(0, h ? 2 : 3)]; };
  const errs = [...pickErr("silage", sid), ...pickErr("grain", gid)];
  const dr = DR?.states[code], wi20 = dr ? DR.gamma * (Math.max(0, 0.20 - DR.threshold) - Math.max(0, dr.shortfall - DR.threshold)) * dr.grain_last : null;
  const sig = hist(code, lastActualYear("silage")) || {};
  const row = (k, v) => `<tr><td>${esc(k)}</td><td class="n">${esc(v)}</td></tr>`;
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${esc(name)}: corn grain and silage brief</title><style>
@page{size:letter;margin:14mm}body{font:12px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;color:#15181d;margin:0 auto;max-width:780px;padding:18px}
h1{font-size:22px;margin:0}h2{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#5a6270;margin:14px 0 4px;border-bottom:1px solid #dde1e7;padding-bottom:3px}
.sub{color:#5a6270}.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:12px 0}.kpi{border:1px solid #dde1e7;border-radius:8px;padding:8px 10px}
.kpi b{display:block;font:600 20px/1.2 ui-monospace,Menlo,monospace}.kpi span{font-size:10.5px;color:#5a6270;text-transform:uppercase;letter-spacing:.05em}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:16px}table{border-collapse:collapse;width:100%}td{padding:3px 4px;border-bottom:1px solid #eef0f3}td.n{text-align:right;font-family:ui-monospace,Menlo,monospace}
.foot{margin-top:14px;font-size:10px;color:#6b7280;border-top:1px solid #dde1e7;padding-top:6px}button{position:fixed;top:12px;right:12px;padding:8px 14px;font:600 13px sans-serif;background:#e0b04a;border:0;border-radius:6px;cursor:pointer}
@media print{button{display:none}}</style></head><body><button onclick="print()">Print / Save as PDF</button>
<div class="sub">${esc(TEAM?.team || "Team Kernel")} · ${esc(TEAM?.event || "Hack the Harvest 2026")} · ${new Date().toLocaleDateString("en-US", {year: "numeric", month: "long", day: "numeric"})}</div>
<h1>${esc(name)}: corn for grain and silage, 2026</h1>
<div class="kpis"><div class="kpi"><span>Silage acres, 2026 forecast</span><b>${fs ? kfmt(fs.predicted) : "—"}</b>${fs?.lo80 != null ? `80% range ${kfmt(fs.lo80)}–${kfmt(fs.hi80)} · ` : ""}${chg(fs?.predicted, h("silage", yr))}</div>
<div class="kpi"><span>Grain acres, 2026 forecast</span><b>${fg ? kfmt(fg.predicted) : "—"}</b>${fg?.lo80 != null ? `80% range ${kfmt(fg.lo80)}–${kfmt(fg.hi80)} · ` : ""}${chg(fg?.predicted, h("grain", yr))}</div>
<div class="kpi"><span>Milk cows (${cy} Census)</span><b>${kfmt(cowSum)}</b>${farms ? farms.toLocaleString("en-US") + " dairy farms" : ""}</div></div>
<h2>Acres harvested (NASS finals) and our 2026 forecast</h2>${svg}
<div class="cols"><div><h2>Where the cows are</h2><table>${topC.map(([f, v]) => row(countyName(f), kfmt(v) + " cows")).join("")}${row("Silage acres, all counties (" + cy + " Census)", kfmt(silC))}</table>
<h2>This season (${fy})</h2><table>${row("Cows in counties with a dry season", feedCows ? kfmt(feedCows) + " (" + Math.round(100 * feedCows / Math.max(1, cowSum)) + "%)" : "none")}
${sig.drought != null ? row("Drought, share of state D2+ (" + sig.year + ")", Math.round(100 * sig.drought) + "%") : ""}${sig.poor_condition != null ? row("Corn rated poor/very poor (" + sig.year + ")", Math.round(100 * sig.poor_condition) + "%") : ""}
${hv?.typical_half_doy ? row("Half the silage usually chopped by", doyDate(hv.typical_half_doy)) : ""}${hv?.half_doy ? row(`Half chopped in ${hv.latest_year} by`, doyDate(hv.half_doy)) : ""}</table></div>
<div><h2>If drought hits</h2><p>${dr ? `If ${esc(name)}'s corn yield fell 20% below normal, our silage model expects about <b>${kfmt(Math.max(0, wi20))}</b> more acres chopped for silage, taken out of the grain harvest. ${DR.worst[code] ? `Worst year on record here: ${DR.worst[code].year} (${Math.round(100 * DR.worst[code].shortfall)}% below trend).` : ""}` : "No drought data for this state."}</p>
<h2>Track record in ${esc(code)}</h2><table>${errs.map(x => row((x.mid == sid || x.mid == gid ? "★ " : "") + (MODELS[x.mid]?.label || x.mid) + " (" + (MODELS[x.mid]?.target || "") + ")", x.e.v.toFixed(1) + "% avg miss")).join("") || row("No state-level backtests", "")}</table><p style="font-size:10px;color:#6b7280;margin:4px 0 0">★ = headline model. Average miss per year in this state, backtest years.</p><table></table></div></div>
<div class="foot">Forecasts: headline models A-G9 (grain: FSA certified acres × each state's usual NASS/FSA ratio) and B-S6 (silage: smoothed level plus drought chopping from NASS's in-season yield forecast), as of 15 November; neither uses NASS's acreage forecast.
Data: USDA NASS Quick Stats and Census of Agriculture (counties USDA withholds are estimated), USDA FSA crop acreage, NOAA nClimGrid, US Drought Monitor. Backtest misses are averages over the board's backtest years. Code and data: ${esc(REPO_URL().replace("https://", ""))}</div>
</body></html>`;
  const w = open(URL.createObjectURL(new Blob([html], {type: "text/html"})), "_blank");
  if (!w) alert("Your browser blocked the new tab. Allow pop-ups for this page to open the brief.");
}
function briefChart(code, fs, fg) {
  const W = 740, H = 170, L = 50, R = 70, T = 8, B = 20, yr = Math.max(lastActualYear("silage"), lastActualYear("grain"));
  const rows = MAP.history.filter(r => r.state == code && r.year >= yr - 15 && (r.silage != null || r.grain != null)).sort((a, b) => a.year - b.year), y0 = rows[0]?.year ?? yr - 15;
  const vals = rows.flatMap(r => [r.silage, r.grain]).concat([fs?.predicted, fg?.predicted]).filter(v => v != null), hi = Math.max(1, ...vals) * 1.08;
  const X = y => L + (y - y0) / (yr + 1 - y0) * (W - L - R), Y = v => T + (1 - v / hi) * (H - T - B), line = (k, c) => {
    const pts = rows.filter(r => r[k] != null); return pts.length ? `<path d="M${pts.map(r => X(r.year).toFixed(1) + "," + Y(r[k]).toFixed(1)).join("L")}" fill="none" stroke="${c}" stroke-width="2"/>` : ""; };
  let g = ""; for (let i = 0; i <= 4; i++) { const v = hi * i / 4; g += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="#eef0f3"/><text x="${L - 6}" y="${Y(v) + 3}" text-anchor="end" font-size="9" fill="#6b7280">${kfmt(v)}</text>`; }
  for (let y = Math.ceil(y0 / 5) * 5; y <= yr + 1; y += 5) g += `<text x="${X(y)}" y="${H - 5}" text-anchor="middle" font-size="9" fill="#6b7280">${y}</text>`;
  const dot = (v, c, lab) => v == null ? "" : `<circle cx="${X(yr + 1)}" cy="${Y(v.predicted)}" r="4.5" fill="${c}"/>${v.lo80 != null ? `<line x1="${X(yr + 1)}" x2="${X(yr + 1)}" y1="${Y(v.lo80)}" y2="${Y(v.hi80)}" stroke="${c}" stroke-width="2"/>` : ""}<text x="${X(yr + 1) + 8}" y="${Y(v.predicted) + 3}" font-size="10" fill="${c}">2026 ${lab}</text>`;
  return `<svg viewBox="0 0 ${W} ${H}" width="100%">${g}${line("grain", "#c98500")}${line("silage", "#1c7c54")}${dot(fg, "#c98500", "grain")}${dot(fs, "#1c7c54", "silage")}</svg>`;
}

// ---------------------------------------------------------------- briefing mode: a short story told on the live map
const BRIEF = [];
function briefingSteps() {
  const sid = bs6Id(), gid = ag9Id(), us = id => usTotal(id, MODELS[id]?.target) || {}, yrs = [2017, 2024];
  const err = id => { const r = (BT[id] || []).filter(x => (x.asof == null || x.asof == "nov") && x.year >= yrs[0] && x.year <= yrs[1] && x.state_error_pct != null); return r.length ? r.reduce((a, x) => a + x.state_error_pct, 0) / r.length : null; };
  const nass = (CAT.benchmarks || []).find(b => b.crop == "grain" && /NASS/i.test(b.label))?.model_id, last = (CAT.benchmarks || []).find(b => b.crop == "silage" && /last year/i.test(b.label))?.model_id;
  const eG = err(gid), eN = nass && err(nass), eS = err(sid), eL = last && err(last);
  const fst = feedStats(feedYears().at(-1)), cowsUS = Object.values(EXT.county.milk_cows[EXT.county.census_years.at(-1)] || {}).reduce((a, b) => a + b, 0);
  const saved = {mode: M.wi.mode, where: M.wi.where, pct: M.wi.pct};
  Object.assign(M.wi, {mode: DR?.by_year[2012] ? 2012 : "custom", where: "ALL", pct: 30}); const w12 = whatIf(); Object.assign(M.wi, saved);
  return [
    {t: "Grain or silage?", b: `Knowing in November what USDA publishes in January. ${TEAM?.team || "Team Kernel"} · ${TEAM?.event || "Hack the Harvest 2026"}${TEAM?.award ? " · " + TEAM.award : ""}.`,
      credits: true, go: () => { setLayer("forecast", "silage"); resetView(); }},
    {t: "Two harvests, one crop", b: "US corn is harvested two ways. Grain: the crop dries and a combine takes the kernels. Silage: the whole green plant is chopped as cattle feed. From space they look the same until harvest day, and USDA publishes the official split in January, after markets have moved.",
      go: () => { setLayer("history", "silage"); resetView(); }},
    {t: "Our 2026 answer, today", b: `Silage: ${kfmt(us(sid).v)} acres${us(sid).lo != null ? ` (80% range ${kfmt(us(sid).lo)}–${kfmt(us(sid).hi)})` : ""}. Grain: ${kfmt(us(gid).v)} acres. Tested on every year ${yrs[0]}–${yrs[1]} as of November 15: grain lands within ${eG?.toFixed(2)}% by state${eN ? `, tied with NASS's own November forecast (${eN.toFixed(2)}%)` : ""}; silage within ${eS?.toFixed(1)}%${eL ? `, better than “same as last year” (${eL.toFixed(1)}%)` : ""}. No NASS acreage forecast goes in.`,
      go: () => { setLayer("forecast", "silage"); resetView(); }},
    {t: "Silage follows the cows", b: `Silage is cow feed, so it's grown next to dairies: ${(cowsUS / 1e6).toFixed(1)} million milk cows in the ${EXT.county.census_years.at(-1)} Census, county by county. Wisconsin, New York and California's Central Valley stand out.`,
      go: () => { setLayer("dairy"); resetView(); }},
    {t: "When drought hits, farmers chop", b: `When the corn fails, farmers chop it for feed instead of waiting for grain, and our silage model has that built in. Replay 2012's drought on this year's fields: about ${w12 ? kfmt(w12.moved) : "—"} more acres chopped for silage (US silage ${w12 ? kfmt(w12.us0) + " → " + kfmt(w12.us1) : ""}), taken straight out of the grain harvest.`,
      go: () => { M.wi.mode = DR?.by_year[2012] ? 2012 : "custom"; M.wi.pct = 30; M.wi.where = "ALL"; setLayer("whatif"); resetView(); }, done: () => Object.assign(M.wi, saved)},
    {t: "Where to watch this season", b: `${(fst.watch / 1e6).toFixed(1)} million milk cows (${Math.round(100 * fst.watch / Math.max(1, fst.total))}% of the herd) are in counties that had a dry ${feedYears().at(-1)} growing season. That's where feed is tight and more corn gets chopped.`,
      go: () => { M.fyear = feedYears().at(-1); setLayer("feed"); resetView(); }},
    {t: "Every field, from space", b: `Sentinel-2 and Landsat photograph every US cornfield every few days. Silage fields lose their green in days; grain fades over weeks. That one rule calls ${FIELDS ? FIELDS.correct + " of " + FIELDS.n : "42 of 44"} of USDA's labeled test fields right.`,
      go: async () => { closeFieldCard(); if (!OV.sats) { OV.sats = true; await drawOverlays(); } setLayer("satellite"); resetView(); await openFieldCard("test"); }, done: () => closeFieldCard()},
    {t: "Your county", b: `Type any town, ZIP code or county in \u201cFind your area\u201d: the cows, silage, weather, forecast and next satellite picture around it. All the code and data are open: ${REPO_URL().replace("https://", "")}. Thank you.`,
      go: () => { closeFieldCard(); OV.sats = false; drawOverlays(); setLayer("dairy"); setTimeout(() => $("#locq")?.focus(), 400); }},
  ];
}
function setLayer(k, crop) { if (crop) M.crop = crop; M.layer = k; M.sel = null; draw(); }
let BSTEP = -1, BSTEPS = null;
async function startBriefing() {
  endGuide(false); closeLayerMenu(); try { DR ??= await fetch("/api/drought").then(r => r.ok ? r.json() : null); } catch (e) { /* optional */ }
  await loadFields().catch(() => null); S.tab = "map"; draw();
  BSTEPS = briefingSteps(); document.body.classList.add("briefing"); BSTEP = -1; await briefTo(0);
  try { await document.documentElement.requestFullscreen?.(); } catch (e) { /* not allowed: fine */ }
  addEventListener("keydown", briefKey, true);
}
async function briefTo(i) {
  if (BSTEP >= 0) BSTEPS[BSTEP].done?.();
  BSTEP = Math.max(0, Math.min(BSTEPS.length - 1, i)); const st = BSTEPS[BSTEP];
  await st.go?.(); setTimeout(() => applyT(), 50);
  let card = $("#briefcard"); if (!card) { card = el("div", {id: "briefcard"}); document.body.append(card); }
  const prev = el("button", {className: "ghost", type: "button", textContent: "← Back", disabled: BSTEP == 0}); prev.onclick = () => briefTo(BSTEP - 1);
  const next = el("button", {className: "act", type: "button", textContent: BSTEP == BSTEPS.length - 1 ? "Finish" : "Next →"}); next.onclick = () => BSTEP == BSTEPS.length - 1 ? endBriefing() : briefTo(BSTEP + 1);
  const exit = el("button", {className: "linkish", type: "button", textContent: "Exit (Esc)"}); exit.onclick = endBriefing;
  const credits = st.credits && TEAM?.members?.length ? el("div", {className: "bcred"}, TEAM.members.map(m => el("span", {textContent: m.name + (m.role ? " · " + m.role : "")}))) : null;
  card.replaceChildren(...[el("div", {className: "bstep", textContent: `${BSTEP + 1} / ${BSTEPS.length}`}), el("h2", {textContent: st.t}), el("p", {textContent: st.b}), credits,
    el("div", {className: "grow"}, el("div", {className: "gdots"}, BSTEPS.map((_, j) => el("i", {className: j == BSTEP ? "on" : ""}))), exit, prev, next)].filter(Boolean));
  next.focus();
}
function briefKey(e) {
  if (e.target.tagName == "INPUT" && e.key != "Escape") return;
  if (e.key == "ArrowRight" || e.key == " " || e.key == "PageDown") { e.preventDefault(); e.stopPropagation(); BSTEP == BSTEPS.length - 1 ? endBriefing() : briefTo(BSTEP + 1); }
  else if (e.key == "ArrowLeft" || e.key == "PageUp") { e.preventDefault(); e.stopPropagation(); briefTo(BSTEP - 1); }
  else if (e.key == "Escape") { e.preventDefault(); e.stopPropagation(); endBriefing(); }
}
function endBriefing() {
  BSTEPS?.[BSTEP]?.done?.(); BSTEP = -1; $("#briefcard")?.remove(); document.body.classList.remove("briefing"); removeEventListener("keydown", briefKey, true);
  if (document.fullscreenElement) document.exitFullscreen?.().catch(() => null);
  draw(); setTimeout(() => applyT(), 50);
}
function teamFooter() {
  if ($("#teamfoot") || !TEAM) return;
  document.body.append(el("footer", {id: "teamfoot"}, el("b", {textContent: TEAM.team}), " · ", (TEAM.members || []).map(m => m.name).join(", "), " · ", TEAM.event, " \u00b7 ", el("a", {href: REPO_URL(), target: "_blank", rel: "noopener", className: "brlink", textContent: "Code on GitHub"}),
    el("div", {className: "note", textContent: "Data: USDA NASS Quick Stats and Census of Agriculture, USDA FSA crop acreage, USDA RMA, NOAA nClimGrid, US Drought Monitor, ESA Sentinel-2 (Copernicus) via Microsoft Planetary Computer, USGS Landsat. Orbits: CelesTrak. Place search: OpenStreetMap."})));
}

// ---------------------------------------------------------------- "About & code": a README for the GitHub repo
const REPO_URL = () => TEAM?.repo || "https://github.com/Severynson/Hack-the-Harvest";
function headline() {   // the same live numbers the briefing uses
  const sid = bs6Id(), gid = ag9Id(), yrs = [2017, 2024];
  const err = id => { const r = (BT[id] || []).filter(x => (x.asof == null || x.asof == "nov") && x.year >= yrs[0] && x.year <= yrs[1] && x.state_error_pct != null); return r.length ? r.reduce((a, x) => a + x.state_error_pct, 0) / r.length : null; };
  const nass = (CAT.benchmarks || []).find(b => b.crop == "grain" && /NASS/i.test(b.label))?.model_id, last = (CAT.benchmarks || []).find(b => b.crop == "silage" && /last year/i.test(b.label))?.model_id;
  return {yrs, eG: err(gid), eN: nass && err(nass), eS: err(sid), eL: last && err(last), sUS: usTotal(sid, "silage"), gUS: usTotal(gid, "grain")};
}
async function aboutTab() {
  const box = $("#about"); if (!box) return;
  if (!TEAM) TEAM = await fetch("/api/team").then(r => r.ok ? r.json() : null).catch(() => null);
  await loadFields().catch(() => null);
  const R = REPO_URL(), h = headline(), f2 = v => v == null ? "—" : v.toFixed(2) + "%", f1 = v => v == null ? "—" : v.toFixed(1) + "%";
  const a = (href, text, cls = "") => el("a", {href, target: "_blank", rel: "noopener", className: cls, textContent: text});
  const card = (title, ...kids) => el("div", {className: "card"}, el("h2", {textContent: title}), ...kids);
  const branch = (name, what, path, label) => el("div", {className: "brcard"}, el("div", {className: "mono br", textContent: name}), el("p", {textContent: what}), a(R + path, label + " →", "brlink"));
  box.replaceChildren(
    el("div", {className: "abouthero"},
      el("div", {}, el("div", {className: "eyebrow", textContent: `${TEAM?.team || "Team Kernel"} · ${TEAM?.event || "Hack the Harvest 2026"}`}),
        el("h1", {textContent: "Grain or silage? Corn harvest type from public data"}),
        el("p", {textContent: "USDA's National Agricultural Statistics Service publishes how much US corn was harvested for grain and how much was chopped for silage in January. We estimate both in November, state by state, from public data, and call single fields from satellite pictures. All the code, data and tests are open."}),
        TEAM?.award ? el("p", {className: "callout", textContent: "\u{1F3C6} " + TEAM.award}) : null),
      el("div", {className: "aboutbtns"}, a(R, "⭐ View the code on GitHub", "act big"), a(R + "/blob/main/grain-or-silage.ipynb", "Open the notebook", "ghostl"),
        a(R + "/tree/hackathon-2026-submission", "Full hackathon code", "ghostl"), TEAM?.live_url ? a(TEAM.live_url, "Live board", "ghostl") : null,
        el("div", {className: "mono note", textContent: R.replace("https://", "")}))),
    el("div", {className: "aboutgrid"},
      card("What's in the repository",
        branch("main", "The clean version: one notebook (grain-or-silage.ipynb) with the three headline models, 9 MB of public data, runs start to finish offline in about 20 seconds.", "", "Browse main"),
        branch("hackathon-2026-submission", "Everything from the two hackathon days, unchanged: every experiment, all of the team's models, the agents' coordination files and the data this board reads.", "/tree/hackathon-2026-submission", "Browse the full history"),
        branch("board", "This website: the model board, its map layers, the briefing mode and the field checker (folder board/).", "/tree/board/board", "Browse the board code")),
      card("The three models, and how well they do",
        el("table", {className: "mini"},
          el("tr", {}, el("td", {}, el("b", {textContent: "A-G9 · grain acres by state"}), el("div", {className: "note", textContent: "Farmers certify their planted acres and intended use to USDA's Farm Service Agency by mid-July. Each state's FSA count differs from NASS's final by a steady ratio: learn it from the last three years and apply it."})),
            el("td", {className: "n", textContent: `${f2(h.eG)} state error`}), el("td", {className: "n muted", textContent: h.eN != null ? `NASS's own Nov forecast: ${f2(h.eN)}` : ""})),
          el("tr", {}, el("td", {}, el("b", {textContent: "B-S6 · silage acres by state"}), el("div", {className: "note", textContent: "A smoothed level of each state's past silage acres (most year-to-year swings are survey noise), plus the acres farmers chop when drought ruins the grain crop, from NASS's in-season yield forecast."})),
            el("td", {className: "n", textContent: `${f1(h.eS)} state error`}), el("td", {className: "n muted", textContent: h.eL != null ? `Same as last year: ${f1(h.eL)}` : ""})),
          el("tr", {}, el("td", {}, el("b", {textContent: "Caveman rule · silage or grain, per field"}), el("div", {className: "note", textContent: "Silage is chopped in one pass, so a field's greenness falls off a cliff; grain fades for weeks. Silage if greenness falls from 80% to 20% of its range in under 17.5 days. Learned on 801 Quebec fields, tested on USDA's Maryland fields."})),
            el("td", {className: "n", textContent: FIELDS ? `${FIELDS.correct}/${FIELDS.n} fields right` : "42/44 fields right"}), el("td", {className: "n muted", textContent: "Always guessing grain: 72.7%"}))),
        el("p", {className: "note", textContent: `State error = total acres put in the wrong state ÷ true acres, averaged over forecasts made each 15 November, ${h.yrs[0]}–${h.yrs[1]}. No model uses NASS's acreage forecast for the year it predicts. 2026 forecast: ${h.sUS ? (h.sUS.v / 1e6).toFixed(2) + "M acres of silage" : "—"}, ${h.gUS ? (h.gUS.v / 1e6).toFixed(2) + "M acres of grain" : "—"}.`})),
      card("Run it yourself",
        el("p", {className: "note", textContent: "The notebook (main branch): no accounts or keys needed."}),
        el("pre", {textContent: `git clone ${R}.git\ncd Hack-the-Harvest\npip install -r requirements.txt\njupyter lab grain-or-silage.ipynb      # Run All, about 20 seconds`}),
        el("p", {className: "note", textContent: "This board (board branch, reading the full hackathon data):"}),
        el("pre", {textContent: `git clone --branch hackathon-2026-submission ${R}.git hth\ncd hth\ngit fetch origin board && git checkout origin/board -- board\npip install pandas numpy pyarrow geopandas fastapi uvicorn\npython board/app.py                      # http://localhost:7870`})),
      card("Data (all public)",
        el("ul", {className: "srcs"}, [
          ["USDA NASS Quick Stats", "acres, yields, prices, harvest progress, milk cows", "https://quickstats.nass.usda.gov/"],
          ["USDA Census of Agriculture", "county milk cows and silage acres, 2017 and 2022", "https://www.nass.usda.gov/AgCensus/"],
          ["USDA FSA crop acreage", "acres farmers certify, by intended use", "https://www.fsa.usda.gov/news-room/efoia/electronic-reading-room/frequently-requested-information/crop-acreage-data"],
          ["USDA ARS Beltsville", "the organizers' labeled Maryland fields", ""],
          ["La Financière agricole du Québec", "801 declared grain/silage parcels, 2023", ""],
          ["ESA Copernicus Sentinel-2", "field greenness, via Microsoft Planetary Computer", "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a"],
          ["NOAA nClimGrid · US Drought Monitor · USDA RMA", "weather, drought and insurance losses", ""],
        ].map(([n, w, u]) => el("li", {}, u ? a(u, n) : el("b", {textContent: n}), " — ", w)))),
      card("Team",
        el("div", {className: "teamlist"}, (TEAM?.members || []).map(m => el("div", {}, el("b", {textContent: m.name}), m.role ? el("div", {className: "note", textContent: m.role}) : null))),
        el("p", {className: "note", textContent: "Questions or ideas: open an issue on GitHub."}), a(R + "/issues", "Open an issue →", "brlink"))));
}
