# Claude Code Prompt: Steam Family Collections TUI

You are helping me build a Python TUI application to manage Steam game collections for my children based on PEGI ratings. The platform is Linux.

---

## Configuration

All private configuration lives in `~/.config/steam-family-collections/config.toml`. The application must read from this file on startup and fail with a clear error if required keys are missing.

```toml
[steam]
api_key = "YOUR_STEAM_API_KEY"
steam_id = "YOUR_STEAM_ID_64"
user_id = "YOUR_STEAM_USERDATA_ID"   # numeric directory under ~/.local/share/Steam/userdata/

[mobygames]
api_key = "YOUR_MOBYGAMES_API_KEY"
```

- Create the config directory and an example `config.toml` if it does not exist on first run, then prompt the user to fill it in and exit
- All values previously passed as environment variables are instead read from this file
- No secrets are ever hardcoded or stored in the data directory

---

## Data layout

```
games.json                        # master game library
children/
  {child_name}.json               # one file per child profile
```

### `games.json`

Keyed by AppID:

```json
{
  "123456": {
    "appid": 123456,
    "title": "Game Title",
    "pegi_rating": null,
    "pegi_source": null,
    "pegi_flag": null
  }
}
```

- `pegi_rating` — integer (3, 7, 12, 16, 18) or null
- `pegi_source` — `"steam"`, `"mobygames"`, `"manual"`, or null
- `pegi_flag` — `"unrated"`, `"ambiguous"`, or null. Flagged games are excluded from all collections.

### `children/{child_name}.json`

```json
{
  "name": "Alice",
  "max_age": 12,
  "library": [123456, 789012]
}
```

`library` is always derived: `pegi_rating <= max_age` AND `pegi_flag` is null AND `pegi_rating` is not null. It is never manually authoritative — sync always recomputes it from `games.json`.

---

## Technology

- Python 3
- `textual` for the TUI
- `requests` for HTTP
- `tomllib` (stdlib, Python 3.11+) for config parsing
- No other frameworks
- All data stored as JSON files — no database

---

## Application structure

The app is a single entry point (`main.py`) that launches the TUI. All logic (fetch library, enrich ratings, build collection, write to Steam) is implemented in a `core/` module and called from the TUI. There are no standalone scripts; the TUI is the only interface.

```
main.py
core/
  config.py       # config loading and validation
  steam.py        # Steam API and library fetch logic
  mobygames.py    # MobyGames API and enrichment logic
  database.py     # games.json read/write
  children.py     # child profile management
  collection.py   # Steam collection file read/write
children/
games.json
```

---

## Screens

### Screen 1 — Library (default)

A full-screen table showing all games in `games.json`. Columns:

| Title | AppID | PEGI Rating | Source | Flag |
|-------|-------|-------------|--------|------|

Keyboard navigation: arrow keys to move. Actions on the highlighted row:

| Key | Action |
|-----|--------|
| `d` | Delete game from `games.json` (confirm via modal) |
| `e` | Edit PEGI rating manually; modal with numeric input; sets `pegi_source = "manual"`, clears `pegi_flag` |
| `m` | Look up this game on MobyGames; triggers disambiguation modal if needed |
| `a` | Add to a child's collection; modal listing child profiles; warns if game fails age filter |

Global commands (available from any screen):

| Key | Action |
|-----|--------|
| `F1` | Fetch/refresh Steam library |
| `F2` | Enrich all unrated games from MobyGames |
| `F3` | Switch to Children screen |
| `q` | Quit |

---

### MobyGames Disambiguation Modal

Triggered when a MobyGames search returns multiple results. Shows a scrollable list of candidates with platform and year.

| Key | Action |
|-----|--------|
| Arrow keys | Navigate candidates |
| `Enter` | Confirm selection |
| `s` / `Escape` | Skip — marks `pegi_flag = "ambiguous"` |

---

### Screen 2 — Children

A list of child profiles showing name and max age.

| Key | Action |
|-----|--------|
| `n` | Create new child profile; modal asks for name and max age; saves `children/{name}.json` and immediately computes library |
| `Enter` | Open that child's Collection screen |
| `e` | Edit child's max age; modal with numeric input; immediately resyncs library on confirm |
| `d` | Delete child profile (confirm via modal) |

---

### Screen 3 — Child Collection

Header shows child's name and max age. Table of games in this child's `library`. Columns: Title, AppID, PEGI Rating, Source.

| Key | Action |
|-----|--------|
| `r` | Remove game from this child's library (does not affect `games.json`) |
| `a` | Add a game; searchable overlay of `games.json` filtered to games passing this child's age filter and not already in the collection |
| `s` | Sync collection; recomputes `library` from `games.json`; shows summary (added N, removed N) |
| `p` | Push to Steam (see below) |
| `Backspace` | Return to Children screen |

---

## Steam Enrichment (F2 / per-game `m`)

### Primary source — Steam store API

- Endpoint: `https://store.steampowered.com/api/appdetails?appids={appid}&cc=gb&l=en`
- Extract PEGI from the `ratings` object
- Rate limit: 1 request per second; back off and retry on 429

### Fallback — MobyGames API

Only used if Steam returns no PEGI rating.

| Result | Action |
|--------|--------|
| Zero results | `pegi_flag = "unrated"` |
| One result, has PEGI | Use it |
| One result, no PEGI | `pegi_flag = "unrated"` |
| Multiple results | Disambiguation modal |
| User skips modal | `pegi_flag = "ambiguous"` |

No enrichment data is ever overwritten once set, unless the user explicitly uses `e` (manual edit) or `m` (force MobyGames lookup) on a specific game.

---

## Steam Library Fetch (F1)

- Reads `steam.api_key` and `steam.steam_id` from config
- Uses `IPlayerService/GetOwnedGames` with `include_appinfo=1`
- Adds new games to `games.json`; never overwrites existing entries
- Shows summary on completion: N new games added, N already present

---

## Push to Steam (Screen 3 → `p`)

1. Show modal: "Ensure Steam is fully closed before continuing"
2. On confirm: check for a running `steam` process; if found, abort with a clear error in the modal
3. Back up target file to `cloud-storage-namespace-1.json.bak`
4. Merge new collection into existing file without destroying other collections
5. Add a comment in `core/collection.py` describing the schema of the collection file as found

Target file path:
```
~/.local/share/Steam/userdata/{steam.user_id}/config/cloudstorage/cloud-storage-namespace-1.json
```

`user_id` is read from config. If `steam.user_id` is not set in config, attempt to auto-detect by listing numeric directories under `~/.local/share/Steam/userdata/`; error if zero or more than one found.

---

## General Requirements

- All file writes are atomic where possible (write to temp file, rename)
- All destructive actions require confirmation via modal
- Missing `games.json` or `children/` directory: create them gracefully on first run
- Status bar at the bottom of every screen showing the result of the last action
- All network operations run in a Textual background worker so the TUI never blocks
- Error handling: network failures, missing/invalid config, malformed API responses surface as readable error modals — the app never crashes to a traceback

---

## Acceptance Criteria

1. **Config**: app exits cleanly with a helpful message if `config.toml` is missing or any required key is absent
2. **F1 fetch**: after running, the library table shows every game in the Steam account with correct titles and AppIDs
3. **F2 enrichment**: spot-check 20 games against [pegi.info](https://pegi.info) after enrichment — expect ≥18/20 correct
4. **Child sync**: creating a child profile with max age 12 and running sync produces a library containing no games with PEGI > 12 and no flagged games
5. **Age edit**: editing a child's max age immediately updates their library without requiring a manual sync trigger
6. **Push to Steam**: after pushing, launch Steam and verify the named collection exists and contains the expected games
7. **Idempotency**: every operation is safe to run multiple times with the same outcome
