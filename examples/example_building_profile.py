from datetime import datetime, timedelta

from ieh_client import ProfileAPIClient


def main() -> None:
    client = ProfileAPIClient()  # expects PROFILE_API_KEY in environment or .env
    df = client.generate_building_profile(
        start=datetime(2026, 1, 1, 0, 0, 0),
        end=datetime(2026, 7, 1, 0, 0, 0),
        resolution=timedelta(minutes=15),
        building_usage="household",
        yearly_energy_kwh=3500.0,
        working_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
    )
    print(df.head())


if __name__ == "__main__":
    main()
