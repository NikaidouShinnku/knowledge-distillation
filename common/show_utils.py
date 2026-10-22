from consoles import print_markdown
from rich.text import Text
from itertools import cycle
from contextlib import contextmanager
from time import perf_counter


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
        print(f"[{title}]", flush=True)
        chunks = []
        for chunk in res:
            if chunk:
                print(chunk, end="", flush=True)
                chunks.append(chunk)
        print()
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
