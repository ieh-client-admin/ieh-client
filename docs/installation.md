# Installation

## Requirements

- Python `>=3.11`
- An API key for the IEH profile API (`PROFILE_API_KEY`)

## Install from GitHub

```bash
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/ieh-client-admin/ieh-client.git"
```

## Optional extras

Holiday country/subdivision validation:

```bash
python -m pip install "ieh-client[holidays] @ git+https://github.com/ieh-client-admin/ieh-client.git"
```

Plotting support for examples:

```bash
python -m pip install "ieh-client[plot] @ git+https://github.com/ieh-client-admin/ieh-client.git"
```

## Conda example

```bash
conda create -n ieh-client python=3.11 -y
conda activate ieh-client
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/ieh-client-admin/ieh-client.git"
```

## Development install (editable)

```bash
git clone https://github.com/ieh-client-admin/ieh-client.git
cd ieh-client
python -m pip install -e ".[dev,holidays,plot]"
```

## API key setup

Use either an environment variable or a `.env` file in your project root.

```bash
# Linux/macOS
export PROFILE_API_KEY="your-api-key"

# Windows PowerShell
$env:PROFILE_API_KEY="your-api-key"
```

`.env` example:

```dotenv
PROFILE_API_KEY=your-api-key
```
