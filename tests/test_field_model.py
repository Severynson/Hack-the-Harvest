"""Scoring is as documented, and a field without evidence is never called silage."""

import numpy as np
import pandas as pd

from kernelag.field_model import MODEL_FEATURES, evidence_table, make_model, predict_silage, scores
from tests.test_features import CLIFF, FADE


def test_scores_counts_silage_as_the_positive_class():
    truth = np.array([1, 1, 1, 0, 0, 0, 0, 0])
    call = np.array([1, 1, 0, 1, 0, 0, 0, 0])
    result = scores(truth, call)
    assert (result["TP"], result["FP"], result["FN"], result["TN"]) == (2, 1, 1, 4)
    assert result["silage_precision"] == 0.667 and result["silage_recall"] == 0.667
    assert result["grain_precision"] == 0.8 and result["grain_recall"] == 0.8
    assert result["false_positive_rate"] == 0.2 and result["accuracy"] == 0.75


def test_evidence_table_marks_fields_without_a_usable_series():
    series = pd.concat([
        CLIFF.assign(field_id=1, year=2023),
        FADE.assign(field_id=2, year=2023),
        CLIFF.head(3).assign(field_id=3, year=2023),   # too few clear looks
    ])
    labels = pd.DataFrame({"field_id": [1, 2, 3, 4], "year": 2023,
                           "label": ["silage", "grain", "silage", "grain"]})
    table = evidence_table(labels, series)
    assert table["field_id"].tolist() == ["1", "2", "3"]      # field 4 has no series at all
    assert table["assessable"].tolist() == [True, True, False]
    assert table["is_silage"].tolist() == [1, 0, 1]


def test_not_assessable_fields_are_scored_as_grain():
    series = pd.concat([CLIFF.assign(field_id=i, year=2023) for i in (1, 2, 3)]
                       + [FADE.assign(field_id=i, year=2023) for i in (4, 5, 6)]
                       + [CLIFF.head(3).assign(field_id=7, year=2023)])
    labels = pd.DataFrame({"field_id": range(1, 8), "year": 2023,
                           "label": ["silage"] * 3 + ["grain"] * 3 + ["silage"]})
    table = evidence_table(labels, series)
    fit_part = table[table["assessable"]]
    model = make_model().fit(fit_part[MODEL_FEATURES], fit_part["is_silage"])
    probability, call = predict_silage(model, table)
    assert call.tolist() == [1, 1, 1, 0, 0, 0, 0]
    assert np.isnan(probability[-1])


def test_text_ids_in_labels_match_numeric_ids_in_series():
    """Quebec label files hold ids as text; the series CSVs read back as numbers."""
    series = pd.concat([CLIFF.assign(field_id=101, year=2023), FADE.assign(field_id=102, year=2023)])
    labels = pd.DataFrame({"field_id": ["101", "102"], "year": 2023, "label": ["silage", "grain"]})
    table = evidence_table(labels, series)
    assert table["field_id"].tolist() == ["101", "102"] and table["assessable"].all()


def test_held_out_year_calls_never_fit_on_the_scored_year():
    from kernelag.field_model import held_out_year_calls

    # 2022 and 2023 follow the usual pattern; in 2024 the labels are swapped. A model that saw
    # 2024 while scoring it would get 2024 right; one fitted on the other years gets it wrong.
    parts, labels = [], []
    for year, flip in [(2022, False), (2023, False), (2024, True)]:
        for i in range(4):
            cliff_id, fade_id = f"{year}c{i}", f"{year}f{i}"
            parts += [CLIFF.assign(field_id=cliff_id, year=year), FADE.assign(field_id=fade_id, year=year)]
            labels += [{"field_id": cliff_id, "year": year, "label": "grain" if flip else "silage"},
                       {"field_id": fade_id, "year": year, "label": "silage" if flip else "grain"}]
    table = evidence_table(pd.DataFrame(labels), pd.concat(parts))
    call = held_out_year_calls(table)
    truth = table["is_silage"].to_numpy()
    in_2024 = (table["year"] == 2024).to_numpy()
    assert (call[in_2024] != truth[in_2024]).all()
