import os
from pathlib import Path
import subprocess
import sys
import venv
import json

from common.tooling import browser_executable, npm_command, node_command


def main():
    if sys.version_info[:2] != (3, 12):
        print('Run this installer with Python 3.12 (64-bit).')
        return 1
    if sys.maxsize <= 2 ** 32:
        print('Use 64-bit Python 3.12.')
        return 1
    root = Path(__file__).resolve().parent
    try:
        npm = npm_command()
        node = node_command('')[0]
        version = subprocess.check_output([node, '--version'], text=True).strip().lstrip('v')
        if tuple(map(int, version.split('.')[:3])) < (22, 13, 0):
            raise RuntimeError('Node.js 22.13 or newer is required.')
        environment = root / '.venv'
        python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        if not python.is_file():
            print('Creating .venv...', flush=True)
            venv.EnvBuilder(with_pip=True).create(environment)
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(root / 'requirements.txt')], cwd=root, check=True)
        settings = os.environ.copy()
        browser = browser_executable()
        if browser or settings.get('MERMAID_PUPPETEER_CONFIG'):
            settings['PUPPETEER_SKIP_DOWNLOAD'] = 'true'
        subprocess.run([*npm, 'install', '--no-audit', '--no-fund'], cwd=root, env=settings, check=True)
        if not browser and not settings.get('MERMAID_PUPPETEER_CONFIG'):
            package = root / 'node_modules/puppeteer/package.json'
            metadata = json.loads(package.read_text(encoding='utf-8'))
            cli = metadata['bin']
            if isinstance(cli, dict):
                cli = cli['puppeteer']
            subprocess.run([node, str(package.parent / cli), 'browsers', 'install', 'chrome'], cwd=root, env=settings, check=True)
        subprocess.run([str(python), '-m', 'pip', 'check'], cwd=root, check=True)
        subprocess.run([str(python), '-c', "from entity_extraction.mermaid_opts import create_mermaid_png_and_display; create_mermaid_png_and_display('graph TD\\n  A[Installation] --> B[Ready]', [], display_in_term=False, output_file='task_result/install-check.png')"], cwd=root, check=True)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'Installation failed: {error}', file=sys.stderr)
        return 1
    print('Installation verified. Configure .env, then run:')
    print(f'"{python}" main.py')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
