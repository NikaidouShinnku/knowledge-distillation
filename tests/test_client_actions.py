import json
import os
import unittest
from unittest.mock import Mock, patch

import httpx
from openai import OpenAI

from llms import ConfigurationError, ModelAPIError, ModelClient, ModelConfig
from knowledge_graph.actions import apply_actions, parse_actions
from knowledge_graph.model import KnowledgeGraph, Knowledge, Objective
from common.mermaid_code import generate_mermaid


class ClientTests(unittest.TestCase):
    def client(self, handler, attempts=3):
        config = ModelConfig('groq', 'test/model', 'https://example.test/v1', 'test-secret', attempts=attempts)
        transport = httpx.MockTransport(handler)
        sdk = OpenAI(api_key=config.api_key, base_url=config.base_url,
                     http_client=httpx.Client(transport=transport), max_retries=0)
        return ModelClient(config, sdk, sleeper=Mock())

    def response(self, content='OK'):
        return {'id': 'test', 'object': 'chat.completion', 'created': 0, 'model': 'test/model',
                'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': content}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 3, 'completion_tokens': 1, 'total_tokens': 4}}

    def test_complete_payload_and_usage(self):
        requests = []
        def handler(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json=self.response())
        with self.client(handler) as client, patch('llms.client.update_usage') as usage:
            self.assertEqual(client.complete(prompt='hello'), 'OK')
            usage.assert_called_once()
        self.assertEqual(requests[0]['model'], 'test/model')
        self.assertEqual(requests[0]['messages'], [{'role': 'user', 'content': 'hello'}])

    def test_retry_then_success(self):
        calls = []
        def handler(request):
            calls.append(1)
            if len(calls) < 3:
                return httpx.Response(429, headers={'retry-after': '0'}, json={'error': {'message': 'busy'}})
            return httpx.Response(200, json=self.response())
        with self.client(handler) as client:
            self.assertEqual(client.complete(prompt='hello'), 'OK')
            self.assertEqual(client.sleeper.call_count, 2)
        self.assertEqual(len(calls), 3)

    def test_retries_bounded(self):
        handler = Mock(return_value=httpx.Response(503, json={'error': {'message': 'busy'}}))
        with self.client(handler) as client:
            with self.assertRaises(ModelAPIError):
                client.complete(prompt='hello')
        self.assertEqual(handler.call_count, 3)

    def test_token_reset_header_controls_retry_delay(self):
        calls = []
        def handler(request):
            calls.append(1)
            if len(calls) == 1:
                return httpx.Response(429, headers={'x-ratelimit-reset-tokens': '10.5s'}, json={'error': {'message': 'quota'}})
            return httpx.Response(200, json=self.response())
        with self.client(handler) as client:
            self.assertEqual(client.complete(prompt='hello'), 'OK')
            client.sleeper.assert_called_once_with(10.5)

    def test_rate_limit_without_headers_waits_a_window(self):
        handler = Mock(side_effect=[httpx.Response(429, json={'error': {'message': 'quota'}}), httpx.Response(200, json=self.response())])
        with self.client(handler) as client:
            self.assertEqual(client.complete(prompt='hello'), 'OK')
            client.sleeper.assert_called_once_with(60)

    def test_transcription_uses_common_client(self):
        import tempfile
        from pathlib import Path
        requests = []
        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={'text': 'Test speech'})
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'speech.wav'
            file.write_bytes(b'audio-bytes')
            with self.client(handler) as client:
                self.assertEqual(client.transcribe(file, language='en'), 'Test speech')
        self.assertIn(b'audio-bytes', requests[0].content)
        self.assertTrue(requests[0].url.path.endswith('/audio/transcriptions'))

    def test_auth_error_not_retried_or_leaked(self):
        handler = Mock(return_value=httpx.Response(401, json={'error': {'message': 'test-secret'}}))
        with self.client(handler) as client:
            with self.assertRaises(ModelAPIError) as error:
                client.complete(prompt='hello')
            self.assertNotIn('test-secret', str(error.exception))
            client.sleeper.assert_not_called()
        self.assertEqual(handler.call_count, 1)

    def test_stream_handles_empty_and_usage_events(self):
        events = [
            {'id': '1', 'object': 'chat.completion.chunk', 'created': 0, 'model': 'test/model', 'choices': [{'index': 0, 'delta': {'role': 'assistant', 'content': None}}]},
            {'id': '1', 'object': 'chat.completion.chunk', 'created': 0, 'model': 'test/model', 'choices': [{'index': 0, 'delta': {'content': 'OK'}}]},
            {'id': '1', 'object': 'chat.completion.chunk', 'created': 0, 'model': 'test/model', 'choices': [], 'usage': {'prompt_tokens': 3, 'completion_tokens': 1, 'total_tokens': 4}},
        ]
        payload = ''.join(f'data: {json.dumps(event)}\n\n' for event in events) + 'data: [DONE]\n\n'
        with self.client(lambda request: httpx.Response(200, headers={'content-type': 'text/event-stream'}, content=payload)) as client:
            with patch('llms.client.update_usage') as usage:
                self.assertEqual(''.join(client.complete(prompt='hello', stream=True)), 'OK')
                usage.assert_called_once()

    def test_missing_key_no_request(self):
        with patch('llms.config.load_environment'), patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigurationError):
                ModelConfig.resolve('groq/test')

    def test_model_nested_slash_and_key_not_in_repr(self):
        with patch('llms.config.load_environment'), patch.dict(os.environ, {'GROQ_API_KEY': 'hidden-key'}):
            config = ModelConfig.resolve('groq/openai/gpt-oss-120b')
        self.assertEqual(config.model, 'openai/gpt-oss-120b')
        self.assertNotIn('hidden-key', repr(config))

    def test_ollama_needs_no_key(self):
        with patch('llms.config.load_environment'), patch.dict(os.environ, {}, clear=True):
            config = ModelConfig.resolve('ollama/qwen3:8b')
        self.assertEqual(config.base_url, 'http://127.0.0.1:11434/v1')

    def test_legacy_model_requires_explicit_choice(self):
        with self.assertRaisesRegex(ConfigurationError, 'Legacy model'):
            ModelConfig.resolve('llama3-70b-8192')

    def test_dotenv_does_not_override_environment(self):
        import tempfile
        from pathlib import Path
        from dotenv import load_dotenv
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('GROQ_API_KEY=file-key\n', encoding='utf-8')
            with patch.dict(os.environ, {'GROQ_API_KEY': 'shell-key'}):
                load_dotenv(path, override=False)
                self.assertEqual(os.environ['GROQ_API_KEY'], 'shell-key')


class ActionTests(unittest.TestCase):
    def tree(self):
        return KnowledgeGraph(objectives=[Objective(id='root')])

    def test_invalid_batch_is_atomic(self):
        tree = self.tree()
        actions = parse_actions(json.dumps([
            {'action': 'add_new_knowledge_node', 'arguments': {'parent_id': 'root', 'knowledge_detail': {'concept': 'Valid'}}},
            {'action': 'delete_knowledge_node', 'arguments': {'knowledge_id': 'missing'}}]))
        before = tree.model_dump()
        with self.assertRaises(ValueError):
            apply_actions(tree, actions, 'answer', 0)
        self.assertEqual(tree.model_dump(), before)

    def test_tagged_action_response(self):
        self.assertEqual(parse_actions('<thought>reason</thought><action>[]</action>'), [])
        self.assertEqual(parse_actions('<action>```json\n[]\n```</action>'), [])

    def test_invalid_schema_rejected(self):
        for text in ['[{"action":"unknown","arguments":{}}]',
                     '[{"action":"add_new_knowledge_node","arguments":{"parent_id":"root","knowledge_detail":{"concept":1}}}]',
                     "[{'action': 'delete_knowledge_node'}]", '[] trailing text']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_actions(text)

    def test_json_strings_preserve_apostrophes(self):
        text = json.dumps([{'action': 'add_new_knowledge_node', 'arguments': {'parent_id': 'root', 'knowledge_detail': {'concept': "It's intact"}}}])
        tree = self.tree()
        apply_actions(tree, parse_actions(f'```json\n{text}\n```'), 'answer', 1)
        self.assertEqual(tree.objectives[0].knowledge[0].concept, "It's intact")

    def test_generalize_invalid_parent_preserves_data(self):
        node = Knowledge(id='child')
        tree = KnowledgeGraph(objectives=[Objective(id='root', knowledge=[node])])
        before = tree.model_dump()
        with self.assertRaises(ValueError):
            tree.generalize_knowledge('', {'concept': 'new'}, ['child'], 0, 'missing')
        self.assertEqual(tree.model_dump(), before)

    def test_streaming_reply_removes_split_wrappers(self):
        from agent.generation import stream_reply
        chunks = iter(['<thought>Internal text</thought><rep', 'ly>Quest', 'ion?</rep', 'ly>trailing'])
        self.assertEqual(''.join(stream_reply(chunks)), 'Question?')

    def test_streaming_reply_accepts_plain_text(self):
        from agent.generation import stream_reply
        self.assertEqual(''.join(stream_reply(iter(['Plain ', 'question']))), 'Plain question')

    def test_mermaid_does_not_mutate_entities(self):
        entities = [{'name': 'Name with space', 'type': 'Type'}, {'name': 'Other', 'type': 'Type'}]
        relations = [{'source': 'Name with space', 'target': 'Other', 'id': '1', 'strength': 3}]
        before = json.dumps([entities, relations])
        rendered = generate_mermaid(entities, relations)
        self.assertIn('node_0 -->', rendered)
        self.assertEqual(json.dumps([entities, relations]), before)


if __name__ == '__main__':
    unittest.main()
