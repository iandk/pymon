from rich.console import Console
from rich.text import Text
from rich.table import Table
from datetime import datetime
from typing import Dict, Optional
import threading

# Lazy console initialization - only created when needed
_console: Optional[Console] = None


def get_console() -> Console:
    """Get or create the Rich console (lazy initialization)"""
    global _console
    if _console is None:
        _console = Console()
    return _console


class ServerResult:
    def __init__(self, status: str, latency: Optional[str] = None, error: Optional[str] = None):
        self.status = status
        self.latency = latency
        self.error = error


class MonitorDisplay:
    def __init__(self):
        self.results: Dict[str, ServerResult] = {}
        self.lock = threading.Lock()

    def update_server(self, name: str, status: str, latency: Optional[str] = None, error: Optional[str] = None):
        with self.lock:
            self.results[name] = ServerResult(status, latency, error)

    def clear(self):
        # Clear the viewport and scrollback to avoid stacking frames in terminals that ignore partial clears
        console = get_console()
        console.clear()
        console.file.write("\033[3J")
        console.file.flush()

    def clear_results(self):
        with self.lock:
            self.results.clear()

    def print_header(self):
        now = datetime.now().strftime("%H:%M:%S")
        get_console().print(f"[bold blue]pymon[/bold blue] [dim]{now}[/dim]\n")

    def print_results(self):
        """Print all results in a clean, minimal format with aligned columns"""
        console = get_console()
        with self.lock:
            sorted_items = sorted(
                self.results.items(),
                key=lambda x: (0 if x[1].status == "Down" else 1, x[0].lower())
            )

            up_count = sum(1 for _, r in self.results.items() if r.status == "Up")
            down_count = sum(1 for _, r in self.results.items() if r.status == "Down")

            table = Table(
                show_header=False,
                box=None,
                pad_edge=False,
                collapse_padding=True,
                padding=(0, 1)
            )
            table.add_column("name", overflow="ellipsis", no_wrap=True, min_width=12, max_width=64)
            table.add_column("result", justify="right", no_wrap=True, min_width=8, max_width=18, overflow="ellipsis")

            for name, result in sorted_items:
                table.add_row(*self._format_row(name, result))

            console.print(table)

            # Summary
            console.print()
            summary = Text()
            summary.append(f"{up_count}", style="green")
            summary.append(" up", style="dim")
            if down_count > 0:
                summary.append("  ")
                summary.append(f"{down_count}", style="red")
                summary.append(" down", style="dim")
            console.print(summary)

    def _format_row(self, name: str, result: ServerResult):
        status_icon = "[green]●[/green]" if result.status == "Up" else "[red]●[/red]"
        display_name = name if len(name) <= 60 else name[:57] + "..."
        name_col = f"{status_icon} {display_name}"

        result_col = ""
        if result.status == "Up" and result.latency:
            latency_str = result.latency.replace(" ms", "").replace("ms", "")
            try:
                latency_val = float(latency_str)
                style = "green" if latency_val < 50 else "yellow" if latency_val < 150 else "red"
                result_col = f"[{style}]{latency_val:,.0f} ms[/{style}]"
            except ValueError:
                result_col = f"[dim]{result.latency}[/dim]"
        elif result.error:
            err = result.error if len(result.error) <= 20 else result.error[:17] + "..."
            result_col = f"[red dim]{err}[/red dim]"

        return name_col, result_col


_display: Optional[MonitorDisplay] = None


def get_display() -> MonitorDisplay:
    global _display
    if _display is None:
        _display = MonitorDisplay()
    return _display


def reset_display():
    global _display
    _display = None
