"""
VLM-powered caveman (idea: test_models/danielModel/README.md, "severynModel - VLM-powered caveman").

Instead of reading NDVI numbers, NVIDIA Nemotron looks at plain true-colour Sentinel-2 pictures of a field
and labels every date: 0 = no crop yet, 1 = crop standing (growing or drying), 2 = harvested.
The caveman rule then works on those labels: when was the field harvested, compared with the other
fields that year, and how abruptly did it go from standing crop to harvested.

Steps (each cached under ~/.cache/autoresearch-silage/vlm/):
  1. chips   one PNG per field and clear date (Jun-Nov), cut from the Sentinel-2 RGB bands
  2. strips  one dated contact sheet per field-year
  3. ask     one Nemotron call per field-year -> JSON labels
  4. score   leave-one-year-out on the 44 BARC field-years, same metric as prepare.evaluate

Run: NVIDIA_API_KEY=... uv run vlm_caveman.py [--model nvidia/nemotron-3.5-super-vl-120b-a12b]
The key is read from the environment only; it is never written to disk by this script.
"""

import argparse
import base64
import io
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import requests
from PIL import Image, ImageDraw, ImageFont

import prepare as P

OUT = P.CACHE_DIR / "vlm"
CHIPS, STRIPS, ANSWERS = OUT / "chips", OUT / "strips", OUT / "answers"
MONTHS = (6, 11)            # June-November: the corn season, no winter
MIN_CLEAR = 0.8             # a date is used for a field only if >= 80% of its pixels are clear
MAX_DATES = 20              # at most this many pictures per field-year (evenly thinned)
CHIP_PX = 120
MARGIN_M = 40
API = "https://integrate.api.nvidia.com/v1/chat/completions"

PROMPT = """These are true-colour satellite pictures (Sentinel-2, 10 m pixels) of ONE corn field, outlined in yellow, on the dates written above each picture, in time order.
Label every date with exactly one number:
0 = no crop yet: bare soil or old stubble before the corn has emerged
1 = crop standing in the field: green growing corn, OR mature yellow/brown corn still standing
2 = harvested: the crop is gone; bare soil, short stubble or new low regrowth after harvest
Judge only the area inside the yellow outline. Once a field is harvested it stays harvested.
Answer with JSON only, no other text: [{"date": "YYYY-MM-DD", "label": 0}, ...] with one entry per picture."""


# ---------------------------------------------------------------------------
# 1. chips
# ---------------------------------------------------------------------------


def wanted_dates(labels):
    rows = []
    for f in sorted(P.SCENE_DIR.glob("*.parquet")):
        d = pd.read_parquet(f, columns=["OBJECTID", "date", "valid_frac", "scene"])
        rows.append(d)
    s = pd.concat(rows)
    s["date"] = pd.to_datetime(s["date"])
    s["year"] = s["date"].dt.year
    s = s[s["date"].dt.month.between(*MONTHS) & (s["valid_frac"] >= MIN_CLEAR)]
    s = s.merge(labels[["OBJECTID", "year"]], on=["OBJECTID", "year"])
    s = s.sort_values("date").drop_duplicates(["OBJECTID", "date"])
    keep = []
    for _, g in s.groupby(["OBJECTID", "year"]):
        idx = np.unique(np.linspace(0, len(g) - 1, min(MAX_DATES, len(g))).round().astype(int))
        keep.append(g.iloc[idx])
    return pd.concat(keep)


def _items(ids):
    import planetary_computer as pc
    import pystac_client

    cat = pystac_client.Client.open(P.STAC_URL, modifier=pc.sign_inplace)
    out = {}
    for i in range(0, len(ids), 50):
        for it in cat.search(collections=["sentinel-2-l2a"], ids=ids[i : i + 50]).items():
            out[it.id] = it
    return out


def _chip(rgb, transform, geom):
    from rasterio.transform import rowcol

    minx, miny, maxx, maxy = geom.buffer(MARGIN_M).bounds
    r0, c0 = rowcol(transform, minx, maxy)
    r1, c1 = rowcol(transform, maxx, miny)
    r0, c0 = max(r0, 0), max(c0, 0)
    sub = rgb[r0 : r1 + 1, c0 : c1 + 1]
    if sub.size == 0:
        return None
    img = Image.fromarray(sub).resize((CHIP_PX, CHIP_PX), Image.NEAREST)
    sx, sy = CHIP_PX / sub.shape[1], CHIP_PX / sub.shape[0]
    draw = ImageDraw.Draw(img)
    polys = getattr(geom, "geoms", [geom])
    for poly in polys:
        pts = []
        for x, y in poly.exterior.coords:
            r, c = rowcol(transform, x, y, op=float)
            pts.append(((c - c0) * sx, (r - r0) * sy))
        draw.line(pts + [pts[0]], fill=(255, 220, 0), width=2)
    return img


def make_chips(want, fields):
    import rasterio
    from rasterio.windows import from_bounds

    CHIPS.mkdir(parents=True, exist_ok=True)
    todo = want[[not (CHIPS / f"{o}_{d:%Y-%m-%d}.png").exists() for o, d in zip(want["OBJECTID"], want["date"])]]
    if todo.empty:
        return
    items = _items(sorted(todo["scene"].unique()))
    geoms = dict(zip(fields["OBJECTID"], fields.geometry))
    bounds = tuple(fields.total_bounds + np.array([-100, -100, 100, 100]))

    def one(scene, g):
        it = items[scene]
        pb = float(it.properties.get("s2:processing_baseline", "0"))
        off = 1000.0 if pb >= 4.0 else 0.0
        bands = []
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_TIMEOUT="60", GDAL_HTTP_MAX_RETRY="4"):
            for b in ("B04", "B03", "B02"):
                with rasterio.open(it.assets[b].href) as src:
                    win = from_bounds(*bounds, transform=src.transform).round_offsets().round_lengths()
                    bands.append(src.read(1, window=win).astype("float32"))
                    transform = src.window_transform(win)
        rgb = np.clip((np.dstack(bands) - off) / 10000.0 * 3.5, 0, 1)
        rgb = (rgb ** (1 / 1.4) * 255).astype("uint8")  # mild gamma so dark fields stay readable
        for oid, d in zip(g["OBJECTID"], g["date"]):
            img = _chip(rgb, transform, geoms[oid])
            if img is not None:
                img.save(CHIPS / f"{oid}_{d:%Y-%m-%d}.png")
        return len(g)

    done = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(one, s, g) for s, g in todo.groupby("scene")]
        for f in as_completed(futs):
            try:
                done += f.result()
            except Exception as e:
                print(f"  chip scene failed: {e}", file=sys.stderr)
    print(f"chips written: {done}", flush=True)


# ---------------------------------------------------------------------------
# 2. strips
# ---------------------------------------------------------------------------


def make_strip(oid, year, dates):
    STRIPS.mkdir(parents=True, exist_ok=True)
    path = STRIPS / f"{oid}_{year}.png"
    chips = [(d, CHIPS / f"{oid}_{d:%Y-%m-%d}.png") for d in dates]
    chips = [(d, p) for d, p in chips if p.exists()]
    cols, cap = 5, 18
    rows = -(-len(chips) // cols)
    sheet = Image.new("RGB", (cols * (CHIP_PX + 6), rows * (CHIP_PX + cap + 6)), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for i, (d, p) in enumerate(chips):
        x, y = (i % cols) * (CHIP_PX + 6), (i // cols) * (CHIP_PX + cap + 6)
        draw.text((x + 3, y + 2), f"{d:%Y-%m-%d}", fill=(255, 255, 255), font=font)
        sheet.paste(Image.open(p), (x, y + cap))
    sheet.save(path)
    return path, [d for d, _ in chips]


# ---------------------------------------------------------------------------
# 3. ask Nemotron
# ---------------------------------------------------------------------------


def ask(model, strip_path, dates, key):
    ANSWERS.mkdir(parents=True, exist_ok=True)
    out = ANSWERS / f"{strip_path.stem}__{model.split('/')[-1]}.json"
    if out.exists():
        return json.loads(out.read_text())
    b64 = base64.b64encode(strip_path.read_bytes()).decode()
    body = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT + "\nDates: " + ", ".join(f"{d:%Y-%m-%d}" for d in dates)},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]}],
        "temperature": 0.0,
        "max_tokens": 16000,
        "chat_template_kwargs": {"enable_thinking": False},  # labels only, no long hidden reasoning
    }
    for attempt in range(6):
        r = requests.post(API, headers={"Authorization": f"Bearer {key}", "Accept": "application/json"}, json=body, timeout=180)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(5 * (attempt + 1))
            continue
        r.raise_for_status()
        text = r.json()["choices"][0]["message"].get("content") or ""
        m = re.findall(r"\[\s*\{.*?\}\s*\]", text, re.S)
        if not m:
            raise ValueError(f"no JSON in answer: {text[:300]}")
        ans = json.loads(m[-1])
        out.write_text(json.dumps(ans))
        return ans
    raise RuntimeError("API kept failing")


# ---------------------------------------------------------------------------
# 4. caveman rules on the labels
# ---------------------------------------------------------------------------


def label_features(ans):
    a = pd.DataFrame(ans)
    a["date"] = pd.to_datetime(a["date"])
    a = a.sort_values("date")
    a["label"] = pd.to_numeric(a["label"], errors="coerce")
    grown = a[a["label"] == 1]
    if grown.empty:
        return {"harvest_doy": np.nan, "gap_days": np.nan}
    after = a[(a["date"] > grown["date"].iloc[0]) & (a["label"] == 2)]
    if after.empty:
        return {"harvest_doy": np.nan, "gap_days": np.nan}
    h = after["date"].iloc[0]
    last_standing = a[(a["date"] < h) & (a["label"] == 1)]["date"].iloc[-1]
    return {"harvest_doy": h.dayofyear, "gap_days": (h - last_standing).days, "last_standing_doy": last_standing.dayofyear}


def fit_cut(x, y):
    x = np.where(np.isfinite(x), x, np.inf)
    c = np.unique(x[np.isfinite(x)])
    c = np.concatenate([[-np.inf], (c[:-1] + c[1:]) / 2]) if len(c) > 1 else c
    f1 = lambda p: 2 * ((y == 1) & p).sum() / max(1, 2 * ((y == 1) & p).sum() + ((y == 0) & p).sum() + ((y == 1) & ~p).sum())
    s = np.array([f1(x < t) for t in c])
    return float(np.median(c[np.flatnonzero(s == s.max())]))


def loyo(feat, col):
    preds = []
    for yr in sorted(feat["year"].unique()):
        tr, te = feat[feat["year"] != yr], feat[feat["year"] == yr]
        t = fit_cut(tr[col].to_numpy(float), tr["y"].to_numpy())
        preds.append(te.assign(pred=np.where(np.isfinite(te[col]), te[col] < t, False).astype(int), cut=t))
    p = pd.concat(preds)
    return P._scores(p["y"].to_numpy(), p["pred"].to_numpy()), p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="nvidia/nemotron-3.5-super-vl-120b-a12b")
    args = ap.parse_args()
    key = os.environ.get("NVIDIA_API_KEY")
    if not key:
        raise SystemExit("set NVIDIA_API_KEY")

    _, labels = P.load_data()
    fields = P.load_fields()
    want = wanted_dates(labels)
    print(f"field-years: {want.groupby(['OBJECTID','year']).ngroups}, pictures: {len(want)}", flush=True)
    make_chips(want, fields)

    rows, fails = [], 0
    for (oid, yr), g in want.groupby(["OBJECTID", "year"]):
        strip, dates = make_strip(oid, yr, list(g["date"]))
        try:
            ans = ask(args.model, strip, dates, key)
        except Exception as e:
            fails += 1
            print(f"  {oid}/{yr} failed: {e}", file=sys.stderr, flush=True)
            continue
        rows.append({"OBJECTID": oid, "year": yr, "n_pictures": len(dates), **label_features(ans)})
        print(f"  {oid}/{yr}: {''.join(str(int(x['label'])) if str(x.get('label')).isdigit() else '?' for x in ans)}", flush=True)
    feat = pd.DataFrame(rows).merge(labels[["OBJECTID", "year", "y"]], on=["OBJECTID", "year"])
    feat["harvest_rel"] = feat["harvest_doy"] - feat.groupby("year")["harvest_doy"].transform("median")
    feat.to_parquet(OUT / f"features__{args.model.split('/')[-1]}.parquet")

    print(f"\nanswered {len(feat)} of 44 field-years ({fails} failed); harvest found for {feat['harvest_doy'].notna().sum()}")
    print("median by class:\n" + feat.groupby("y")[["harvest_doy", "harvest_rel", "gap_days", "n_pictures"]].median().rename(index={0: "grain", 1: "silage"}).to_string())
    for col in ["harvest_doy", "harvest_rel", "gap_days"]:
        s, p = loyo(feat, col)
        print(f"rule '{col} < cut' (BARC leave-one-year-out): F1 {s['silage_f1']:.3f}  acc {s['accuracy']:.3f}  "
              f"P {s['silage_precision']:.3f}  R {s['silage_recall']:.3f}  tp={s['tp']} fp={s['fp']} fn={s['fn']} tn={s['tn']}  cuts {sorted(p['cut'].unique().round(1))}")


if __name__ == "__main__":
    main()
