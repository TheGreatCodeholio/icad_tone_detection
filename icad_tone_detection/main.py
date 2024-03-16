from .audio_loader import load_audio
from .frequency_extraction import FrequencyExtraction
from .tone_detection import detect_quickcall, detect_long_tones, detect_warble_tones


class ToneDetectionResult:
    def __init__(self, two_tone_result, long_result, hi_low_result):
        self.two_tone_result = two_tone_result
        self.long_result = long_result
        self.hi_low_result = hi_low_result


def tone_detect(audio_path, matching_threshold=2, time_resolution_ms=100, hi_low_interval=0.2,
                hi_low_min_alternations=2, debug=False):
    """
        Loads audio from various sources including local path, URL, BytesIO object, or a PyDub AudioSegment.

        Parameters:
           - audio_input: Can be a string (path or URL), bytes like object, or AudioSegment.
           - matching_threshold (float): The percentage threshold used to determine if two frequencies
                are considered a match. For example, a threshold of 2 means that two frequencies are considered matching
                if they are within 2% of each other.
           - time_resolution_ms (int): The time resolution in milliseconds for the STFT. Default is 100ms.
           - hi_low_interval (float): The maximum allowed interval in seconds between two consecutive alternating tones. Default is 0.2
           - hi_low_min_alternations (int): The minimum number of alternations for a hi-low warble tone sequence to be considered valid. Default 2
           - debug (bool): If debug is enabled, print all tones found in audio file. Default is False

        Returns:
           - An instance of ToneDetectionResult containing information about the found tones in the audio.

        Raises:
            -ValueError for unsupported audio input types or errors in processing.
        """

    samples, frame_rate, duration_seconds = load_audio(audio_path)

    matched_frequencies = FrequencyExtraction(samples, frame_rate, duration_seconds, matching_threshold,
                                              time_resolution_ms).get_audio_frequencies()
    if debug is True:
        print("Matched frequencies: ", matched_frequencies)

    two_tone_result = detect_quickcall(matched_frequencies)
    long_result = detect_long_tones(matched_frequencies, two_tone_result)
    hi_low_result = detect_warble_tones(matched_frequencies, hi_low_interval, hi_low_min_alternations)
    return ToneDetectionResult(two_tone_result, long_result, hi_low_result)
