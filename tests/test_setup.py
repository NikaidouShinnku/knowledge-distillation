import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from common.setup import choose, select_expert, select_topic, select_tone
from common.show_utils import to_progress_bar, show_response
from knowledge_graph.model import KnowledgeGraph


class SetupTests(unittest.TestCase):
    def test_existing_expert_is_selected_by_display_name(self):
        with tempfile.TemporaryDirectory() as directory:
            data = dict(name='Expert Name', age='30', sex='', education_level='', profession='Engineer', other='')
            Path(directory, 'expert.json').write_text(json.dumps(data), encoding='utf-8')
            with patch('common.setup.prompt', return_value='1'), contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(select_expert(directory), 'expert')
            self.assertIn('Expert Name', output.getvalue())

    def test_new_expert_is_saved_and_reusable(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('common.setup.prompt', side_effect=['x', '0', '', '../Alice <test>', '36', '', 'MSc', 'Engineer', 'Robotics']), contextlib.redirect_stdout(io.StringIO()):
                identifier = select_expert(directory)
            self.assertTrue(identifier.startswith('local-'))
            profile = json.loads(Path(directory, identifier + '.json').read_text(encoding='utf-8'))
            self.assertEqual(profile['name'], '../Alice <test>')
            self.assertEqual(profile['profession'], 'Engineer')
            with patch('common.setup.prompt', return_value='1'), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(select_expert(directory), identifier)

    def test_new_topic_validates_duration_and_objectives(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('common.setup.prompt', side_effect=['0', 'Robotics', 'Engineering', 'Designing robots', 'Sensors；Control', '0', 'text', '15']), contextlib.redirect_stdout(io.StringIO()):
                identifier = select_topic(directory)
            tree = KnowledgeGraph.model_validate_json(Path(directory, identifier + '.json').read_text(encoding='utf-8'))
            self.assertEqual(tree.estimated_minute, 15)
            self.assertEqual([obj.obj_description for obj in tree.objectives], ['Sensors', 'Control'])
            with patch('common.setup.prompt', return_value='1'), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(select_topic(directory), identifier)

    def test_bad_files_are_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'bad.json').write_text('{', encoding='utf-8')
            with patch('common.setup.prompt', side_effect=['0', 'Alice', '', '', '', '', '']), contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(select_expert(directory).startswith('local-'))

    def test_english_styles_do_not_contain_chinese_literary_styles(self):
        with patch('common.setup.prompt', side_effect=['7', '5']), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(select_tone('en-US'), 'Neutral')
        self.assertNotIn('甄嬛', output.getvalue())
        self.assertNotIn('鲁迅', output.getvalue())

    def test_menu_rejects_invalid_choices(self):
        with patch('common.setup.prompt', side_effect=['', '-1', '99', 'hello', '1']), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(choose('Choose', ['One']), 0)

    def test_terminal_symbols_are_portable(self):
        self.assertEqual(to_progress_bar(n_done=1, n_total=2, bar_len=4), '[##--]')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(show_response(iter(['Hello ', 'expert']), title='Interviewer'), 'Hello expert')
