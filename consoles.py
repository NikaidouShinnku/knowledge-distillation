import re
from itertools import cycle

import rich
from colorama import Fore, Style
from colorama import init as colorama_init
from rich.box import DOUBLE, ROUNDED
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.style import Style
from rich.syntax import Syntax
from rich.text import Text

colorama_init(autoreset=True)


def print_with_color(text: str, color: str = ""):
    """
    Print text with specified color using ANSI escape codes from Colorama library.

    :param text: The text to print.
    :param color: The color of the text (options: red, green, yellow, blue, magenta, cyan, white, black).
    """
    color_mapping = {
        "red": Fore.RED,
        "green": Fore.GREEN,
        "yellow": Fore.YELLOW,
        "blue": Fore.BLUE,
        "magenta": Fore.MAGENTA,
        "cyan": Fore.CYAN,
        "white": Fore.WHITE,
        "black": Fore.BLACK,
    }

    selected_color = color_mapping.get(color.lower(), "")
    colored_text = selected_color + text + Style.RESET_ALL

    print(colored_text)


def yellow_bold(s):
    return f"\033[1m\033[33m{s}\033[0m"


def red_bold(s):
    return f"\033[1m\033[31m{s}\033[0m"


def green_bold(s):
    return f"\033[1m\033[32m{s}\033[0m"


def blue_bold(s):
    return f"\033[1m\033[34m{s}\033[0m"


def purple_bold(s):
    return f"\033[1m\033[35m{s}\033[0m"


def cyan_bold(s):
    return f"\033[1m\033[36m{s}\033[0m"


def white_bold(s):
    return f"\033[1m\033[37m{s}\033[0m"


def red(s):
    return f"\033[31m{s}\033[0m"


def green(s):
    return f"\033[32m{s}\033[0m"


def yellow(s):
    return f"\033[33m{s}\033[0m"


def blue(s):
    return f"\033[34m{s}\033[0m"


def purple(s):
    return f"\033[35m{s}\033[0m"


def cyan(s):
    return f"\033[36m{s}\033[0m"


def white(s):
    return f"\033[37m{s}\033[0m"


def black_bg(s):
    return f"\033[40m{s}\033[0m"


def red_bg(s):
    return f"\033[41m{s}\033[0m"


def green_bg(s):
    return f"\033[42m{s}\033[0m"


def yellow_bg(s):
    return f"\033[43m{s}\033[0m"


def blue_bg(s):
    return f"\033[44m{s}\033[0m"


def purple_bg(s):
    return f"\033[45m{s}\033[0m"


def cyan_bg(s):
    return f"\033[46m{s}\033[0m"


def white_bg(s):
    return f"\033[47m{s}\033[0m"


def reset_all_attributes(s):
    return f"\033[0m{s}\033[0m"


def bold(s):
    return f"\033[1m{s}\033[0m"


def italic(s):
    return f"\033[3m{s}\033[0m"


def underline(s):
    return f"\033[4m{s}\033[0m"


def blink(s):
    return f"\033[5m{s}\033[0m"


def reverse_view(s):
    return f"\033[7m{s}\033[0m"


def invisible(s):
    return f"\033[8m{s}\033[0m"


def strikethrough(s):
    return f"\033[9m{s}\033[0m"


_console_style_pattern = re.compile(r"^(\033\[\d+m)+")


def extract_console_color_code_from_head(s):
    """
    Extracts the console color code from the given string.

    Args:
        s (str): The input string to extract the console color code from.

    Returns:
        str or None: The console color code if found, None otherwise.
    """
    match = _console_style_pattern.match(s)
    if match:
        return match.group(0)
    return None


def print_code(
    code: str,
    *,
    title: str = None,
    language: str = "python",
    theme: str = "monokai",
    style: str = "bold green",
    console: Console = None,
    width: int = 120,  # Specify the width for wrapping
) -> None:
    """
    Prints the given code with syntax highlighting, formatting, and word wrapping.

    Args:
        code (str): The code to be printed.
        language (str, optional): The language of the code. Defaults to "python".
        theme (str, optional): The theme for syntax highlighting. Defaults to "monokai".
        style (str, optional): The style for formatting. Defaults to "bold green".
        console (Console, optional): The console object to use for printing. If not provided, a new console will be created.
        title (str, optional): The title of the code block. If provided, it will be displayed in yellow bold style.
        width (int, optional): The maximum width of the code block. Defaults to 120.

    Returns:
        None
    """
    if console is None:
        console = Console()

    # Create a Syntax object with word wrapping
    syntax = Syntax(code, language, theme=theme, word_wrap=True)

    # Check if title is provided and adjust the title style
    if title is not None:
        title = Text(title, style="bold yellow")
        # Create a Panel object with title and width settings
        panel = Panel(
            syntax, title=title, style=style, border_style="bold blue", width=width
        )
    else:
        # Create a Panel object without title but with width setting
        panel = Panel(syntax, style=style, border_style="bold blue", width=width)

    console.print(panel)

def place_to_center(layout, *, total_width):
    if layout.width > total_width:
        return layout

    left_padding = (total_width - layout.width) // 2
    left_padding = max(left_padding, 0)  # Ensure left_padding is not negative

    # Apply padding to center the panel
    return Padding(layout, (0, 0, 0, left_padding))

def offset_panel(layout, *, total_width, offset):
    if layout.width > total_width:
        return layout

    return Padding(layout, (0, 0, 0, offset))

def print_markdown(
    markdown_text: str,
    *,
    style: str = "bold white",
    console: Console = None,
    title: str = None,
    bgcolor: str = "black",
    title_align: str = "center",
    width: int = 120,
    offset: int = None,
    border_color: str = "dark_cyan"
):
    if console is None:
        console = Console()

    markdown = Markdown(markdown_text)
    if offset is not None:
        offset = min(max(offset, 0), max(console.width - 40, 0))
    width = max(1, min(width, console.width - (offset or 0)))

    # title = Text(title, style="bold bright_cyan") if title else None
    if title:
        segments = title.split('/')
        colors = cycle(["red", "cyan",  "magenta", "blue", "yellow", "white"])
        styled_title = Text()
        for index, (seg, color) in enumerate(zip(segments, colors)):
            styled_title.append(seg, style=color)
            if index < len(segments) - 1:
                styled_title.append('/', style="white")
    else:
        styled_title = None

    panel = Panel(
        markdown,
        title_align=title_align,
        title=styled_title,
        box=ROUNDED,
        padding=(1, 1),
        style=style,
        width=width,
        border_style=border_color,
    )
    panel.style = Style(color="white", bgcolor=bgcolor)

    if offset is None:
        console.print(place_to_center(panel, total_width=console.size.width))
    else:
        console.print(offset_panel(panel, total_width=console.size.width, offset=offset))

def print_pair(*, src: str, dst: str, src_title: str, dst_title: str) -> None:
    """
    Prints a pair of source and destination strings in a formatted console output.

    Args:
        src (str): The source string to be displayed.
        dst (str): The destination string to be displayed.
        src_title (str): The title for the source panel.
        dst_title (str): The title for the destination panel.

    Returns:
        None
    """
    console = rich.console.Console()
    # Create the title for the source panel
    src_title = Text(src_title, style="bold green underline")
    src_panel = Panel(src, title=src_title, style="on blue")

    # Create the title for the destination panel
    dst_title = Text(dst_title, style="bold yellow underline")
    dst_panel = Panel(dst, title=dst_title, style="on red")

    # Create a group of panels
    panel_group = Group(src_panel, dst_panel)
    # Print the group of panels
    console.print(panel_group)
