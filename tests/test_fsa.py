"""The FSA parser: label mapping, dates from file names and stamps, the conservative release-date rule, a synthetic
workbook end to end, the as-of rule."""

import io
import statistics
import zipfile
from datetime import date, datetime

import pandas as pd
import pytest

from kernelag import fsa

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
CORE = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
NO_TIME = (1980, 1, 1, 0, 0, 0)          # the zip placeholder date-time: no usable entry time


class Inline(str):
    """A cell written as an inline string instead of a shared string (both occur in real workbooks)."""


def _column(index: int) -> str:
    letters = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


def make_xlsx(sheets: dict[str, list[list]], modified: str | None = None) -> bytes:
    """A minimal .xlsx: one worksheet per entry, strings shared (or inline), numbers as values, None empty;
    ``modified`` (W3CDTF, e.g. "2024-11-12T15:00:00Z") adds docProps/core.xml with that dcterms:modified."""
    shared: list[str] = []
    parts = {}
    for number, rows in enumerate(sheets.values(), start=1):
        xml_rows = []
        for r, row in enumerate(rows, start=1):
            cells = []
            for c, value in enumerate(row):
                ref = f"{_column(c)}{r}"
                if value is None:
                    continue
                if isinstance(value, Inline):
                    cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{value}</t></is></c>')
                elif isinstance(value, str):
                    if value not in shared:
                        shared.append(value)
                    cells.append(f'<c r="{ref}" t="s"><v>{shared.index(value)}</v></c>')
                else:
                    cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            xml_rows.append(f'<row r="{r}">{"".join(cells)}</row>')
        parts[f"xl/worksheets/sheet{number}.xml"] = (
            f'<worksheet xmlns="{MAIN}"><sheetData>{"".join(xml_rows)}</sheetData></worksheet>')
    names = "".join(f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>' for i, name in enumerate(sheets, start=1))
    parts["xl/workbook.xml"] = f'<workbook xmlns="{MAIN}" xmlns:r="{RELS}"><sheets>{names}</sheets></workbook>'
    links = "".join(f'<Relationship Id="rId{i}" Type="{RELS}/worksheet" Target="worksheets/sheet{i}.xml"/>'
                    for i in range(1, len(sheets) + 1))
    parts["xl/_rels/workbook.xml.rels"] = f'<Relationships xmlns="{PACKAGE_RELS}">{links}</Relationships>'
    strings = "".join(f"<si><t>{s}</t></si>" for s in shared)
    parts["xl/sharedStrings.xml"] = f'<sst xmlns="{MAIN}">{strings}</sst>'
    if modified is not None:
        parts["docProps/core.xml"] = (
            f'<cp:coreProperties xmlns:cp="{CORE}" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dcterms:created xsi:type="dcterms:W3CDTF">2012-07-30T19:01:41Z</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{modified}</dcterms:modified></cp:coreProperties>')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as book:
        for name, text in parts.items():
            book.writestr(name, text)
    return buffer.getvalue()


def make_archive(folder, zip_name: str, inner_name: str, sheets: dict[str, list[list]], modified: str | None = None,
                 entry_time: tuple = NO_TIME):
    """An FSA-style download: a zip holding one workbook, its zip entry stamped ``entry_time``."""
    path = folder / zip_name
    with zipfile.ZipFile(path, "w") as outer:
        outer.writestr(zipfile.ZipInfo(inner_name, date_time=entry_time), make_xlsx(sheets, modified))
    return path


HEADER = ["State Code", "County Code", "Crop Code", "State", "County", "State County Code", "Crop", "Crop Type",
          "Intended Use", "Irrigation Practice", "Planted Acres", "Volunteer Acres", "Failed Acres", "Prevented Acres",
          "Not Planted Acres", "Planted and Failed Acres"]


def corn(state, county, crop_type, use, practice, planted, failed=0, crop="CORN"):
    return [state, county, "0041", "Iowa", "Story", f"{state}{county}", crop, crop_type, use, practice,
            planted, 0, failed, 0, 0, planted + failed]


def synthetic_detail(tmp_path, modified: str | None = None, entry_time: tuple = NO_TIME):
    county_rows = [
        ["2024 ACRES BY COUNTY BY CROP ... REPORTED TO FARM SERVICE AGENCY", None, None, None, None, None, None,
         None, None, None, None, None, None, None, None, 45597],              # 45597 = 2024-11-01
        HEADER,
        corn("19", "169", "YELLOW", "Grain", "N", 1000.5, failed=10),
        corn("19", "169", "WHITE", "Grain", "N", 99.5),                       # summed with yellow
        corn("19", "169", "YELLOW", "Grain", "I", 50),
        corn("19", "169", "YELLOW", "Silage", "N", 200),
        corn("19", "169", "SWEET, BICOLOR", "Fresh", "N", 30),                # sweet corn: dropped
        corn("19", "169", "POPCORN", "Grain", "N", 40),                       # popcorn: dropped
        corn("19", "169", "SWEET, WHITE", "Silage", "N", 5),                  # dropped, but in the all-type check
        ["19", "169", "0011", "Iowa", "Story", "19169", "WHEAT", "SRW", "Grain", "N", 70, 0, 0, 0, 0, 70],
        ["36", "001", "0041", "New York", "Albany", "36001", Inline("CORN"), "YELLOW", "Forage", "N",
         300, 0, 0, 0, 0, 300],                                               # inline string; Forage = silage
        corn("36", "001", "YELLOW", "Blank", "N", 1),
    ]
    pivot_rows = [
        [45597, "2024 PLANTED ACRES (INCLUDING FAILED ACRES) REPORTED TO FARM SERVICE AGENCY"],
        ["Planted and Failed", "Column Labels"],
        ["Row Labels", "BARLEY", "CORN", "Grand Total"],
        ["Iowa", 1, 1435, 1436],
        ["New York", None, 301, 301],
        ["Grand Total", 1, 1736, 1737],
    ]
    return make_archive(tmp_path, "kmWMJUc631qPEbuuKeWH.zip", "2024_fsa_acres_web_110124.xlsx",
                        {"plant_and_fail": pivot_rows, "county_data": county_rows}, modified, entry_time)


# --- labels ----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("label, expected", [
    ("Grain", "grain"), ("GR", "grain"), (" grain ", "grain"),
    ("Silage", "silage"), ("SG", "silage"), ("Forage", "silage"), ("FG", "silage"),
    ("Seed", "seed"), ("SD", "seed"), ("Grazing", "grazing"), ("GZ", "grazing"),
    ("Fresh", "other"), ("FH", "other"), ("Processed", "other"), ("PR", "other"), ("Left Standing", "other"),
    ("LS", "other"), ("Something New", "other"),
    ("", "unspecified"), (None, "unspecified"), ("Blank", "unspecified"),
])
def test_normalise_use(label, expected):
    assert fsa.normalise_use(label) == expected


def test_corn_and_field_corn_types():
    assert fsa.is_corn("CORN") and fsa.is_corn(" corn ")
    assert not fsa.is_corn("SWEET CORN") and not fsa.is_corn("POPCORN")
    for kept in ["YELLOW", "WHITE", "WXY", "WAXY", "AMA", "HIGH AMYLASE", "BLUE", "GRAINLESS FORAGE", "", None]:
        assert fsa.is_field_corn(kept), kept
    for dropped in ["SWEET", "SWEET, BICOLOR", "SWEET-WHITE", "SWEET YELLOW/GOLDEN LATE", "POPCORN",
                    "STRAWBERRY POPCORN", "SWT", "SBI", "SWH", "SYE", "SYL", "POP", "PSN"]:
        assert not fsa.is_field_corn(dropped), dropped


# --- dates -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name, crop_year, expected", [
    ("2026_fsa_acres_web_110526.xlsx", 2026, (date(2026, 11, 5), "day")),
    ("2015_fsa_acres_08032015.xlsx", 2015, (date(2015, 8, 3), "day")),
    ("Copy of 2016_fsa_acres_09012016.xlsx", 2016, (date(2016, 9, 1), "day")),
    ("2018_fsa_acres_090618.checked.xlsx", 2018, (date(2018, 9, 6), "day")),
    ("2020_fsa_acres_web_073120.xlsx", 2020, (date(2020, 7, 31), "day")),
    ("2024_fsa_acres_010225.xlsx", 2024, (date(2025, 1, 2), "day")),
    ("2012_fsa_acres_nov_2012.xlsx", 2012, (date(2012, 11, 1), "month")),
    ("Revised_2012_fsa_acres_dec_2012.xlsx", 2012, (date(2012, 12, 1), "month")),
    ("2011_fsa_acres_detail_sep2011_1.xlsx", 2011, (date(2011, 9, 1), "month")),
    ("2011_fsa_acres_sum_aug11_4.zip", 2011, (date(2011, 8, 1), "month")),
    ("FINAL_2015_fsa_acres_sept2015.xlsx", 2015, (date(2015, 9, 1), "month")),
    ("2011_fsa_acres_detail_jan2012.xlsx", 2011, (date(2012, 1, 1), "month")),
    ("2014_fsa_acres_jan2014.xlsx", 2014, (None, "none")),          # FSA's typo (it is January 2015): rejected
    ("2016_fsa_acres_1003016.xlsx", 2016, (None, "none")),          # seven digits: not guessed
    ("2009_fsa_acres_detail_final_7.xlsx", 2009, (None, "none")),
])
def test_date_from_name(name, crop_year, expected):
    assert fsa.date_from_name(name, crop_year) == expected


def test_crop_year_and_excel_dates():
    assert fsa.crop_year_from_name("Revised1_2013_fsa_acres_sep_2013.xlsx") == 2013
    assert fsa.crop_year_from_name("Copy of 2016_fsa_acres_09012016.xlsx") == 2016
    assert fsa.crop_year_from_name("DoISjehvQfz9.ZIP") is None
    assert fsa.excel_date("46331") == date(2026, 11, 5)
    assert fsa.excel_date("1000.5") is None and fsa.excel_date("text") is None


def test_vintage():
    assert fsa.vintage_label(date(2017, 8, 31), 2017) == "sep"        # FSA's September 2017 file
    assert fsa.vintage_label(date(2020, 7, 31), 2020) == "aug"
    assert fsa.vintage_label(date(2019, 8, 22), 2019) == "aug"
    assert fsa.vintage_label(date(2025, 12, 1), 2025) == "dec"
    assert fsa.vintage_label(date(2026, 1, 5), 2025) == "final"
    assert fsa.vintage_label(None, 2009, final_in_name=True) == "final"


# --- the conservative release date -----------------------------------------------------------------------------

def test_lag_is_the_median_documented_lag():
    lags = [(release - data).days for data, release in fsa.DOCUMENTED_RELEASES.items()]
    assert min(lags) == 5 and max(lags) == 11
    assert fsa.PUBLICATION_LAG_DAYS == statistics.median(lags) == 8


def test_published_date_rule():
    data = date(2013, 9, 1)
    assert fsa.published_date(data) == (date(2013, 9, 9), "assumed: data date + 8 days", "data date + 8 days")
    # saved 17 Sep (as the real 2013 September workbook was): posted no earlier than the 18th
    assert fsa.published_date(data, datetime(2013, 9, 17, 12, 36)) == (
        date(2013, 9, 18), "assumed: workbook saved 2013-09-17 + 1 day", "internal save + 1 day")
    assert fsa.published_date(data, datetime(2013, 9, 9, 8, 0))[0] == date(2013, 9, 10)      # saved on data + 8
    assert fsa.published_date(data, datetime(2013, 9, 8, 23, 59))[2] == "data date + 8 days"  # tie: lag kept
    assert fsa.published_date(data, datetime(2013, 9, 3))[0] == date(2013, 9, 9)              # saved early
    # a documented release wins over both inputs, even when the save time is later
    assert fsa.published_date(date(2026, 11, 5)) == (date(2026, 11, 10), "documented", "documented release")
    assert fsa.published_date(date(2026, 11, 5), datetime(2026, 11, 20))[0] == date(2026, 11, 10)
    assert fsa.published_date(None)[:2] == (None, "unknown (no data date)")


def test_internal_save_time_sources():
    book = zipfile.ZipFile(io.BytesIO(make_xlsx({"s": [["x"]]}, modified="2015-11-13T14:36:31Z")))
    assert fsa.internal_saved(book, (2015, 11, 13, 9, 36, 32)) == (
        datetime(2015, 11, 13, 14, 36, 31), "docProps/core.xml dcterms:modified (UTC)")
    offset = zipfile.ZipFile(io.BytesIO(make_xlsx({"s": [["x"]]}, modified="2014-12-11T23:41:47-05:00")))
    assert fsa.core_modified(offset) == datetime(2014, 12, 12, 4, 41, 47)                    # converted to UTC
    bare = zipfile.ZipFile(io.BytesIO(make_xlsx({"s": [["x"]]})))
    assert fsa.internal_saved(bare, (2016, 9, 12, 11, 27, 50)) == (
        datetime(2016, 9, 12, 11, 27, 50), "zip entry date-time (local clock)")
    assert fsa.internal_saved(bare, NO_TIME)[0] is None and fsa.internal_saved(bare, None)[0] is None


# --- one synthetic archive end to end --------------------------------------------------------------------------

def test_synthetic_detail_round_trip(tmp_path):
    info, county = fsa.parse_archive(synthetic_detail(tmp_path))
    assert info["status"] == "ok" and info["kind"] == "detail"
    assert info["crop_year"] == 2024
    assert info["data_as_of"] == date(2024, 11, 1) and info["date_source"] == "sheet date stamp"
    assert info["vintage"] == "nov" and info["assumed_published"] == date(2024, 11, 9)       # data date + 8
    assert info["internal_saved"] is None and info["published_rule"] == "data date + 8 days"
    assert info["us_grain_planted"] == pytest.approx(1150)
    assert info["us_silage_planted"] == pytest.approx(500)                 # 200 Silage + 300 Forage
    assert info["us_corn_planted"] == pytest.approx(1651)
    assert info["us_sweet_pop_planted"] == pytest.approx(75)
    assert info["us_silage_all_types"] == pytest.approx(505)               # includes the sweet silage row
    assert info["us_all_types_planted_and_failed"] == pytest.approx(info["pivot_corn_planted_and_failed"])
    assert info["counties_with_silage"] == 2
    assert '"SWEET, BICOLOR|Fresh": 30' in info["corn_type_use_labels"]

    rows = county.set_index(["county_fips", "intended_use_raw", "irrigation"])
    grain = rows.loc[("19169", "Grain", "N")]
    assert grain["planted_acres"] == pytest.approx(1100) and grain["failed_acres"] == pytest.approx(10)
    assert grain["state"] == "IOWA" and grain["intended_use"] == "grain"
    assert rows.loc[("36001", "Forage", "N"), "intended_use"] == "silage"
    assert rows.loc[("36001", "Blank", "N"), "intended_use"] == "unspecified"
    assert len(county) == 5                                                # wheat, sweet and popcorn rows gone

    table = fsa.county_table(county.assign(vintage="nov"))
    state = fsa.state_table(table)
    iowa = state[state["state"] == "IOWA"].set_index("intended_use")
    assert iowa.loc["grain", "planted_acres"] == pytest.approx(1150)
    assert iowa.loc["silage", "planted_acres"] == pytest.approx(200)


def test_synthetic_workbook_saved_after_data_plus_8_is_published_the_next_day(tmp_path):
    info, _ = fsa.parse_archive(synthetic_detail(tmp_path, modified="2024-11-12T15:00:00Z",
                                                 entry_time=(2024, 11, 20, 9, 0, 0)))
    assert info["data_as_of"] == date(2024, 11, 1)                          # data date + 8 = 9 Nov
    assert info["internal_saved"] == datetime(2024, 11, 12, 15, 0)         # core.xml beats the later zip entry
    assert info["internal_saved_source"].startswith("docProps/core.xml")
    assert info["assumed_published"] == date(2024, 11, 13) and info["published_rule"] == "internal save + 1 day"
    files = pd.DataFrame([info]).assign(data_as_of=lambda f: pd.to_datetime(f["data_as_of"]),
                                        assumed_published=lambda f: pd.to_datetime(f["assumed_published"]))
    assert fsa.latest_file(files, "2024-11-12", 2024) is None              # saved that day: not out yet
    assert fsa.latest_file(files, "2024-11-13", 2024)["zip_name"] == "kmWMJUc631qPEbuuKeWH.zip"


def test_synthetic_workbook_without_core_xml_falls_back_to_the_zip_entry(tmp_path):
    info, _ = fsa.parse_archive(synthetic_detail(tmp_path, entry_time=(2024, 11, 14, 16, 5, 0)))
    assert info["internal_saved"] == datetime(2024, 11, 14, 16, 5)
    assert info["internal_saved_source"].startswith("zip entry")
    assert info["assumed_published"] == date(2024, 11, 15) and info["published_rule"] == "internal save + 1 day"


def test_synthetic_workbook_documented_release_wins(tmp_path):
    rows = [["2026 ACRES BY COUNTY BY CROP", None, None, None, None, None, None, None, None, None, None, None,
             None, None, None, 46331],                                         # 46331 = 2026-11-05 (documented)
            HEADER, corn("19", "169", "YELLOW", "Grain", "N", 100)]
    path = make_archive(tmp_path, "Wrcdk.zip", "2026_fsa_acres_web_110526.xlsx", {"county_data": rows},
                        modified="2026-11-20T10:00:00Z")
    info, _ = fsa.parse_archive(path)
    assert info["data_as_of"] == date(2026, 11, 5) and info["internal_saved"] == datetime(2026, 11, 20, 10, 0)
    assert info["assumed_published"] == date(2026, 11, 10)
    assert info["published_source"] == "documented" and info["published_rule"] == "documented release"
    assert "after its documented release" in info["notes"]


def test_summary_workbook_is_marked_and_skips_the_us_row(tmp_path):
    rows = [[None, "2010 PLANTED ACRES (INCLUDING FAILED ACRES) REPORTED TO FARM SERVICE AGENCY final"],
            ["State", "BARLEY", "CORN", "TOTAL"], ["IA", 5, 1000, 1005], ["NY", None, 200, 200],
            ["US", 5, 1200, 1205]]
    path = make_archive(tmp_path, "2010_fsa_acres_sum_final_6.zip", "2010_fsa_acres_summary_final_6.xlsx",
                        {"pltfail": rows})
    info, county = fsa.parse_archive(path)
    assert info["status"] == "summary_only" and county.empty
    assert info["pivot_corn_planted_and_failed"] == pytest.approx(1200)
    assert info["vintage"] == "final" and info["data_as_of"] is None


def test_truncated_archive_is_corrupt(tmp_path):
    good = make_archive(tmp_path, "full.zip", "2020_fsa_acres_web_100120.xlsx",
                        {"county_data": [HEADER, corn("19", "169", "YELLOW", "Grain", "N", 1)]},
                        entry_time=(2020, 10, 9, 8, 0, 0))
    broken = tmp_path / "2020_FSA_acres_web_as_of_100120_gHlBad.zip"
    broken.write_bytes(good.read_bytes()[:200])
    info, county = fsa.parse_archive(broken)
    assert info["status"] == "corrupt" and county.empty
    assert info["reason"].startswith("truncated download")
    assert info["inner_xlsx"] == "2020_fsa_acres_web_100120.xlsx"
    assert info["crop_year"] == 2020 and info["data_as_of"] == date(2020, 10, 1)
    assert info["internal_saved"] == datetime(2020, 10, 9, 8, 0)           # from the local file header
    assert info["assumed_published"] == date(2020, 10, 10) and info["published_rule"] == "internal save + 1 day"


def test_parse_all_writes_three_tables(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    synthetic_detail(raw)
    files, county = fsa.parse_all(raw, workers=1)
    paths = fsa.write_outputs(files, county, tmp_path / "out")
    assert [p.name for p in paths] == ["fsa_files.csv", "fsa_corn_county.parquet", "fsa_corn_state.csv"]
    back = pd.read_parquet(paths[1])
    assert set(back["intended_use"].astype(str)) == {"grain", "silage", "unspecified"}
    assert back["planted_acres"].sum() == pytest.approx(1651)
    listed = pd.read_csv(paths[0])
    assert listed.loc[0, "status"] == "ok" and listed.loc[0, "data_as_of"] == "2024-11-01"
    assert {"published_rule", "internal_saved", "internal_saved_source"} <= set(listed.columns)


# --- the as-of rule --------------------------------------------------------------------------------------------

def _files() -> pd.DataFrame:
    rows = [  # crop year, vintage, data date, publication date, status
        (2024, "nov", "2024-11-01", "2024-11-06", "ok"),
        (2024, "final", "2025-01-02", "2025-01-07", "ok"),
        (2025, "sep", "2025-09-02", "2025-09-12", "ok"),
        (2025, "dec", "2025-12-01", "2025-12-09", "ok"),     # no October or November 2025 file
        (2025, "final", "2026-01-05", "2026-01-12", "ok"),
        (2026, "oct", "2026-10-01", "2026-10-09", "corrupt"),
    ]
    frame = pd.DataFrame(rows, columns=["crop_year", "vintage", "data_as_of", "assumed_published", "status"])
    return frame.assign(data_as_of=pd.to_datetime(frame["data_as_of"]),
                        assumed_published=pd.to_datetime(frame["assumed_published"]))


def test_latest_file_never_uses_a_later_release():
    files = _files()
    assert fsa.latest_file(files, "2025-11-15", 2025)["vintage"] == "sep"     # December file not out yet
    assert fsa.latest_file(files, "2025-12-15", 2025)["vintage"] == "dec"
    assert fsa.latest_file(files, "2025-09-11", 2025) is None                 # September released on the 12th
    assert fsa.latest_file(files, "2026-03-01", 2025)["vintage"] == "dec"     # own final is not in-season input
    assert fsa.latest_file(files, "2026-11-15", 2026) is None                 # corrupt files are never usable


def test_usable_files_history_is_earlier_years_published_by_the_date():
    usable = fsa.usable_files(_files(), "2025-11-15", 2025)
    assert sorted(zip(usable["crop_year"], usable["vintage"])) == [(2024, "final"), (2024, "nov"), (2025, "sep")]
