import importlib
import platform
import stat
from pathlib import Path

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
    system = platform.system().lower()
    arch = platform.machine().lower()

    if system == "linux":
        if "arm" in arch:
            resource = _path_to_bin("linux_arm64", "icad_decode")
        else:
            resource = _path_to_bin("linux_x86_64", "icad_decode")
    elif system == "darwin":
        resource = _path_to_bin("macos_arm64", "icad_decode")
    elif system == "windows":
        return _path_to_bin("windows_x86_64", "icad_decode.exe")
    else:
        raise RuntimeError(f"Unsupported OS/arch: {system}/{arch}")

    # If not on Windows, try to chmod +x (assuming it's a real file on disk)
    if system != "windows":
        # `resource` is a Traversable. Usually you can do resource.__fspath__()
        # or cast to Path if you know it’s a FilePath:
        real_path = Path(resource)
        old_mode = real_path.stat().st_mode
        real_path.chmod(old_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return resource


def tone_detect(audio_path, matching_threshold=2.5, time_resolution_ms=50, tone_a_min_length=0.85, tone_b_min_length=2.6,
                hi_low_interval=0.2,
                hi_low_min_alternations=6, long_tone_min_length=3.8, detect_mdc=True, mdc_high_pass=200, mdc_low_pass=4000, detect_dtmf=True, debug=False):
    """
        Loads audio from various sources including local path, URL, BytesIO object, or a PyDub AudioSegment.

        Parameters:
           - audio_input: Can be a string (path or URL), bytes like object, or AudioSegment.
           - matching_threshold (float): The percentage threshold used to determine if two frequencies
                are considered a match. For example, a threshold of 2 means that two frequencies are considered matching
                if they are within x% of each other. Default 2.5%
           - time_resolution_ms (int): The time resolution in milliseconds for the STFT. Default is 50ms.
           - tone_a_min_length (float): The minimum length in seconds of an A tone for two tone detections. Default 0.85 Seconds
           - tone_b_min_length (float): The minimum length in seconds of a B tone for two tone detections. Default 2.8 Seconds
           - long_tone_min_length (float): The minimum length a long tone needs to be to consider it a match. Default 3.8 Seconds
           - hi_low_interval (float): The maximum allowed interval in seconds between two consecutive alternating tones. Default is 0.2 Seconds
           - hi_low_min_alternations (int): The minimum number of alternations for a hi-low warble tone sequence to be considered valid. Default 6
           - detect_mdc (bool): detect MDC/FleetSync
           - mdc_high_pass (int): The high pass filter for detecting MDC/FleetSync
           - mdc_low_pass (int): The low pass filter for detecting MDC/FleetSync
           - detect_dtmf (bool): detect DTMF
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
        if matched_frequencies:
            freq_lines = []
            for idx, (start, end, length, freq_list) in enumerate(matched_frequencies, start=1):
                # Convert freq_list to a simple string; optionally truncate if extremely large
                freq_str = ", ".join(str(freq) for freq in freq_list)
                freq_lines.append(
                    f"  {idx:2d}) Start={start:.2f}s | End={end:.2f}s | Dur={length:.2f}s\n"
                    f"       Freqs: [{freq_str}]"
                )
            freq_summary = "\n".join(freq_lines)
        else:
            freq_summary = "  None"


        debug_info = f"""
############################################################
ICAD Tone Detection: DEBUG
------------------------------------------------------------
Decode binary path:        {icad_decode_path}
Analyzing audio at:        {audio_path}

Matching Threshold:        {matching_threshold}%
Time Resolution (ms):      {time_resolution_ms}
Tone A Min Length (s):     {tone_a_min_length}
Tone B Min Length (s):     {tone_b_min_length}
Long Tone Min Length (s):  {long_tone_min_length}
Hi-Low Interval (s):       {hi_low_interval}
Hi-Low Min Alternations:   {hi_low_min_alternations}
Detect MDC/FleetSync:      {detect_mdc}
  MDC High Pass (Hz):      {mdc_high_pass}
  MDC Low Pass (Hz):       {mdc_low_pass}
Detect DTMF:               {detect_dtmf}

Total Duration (s):        {duration_seconds:.2f}
Sample Rate (Hz):          {frame_rate}

Matched Frequencies ({len(matched_frequencies)} groups):
{freq_summary}
############################################################
"""
        print(debug_info)

    two_tone_result = detect_two_tone(matched_frequencies, tone_a_min_length, tone_b_min_length)
    long_result = detect_long_tones(matched_frequencies, two_tone_result, long_tone_min_length)
    hi_low_result = detect_warble_tones(matched_frequencies, hi_low_interval, hi_low_min_alternations)
    if detect_mdc:
        mdc_result = detect_mdc_tones(audio_segment, binary_path=icad_decode_path, highpass_freq=mdc_high_pass, lowpass_freq=mdc_low_pass)
    else:
        mdc_result = []
    if detect_dtmf:
        dtmf_result = detect_dtmf_tones(audio_segment, binary_path=icad_decode_path)
    else:
        dtmf_result = []

    if debug:
        summary_info = f"""
------------------------------------------------------------
DETECTION SUMMARY
------------------------------------------------------------
Two-Tone (Quick Call): {len(two_tone_result)}
Long Tones:            {len(long_result)}
Hi-Low Warble:         {len(hi_low_result)}
MDC1200/FleetSync:     {len(mdc_result)}
DTMF:                  {len(dtmf_result)}
------------------------------------------------------------
"""
        print(summary_info)

    return ToneDetectionResult(two_tone_result, long_result, hi_low_result, mdc_result, dtmf_result)
