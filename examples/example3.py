from datetime import datetime, timedelta
from ieh_client import ProfileAPIClient


def main() -> None:
    client = ProfileAPIClient(
        api_key="8804d81548fd0cf5b1a1a982d2665e52732d65b82236b3214300bc556a73e3b9"
    )
    df = client.generate_truck_profile(
        start=datetime(2025, 1, 1),
        end=datetime(2025, 1, 31),
        resolution=timedelta(hours=1),
        n_bet=10,
        site_type="distribution_center"
    )
    df.to_csv("truck_site_profiles.csv", index=True)


if __name__ == "__main__":
    main()


