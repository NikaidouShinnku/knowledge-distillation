import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from knowledge_graph.model import Knowledge, Objective, KnowledgeGraph
from knowledge_graph.model_manager import KnowledgeTreeManager
from chat_history import ChatHistory
from progress.progress import Progress
from agent.distill import DistillAgent
from agent.generation import GenerationAgent
from agent.generation_review import ReviewGenerationAgent
from agent.summary import SummaryAgent
from agent.simulation import SimulationAgent
from agent.critique import CritiqueAgent
from agent.entity_extraction_distill import EntityExtractionAgent
from knowledge_graph.entity_relation_triple import EntityRelationTriple
from plan import plan_directory
import llms
import main


class RegressionTests(unittest.TestCase):
    def tree(self):
        return KnowledgeGraph.restore(str(Path(plan_directory()) / 'organism-classification-distill-plan'))

    def test_ids_unique(self):
        self.assertNotEqual(Knowledge().id, Knowledge().id)
        self.assertNotEqual(Objective().id, Objective().id)

    def test_history_isolation_and_branch(self):
        tree = self.tree()
        manager = KnowledgeTreeManager()
        manager.push_back(tree)
        tree.name = 'second'
        manager.push_back(tree)
        self.assertNotEqual(manager.undo().name, 'second')
        self.assertEqual(manager.redo().name, 'second')
        manager.undo()
        tree.name = 'branch'
        manager.push_back(tree)
        self.assertEqual(manager.redo().name, 'branch')
        tree.name = 'later mutation'
        self.assertEqual(manager.get_current_tree().name, 'branch')

    def test_invalid_move_preserves_tree(self):
        child = Knowledge()
        parent = Knowledge(sub_knowledge=[child])
        tree = KnowledgeGraph(objectives=[Objective(knowledge=[parent])])
        before = tree.model_dump()
        for destination in ['missing', parent.id, child.id]:
            with self.assertRaises(ValueError):
                tree.move_knowledge(parent.id, destination)
            self.assertEqual(tree.model_dump(), before)

    def test_progress_percent(self):
        progress = Progress(10, 4)
        progress.on_interviewee_replied(1, 1.0)
        self.assertEqual(progress.get_progress()['objectives_completed'], '25.0%')

    def test_unknown_model_fails(self):
        with self.assertRaises(ValueError):
            llms.chat(model='invalid', prompt='test')

    def test_all_agent_prompts(self):
        tree = self.tree()
        history = ChatHistory()
        history.append(role='expert', content='test answer')
        progress = Progress(10, len(tree.objectives))
        common = dict(name='test', distilled_tree=tree, model='deepseek-chat')
        for cls in [DistillAgent, SimulationAgent, CritiqueAgent]:
            agent = cls(**common, chat_history=history, interviewee='maria')
            self.assertTrue(agent.get_prompt())
        self.assertTrue(SummaryAgent(**common, chat_history=history).get_prompt())
        self.assertTrue(GenerationAgent(**common, chat_history=history, interviewee='maria', progress=progress, tone='default', review_history=history).get_prompt())
        self.assertTrue(ReviewGenerationAgent(**common, progress=progress, review_history=history).get_prompt())
        graph = EntityRelationTriple()
        graph.entities = [{'name': 'entity-marker'}]
        graph.relationships = [{'source': 'relationship-marker'}]
        prompt = EntityExtractionAgent(**common, chat_history=history, entity_types=['OTHER'], entity_relationship_triple=graph).get_prompt()
        self.assertIn('entity-marker', prompt)
        self.assertIn('relationship-marker', prompt)

    def test_snapshot_roundtrip(self):
        tree = self.tree()
        graph = EntityRelationTriple()
        graph.entities = [{'id': '1', 'name': 'example'}]
        graph.current_entity_id = 2
        main.entity_relationship_triple = EntityRelationTriple()
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / 'saved'
            main.dump_snapshot(str(snapshot), tree.model_dump(), ChatHistory().model_dump(), ChatHistory().model_dump(), 'maria', 'deepseek-chat', 'task', 'tone', Progress(10, 1).mapping(), graph.__dict__)
            with patch('builtins.open', side_effect=lambda *args, **kw: snapshot.with_suffix('.json').open('r', encoding='utf-8')):
                restored = main.load_restore_data('saved')
            self.assertEqual(restored[0].model_dump(), tree.model_dump())
            self.assertEqual(main.entity_relationship_triple.__dict__, graph.__dict__)

    def test_failed_action_batch_rolls_back(self):
        tree = self.tree()
        history = ChatHistory()
        history.append(role='expert', content='test')
        agent = DistillAgent('test', tree, history, 'maria', 'deepseek-chat')
        before = tree.model_dump()
        def partial_failure(turn):
            tree.name = 'partial'
            raise ValueError('invalid action')
        with patch.object(agent, 'do_update_tree', side_effect=partial_failure):
            with self.assertRaises(ValueError):
                agent.update_tree(1)
        self.assertEqual(tree.model_dump(), before)


    def test_one_interview_round_without_network(self):
        import runpy
        from contextlib import ExitStack
        with ExitStack() as stack:
            stack.enter_context(patch('sys.argv', ['main.py', '--auto', '--model', 'ollama/test']))
            stack.enter_context(patch('prompt_toolkit.prompt', return_value=''))
            stack.enter_context(patch('agent.generation.chat', return_value='<reply>Question?</reply>'))
            stack.enter_context(patch('agent.generation_review.chat', return_value='<verify>Yes</verify><reply>OK</reply>'))
            stack.enter_context(patch('agent.simulation.chat', return_value='Expert answer'))
            stack.enter_context(patch('agent.entity_extraction_distill.chat', return_value='<|COMPLETE|>'))
            stack.enter_context(patch('agent.distill.chat', return_value='[]'))
            stack.enter_context(patch.object(KnowledgeGraph, 'dump'))
            stack.enter_context(patch.object(Progress, 'get_time_remaining', return_value=0))
            stack.enter_context(patch('common.show_utils.show_response', side_effect=lambda res, **kwargs: res if isinstance(res, str) else ''.join(res)))
            stack.enter_context(patch('rich.console.Console.print'))
            result = runpy.run_path(str(Path(main.__file__)), run_name='__main__')
        self.assertEqual(result['progress'].rounds, 1)
        self.assertEqual(result['chat_history'].get_message()[-1]['content'], 'Expert answer')
        self.assertEqual(result['tree_manager'].cursor, 1)

    def test_streaming_interview_keeps_text_history(self):
        import runpy
        from contextlib import ExitStack
        with ExitStack() as stack:
            stack.enter_context(patch('sys.argv', ['main.py', '--auto', '--stream', '--model', 'ollama/test']))
            stack.enter_context(patch('prompt_toolkit.prompt', return_value=''))
            stack.enter_context(patch('agent.generation.chat', side_effect=lambda **kw: iter(['Question', '?']) if kw.get('stream') else 'Goodbye'))
            stack.enter_context(patch('agent.generation_review.chat', return_value='<verify>Yes</verify><reply>OK</reply>'))
            stack.enter_context(patch('agent.simulation.chat', return_value='Expert answer'))
            stack.enter_context(patch('agent.entity_extraction_distill.chat', return_value='<|COMPLETE|>'))
            stack.enter_context(patch('agent.distill.chat', return_value='[]'))
            stack.enter_context(patch.object(KnowledgeGraph, 'dump'))
            stack.enter_context(patch.object(Progress, 'get_time_remaining', return_value=0))
            stack.enter_context(patch('common.show_utils.show_response', side_effect=lambda res, **kw: res if isinstance(res, str) else ''.join(res)))
            stack.enter_context(patch('rich.console.Console.print'))
            result = runpy.run_path(str(Path(main.__file__)), run_name='__main__')
        self.assertEqual(result['review_history'].get_message()[0]['content'], 'Question?')
        self.assertEqual(result['chat_history'].get_message()[0]['content'], 'Question?')

    def test_rejected_questions_never_reach_expert(self):
        import runpy
        from contextlib import ExitStack
        with ExitStack() as stack:
            stack.enter_context(patch('sys.argv', ['main.py', '--auto', '--model', 'ollama/test']))
            stack.enter_context(patch('prompt_toolkit.prompt', return_value=''))
            stack.enter_context(patch('agent.generation.chat', return_value='Rejected question'))
            stack.enter_context(patch('agent.generation_review.chat', return_value='<verify>No</verify><reply>Try again</reply>'))
            simulate = stack.enter_context(patch('agent.simulation.chat'))
            stack.enter_context(patch('common.show_utils.show_response', side_effect=lambda res, **kw: res))
            result = runpy.run_path(str(Path(main.__file__)), run_name='__main__')
        simulate.assert_not_called()
        self.assertEqual(result['chat_history'].get_message(), [])


if __name__ == '__main__':
    unittest.main()
