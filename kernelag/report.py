"""One offline page that shows the answer and the evidence: ``report/index.html``.

Every number on the page is read from files the pipeline wrote; nothing is typed by hand, and a
value that was not computed is shown as "—". The page is one self-contained HTML file (inline CSS
and SVG, no scripts, no network).

Steps:
    1. Gather the model outputs into ``data/models/metrics.json``.
    2. Render seven sections: the answer, states, trust, bias, earliness, the field signal, limits.

Reads (``data/models/``): state_forecast_<year>.csv, state_model_metrics[_asof_sep].json,
state_model_backtest.csv, state_model_bias.csv, state_score_2025.json, field_eval.json,
field_earliness.csv, field_model_coefficients.csv; plus the Maryland labels and series.

Run: ``python -m kernelag.report``
"""

from __future__ import annotations

import argparse
import html
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from kernelag.field_model import load_series
from kernelag.paths import REPO, data_dir, record_in_manifest

FORECAST_YEAR = 2026
DASH = "—"
FEATURE_WORDS = {
    "max_drop": "Size of the greenness drop",
    "max_drop_rate": "Speed of the drop",
    "fade_days": "Days from green to bare",
    "green_at_cut": "Greenness just before the cut",
    "ndmi_before_cut": "Canopy moisture before the cut",
    "ndti_post": "Residue left after the cut",
}
PREDICTOR_WORDS = {
    "same_as_last_year": "Last year", "reversion_only": "Kernel", "nass_latest": "Kernel",
    "reversion_plus_satellite": "Kernel + satellite", "satellite_ratio": "Satellite ratio",
}


# --- reading -------------------------------------------------------------------------------------

def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def gather(models: Path) -> dict:
    """All headline numbers in one dictionary, written to ``metrics.json``."""
    forecast = read_csv(models / f"state_forecast_{FORECAST_YEAR}.csv")
    us = forecast[forecast["state"].str.startswith("US")].iloc[0].to_dict() if len(forecast) else {}
    return {
        "built_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
        "forecast_year": FORECAST_YEAR,
        "us_forecast": {k: v for k, v in us.items() if k not in ("year", "state")},
        "forecast_scope": {name: int(forecast.loc[~forecast["state"].str.startswith("US"), name].notna().sum())
                           for name in ("silage", "grain")} if len(forecast) else {},
        "state_model": read_json(models / "state_model_metrics.json"),
        "state_model_asof_sep": read_json(models / "state_model_metrics_asof_sep.json"),
        "score_2025": read_json(models / "state_score_2025.json"),
        "field_eval": read_json(models / "field_eval.json"),
    }


# --- formatting ----------------------------------------------------------------------------------

def missing(value) -> bool:
    return value is None or (isinstance(value, float) and not math.isfinite(value))


def acres(value, unit: float = 1e6, digits: int = 2) -> str:
    """Acres in millions (or thousands with ``unit=1e3``), or a dash."""
    return DASH if missing(value) else f"{value / unit:,.{digits}f}"


def number(value, digits: int = 1, suffix: str = "") -> str:
    return DASH if missing(value) else f"{value:,.{digits}f}{suffix}"


def dig(tree: dict, *keys):
    """A nested value, or None if any key is absent."""
    for key in keys:
        if not isinstance(tree, dict) or key not in tree:
            return None
        tree = tree[key]
    return tree


def esc(text) -> str:
    return html.escape(str(text))


# --- charts (inline SVG) -------------------------------------------------------------------------

def line_chart(labels: list, lines: list[dict], unit: str, width: int = 640, height: int = 220,
               y_max: float | None = None) -> str:
    """Lines over categories. Each line: name, values, css class. Ends are labeled directly."""
    values = [v for line in lines for v in line["values"] if not missing(v)]
    if not values:
        return f'<p class="muted">{DASH} not computed</p>'
    top = y_max or max(values) * 1.15
    left, right, upper, lower = 40, 170, 12, 26
    step = (width - left - right) / max(len(labels) - 1, 1)

    def x(i: int) -> float:
        return left + i * step

    def y(v: float) -> float:
        return upper + (height - upper - lower) * (1 - v / top)

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{esc(unit)} by {esc(labels[0])} to {esc(labels[-1])}">']
    for tick in range(5):
        v = top * tick / 4
        parts.append(f'<line class="grid" x1="{left}" x2="{width - right}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>'
                     f'<text class="tick" x="{left - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v:.0f}</text>')
    for i, label in enumerate(labels):
        parts.append(f'<text class="tick" x="{x(i):.1f}" y="{height - 6}" text-anchor="middle">{esc(label)}</text>')
    ends = []
    for line in lines:
        points = [(x(i), y(v)) for i, v in enumerate(line["values"]) if not missing(v)]
        if not points:
            continue
        path = " ".join(f"{'M' if k == 0 else 'L'}{px:.1f},{py:.1f}" for k, (px, py) in enumerate(points))
        parts.append(f'<path class="line {line["css"]}" d="{path}"/>')
        parts += [f'<circle class="dot {line["css"]}" cx="{px:.1f}" cy="{py:.1f}" r="2.5"/>' for px, py in points]
        ends.append([points[-1][1], line])
    ends.sort(key=lambda item: item[0])
    for k in range(1, len(ends)):                      # keep end labels 14 px apart
        ends[k][0] = max(ends[k][0], ends[k - 1][0] + 14)
    for py, line in ends:
        last = [v for v in line["values"] if not missing(v)][-1]
        parts.append(f'<text class="end {line["css"]}" x="{width - right + 8}" y="{py + 4:.1f}">'
                     f'{esc(line["name"])} {last:.1f}</text>')
    parts.append(f'<text class="tick" x="{left}" y="10">{esc(unit)}</text></svg>')
    return "".join(parts)


def range_bar(low, value, high, scale: float, css: str, width: int = 180) -> str:
    """A point estimate with its interval on a shared scale."""
    if missing(value) or not scale:
        return DASH

    def x(v: float) -> float:
        return min(v / scale, 1.0) * (width - 4) + 2

    whisker = "" if missing(low) or missing(high) else (
        f'<line class="whisker {css}" x1="{x(low):.1f}" x2="{x(high):.1f}" y1="7" y2="7"/>')
    return (f'<svg class="bar" viewBox="0 0 {width} 14" width="{width}" height="14" aria-hidden="true">'
            f'<line class="grid" x1="2" x2="{width - 2}" y1="7" y2="7"/>{whisker}'
            f'<circle class="dot {css}" cx="{x(value):.1f}" cy="7" r="3.5"/></svg>')


def signed_bar(value, scale: float, width: int = 180) -> str:
    """A bar left or right of zero."""
    if missing(value) or not scale:
        return DASH
    half = width / 2
    length = min(abs(value) / scale, 1.0) * (half - 2)
    start = half if value >= 0 else half - length
    return (f'<svg class="bar" viewBox="0 0 {width} 14" width="{width}" height="14" aria-hidden="true">'
            f'<rect class="signed" x="{start:.1f}" y="3" width="{length:.1f}" height="8"/>'
            f'<line class="zero" x1="{half}" x2="{half}" y1="0" y2="14"/></svg>')


def curves_chart(series: pd.DataFrame, width: int = 640, height: int = 240) -> str:
    """Greenness through the season, one thin line per field-year; silage solid, grain dashed."""
    if series.empty:
        return f'<p class="muted">{DASH} no series</p>'
    left, right, upper, lower = 40, 150, 12, 26
    first, last = 121, 334                                   # 1 May to 30 November

    def x(doy: float) -> float:
        return left + (doy - first) / (last - first) * (width - left - right)

    def y(v: float) -> float:
        return upper + (height - upper - lower) * (1 - max(min(v, 1.0), 0.0))

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Greenness by date, silage and grain fields">']
    for v in (0, 0.25, 0.5, 0.75, 1.0):
        parts.append(f'<line class="grid" x1="{left}" x2="{width - right}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>'
                     f'<text class="tick" x="{left - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v:.2f}</text>')
    for doy, label in [(121, "May"), (152, "Jun"), (182, "Jul"), (213, "Aug"), (244, "Sep"), (274, "Oct"), (305, "Nov")]:
        parts.append(f'<text class="tick" x="{x(doy):.1f}" y="{height - 6}">{label}</text>')
    for label, css in [("grain", "grain thin"), ("silage", "silage thin")]:
        for _, field in series[series["label"] == label].groupby(["field_id", "year"]):
            field = field[(field["doy"] >= first) & (field["doy"] <= last)].sort_values("doy")
            if len(field) > 2:
                path = " ".join(f"{'M' if k == 0 else 'L'}{x(d):.1f},{y(v):.1f}"
                                for k, (d, v) in enumerate(zip(field["doy"], field["ndvi"])))
                parts.append(f'<path class="line {css}" d="{path}"/>')
    parts.append(f'<text class="end silage" x="{width - right + 8}" y="{y(0.75):.1f}">Silage: solid</text>'
                 f'<text class="end grain" x="{width - right + 8}" y="{y(0.75) + 16:.1f}">Grain: dashed</text>'
                 f'<text class="tick" x="{left}" y="10">NDVI (greenness)</text></svg>')
    return "".join(parts)


# --- sections ------------------------------------------------------------------------------------

def section(title: str, lead: str, body: str) -> str:
    return f'<section><h2>{esc(title)}</h2><p class="lead">{lead}</p>{body}</section>'


def tile(label: str, value: str, note: str = "", css: str = "") -> str:
    return (f'<div class="tile"><div class="label">{esc(label)}</div>'
            f'<div class="value {css}">{value}</div><div class="note">{note}</div></div>')


def answer(metrics: dict) -> str:
    us = metrics["us_forecast"]
    tiles = "".join(
        tile(f"Corn for {name}, {metrics['forecast_year']}", f"{acres(us.get(name))}<span class='unit'>M acres</span>",
             f"80% interval {acres(us.get(f'{name}_lo80'))} to {acres(us.get(f'{name}_hi80'))}", name)
        for name in ("silage", "grain"))
    return section("The answer", f"US acres, November forecast. Built {esc(metrics['built_utc'])}.",
                   f'<div class="tiles two">{tiles}</div><p class="muted">'
                   'Silage is a historical acreage model. Grain uses NASS’s in-season forecast where available. '
                   'Satellite acreage improvement is unproven; the field test is separate evidence. '
                   f'Totals sum the states shown: {number(dig(metrics, "forecast_scope", "silage"), 0)} silage, '
                   f'{number(dig(metrics, "forecast_scope", "grain"), 0)} grain; missing states are excluded.</p>')


def states(forecast: pd.DataFrame, last_silage: pd.Series) -> str:
    rows = forecast[~forecast["state"].str.startswith("US")].sort_values("silage", ascending=False)
    if rows.empty:
        return section("States", "", f'<p class="muted">{DASH} no forecast file</p>')
    scale = rows["silage_hi80"].max()
    body = []
    for _, row in rows.iterrows():
        before = last_silage.get(row["state"])
        change = None if missing(before) or not before else (row["silage"] / before - 1) * 100
        body.append(
            f'<tr><th scope="row">{esc(row["state"].title())}</th>'
            f'<td class="num">{acres(row["silage"], 1e3, 0)}</td>'
            f'<td class="num muted">{acres(row["silage_lo80"], 1e3, 0)} to {acres(row["silage_hi80"], 1e3, 0)}</td>'
            f'<td>{range_bar(row["silage_lo80"], row["silage"], row["silage_hi80"], scale, "silage")}</td>'
            f'<td class="num">{DASH if change is None else f"{change:+.1f}%"}</td>'
            f'<td class="num">{acres(row["grain"], 1e3, 0)}</td></tr>')
    table = ('<div class="scroll" tabindex="0" role="region" aria-label="State acreage forecasts"><table><thead><tr><th scope="col">State</th><th scope="col" class="num">Silage</th>'
             '<th scope="col" class="num">80% interval</th><th scope="col">Interval</th>'
             '<th scope="col" class="num">vs last year</th><th scope="col" class="num">Grain</th></tr></thead>'
             f'<tbody>{"".join(body)}</tbody></table></div>')
    return section("States", f"Thousand acres, {len(rows)} states, largest silage first.", table)


def trust(metrics: dict, backtest: pd.DataFrame) -> str:
    charts = []
    if not backtest.empty:
        part = backtest[backtest["scope"] == "all_states"] if "scope" in backtest else backtest
        chosen = {"silage": dig(metrics, "state_model", "selected_silage_set"), "grain": "nass_latest"}
        for series, css in [("silage", "silage"), ("grain", "grain")]:
            wide = part[part["series"] == series].pivot(index="year", columns="predictor", values="state_error_pct")
            lines = [{"name": PREDICTOR_WORDS.get(name, name), "values": wide[name].tolist(), "css": style}
                     for name, style in [(chosen[series], css), ("same_as_last_year", "base")] if name in wide]
            charts.append(f'<figure><figcaption>{series.title()}: state acreage error</figcaption>'
                          f'{line_chart([str(y) for y in wide.index], lines, "% of acres")}</figure>')
    score = metrics["score_2025"]
    tiles = "".join([
        tile("Silage 2025, state error", number(dig(score, "silage", "model", "state_error_pct"), 1, "%"),
             f"Same as last year {number(dig(score, 'silage', 'same_as_last_year', 'state_error_pct'), 1, '%')}", "silage"),
        tile("Grain 2025, state error", number(dig(score, "grain", "model", "state_error_pct"), 1, "%"),
             f"Same as last year {number(dig(score, 'grain', 'same_as_last_year', 'state_error_pct'), 1, '%')}", "grain"),
        tile("Silage inside 80% interval", number(dig(score, "silage", "inside_80"), 2),
             f"Backtest {number(dig(metrics, 'state_model', 'interval_coverage', 'silage', '80'), 2)}; target 0.80"),
        tile("Grain inside 80% interval", number(dig(score, "grain", "inside_80"), 2),
             f"Backtest {number(dig(metrics, 'state_model', 'interval_coverage', 'grain', '80'), 2)}; target 0.80"),
    ])
    us_error = ('<p class="muted">2025 US silage total error (signed): '
                f'{number(dig(score, "silage", "model", "total_error_pct"), 2, "%")} for Kernel; '
                f'{number(dig(score, "silage", "same_as_last_year", "total_error_pct"), 2, "%")} for last year. '
                'State error is summed absolute state acreage error / summed actual acreage; '
                'it does not identify which individual acres were misclassified. '
                'Backtest years also select the feature set. Backtest interval coverage uses '
                'leave-one-year-out calibration with other years, including later years; '
                'it is not historical operational coverage.</p>')
    years = dig(metrics, "state_model", "backtest_years") or []
    span = f"{years[0]} to {years[-1]}" if years else DASH
    return section("Can you trust it", f"Each year {span} forecast from earlier years only. 2025 was held out and scored once.",
                   f'<div class="charts">{"".join(charts)}</div><div class="tiles four">{tiles}</div>{us_error}')


def bias(table: pd.DataFrame) -> str:
    if table.empty:
        return section("Bias", "", f'<p class="muted">{DASH} not computed</p>')
    table = table[table["by"] != "year"]
    scale = table["signed_error_pct"].abs().max()
    blocks = []
    for (series, by), part in table.groupby(["series", "by"], sort=False):
        rows = "".join(
            f'<tr><th scope="row">{esc(str(r["group"]).replace("_", " "))}</th><td class="num muted">{int(r["n"])}</td>'
            f'<td>{signed_bar(r["signed_error_pct"], scale)}</td><td class="num">{r["signed_error_pct"]:+.1f}%</td></tr>'
            for _, r in part.iterrows())
        blocks.append(f'<figure><figcaption>{esc(series.title())} by {esc(by.replace("_", " "))}</figcaption>'
                      f'<table class="compact"><thead><tr><th scope="col">Group</th><th scope="col" class="num">n</th>'
                      f'<th scope="col">Under / over</th><th scope="col" class="num">Signed error</th></tr></thead>'
                      f'<tbody>{rows}</tbody></table></figure>')
    return section("Bias", "Signed error of the backtest totals. Left of the line is too low, right is too high.",
                   f'<div class="charts">{"".join(blocks)}</div>')


def earliness(metrics: dict, by_date: pd.DataFrame) -> str:
    chart = f'<p class="muted">{DASH} not computed</p>'
    if not by_date.empty:
        labels = [datetime.strptime(d, "%m-%d").strftime("%-d %b") for d in by_date["asof"]]
        lines = [{"name": "Recall", "values": (by_date["silage_recall"] * 100).tolist(), "css": "silage"},
                 {"name": "Precision", "values": (by_date["silage_precision"] * 100).tolist(), "css": "grain"},
                 {"name": "False pos.", "values": (by_date["false_positive_rate"] * 100).tolist(), "css": "base"},
                 {"name": "Coverage", "values": (by_date["assessable_share"] * 100).tolist(), "css": "base"}]
        chart = (f'<figure><figcaption>Field calls by as-of date, Maryland test fields</figcaption>'
                 f'{line_chart(labels, lines, "%", y_max=100)}</figure>')

    def error(tree: str, key: str):
        chosen = dig(metrics, tree, "selected_silage_set") if key == "silage" else "nass_latest"
        return dig(metrics, tree, "mean_errors_pct", f"{key}.{chosen}", "state_error_pct")

    tiles = "".join([
        tile("Silage, as of 15 Sep", number(error("state_model_asof_sep", "silage"), 1, "%"),
             f"15 Nov {number(error('state_model', 'silage'), 1, '%')}", "silage"),
        tile("Grain, as of 15 Sep", number(error("state_model_asof_sep", "grain"), 1, "%"),
             f"15 Nov {number(error('state_model', 'grain'), 1, '%')}", "grain"),
    ])
    return section("How early", "State error when the forecast is made two months sooner, and what the field model sees by date.",
                   f'<div class="tiles two">{tiles}</div><div class="charts one">{chart}</div>'
                   '<p class="muted">Coverage means features are computable, not that harvest is confirmed. '
                   'Unassessable fields count as grain for scoring only. Early drops and calls can change '
                   'with later imagery; rates use the complete labeled test roster.</p>')


def field_signal(metrics: dict, curves: pd.DataFrame, weights: pd.DataFrame) -> str:
    field = metrics["field_eval"]

    def rate(key: str) -> str:
        return number(dig(field, "rates", key), 2)

    def interval(key: str) -> str:
        low, high = dig(field, "intervals_90", key) or (None, None)
        return f"90% interval {number(low, 2)} to {number(high, 2)}"

    tiles = "".join([
        tile("Silage precision", rate("silage_precision"), interval("silage_precision"), "silage"),
        tile("Silage recall", rate("silage_recall"), interval("silage_recall"), "silage"),
        tile("False positive rate", rate("false_positive_rate"), interval("false_positive_rate")),
        tile("Response time", f"{number(dig(field, 'response_seconds_per_field'), 3)}<span class='unit'>s per field</span>",
             "Features and call; download excluded"),
    ])
    rows = "".join(
        f'<tr><th scope="row">{esc(FEATURE_WORDS.get(r["feature"], r["feature"]))}</th>'
        f'<td>{signed_bar(r["weight_per_std"], weights["weight_per_std"].abs().max())}</td>'
        f'<td class="num">{r["weight_per_std"]:+.2f}</td></tr>' for _, r in weights.iterrows())
    evidence = ('<figure><figcaption>Evidence weights (right means silage)</figcaption><table class="compact"><thead><tr>'
                '<th scope="col">Evidence</th><th scope="col">Weight</th><th scope="col" class="num">Per std</th></tr></thead>'
                f'<tbody>{rows}</tbody></table></figure>') if len(weights) else ""
    lead = (f"Trained on {number(dig(field, 'train', 'field_years'), 0)} Quebec parcels, tested on "
            f"{number(dig(field, 'test', 'field_years'), 0)} Maryland field-years it never saw "
            f"({number(dig(field, 'test', 'silage'), 0)} silage). "
            f"{number(dig(field, 'test', 'unique_fields'), 0)} distinct fields; intervals resample whole fields. "
            "Silage is cut green and wet; grain fades first.")
    return section("The field signal", lead,
                   f'<div class="charts"><figure><figcaption>Greenness through the season, Maryland</figcaption>'
                   f'{curves_chart(curves)}</figure>{evidence}</div><div class="tiles four">{tiles}</div>')


def limits(metrics: dict) -> str:
    caveats = (dig(metrics, "state_model", "caveats") or []) + (dig(metrics, "field_eval", "caveats") or [])
    sampled = dig(metrics, "state_model", "sampled_states_silage_errors_pct") or {}
    satellite = (f"Satellite change, sampled states: {number(sampled.get('reversion_plus_satellite'), 1, '%')} "
                 f"against {number(sampled.get('same_as_last_year'), 1, '%')} for same as last year.")
    fixed = ["Truth is state totals only; field rates come from proxy labels.",
             "Field labels cover one Maryland farm and one Quebec year.",
             "Harvest calendars and soil colour differ by region; evidence is relative to each field's own season.",
             "Satellite backtests with a fixed Quebec classifier are retrospective; the classifier may use later training labels.",
             satellite]
    items = "".join(f"<li>{esc(text)}</li>" for text in fixed + [c[0].upper() + c[1:] + "." for c in caveats])
    return section("Limits", "What the numbers do not show.", f"<ul>{items}</ul>")


# --- page ----------------------------------------------------------------------------------------

STYLE = """
:root{--bg:#0e1113;--surface:#15191c;--line:#272d32;--text:#e7e9eb;--muted:#9aa4ac;--silage:#5cc8a9;
--grain:#e3b556;--base:#8a949c;--focus:#8ab4ff;--sans:"IBM Plex Sans",system-ui,sans-serif;
--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}
*{box-sizing:border-box}html{color-scheme:dark}
body{margin:0;background:var(--bg);color:var(--text);font:400 15px/1.5 var(--sans)}
main{max-width:1040px;margin:0 auto;padding:32px 16px 64px}
header{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid var(--line);padding-bottom:16px}
h1{font:600 20px/1.2 var(--sans);margin:0}h2{font:600 20px/1.2 var(--sans);margin:0 0 4px}
header p,.lead,.muted,.note,.label,figcaption{color:var(--muted)}header p{margin:0;font-size:13px}
a{color:var(--silage)}
section{padding:32px 0;border-bottom:1px solid var(--line)}.lead{margin:0 0 16px;font-size:13px;max-width:72ch}
.tiles{display:grid;gap:8px}.tiles.two{grid-template-columns:repeat(2,1fr)}.tiles.four{grid-template-columns:repeat(4,1fr)}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:16px}
.label,.note,figcaption{font-size:12px}.value{font:500 28px/1.3 var(--mono);font-variant-numeric:tabular-nums}
.value.silage,.end.silage{color:var(--silage)}.value.grain,.end.grain{color:var(--grain)}
.unit{font:400 13px var(--sans);color:var(--muted);margin-left:6px}
.charts{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-bottom:16px}.charts.one{grid-template-columns:minmax(0,680px);margin-top:16px}
figure{margin:0;background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:16px;min-width:0}
figcaption{margin-bottom:8px}svg{display:block;width:100%;height:auto}svg.bar{width:180px;height:14px}
.grid{stroke:var(--line);stroke-width:1}.zero{stroke:var(--muted);stroke-width:1}
.tick{fill:var(--muted);font:12px var(--mono)}.end{font:12px var(--mono);fill:var(--base)}
.end.silage{fill:var(--silage)}.end.grain{fill:var(--grain)}
.line{fill:none;stroke-width:2;stroke:var(--base)}.line.silage{stroke:var(--silage)}.line.grain{stroke:var(--grain)}
.line.base{stroke-dasharray:4 4}.line.thin{stroke-width:1;opacity:.75}.line.grain.thin{stroke-dasharray:3 3}
.dot{fill:var(--base)}.dot.silage{fill:var(--silage)}.dot.grain{fill:var(--grain)}
.whisker{stroke-width:3;stroke:var(--base);opacity:.55}.whisker.silage{stroke:var(--silage)}.signed{fill:var(--base)}
.scroll{max-height:440px;overflow:auto;scrollbar-color:var(--line) var(--surface);border:1px solid var(--line);border-radius:6px}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:8px 12px;text-align:left;border-bottom:1px solid var(--line)}
thead th{position:sticky;top:0;background:var(--surface);color:var(--muted);font-weight:500;font-size:12px}
tbody th{font-weight:400}.num{font-family:var(--mono);font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
table.compact th,table.compact td{padding:4px 8px}ul{margin:0;padding-left:20px;max-width:80ch}li{margin:4px 0}
:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
@media (max-width:760px){.tiles.two,.tiles.four,.charts{grid-template-columns:1fr}.value{font-size:20px}}
"""


def render(metrics: dict, tables: dict) -> str:
    sections = [
        answer(metrics),
        states(tables["forecast"], tables["last_silage"]),
        trust(metrics, tables["backtest"]),
        bias(tables["bias"]),
        earliness(metrics, tables["earliness"]),
        field_signal(metrics, tables["curves"], tables["weights"]),
        limits(metrics),
    ]
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>Kernel</title>'
            f'<style>{STYLE}</style></head><body><main><header><h1>Kernel</h1>'
            f'<p>Corn for silage or grain, by state, before January</p></header>'
            f'<p><a href="fields.html">Explore real field evidence</a></p>{"".join(sections)}</main></body></html>')


def maryland_curves(data: Path) -> pd.DataFrame:
    """Clear looks of the labeled Maryland fields: field_id, year, label, doy, ndvi."""
    labels_file, series_folder = data / "labels" / "barc_2021_2023.parquet", data / "s2_series" / "barc_2021_2023"
    if not labels_file.exists() or not series_folder.exists():
        return pd.DataFrame()
    labels = pd.read_parquet(labels_file, columns=["field_id", "year", "label"])
    labels["field_id"] = labels["field_id"].astype(str)
    series = load_series(series_folder)
    series = series[series["valid_frac"] >= 0.5].merge(labels, on=["field_id", "year"])
    return series.assign(doy=series["date"].dt.day_of_year)[["field_id", "year", "label", "doy", "ndvi"]]


def presentation_notes(metrics: dict) -> str:
    """A five-minute talk track, regenerated from the same metrics as the page."""
    us = metrics["us_forecast"]
    selected = dig(metrics, "state_model", "selected_silage_set")
    errors = dig(metrics, "state_model", "mean_errors_pct") or {}
    state = errors.get(f"silage.{selected}", {})
    baseline = errors.get("silage.same_as_last_year", {})
    field = metrics["field_eval"]
    score = metrics["score_2025"]
    return f'''# Kernel: five-minute presentation

Generated from `data/models/metrics.json` at {metrics["built_utc"]}. Open `report/index.html` offline.
The talk follows the seven sections from top to bottom. Acreage error is WAPE unless stated otherwise.

## 0:00–0:40 — The answer (mission)

USDA needs corn acreage by harvest use before January. Silage is cut green and wet; grain usually dries first.
Kernel combines a state acreage forecast with a separate satellite test of that physical signal.
Our November forecast is {acres(us.get("silage"))} million silage acres, with an 80% interval of
{acres(us.get("silage_lo80"))} to {acres(us.get("silage_hi80"))} million.
Grain is {acres(us.get("grain"))} million acres, primarily NASS's own in-season figures.
These totals sum the states shown; missing grain states are excluded.

## 0:40–1:05 — States (usefulness)

Scroll the state table. Each silage forecast has an interval and change from last year.
The state model uses public acreage history and tests additional season context against persistence.
The selected model is `{selected}`; it adjusts unusual prior-year silage acreage toward its historical level.
Do not present the satellite classifier as the source of these acreage totals.

## 1:05–2:00 — Can you trust it (technical quality)

We predict each historical year using earlier outcomes, then select the feature set on the historical validation years.
Mean silage state error is {number(state.get("state_error_pct"), 2)}%, versus
{number(baseline.get("state_error_pct"), 2)}% when copying last year.
The separate 2025 score is {number(dig(score, "silage", "model", "state_error_pct"), 2)}%, versus
{number(dig(score, "silage", "same_as_last_year", "state_error_pct"), 2)}% for persistence.
For the 2025 national total, signed error is {number(dig(score, "silage", "model", "total_error_pct"), 2)}%, versus
{number(dig(score, "silage", "same_as_last_year", "total_error_pct"), 2)}%.
That is a modest validation gain and no held-out silage win. We do not claim otherwise.
The grain advantage comes largely from NASS inputs, not a new satellite discovery.

## 2:00–2:30 — Bias (technical maturity)

Show the signed regional errors: positive means too many predicted acres, negative too few.
State WAPE sums absolute state acreage errors and divides by actual acres; it does not locate individual errors.
Intervals use historical residuals. Historical coverage uses leave-one-year-out calibration,
including later years, so it is a retrospective check rather than operational historical coverage.

## 2:30–3:05 — How early (innovation)

Show the September state comparison and the field earliness curve.
The imagery is truncated before recomputing features; no later scene enters an early call.
Coverage means features can be computed, not confirmed harvest. Unassessable fields count as grain
for scoring only, and provisional calls can change as more imagery arrives.
An early state replay requires its own dated satellite aggregate; it cannot reuse the November file.

## 3:05–4:10 — The field signal (innovation and evidence)

The six features describe drop size, speed, fade time, greenness and moisture before the cut, and residue after it.
We fit on {number(dig(field, "train", "field_years"), 0)} Quebec parcels and test on
{number(dig(field, "test", "field_years"), 0)} Maryland research-farm field-years from
{number(dig(field, "test", "unique_fields"), 0)} distinct fields. These are proxy labels, not nationwide validation.
Silage precision is {number(dig(field, "rates", "silage_precision"), 3)}, recall
{number(dig(field, "rates", "silage_recall"), 3)}, false positive rate
{number(dig(field, "rates", "false_positive_rate"), 3)}. The confusion matrix is
TP={dig(field, "rates", "TP")}, FP={dig(field, "rates", "FP")}, FN={dig(field, "rates", "FN")}, TN={dig(field, "rates", "TN")}.
Confidence intervals resample whole fields, keeping their repeated years together.
Feature extraction plus prediction takes {number(field.get("response_seconds_per_field"), 4)} seconds per field
on this machine; imagery downloading is excluded.

## 4:10–5:00 — Limits and next steps (feasibility)

One farm and one Quebec training year cannot establish national performance. Weather, cloud cover,
soil and harvest systems vary. A false positive rate that looks small can overwhelm a rare silage class,
so we do not sum field calls into acres.
The next test is whether paired satellite share changes on the same sampled areas improve state forecasts,
under the existing selection rule and with sampled-state results shown separately.
If the data are missing or the test loses, keep the historical forecast and report that result.
The contribution is a reproducible harvest-evidence test, a usable acreage report, and explicit uncertainty.

## Likely USDA questions

- **Does this beat last year?** Slightly on historical silage validation; not on the separate 2025 score.
- **Is grain independent of NASS?** No. NASS's in-season forecast is the principal grain input.
- **Are these national field accuracy numbers?** No. They are a transfer test on one Maryland research farm.
- **Can I add field probabilities to get acres?** No. Sampling, class prevalence and classifier error require correction.
- **Was 2025 used to tune the model?** The stored 2025 score was generated separately; do not tune on it or overwrite it.
- **Are early results guaranteed to hold?** No. The cutoff is enforced, but noisy partial-season evidence can change.
- **What is still unproven?** Satellite-driven improvement in state acreage error and transfer to other US regions.
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(REPO / "report" / "index.html"))
    parser.add_argument("--notes", default=str(REPO / "DOCS" / "presentation.md"))
    args = parser.parse_args()
    data = data_dir()
    models = data / "models"

    metrics = gather(models)
    metrics_file = models / "metrics.json"
    metrics_file.write_text(json.dumps(metrics, indent=1) + "\n", encoding="utf-8")
    record_in_manifest(metrics_file, "derived: kernelag.report")

    panel = read_csv(data / "panel" / "state_year.csv")
    last = panel[panel["year"] == FORECAST_YEAR - 1].set_index("state")["silage"] if len(panel) else pd.Series(dtype=float)
    forecast = read_csv(models / f"state_forecast_{FORECAST_YEAR}.csv")
    tables = {
        "forecast": forecast if len(forecast) else pd.DataFrame(columns=["state", "silage"]),
        "last_silage": last,
        "backtest": read_csv(models / "state_model_backtest.csv"),
        "bias": read_csv(models / "state_model_bias.csv"),
        "earliness": read_csv(models / "field_earliness.csv"),
        "weights": read_csv(models / "field_model_coefficients.csv"),
        "curves": maryland_curves(data),
    }
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(metrics, tables), encoding="utf-8")
    notes = Path(args.notes)
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text(presentation_notes(metrics), encoding="utf-8")
    print(f"metrics -> {metrics_file}\nreport  -> {target} ({target.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
