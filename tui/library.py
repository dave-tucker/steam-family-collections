from __future__ import annotations

import time
from collections import deque

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Label

import core.children as children
import core.database as database
import core.mobygames as mobygames
import core.steam as steam
from tui.modals import (
    AddToChildModal,
    ConfirmModal,
    DisambiguationModal,
    EditPegiModal,
)


class LibraryScreen(Screen):
    CSS = """
    LibraryScreen > DataTable { height: 1fr; }
    LibraryScreen > #status {
        height: 1;
        padding: 0 1;
        background: $panel-darken-1;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("d", "delete_game", "Delete", show=True),
        Binding("e", "edit_rating", "Edit Rating", show=True),
        Binding("m", "moby_lookup", "MobyGames", show=True),
        Binding("a", "add_to_child", "Add to Child", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        # Queue of appids waiting for MobyGames title search / disambiguation
        self._search_queue: deque[str] = deque()
        # Appids that have a moby_id and are waiting for per-platform ratings fetch
        self._ratings_queue: list[str] = []
        # Appid currently being processed (to avoid double-queuing)
        self._current_appid: str | None = None
        # True while the queue is actively running
        self._queue_active = False

    # ------------------------------------------------------------------ table

    def compose(self) -> ComposeResult:
        yield DataTable(id="game-table", zebra_stripes=True)
        yield Label("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._init_columns()
        self._reload_rows()

    def on_resize(self) -> None:
        self._init_columns()
        self._reload_rows()

    def on_screen_resume(self) -> None:
        self._reload_rows()

    def _init_columns(self) -> None:
        table = self.query_one(DataTable)
        table.clear(columns=True)
        title_w = max(20, self.size.width // 2)
        table.add_column("Title", width=title_w)
        table.add_column("AppID", width=10)
        table.add_column("Moby ID", width=10)
        table.add_column("PEGI Rating", width=11)
        table.add_column("Source", width=10)
        table.add_column("Flag", width=10)

    def _reload_rows(self) -> None:
        table = self.query_one(DataTable)

        selected_key: str | None = None
        if table.row_count > 0:
            keys = list(table.rows.keys())
            idx = table.cursor_row
            if 0 <= idx < len(keys):
                selected_key = str(keys[idx].value)

        table.clear()
        games = database.load_games()
        for appid, game in sorted(games.items(), key=lambda x: x[1]["title"].lower()):
            table.add_row(
                game["title"],
                str(game["appid"]),
                str(game.get("moby_id") or ""),
                str(game.get("pegi_rating") or ""),
                game.get("pegi_source") or "",
                game.get("pegi_flag") or "",
                key=appid,
            )

        if selected_key is not None and selected_key in {str(k.value) for k in table.rows}:
            target = next(
                i for i, k in enumerate(table.rows.keys())
                if str(k.value) == selected_key
            )
            table.move_cursor(row=target)

    def _selected_appid(self) -> str | None:
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

    # ------------------------------------------------------------------ queue

    def enqueue_moby_search(self, appids: list[str]) -> None:
        """Add appids to the search queue and start processing if idle."""
        added = 0
        for appid in appids:
            if (
                appid not in self._search_queue
                and appid not in self._ratings_queue
                and appid != self._current_appid
            ):
                self._search_queue.append(appid)
                added += 1
        if added and not self._queue_active:
            self._advance_queue()

    def _advance_queue(self) -> None:
        """Pick the next item to process. Always called on the main thread."""
        if self._search_queue:
            appid = self._search_queue.popleft()
            self._current_appid = appid
            self._queue_active = True
            games = database.load_games()
            title = games.get(appid, {}).get("title", appid)
            n = len(self._search_queue)
            self.set_status(
                f"Searching \"{title}\""
                + (f"  —  {n} more in queue" if n else "") + "…"
            )
            self._do_search(appid)

        elif self._ratings_queue:
            self._queue_active = True
            appids = list(self._ratings_queue)
            self._ratings_queue.clear()
            n = len(appids)
            self.set_status(f"Fetching ratings for {n} game{'s' if n != 1 else ''}…")
            self._fetch_all_ratings(appids)

        else:
            self._queue_active = False
            self._current_appid = None
            self._reload_rows()
            self.set_status("Enrichment complete")

    @work(thread=True)
    def _do_search(self, appid: str) -> None:
        """Search MobyGames for one game. Runs in a thread."""
        games = database.load_games()
        game = games.get(appid)
        if not game:
            self.app.call_from_thread(self._advance_queue)
            return

        api_key = self.app.config["mobygames"]["api_key"]
        try:
            candidates = mobygames.search_games(game["title"], api_key)
        except Exception as exc:
            self.app.call_from_thread(
                self.set_status, f"Search error for \"{game['title']}\": {exc}"
            )
            self.app.call_from_thread(self._advance_queue)
            return

        if len(candidates) == 0:
            self.app.call_from_thread(self._on_unmatched, appid, "unrated")
        elif len(candidates) == 1:
            self.app.call_from_thread(self._on_matched, appid, candidates[0]["game_id"])
        else:
            self.app.call_from_thread(self._show_disambiguation, appid, candidates)

    def _on_matched(self, appid: str, moby_id: int) -> None:
        """Store moby_id and queue ratings fetch. Main thread."""
        games = database.load_games()
        games[appid]["moby_id"] = moby_id
        database.save_games(games)
        self._ratings_queue.append(appid)
        self._reload_rows()
        self._advance_queue()

    def _on_unmatched(self, appid: str, flag: str) -> None:
        """Store flag for a game with no usable match. Main thread."""
        games = database.load_games()
        games[appid]["pegi_flag"] = flag
        database.save_games(games)
        self._reload_rows()
        self._advance_queue()

    def _show_disambiguation(self, appid: str, candidates: list) -> None:
        """Show disambiguation modal then continue queue. Main thread."""
        games = database.load_games()
        title = games.get(appid, {}).get("title", appid)
        remaining = len(self._search_queue)

        def on_result(selected: dict | None) -> None:
            if selected is None:
                self._on_unmatched(appid, "ambiguous")
            else:
                self._on_matched(appid, selected["game_id"])

        self.app.push_screen(
            DisambiguationModal(candidates, game_title=title, queue_remaining=remaining),
            on_result,
        )

    @work(thread=True)
    def _fetch_all_ratings(self, appids: list[str]) -> None:
        """Fetch per-platform ratings for all queued moby_ids. Runs in a thread."""
        games = database.load_games()
        api_key = self.app.config["mobygames"]["api_key"]
        rated = 0
        total = len(appids)

        for i, appid in enumerate(appids):
            game = games.get(appid)
            if not game or not game.get("moby_id"):
                continue
            try:
                rating = mobygames.fetch_pegi_for_moby_id(game["moby_id"], api_key)
                if rating is not None:
                    game["pegi_rating"] = rating
                    game["pegi_source"] = "mobygames"
                    rated += 1
                else:
                    game["pegi_flag"] = "unrated"
            except Exception:
                pass
            if (i + 1) % 5 == 0:
                database.save_games(games)
                self.app.call_from_thread(
                    self.set_status, f"Fetching ratings… {i + 1}/{total}"
                )

        database.save_games(games)
        self.app.call_from_thread(self._on_ratings_done, rated, total)

    def _on_ratings_done(self, rated: int, total: int) -> None:
        """Called on main thread when ratings fetch batch completes."""
        self._reload_rows()
        self.set_status(f"Ratings done — {rated}/{total} games rated via MobyGames")
        # Advance again: picks up any searches queued while ratings were running
        self._queue_active = False
        if self._search_queue or self._ratings_queue:
            self._advance_queue()

    # ------------------------------------------------------------------ delete

    def action_delete_game(self) -> None:
        appid = self._selected_appid()
        if not appid:
            return
        games = database.load_games()
        game = games.get(appid)
        if not game:
            return

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                del games[appid]
                database.save_games(games)
                self._reload_rows()
                self.set_status(f"Deleted '{game['title']}'")

        self.app.push_screen(ConfirmModal(f"Delete '{game['title']}'?"), on_confirm)

    # ------------------------------------------------------------------ edit rating

    def action_edit_rating(self) -> None:
        appid = self._selected_appid()
        if not appid:
            return
        games = database.load_games()
        game = games.get(appid)
        if not game:
            return

        def on_result(rating: int | None) -> None:
            if rating is not None:
                game["pegi_rating"] = rating
                game["pegi_source"] = "manual"
                game["pegi_flag"] = None
                database.save_games(games)
                self._reload_rows()
                self.set_status(f"Set '{game['title']}' to PEGI {rating} (manual)")

        self.app.push_screen(EditPegiModal(game), on_result)

    # ------------------------------------------------------------------ m key (force MobyGames lookup)

    def action_moby_lookup(self) -> None:
        appid = self._selected_appid()
        if not appid:
            return
        # Clear existing enrichment so the force re-lookup can overwrite it
        games = database.load_games()
        game = games.get(appid)
        if game:
            game["pegi_rating"] = None
            game["pegi_source"] = None
            game["pegi_flag"] = None
            game["moby_id"] = None
            database.save_games(games)
            self._reload_rows()
        self.enqueue_moby_search([appid])

    # ------------------------------------------------------------------ add to child

    def action_add_to_child(self) -> None:
        appid = self._selected_appid()
        if not appid:
            return
        games = database.load_games()
        game = games.get(appid)
        if not game:
            return
        child_list = children.list_children()
        if not child_list:
            self.set_status("No child profiles — create one on the Children screen (F3)")
            return

        def on_result(child_name: str | None) -> None:
            if child_name is None:
                return
            child = children.load_child(child_name)
            if child is None:
                return
            appid_int = int(appid)
            warning = ""
            if game.get("pegi_flag"):
                warning = f"Warning: game is flagged ({game['pegi_flag']}). "
            elif game.get("pegi_rating") and game["pegi_rating"] > child["max_age"]:
                warning = (
                    f"Warning: PEGI {game['pegi_rating']} > "
                    f"{child_name}'s max age {child['max_age']}. "
                )
            if appid_int not in child["library"]:
                child["library"].append(appid_int)
                child["library"].sort()
                children.save_child(child)
            self.set_status(
                f"{warning}Added '{game['title']}' to {child_name}'s collection"
            )

        self.app.push_screen(AddToChildModal(child_list, game), on_result)

    # ------------------------------------------------------------------ F1 fetch library

    @work(thread=True, exclusive=True)
    def start_fetch_library(self) -> None:
        self.app.call_from_thread(self.set_status, "Fetching Steam library…")
        try:
            cfg = self.app.config
            game_list = steam.fetch_library(
                cfg["steam"]["api_key"], cfg["steam"]["steam_id"]
            )
            games = database.load_games()
            added = 0
            for g in game_list:
                key = str(g["appid"])
                if key not in games:
                    games[key] = {
                        "appid": g["appid"],
                        "title": g.get("name", f"App {g['appid']}"),
                        "pegi_rating": None,
                        "pegi_source": None,
                        "pegi_flag": None,
                        "moby_id": None,
                    }
                    added += 1
            database.save_games(games)
            self.app.call_from_thread(self._reload_rows)
            self.app.call_from_thread(
                self.set_status,
                f"Fetch complete: {added} new, {len(game_list) - added} already present",
            )
        except Exception as exc:
            self.app.call_from_thread(self.set_status, f"Fetch error: {exc}")

    # ------------------------------------------------------------------ F2 enrich all

    @work(thread=True, exclusive=True)
    def start_enrich_all(self) -> None:
        """Steam pass first, then hand remaining games to the shared queue."""
        games = database.load_games()
        steam_key = self.app.config["steam"]["api_key"]

        unprocessed = [
            appid for appid, g in games.items()
            if g.get("pegi_rating") is None and g.get("pegi_flag") is None
        ]
        if not unprocessed:
            self.app.call_from_thread(self.set_status, "Nothing to enrich")
            return

        self.app.call_from_thread(
            self.set_status, f"Steam pass: checking {len(unprocessed)} games…"
        )
        steam_rated = 0
        still_needed: list[str] = []

        for i, appid in enumerate(unprocessed):
            game = games[appid]
            try:
                rating = steam.fetch_pegi_from_steam(int(appid))
                time.sleep(1)
                if rating:
                    game["pegi_rating"] = rating
                    game["pegi_source"] = "steam"
                    steam_rated += 1
                    continue
            except Exception:
                pass
            still_needed.append(appid)
            if (i + 1) % 20 == 0:
                database.save_games(games)
                self.app.call_from_thread(
                    self.set_status, f"Steam pass: {i + 1}/{len(unprocessed)}…"
                )

        database.save_games(games)
        self.app.call_from_thread(self._reload_rows)
        self.app.call_from_thread(
            self.set_status,
            f"Steam pass done: {steam_rated} rated. "
            f"Queuing {len(still_needed)} for MobyGames…",
        )
        self.app.call_from_thread(self.enqueue_moby_search, still_needed)
