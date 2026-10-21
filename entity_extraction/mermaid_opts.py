import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from common.show_utils import show_response


def display_relationship_descriptions(relationships):
    if relationships:
        text = "\n".join(f"{item['id']}. {item['description']}" for item in relationships)
        show_response(text, title="关系备注", title_align="center")


def create_mermaid_png_and_display(mermaid_code, relationships, display_in_term=True,
                                    output_file="task_result/knowledge_graph.png"):
    executable = os.getenv("MERMAID_CLI") or shutil.which("mmdc")
    if not executable:
        raise FileNotFoundError("Set MERMAID_CLI or install mmdc on PATH")
    output = Path(output_file).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "graph.mmd"
        source.write_text(mermaid_code, encoding="utf-8")
        command = [executable, "-i", str(source), "-t", "dark", "-b", "transparent", "-o", str(output)]
        config = os.getenv("MERMAID_PUPPETEER_CONFIG")
        if config:
            command.extend(["-p", config])
        subprocess.run(command, check=True, capture_output=True, timeout=90)
    if not output.is_file():
        raise FileNotFoundError("Mermaid did not produce an image")
    wezterm = shutil.which("wezterm")
    if display_in_term and wezterm:
        subprocess.run([wezterm, "imgcat", str(output)], check=True, timeout=30)
    print(f"Knowledge graph: {output}")
    display_relationship_descriptions(relationships)
    return str(output)
