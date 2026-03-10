import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import sys
import types

import requests

# Lightweight dependency stubs so tests can run in minimal environments.
if "beartype" not in sys.modules:
    beartype_stub = types.ModuleType("beartype")
    beartype_stub.beartype = lambda func: func
    sys.modules["beartype"] = beartype_stub

if "dotenv" not in sys.modules:
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda *args, **kwargs: None
    sys.modules["dotenv"] = dotenv_stub

from ieh_client.client import client as client_module


def _response(*, status_code=200, json_data=None, text="OK"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.json.return_value = {} if json_data is None else json_data
    resp.raise_for_status.return_value = None
    return resp


class TestProfileAPIClientInit(unittest.TestCase):
    @patch.object(client_module, "load_dotenv", autospec=True)
    def test_init_uses_explicit_api_key(self, _load_dotenv):
        with patch.dict("os.environ", {"PROFILE_API_KEY": "env-key"}, clear=True):
            with patch.object(client_module.requests, "Session", autospec=True) as session_cls:
                session_cls.return_value = MagicMock()
                client = client_module.ProfileAPIClient(api_key="arg-key")
        self.assertEqual(client.api_key, "arg-key")
        self.assertEqual(client.headers["x-api-key"], "arg-key")

    @patch.object(client_module, "load_dotenv", autospec=True)
    def test_init_uses_env_api_key(self, _load_dotenv):
        with patch.dict("os.environ", {"PROFILE_API_KEY": "env-key"}, clear=True):
            with patch.object(client_module.requests, "Session", autospec=True) as session_cls:
                session_cls.return_value = MagicMock()
                client = client_module.ProfileAPIClient()
        self.assertEqual(client.api_key, "env-key")
        self.assertEqual(client.headers["x-api-key"], "env-key")

    @patch.object(client_module, "load_dotenv", autospec=True)
    def test_init_raises_without_api_key(self, _load_dotenv):
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(client_module.requests, "Session", autospec=True) as session_cls:
                session_cls.return_value = MagicMock()
                with self.assertRaises(ValueError) as ctx:
                    client_module.ProfileAPIClient()
        self.assertIn("PROFILE_API_KEY not found", str(ctx.exception))


class TestPostAndResponseProcessing(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict("os.environ", {"PROFILE_API_KEY": "test-key"}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

        self.load_dotenv = patch.object(client_module, "load_dotenv", autospec=True)
        self.load_dotenv.start()
        self.addCleanup(self.load_dotenv.stop)

    def test_post_success(self):
        session = MagicMock()
        session.post.return_value = _response(json_data={"ok": True})

        with patch.object(client_module.requests, "Session", autospec=True, return_value=session):
            client = client_module.ProfileAPIClient(timeout=5)
            result = client._post("/endpoint", {"a": 1})

        self.assertEqual(result, {"ok": True})
        session.post.assert_called_once()
        _, kwargs = session.post.call_args
        self.assertEqual(kwargs["timeout"], 5)
        self.assertEqual(kwargs["json"], {"a": 1})
        self.assertFalse(kwargs["verify"])

    def test_post_422_with_detail_list(self):
        resp = _response(
            status_code=422,
            json_data={
                "detail": [
                    {"loc": ["body", "start"], "msg": "Invalid datetime", "input": "x"},
                    {"loc": ["body", "n_trucks"], "msg": "Input should be >= 1", "input": 0},
                ]
            },
            text="unprocessable",
        )
        http_error = requests.exceptions.HTTPError("422")
        http_error.response = resp
        resp.raise_for_status.side_effect = http_error

        session = MagicMock()
        session.post.return_value = resp

        with patch.object(client_module.requests, "Session", autospec=True, return_value=session):
            client = client_module.ProfileAPIClient()
            with self.assertRaises(ValueError) as ctx:
                client._post("/endpoint", {"a": 1})

        message = str(ctx.exception)
        self.assertIn("Validation Failed", message)
        self.assertIn("start", message)
        self.assertIn("n_trucks", message)

    def test_post_422_with_string_detail(self):
        resp = _response(status_code=422, json_data={"detail": "Invalid payload"}, text="unprocessable")
        http_error = requests.exceptions.HTTPError("422")
        http_error.response = resp
        resp.raise_for_status.side_effect = http_error

        session = MagicMock()
        session.post.return_value = resp

        with patch.object(client_module.requests, "Session", autospec=True, return_value=session):
            client = client_module.ProfileAPIClient()
            with self.assertRaises(ValueError) as ctx:
                client._post("/endpoint", {"a": 1})
        self.assertIn("API Error: Invalid payload", str(ctx.exception))

    def test_post_non_422_http_error(self):
        resp = _response(status_code=500, json_data={"x": 1}, text="server down")
        http_error = requests.exceptions.HTTPError("500")
        http_error.response = resp
        resp.raise_for_status.side_effect = http_error

        session = MagicMock()
        session.post.return_value = resp

        with patch.object(client_module.requests, "Session", autospec=True, return_value=session):
            client = client_module.ProfileAPIClient()
            with self.assertRaises(ConnectionError) as ctx:
                client._post("/endpoint", {"a": 1})
        self.assertIn("Request failed with status 500", str(ctx.exception))

    def test_post_request_exception(self):
        session = MagicMock()
        session.post.side_effect = requests.exceptions.RequestException("network")

        with patch.object(client_module.requests, "Session", autospec=True, return_value=session):
            client = client_module.ProfileAPIClient()
            with self.assertRaises(ConnectionError) as ctx:
                client._post("/endpoint", {"a": 1})
        self.assertIn("Network/Transport error", str(ctx.exception))

    def test_process_response_sets_timestamp_index(self):
        data = [
            {"timestamp": "2026-01-01 00:00:00", "p_kw": 12.5},
            {"timestamp": "2026-01-01 01:00:00", "p_kw": 9.0},
        ]
        df = client_module._APIClient._process_response(data)
        self.assertEqual(df.index.name, "timestamp")
        self.assertEqual(list(df.columns), ["p_kw"])

    def test_process_response_without_timestamp_keeps_default_index(self):
        data = [{"p_kw": 12.5}, {"p_kw": 9.0}]
        df = client_module._APIClient._process_response(data)
        self.assertIsNone(df.index.name)
        self.assertEqual(list(df.columns), ["p_kw"])


class TestGeneratorMethods(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict("os.environ", {"PROFILE_API_KEY": "test-key"}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

        self.load_dotenv = patch.object(client_module, "load_dotenv", autospec=True)
        self.load_dotenv.start()
        self.addCleanup(self.load_dotenv.stop)

        with patch.object(client_module.requests, "Session", autospec=True) as session_cls:
            session_cls.return_value = MagicMock()
            self.client = client_module.ProfileAPIClient()

    def test_generate_building_profile_payload(self):
        start = datetime(2026, 1, 1, 0, 0, 0)
        end = datetime(2026, 1, 2, 0, 0, 0)
        resolution = timedelta(minutes=30)

        with patch.object(client_module, "validate_building_profile_input", autospec=True) as validate_mock:
            with patch.object(self.client, "_post", autospec=True, return_value=[{"p_kw": 1.0}]) as post_mock:
                df = self.client.generate_building_profile(
                    start=start,
                    end=end,
                    resolution=resolution,
                    building_usage="household",
                    yearly_energy_kwh=3500.0,
                    working_days=["monday", "tuesday"],
                )

        validate_mock.assert_called_once_with(building_usage="household", yearly_energy_kwh=3500.0)
        endpoint, payload = post_mock.call_args.args
        self.assertEqual(endpoint, "/generate-building-profile")
        self.assertEqual(payload["start"], "2026-01-01 00:00:00")
        self.assertEqual(payload["end"], "2026-01-02 00:00:00")
        self.assertEqual(payload["resolution_minutes"], 30)
        self.assertEqual(payload["generation_method"], "semi_markov")
        self.assertEqual(payload["working_days"], ["monday", "tuesday"])
        self.assertEqual(list(df.columns), ["p_kw"])

    def test_generate_charging_point_profile_payload_scalar_power(self):
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 2)

        with patch.object(self.client, "_post", autospec=True, return_value=[{"p_kw": 1.0}]) as post_mock:
            self.client.generate_charging_point_profile(
                start=start,
                end=end,
                resolution=timedelta(hours=1),
                coordinates=(48.7784, 9.18),
                power_nom_kw=22.0,
                charging_technology="AC",
            )

        endpoint, payload = post_mock.call_args.args
        self.assertEqual(endpoint, "/generate-charging-profile")
        self.assertEqual(payload["latitude"], 48.7784)
        self.assertEqual(payload["longitude"], 9.18)
        self.assertEqual(payload["power_range_lower"], 22.0)
        self.assertEqual(payload["power_range_upper"], 22.0)
        self.assertEqual(payload["resolution_minutes"], 60)
        self.assertEqual(payload["charging_technology"], "AC")

    def test_generate_charging_point_profile_invalid_power_tuple(self):
        with self.assertRaises(ValueError):
            self.client.generate_charging_point_profile(
                start=datetime(2026, 1, 1),
                end=datetime(2026, 1, 2),
                coordinates=(48.7784, 9.18),
                power_nom_kw=(50.0, 10.0),
            )

    def test_generate_truck_profile_payload(self):
        start = datetime(2026, 1, 1, 0, 0, 0)
        end = datetime(2026, 1, 2, 0, 0, 0)

        with patch.object(self.client, "_post", autospec=True, return_value=[{"p_kw": 1.0}]) as post_mock:
            self.client.generate_truck_profile(
                start=start,
                end=end,
                resolution=timedelta(minutes=15),
                n_trucks=10,
                location_type="warehouse",
                power_nom_charging_point_kw=300.0,
                charging_mode="DC",
                country="DE",
                subdiv="BW",
            )

        endpoint, payload = post_mock.call_args.args
        self.assertEqual(endpoint, "/generate-truck-profile")
        self.assertEqual(payload["start"], "2026-01-01 00:00:00")
        self.assertEqual(payload["end"], "2026-01-02 00:00:00")
        self.assertEqual(payload["resolution_minutes"], 15)
        self.assertEqual(payload["n_trucks"], 10)
        self.assertEqual(payload["location_type"], "warehouse")
        self.assertEqual(payload["power_nom_charging_point_kw"], 300.0)
        self.assertEqual(payload["charging_mode"], "DC")

    def test_generate_truck_profile_calls_country_validation_for_non_default(self):
        with patch.object(client_module, "validate_country_holidays", autospec=True) as validate_country_mock:
            with patch.object(client_module, "validate_subdivision_holidays", autospec=True) as validate_subdiv_mock:
                with patch.object(self.client, "_post", autospec=True, return_value=[{"p_kw": 1.0}]):
                    self.client.generate_truck_profile(
                        start=datetime(2026, 1, 1),
                        end=datetime(2026, 1, 2),
                        country="US",
                        subdiv="CA",
                    )

        validate_country_mock.assert_called_once_with("US")
        validate_subdiv_mock.assert_called_once_with("US", "CA")

    def test_aliases_reference_primary_methods(self):
        self.assertIs(
            client_module.ProfileAPIClient.generate_blpg_profile,
            client_module.ProfileAPIClient.generate_building_profile,
        )
        self.assertIs(
            client_module.ProfileAPIClient.generate_cplpg_profile,
            client_module.ProfileAPIClient.generate_charging_point_profile,
        )
        self.assertIs(
            client_module.ProfileAPIClient.generate_tlpg_profile,
            client_module.ProfileAPIClient.generate_truck_profile,
        )


if __name__ == "__main__":
    unittest.main()
