from datetime import datetime, timedelta

from ieh_client import ProfileAPIClient
import matplotlib.pyplot as plt


def main() -> None:
    client = ProfileAPIClient()  # expects PROFILE_API_KEY in environment or .env
    df = client.generate_truck_profile(
        start=datetime(2026, 1, 1, 0, 0, 0),
        end=datetime(2026, 7, 1, 0, 0, 0),
        resolution=timedelta(minutes=15),
        n_trucks=25,
        location_type="warehouse",
        power_nom_charging_point_kw=300.0,
        charging_mode="DC",
    )
    df.plot()
    plt.show()


if __name__ == "__main__":
    main()
