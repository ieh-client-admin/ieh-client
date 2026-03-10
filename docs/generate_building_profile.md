# `generate_building_profile`

Generates a building load profile and returns a `pandas.DataFrame` indexed by timestamp.

## Example

```python
from datetime import datetime, timedelta
from ieh_client import ProfileAPIClient

client = ProfileAPIClient()
df = client.generate_building_profile(
    start=datetime(2026, 1, 1, 0, 0, 0),
    end=datetime(2026, 1, 2, 0, 0, 0),
    resolution=timedelta(minutes=15),
    building_usage="household",
    yearly_energy_kwh=3500.0,
    working_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
)
```

## Parameters

| Name | Type | Allowed values | Description |
|---|---|---|---|
| `start` | `datetime` | Any valid datetime | Inclusive start timestamp. |
| `end` | `datetime` | Any valid datetime | Exclusive end timestamp. |
| `resolution` | `timedelta` | Any positive duration (internally converted to minutes) | Output time resolution. Default: `timedelta(hours=1)`. |
| `building_usage` | `Literal[...] \| Iterable[Literal[...]]` | Scalar or sequence of: `"agriculture"`, `"household"`, `"business"`, `"industrial"` | Building usage class(es). |
| `yearly_energy_kwh` | `float \| Iterable[float]` | Scalar float or sequence of floats | Annual energy demand in kWh. |
| `working_days` | `Iterable[int \| Literal[...]] \| None` | `0..6` (`0 = monday`) and/or names `"monday"` ... `"sunday"`, `"public_holiday"`, or `None` | Active days for load generation. |

## Notes

- `building_usage` and `yearly_energy_kwh` must be both scalar or both iterable.
- If iterable, both must have identical length; otherwise the client raises an error before API request.
- Invalid values raise `TypeError`/`ValueError`; transport/API failures raise `ConnectionError`.
