# Demo Mode

Demo mode lets you explore the full app UI without API keys, using 25 bundled sample games and three pre-built child profiles.

## Enable demo mode

Add the following to a `config.toml` in the project directory (or your user config):

```toml
[app]
demo = true
```

Then run:

```bash
uv run python main.py
```

The title bar shows `[DEMO MODE]` to confirm it is active.

## What's included

**25 games** spanning all PEGI ratings:

| Rating | Games |
|--------|-------|
| PEGI 3 | Stardew Valley, Rocket League, Cities: Skylines, Overcooked! 2, Celeste |
| PEGI 7 | Terraria, Hollow Knight, Cuphead, Ori and the Blind Forest, Undertale, A Hat in Time, Minecraft Dungeons |
| PEGI 12 | Portal 2, Team Fortress 2, Civilization VI, Slay the Spire, Hades, It Takes Two, Spelunky 2, Among Us, Garry's Mod |
| PEGI 16 | SUPERHOT, Disco Elysium |
| PEGI 18 | DOOM, Left 4 Dead 2 |

**Three child profiles:**

| Name | Max age | Library size |
|------|---------|-------------|
| Alex | 12 | 21 games |
| Emma | 7 | 12 games |
| Sam | 16 | 23 games |

## Limitations

The following operations are disabled in demo mode and show a notice if attempted:

- **F1 — Fetch Library**: no Steam API calls
- **F2 — Enrich Ratings**: no MobyGames or Steam store lookups
- **P — Push to Steam**: no writes to Steam's cloud-storage

All other interactions work normally: filtering, manual rating edits, adding/removing games from collections, and navigating between screens.

## Resetting demo state

Demo mode is read-only — no writes are made to the bundled data. The game list and child profiles remain exactly as shipped, regardless of what you do in the UI.

## Using demo mode for screenshots

```bash
uv run python scripts/take_screenshots.py
```

This captures SVG screenshots of each major screen and writes them to `docs/assets/screenshots/`.
