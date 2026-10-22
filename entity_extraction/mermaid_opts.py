import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import json
import webbrowser

from common.show_utils import show_response
from common.tooling import mermaid_command, browser_executable


def display_relationship_descriptions(relationships):
    if relationships:
        text = "\n".join(f"{item['id']}. {item['description']}" for item in relationships)
        show_response(text, title="关系备注", title_align="center")


def create_mermaid_png_and_display(mermaid_code, relationships, display_in_term=True,
                                    output_file="task_result/knowledge_graph.png"):
    output = Path(output_file).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    source = output.with_suffix('.mmd')
    source.write_text(mermaid_code, encoding='utf-8')
    executable = mermaid_command()
    with tempfile.TemporaryDirectory() as directory:
        command = [*executable, "-i", str(source), "-t", "dark", "-b", "transparent", "-o", str(output)]
        config = os.getenv("MERMAID_PUPPETEER_CONFIG")
        if not config:
            browser = browser_executable()
            if browser:
                config = str(Path(directory) / 'puppeteer.json')
                Path(config).write_text(json.dumps({'executablePath': browser}), encoding='utf-8')
        if config:
            command.extend(["-p", config])
        try:
            subprocess.run(command, check=True, capture_output=True, timeout=90)
        except subprocess.CalledProcessError as error:
            detail = error.stderr.decode('utf-8', errors='replace') if isinstance(error.stderr, bytes) else (error.stderr or '')
            detail = detail if len(detail) <= 1500 else detail[:900] + '\n...\n' + detail[-600:]
            raise RuntimeError(f'Mermaid rendering failed: {detail}') from error
    if not output.is_file():
        raise FileNotFoundError("Mermaid did not produce an image")
    wezterm = shutil.which("wezterm")
    if display_in_term:
        try:
            if wezterm and (os.getenv('WEZTERM_PANE') or os.getenv('TERM_PROGRAM') == 'WezTerm'):
                subprocess.run([wezterm, "imgcat", str(output)], check=True, timeout=30)
            elif os.name == 'nt':
                os.startfile(str(output))
            else:
                webbrowser.open(output.as_uri())
        except (OSError, subprocess.SubprocessError) as error:
            print(f'Image saved; open it manually if the viewer is unavailable: {error}')
    print(f"Knowledge graph: {output}")
    print(f"Mermaid source: {source}")
    display_relationship_descriptions(relationships)
    return str(output)
