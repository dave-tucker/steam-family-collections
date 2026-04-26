from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Label

import core.children as children
import core.database as database
from tui.modals import ConfirmModal, EditAgeModal, NewChildModal


class ChildrenScreen(Screen):
    CSS = """
    ChildrenScreen > #title {
        height: 1;
        padding: 0 1;
        background: $primary;
        color: $text;
        text-style: bold;
    }
    ChildrenScreen > DataTable { height: 1fr; }
    ChildrenScreen > #status {
        height: 1;
        padding: 0 1;
        background: $panel-darken-1;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("n", "new_child", "New Child", show=True),
        Binding("e", "edit_age", "Edit Age", show=True),
        Binding("d", "delete_child", "Delete", show=True),
        Binding("enter", "open_collection", "Open", show=True, priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Label("Children", id="title")
        yield DataTable(id="children-table", zebra_stripes=True)
        yield Label("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._load_table()

    def on_screen_resume(self) -> None:
        self._load_table()

    def _load_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns("Name", "Max Age", "Games in Library")
        for child in children.list_children():
            table.add_row(
                child["name"],
                str(child["max_age"]),
                str(len(child.get("library", []))),
                key=child["name"],
            )

    def _selected_name(self) -> str | None:
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return None
        keys = list(table.rows.keys())
        idx = table.cursor_row
        if 0 <= idx < len(keys):
            return str(keys[idx].value)
        return None

    def set_status(self, msg: str) -> None:
        self.query_one("#status", Label).update(msg)

    # ------------------------------------------------------------------ new child
    def action_new_child(self) -> None:
        def on_result(data: dict | None) -> None:
            if data is None:
                return
            name = data["name"]
            if children.load_child(name) is not None:
                self.set_status(f"A profile named '{name}' already exists")
                return
            child = {"name": name, "max_age": data["max_age"], "library": []}
            games = database.load_games()
            children.sync_child(child, games)
            children.save_child(child)
            self._load_table()
            self.set_status(
                f"Created '{name}' (max age {data['max_age']}, {len(child['library'])} games)"
            )

        self.app.push_screen(NewChildModal(), on_result)

    # ------------------------------------------------------------------ edit age
    def action_edit_age(self) -> None:
        name = self._selected_name()
        if not name:
            return
        child = children.load_child(name)
        if not child:
            return

        def on_result(age: int | None) -> None:
            if age is None:
                return
            child["max_age"] = age
            games = database.load_games()
            added, removed = children.sync_child(child, games)
            children.save_child(child)
            self._load_table()
            self.set_status(f"Updated '{name}' max age to {age} (+{added} / -{removed} games)")

        self.app.push_screen(EditAgeModal(child), on_result)

    # ------------------------------------------------------------------ delete child
    def action_delete_child(self) -> None:
        name = self._selected_name()
        if not name:
            return

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                children.delete_child(name)
                self._load_table()
                self.set_status(f"Deleted profile '{name}'")

        self.app.push_screen(ConfirmModal(f"Delete profile '{name}'?"), on_confirm)

    # ------------------------------------------------------------------ open collection
    def action_open_collection(self) -> None:
        name = self._selected_name()
        if not name:
            return
        from tui.collection_screen import ChildCollectionScreen

        self.app.push_screen(ChildCollectionScreen(name))
