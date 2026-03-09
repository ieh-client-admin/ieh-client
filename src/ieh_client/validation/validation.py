from collections.abc import Iterable, Sized
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import holidays
except ModuleNotFoundError:  # Optional dependency in minimal environments.
    holidays = None



def validate_building_profile_input(
        building_usage: str | Iterable[str],
        yearly_energy_kwh: float | Iterable[float],
) -> None:
    usage_is_seq = not isinstance(building_usage, (str, bytes)) and isinstance(building_usage, Iterable)
    energy_is_seq = not isinstance(yearly_energy_kwh, (str, bytes)) and isinstance(yearly_energy_kwh, Iterable)

    if usage_is_seq != energy_is_seq:
        raise TypeError(
            "building_usage and yearly_energy_kwh must either BOTH be scalars "
            "(str, float) or BOTH be sequences of equal length."
        )

    if usage_is_seq:
        if not isinstance(building_usage, Sized) or not isinstance(yearly_energy_kwh, Sized):
            raise TypeError(
                "When providing sequences, building_usage and yearly_energy_kwh must be sized "
                "(e.g. list/tuple) so their lengths can be compared."
            )

        if len(building_usage) != len(yearly_energy_kwh):  # type: ignore[arg-type]
            raise ValueError(
                "building_usage and yearly_energy_kwh must have the same length when provided as sequences. "
                f"Got len(building_usage)={len(building_usage)} and len(yearly_energy_kwh)={len(yearly_energy_kwh)}."
            )


if holidays is None:
    _SUPPORTED_COUNTRIES = {"DE"}
else:
    _SUPPORTED_COUNTRIES = set(holidays.list_supported_countries())

_OPTIONAL_WARNING_EMITTED: set[str] = set()


def validate_country_holidays(value: str):
    if holidays is None:
        handle_missing_optional_dependency(
            "holidays",
            "Country validation based on holidays metadata",
        )
        return True

    if value not in _SUPPORTED_COUNTRIES:
        allowed = ", ".join(sorted(_SUPPORTED_COUNTRIES))

        raise ValueError(
            f"Invalid value for 'country': {value}. "
            f"Allowed ISO country codes supported by holidays. "
            f"Examples: {allowed[:80]}..."
        )

    return True


def validate_subdivision_holidays(country: str, subdiv: str):
    if holidays is None:
        handle_missing_optional_dependency(
            "holidays",
            "Subdivision validation based on holidays metadata",
        )
        return True

    try:
        holidays.country_holidays(country, subdiv=subdiv)

    except Exception:

        try:
            valid = holidays.country_holidays(country).subdivisions
        except Exception:
            valid = None

        if valid:
            raise ValueError(
                f"Invalid value for 'subdiv': {subdiv}. "
                f"Allowed subdivisions for country '{country}' are: {sorted(valid)}"
            )

        raise ValueError(
            f"Invalid value for 'subdiv': {subdiv} for country '{country}'."
        )

    return True


def handle_missing_optional_dependency(
        dependency_name: str,
        feature_description: str
) -> None:
    if dependency_name != "holidays" or holidays is not None:
        return

    message = (
        f"Optional dependency '{dependency_name}' is not installed. "
        f"{feature_description} will be limited. "
        f"Install it with: pip install {dependency_name}"
    )

    raise ModuleNotFoundError(message)
