import contextlib
import io
import itertools
import json
from pathlib import Path
import runpy
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from chat_history import ChatHistory
from knowledge_graph.model import Knowledge, KnowledgeGraph, Objective
from plan import plan_directory
from progress.progress import Progress
import main


class WorkflowTests(unittest.TestCase):
    def run_case(self, flags=(), commands=('Answer',), remaining=None, confirmation='N', restore=False, setup_choices=None, profile_directory=None):
        root = Path(main.__file__).parent
        tree = KnowledgeGraph.restore(str(Path(plan_directory()) / 'organism-classification-distill-plan'))
        parent = tree.objectives[0].id
        actions = json.dumps([{'action': 'add_new_knowledge_node', 'arguments': {'parent_id': parent, 'knowledge_detail': {'concept': 'Mammals', 'example': 'Whale'}}}])
        session = Mock()
        session.prompt.side_effect = list(commands)
        recorded = Mock(return_value='Recorded answer')
        original_open = open
        with tempfile.TemporaryDirectory() as directory, contextlib.ExitStack() as stack:
            if profile_directory is not None:
                for module in ('common.setup', 'agent.generation', 'agent.distill', 'agent.critique', 'agent.simulation'):
                    stack.enter_context(patch(module + '.interviewee_directory', return_value=profile_directory))
            snapshot = Path(directory) / 'snapshot.json'
            if restore:
                main.dump_snapshot(str(snapshot.with_suffix('')), tree.model_dump(), ChatHistory().model_dump(), ChatHistory().model_dump(), 'maria', 'retired-model', 'organism-classification-distill-plan', '严肃', Progress(10, len(tree.objectives)).mapping())
            def route_open(file, *args, **kwargs):
                if str(file).replace('\\', '/').endswith('snapshot/test-snapshot2.json'):
                    file = snapshot
                return original_open(file, *args, **kwargs)
            args = ['main.py', '--model', 'ollama/test', *flags]
            if setup_choices is None:
                args.extend(['--interviewee', 'maria', '--task', 'organism-classification-distill-plan'])
            if restore:
                args.extend(['--restore', 'test-snapshot2'])
            stack.enter_context(patch('sys.argv', args))
            stack.enter_context(patch('builtins.open', side_effect=route_open))
            stack.enter_context(patch('builtins.input', return_value=confirmation))
            if setup_choices is None:
                stack.enter_context(patch('common.setup.select_tone', return_value='Serious'))
            else:
                stack.enter_context(patch('common.setup.prompt', side_effect=setup_choices))
            stack.enter_context(patch('prompt_toolkit.PromptSession', return_value=session))
            generation = stack.enter_context(patch('agent.generation.chat', side_effect=lambda **kw: iter(['Question', '?']) if kw.get('stream') else 'Question?'))
            review = stack.enter_context(patch('agent.generation_review.chat', return_value='<verify>Yes</verify><reply>Approved</reply>'))
            stack.enter_context(patch('agent.simulation.chat', return_value='Simulated answer'))
            distillation = stack.enter_context(patch('agent.distill.chat', return_value=actions))
            stack.enter_context(patch('agent.summary.chat', return_value='[]'))
            entities = stack.enter_context(patch('agent.entity_extraction_distill.chat', return_value='<|COMPLETE|>'))
            evaluation = stack.enter_context(patch('agent.critique.chat', return_value='Score: good'))
            stack.enter_context(patch.object(KnowledgeGraph, 'dump'))
            stack.enter_context(patch.object(Progress, 'get_time_remaining', autospec=True, side_effect=remaining if remaining is not None else lambda progress: 0))
            stack.enter_context(patch('common.show_utils.show_response', side_effect=lambda res, **kw: res if isinstance(res, str) else ''.join(res)))
            stack.enter_context(patch('rich.console.Console.print'))
            speech = stack.enter_context(patch('tts.tts'))
            graph = stack.enter_context(patch('entity_extraction.mermaid_opts.create_mermaid_png_and_display'))
            stack.enter_context(patch('pyperclip.paste', return_value='Clipboard answer'))
            stack.enter_context(patch.dict('sys.modules', {'asr': types.SimpleNamespace(record_and_asr=recorded)}))
            stack.enter_context(patch.dict('os.environ', {}))
            factory = Mock()
            factory.return_value.__enter__ = Mock(return_value=types.SimpleNamespace(models=lambda: ['test', 'second']))
            factory.return_value.__exit__ = Mock(return_value=False)
            stack.enter_context(patch('llms.ModelClient', factory))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            result = runpy.run_path(str(root / 'main.py'), run_name='__main__')
            result['api_calls'] = dict(generation=generation.call_count, review=review.call_count, distillation=distillation.call_count, entities=entities.call_count)
            result['saved_snapshot'] = json.loads(snapshot.read_text(encoding='utf-8')) if snapshot.exists() else None
            return result, evaluation, speech, graph, recorded

    def test_default_path_avoids_optional_model_calls(self):
        result, *_ = self.run_case()
        self.assertEqual(result['args'].generation_mode, 'solo')
        self.assertTrue(result['args'].stream)
        self.assertEqual(result['args'].prompt_language, 'en-US')
        self.assertEqual(result['api_calls'], dict(generation=2, review=0, distillation=1, entities=0))

    def test_optional_relationship_extraction(self):
        for flag in ('--entities', '--graph'):
            with self.subTest(flag=flag):
                result, *_ = self.run_case(flags=[flag])
                self.assertEqual(result['api_calls']['entities'], 1)

    def test_startup_selects_expert_topic_and_style(self):
        result, *_ = self.run_case(setup_choices=['2', '3', '1'])
        self.assertEqual(result['args'].interviewee, 'maria')
        self.assertEqual(result['args'].task, 'organism-classification-distill-plan')
        self.assertEqual(result['tone'], 'Serious')

    def test_chinese_prompt_mode_remains_available(self):
        result, *_ = self.run_case(flags=['--prompt-language', 'zh-CN', '--no-stream'])
        self.assertEqual(result['args'].prompt_language, 'zh-CN')
        self.assertFalse(result['args'].stream)

    def test_new_expert_is_used_by_the_interview(self):
        with tempfile.TemporaryDirectory() as directory:
            result, *_ = self.run_case(setup_choices=['0', 'Alice <Engineer>', '36', '', 'MSc', 'Engineer', 'Robotics', '3', '1'], profile_directory=directory)
            self.assertTrue(result['args'].interviewee.startswith('local-'))
            self.assertEqual(result['generate_agent'].interviewee_name, 'Alice <Engineer>')
            self.assertIn('Robotics', result['generate_agent'].background_info)
            self.assertEqual(result['distill_agent'].interviewee_name, 'Alice <Engineer>')
            self.assertEqual(result['progress'].rounds, 1)

    def test_all_interview_mode_combinations(self):
        for auto, mode, stream, evaluate in itertools.product([False, True], ['solo', 'conversation'], [False, True], [False, True]):
            flags = ['--generation-mode', mode]
            if auto:
                flags.append('--auto')
            if stream:
                flags.append('--stream')
            else:
                flags.append('--no-stream')
            if evaluate:
                flags.append('--evaluate')
            with self.subTest(auto=auto, mode=mode, stream=stream, evaluate=evaluate):
                result, evaluation, *_ = self.run_case(flags)
                self.assertEqual(result['progress'].rounds, 1)
                self.assertEqual(result['distilled_tree'].objectives[0].knowledge[0].concept, 'Mammals')
                self.assertEqual(evaluation.call_count, int(evaluate))

    def test_commands_and_model_switch(self):
        commands = ['/tree', '/progress', '/model', '/models ollama', '/model invalid', '/model ollama/second', '/generation-prompt', '/distill-prompt', '/review-generation-prompt', '/summary-prompt', '/refine', '/undo', '/redo', '/dump', '/unknown', 'Answer']
        result, *_ = self.run_case(commands=commands)
        self.assertTrue(all(agent.model == 'ollama/second' for agent in result['agent_group']))
        self.assertEqual(result['saved_snapshot']['model'], 'ollama/second')
        self.assertEqual(result['saved_snapshot']['chat_history']['chat_history'], [])
        self.assertEqual(result['tree_manager'].cursor, 2)

    def test_restore_and_model_override(self):
        result, *_ = self.run_case(restore=True)
        self.assertEqual(result['args'].model, 'ollama/test')
        self.assertEqual(result['tone'], '严肃')
        self.assertEqual(result['progress'].rounds, 1)

    def test_input_sources(self):
        for command, expected in [('/clipboard', 'Clipboard answer'), ('/asr', 'Recorded answer'), ('/auto', 'Simulated answer')]:
            with self.subTest(command=command):
                result, *_ = self.run_case(commands=[command])
                self.assertEqual(result['chat_history'].get_message()[-1]['content'], expected)

    def test_exit_commands(self):
        for command in ['/quit', '/exit']:
            with self.subTest(command=command), self.assertRaises(SystemExit) as result:
                self.run_case(commands=[command])
            self.assertEqual(result.exception.code, 0)

    def test_optional_media_modes(self):
        result, _, speech, graph, _ = self.run_case(flags=['--auto', '--tts', '--graph'])
        speech.assert_called_once()
        self.assertEqual(graph.call_count, 2)
        self.assertEqual(result['progress'].rounds, 1)

    def test_auto_returns_to_human(self):
        result, *_ = self.run_case(flags=['--auto'], remaining=lambda progress: 100 if progress.rounds < 4 else 0)
        self.assertEqual(result['progress'].rounds, 4)
        self.assertFalse(result['args'].auto)
        self.assertEqual(result['chat_history'].get_message()[-1]['content'], 'Answer')

    def test_all_plan_persona_combinations(self):
        from agent.distill import DistillAgent
        from agent.generation import GenerationAgent
        from agent.simulation import SimulationAgent
        from agent.critique import CritiqueAgent
        root = Path(main.__file__).parent
        for plan in (root / 'plan').glob('*.json'):
            for persona in (root / 'interviewee').glob('*.json'):
                with self.subTest(plan=plan.name, persona=persona.name):
                    tree = KnowledgeGraph.restore(str(plan.with_suffix('')))
                    history = ChatHistory()
                    history.append('expert', 'Answer')
                    args = dict(name='test', distilled_tree=tree, chat_history=history, interviewee=persona.stem, model='ollama/test')
                    for cls in [DistillAgent, SimulationAgent, CritiqueAgent]:
                        self.assertTrue(cls(**args).get_prompt())
                    self.assertTrue(GenerationAgent(**args, progress=Progress(10, len(tree.objectives)), tone='严肃', review_history=history).get_prompt())

    def test_deep_progress_and_generalization(self):
        leaf = Knowledge(id='leaf')
        middle = Knowledge(sub_knowledge=[leaf])
        root = Knowledge(sub_knowledge=[middle])
        tree = KnowledgeGraph(objectives=[Objective(id='objective', knowledge=[root])])
        tree.renew_knowledge('answer', 'Concept', 'concept', 0, 'leaf')
        self.assertGreater(tree.objectives[0].progress, 0)
        before = tree.objectives[0].progress
        tree.generalize_knowledge('answer', {'concept': 'Group'}, [root.id], 0, 'objective')
        self.assertEqual(tree.objectives[0].progress, before)


if __name__ == '__main__':
    unittest.main()
