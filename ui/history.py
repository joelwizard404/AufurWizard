from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header

from ..utils.logger import read_log


class HistoryScreen(Screen):
    TITLE = "History"

    BINDINGS = [Binding("escape", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#table", DataTable)
        table.add_columns("Time", "Target", "Standard", "✓", "✗", "Wiped")

        for entry in read_log():
            table.add_row(
                entry.get("ts", "")[:19].replace("T", " "),
                entry.get("target", ""),
                entry.get("standard", ""),
                str(entry.get("success", 0)),
                str(entry.get("errors", 0)),
                _human(entry.get("bytes_wiped", 0)),
            )

        if not table.row_count:
            table.add_row("–", "No entries yet.", "", "", "", "")


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} PB"
