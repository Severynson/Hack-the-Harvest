"""Harvest evidence for one field-season, read from its Sentinel-2 series.

Ported unchanged in logic from the team notebook ``Kernel/kernel_barc_silage_grain.ipynb``
so that Maryland test fields and training parcels get identical features.

Input: one field-year with columns ``date, ndvi, ndmi, ndti, valid_frac``.
Output features:
    cut_doy          day of year of the first clear look after the biggest greenness drop
    cut_gap_days     days between the last look before the drop and the first after (date uncertainty)
    max_drop         size of that drop in NDVI
    green_at_cut     NDVI just before the drop, as a share of the season peak
    ndmi_before_cut  canopy moisture index just before the drop
    drydown_days     days from first browning (below 90% of peak) to the cut
    fade_days        days from the last clearly green look to the first clearly bare look
    ndti_post        residue index on the first bare looks after the cut
    ndvi_nov         November greenness (regrowth or cover crop)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def drop_dips(s: pd.DataFrame, recover: float = 0.15, within_days: int = 20, max_doy: int = 300) -> pd.DataFrame:
    """Remove cloud and haze dips: a value that bounces back by ``recover`` within ``within_days``.

    Corn cannot regrow that fast after a real cut, so a quick rebound means the low value was noise.
    """
    v, d = s["ndvi"].to_numpy(), s["doy"].to_numpy()
    keep = np.ones(len(s), bool)
    for i in range(len(s)):
        if d[i] > max_doy:
            continue
        later = (d > d[i]) & (d - d[i] <= within_days)
        if later.any() and v[later].max() > v[i] + recover:
            keep[i] = False
    return s[keep].reset_index(drop=True)


def kernel_features(series: pd.DataFrame, min_valid: float = 0.5, bare_ndvi: float = 0.35,
                    season_end_doy: int = 300) -> dict:
    """Features for one field-year. Missing evidence stays missing (NaN or absent), never guessed."""
    s = series[(series["valid_frac"] >= min_valid) & series["ndvi"].notna()].sort_values("date")
    s = s.assign(doy=s["date"].dt.day_of_year.astype(int)).reset_index(drop=True)
    s = drop_dips(s)
    f: dict = {"n_obs": len(s)}
    if len(s) < 4:
        return f
    f["ndvi_nov"] = float(s.loc[s["doy"] >= 305, "ndvi"].median()) if (s["doy"] >= 305).any() else np.nan

    window = s[(s["doy"] >= 150) & (s["doy"] <= 260)]  # June to mid-September
    if window.empty:
        return f
    ip = int(window["ndvi"].idxmax())
    peak = float(s.loc[ip, "ndvi"])
    f.update(peak_ndvi=peak, peak_doy=int(s.loc[ip, "doy"]))
    # Season after the peak, ending before late-fall cover crops or regrowth confuse things.
    after = s.loc[ip:][lambda d: d["doy"] <= season_end_doy].reset_index(drop=True)
    if len(after) < 2:
        return f

    # Organizers' baseline: first date of a sustained decline (below the halfway point, and stays there).
    floor = float(after["ndvi"].min())
    half = floor + 0.5 * (peak - floor)
    below = (after["ndvi"] < half).to_numpy()
    for i in range(1, len(after)):
        if below[i] and (i == len(after) - 1 or below[i + 1]):
            f["decline_doy"] = int(after.loc[i, "doy"])
            break

    # Fade time: last clearly green look (>= 0.6) to first clearly brown or bare look (<= 0.4).
    green = after[after["ndvi"] >= 0.6]
    if len(green):
        g_doy = int(green["doy"].iloc[-1])
        brown = after[(after["doy"] > g_doy) & (after["ndvi"] <= 0.4)]
        f["fade_days"] = int(brown["doy"].iloc[0] - g_doy) if len(brown) else np.nan

    # Biggest single drop between consecutive clear looks = most likely cut.
    d_ndvi = after["ndvi"].diff().to_numpy()[1:] * -1
    d_days = after["doy"].diff().to_numpy()[1:]
    k = int(np.nanargmax(d_ndvi)) + 1  # index of the first look after the drop
    f.update(
        cut_doy=int(after.loc[k, "doy"]),
        cut_gap_days=int(d_days[k - 1]),
        max_drop=float(d_ndvi[k - 1]),
        max_drop_rate=float(d_ndvi[k - 1] / max(d_days[k - 1], 1)),
        green_at_cut=float(after.loc[k - 1, "ndvi"] / peak) if peak > 0 else np.nan,
        ndmi_before_cut=float(after.loc[k - 1, "ndmi"]),
    )

    browning = after[(after.index < k) & (after["ndvi"] < 0.9 * peak)]
    f["drydown_days"] = int(f["cut_doy"] - browning["doy"].iloc[0]) if len(browning) else 0

    # Surface after the cut: the earliest up-to-3 clear looks once the field is no longer green.
    post = after.loc[k:]
    post = post[post["ndvi"] < bare_ndvi].head(3)
    f["ndti_post"] = float(post["ndti"].median()) if len(post) else np.nan
    return f


def build_features(ts: pd.DataFrame, min_valid: float = 0.5) -> pd.DataFrame:
    """One row of features per ``field_id`` and ``year`` in a long per-date table."""
    rows = [
        {"field_id": field_id, "year": year, **kernel_features(group, min_valid)}
        for (field_id, year), group in ts.groupby(["field_id", "year"])
    ]
    return pd.DataFrame(rows)
