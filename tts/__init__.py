from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading


def edge_tts(text, *, voice="zh-CN-YunyangNeural", rate="+50%", output, **kwargs):
    subprocess.run([sys.executable, "-m", "edge_tts", "--voice", voice or "zh-CN-YunyangNeural",
                    f"--rate={rate}", "--text", text, "--write-media", str(output)],
                   check=True, capture_output=True, timeout=90)


def play_sound(file):
    executable = shutil.which("ffplay")
    if executable:
        subprocess.run([executable, "-vn", "-nodisp", "-autoexit", str(file)],
                       check=True, capture_output=True, timeout=180)
        return
    import miniaudio

    ended = threading.Event()
    source = miniaudio.stream_file(str(file))
    stream = miniaudio.stream_with_callbacks(source, end_callback=ended.set)
    next(stream)
    try:
        with miniaudio.PlaybackDevice() as device:
            device.start(stream)
            if not ended.wait(180):
                raise TimeoutError("Audio playback did not complete")
    except miniaudio.MiniaudioError as exc:
        raise RuntimeError("Audio playback failed") from exc
    finally:
        stream.close()
        source.close()


def tts(text, *, vendor="edge", output=None, play=False, **kwargs):
    if output:
        do_tts(text, vendor=vendor, output=output, **kwargs)
        if play:
            play_sound(output)
        return output
    with tempfile.TemporaryDirectory() as directory:
        file = Path(directory) / "speech.mp3"
        do_tts(text, vendor=vendor, output=file, **kwargs)
        if play:
            play_sound(file)
    return None


def do_tts(text, *, vendor="edge", output, **kwargs):
    if vendor != "edge":
        raise ValueError(f"Unsupported TTS vendor: {vendor}")
    if not output or not text.strip():
        raise ValueError("Text and output file are required")
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    edge_tts(text, output=output, **kwargs)
