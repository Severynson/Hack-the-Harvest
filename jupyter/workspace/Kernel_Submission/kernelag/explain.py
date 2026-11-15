"""Harvest Story: a short plain-English explanation of each field call, written by Nemotron.

The numbers are never the model's. Python computes every fact (cut date, greenness at the cut,
moisture, residue, the probability, and how much each piece of evidence pushed the call); Nemotron
only turns those facts into two or three sentences for a statistician. Every number in its answer
is then checked against the facts, and any number not found there is flagged in ``numbers_check``.

Nemotron runs on NVIDIA's hosted endpoint (the organizers' ``05 - Nemotron on NVIDIA`` notebook
uses the same one). The key is read from ``NVIDIA_API_KEY`` in the environment or ``.env``.

Input: the field model (fitted as in ``kernelag.field_model``) and the Maryland test fields.
Output: ``data/models/field_explanations.csv``
    field_id, year, label, call, p_silage, top_evidence, explanation, numbers_check

Run:
    python -m kernelag.explain --dry-run       print two prompts, call nothing
    python -m kernelag.explain                 all 44 Maryland field-years
"""

from __future__ import annotations

import argparse
import re
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from kernelag.field_model import (MODEL_FEATURES, TRAIN_PATTERN, evidence_table, load_series, load_training,
                                  make_model, predict_silage)
from kernelag.paths import data_dir, record_in_manifest, secret

BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "nvidia/nemotron-3-super-120b-a12b"

# Plain names for the evidence, and which way a high value points.
EVIDENCE = {
    "max_drop": "size of the greenness drop at the cut",
    "max_drop_rate": "speed of that drop",
    "fade_days": "days from clearly green to clearly bare",
    "green_at_cut": "greenness just before the cut, as a share of the season peak",
    "ndmi_before_cut": "canopy moisture just before the cut",
    "ndti_post": "crop residue left on the ground after the cut",
}

SYSTEM = (
    "You explain satellite evidence about one cornfield to a USDA statistician. "
    "Use only the facts given. Do not add any number that is not in the facts. "
    "Write two or three plain sentences, no lists, no headings. "
    "Say which evidence pointed to silage, which pointed to grain, and how sure the call is."
)


def contributions(model, row: pd.DataFrame) -> dict:
    """How far each feature moved the log-odds of silage for one field (weight x standardized value)."""
    imputer, scaler, logistic = (model.named_steps[k] for k in ["simpleimputer", "standardscaler", "logisticregression"])
    z = scaler.transform(imputer.transform(row[MODEL_FEATURES]))[0]
    return dict(zip(MODEL_FEATURES, (logistic.coef_[0] * z).round(2)))


def day_to_date(year: int, day_of_year: float) -> str:
    return (pd.Timestamp(f"{int(year)}-01-01") + pd.Timedelta(days=int(day_of_year) - 1)).strftime("%d %B").lstrip("0")


def facts(row: pd.Series, push: dict) -> str:
    """The fact sheet Nemotron may use, as text. Every number in it is computed here."""
    lines = [
        f"Year: {int(row['year'])}.",
        f"Model probability that the field was chopped for silage: {round(100 * row['p_silage'])}%.",
        f"Call: {'silage' if row['p_silage'] >= 0.5 else 'grain'} (silage if the probability is 50% or more).",
    ]
    if pd.notna(row.get("cut_doy")):
        lines.append(f"Most likely harvest: around {day_to_date(row['year'], row['cut_doy'])}, "
                     f"give or take {int(row['cut_gap_days'])} days between clear satellite looks.")
    if pd.notna(row.get("green_at_cut")):
        lines.append(f"Greenness just before the harvest: {round(100 * row['green_at_cut'])}% of the season peak.")
    if pd.notna(row.get("max_drop")):
        lines.append(f"Greenness (NDVI) fell by {row['max_drop']:.2f} between two clear looks.")
    if pd.notna(row.get("ndmi_before_cut")):
        lines.append(f"Canopy moisture index (NDMI) before the harvest: {row['ndmi_before_cut']:.2f}.")
    if pd.notna(row.get("ndti_post")):
        lines.append(f"Residue index (NDTI) on the first bare looks after: {row['ndti_post']:.2f}.")
    ranked = sorted(push.items(), key=lambda item: -abs(item[1]))[:3]
    for name, value in ranked:
        direction = "towards silage" if value > 0 else "towards grain"
        lines.append(f"Evidence that weighed most: {EVIDENCE[name]}, pushing {direction}.")
    return "\n".join(lines)


NUMBER = re.compile(r"\d+(?:\.\d+)?")


def unsupported_numbers(text: str, fact_sheet: str) -> list[str]:
    """Numbers in Nemotron's answer that do not appear in the fact sheet."""
    allowed = set(NUMBER.findall(fact_sheet))
    allowed |= {n.lstrip("0") or "0" for n in allowed}
    return [n for n in NUMBER.findall(text) if n not in allowed and n.lstrip("0") not in allowed]


def strip_reasoning(text: str) -> str:
    """Drop a reasoning block if the model wrote one before its answer."""
    return text.split("</think>")[-1].strip()


def ask(client, fact_sheet: str) -> str:
    response = client.chat.completions.create(
        model=MODEL, temperature=0.2, max_tokens=700,
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": "Facts about one cornfield:\n" + fact_sheet}],
    )
    return strip_reasoning(response.choices[0].message.content or "")


def main() -> None:
    import geopandas as gpd

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--train-pattern", default=TRAIN_PATTERN)
    parser.add_argument("--dry-run", action="store_true", help="print two prompts and stop")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    data = data_dir()

    train, _ = load_training(data, args.train_pattern)
    train = train[train["assessable"]]
    model = make_model().fit(train[MODEL_FEATURES], train["is_silage"])
    test = evidence_table(gpd.read_parquet(data / "labels" / "barc_2021_2023.parquet"),
                          load_series(data / "s2_series" / "barc_2021_2023"))
    test["p_silage"], _ = predict_silage(model, test)
    test = test[test["assessable"]].reset_index(drop=True)
    pushes = [contributions(model, test.iloc[[i]]) for i in range(len(test))]
    sheets = [facts(test.iloc[i], pushes[i]) for i in range(len(test))]
    print(f"field model fitted on {len(train)} Quebec parcels; {len(test)} Maryland field-years to explain")

    if args.dry_run:
        for sheet in sheets[:2]:
            print("----\n" + SYSTEM + "\n\n" + sheet)
        return

    from openai import OpenAI

    key = secret("NVIDIA_API_KEY")
    if not key:
        raise SystemExit("NVIDIA_API_KEY is not set in the environment or .env")
    client = OpenAI(base_url=BASE_URL, api_key=key)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        answers = list(pool.map(lambda sheet: ask(client, sheet), sheets))

    table = test[["field_id", "year", "label", "p_silage"]].copy()
    table["call"] = np.where(table["p_silage"] >= 0.5, "silage", "grain")
    table["p_silage"] = table["p_silage"].round(3)
    table["top_evidence"] = [", ".join(f"{k} {v:+.2f}" for k, v in sorted(p.items(), key=lambda i: -abs(i[1]))[:3])
                             for p in pushes]
    table["explanation"] = answers
    table["numbers_check"] = [", ".join(unsupported_numbers(a, s)) or "ok" for a, s in zip(answers, sheets)]
    target = data / "models" / "field_explanations.csv"
    table.to_csv(target, index=False, lineterminator="\n")
    record_in_manifest(target, f"derived: kernelag.explain with {MODEL}")

    print(f"{len(table)} explanations -> {target}")
    print(f"answers with a number not in the facts: {(table['numbers_check'] != 'ok').sum()} of {len(table)}")
    for row in table.head(3).itertuples():
        print(f"\nfield {row.field_id} {row.year} | truth {row.label} | call {row.call} ({row.p_silage})")
        print(row.explanation)


if __name__ == "__main__":
    main()
