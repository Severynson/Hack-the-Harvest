"""
Nemotron's model: silage vs grain on BARC corn fields. Written by Nemotron, one experiment at a time.

Starting point: a blank model that calls every field grain (val_f1 = 0). Nemotron replaces
fit_predict with a model of its own; the run block below is fixed and added by the agent.

Data handed to fit_predict (see prepare.py):
  ts_*   one row per field per Sentinel-2 scene: OBJECTID, date, year, doy, n_pixels, valid_frac,
         ndvi, ndvi_p25, ndvi_p75, ndmi, ndti, bsi, red, nir, swir1, swir2, scene
  lab_tr labelled training field-years: OBJECTID, year, harvest_type, y (1 = Silage), ACRES
  keys_te the field-years to predict: OBJECTID, year
"""

import time

import numpy as np
import pandas as pd

from prepare import evaluate

t0 = time.time()


def fit_predict(ts_tr, lab_tr, ts_te, keys_te):
    return np.zeros(len(keys_te), dtype=int)
