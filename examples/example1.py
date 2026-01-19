from datetime import datetime, timedelta

from ieh_client import ProfileAPIClient


def main() -> None:
    _ = ProfileAPIClient()
    client = ProfileAPIClient(
        api_key="8804d81548fd0cf5b1a1a982d2665e52732d65b82236b3214300bc556a73e3b9"
    )

    df = client.generate_charging_point_profile(
        start=datetime(2025, 1, 1, 0, 0),
        end=datetime(2025, 1, 7, 0, 0),
        resolution=timedelta(minutes=15),
        coordinates=(48.77, 9.17),  # Stuttgart, WGS84
        power_nom_kw=(11.0, 22.0),
        charging_technology="AC",
    )
    df.to_csv("charging_profiles.csv", index=True)

    df = client.generate_building_profile(
        start=datetime(2025, 1, 1),
        end=datetime(2025, 1, 31),
        resolution=timedelta(hours=1),
        building_usage=["household", "business"],
        yearly_energy_kwh=[3500.0, 12000.0],
        working_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
    )
    df.to_csv("building_profiles.csv", index=True)


if __name__ == "__main__":
    main()
