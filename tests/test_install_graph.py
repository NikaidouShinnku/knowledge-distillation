import contextlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from common.tooling import mermaid_command
from entity_extraction.mermaid_opts import create_mermaid_png_and_display
import install


class InstallGraphTests(unittest.TestCase):
    def test_windows_mermaid_launcher_uses_node_without_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            launcher = root / 'mmdc.cmd'
            launcher.write_text('@echo off', encoding='utf-8')
            script = root / 'node_modules/@mermaid-js/mermaid-cli/src/cli.js'
            script.parent.mkdir(parents=True)
            script.write_text('', encoding='utf-8')
            with patch.dict(os.environ, {'MERMAID_CLI': str(launcher)}), patch('common.tooling.shutil.which', side_effect=lambda name: 'node.exe' if name == 'node' else None):
                self.assertEqual(mermaid_command(), ['node.exe', str(script)])

    def test_graph_source_is_saved_and_windows_viewer_opens(self):
        def render(command, **kwargs):
            Path(command[command.index('-o') + 1]).write_bytes(b'PNG')
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            output = Path(directory) / 'graph.png'
            with patch('entity_extraction.mermaid_opts.mermaid_command', return_value=['node', 'cli.js']), patch('entity_extraction.mermaid_opts.browser_executable', return_value=None), patch('entity_extraction.mermaid_opts.shutil.which', return_value=None), patch('entity_extraction.mermaid_opts.subprocess.run', side_effect=render), patch('entity_extraction.mermaid_opts.os.startfile', create=True) as viewer, patch('entity_extraction.mermaid_opts.webbrowser.open'), contextlib.redirect_stdout(io.StringIO()):
                create_mermaid_png_and_display('graph TD\n  A --> B', [], output_file=output)
            self.assertEqual(output.with_suffix('.mmd').read_text(encoding='utf-8'), 'graph TD\n  A --> B')
            if os.name == 'nt':
                viewer.assert_called_once_with(str(output.resolve()))

    def test_missing_renderer_preserves_editable_source(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'graph.png'
            with patch('entity_extraction.mermaid_opts.mermaid_command', side_effect=FileNotFoundError('missing')):
                with self.assertRaises(FileNotFoundError):
                    create_mermaid_png_and_display('graph TD\n  A --> B', [], display_in_term=False, output_file=output)
            self.assertTrue(output.with_suffix('.mmd').exists())

    def test_installer_requires_graph_tools_and_runs_render_check(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(install, '__file__', str(Path(directory) / 'install.py')), patch('install.npm_command', return_value=['npm']), patch('install.node_command', return_value=['node', '']), patch('install.subprocess.check_output', return_value='v22.13.0'), patch('install.venv.EnvBuilder'), patch('install.browser_executable', return_value='msedge.exe'), patch('install.subprocess.run') as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(install.main(), 0)
            commands = [call.args[0] for call in run.call_args_list]
            self.assertIn('requirements.txt', commands[0][-1])
            self.assertEqual(commands[1][:2], ['npm', 'install'])
            self.assertIn('create_mermaid_png_and_display', commands[-1][-1])
            captured = []
            with patch('entity_extraction.mermaid_opts.create_mermaid_png_and_display', side_effect=lambda text, *args, **kwargs: captured.append(text)):
                exec(commands[-1][-1], {})
            self.assertTrue(captured[0].startswith('graph TD\n'))

    def test_installer_stops_on_dependency_failure(self):
        with patch('install.npm_command', return_value=['npm']), patch('install.node_command', return_value=['node', '']), patch('install.subprocess.check_output', return_value='v22.13.0'), patch('install.venv.EnvBuilder'), patch('install.subprocess.run', side_effect=subprocess.CalledProcessError(1, 'pip')) as run, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(install.main(), 1)
            self.assertEqual(run.call_count, 1)
