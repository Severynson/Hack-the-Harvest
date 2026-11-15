"""Only single-crop grain or silage maize parcels of usable size become labels."""

import geopandas as gpd
from shapely.geometry import box

from kernelag.quebec import label_parcels


def test_label_parcels_keeps_single_crop_maize_of_usable_size():
    parcels = gpd.GeoDataFrame(
        {
            "IDANPAR": [1, 2, 3, 4, 5],
            "IDPAR": [11, 12, 13, 14, 15],
            "SUPHEC": [10.0, 8.0, 6.0, 1.0, 9.0],
            "NBPRO": [1, 1, 1, 1, 2],
            "CODPRO1": ["MGR", "MFO", "MFE", "MGR", "MGR"],
            "VARCUL": ["P9188 UTM: 2700", None, "silage hybrid", "x", "y"],
        },
        geometry=[box(0, 0, 1, 1)] * 5,
        crs="EPSG:4326",
    )
    labeled = label_parcels(parcels, 2023)

    assert labeled["field_id"].tolist() == ["1", "2", "3"]          # too small (4) and two-crop (5) dropped
    assert labeled["label"].tolist() == ["grain", "silage", "silage"]
    assert labeled["heat_units"].tolist()[0] == 2700
    assert labeled["heat_units"].isna().tolist() == [False, True, True]
    assert (labeled["year"] == 2023).all()
