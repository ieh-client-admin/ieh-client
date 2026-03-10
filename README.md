# ieh-client

Python client for running IEH profile generators on the remote IEH simulation server.

## Overview

`ieh-client` connects your local Python application to the IEH API and returns generated time-series data as `pandas.DataFrame` objects.

Supported generators:

- Truck charging profile (`generate_truck_profile`)
- Building load profile (`generate_building_profile`)
- Charging point profile (`generate_charging_point_profile`)

## Architecture

```text
+--------------------+      HTTPS API      +---------------------+      Internal compute      +--------------------------+
| Local PC           | <-----------------> | ieh-client (Python) | <------------------------> | IEH simulation server    |
| your script/notebook|                    | request + validation |                           | profile generators (API) |
+--------------------+                     +---------------------+                            +--------------------------+
```

## Documentation

- [Client Usage](docs/client_usage.md)
- [Installation](docs/installation.md)
- [Truck Profile Generator (`generate_truck_profile`)](docs/generate_truck_profile.md)
- [Building Profile Generator (`generate_building_profile`)](docs/generate_building_profile.md)
- [Charging Point Profile Generator (`generate_charging_point_profile`)](docs/generate_charging_point_profile.md)
