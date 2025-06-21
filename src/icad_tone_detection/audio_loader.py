import io
import os
import subprocess
from typing import Union, IO, Tuple

import numpy as np
from pydub import AudioSegment
import requests


def load_audio(audio_input: Union[str, bytes, bytearray, IO, AudioSegment]) -> Tuple[AudioSegment, np.ndarray, int, float]:
    """
    Load audio from various sources and convert it to 16 kHz, mono, 16-bit PCM WAV using FFmpeg.

    This function can handle:
      - Local file paths (string)
      - URLs (string starting with 'http' or 'https')
      - Bytes or bytearray
      - File-like objects (e.g. io.BytesIO)
      - Pydub AudioSegment objects

    After conversion via FFmpeg, it returns:
      1) A pydub AudioSegment (16 kHz, mono, 16-bit)
      2) A NumPy float32 array of samples (range [-1, 1])
      3) The frame rate (16 kHz)
      4) Duration in seconds

    Args:
        audio_input (Union[str, bytes, bytearray, IO, AudioSegment]):
            The audio to load/convert. If a string:
              - If it starts with 'http' or 'https', treated as a URL.
              - Else, treated as a local file path.

    Returns:
        Tuple[AudioSegment, np.ndarray, int, float]:
            (audio_segment, samples, frame_rate, duration_seconds)

    Raises:
        ValueError: If the input type is unsupported or empty.
        RuntimeError: If FFmpeg conversion fails.
    """

    # 1) ---- Unify the input into raw bytes ----
    if isinstance(audio_input, AudioSegment):
        # Export AudioSegment to raw bytes
        buffer = io.BytesIO()
        audio_input.export(buffer, format="wav")
        input_bytes = buffer.getvalue()
    elif isinstance(audio_input, (bytes, bytearray)):
        input_bytes = audio_input
        if not input_bytes:
            raise ValueError("Received empty bytes/bytearray for audio input.")
    elif hasattr(audio_input, "read"):
        # Covers file-like objects, including io.BytesIO and open('file', 'rb')
        raw_data = audio_input.read()
        if not raw_data:
            raise ValueError("File-like object is empty or could not be read.")
        input_bytes = raw_data
    elif isinstance(audio_input, str):
        if audio_input.startswith("http://") or audio_input.startswith("https://"):
            # It's a URL: download the audio data
            response = requests.get(audio_input)
            response.raise_for_status()
            input_bytes = response.content
        else:
            # It's a local file path
            if not os.path.isfile(audio_input):
                raise ValueError(f"File path does not exist: {audio_input}")
            with open(audio_input, "rb") as f:
                input_bytes = f.read()
    else:
        raise ValueError("Unsupported audio input type. Must be a file path, URL, bytes, BytesIO, or AudioSegment.")

    if not input_bytes:
        raise ValueError("Audio data is empty after reading.")

    # 2) ---- Convert to 16 kHz, mono, 16-bit PCM WAV using FFmpeg ----
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i", "pipe:0",        # read from stdin
        "-acodec", "pcm_s16le", # 16-bit PCM
        "-ar", "16000",         # 16 kHz sample rate
        "-ac", "1",             # mono
        "-f", "wav",            # output to WAV
        "pipe:1"                # write to stdout
    ]

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    out_data, err_data = process.communicate(input=input_bytes)
    if process.returncode != 0:
        error_message = err_data.decode("utf-8", "replace")
        raise RuntimeError(f"FFmpeg conversion failed:\n{error_message}")

    # 3) ---- Load FFmpeg's output into pydub AudioSegment ----
    audio_segment = AudioSegment.from_wav(io.BytesIO(out_data))

    # 4) ---- Convert to NumPy float32 samples in [-1, 1] ----
    float32_samples = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)
    max_val = float(2 ** (audio_segment.sample_width * 8 - 1))
    float32_samples /= max_val

    # 5) ---- Return results: (AudioSegment, sample array, frame_rate, duration) ----
    return audio_segment, float32_samples, audio_segment.frame_rate, audio_segment.duration_seconds


def get_audio_from_url(url: str) -> Tuple[AudioSegment, np.ndarray, int, float]:
    """
    Fetches audio from a given URL and converts it to 16 kHz, mono, 16-bit PCM WAV
    using the FFmpeg-based pipeline (load_audio).

    Args:
        url (str): The URL from which to fetch the audio file.

    Returns:
        Tuple[AudioSegment, np.ndarray, int, float]:
            - A pydub AudioSegment (16 kHz, mono, 16-bit)
            - A NumPy float32 array of samples in range [-1, 1]
            - The frame rate (16 kHz)
            - Duration in seconds

    Raises:
        ValueError: If fetching the content from the URL fails, or the audio cannot be converted.
    """
    try:
        response = requests.get(url)
        # Ensure the request was successful
        response.raise_for_status()

        # Now pass the raw content to your load_audio function
        return load_audio(response.content)

    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to fetch audio from URL '{url}': {e}")
    except Exception as e:
        raise ValueError(f"Failed to process audio from URL '{url}': {e}")
