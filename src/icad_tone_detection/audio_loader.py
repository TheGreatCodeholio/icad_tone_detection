import numpy as np
from pydub import AudioSegment
import requests
from io import BytesIO, IOBase


def load_audio(audio_input):
    """
        Loads audio from various sources including local path, URL, BytesIO object, or a PyDub AudioSegment.

        Parameters:
        - audio_input: Can be a string (path or URL), BytesIO object, or AudioSegment.

        Returns:
        - Tuple of (samples as np.array, frame rate, duration in seconds).

        Raises:
        - ValueError for unsupported audio input types or errors in processing.
    """
    # Check the type of audio_input to handle different sources
    if isinstance(audio_input, AudioSegment):
        audio = audio_input
    elif isinstance(audio_input, str):
        if audio_input.startswith('http://') or audio_input.startswith('https://'):
            audio = get_audio_from_url(audio_input)
        else:
            audio = AudioSegment.from_file(audio_input)
    elif isinstance(audio_input, IOBase) or isinstance(audio_input, bytes) or isinstance(audio_input, bytearray):
        audio = AudioSegment.from_file(audio_input)
    elif hasattr(audio_input, 'read'):
        audio_input.seek(0)
        audio = AudioSegment.from_file(BytesIO(audio_input.read()))
    else:
        raise ValueError("Unsupported audio input type. Must be a file path, URL, Bytes object, or Pydub AudioSegment.")

    # Processing
    try:
        audio = audio.set_channels(1)  # Ensure the audio is mono
        audio = audio.set_frame_rate(22050)  # Set the frame rate to 22050 Hz
        samples = np.array(audio.get_array_of_samples()).astype(np.float32)
        samples /= np.iinfo(audio.sample_width * 8).max  # Adjusted for correct normalization
    except Exception as e:
        raise RuntimeError(f"Error processing audio: {e}")

    return samples, audio.frame_rate, audio.duration_seconds


def get_audio_from_url(url):
    """
    Attempts to load audio from a given URL.

    Parameters:
    - url: str, the URL from which to fetch the audio file.

    Returns:
    - An AudioSegment object of the audio file.

    Raises:
    - ValueError if the audio cannot be fetched or loaded.
    """
    try:
        response = requests.get(url)
        # Check if the request was successful
        response.raise_for_status()
        audio = AudioSegment.from_file(BytesIO(response.content))
        return audio
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to fetch audio from URL: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load audio from the fetched content: {e}")
