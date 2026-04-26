#!/usr/bin/env python3
"""Steam Family Collections — TUI entry point."""

from __future__ import annotations

import sys

from textual.app import App
from textual.binding import Binding

from core.config import ConfigError, load_config
from core.database import ensure_data_dir


class SteamFamilyApp(App):
    TITLE = "Steam Family Collections"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("f1", "fetch_library", "Fetch Library", show=True, priority=True),
        Binding("f2", "enrich_ratings", "Enrich Ratings", show=True, priority=True),
        Binding("f3", "toggle_children", "Children", show=True, priority=True),
        Binding("q", "quit", "Quit", show=True, priority=True),
    ]

    def __init__(self, config: dict) -> None:
        super().__init__()
        self.config = config

    def on_mount(self) -> None:
        import core.config as _cfg
        from tui.library import LibraryScreen

        if _cfg.DEMO_MODE:
            self.title = "Steam Family Collections [DEMO MODE]"
        self.push_screen(LibraryScreen())

    # ------------------------------------------------------------------ F1
    def action_fetch_library(self) -> None:
        import core.config as _cfg

        if _cfg.DEMO_MODE:
            self.notify("Demo mode — fetch is disabled", severity="warning")
            return
        screen = self._get_or_push_library()
        if screen:
            screen.start_fetch_library()

    # ------------------------------------------------------------------ F2
    def action_enrich_ratings(self) -> None:
        import core.config as _cfg

        if _cfg.DEMO_MODE:
            self.notify("Demo mode — enrich is disabled", severity="warning")
            return
        screen = self._get_or_push_library()
        if screen:
            screen.start_enrich_all()

    # ------------------------------------------------------------------ F3
    def action_toggle_children(self) -> None:
        from tui.children_screen import ChildrenScreen
        from tui.library import LibraryScreen

        if isinstance(self.screen, LibraryScreen):
            self.push_screen(ChildrenScreen())
        elif isinstance(self.screen, ChildrenScreen):
            self.pop_screen()
        else:
            # On collection screen or elsewhere — navigate to children
            for screen in reversed(self.screen_stack):
                if isinstance(screen, ChildrenScreen):
                    while not isinstance(self.screen, ChildrenScreen):
                        self.pop_screen()
                    return
            self.push_screen(ChildrenScreen())

    # ------------------------------------------------------------------ helpers
    def _get_or_push_library(self):
        from tui.library import LibraryScreen

        for screen in reversed(self.screen_stack):
            if isinstance(screen, LibraryScreen):
                while not isinstance(self.screen, LibraryScreen):
                    self.pop_screen()
                return self.screen
        ls = LibraryScreen()
        self.push_screen(ls)
        return ls


def main() -> None:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Configuration error:\n{exc}", file=sys.stderr)
        sys.exit(1)

    ensure_data_dir()
    SteamFamilyApp(config).run()


if __name__ == "__main__":
    main()
