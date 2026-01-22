import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import requests


from ieh_client.client import client


def make_response(*, status_code=200, json_data=None, text="OK"):
    """
    Create a lightweight response-like mock that behaves like requests.Response
    for the parts your client uses.
    """
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    if json_data is None:
        json_data = {}
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


class TestAPIClientInit(unittest.TestCase):
    @patch.object(client, "load_dotenv", autospec=True)
    def test_init_uses_explicit_api_key_over_env(self, _load_dotenv):
        with patch.dict("os.environ", {"PROFILE_API_KEY": "env-key"}, clear=True):
            with patch.object(client.requests, "Session", autospec=True) as session_cls:
                session_cls.return_value = MagicMock()
                c = client.ProfileAPIClient(api_key="arg-key")
                self.assertEqual(c.api_key, "arg-key")
                self.assertEqual(c.headers["x-api-key"], "arg-key")

    @patch.object(client, "load_dotenv", autospec=True)
    def test_init_uses_env_if_no_explicit_key(self, _load_dotenv):
        with patch.dict("os.environ", {"PROFILE_API_KEY": "env-key"}, clear=True):
            with patch.object(client.requests, "Session", autospec=True) as session_cls:
                session_cls.return_value = MagicMock()
                c = client.ProfileAPIClient()
                self.assertEqual(c.api_key, "env-key")
                self.assertEqual(c.headers["x-api-key"], "env-key")

    @patch.object(client, "load_dotenv", autospec=True)
    def test_init_raises_if_no_key(self, _load_dotenv):
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(client.requests, "Session", autospec=True) as session_cls:
                session_cls.return_value = MagicMock()
                with self.assertRaises(ValueError) as ctx:
                    client.ProfileAPIClient()
                self.assertIn("PROFILE_API_KEY not found", str(ctx.exception))


class TestPostHelper(unittest.TestCase):
    def setUp(self):
        # Ensure init succeeds
        self.env = patch.dict("os.environ", {"PROFILE_API_KEY": "k"}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

        self.load_dotenv = patch.object(client, "load_dotenv", autospec=True)
        self.load_dotenv.start()
        self.addCleanup(self.load_dotenv.stop)

    def test_post_success_returns_json(self):
        session = MagicMock()
        session.post.return_value = make_response(json_data={"a": 1})

        with patch.object(client.requests, "Session", autospec=True, return_value=session):
            c = client.ProfileAPIClient(timeout=7)
            out = c._post("/x", {"p": 1})

        self.assertEqual(out, {"a": 1})
        session.post.assert_called_once()
        args, kwargs = session.post.call_args
        self.assertIn("/x", args[0])  # url
        self.assertEqual(kwargs["json"], {"p": 1})
        self.assertEqual(kwargs["headers"]["x-api-key"], "k")
        self.assertEqual(kwargs["timeout"], 7)
        self.assertFalse(kwargs["verify"])

    def test_post_http_422_list_detail_becomes_valueerror(self):
        # Build response that raises HTTPError with response attached
        resp = make_response(
            status_code=422,
            json_data={
                "detail": [
                    {"loc": ["body", "yearly_energy_kwh"], "msg": "Input should be a valid number", "input": "x"},
                    {"loc": ["body", "start"], "msg": "Invalid datetime", "input": "nope"},
                ]
            },
            text="unprocessable",
        )
        http_err = requests.exceptions.HTTPError("422")
        http_err.response = resp
        resp.raise_for_status.side_effect = http_err

        session = MagicMock()
        session.post.return_value = resp

        with patch.object(client.requests, "Session", autospec=True, return_value=session):
            c = client.ProfileAPIClient()
            with self.assertRaises(ValueError) as ctx:
                c._post("/x", {"p": 1})

        msg = str(ctx.exception)
        self.assertIn("Validation Failed", msg)
        self.assertIn("yearly_energy_kwh", msg)
        self.assertIn("Input should be a valid number", msg)

    def test_post_http_422_non_list_detail_becomes_valueerror(self):
        resp = make_response(
            status_code=422,
            json_data={"detail": "Something wrong"},
            text="unprocessable",
        )
        http_err = requests.exceptions.HTTPError("422")
        http_err.response = resp
        resp.raise_for_status.side_effect = http_err

        session = MagicMock()
        session.post.return_value = resp

        with patch.object(client.requests, "Session", autospec=True, return_value=session):
            c = client.ProfileAPIClient()
            with self.assertRaises(ValueError) as ctx:
                c._post("/x", {"p": 1})
        self.assertIn("API Error", str(ctx.exception))
        self.assertIn("Something wrong", str(ctx.exception))

    def test_post_http_other_status_becomes_connectionerror(self):
        resp = make_response(status_code=500, json_data={"x": 1}, text="server down")
        http_err = requests.exceptions.HTTPError("500")
        http_err.response = resp
        resp.raise_for_status.side_effect = http_err

        session = MagicMock()
        session.post.return_value = resp

        with patch.object(client.requests, "Session", autospec=True, return_value=session):
            c = client.ProfileAPIClient()
            with self.assertRaises(ConnectionError) as ctx:
                c._post("/x", {"p": 1})

        self.assertIn("Request failed with status 500", str(ctx.exception))
        self.assertIn("server down", str(ctx.exception))

    def test_post_request_exception_becomes_connectionerror(self):
        session = MagicMock()
        session.post.side_effect = requests.exceptions.RequestException("network")

        with patch.object(client.requests, "Session", autospec=True, return_value=session):
            c = client.ProfileAPIClient()
            with self.assertRaises(ConnectionError) as ctx:
                c._post("/x", {"p": 1})
        self.assertIn("Network/Transport error", str(ctx.exception))


class TestValidateBuildingProfileInput(unittest.TestCase):
    def test_scalar_scalar_ok(self):
        client._validate_building_profile_input("household", 1000.0)

    def test_scalar_sequence_typeerror(self):
        with self.assertRaises(TypeError):
            client._validate_building_profile_input("household", [1000.0, 2000.0])

    def test_sequence_scalar_typeerror(self):
        with self.assertRaises(TypeError):
            client._validate_building_profile_input(["household", "business"], 1000.0)

    def test_sequence_must_be_sized(self):
        # generator is Iterable but not Sized -> should raise TypeError in your implementation
        usages = (u for u in ["household", "business"])
        energies = (e for e in [1000.0, 2000.0])
        with self.assertRaises(TypeError):
            client._validate_building_profile_input(usages, energies)

    def test_sequence_length_mismatch_valueerror(self):
        with self.assertRaises(ValueError) as ctx:
            client._validate_building_profile_input(
                ["household", "business"],
                [1000.0],
            )
        self.assertIn("must have the same length", str(ctx.exception))


class TestProfileMethods(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict("os.environ", {"PROFILE_API_KEY": "k"}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

        self.load_dotenv = patch.object(client, "load_dotenv", autospec=True)
        self.load_dotenv.start()
        self.addCleanup(self.load_dotenv.stop)

        # Use a real client but mock _post for profile methods
        with patch.object(client.requests, "Session", autospec=True) as session_cls:
            session_cls.return_value = MagicMock()
            self.client = client.ProfileAPIClient()

    def test_generate_building_profile_payload_and_dataframe(self):
        start = datetime(2026, 1, 1, 0, 0, 0)
        end = datetime(2026, 1, 2, 0, 0, 0)
        resolution = timedelta(minutes=30)

        fake_data = [{"t": "x", "p": 1}, {"t": "y", "p": 2}]
        with patch.object(self.client, "_post", autospec=True, return_value=fake_data) as post_mock:
            df = self.client.generate_building_profile(
                start=start,
                end=end,
                resolution=resolution,
                building_usage="household",
                yearly_energy_kwh=1234.5,
                working_days=["monday", "tuesday"],
            )

        # verify payload
        post_mock.assert_called_once()
        endpoint, payload = post_mock.call_args.args
        self.assertEqual(endpoint, "/generate-building-profile")
        self.assertEqual(payload["start"], "2026-01-01 00:00:00")
        self.assertEqual(payload["end"], "2026-01-02 00:00:00")
        self.assertEqual(payload["resolution_minutes"], 30)
        self.assertEqual(payload["building_usage"], "household")
        self.assertEqual(payload["yearly_energy_kwh"], 1234.5)
        self.assertEqual(payload["generation_method"], "semi_markov")
        self.assertEqual(payload["working_days"], ["monday", "tuesday"])

        # verify DataFrame content
        self.assertEqual(list(df.columns), ["t", "p"])
        self.assertEqual(len(df), 2)

    def test_generate_building_profile_calls_validation(self):
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 2)

        with patch.object(client, "_validate_building_profile_input", autospec=True) as val_mock:
            with patch.object(self.client, "_post", autospec=True, return_value=[]):
                self.client.generate_building_profile(
                    start=start, end=end, building_usage=["household"], yearly_energy_kwh=[1000.0]
                )
        val_mock.assert_called_once()

    def test_generate_blpg_profile_is_alias(self):
        self.assertIs(
            client.ProfileAPIClient.generate_blpg_profile,
            client.ProfileAPIClient.generate_building_profile,
        )

    def test_generate_charging_point_profile_power_tuple_validation(self):
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 2)

        with self.assertRaises(ValueError):
            self.client.generate_charging_point_profile(
                start=start,
                end=end,
                coordinates=(48.77, 9.18),
                power_nom_kw=(50.0, 10.0),  # min > max
            )

    def test_generate_charging_point_profile_payload_power_range_from_scalar(self):
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 2)

        with patch.object(self.client, "_post", autospec=True, return_value=[{"p": 1}]) as post_mock:
            self.client.generate_charging_point_profile(
                start=start,
                end=end,
                resolution=timedelta(hours=1),
                coordinates=(48.77, 9.18),
                power_nom_kw=22.0,
                charging_technology="AC",
            )

        endpoint, payload = post_mock.call_args.args
        self.assertEqual(endpoint, "/generate-charging-profile")
        self.assertEqual(payload["latitude"], 48.77)
        self.assertEqual(payload["longitude"], 9.18)
        self.assertEqual(payload["power_range_lower"], 22.0)
        self.assertEqual(payload["power_range_upper"], 22.0)
        self.assertEqual(payload["charging_technology"], "AC")
        self.assertEqual(payload["resolution_minutes"], 60)

    def test_generate_charging_point_profile_payload_power_range_from_tuple(self):
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 2)

        with patch.object(self.client, "_post", autospec=True, return_value=[{"p": 1}]) as post_mock:
            self.client.generate_charging_point_profile(
                start=start,
                end=end,
                coordinates=(48.77, 9.18),
                power_nom_kw=(10.0, 50.0),
                charging_technology="DC",
            )

        endpoint, payload = post_mock.call_args.args
        self.assertEqual(payload["power_range_lower"], 10.0)
        self.assertEqual(payload["power_range_upper"], 50.0)
        self.assertEqual(payload["charging_technology"], "DC")

    def test_generate_charging_point_profile_coordinates_none_currently_errors(self):
        # Your current implementation indexes coordinates[0]/[1] unconditionally.
        # This test documents that behavior (TypeError).
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 2)

        with patch.object(self.client, "_post", autospec=True, return_value=[]):
            with self.assertRaises(TypeError):
                self.client.generate_charging_point_profile(
                    start=start,
                    end=end,
                    coordinates=None,  # will fail at coordinates[0]
                )

    def test_generate_cplpg_profile_is_alias(self):
        self.assertIs(
            client.ProfileAPIClient.generate_cplpg_profile,
            client.ProfileAPIClient.generate_charging_point_profile,
        )

    def test_generate_truck_profile_payload(self):
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 2)

        with patch.object(self.client, "_post", autospec=True, return_value=[{"x": 1}]) as post_mock:
            self.client.generate_truck_profile(
                start=start, end=end, resolution=timedelta(minutes=15), n_bet=3, site_type="general_cargo_hub"
            )

        endpoint, payload = post_mock.call_args.args
        self.assertEqual(endpoint, "/generate-truck-profile")
        self.assertEqual(payload["resolution_minutes"], 15)
        self.assertEqual(payload["n_bet"], 3)
        self.assertEqual(payload["site_type"], "general_cargo_hub")

    def test_generate_tlpg_profile_is_alias(self):
        self.assertIs(
            client.ProfileAPIClient.generate_tlpg_profile,
            client.ProfileAPIClient.generate_truck_profile,
        )


if __name__ == "__main__":
    unittest.main()
