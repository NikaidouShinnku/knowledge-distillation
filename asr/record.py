from pathlib import Path
import shutil
import subprocess
import wave

import numpy as np
import pyaudio
from rich.console import Console
from rich.live import Live
from rich.panel import Panel


CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
OUTPUT_WAVE_FILE = "output.wav"


def record_with_silence_detection(output_file="output.wav", *, duration=60, max_silence_seconds=5):
    if duration <= 0 or max_silence_seconds < 0:
        raise ValueError("Invalid recording duration or silence limit")
    audio = pyaudio.PyAudio()
    stream = None
    frames = []
    silence = 0
    sample_width = audio.get_sample_size(FORMAT)
    try:
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                            input=True, frames_per_buffer=CHUNK)
        with Live(console=Console(), refresh_per_second=10) as live:
            for _ in range(max(1, int(RATE / CHUNK * duration))):
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                amplitude = int(np.abs(np.frombuffer(data, dtype=np.int16).astype(np.int32)).max())
                live.update(Panel("█" * min(50, amplitude * 50 // 32768), title="录音中"))
                silence = silence + CHUNK / RATE if amplitude < 200 else 0
                if max_silence_seconds and silence >= max_silence_seconds:
                    break
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if stream is not None:
                try:
                    stream.stop_stream()
                finally:
                    stream.close()
        finally:
            audio.terminate()
    if output_file:
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_file), "wb") as file:
            file.setnchannels(CHANNELS)
            file.setsampwidth(sample_width)
            file.setframerate(RATE)
            file.writeframes(b"".join(frames))
    return frames


def is_ffmpeg_available():
    return shutil.which("ffmpeg") is not None


def convert_audio_to_format(input_file, output_file):
    executable = shutil.which("ffmpeg")
    if not executable:
        raise FileNotFoundError("ffmpeg is not on PATH")
    subprocess.run([executable, "-y", "-i", str(input_file), "-ar", "16000", "-ac", "1",
                    "-c:a", "pcm_s16le", str(output_file)], check=True, capture_output=True, timeout=90)


def _ffmpeg_record_and_convert_to_wav(*, device_id=0, duration=None, output_file):
    return record_with_silence_detection(output_file, duration=duration or 60)


def ffmpeg_record(*, output_file, duration=None):
    return record_with_silence_detection(output_file, duration=duration or 60)


if __name__ == "__main__":
    record_with_silence_detection()
