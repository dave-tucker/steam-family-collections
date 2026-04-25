# Steam Family Collections

A terminal UI app that helps parents create age-appropriate Steam game collections for their children, based on PEGI ratings. It fetches your Steam library, enriches games with PEGI ratings via MobyGames, and pushes filtered collections directly into Steam's cloud storage so they appear on your child's account.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- A [Steam API key](https://steamcommunity.com/dev/apikey)
- A [MobyGames API key](https://www.mobygames.com/info/api/)

## Installation

```bash
git clone https://github.com/dtucker/steam-family-collections
cd steam-family-collections
uv sync
```

## Configuration

Copy the example config and fill in your API keys:

```bash
cp config.example.toml config.toml
```

The app looks for `config.toml` in the current directory first, then falls back to `~/.config/steam-family-collections/config.toml`.

```toml
[steam]
api_key = "YOUR_STEAM_API_KEY"
steam_id = "YOUR_STEAM_ID_64"
# user_id = "12345678"  # optional; auto-detected when only one account exists

[mobygames]
api_key = "YOUR_MOBYGAMES_API_KEY"
```

To find your `steam_id`, visit your Steam profile page — the 64-bit ID appears in the URL (e.g. `https://steamcommunity.com/profiles/76561198XXXXXXXXX`).

## Usage

```bash
uv run python main.py
```

| Key | Action |
|-----|--------|
| F1  | Fetch your Steam library |
| F2  | Enrich games with PEGI ratings (via MobyGames) |
| F3  | Manage child profiles |
| q   | Quit |

### Workflow

1. **F1 — Fetch Library**: Downloads your owned games from the Steam API.
2. **F2 — Enrich Ratings**: Looks up PEGI ratings for each unrated game. You may be prompted to disambiguate titles.
3. **F3 — Manage Children**: Create profiles for each child with a maximum PEGI age. From a child's profile you can review their filtered game list and push it to Steam.

Pushing a collection writes a filtered game list into Steam's cloud storage (`~/.local/share/Steam/userdata/{user_id}/config/cloudstorage/`). A backup of the existing file is created before any write.

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
