"""
Slide figure: the satellite pictures Nemotron labeled, with its label and the measured greenness under each.

Reads the cached chips and answers from vlm_caveman.py (no API calls) and writes:
  figures/nemotron_vs_greenness.png      silage field 280 vs grain field 334 (2021), Aug-Oct
  figures/nemotron_input_<field>_<year>.png   the exact sheets sent to Nemotron

Run: uv run make_nemotron_figure.py
"""

import json
import shutil
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

import prepare as P
import vlm_caveman as V

FIG = Path(__file__).resolve().parent / "figures"
MODEL = "nemotron-3.5-super-vl-120b-a12b"
ROWS = [  # field, year, class, (cut start, cut end) from the greenness line
    (280, 2021, "SILAGE", ("2021-09-03", "2021-09-14")),
    (334, 2021, "GRAIN", ("2021-08-28", "2021-09-24")),
]
WINDOW = ("08-01", "10-20")
BG, FG, MUTED = (43, 29, 20), (240, 230, 214), (170, 155, 135)
COL = {0: (120, 120, 120), 1: (92, 191, 122), 2: (232, 120, 70)}
NAME = {0: "no crop", 1: "standing", 2: "harvested"}
CHIP = 150


def font(size, bold=False):
    for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
              "/Library/Fonts/Arial.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main():
    FIG.mkdir(exist_ok=True)
    ts, _ = P.load_data()
    panels = []
    for oid, yr, cls, (c0, c1) in ROWS:
        shutil.copy(V.STRIPS / f"{oid}_{yr}.png", FIG / f"nemotron_input_{oid}_{yr}.png")
        ans = pd.DataFrame(json.loads((V.ANSWERS / f"{oid}_{yr}__{MODEL}.json").read_text()))
        ans["date"] = pd.to_datetime(ans["date"])
        ans = ans[ans["date"].between(f"{yr}-{WINDOW[0]}", f"{yr}-{WINDOW[1]}")]
        g = ts[(ts["OBJECTID"] == oid) & (ts["year"] == yr)].set_index("date")["ndvi"]
        panels.append((oid, yr, cls, pd.Timestamp(c0), pd.Timestamp(c1), ans, g))

    ncol = max(len(p[5]) for p in panels)
    pad, head, foot = 14, 84, 70
    W = pad + ncol * (CHIP + pad) + 10
    H = 120 + len(panels) * (head + CHIP + foot + 30) + 70
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((pad, 20), "What Nemotron saw: free 10 m satellite pictures, one corn field outlined in yellow", fill=FG, font=font(30, True))
    d.text((pad, 62), "Border = Nemotron's label.  Number under each picture = measured greenness (NDVI).  Bracket = when greenness actually collapsed.",
           fill=MUTED, font=font(19))
    y = 120
    for oid, yr, cls, c0, c1, ans, g in panels:
        d.text((pad, y), f"{cls} · USDA Beltsville field {oid} · {yr}", fill=FG, font=font(24, True))
        xs = {}
        for i, (dt_, lab) in enumerate(zip(ans["date"], ans["label"])):
            x = pad + i * (CHIP + pad)
            xs[dt_] = x
            chip = Image.open(V.CHIPS / f"{oid}_{dt_:%Y-%m-%d}.png").resize((CHIP, CHIP), Image.NEAREST)
            yy = y + head
            d.rectangle([x - 5, yy - 5, x + CHIP + 4, yy + CHIP + 4], fill=COL[int(lab)])
            img.paste(chip, (x, yy))
            d.text((x, yy + CHIP + 10), f"{dt_:%b %d}", fill=FG, font=font(19, True))
            nd = g.get(dt_)
            d.text((x, yy + CHIP + 34), f"{NAME[int(lab)]} · {nd:.2f}" if nd is not None else NAME[int(lab)], fill=COL[int(lab)], font=font(17))
        inside = [x for t, x in xs.items() if c0 - pd.Timedelta(days=3) <= t <= c1 + pd.Timedelta(days=3)]
        if inside:
            bx0, bx1, by = min(inside) - 5, max(inside) + CHIP + 5, y + head - 14
            d.line([bx0, by + 8, bx0, by, bx1, by, bx1, by + 8], fill=(242, 196, 48), width=4)
            d.text((bx0 + 6, by - 26), f"greenness collapsed: {(c1 - c0).days} days", fill=(242, 196, 48), font=font(18, True))
        y += head + CHIP + foot + 30
    lx = pad
    for k in (1, 2):
        d.rectangle([lx, y + 6, lx + 22, y + 28], fill=COL[k])
        d.text((lx + 30, y + 4), f"Nemotron: {NAME[k]}", fill=FG, font=font(19))
        lx += 260
    d.text((lx, y + 4), "Silage was cut in early September; Nemotron still saw a standing crop until late September.", fill=MUTED, font=font(19))
    out = FIG / "nemotron_vs_greenness.png"
    img.save(out)
    print(out, img.size)


if __name__ == "__main__":
    main()
