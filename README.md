# Steam Family Collections

[![CI](https://github.com/dave-tucker/steam-family-collections/actions/workflows/ci.yml/badge.svg)](https://github.com/dave-tucker/steam-family-collections/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-online-blue)](https://dave-tucker.github.io/steam-family-collections/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

[Documentation](https://dave-tucker.github.io/steam-family-collections/)

![Library screen](docs/assets/screenshots/library.svg)

I have a large Steam library, and I want to share it with my Kids.
Steam offers 2 options:

- Allow all games
- Allow only selected games

The latter is the only sensible option, but there is no way to quickly
filter your library to "just games suitable for ages 12 and below" for
you to add them.

Enter, `steam-family-collections`. A TUI app that helps parents create
age-appropriate Steam game collections for their children. 

- Fetches your Steam library using the Steam API
- Enriches games with age ratings via MobyGames (requires API key)
- Supports multiple rating schemes: PEGI, BBFC, ESRB, USK, and more
- Pushes filtered collections directly into Steam

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- A [Steam API key](https://steamcommunity.com/dev/apikey)
- A [MobyGames API key](https://www.mobygames.com/info/api/)

## Installation

### Via uv (recommended)

```bash
uv tool install git+https://github.com/dave-tucker/steam-family-collections
```

Then run with:

```bash
steam-family-collections
```

### From source

```bash
git clone https://github.com/dave-tucker/steam-family-collections
cd steam-family-collections
uv sync
uv run python main.py
```

## Configuration

The app looks for `config.toml` in the current directory first, then falls back to `~/.config/steam-family-collections/config.toml`.

On first run with no config file present, a template is written to the user config path automatically.

```toml
[steam]
api_key = "YOUR_STEAM_API_KEY"
steam_id = "YOUR_STEAM_ID_64"
# user_id = "12345678"  # optional; auto-detected when only one account exists
# path = "/home/user/.local/share/Steam"  # optional; auto-detects Flatpak then native

[mobygames]
api_key = "YOUR_MOBYGAMES_API_KEY"
```

See `config.example.toml` for the full reference, including `[ratings]` options for configuring rating scheme preference order and custom value maps.

To find your `steam_id`, visit your Steam profile page — the 64-bit ID appears in the URL (e.g. `https://steamcommunity.com/profiles/76561198XXXXXXXXX`).

## Usage

| Key       | Screen     | Action                                  |
|-----------|------------|-----------------------------------------|
| F1        | Main       | Fetch your Steam library                |
| F2        | Main       | Enrich games with age ratings           |
| F3        | Main       | Manage child profiles                   |
| q         | Main       | Quit                                    |
| m         | Library    | Search MobyGames for selected game      |
| e         | Library    | Edit age rating manually                |
| i         | Library    | Set MobyGames ID manually               |
| d         | Library    | Delete rating for selected game         |
| a         | Library    | Add selected game to a child's list     |
| f         | Library    | Cycle filter (all / unrated / ambiguous)|
| Enter     | Children   | Open child's collection                 |
| n         | Children   | New child profile                       |
| e         | Children   | Edit child's max age                    |
| d         | Children   | Delete child profile                    |
| r         | Collection | Remove selected game                    |
| a         | Collection | Add a game manually                     |
| s         | Collection | Sync collection against current ratings |
| p         | Collection | Push collection to Steam                |
| Backspace | Collection | Back to children list                   |

### Workflow

1. **F1 — Fetch Library**: Downloads your owned games from the Steam API.
2. **F2 — Enrich Ratings**: Looks up age ratings for each unrated game via MobyGames. Multiple rating schemes are fetched (PEGI, BBFC, ESRB, etc.) and the best match per your preference order is stored. Press `m` on any game to search MobyGames interactively with an editable search term.
3. **F3 — Manage Children**: Create profiles for each child with a maximum age rating. From a child's profile you can review their filtered game list, sync it as ratings update, and push it to Steam.

Pushing a collection writes a filtered game list into Steam's cloud storage. The Steam directory is auto-detected (Flatpak at `~/.var/app/com.valvesoftware.Steam/data/Steam/` is preferred over native `~/.local/share/Steam/`). A backup of the existing file is created before any write.

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Lint and format
uv run ruff check .
uv run ruff format .
```
