# Client Usage

This page explains how to initialize and use `ProfileAPIClient` before calling a specific profile generator.

## 1. Initialize the client

```python
from ieh_client import ProfileAPIClient

client = ProfileAPIClient(api_key="your-api-key")
```

You can now call generator methods such as:

- `generate_truck_profile(...)`
- `generate_building_profile(...)`
- `generate_charging_point_profile(...)`

## 2. Authentication options

The client supports two ways to provide the API key:

1. Directly in code via `api_key=...`
2. Via environment variable `PROFILE_API_KEY` (including `.env` support)

### Option A: Use `.env` (recommended)

Create a `.env` file in your project root:

```dotenv
PROFILE_API_KEY=your-api-key
```

Then initialize without passing `api_key`:

```python
from ieh_client import ProfileAPIClient

client = ProfileAPIClient()
```

### Option B: Use environment variable

```bash
# Linux/macOS
export PROFILE_API_KEY="your-api-key"

# Windows PowerShell
$env:PROFILE_API_KEY="your-api-key"
```

Then:

```python
client = ProfileAPIClient()
```

### Option C: Pass key directly

```python
client = ProfileAPIClient(api_key="your-api-key")
```

## 3. How to get an API key

To request an API key, contact:

- `johannes.beck@ieh.uni-stuttgart.de`

## 4. Important: key scope may be generator-specific

API keys are not necessarily valid for all profile generators.
Depending on your permission setup, a key may only be allowed for specific generators (for example only for the truck profile generator).

If a request is rejected for one generator but works for another, your key likely has limited scope.
