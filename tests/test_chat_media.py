import contextlib
import io
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import Mock, patch

import chat
from tts import tts, do_tts, play_sound


class ChatFlowTests(unittest.TestCase):
    def run_chat(self, flags=(), inputs=('/quit',), fetch=None):
        calls = []
        def respond(**kwargs):
            calls.append(kwargs)
            return iter(['O', 'K']) if kwargs.get('stream') else 'OK'
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch('sys.argv', ['chat.py', '--model', 'ollama/test', '--prompt', 'Question', *flags]))
            stack.enter_context(patch('llms.chat', side_effect=respond))
            stack.enter_context(patch('builtins.input', side_effect=inputs))
            if fetch is not None:
                stack.enter_context(patch('requests.get', return_value=fetch))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            result = runpy.run_path(str(Path(chat.__file__)), run_name='__main__')
        return calls, result

    def test_plain_pretty_and_streaming(self):
        for flags in [[], ['--stream'], ['--no-pretty'], ['--stream', '--no-pretty']]:
            with self.subTest(flags=flags):
                calls, result = self.run_chat(flags)
                self.assertEqual(result['response'], 'OK')
                self.assertEqual(len(calls), 1)

    def test_multiple_models(self):
        calls, _ = self.run_chat(['--model', 'ollama/second'])
        self.assertEqual([call['model'] for call in calls], ['ollama/test', 'ollama/second'])

    def test_file_url_and_prompt_file_are_combined(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.txt'
            instruction = Path(directory) / 'prompt.txt'
            source.write_text('Source content', encoding='utf-8')
            instruction.write_text('Keep this instruction', encoding='utf-8')
            response = Mock(text='<p>Web content</p>')
            calls, _ = self.run_chat(['--file', str(source), '--prompt-file', str(instruction), '--url', 'https://example.test'], fetch=response)
            for expected in ['Source content', 'Keep this instruction', 'Web content', 'Question']:
                self.assertIn(expected, calls[0]['prompt'])

    def test_history_stream_blank_and_exit(self):
        calls, result = self.run_chat(['--history', '--stream'], inputs=['', 'Follow up', '/exit'])
        self.assertEqual(len(calls), 2)
        self.assertEqual(result['chat_history'][-1]['content'], 'OK')
        self.assertTrue(all(isinstance(message['content'], str) for message in result['chat_history']))

    def test_history_eof(self):
        calls, result = self.run_chat(['--history'], inputs=[EOFError()])
        self.assertEqual(len(calls), 1)


class MediaFlowTests(unittest.TestCase):
    def test_tts_temporary_file_can_be_written_and_played(self):
        def synthesize(text, *, output, **kwargs):
            Path(output).write_bytes(b'synthetic audio')
        def playback(file):
            self.assertEqual(Path(file).read_bytes(), b'synthetic audio')
        with patch('tts.edge_tts', side_effect=synthesize), patch('tts.play_sound', side_effect=playback) as player:
            tts('Test', play=True)
        player.assert_called_once()
        self.assertFalse(Path(player.call_args.args[0]).exists())

    def test_unsupported_vendor_rejected(self):
        with self.assertRaises(ValueError):
            do_tts('Test', vendor='unknown', output='unused.mp3')

    def test_ffplay_failure_propagates(self):
        import subprocess
        with patch('tts.shutil.which', return_value='ffplay'), patch('tts.subprocess.run', side_effect=subprocess.CalledProcessError(1, 'ffplay')):
            with self.assertRaises(subprocess.CalledProcessError):
                play_sound('audio.mp3')

    def test_graph_exports_file_without_terminal_viewer(self):
        from entity_extraction.mermaid_opts import create_mermaid_png_and_display
        def render(command, **kwargs):
            source = Path(command[command.index('-i') + 1])
            self.assertIn('graph TD', source.read_text(encoding='utf-8'))
            Path(command[command.index('-o') + 1]).write_bytes(b'PNG')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'graph.png'
            with patch.dict('os.environ', {'MERMAID_CLI': 'mmdc'}), patch('entity_extraction.mermaid_opts.shutil.which', return_value=None), patch('entity_extraction.mermaid_opts.subprocess.run', side_effect=render), contextlib.redirect_stdout(io.StringIO()):
                result = create_mermaid_png_and_display('graph TD\n', [], output_file=output)
            self.assertEqual(Path(result).read_bytes(), b'PNG')


    def test_recording_failure_closes_devices(self):
        import importlib.util
        if importlib.util.find_spec('pyaudio') is None or importlib.util.find_spec('numpy') is None:
            self.skipTest('Optional recording dependencies are not installed')
        from asr.record import record_with_silence_detection
        device = Mock()
        stream = device.open.return_value
        stream.read.side_effect = OSError('Capture failed')
        device.get_sample_size.return_value = 2
        with patch('asr.record.pyaudio.PyAudio', return_value=device), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(OSError):
                record_with_silence_detection(None, duration=0.1)
        stream.stop_stream.assert_called_once()
        stream.close.assert_called_once()
        device.terminate.assert_called_once()

    def test_recording_without_output_file(self):
        import importlib.util
        if importlib.util.find_spec('pyaudio') is None or importlib.util.find_spec('numpy') is None:
            self.skipTest('Optional recording dependencies are not installed')
        from asr.record import record_with_silence_detection
        device = Mock()
        device.open.return_value.read.return_value = b'\x00\x80' * 1024
        device.get_sample_size.return_value = 2
        with patch('asr.record.pyaudio.PyAudio', return_value=device), contextlib.redirect_stdout(io.StringIO()):
            frames = record_with_silence_detection(None, duration=0.01, max_silence_seconds=0)
        self.assertEqual(len(frames), 1)
        device.terminate.assert_called_once()


if __name__ == '__main__':
    unittest.main()
