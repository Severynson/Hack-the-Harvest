# manrajModel

Throwaway scan of two silage signals that looked promising and are not. Standard library only.

```
python3 -I test_models/manrajModel/signal_scan.py
```

Result on 528 state-years, 2014 to 2024 (share of silage acres put in the wrong state):

| Predictor | State error |
| --- | --- |
| Same as last year | 14.3% |
| Last year times the change in RMA insured silage acres | 19.4% |
| Last year plus the change in (planted minus NASS grain forecast) | 17.2% |

The change in RMA insured silage acres has an acre-weighted correlation of 0.03 with the change in NASS silage acres.
RMA covers under a fifth of silage acres and its changes follow insurance uptake, not harvest.
Planted minus grain mixes silage with abandoned acres, and both inputs carry rounding larger than the silage change.

Neither is used in `kernelag/state_model.py`. The clean pipeline is in `kernelag/`.
