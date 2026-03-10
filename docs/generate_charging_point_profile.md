# `generate_charging_point_profile`

Generates a charging-point load profile and returns a `pandas.DataFrame` indexed by timestamp.

## Example

```python
from datetime import datetime, timedelta
from ieh_client import ProfileAPIClient

client = ProfileAPIClient()
df = client.generate_charging_point_profile(
    start=datetime(2026, 1, 1, 0, 0, 0),
    end=datetime(2026, 1, 2, 0, 0, 0),
    resolution=timedelta(minutes=30),
    coordinates=(48.7784, 9.1800),
    power_nom_kw=(11.0, 22.0),
    charging_technology="AC",
)
```

## Parameters

| Name | Type | Allowed values | Description |
|---|---|---|---|
| `start` | `datetime` | Any valid datetime | Inclusive start timestamp. |
| `end` | `datetime` | Any valid datetime | Exclusive end timestamp. |
| `resolution` | `timedelta` | Any positive duration (internally converted to minutes) | Output time resolution. Default: `timedelta(hours=1)`. |
| `coordinates` | `tuple[float, float] \| None` | Tuple `(latitude, longitude)` | Geographic location of the charging point. |
| `power_nom_kw` | `float \| tuple[float, float] \| None` | Single value or `(min_kw, max_kw)` with `min_kw <= max_kw` | Nominal charging power range in kW. |
| `charging_technology` | `str \| None` | Typical values: `"AC"`, `"DC"` | Charging technology label passed to API. |

## Notes

- Current implementation expects indexable `coordinates`; pass a tuple to avoid runtime errors.
- If `power_nom_kw` is a scalar, it is converted to a fixed range `(value, value)`.
- Invalid values raise `ValueError`/`TypeError`; transport/API failures raise `ConnectionError`.
