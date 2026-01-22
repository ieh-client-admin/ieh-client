from datetime import datetime, timedelta
import pandas as pd
from ieh_client import ProfileAPIClient


def main() -> None:
    client = ProfileAPIClient(
        api_key="8804d81548fd0cf5b1a1a982d2665e52732d65b82236b3214300bc556a73e3b9"
    )
    sites = pd.read_csv("truck_sites.csv").to_dict(orient="records")
    site_profiles = pd.DataFrame()
    scaling_factor = 4.
    for site in sites:
        site_profile = client.generate_truck_profile(
            start=datetime(2025, 1, 1),
            end=datetime(2025, 1, 31),
            resolution=timedelta(hours=1),
            n_bet=site["n_trucks"] * scaling_factor,
            site_type=site["site_type"],
        )
        site_profile[site["site_id"]] = site_profile
    site_profiles.to_csv("truck_sites.csv", index=False)


if __name__ == "__main__":
    main()


