import os
from datetime import datetime, timedelta
from typing import Literal, Iterable
from beartype import beartype

from dotenv import load_dotenv
import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class _APIClient:
    _base_url = "https://profile-generator.ieh.uni-stuttgart.de/api-server"

    def __init__(self, api_key: str = None, timeout: int = 10, max_retries: int = 3):
        """
        Initialize the Profile API client.

        Priority for API key:
        1. Explicit argument
        2. Environment variable PROFILE_API_KEY
        3. .env file (loaded automatically)

        Args:
            api_key (str | None): Authentication API key.
            timeout (int): Request timeout in seconds.
            max_retries (int): Max retries for failed requests.
        """
        load_dotenv()
        self.api_key = api_key or os.getenv("PROFILE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "PROFILE_API_KEY not found. "
                "Provide it explicitly, set it as an environment variable, "
                "or define it in a .env file."
            )
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        self.timeout = timeout
        self.session = requests.Session()
        retries = Retry(
            total=max_retries,
            backoff_factor=2,  # exponential backoff: 1s, 2s, 4s...
            status_forcelist=[429, 500, 502, 503, 504],  # transient errors
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _post(self, endpoint: str, payload: dict):
        """
        Internal helper to POST to an endpoint with authentication.
        """
        url = f"{self._base_url}{endpoint}"
        try:
            response = self.session.post(
                url, json=payload, headers=self.headers, timeout=self.timeout, verify=False
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Request to {url} timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Request to {url} failed: {e}")

        return response.json()


class ProfileAPIClient(_APIClient):
    """Class used to simulate the profiles with Profile API client."""

    @beartype
    def generate_building_profile(
            self,
            start: datetime,
            end: datetime,
            resolution: timedelta = timedelta(hours=1),
            building_usage: Literal["agriculture", "household", "business", "industrial"] | Iterable[
                Literal["agriculture", "household", "business", "industrial"]] = "household",
            yearly_energy_kwh: float | Iterable[float] = 1000,
            working_days: Iterable[int | Literal[
                "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "public_holiday"
            ]] | None = None
    ) -> pd.DataFrame:
        """
        Generate a building load profile using the IEH BLPG
        (Building Load Profile Generator) service.

        The method sends the specified parameters to the backend service and
        returns the resulting building load profile as a pandas DataFrame.

        Args:
            start (datetime):
                Start timestamp of the building profile (inclusive).

            end (datetime):
                End timestamp of the building profile (exclusive).

            resolution (timedelta, optional):
                Temporal resolution of the generated profile.
                Defaults to 1 hour.

            building_usage (str | Iterable[str], optional):
                Usage type of the building.
                Supported values are:

                - ``"household"``
                - ``"agriculture"``
                - ``"business"``
                - ``"industrial"``

                May be provided as a single value or as an iterable of values.
                Defaults to ``"household"``.

            yearly_energy_kwh (float | Iterable[float], optional):
                Annual energy demand of the building in kilowatt-hours.
                May be provided as a single value or as an iterable of values.
                Defaults to ``1000``.

            working_days (Iterable[int | str] | None, optional):
                Days of the week on which the building is considered occupied or active.
                Days may be specified either as integers (``0`` = Monday, ``6`` = Sunday)
                or as strings:

                - ``"monday"`` … ``"sunday"``
                - ``"public_holiday"``

                If ``None``, a default working-day configuration
                (typically Monday–Friday) is used by the service.

        Returns:
            pandas.DataFrame:
                A DataFrame containing the generated building load profile.
                The index represents time steps according to the chosen resolution.
        """
        payload = {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "resolution_minutes": int(resolution.total_seconds() // 60),
            "building_usage": building_usage,
            "yearly_energy_kwh": yearly_energy_kwh,
            "generation_method": "semi_markov",
            "working_days": working_days
        }
        data = self._post("/generate-building-profile", payload)
        return pd.DataFrame(data)

    generate_blpg_profile = generate_building_profile

    @beartype
    def generate_charging_point_profile(
            self,
            start: datetime,
            end: datetime,
            resolution: timedelta = timedelta(hours=1),
            coordinates: None | tuple[float, float] = None,
            power_nom_kw: None | float | tuple[float, float] = None,
            charging_technology: None | str = None,
    ) -> pd.DataFrame:
        """
    Generate a charging point load profile using the IEH CPLPG
    (Charging Point Load Profile Generator) service.

    The method sends the specified parameters to the backend service and
    returns the resulting load profile as a pandas DataFrame.

    Args:
        start (datetime):
            Start timestamp of the charging point profile (inclusive).

        end (datetime):
            End timestamp of the charging point profile (exclusive).

        resolution (timedelta, optional):
            Temporal resolution of the generated profile.
            Defaults to 1 hour.

        coordinates (tuple[float, float] | None, optional):
            Geographic coordinates of the charging point given as
            ``(latitude, longitude)`` in EPSG:4326 (WGS84).
            If ``None``, a default or aggregated location is used by the service.
            Note that only coordinates in Baden-Wuerttemberg are supported.

        power_nom_kw (float | tuple[float, float] | None, optional):
            Nominal power of the charging point in kilowatts.

            - If a single float is provided, this value is used directly.
            - If a tuple ``(min_kw, max_kw)`` is provided, the value is interpreted
              as a continuous range between the two bounds (inclusive).
            - If ``None``, the service default configuration is used.

        charging_technology (str | None, optional):
            Charging technology of the charging point.
            Supported values are:

            - ``"AC"``: AC charging points (Type 2 or Schuko connector)
            - ``"DC"``: DC charging points (CCS or CHAdeMO connector)

            If ``None``, the charging technology is inferred or defaults are used.

    Returns:
        pandas.DataFrame:
            A DataFrame containing the generated charging point load profile.
            The index represents time steps according to the chosen resolution.
    """
        if power_nom_kw is not None and isinstance(power_nom_kw, tuple):
            if len(power_nom_kw) != 2 or power_nom_kw[0] > power_nom_kw[1]:
                raise ValueError(
                    "power_nom_kw must be a float or a tuple (min_kw, max_kw) with min_kw <= max_kw."
                )
        else:
            power_nom_kw = (power_nom_kw, power_nom_kw)
        payload = {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "resolution_minutes": int(resolution.total_seconds() // 60),
            "coordinates": coordinates,
            "power_range_lower": power_nom_kw[0],
            "power_range_upper": power_nom_kw[1],
            "charging_technology": charging_technology
        }
        data = self._post("/generate-charging-profile", payload)
        return pd.DataFrame(data)

    generate_cplpg_profile = generate_charging_point_profile
