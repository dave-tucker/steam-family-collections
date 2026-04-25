# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Set up venv and install all dependencies (including dev)
uv sync --dev

# Run the application
uv run python main.py

# Run tests
uv run pytest

# Run a single test file
uv run pytest tests/test_mobygames.py -v

# Lint and format
uv run ruff check .
uv run ruff format .
```

## Architecture

Steam Family Collections is a Python TUI app (using [Textual](https://textual.textualize.io/)) that helps parents create age-appropriate Steam game collections for their children based on PEGI ratings.

### Data flow

1. **Fetch Library** (F1): Calls Steam API → stores owned games in `~/.local/share/steam-family-collections/games.json`
2. **Enrich Ratings** (F2): Searches MobyGames for each unrated game → prompts user to disambiguate titles → stores PEGI ratings in `games.json`
3. **Manage Children** (F3): CRUD for child profiles stored in `~/.local/share/steam-family-collections/children/{name}.json`; each child has a `max_age` used to filter games by PEGI ≤ max_age
4. **Push Collection**: Writes filtered game list into Steam's cloud-storage file at `~/.local/share/Steam/userdata/{user_id}/config/cloudstorage/cloud-storage-namespace-1.json` (with backup), which syncs to the child's Steam client

### Module responsibilities

**`core/`** — stateless business logic:
- `config.py` — loads `~/.config/steam-family-collections/config.toml`, validates API keys, auto-detects Steam user ID
- `database.py` — atomic load/save of `games.json`
- `steam.py` — Steam API (`GetOwnedGames`) and Steam Store PEGI extraction with rate-limit backoff
- `mobygames.py` — MobyGames title search, PEGI-per-platform fetch, title normalization (strips edition qualifiers, trademarks)
- `children.py` — child profile load/save/delete, library filtering, game-rating sync
- `collection.py` — read/write Steam cloud-storage collection JSON with schema parsing and backup

**`tui/`** — Textual screens and modals:
- `main.py` — `SteamFamilyApp`, screen stack, F1/F2/F3 bindings
- `library.py` — main game table, fetch/enrich queuing, modal integration
- `children_screen.py` — child profile table, CRUD
- `collection_screen.py` — per-child filtered game view, add/remove, sync, push to Steam
- `modals.py` — all dialog components (confirm, edit PEGI, disambiguation, new child, edit age, add game, push warning)

### Configuration

`~/.config/steam-family-collections/config.toml` — Steam API key, Steam ID, MobyGames API key.
