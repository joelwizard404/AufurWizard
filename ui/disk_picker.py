from __future__ import annotations

import re
import subprocess
import sys
import threading
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button, Footer, Header, Label,
    ProgressBar, Select, Static,
)

from ..core.scanner import list_disks
from ..core.shredder import EventType, ShredEvent, shred_block_device
from ..core.standards import ALL_STANDARDS
from ..utils.logger import log_operation
from ..utils.permissions import require_root_for_device


_STANDARD_OPTIONS = [(s.name, s.id) for s in ALL_STANDARDS.values()]


class DiskPicker(Screen):
    TITLE = "Shred Disk / Partition"
    CSS = """
    DiskPicker {
        align: center middle;
    }

    #card {
        width: 70;
        height: auto;
        border: round $error;
        padding: 1 2;
    }

    #warning {
        color: $error;
        text-style: bold;
        margin-bottom: 1;
    }

    #status {
        margin-top: 1;
        color: $text-muted;
        height: 3;
    }

    .row {
        height: auto;
        margin-bottom: 1;
    }

    Button {
        margin-right: 1;
    }
    """

    BINDINGS = [Binding("escape", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="card"):
            yield Label(
                "⚠  This will permanently destroy all data on the selected device.",
                id="warning",
            )
            yield Label("Device", classes="row")
            yield Select(self._disk_options(), id="disk_select")
            yield Label("Standard", classes="row")
            yield Select(_STANDARD_OPTIONS, value="dod3", id="standard_select")
            with Horizontal(classes="row"):
                yield Button("Wipe Device", variant="error", id="btn_wipe")
                yield Button("Back", id="btn_back")
            yield ProgressBar(total=100, show_eta=False, id="progress")
            yield Static("", id="status")
        yield Footer()

    def _disk_options(self) -> list[tuple[str, str]]:
        disks = list_disks()
        options: list[tuple[str, str]] = []
        
        if sys.platform == "win32":
            for pd_label, pd_path in _list_physical_drives_windows():
                options.append((pd_label, pd_path))

        for d in disks:
            options.append((
                f"{d.device}  [{d.fstype}]  {d.total_human}  {d.mountpoint}",
                d.device,
            ))

        return options or [("No disks found", "")]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_back":
            self.app.pop_screen()
        elif event.button.id == "btn_wipe":
            self._start_wipe()

    def _start_wipe(self) -> None:
        device_str = self.query_one("#disk_select", Select).value
        standard_id = self.query_one("#standard_select", Select).value

        if not device_str:
            self._set_status("[red]No device selected.[/red]")
            return

        device = Path(str(device_str))
        err = require_root_for_device(device)
        if err:
            self._set_status(f"[red]{err}[/red]")
            return

        from ..core.standards import get
        standard = get(str(standard_id))

        self._set_status(
            f"Wiping [bold]{device}[/bold] with [bold]{standard.name}[/bold]…"
        )
        self.query_one("#btn_wipe", Button).disabled = True
        self.query_one("#progress", ProgressBar).update(progress=0)
        self._bytes_written = 0

        def run() -> None:
            ok = shred_block_device(device, standard, self._on_event)
            log_operation(
                target=str(device),
                standard_id=standard.id,
                standard_name=standard.name,
                success=int(ok),
                errors=int(not ok),
                bytes_wiped=self._bytes_written,
            )
            self.call_from_thread(self._on_done, ok)

        threading.Thread(target=run, daemon=True).start()

    def _on_event(self, event: ShredEvent) -> None:
        if event.type == EventType.PASS_PROGRESS:
            self._bytes_written = event.bytes_written
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
                self._set_status, f"[red]{event.message}[/red]"
            )

    def _on_done(self, success: bool) -> None:
        self.query_one("#btn_wipe", Button).disabled = False
        self.query_one("#progress", ProgressBar).update(progress=100)
        if success:
            self._set_status("[green]Wipe complete.[/green]")
        else:
            self._set_status("[red]Wipe failed. Check status above.[/red]")

    def _set_status(self, text: str) -> None:
        self.query_one("#status", Static).update(text)

def _list_physical_drives_windows() -> list[tuple[str, str]]:
    """Return (label, path) pairs for \\.\PhysicalDriveN on Windows."""
    drives: list[tuple[str, str]] = []
    try:
        result = subprocess.run(
            [
                "wmic", "diskdrive",
                "get", "DeviceID,Size,Model",
                "/format:csv",
            ],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 4 or not parts[1].startswith("\\\\.\\"):
                continue
            device_id = parts[1]
            model     = parts[2]
            size_raw  = parts[3]
            try:
                size_label = _human_size(int(size_raw))
            except ValueError:
                size_label = "? GB"
            label = f"{device_id}  {model}  {size_label}  [physical]"
            drives.append((label, device_id))
    except Exception:
        pass
    return drives


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} PB"
