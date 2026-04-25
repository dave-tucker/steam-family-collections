from __future__ import annotations

import subprocess

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Label

import core.children as children
import core.collection as collection
import core.database as database
from tui.modals import AddGameModal, ConfirmModal, PushWarningModal


class ChildCollectionScreen(Screen):
    CSS = """
    ChildCollectionScreen > #header {
        height: 1;
        padding: 0 1;
        background: $primary;
        color: $text;
        text-style: bold;
    }
    ChildCollectionScreen > DataTable { height: 1fr; }
    ChildCollectionScreen > #status {
        height: 1;
        padding: 0 1;
        background: $panel-darken-1;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("r", "remove_game", "Remove", show=True),
        Binding("a", "add_game", "Add Game", show=True),
        Binding("s", "sync_collection", "Sync", show=True),
        Binding("p", "push_to_steam", "Push to Steam", show=True),
        Binding("backspace", "pop_screen", "Back", show=True),
    ]

    def __init__(self, child_name: str) -> None:
        super().__init__()
        self._child_name = child_name

    def compose(self) -> ComposeResult:
        yield Label("", id="header")
        yield DataTable(id="collection-table", zebra_stripes=True)
        yield Label("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._load_table()

    def on_screen_resume(self) -> None:
        self._load_table()

    def _load_table(self) -> None:
        child = children.load_child(self._child_name)
        if not child:
            self.set_status(f"Profile '{self._child_name}' not found")
            return

        self.query_one("#header", Label).update(
            f"{child['name']} — max age {child['max_age']} "
            f"({len(child.get('library', []))} games)"
        )

        games = database.load_games()
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns("Title", "AppID", "PEGI Rating", "Source")
        for appid_int in child.get("library", []):
            game = games.get(str(appid_int), {})
            table.add_row(
                game.get("title", f"App {appid_int}"),
                str(appid_int),
                str(game.get("pegi_rating") or ""),
                game.get("pegi_source") or "",
                key=str(appid_int),
            )

    def _selected_appid(self) -> int | None:
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return None
        keys = list(table.rows.keys())
        idx = table.cursor_row
        if 0 <= idx < len(keys):
            return int(str(keys[idx].value))
        return None

    def set_status(self, msg: str) -> None:
        self.query_one("#status", Label).update(msg)

    # ------------------------------------------------------------------ remove game
    def action_remove_game(self) -> None:
        appid = self._selected_appid()
        if appid is None:
            return
        child = children.load_child(self._child_name)
        if not child:
            return
        games = database.load_games()
        title = games.get(str(appid), {}).get("title", f"App {appid}")

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                child["library"] = [a for a in child["library"] if a != appid]
                children.save_child(child)
                self._load_table()
                self.set_status(f"Removed '{title}' from {self._child_name}'s collection")

        self.app.push_screen(ConfirmModal(f"Remove '{title}' from collection?"), on_confirm)

    # ------------------------------------------------------------------ add game
    def action_add_game(self) -> None:
        child = children.load_child(self._child_name)
        if not child:
            return
        games = database.load_games()
        in_library = set(child.get("library", []))
        eligible = [
            g
            for g in games.values()
            if g.get("pegi_rating") is not None
            and g.get("pegi_flag") is None
            and g["pegi_rating"] <= child["max_age"]
            and g["appid"] not in in_library
        ]
        eligible.sort(key=lambda g: g["title"].lower())

        if not eligible:
            self.set_status("No eligible games to add")
            return

        def on_result(appid: int | None) -> None:
            if appid is None:
                return
            child = children.load_child(self._child_name)
            if child and appid not in child["library"]:
                child["library"].append(appid)
                child["library"].sort()
                children.save_child(child)
                game = games.get(str(appid), {})
                self._load_table()
                self.set_status(f"Added '{game.get('title', appid)}'")

        self.app.push_screen(AddGameModal(eligible), on_result)

    # ------------------------------------------------------------------ sync
    def action_sync_collection(self) -> None:
        child = children.load_child(self._child_name)
        if not child:
            return
        games = database.load_games()
        added, removed = children.sync_child(child, games)
        children.save_child(child)
        self._load_table()
        self.set_status(f"Sync complete: +{added} added, -{removed} removed")

    # ------------------------------------------------------------------ push to steam
    def action_push_to_steam(self) -> None:
        def on_warning(confirmed: bool) -> None:
            if not confirmed:
                return
            self._do_push()

        self.app.push_screen(PushWarningModal(self._child_name), on_warning)

    @work(thread=True)
    def _do_push(self) -> None:
        result = subprocess.run(
            ["pgrep", "-ix", "steam"], capture_output=True
        )
        if result.returncode == 0:
            self.app.call_from_thread(
                self.set_status,
                "Steam is running — close Steam fully before pushing",
            )
            return

        try:
            cfg = self.app.config
            from core.config import get_user_id
            user_id = get_user_id(cfg)
        except Exception as exc:
            self.app.call_from_thread(self.set_status, f"Config error: {exc}")
            return

        child = children.load_child(self._child_name)
        if not child:
            self.app.call_from_thread(self.set_status, "Child profile not found")
            return

        try:
            collection.push_collection(
                user_id, self._child_name, child.get("library", [])
            )
            self.app.call_from_thread(
                self.set_status,
                f"Pushed {len(child.get('library', []))} games for {self._child_name}",
            )
        except Exception as exc:
            self.app.call_from_thread(self.set_status, f"Push error: {exc}")
