# Configuration

The config file uses [TOML](https://toml.io/) format. The app looks for it at:

1. `./config.toml` (current directory, checked first)
2. `~/.config/steam-family-collections/config.toml`

A template is generated automatically on first run, or you can copy `config.example.toml`.

## `[app]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `demo` | bool | `false` | Enable [demo mode](demo.md) — loads bundled sample data, no API keys required |

## `[steam]`

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `api_key` | string | Yes | Steam Web API key from [steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey) |
| `steam_id` | string | Yes | Your 64-bit Steam ID |
| `user_id` | string | No | Steam user directory ID (auto-detected when only one account exists) |
| `path` | string | No | Path to Steam data directory (auto-detects Flatpak then native install) |

## `[mobygames]`

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `api_key` | string | Yes | MobyGames API key from your account settings |

## `[ratings]`

Controls how age ratings are selected when a game has ratings from multiple schemes.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `preference` | list of strings | `["bbfc", "pegi", "usk", "esrb"]` | Schemes tried in order; first match wins. Falls back to average of all available ratings. |

### `[ratings.map.*]`

Override or extend the default mapping from rating codes to numeric ages.

```toml
[ratings.map.esrb]
"EC" = 3
"E" = 3
"E10+" = 7
"T" = 12
"M" = 16
"AO" = 18

[ratings.map.bbfc]
"U" = 0
"PG" = 5
"12A" = 12
"12" = 12
"15" = 15
"18" = 18
"R18" = 18
```

Built-in defaults exist for ESRB and BBFC. All other schemes extract the numeric age directly from the rating string (e.g. `"12"` → `12`).

## Full example

```toml
[app]
# demo = true

[steam]
api_key = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
steam_id = "76561198012345678"

[mobygames]
api_key = "YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY"

[ratings]
preference = ["pegi", "bbfc", "esrb"]

[ratings.map.esrb]
"T" = 13
```
