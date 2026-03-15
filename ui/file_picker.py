from __future__ import annotations

import threading
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button, Footer, Header, Input, Label,
    ProgressBar, Select, Static,
)

from ..core.shredder import EventType, ShredEvent, shred_directory, shred_file
from ..core.standards import ALL_STANDARDS
from ..utils.logger import log_operation
from ..utils.permissions import can_write
from .path_browser import PathBrowser


_STANDARD_OPTIONS = [(s.name, s.id) for s in ALL_STANDARDS.values()]


class FilePicker(Screen):
    TITLE = "Shred Files / Folders"
    CSS = """
    FilePicker {
        align: center middle;
    }

    #card {
        width: 64;
        height: auto;
        border: round $primary;
        padding: 1 2;
    }

    #status {
        margin-top: 1;
        color: $text-muted;
        height: 3;
    }

    #progress {
        margin-top: 1;
    }

    .row {
        height: auto;
        margin-bottom: 1;
    }

    /* path row: input stretches, browse button stays fixed */
    #path-row {
        height: auto;
        margin-bottom: 1;
    }

    #path_input {
        width: 1fr;
    }

    #btn_browse {
        width: auto;
        margin-left: 1;
    }

    Button {
        margin-right: 1;
    }
    """

    BINDINGS = [Binding("escape", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="card"):
            yield Label("Path (file or folder)")
            with Horizontal(id="path-row"):
                yield Input(placeholder="/home/user/secret_stuff", id="path_input")
                yield Button("Browse…", id="btn_browse")
            yield Label("Standard", classes="row")
            yield Select(_STANDARD_OPTIONS, value="dod3", id="standard_select")
            with Horizontal(classes="row"):
                yield Button("Shred", variant="error", id="btn_shred")
                yield Button("Back", id="btn_back")
            yield ProgressBar(total=100, show_eta=False, id="progress")
            yield Static("", id="status")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn_back":
                self.app.pop_screen()
            case "btn_shred":
                self._start_shred()
            case "btn_browse":
                self._open_browser()

    def _open_browser(self) -> None:
        """Push PathBrowser modal; fill the input when user confirms."""
        current = self.query_one("#path_input", Input).value.strip()
        start = Path(current) if current else None

        def _on_dismiss(selected: Path | None) -> None:
            if selected is not None:
                self.query_one("#path_input", Input).value = str(selected)

        self.app.push_screen(PathBrowser(start=start), _on_dismiss)

    def _start_shred(self) -> None:
        path_str = self.query_one("#path_input", Input).value.strip()
        standard_id = self.query_one("#standard_select", Select).value
        path = Path(path_str)

        if not path.exists():
            self._set_status(f"[red]Path not found: {path_str}[/red]")
            return
        if not can_write(path):
            self._set_status("[red]No write permission.[/red]")
            return

        from ..core.standards import get
        standard = get(str(standard_id))

        self._set_status(f"Shredding with [bold]{standard.name}[/bold]…")
        self.query_one("#btn_shred", Button).disabled = True
        self.query_one("#btn_browse", Button).disabled = True
        self.query_one("#progress", ProgressBar).update(progress=0)

        self._bytes_total   = 0
        self._bytes_written = 0
        self._success       = 0
        self._errors        = 0

        def run() -> None:
            if path.is_file():
                ok = shred_file(path, standard, self._on_event)
                self._success = int(ok)
                self._errors  = int(not ok)
            else:
                self._success, self._errors = shred_directory(
                    path, standard, self._on_event
                )
            log_operation(
                target=str(path),
                standard_id=standard.id,
                standard_name=standard.name,
                success=self._success,
                errors=self._errors,
                bytes_wiped=self._bytes_written,
            )
            self.call_from_thread(self._on_done)

        threading.Thread(target=run, daemon=True).start()

    def _on_event(self, event: ShredEvent) -> None:
        if event.type == EventType.PASS_PROGRESS:
            self._bytes_written = event.bytes_written
            self._bytes_total   = event.bytes_total
            if event.bytes_total:
                pct = int(event.bytes_written / event.bytes_total * 100)
                self.call_from_thread(
                    self.query_one("#progress", ProgressBar).update, progress=pct
                )
                self.call_from_thread(
                    self._set_status,
                    f"Pass {event.pass_index + 1}/{event.pass_total} – "
                    f"{event.pass_label}  ({pct}%)",
                )
        elif event.type == EventType.ERROR:
            self.call_from_thread(
                self._set_status, f"[red]Error: {event.message}[/red]"
            )

    def _on_done(self) -> None:
        self.query_one("#btn_shred", Button).disabled = False
        self.query_one("#btn_browse", Button).disabled = False
        self.query_one("#progress", ProgressBar).update(progress=100)
        if self._errors:
            self._set_status(
                f"[yellow]Done with {self._errors} error(s). "
                f"{self._success} file(s) shredded.[/yellow]"
            )
        else:
            self._set_status(
                f"[green]Done! {self._success} file(s) shredded.[/green]"
            )

    def _set_status(self, text: str) -> None:
        self.query_one("#status", Static).update(text)
