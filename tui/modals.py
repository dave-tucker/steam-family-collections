from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Static

_VALID_PEGI = (3, 7, 12, 16, 18)

_SHARED_CSS = """
.dialog {
    width: 70;
    height: auto;
    background: $surface;
    border: thick $primary;
    padding: 1 2;
}
.dialog-title {
    text-style: bold;
    margin-bottom: 1;
}
.dialog-buttons {
    height: 3;
    align: center middle;
    margin-top: 1;
}
.dialog-buttons Button {
    margin: 0 1;
}
"""


class ConfirmModal(ModalScreen):
    DEFAULT_CSS = (
        _SHARED_CSS
        + """
ConfirmModal { align: center middle; }
"""
    )

    def __init__(self, message: str, title: str = "Confirm") -> None:
        super().__init__()
        self._message = message
        self._title = title

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label(self._title, classes="dialog-title")
            yield Label(self._message)
            with Horizontal(classes="dialog-buttons"):
                yield Button("Yes", variant="error", id="yes")
                yield Button("No", variant="primary", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class EditPegiModal(ModalScreen):
    DEFAULT_CSS = (
        _SHARED_CSS
        + """
EditPegiModal { align: center middle; }
"""
    )

    def __init__(self, game: dict) -> None:
        super().__init__()
        self._game = game

    def compose(self) -> ComposeResult:
        current = str(self._game.get("pegi_rating") or "")
        with Vertical(classes="dialog"):
            yield Label(f"Edit PEGI rating — {self._game['title']}", classes="dialog-title")
            yield Label(f"Valid values: {', '.join(str(p) for p in _VALID_PEGI)}")
            yield Input(value=current, placeholder="e.g. 12", id="rating-input")
            yield Label("", id="error-label")
            with Horizontal(classes="dialog-buttons"):
                yield Button("Save", variant="success", id="save")
                yield Button("Cancel", variant="primary", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        self._try_save()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self._try_save()

    def _try_save(self) -> None:
        raw = self.query_one("#rating-input", Input).value.strip()
        try:
            val = int(raw)
        except ValueError:
            self.query_one("#error-label", Label).update("Must be a number")
            return
        if val not in _VALID_PEGI:
            self.query_one("#error-label", Label).update(
                f"Must be one of: {', '.join(str(p) for p in _VALID_PEGI)}"
            )
            return
        self.dismiss(val)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class DisambiguationModal(ModalScreen):
    DEFAULT_CSS = (
        _SHARED_CSS
        + """
DisambiguationModal { align: center middle; }
DisambiguationModal .dialog { height: 30; width: 90; }
DisambiguationModal DataTable { height: 1fr; }
"""
    )

    BINDINGS = [
        Binding("enter", "confirm", "Select", priority=True),
        Binding("s", "skip", "Skip"),
        Binding("escape", "skip", "Skip"),
    ]

    def __init__(
        self, candidates: list[dict], game_title: str = "", queue_remaining: int = 0
    ) -> None:
        super().__init__()
        self._candidates = candidates
        self._game_title = game_title
        self._queue_remaining = queue_remaining

    def compose(self) -> ComposeResult:
        heading = (
            f'Multiple results for "{self._game_title}"'
            if self._game_title
            else "Multiple results found"
        )
        if self._queue_remaining > 0:
            heading += f"  ({self._queue_remaining} more in queue)"
        with Vertical(classes="dialog"):
            yield Label(heading, classes="dialog-title")
            yield DataTable(id="candidates-table")
            yield Static("Enter: confirm  s/Esc: skip", classes="help-text")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Title", "Year", "Platforms")
        for i, game in enumerate(self._candidates):
            title = game.get("title", "Unknown")
            year = (game.get("first_release_date") or "")[:4] or "?"
            platforms = ", ".join(p.get("platform_name", "") for p in game.get("platforms", [])[:3])
            table.add_row(title, year, platforms, key=str(i))
        table.focus()

    def action_confirm(self) -> None:
        table = self.query_one(DataTable)
        keys = list(table.rows.keys())
        if not keys:
            return
        idx = int(str(keys[table.cursor_row].value))
        self.dismiss(self._candidates[idx])

    def action_skip(self) -> None:
        self.dismiss(None)


class AddToChildModal(ModalScreen):
    DEFAULT_CSS = (
        _SHARED_CSS
        + """
AddToChildModal { align: center middle; }
AddToChildModal .dialog { height: auto; max-height: 30; }
AddToChildModal DataTable { height: auto; max-height: 15; }
"""
    )

    BINDINGS = [
        Binding("enter", "confirm", "Select", priority=True),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, children: list[dict], game: dict) -> None:
        super().__init__()
        self._children = children
        self._game = game

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label(
                f"Add '{self._game['title']}' to child's collection",
                classes="dialog-title",
            )
            yield DataTable(id="children-table")
            yield Static("Enter: select  Esc: cancel")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Name", "Max Age")
        for child in self._children:
            table.add_row(child["name"], str(child["max_age"]), key=child["name"])
        table.focus()

    def action_confirm(self) -> None:
        table = self.query_one(DataTable)
        keys = list(table.rows.keys())
        if not keys:
            return
        self.dismiss(str(keys[table.cursor_row].value))

    def action_cancel(self) -> None:
        self.dismiss(None)


class NewChildModal(ModalScreen):
    DEFAULT_CSS = (
        _SHARED_CSS
        + """
NewChildModal { align: center middle; }
"""
    )

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label("New Child Profile", classes="dialog-title")
            yield Label("Name:")
            yield Input(placeholder="e.g. Alice", id="name-input")
            yield Label("Max PEGI age:")
            yield Input(placeholder="e.g. 12", id="age-input")
            yield Label("", id="error-label")
            with Horizontal(classes="dialog-buttons"):
                yield Button("Create", variant="success", id="create")
                yield Button("Cancel", variant="primary", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        self._try_create()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self._try_create()

    def _try_create(self) -> None:
        name = self.query_one("#name-input", Input).value.strip()
        age_raw = self.query_one("#age-input", Input).value.strip()
        err = self.query_one("#error-label", Label)

        if not name:
            err.update("Name is required")
            return
        if "/" in name or "\\" in name:
            err.update("Name must not contain / or \\")
            return
        try:
            age = int(age_raw)
            if age < 0 or age > 18:
                raise ValueError
        except ValueError:
            err.update("Max age must be a number 0–18")
            return

        self.dismiss({"name": name, "max_age": age})

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class EditAgeModal(ModalScreen):
    DEFAULT_CSS = (
        _SHARED_CSS
        + """
EditAgeModal { align: center middle; }
"""
    )

    def __init__(self, child: dict) -> None:
        super().__init__()
        self._child = child

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label(f"Edit max age — {self._child['name']}", classes="dialog-title")
            yield Input(
                value=str(self._child["max_age"]),
                placeholder="e.g. 12",
                id="age-input",
            )
            yield Label("", id="error-label")
            with Horizontal(classes="dialog-buttons"):
                yield Button("Save", variant="success", id="save")
                yield Button("Cancel", variant="primary", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        self._try_save()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self._try_save()

    def _try_save(self) -> None:
        raw = self.query_one("#age-input", Input).value.strip()
        try:
            age = int(raw)
            if age < 0 or age > 18:
                raise ValueError
        except ValueError:
            self.query_one("#error-label", Label).update("Must be a number 0–18")
            return
        self.dismiss(age)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class PushWarningModal(ModalScreen):
    DEFAULT_CSS = (
        _SHARED_CSS
        + """
PushWarningModal { align: center middle; }
"""
    )

    def __init__(self, child_name: str) -> None:
        super().__init__()
        self._child_name = child_name

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label("Push to Steam", classes="dialog-title")
            yield Label(
                f"This will write {self._child_name}'s collection to the Steam\n"
                "local config file.\n\n"
                "[bold]Ensure Steam is fully closed before continuing.[/bold]"
            )
            with Horizontal(classes="dialog-buttons"):
                yield Button("Push", variant="error", id="push")
                yield Button("Cancel", variant="primary", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "push")

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class SetMobyIdModal(ModalScreen):
    DEFAULT_CSS = (
        _SHARED_CSS
        + """
SetMobyIdModal { align: center middle; }
"""
    )

    def __init__(self, game: dict) -> None:
        super().__init__()
        self._game = game

    def compose(self) -> ComposeResult:
        current = str(self._game.get("moby_id") or "")
        with Vertical(classes="dialog"):
            yield Label(f"Set MobyGames ID — {self._game['title']}", classes="dialog-title")
            yield Input(value=current, placeholder="e.g. 1234", id="moby-input")
            yield Label("", id="error-label")
            with Horizontal(classes="dialog-buttons"):
                yield Button("Save", variant="success", id="save")
                yield Button("Cancel", variant="primary", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        self._try_save()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self._try_save()

    def _try_save(self) -> None:
        raw = self.query_one("#moby-input", Input).value.strip()
        try:
            val = int(raw)
            if val <= 0:
                raise ValueError
        except ValueError:
            self.query_one("#error-label", Label).update("Must be a positive integer")
            return
        self.dismiss(val)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class AddGameModal(ModalScreen):
    DEFAULT_CSS = (
        _SHARED_CSS
        + """
AddGameModal { align: center middle; }
AddGameModal .dialog { height: 35; width: 90; }
AddGameModal DataTable { height: 1fr; }
"""
    )

    BINDINGS = [
        Binding("enter", "confirm", "Select", priority=True),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, eligible_games: list[dict]) -> None:
        super().__init__()
        self._all = eligible_games

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label("Add game to collection", classes="dialog-title")
            yield Input(placeholder="Filter by title…", id="filter-input")
            yield DataTable(id="games-table")
            yield Static("Type to filter · ↓/↑ to move · Enter to add · Esc to cancel")

    def on_mount(self) -> None:
        self._rebuild_table(self._all)
        self.query_one("#filter-input", Input).focus()

    def _rebuild_table(self, games: list[dict]) -> None:
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns("Title", "AppID", "PEGI")
        for game in games:
            table.add_row(
                game["title"],
                str(game["appid"]),
                str(game.get("pegi_rating") or ""),
                key=str(game["appid"]),
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        q = event.value.lower()
        self._rebuild_table([g for g in self._all if q in g["title"].lower()])

    def on_key(self, event) -> None:
        if event.key in ("down", "up"):
            self.query_one(DataTable).focus()

    def action_confirm(self) -> None:
        if self.query_one("#filter-input", Input).has_focus:
            self.query_one(DataTable).focus()
            return
        self._confirm_selection()

    def _confirm_selection(self) -> None:
        table = self.query_one(DataTable)
        keys = list(table.rows.keys())
        if not keys:
            return
        self.dismiss(int(str(keys[table.cursor_row].value)))

    def action_cancel(self) -> None:
        self.dismiss(None)
