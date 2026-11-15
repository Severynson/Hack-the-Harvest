"""Exploration (not part of the clean pipeline): the year effect in the field model.

What prompted it: with Quebec years held out in turn, the share of fields called silage swings
from 32% (2022) to 65% (2023) while the true share stays at 54-58%. The state signal uses the
CHANGE in that share between years, so the swing drowns the real change.

Every number below comes from a year the model never saw (fitted on the other years):
    accuracy     on the natural Quebec mix (about 55% silage)
    share@15     predicted silage share when the year is thinned to 15% silage, one value per year.
                 The truth is 15% every year, so the spread across years is pure year noise.
    spread       standard deviation of share@15 across the years
    slope        how far the predicted share moves per unit of true share (15% -> 30%)
    noise        spread / slope: the year noise in units of true share. Smaller is better; the real
                 year-to-year change in a state's silage share is only a few points.
    maryland     the 44 Maryland field-years, model fitted on all Quebec years (test only)

Variants:
    absolute        the current six features
    plus_timing     plus days from the field's own season peak to its cut
    area_relative   every feature minus the median of its area and year (neighbours as yardstick)
    year_relative   every feature minus the median of its year
    area_grain_side every feature minus the grain-side quartile of its area and year. A median moves
    year_grain_side with the silage share itself; the quartile on the grain side moves much less.
    trees           the plus_timing features in boosted trees instead of the logistic model

Run where the series are: ``python test_models/varunModel/year_effect.py``
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from kernelag.field_model import DECISION_THRESHOLD, MODEL_FEATURES, evidence_table, load_series, make_model
from kernelag.paths import data_dir

TIMING = MODEL_FEATURES + ["peak_to_cut"]
MIXES = (0.15, 0.30)     # silage shares the held-out year is thinned to
SEEDS = range(5)         # random thinnings averaged per year
MIN_GROUP = 8            # fewer fields than this in an area-year: use the year's median instead
CACHE = data_dir() / "models" / "explore_quebec_evidence.csv"


def tree_model():
    from sklearn.ensemble import HistGradientBoostingClassifier

    return HistGradientBoostingClassifier(max_depth=3, max_iter=150, learning_rate=0.05, class_weight="balanced")


MEDIAN = dict.fromkeys(TIMING, 0.5)
# The quartile on the grain side of each feature: low where silage runs high, high where it runs low.
GRAIN_SIDE = {"max_drop": 0.25, "max_drop_rate": 0.25, "green_at_cut": 0.25, "ndmi_before_cut": 0.25,
              "fade_days": 0.75, "ndti_post": 0.75, "peak_to_cut": 0.75}

# name: (features, group columns or None, quantile subtracted per feature, model factory)
VARIANTS = {
    "absolute": (MODEL_FEATURES, None, None, make_model),
    "plus_timing": (TIMING, None, None, make_model),
    "area_relative": (TIMING, ["cell", "year"], MEDIAN, make_model),
    "year_relative": (TIMING, ["year"], MEDIAN, make_model),
    "area_grain_side": (TIMING, ["cell", "year"], GRAIN_SIDE, make_model),
    "year_grain_side": (TIMING, ["year"], GRAIN_SIDE, make_model),
    "trees": (TIMING, None, None, tree_model),
}


def with_timing(table: pd.DataFrame) -> pd.DataFrame:
    return table.assign(peak_to_cut=table["cut_doy"] - table["peak_doy"])


def quebec_evidence() -> pd.DataFrame:
    """Features and labels for every Quebec parcel with a series, tagged with its 10 km area."""
    if CACHE.exists():
        return pd.read_csv(CACHE, dtype={"field_id": str, "cell": str})
    data, tables = data_dir(), []
    for labels_file in sorted((data / "labels").glob("quebec_maize_*.parquet")):
        series_dir = data / "s2_series" / labels_file.stem
        if not series_dir.is_dir():
            continue
        cell_of = {}
        for part in series_dir.glob("*.csv"):   # files are named <area>_<year>.csv
            ids = pd.read_csv(part, usecols=["field_id"])["field_id"].astype(str).unique()
            cell_of.update(dict.fromkeys(ids, part.stem.rsplit("_", 1)[0]))
        labels = pd.read_parquet(labels_file, columns=["field_id", "year", "label"])
        table = evidence_table(labels, load_series(series_dir))
        table["cell"] = table["field_id"].map(cell_of)
        tables.append(table)
        print(f"features built for {labels_file.stem}: {len(table)} parcels", flush=True)
    table = pd.concat(tables, ignore_index=True)
    table.to_csv(CACHE, index=False, lineterminator="\n")
    return table


def maryland_evidence() -> pd.DataFrame:
    data = data_dir()
    labels = pd.read_parquet(data / "labels" / "barc_2021_2023.parquet", columns=["field_id", "year", "label"])
    table = evidence_table(labels, load_series(data / "s2_series" / "barc_2021_2023"))
    return table.assign(cell="barc")


def centred(table: pd.DataFrame, features: list[str], by: list[str] | None, quantile: dict | None) -> pd.DataFrame:
    """Each feature minus a quantile of its group; small groups use the same quantile of their year."""
    if by is None:
        return table
    big_enough = (table.groupby(by)["field_id"].transform("size") >= MIN_GROUP).to_numpy()
    out = table.copy()
    for feature in features:
        def reference(values: pd.Series, q: float = quantile[feature]) -> float:
            return values.quantile(q)

        of_group = table.groupby(by)[feature].transform(reference).to_numpy()
        of_year = table.groupby("year")[feature].transform(reference).to_numpy()
        out[feature] = table[feature].to_numpy() - np.where(big_enough, of_group, of_year)
    return out


def thinned(table: pd.DataFrame, mix: float, seed: int) -> pd.DataFrame:
    """All grain fields plus a random draw of silage fields so that silage is ``mix`` of the total."""
    grain, silage = table[table["is_silage"] == 0], table[table["is_silage"] == 1]
    wanted = min(len(silage), round(len(grain) * mix / (1 - mix)))
    return pd.concat([grain, silage.sample(wanted, random_state=seed)])


def predicted_share(model, table: pd.DataFrame, features: list[str], by, quantile) -> np.ndarray:
    """Probability of silage per field; its mean is the share the state signal would report."""
    return model.predict_proba(centred(table, features, by, quantile)[features])[:, 1]


def evaluate(train: pd.DataFrame, test: pd.DataFrame | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One summary row per variant, and the per-year shares behind it."""
    train = with_timing(train[train["assessable"]])
    years = sorted(train["year"].unique())
    summary, by_year = [], []
    for name, (features, by, quantile, factory) in VARIANTS.items():
        correct, shares = [], {mix: [] for mix in MIXES}
        for year in years:
            fit, held_out = train[train["year"] != year], train[train["year"] == year]
            model = factory().fit(centred(fit, features, by, quantile)[features], fit["is_silage"])
            probability = predicted_share(model, held_out, features, by, quantile)
            correct.append((probability >= DECISION_THRESHOLD) == held_out["is_silage"].to_numpy())
            for mix in MIXES:
                shares[mix].append(float(np.mean([
                    predicted_share(model, thinned(held_out, mix, seed), features, by, quantile).mean() for seed in SEEDS])))
            by_year.append({"variant": name, "year": int(year), "true_share": round(held_out["is_silage"].mean(), 3),
                            "predicted_share": round(float(probability.mean()), 3),
                            **{f"share@{int(mix * 100)}": round(shares[mix][-1], 3) for mix in MIXES}})
        low, high = (np.array(shares[mix]) for mix in MIXES)
        slope = float(((high - low) / (MIXES[1] - MIXES[0])).mean())
        spread = float(low.std(ddof=1)) if len(years) > 1 else float("nan")
        row = {"variant": name, "accuracy": round(float(np.concatenate(correct).mean()), 3),
               "spread": round(spread, 3), "slope": round(slope, 3),
               "noise": round(spread / slope, 3) if slope > 0 else float("nan")}
        if test is not None:
            # One farm, so every relative variant uses the farm's own fields in that year.
            by_test = ["year"] if by else None
            model = factory().fit(centred(train, features, by, quantile)[features], train["is_silage"])
            ok = with_timing(test[test["assessable"]])
            call = predicted_share(model, ok, features, by_test, quantile) >= DECISION_THRESHOLD
            truth = ok["is_silage"].to_numpy() == 1
            row.update(maryland=round(float((call == truth).mean()), 3), md_found=f"{int((call & truth).sum())}/{int(truth.sum())}",
                       md_false=f"{int((call & ~truth).sum())}/{int((~truth).sum())}")
        summary.append(row)
    return pd.DataFrame(summary), pd.DataFrame(by_year)


def main() -> None:
    pd.set_option("display.width", 200)
    train = quebec_evidence()
    summary, by_year = evaluate(train, maryland_evidence())
    print("\nmedian of each feature by year and class (drift between years is the year effect)")
    ok = with_timing(train[train["assessable"]])
    medians = ok.groupby(["label", "year"])[TIMING + ["cut_doy", "peak_doy"]].median().round(3)
    print(medians.to_string())
    print("\nheld-out year, per variant")
    print(by_year.to_string(index=False))
    print("\nsummary (noise = year spread in units of true silage share; smaller is better)")
    print(summary.to_string(index=False))
    out = data_dir() / "models"
    summary.to_csv(out / "explore_year_effect_summary.csv", index=False, lineterminator="\n")
    by_year.to_csv(out / "explore_year_effect_by_year.csv", index=False, lineterminator="\n")


if __name__ == "__main__":
    main()
