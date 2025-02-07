import importlib
import platform

from .audio_loader import load_audio
from .frequency_extraction import FrequencyExtraction
from .tone_detection import detect_two_tone, detect_long_tones, detect_warble_tones, detect_mdc_tones, detect_dtmf_tones


class ToneDetectionResult:
    def __init__(self, two_tone_result, long_result, hi_low_result, mdc_result, dtmf_result):
        self.two_tone_result = two_tone_result
        self.long_result = long_result
        self.hi_low_result = hi_low_result
        self.mdc_result = mdc_result
        self.dtmf_result = dtmf_result


def _path_to_bin(folder_name, binary_name):
    return importlib.resources.files('icad_tone_detection').joinpath(f'bin/{folder_name}/{binary_name}')


def choose_decode_binary():
    system = platform.system().lower()  # e.g. "linux", "darwin", "windows"
    arch = platform.machine().lower()  # e.g. "x86_64", "arm64"

    # Example logic:
    if system == "linux":
        if "arm" in arch:
            return _path_to_bin("linux_arm64", "icad_decode")
        else:
            return _path_to_bin("linux_x86_64", "icad_decode")
    elif system == "darwin":
        return _path_to_bin("macos_arm64", "icad_decode")

    elif system == "windows":
        return _path_to_bin("windows_x86_64", "icad_decode.exe")
    else:
        raise RuntimeError(f"Unsupported OS/arch: {system}/{arch}")


def tone_detect(audio_path, matching_threshold=2.5, time_resolution_ms=25, tone_a_min_length=0.7, tone_b_min_length=2.7,
                hi_low_interval=0.2,
                hi_low_min_alternations=6, long_tone_min_length=3.8, debug=False):
    """
        Loads audio from various sources including local path, URL, BytesIO object, or a PyDub AudioSegment.

        Parameters:
           - audio_input: Can be a string (path or URL), bytes like object, or AudioSegment.
           - matching_threshold (float): The percentage threshold used to determine if two frequencies
                are considered a match. For example, a threshold of 2 means that two frequencies are considered matching
                if they are within x% of each other. Default 2.5%
           - time_resolution_ms (int): The time resolution in milliseconds for the STFT. Default is 25ms.
           - tone_a_min_length (float): The minimum length in seconds of an A tone for two tone detections. Default 0.8 Seconds
           - tone_b_min_length (float): The minimum length in seconds of a B tone for two tone detections. Default 2.8 Seconds
           - long_tone_min_length (float): The minimum length a long tone needs to be to consider it a match. Default 3.8 Seconds
           - hi_low_interval (float): The maximum allowed interval in seconds between two consecutive alternating tones. Default is 0.2 Seconds
           - hi_low_min_alternations (int): The minimum number of alternations for a hi-low warble tone sequence to be considered valid. Default 6
           - debug (bool): If debug is enabled, print all tones found in audio file. Default is False

        Returns:
           - An instance of ToneDetectionResult containing information about the found tones in the audio.

        Raises:
            -ValueError for unsupported audio input types or errors in processing.
        """

    icad_decode_path = choose_decode_binary()

    audio_segment, samples, frame_rate, duration_seconds = load_audio(audio_path)

    matched_frequencies = FrequencyExtraction(samples, frame_rate, duration_seconds, matching_threshold,
                                              time_resolution_ms).get_audio_frequencies()
    if debug is True:
        debug_info = f"""
############################################
Using decode binary path:
  {icad_decode_path}
############################################

Analyzing audio at: {audio_path}

Matching Threshold:       {matching_threshold}%
Time Resolution:          {time_resolution_ms} ms
Tone A Min Length:        {tone_a_min_length} s
Tone B Min Length:        {tone_b_min_length} s
Long Tone Min Length:     {long_tone_min_length} s
Hi-Low Interval:          {hi_low_interval} s
Hi-Low Min Alternations:  {hi_low_min_alternations}

Matched Frequencies:
  {matched_frequencies}
############################################
"""
        print(debug_info)

    two_tone_result = detect_two_tone(matched_frequencies, tone_a_min_length, tone_b_min_length)
    long_result = detect_long_tones(matched_frequencies, two_tone_result, long_tone_min_length)
    hi_low_result = detect_warble_tones(matched_frequencies, hi_low_interval, hi_low_min_alternations)
    mdc_result = detect_mdc_tones(audio_segment, binary_path=icad_decode_path)
    dtmf_result = detect_dtmf_tones(audio_segment, binary_path=icad_decode_path)

    return ToneDetectionResult(two_tone_result, long_result, hi_low_result, mdc_result, dtmf_result)
