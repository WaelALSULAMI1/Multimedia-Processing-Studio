import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np


MP3_FFMPEG_MESSAGE = "MP3 support requires FFmpeg. Please install FFmpeg and add it to PATH."


@dataclass
class AudioData:
    sample_rate: int
    samples: np.ndarray
    channels: int
    sample_width: int
    source_format: str = "wav"


def _load_mp3_with_pydub(path: str) -> AudioData:
    try:
        from pydub import AudioSegment
        from pydub.exceptions import CouldntDecodeError
        from pydub.utils import which
    except ImportError as exc:
        raise ValueError("MP3 support requires pydub. Install it with: pip install pydub") from exc

    if which("ffmpeg") is None or which("ffprobe") is None:
        raise ValueError(MP3_FFMPEG_MESSAGE)

    try:
        segment = AudioSegment.from_file(path, format="mp3")
    except (FileNotFoundError, OSError) as exc:
        raise ValueError(MP3_FFMPEG_MESSAGE) from exc
    except CouldntDecodeError as exc:
        raise ValueError("Could not decode this MP3 file. Please try another MP3 file or use a WAV file.") from exc

    segment = segment.set_sample_width(2)
    samples = np.array(segment.get_array_of_samples(), dtype=np.int16)
    if segment.channels > 1:
        samples = samples.reshape(-1, segment.channels)
    return AudioData(segment.frame_rate, samples, segment.channels, 2, "mp3")


def load_audio_file(path: str) -> AudioData:
    if not Path(path).exists():
        raise ValueError("The selected audio file does not exist.")

    suffix = Path(path).suffix.lower()
    if suffix == ".mp3":
        return _load_mp3_with_pydub(path)
    return load_wav(path)


def load_wav(path: str) -> AudioData:
    with wave.open(path, "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())

    if sample_width != 2:
        raise ValueError("Only 16-bit PCM WAV files are supported in this simple project.")

    samples = np.frombuffer(frames, dtype=np.int16).copy()
    if channels > 1:
        samples = samples.reshape(-1, channels)

    return AudioData(sample_rate, samples, channels, sample_width, "wav")


def save_wav(path: str, audio: AudioData) -> None:
    samples = np.clip(audio.samples, -32768, 32767).astype(np.int16)
    with wave.open(path, "wb") as wav_file:
        wav_file.setnchannels(audio.channels)
        wav_file.setsampwidth(audio.sample_width)
        wav_file.setframerate(audio.sample_rate)
        wav_file.writeframes(samples.tobytes())


def save_audio_file(path: str, audio: AudioData) -> None:
    suffix = Path(path).suffix.lower()
    if suffix == ".mp3":
        try:
            from pydub import AudioSegment
            from pydub.utils import which
        except ImportError as exc:
            raise ValueError("Saving MP3 requires pydub. Install it with: pip install pydub") from exc

        if which("ffmpeg") is None:
            raise ValueError("Saving MP3 requires FFmpeg. Please install FFmpeg and add it to PATH, or save as WAV.")

        samples = np.clip(audio.samples, -32768, 32767).astype(np.int16)
        segment = AudioSegment(
            samples.tobytes(),
            frame_rate=audio.sample_rate,
            sample_width=audio.sample_width,
            channels=audio.channels,
        )
        try:
            segment.export(path, format="mp3")
        except (FileNotFoundError, OSError) as exc:
            raise ValueError("Saving MP3 requires FFmpeg. Please install FFmpeg and add it to PATH, or save as WAV.") from exc
    else:
        save_wav(path, audio)


def _clip_sample(value: float) -> int:
    return max(-32768, min(32767, int(round(value))))


def change_volume(audio: AudioData, factor: float) -> AudioData:
    result = np.zeros_like(audio.samples)

    # Volume is changed manually by multiplying every sample by the selected factor.
    if audio.channels == 1:
        for i in range(len(audio.samples)):
            result[i] = _clip_sample(int(audio.samples[i]) * factor)
    else:
        for i in range(audio.samples.shape[0]):
            for channel in range(audio.channels):
                result[i, channel] = _clip_sample(int(audio.samples[i, channel]) * factor)

    return AudioData(audio.sample_rate, result, audio.channels, audio.sample_width, audio.source_format)


def normalize(audio: AudioData) -> AudioData:
    largest = 0

    if audio.channels == 1:
        for sample in audio.samples:
            largest = max(largest, abs(int(sample)))
    else:
        for i in range(audio.samples.shape[0]):
            for channel in range(audio.channels):
                largest = max(largest, abs(int(audio.samples[i, channel])))

    if largest == 0:
        return AudioData(audio.sample_rate, audio.samples.copy(), audio.channels, audio.sample_width, audio.source_format)

    # Normalization uses the largest absolute sample to calculate a manual gain factor.
    amp = 32767 / largest
    result = np.zeros_like(audio.samples)

    if audio.channels == 1:
        for i in range(len(audio.samples)):
            result[i] = _clip_sample(int(audio.samples[i]) * amp)
    else:
        for i in range(audio.samples.shape[0]):
            for channel in range(audio.channels):
                result[i, channel] = _clip_sample(int(audio.samples[i, channel]) * amp)

    return AudioData(audio.sample_rate, result, audio.channels, audio.sample_width, audio.source_format)


def reverse_audio(audio: AudioData) -> AudioData:
    if audio.channels == 1:
        result = np.zeros_like(audio.samples)
        source_index = len(audio.samples) - 1
        target_index = 0
        while source_index >= 0:
            result[target_index] = audio.samples[source_index]
            source_index -= 1
            target_index += 1
    else:
        result = np.zeros_like(audio.samples)
        source_index = audio.samples.shape[0] - 1
        target_index = 0
        while source_index >= 0:
            result[target_index] = audio.samples[source_index]
            source_index -= 1
            target_index += 1

    return AudioData(audio.sample_rate, result, audio.channels, audio.sample_width, audio.source_format)


def cut_audio(audio: AudioData, start_second: float, end_second: float) -> AudioData:
    total_frames = len(audio.samples) if audio.channels == 1 else audio.samples.shape[0]
    duration = total_frames / audio.sample_rate
    if start_second < 0 or end_second <= start_second or end_second > duration:
        raise ValueError(f"Cut values must satisfy 0 <= start < end <= {duration:.2f} seconds.")

    start_frame = int(start_second * audio.sample_rate)
    end_frame = int(end_second * audio.sample_rate)

    if audio.channels == 1:
        end_frame = min(len(audio.samples), end_frame)
        result = np.zeros(end_frame - start_frame, dtype=np.int16)
        target_index = 0
        for source_index in range(start_frame, end_frame):
            result[target_index] = audio.samples[source_index]
            target_index += 1
    else:
        end_frame = min(audio.samples.shape[0], end_frame)
        result = np.zeros((end_frame - start_frame, audio.channels), dtype=np.int16)
        target_index = 0
        for source_index in range(start_frame, end_frame):
            for channel in range(audio.channels):
                result[target_index, channel] = audio.samples[source_index, channel]
            target_index += 1

    return AudioData(audio.sample_rate, result, audio.channels, audio.sample_width, audio.source_format)


def duration_seconds(audio: AudioData) -> float:
    frame_count = len(audio.samples) if audio.channels == 1 else audio.samples.shape[0]
    return frame_count / audio.sample_rate


AUDIO_OPERATIONS = {
    "Volume": change_volume,
    "Normalize": normalize,
    "Reverse": reverse_audio,
    "Splice/Cut": cut_audio,
}
