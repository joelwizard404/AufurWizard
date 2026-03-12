from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Label, ListItem, ListView


class Dashboard(App):
    TITLE = "AufurWizard"
    CSS = """
    Screen {
        align: center middle;
    }

    #menu {
        width: 50;
        height: auto;
        border: round $primary;
        padding: 1 2;
    }

    #menu > ListItem {
        padding: 0 1;
    }

    #menu > ListItem:hover {
        background: $primary 20%;
    }

    #menu > ListItem.--highlight {
        background: $primary 40%;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ListView(
            ListItem(Label("  Shred files / folders"), id="files"),
            ListItem(Label("  Shred disk / partition"), id="disk"),
            ListItem(Label("  View history"), id="history"),
            ListItem(Label("  Quit"), id="quit"),
            id="menu",
        )
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        match event.item.id:
            case "files":
                from .file_picker import FilePicker
                self.push_screen(FilePicker())
            case "disk":
                from .disk_picker import DiskPicker
                self.push_screen(DiskPicker())
            case "history":
                from .history import HistoryScreen
                self.push_screen(HistoryScreen())
            case "quit":
                self.exit()
