import os
from datetime import datetime, timedelta
from typing import Literal
from collections.abc import Iterable
from beartype import beartype

from dotenv import load_dotenv
import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

from ieh_client.validation.validation import validate_building_profile_input, validate_country_holidays, \
    validate_subdivision_holidays

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import holidays
except ModuleNotFoundError:  # Optional dependency in minimal environments.
    holidays = None


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
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 422:
                detail = e.response.json().get("detail", [])
                if isinstance(detail, list):
                    error_messages = [
                        f"Field '{' -> '.join(map(str, err['loc']))}': {err['msg']} (Received: {err.get('input')})"
                        for err in detail
                    ]
                    error_str = "; ".join(error_messages)
                    raise ValueError(f"Validation Failed: {error_str}")
                else:
                    raise ValueError(f"API Error: {detail}")

            raise ConnectionError(f"Request failed with status {e.response.status_code}: {e.response.text}")

        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Network/Transport error: {e}")

        return response.json()

    @staticmethod
    def _process_response(data: dict) -> pd.DataFrame:
        df = pd.DataFrame(data)
        if "timestamp" in df.keys():
            df.set_index("timestamp", inplace=True)
        return df


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
        """Generate a building load profile via the BLPG endpoint.

        Args:
            start (datetime): Start timestamp (inclusive).
            end (datetime): End timestamp (exclusive).
            resolution (timedelta, optional): Time resolution of the output profile.
                Defaults to ``timedelta(hours=1)``.
            building_usage (Literal[...] | Iterable[Literal[...]], optional):
                Building usage class or multiple classes. Allowed values are
                ``"agriculture"``, ``"household"``, ``"business"``, and
                ``"industrial"``.
            yearly_energy_kwh (float | Iterable[float], optional):
                Annual energy demand in kWh. If an iterable is provided,
                ``building_usage`` must also be an iterable of identical length.
            working_days (Iterable[int | Literal[...]] | None, optional):
                Active weekdays as integers (``0`` = Monday, ..., ``6`` = Sunday)
                or names (``"monday"`` ... ``"sunday"``, ``"public_holiday"``).

        Returns:
            pd.DataFrame: Generated load profile time series.

        Raises:
            ValueError: If input validation fails or the API rejects the payload.
            ConnectionError: If the request fails due to HTTP or transport issues.

        Examples:
            ```python
            from datetime import datetime, timedelta
            from ieh_client import ProfileAPIClient

            client = ProfileAPIClient(api_key="your-key")
            df = client.generate_building_profile(
                start=datetime(2026, 1, 1),
                end=datetime(2026, 1, 2),
                resolution=timedelta(minutes=15),
                building_usage="household",
                yearly_energy_kwh=3500.0,
                working_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
            )
            ```
        """
        validate_building_profile_input(building_usage=building_usage, yearly_energy_kwh=yearly_energy_kwh)
        payload = {
            "start": start.strftime("%Y-%m-%d %H:%M:%S"),
            "end": end.strftime("%Y-%m-%d %H:%M:%S"),
            "resolution_minutes": int(resolution.total_seconds() // 60),
            "building_usage": building_usage,
            "yearly_energy_kwh": yearly_energy_kwh,
            "working_days": working_days
        }
        data = self._post("/generate-building-profile", payload)
        return self._process_response(data)

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
        """Generate a charging-point load profile via the CPLPG endpoint.

        Args:
            start (datetime): Start timestamp (inclusive).
            end (datetime): End timestamp (exclusive).
            resolution (timedelta, optional): Time resolution of the output profile.
                Defaults to ``timedelta(hours=1)``.
            coordinates (tuple[float, float] | None, optional):
                Charging-point coordinates as ``(latitude, longitude)``.
            power_nom_kw (float | tuple[float, float] | None, optional):
                Nominal power in kW. A tuple is interpreted as
                ``(min_kw, max_kw)``.
            charging_technology (str | None, optional):
                Charging technology (typically ``"AC"`` or ``"DC"``).

        Returns:
            pd.DataFrame: Generated charging-point load profile.

        Raises:
            ValueError: If ``power_nom_kw`` tuple bounds are invalid.
            TypeError: If ``coordinates`` is ``None`` (current implementation
                expects indexable coordinates).
            ConnectionError: If the request fails due to HTTP or transport issues.

        Examples:
            ```python
            from datetime import datetime, timedelta
            from ieh_client import ProfileAPIClient

            client = ProfileAPIClient(api_key="your-key")
            df = client.generate_charging_point_profile(
                start=datetime(2026, 1, 1),
                end=datetime(2026, 1, 2),
                resolution=timedelta(minutes=30),
                coordinates=(48.7784, 9.1800),
                power_nom_kw=(11.0, 22.0),
                charging_technology="AC",
            )
            ```
        """
        if power_nom_kw is not None and isinstance(power_nom_kw, tuple):
            if len(power_nom_kw) != 2 or power_nom_kw[0] > power_nom_kw[1]:
                raise ValueError(
                    "power_nom_kw must be a float or a tuple (min_kw, max_kw) with min_kw <= max_kw."
                )
        else:
            power_nom_kw = (power_nom_kw, power_nom_kw)
        payload = {
            "start": start.strftime("%Y-%m-%d %H:%M:%S"),
            "end": end.strftime("%Y-%m-%d %H:%M:%S"),
            "resolution_minutes": int(resolution.total_seconds() // 60),
            "latitude": coordinates[0],
            "longitude": coordinates[1],
            "power_range_lower": power_nom_kw[0],
            "power_range_upper": power_nom_kw[1],
            "charging_technology": charging_technology,
            "ignore_map": False
        }
        data = self._post("/generate-charging-profile", payload)
        return self._process_response(data)

    generate_cplpg_profile = generate_charging_point_profile

    @beartype
    def generate_truck_profile(
            self,
            start: datetime,
            end: datetime,
            resolution: timedelta = timedelta(hours=1),
            n_trucks: int = 1,
            location_type: Literal[
                "distribution_center",
                "general_cargo_depot",
                "cep_depot",
                "shipping_center",
                "warehouse",
                "rest_stop",
            ] = "distribution_center",
            power_nom_charging_point_kw: float = 150,
            charging_mode: Literal["AC", "DC"] | None = None,
            charging_efficiency: float = 0.95,
            soc_cc_to_cv: float = 0.8,
            switch_off_power_kw: float = 1.0,
            min_charging_duration_minutes: int = 5,
            country: str = "DE",
            subdiv: str = "BW",
    ) -> pd.DataFrame:
        """Generate a truck charging profile via the TLPG endpoint.

        Args:
            start (datetime): Start timestamp (inclusive).
            end (datetime): End timestamp (exclusive).
            resolution (timedelta, optional): Time resolution of the output profile.
                Defaults to ``timedelta(hours=1)``.
            n_trucks (int, optional): Number of trucks in the simulation.
                Defaults to ``1``.
            location_type (Literal[...], optional): Logistics site type. Defaults
                to ``"distribution_center"``.
            power_nom_charging_point_kw (float, optional): Nominal charging power
                in kW. Defaults to ``150``.
            charging_mode (Literal["AC", "DC"] | None, optional): Charging mode
                selector. Defaults to ``None``.
            charging_efficiency (float, optional): Charging efficiency factor.
                Defaults to ``0.95``.
            soc_cc_to_cv (float, optional): SOC threshold for CC-to-CV transition.
                Defaults to ``0.8``.
            switch_off_power_kw (float, optional): Charging stop threshold in kW.
                Defaults to ``1.0``.
            min_charging_duration_minutes (int, optional): Minimum charging event
                duration in minutes. Defaults to ``5``.
            country (str, optional): Country code for holiday handling.
                Defaults to ``"DE"``.
            subdiv (str, optional): Subdivision code for holiday handling.
                Defaults to ``"BW"``.

        Returns:
            pd.DataFrame: Generated truck charging load profile.

        Raises:
            ValueError: If country/subdivision holiday inputs are invalid or the
                API rejects the payload.
            ConnectionError: If the request fails due to HTTP or transport issues.

        Examples:
            ```python
            from datetime import datetime, timedelta
            from ieh_client import ProfileAPIClient

            client = ProfileAPIClient(api_key="your-key")
            df = client.generate_truck_profile(
                start=datetime(2026, 1, 1),
                end=datetime(2026, 1, 2),
                resolution=timedelta(minutes=15),
                n_trucks=25,
                location_type="warehouse",
                power_nom_charging_point_kw=300.0,
                charging_mode="DC",
            )
            ```
        """
        if country != "DE":
            validate_country_holidays(country)
        if subdiv != "BW":
            validate_subdivision_holidays(country, subdiv)
        payload = {
            "start": start.strftime("%Y-%m-%d %H:%M:%S"),
            "end": end.strftime("%Y-%m-%d %H:%M:%S"),
            "resolution_minutes": int(resolution.total_seconds() // 60),
            "n_trucks": n_trucks,
            "location_type": location_type,
            "power_nom_charging_point_kw": power_nom_charging_point_kw,
            "charging_mode": charging_mode,
            "charging_efficiency": charging_efficiency,
            "soc_cc_to_cv": soc_cc_to_cv,
            "switch_off_power_kw": switch_off_power_kw,
            "min_charging_duration_minutes": min_charging_duration_minutes,
            "country": country,
            "subdiv": subdiv
        }
        data = self._post("/generate-truck-profile", payload)
        return self._process_response(data)

    generate_tlpg_profile = generate_truck_profile
