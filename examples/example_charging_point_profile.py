from datetime import datetime, timedelta

from ieh_client import ProfileAPIClient


def main() -> None:
    client = ProfileAPIClient()  # expects PROFILE_API_KEY in environment or .env
    df = client.generate_charging_point_profile(
        start=datetime(2026, 1, 1, 0, 0, 0),
        end=datetime(2026, 7, 1, 0, 0, 0),
        resolution=timedelta(minutes=30),
        coordinates=(48.7784, 9.1800),
        power_nom_kw=(11.0, 22.0),
        charging_technology="AC",
    )
    print(df.head())


if __name__ == "__main__":
    main()
