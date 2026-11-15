# Handoff: `kernelag.field_model.load_series` drops leading zeros in field ids

- From: cc-daniel. To: the owner of `kernelag/field_model.py` (last change b107645, cc-varun).
- State: found while pulling the 15-state candidate series; not fixed (not my file).

## The bug

`load_series` (kernelag/field_model.py:53-55) reads each series CSV with `pd.read_csv(f, parse_dates=["date"])`
and only then casts `field_id` to text. Pandas has already parsed the id as an integer, so any id with a
leading zero loses it. CSB field ids start with the state FIPS code, so every California (06...) and
Colorado (08...) field is affected, for example `061825011676499` becomes `61825011676499`.

## Effect

Any join on `field_id` against a table that keeps the id as text (labels, masks, CSB samples) silently
drops those fields: no error, just fewer rows. Quebec and Maryland ids are unaffected.

## Fix (one line)

```python
series = pd.concat([pd.read_csv(f, parse_dates=["date"], dtype={"field_id": str, "OBJECTID": str})
                    for f in files], ignore_index=True)
```

## Check

```bash
python -I -c "from pathlib import Path; from kernelag.field_model import load_series; \
s = load_series(Path('data/s2_series/candes_06')); print(s.field_id.str.startswith('06').mean())"
```

It should print 1.0 after the fix (prints 0.0 before).
