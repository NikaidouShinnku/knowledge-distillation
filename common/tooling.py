import os
from pathlib import Path
import shutil


def node_command(script):
    node = shutil.which('node')
    if not node:
        raise FileNotFoundError('Install Node.js 22.13 or newer, including npm, then reopen the terminal.')
    return [node, str(script)]


def npm_command():
    npm = shutil.which('npm') or shutil.which('npm.cmd')
    if not npm:
        raise FileNotFoundError('Install Node.js 22.13 or newer, including npm, then reopen the terminal.')
    cli = Path(npm).parent / 'node_modules/npm/bin/npm-cli.js'
    if cli.is_file():
        return node_command(cli)
    if Path(npm).suffix.lower() in ('.cmd', '.bat'):
        raise FileNotFoundError('npm-cli.js is missing. Repair the Node.js installation.')
    return [npm]


def mermaid_command():
    specified = os.getenv('MERMAID_CLI', '').strip()
    local = Path(__file__).resolve().parents[1] / 'node_modules/@mermaid-js/mermaid-cli/src/cli.js'
    executable = specified or (str(local) if local.is_file() else shutil.which('mmdc'))
    if not executable:
        raise FileNotFoundError('Mermaid CLI is missing. Run python install.py in the project directory.')
    executable = shutil.which(executable) or executable
    path = Path(executable)
    if path.suffix.lower() in ('.js', '.mjs', '.cjs'):
        return node_command(path)
    if path.suffix.lower() in ('.cmd', '.bat'):
        for candidate in (path.parent / 'node_modules/@mermaid-js/mermaid-cli/src/cli.js', path.parent.parent / '@mermaid-js/mermaid-cli/src/cli.js'):
            if candidate.is_file():
                return node_command(candidate)
        raise FileNotFoundError('Mermaid CLI launcher is incomplete. Run python install.py again.')
    return [executable]


def browser_executable():
    for name in ('chromium', 'chromium-browser', 'google-chrome', 'msedge'):
        executable = shutil.which(name)
        if executable:
            return executable
    candidates = [Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')]
    for variable, default in (('PROGRAMFILES', 'C:/Program Files'), ('PROGRAMFILES(X86)', 'C:/Program Files (x86)'), ('LOCALAPPDATA', '')):
        base = os.getenv(variable, default)
        if base:
            candidates.extend([Path(base) / 'Microsoft/Edge/Application/msedge.exe', Path(base) / 'Google/Chrome/Application/chrome.exe'])
    return next((str(path) for path in candidates if path.is_file()), None)
