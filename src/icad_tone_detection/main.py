from .audio_loader import load_audio
from .frequency_extraction import FrequencyExtraction
from .tone_detection import detect_two_tone, detect_long_tones, detect_warble_tones


class ToneDetectionResult:
    def __init__(self, two_tone_result, long_result, hi_low_result):
        self.two_tone_result = two_tone_result
        self.long_result = long_result
        self.hi_low_result = hi_low_result


def tone_detect(audio_path, matching_threshold=2.5, time_resolution_ms=25, tone_a_min_length=0.7, tone_b_min_length=2.7, hi_low_interval=0.2,
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

    samples, frame_rate, duration_seconds = load_audio(audio_path)

    matched_frequencies = FrequencyExtraction(samples, frame_rate, duration_seconds, matching_threshold,
                                              time_resolution_ms).get_audio_frequencies()
    if debug is True:
        debug_info = (
            f"Analyzing {audio_path} with the following settings:\n"
            f"Matching Threshold: {matching_threshold}%\n"
            f"Time Resolution: {time_resolution_ms}ms\n"
            f"Tone A Min Length: {tone_a_min_length}s\n"
            f"Tone B Min Length: {tone_b_min_length}s\n"
            f"Long Tone Min Length: {long_tone_min_length}s\n"
            f"Hi-Low Interval: {hi_low_interval}s\n"
            f"Hi-Low Min Alternations: {hi_low_min_alternations}\n"
            f"Matched frequencies: {matched_frequencies}"
        )
        print(debug_info)

    two_tone_result = detect_two_tone(matched_frequencies, tone_a_min_length, tone_b_min_length)
    long_result = detect_long_tones(matched_frequencies, two_tone_result, long_tone_min_length)
    hi_low_result = detect_warble_tones(matched_frequencies, hi_low_interval, hi_low_min_alternations)
    return ToneDetectionResult(two_tone_result, long_result, hi_low_result)
