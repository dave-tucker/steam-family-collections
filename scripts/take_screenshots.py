#!/usr/bin/env python3
"""Capture SVG screenshots of each major screen using Textual's pilot.

Run from the project root with demo mode active:
    uv run python scripts/take_screenshots.py

Screenshots are saved to docs/assets/screenshots/.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

import core.config as _cfg

_cfg.enable_demo_mode()

from main import SteamFamilyApp  # noqa: E402 — must come after enable_demo_mode()

OUT_DIR = Path(__file__).parent.parent / "docs" / "assets" / "screenshots"


def _save(app: SteamFamilyApp, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    svg = app.export_screenshot()
    path.write_text(svg, encoding="utf-8")
    print(f"  saved {path.relative_to(Path(__file__).parent.parent)}")


async def _run() -> None:
    app = SteamFamilyApp({})
    async with app.run_test(size=(180, 45)) as pilot:
        # Library screen — all games
        await pilot.pause(0.5)
        _save(app, "library.svg")

        # Library screen — unrated filter
        await pilot.press("f")
        await pilot.pause(0.2)
        _save(app, "library_unrated.svg")

        # Reset filter to all
        await pilot.press("f")
        await pilot.press("f")
        await pilot.pause(0.1)

        # Children screen
        await pilot.press("f3")
        await pilot.pause(0.3)
        _save(app, "children.svg")

        # Collection screen for first child (Alex — alphabetically first)
        await pilot.press("enter")
        await pilot.pause(0.3)
        _save(app, "collection.svg")


def main() -> None:
    print("Taking screenshots in demo mode…")
    asyncio.run(_run())
    print("Done.")


if __name__ == "__main__":
    main()
