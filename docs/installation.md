# Installation

## Requirements

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A Steam account with games
- A [Steam Web API key](https://steamcommunity.com/dev/apikey)
- A [MobyGames API key](https://www.mobygames.com/info/api/)

## Install

```bash
git clone https://github.com/dave-tucker/steam-family-collections
cd steam-family-collections
uv sync
```

## Get API keys

### Steam Web API key

1. Log in to Steam and visit [https://steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey)
2. Register a domain name (any value works, e.g. `localhost`)
3. Copy the key shown on the page

### MobyGames API key

1. Create a free account at [MobyGames](https://www.mobygames.com/)
2. Go to your profile settings and generate an API key
3. The free tier allows 360 requests per hour — sufficient for most libraries

## Configure

Copy the example config and fill in your keys:

```bash
cp config.example.toml ~/.config/steam-family-collections/config.toml
```

Then edit the file:

```toml
[steam]
api_key = "YOUR_STEAM_API_KEY"
steam_id = "YOUR_STEAM_ID_64"

[mobygames]
api_key = "YOUR_MOBYGAMES_API_KEY"
```

!!! tip "Finding your Steam ID"
    Your Steam ID (64-bit) can be found at [steamidfinder.com](https://www.steamidfinder.com/) or in the Steam client under Account Details.

## Run

```bash
uv run python main.py
```

Or install as a command:

```bash
uv tool install .
steam-family-collections
```

!!! note "Config file location"
    The app first checks for `config.toml` in the current directory, then falls back to `~/.config/steam-family-collections/config.toml`. This lets you keep per-project configs.
