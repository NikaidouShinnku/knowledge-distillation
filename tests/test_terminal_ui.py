import io
import unittest
from unittest.mock import patch

from rich.console import Console
from rich.cells import cell_len
from common.show_utils import show_response
from consoles import print_markdown


class TerminalUITests(unittest.TestCase):
    def test_streaming_keeps_role_panel_and_history_text(self):
        output = io.StringIO()
        console = Console(file=output, width=100, color_system=None)
        with patch('common.show_utils.Console', return_value=console):
            reply = show_response(iter(['Could you ', 'give an example?']), title='Question proposer / Group discussion', offset=50, width=60)
        rendered = output.getvalue()
        self.assertEqual(reply, 'Could you give an example?')
        self.assertRegex(rendered, '[╭┌]')
        self.assertIn('Group discussion', rendered)
        self.assertIn('give an example?', rendered)
        self.assertTrue(all(cell_len(line) <= 100 for line in rendered.splitlines()))

    def test_static_panels_fit_narrow_terminal(self):
        output = io.StringIO()
        console = Console(file=output, width=50, color_system=None)
        print_markdown('[OK] Relevant question.', console=console, title='Reviewer', width=60, offset=40)
        self.assertIn('Reviewer', output.getvalue())
        self.assertTrue(all(cell_len(line) <= 50 for line in output.getvalue().splitlines()))

    def test_plain_stream_remains_available(self):
        output = io.StringIO()
        with patch('sys.stdout', output):
            self.assertEqual(show_response(iter(['Hello', '!']), title='Interviewer', no_pretty=True), 'Hello!')
        self.assertEqual(output.getvalue(), 'Hello!\n')
