import unittest
import sys
import types

# Lightweight dependency stubs so tests can run in minimal environments.
if "beartype" not in sys.modules:
    beartype_stub = types.ModuleType("beartype")
    beartype_stub.beartype = lambda func: func
    sys.modules["beartype"] = beartype_stub

if "dotenv" not in sys.modules:
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda *args, **kwargs: None
    sys.modules["dotenv"] = dotenv_stub

from ieh_client.validation.validation import validate_building_profile_input


class TestValidateBuildingProfileInput(unittest.TestCase):
    def test_scalars_are_valid(self):
        validate_building_profile_input("household", 1000.0)

    def test_scalar_and_sequence_raise_type_error(self):
        with self.assertRaises(TypeError):
            validate_building_profile_input("household", [1000.0, 2000.0])

    def test_sequence_and_scalar_raise_type_error(self):
        with self.assertRaises(TypeError):
            validate_building_profile_input(["household", "business"], 1000.0)

    def test_non_sized_iterables_raise_type_error(self):
        usage_gen = (x for x in ["household", "business"])
        energy_gen = (x for x in [1000.0, 2000.0])
        with self.assertRaises(TypeError):
            validate_building_profile_input(usage_gen, energy_gen)

    def test_length_mismatch_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_building_profile_input(["household", "business"], [1000.0])

    def test_equal_length_sequences_are_valid(self):
        validate_building_profile_input(
            ["household", "business"],
            [1000.0, 2500.0],
        )


if __name__ == "__main__":
    unittest.main()
