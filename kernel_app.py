"""Kernel web app: one page that lets people use the repo's models in a browser.

Tabs
    Forecast     2026 corn-for-silage and corn-for-grain acres by state and for the US (from data/models/)
    Field model  the Quebec-trained logistic model: pick a Maryland field-year or type the six
                 satellite evidence numbers, get a 0-100 score, the call and what pushed it
    Reports      the repo's own offline pages (report/index.html, report/fields.html)
    About        backtest errors and the limits the README states

Optional: "Explain" asks an LLM to write 2-3 plain sentences about a field call. Every number is
computed in Python and the answer is checked against them. Point it at the GPU box
(vLLM / Ollama, OpenAI-compatible) or at NVIDIA's hosted endpoint with environment variables:
    KERNEL_LLM_BASE_URL   default https://integrate.api.nvidia.com/v1 if NVIDIA_API_KEY is set, else http://localhost:8000/v1
    KERNEL_LLM_MODEL      default nvidia/nemotron-3-super-120b-a12b (hosted) or nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16 (local)
    KERNEL_LLM_API_KEY    default NVIDIA_API_KEY; not needed for a local server

Run from the repository root:
    python kernel_app.py                  # http://0.0.0.0:7860
    KERNEL_PORT=9000 python kernel_app.py
"""

from __future__ import annotations

import json
import math
import os
import time
from contextlib import asynccontextmanager

import numpy as np
import pandas as pd
import requests
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from kernelag.explain import (
    EVIDENCE,
    SYSTEM,
    contributions,
    strip_reasoning,
    unsupported_numbers,
)
from kernelag.field_model import MODEL_FEATURES, load_training, make_model
from kernelag.paths import REPO, data_dir, secret

BAND = (40, 60)  # fixed abstention band on the 0-100 score, as in the repo's field explorer
STATE: dict = {}


def clean(value):
    """JSON-safe number: NaN and inf become None."""
    if isinstance(value, (float, np.floating)) and not math.isfinite(value):
        return None
    return value.item() if isinstance(value, np.generic) else value


def llm_settings() -> dict:
    key = os.environ.get("KERNEL_LLM_API_KEY") or secret("NVIDIA_API_KEY")
    base = os.environ.get("KERNEL_LLM_BASE_URL") or ("https://integrate.api.nvidia.com/v1" if key else "http://localhost:8000/v1")
    hosted = "nvidia.com" in base
    model = os.environ.get("KERNEL_LLM_MODEL") or (
        "nvidia/nemotron-3-super-120b-a12b" if hosted else "nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16")
    return {"base_url": base.rstrip("/"), "model": model, "key": key, "hosted": hosted}


@asynccontextmanager
async def lifespan(_: FastAPI):
    data = data_dir()
    train, _blocks = load_training(data)
    fit = train[train["assessable"]]
    STATE["model"] = make_model().fit(fit[MODEL_FEATURES], fit["is_silage"])
    STATE["train_n"] = len(fit)
    STATE["ranges"] = {
        name: {"min": float(fit[name].quantile(0.01)), "max": float(fit[name].quantile(0.99)),
               "median": float(fit[name].median())} for name in MODEL_FEATURES}
    STATE["forecast"] = pd.read_csv(data / "models" / "state_forecast_2026.csv")
    STATE["metrics"] = json.loads((data / "models" / "state_model_metrics.json").read_text())
    try:
        STATE["score_2025"] = json.loads((data / "models" / "state_score_2025.json").read_text())
    except FileNotFoundError:
        STATE["score_2025"] = None
    explorer = json.loads((data / "models" / "field_explorer.json").read_text())
    STATE["explorer_meta"] = explorer["metadata"]
    STATE["fields"] = [
        {"key": f"{f['field_id']}-{f['year']}", "field_id": f["field_id"], "year": f["year"], "county": f["county"],
         "acres": f["acres"], "reference_label": f["reference_label"],
         "features": {k: clean(f["features"].get(k)) for k in MODEL_FEATURES}}
        for f in explorer["fields"]]
    STATE["calls"] = []  # timestamps of recent LLM calls, for a crude rate limit
    yield


app = FastAPI(title="Kernel", lifespan=lifespan)


class FieldInput(BaseModel):
    features: dict[str, float | None]
    year: int | None = None


def score_field(features: dict) -> dict:
    row = pd.DataFrame([{name: features.get(name) for name in MODEL_FEATURES}], dtype=float)
    if row["max_drop"].isna().all():
        return {"assessable": False, "score": None, "call": "not assessable", "contributions": []}
    score = float(STATE["model"].predict_proba(row[MODEL_FEATURES])[0, 1]) * 100
    call = "uncertain" if BAND[0] <= score <= BAND[1] else ("silage-like" if score > BAND[1] else "grain-like")
    push = contributions(STATE["model"], row)
    ranked = sorted(push.items(), key=lambda item: -abs(item[1]))
    return {"assessable": True, "score": round(score, 1), "call": call,
            "contributions": [{"name": k, "label": EVIDENCE[k], "value": float(v)} for k, v in ranked]}


@app.get("/api/meta")
def meta():
    llm = llm_settings()
    return {
        "features": [{"name": n, "label": EVIDENCE[n], **STATE["ranges"][n]} for n in MODEL_FEATURES],
        "band": BAND, "train_n": STATE["train_n"],
        "llm": {"base_url": llm["base_url"], "model": llm["model"], "hosted": llm["hosted"]},
        "metrics": STATE["metrics"], "score_2025": STATE["score_2025"], "caveats": STATE["explorer_meta"]["caveats"],
    }


@app.get("/api/forecast")
def forecast():
    frame = STATE["forecast"].astype(object).where(STATE["forecast"].notna(), None)
    return frame.to_dict(orient="records")


@app.get("/api/fields")
def fields():
    return STATE["fields"]


@app.post("/api/score")
def score(body: FieldInput):
    return score_field(body.features)


def fact_sheet(result: dict, features: dict, year: int | None) -> str:
    lines = [f"Year: {year}."] if year else []
    lines.append(f"Model score for silage: {round(result['score'])} out of 100. Higher means more silage-like evidence; "
                 f"{BAND[0]} to {BAND[1]} is the band where the model abstains.")
    lines.append(f"Call: {result['call']}.")
    if features.get("green_at_cut") is not None:
        lines.append(f"Greenness just before the harvest: {round(100 * features['green_at_cut'])}% of the season peak.")
    if features.get("max_drop") is not None:
        lines.append(f"Greenness (NDVI) fell by {features['max_drop']:.2f} between two clear looks.")
    if features.get("ndmi_before_cut") is not None:
        lines.append(f"Canopy moisture index (NDMI) before the harvest: {features['ndmi_before_cut']:.2f}.")
    if features.get("ndti_post") is not None:
        lines.append(f"Residue index (NDTI) on the first bare looks after: {features['ndti_post']:.2f}.")
    for item in result["contributions"][:3]:
        lines.append(f"Evidence that weighed most: {item['label']}, pushing "
                     f"{'towards silage' if item['value'] > 0 else 'towards grain'}.")
    return "\n".join(lines)


@app.post("/api/explain")
def explain(body: FieldInput):
    result = score_field(body.features)
    if not result["assessable"]:
        raise HTTPException(422, "This field has no measurable greenness drop, so there is nothing to explain.")
    now = time.time()
    STATE["calls"] = [t for t in STATE["calls"] if now - t < 60]
    if len(STATE["calls"]) >= 10:
        raise HTTPException(429, "Too many explanations in the last minute; try again shortly.")
    STATE["calls"].append(now)

    llm = llm_settings()
    sheet = fact_sheet(result, body.features, body.year)
    payload = {
        "model": llm["model"], "temperature": 0.2, "max_tokens": 700,
        "messages": [
            {"role": "system", "content": SYSTEM + " The score is an uncalibrated model score, not a probability or a "
                                                   "confidence; do not call it either."},
            {"role": "user", "content": "Facts about one cornfield:\n" + sheet}]}
    if not llm["hosted"]:
        payload["chat_template_kwargs"] = {"enable_thinking": False}  # vLLM; Nemotron Nano may otherwise write reasoning
    headers = {"Authorization": f"Bearer {llm['key']}"} if llm["key"] else {}
    try:
        response = requests.post(f"{llm['base_url']}/chat/completions", json=payload, headers=headers, timeout=90)
        response.raise_for_status()
        text = strip_reasoning(response.json()["choices"][0]["message"].get("content") or "")
    except requests.RequestException as error:
        raise HTTPException(502, f"The language model at {llm['base_url']} did not answer: {type(error).__name__}") from error
    bad = unsupported_numbers(text, sheet)
    return {"explanation": text, "facts": sheet, "numbers_not_in_facts": bad, "model": llm["model"]}


app.mount("/report", StaticFiles(directory=REPO / "report", html=True), name="report")

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kernel</title>
<style>
:root{--bg:#0e1116;--panel:#151a22;--line:#262d38;--text:#e6e9ee;--muted:#8b95a5;--silage:#e0b04a;--grain:#5fa8d3;--warn:#c98a4b;
--sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 var(--sans)}
header{display:flex;align-items:baseline;gap:16px;padding:16px 24px;border-bottom:1px solid var(--line)}
header h1{font-size:20px;margin:0;font-weight:600}header span{color:var(--muted)}
nav{display:flex;gap:4px;padding:0 24px;border-bottom:1px solid var(--line)}
nav button{background:none;border:0;border-bottom:2px solid transparent;color:var(--muted);padding:12px 12px;font:inherit;cursor:pointer}
nav button[aria-selected=true]{color:var(--text);border-color:var(--silage)}
nav button:focus-visible,select:focus-visible,input:focus-visible,button.act:focus-visible{outline:2px solid var(--grain);outline-offset:2px}
main{padding:24px;max-width:1100px;margin:0 auto}section[hidden]{display:none}
h2{font-size:15px;margin:0 0 12px;font-weight:600}.muted{color:var(--muted)}.note{color:var(--muted);font-size:13px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin-bottom:24px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:16px}
.big{font:500 28px/1.2 var(--mono);font-variant-numeric:tabular-nums}.eyebrow{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
table{border-collapse:collapse;width:100%}th,td{text-align:right;padding:8px 10px;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums}
th:first-child,td:first-child{text-align:left}td.num{font-family:var(--mono)}th{color:var(--muted);font-weight:500;font-size:12px;cursor:pointer;user-select:none}
input,select{background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:8px 10px;font:inherit}
input[type=number]{width:110px;font-family:var(--mono)}
.grid2{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:24px}@media(max-width:800px){.grid2{grid-template-columns:1fr}}
.row{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:10px 0}.row label{flex:1}.row small{display:block;color:var(--muted)}
.badge{border:1px solid var(--line);border-radius:6px;padding:6px 10px}.silage-like{color:var(--silage)}.grain-like{color:var(--grain)}.uncertain,.not-assessable{color:var(--warn)}
.bar{height:8px;background:var(--line);border-radius:4px;position:relative;margin:6px 0 2px}.bar i{position:absolute;top:0;bottom:0;border-radius:4px}
.mid{position:absolute;left:50%;top:-3px;bottom:-3px;width:1px;background:var(--muted)}
button.act{background:var(--silage);color:#111;border:0;border-radius:6px;padding:8px 14px;font:inherit;font-weight:600;cursor:pointer}button.act:disabled{opacity:.5;cursor:wait}
iframe{width:100%;height:78vh;border:1px solid var(--line);border-radius:6px;background:#fff}
.callout{border-left:2px solid var(--warn);padding-left:12px;margin:12px 0}pre{white-space:pre-wrap;font:12px/1.5 var(--mono);color:var(--muted)}
</style></head><body>
<header><h1>Kernel</h1><span>Corn for silage and corn for grain: acreage forecasts and field evidence</span></header>
<nav role="tablist" id="tabs"></nav>
<main>
<section id="forecast">
 <div class="cards" id="us-cards"></div>
 <div class="row"><h2 style="margin:0">States, 2026 forecast (thousand acres, 80% range)</h2><input id="q" placeholder="Filter states" aria-label="Filter states"></div>
 <table id="state-table"><thead><tr><th data-k="state">State</th><th data-k="silage">Silage</th><th data-k="silage_lo80">80% range</th><th data-k="grain">Grain</th><th data-k="grain_lo80">80% range</th><th data-k="grain_method">Grain method</th></tr></thead><tbody></tbody></table>
 <p class="note">Grain rows marked <b>nass_forecast</b> repeat NASS's own in-season forecast; only silage is a Kernel estimate there. Ranges come from the backtest errors; see About for the coverage.</p>
</section>
<section id="field" hidden>
 <div class="grid2">
  <div class="card">
   <h2>Evidence for one field</h2>
   <div class="row"><label for="pick">Start from a labeled Maryland field-year<small>44 research-farm field-years; the model never trained on them</small></label><select id="pick"></select></div>
   <div id="inputs"></div>
   <p class="note">Leave "greenness drop" empty and the field is not assessable: the model does not guess from missing values.</p>
  </div>
  <div class="card">
   <div class="eyebrow">Uncalibrated model score</div>
   <div class="row"><div class="big" id="score">&mdash;</div><span class="badge" id="call">&mdash;</span></div>
   <div class="bar"><div class="mid"></div></div>
   <p class="note" id="reference"></p>
   <h2 style="margin-top:16px">What pushed the call</h2><div id="push"></div>
   <div class="callout note">The score is on a 0 to 100 scale. It is <b>not a probability</b> or a confidence. The 40 to 60 band is a fixed abstention rule.</div>
   <button class="act" id="explain">Explain with the language model</button>
   <p id="story" style="margin-top:12px"></p><p class="note" id="story-meta"></p>
  </div>
 </div>
</section>
<section id="reports" hidden>
 <div class="row"><h2 style="margin:0">Offline reports from the repository</h2><span><button class="act" data-src="/report/index.html">Acreage report</button> <button class="act" data-src="/report/fields.html">Field explorer</button></span></div>
 <iframe id="frame" title="Report" src="/report/index.html"></iframe>
</section>
<section id="about" hidden><div id="about-body"></div></section>
</main>
<script>
const $=s=>document.querySelector(s), el=(t,p={},...k)=>{const e=Object.assign(document.createElement(t),p);k.forEach(c=>e.append(c));return e};
const nf=new Intl.NumberFormat("en-US"), kac=v=>v==null?"\u2014":nf.format(Math.round(v/1000));
const TABS=[["forecast","Forecast"],["field","Field model"],["reports","Reports"],["about","About"]];
let META,FIELDS=[],ROWS=[],sortKey="silage",sortDir=-1;
TABS.forEach(([id,label],i)=>{const b=el("button",{textContent:label,role:"tab"});b.setAttribute("aria-selected",i==0);b.onclick=()=>{
 TABS.forEach(([x],j)=>{$("#"+x).hidden=x!=id;$("#tabs").children[j].setAttribute("aria-selected",x==id)})};$("#tabs").append(b)});
{const s=TABS.findIndex(([x])=>"#"+x==location.hash);if(s>0)$("#tabs").children[s].click()}
async function j(u,o){const r=await fetch(u,o);if(!r.ok){let m=r.statusText;try{m=(await r.json()).detail||m}catch{}throw new Error(m)}return r.json()}
function drawStates(){const q=$("#q").value.toLowerCase(),tb=$("#state-table tbody");tb.replaceChildren();
 ROWS.filter(r=>r.state.toLowerCase().includes(q)).sort((a,b)=>{const x=a[sortKey],y=b[sortKey];return a.state.startsWith("US")?-1:b.state.startsWith("US")?1:(typeof x=="string"?x.localeCompare(y):(x??-1)-(y??-1))*sortDir}).forEach(r=>{
 const tr=el("tr");tr.append(el("td",{textContent:r.state}),el("td",{className:"num",textContent:kac(r.silage)}),
 el("td",{className:"num muted",textContent:kac(r.silage_lo80)+" to "+kac(r.silage_hi80)}),el("td",{className:"num",textContent:kac(r.grain)}),
 el("td",{className:"num muted",textContent:kac(r.grain_lo80)+" to "+kac(r.grain_hi80)}),el("td",{className:"muted",textContent:r.grain_method||""}));tb.append(tr)})}
document.querySelectorAll("#state-table th").forEach(th=>th.onclick=()=>{const k=th.dataset.k;sortDir=k==sortKey?-sortDir:(k=="state"?1:-1);sortKey=k;drawStates()});
$("#q").oninput=drawStates;
function inputsUI(){const box=$("#inputs");META.features.forEach(f=>{const i=el("input",{type:"number",id:"f-"+f.name,step:"any",min:f.min.toFixed(3),max:f.max.toFixed(3)});
 i.oninput=run;const row=el("div",{className:"row"});const lab=el("label",{htmlFor:i.id,textContent:f.label});lab.append(el("small",{textContent:`typical ${f.median.toFixed(2)} (range ${f.min.toFixed(2)} to ${f.max.toFixed(2)} in training)`}));row.append(lab,i);box.append(row)})}
const read=()=>Object.fromEntries(META.features.map(f=>{const v=$("#f-"+f.name).value;return[f.name,v===""?null:Number(v)]}));
let timer,seq=0;function run(){clearTimeout(timer);timer=setTimeout(async()=>{const mine=++seq;$("#story").textContent="";$("#story-meta").textContent="";
 const r=await j("/api/score",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({features:read()})});if(mine!=seq)return;
 $("#score").textContent=r.score==null?"\u2014":r.score.toFixed(1);const c=$("#call");c.textContent=r.call;c.className="badge "+r.call.replace(" ","-");
 $("#explain").disabled=!r.assessable;const bar=$(".bar");bar.querySelectorAll("i").forEach(x=>x.remove());
 if(r.score!=null){bar.append(el("i",{style:`left:0;width:${r.score}%;background:var(--${r.score>META.band[1]?"silage":r.score<META.band[0]?"grain":"warn"})`}))}
 const p=$("#push");p.replaceChildren();const mx=Math.max(1,...r.contributions.map(x=>Math.abs(x.value)));
 r.contributions.forEach(x=>{const b=el("div",{className:"bar"});b.append(el("div",{className:"mid"}),el("i",{style:`${x.value>0?"left:50%":"right:50%"};width:${Math.abs(x.value)/mx*50}%;background:var(--${x.value>0?"silage":"grain"})`}));
  p.append(el("div",{className:"note",textContent:`${x.label} (${x.value>0?"+":""}${x.value.toFixed(2)})`}),b)})},120)}
$("#pick").onchange=()=>{const f=FIELDS.find(x=>x.key==$("#pick").value);META.features.forEach(m=>{const v=f?f.features[m.name]:null;$("#f-"+m.name).value=v==null?"":v});
 $("#reference").textContent=f?`Reference label in the organizers' data: ${f.reference_label}. ${f.county}, ${f.acres} acres, ${f.year}.`:"";run()};
$("#explain").onclick=async()=>{const b=$("#explain");b.disabled=true;$("#story").textContent="Asking the model...";$("#story-meta").textContent="";
 try{const f=FIELDS.find(x=>x.key==$("#pick").value);const r=await j("/api/explain",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({features:read(),year:f?f.year:null})});
  $("#story").textContent=r.explanation;$("#story-meta").textContent=`${r.model}. Numbers not found in the computed facts: ${r.numbers_not_in_facts.length?r.numbers_not_in_facts.join(", "):"none"}. A draft for an analyst, not a finding.`}
 catch(e){$("#story").textContent="";$("#story-meta").textContent="Explain is unavailable: "+e.message}finally{b.disabled=false}};
document.querySelectorAll("#reports button").forEach(b=>b.onclick=()=>{$("#frame").src=b.dataset.src});
function about(){const m=META.metrics.mean_errors_pct,t=el("table"),h=el("tr");["Backtest 2017 to 2024, mean error","State error %","US total error %"].forEach(x=>h.append(el("th",{textContent:x})));t.append(h);
 Object.entries(m).forEach(([k,v])=>{const r=el("tr");r.append(el("td",{textContent:k}),el("td",{className:"num",textContent:v.state_error_pct.toFixed(2)}),el("td",{className:"num",textContent:v.abs_total_error_pct.toFixed(2)}));t.append(r)});
 const b=$("#about-body");b.append(el("h2",{textContent:"How accurate are the state numbers"}),t,el("p",{className:"note",textContent:`Interval coverage in the backtest: silage ${META.metrics.interval_coverage.silage[80]} (80% range), grain ${META.metrics.interval_coverage.grain[80]}. Silage shows a modest gain over "same as last year" in the backtest that does not hold on the separate 2025 score; grain mostly reuses NASS's forecast.`}));
 const s=META.score_2025;if(s)b.append(el("p",{className:"note",textContent:`Separate 2025 score: silage state error ${s.silage.model.state_error_pct}% (model) vs ${s.silage.same_as_last_year.state_error_pct}% (same as last year); grain ${s.grain.model.state_error_pct}% vs ${s.grain.same_as_last_year.state_error_pct}%.`}));
 b.append(el("h2",{textContent:"Limits the repository states"}));const ul=el("ul");META.caveats.forEach(c=>ul.append(el("li",{className:"note",textContent:c})));b.append(ul,
 el("p",{className:"note",textContent:`Field model: logistic regression fitted on ${META.train_n} Quebec parcels. Language model: ${META.llm.model} at ${META.llm.base_url}.`}))}
(async()=>{META=await j("/api/meta");ROWS=await j("/api/forecast");FIELDS=await j("/api/fields");
 const us=ROWS.find(r=>r.state.startsWith("US"));
 [["Corn for silage, US","silage"],["Corn for grain, US","grain"]].forEach(([t,k])=>{const c=el("div",{className:"card"});c.append(el("div",{className:"eyebrow",textContent:t}),
  el("div",{className:"big",textContent:kac(us[k])+"k"}),el("div",{className:"note",textContent:`80% range ${kac(us[k+"_lo80"])}k to ${kac(us[k+"_hi80"])}k acres. Sum of the states shown.`}));$("#us-cards").append(c)});
 drawStates();inputsUI();const p=$("#pick");p.append(el("option",{value:"",textContent:"Type my own numbers"}));
 FIELDS.forEach(f=>p.append(el("option",{value:f.key,textContent:`Field ${f.field_id}, ${f.year} (${f.reference_label})`})));
 p.value=FIELDS[0].key;p.onchange();about()})().catch(e=>document.body.prepend(el("p",{className:"callout",textContent:"Could not load: "+e.message})));
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("KERNEL_PORT", "7860")))
