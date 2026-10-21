from pathlib import Path
import tempfile

from llms import ModelClient, ModelConfig


def do_asr(file, prompt=None, **kwargs):
    path = Path(file)
    if not path.is_file():
        raise FileNotFoundError(f"Audio file does not exist: {path}")
    with ModelClient(ModelConfig.resolve("groq/whisper-large-v3")) as client:
        return client.transcribe(path, prompt=prompt or "请准确转录语音。", **kwargs)


def record_and_asr(*, language="zh", duration=None):
    from asr.record import record_with_silence_detection

    with tempfile.TemporaryDirectory() as directory:
        file = Path(directory) / "input.wav"
        record_with_silence_detection(output_file=str(file), duration=duration or 30)
        return do_asr(file, language=language)
