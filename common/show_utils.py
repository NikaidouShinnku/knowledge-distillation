from consoles import print_markdown
from rich.text import Text
from itertools import cycle
from contextlib import contextmanager
from time import perf_counter
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.padding import Padding
from rich import box


@contextmanager
def processing(label):
    started = perf_counter()
    print(f"[{label}...]", flush=True)
    try:
        yield
    finally:
        print(f"[{label}: {perf_counter() - started:.1f}s]", flush=True)

def show_response(
        res,
        *,
        no_pretty:bool = False,
        title:str,
        title_align: str = "center",
        width: int = 120,
        offset:int = None,
        border_color: str = "dark_cyan"
):
    if not isinstance(res, str):
        chunks = []
        if no_pretty:
            for chunk in res:
                if chunk:
                    print(chunk, end="", flush=True)
                    chunks.append(chunk)
            print()
            return "".join(chunks)
        console = Console()
        padding = min(max(offset or 0, 0), max(console.width - 40, 0))
        panel_width = max(1, min(width, console.width - padding))
        if offset is None:
            padding = max((console.width - panel_width) // 2, 0)

        def render():
            panel = Panel(Markdown("".join(chunks) or "Waiting for reply..."), title=Text(title, style="bold cyan"), title_align=title_align, width=panel_width, border_style=border_color, box=box.ROUNDED, padding=(1, 1))
            return Padding(panel, (0, 0, 0, padding))

        try:
            with Live(render(), console=console, refresh_per_second=8, vertical_overflow="visible") as live:
                for chunk in res:
                    if chunk:
                        chunks.append(chunk)
                        live.update(render())
        finally:
            close = getattr(res, "close", None)
            if close:
                close()
        return "".join(chunks)
    if isinstance(res, str):
        if no_pretty:
            print(res)
        else:
            print_markdown(res, title=title, title_align=title_align, width=width, offset=offset, border_color=border_color)
        return res


def to_progress_bar(
        *,
        n_done: int,
        n_total: int,
        bar_len: int = 20
):
    done_ratio = min(1, max(0, n_done / n_total)) if n_total > 0 else 0
    done_bar_count = round(done_ratio * bar_len)
    return "[" + "#" * done_bar_count + "-" * (bar_len - done_bar_count) + "]"
