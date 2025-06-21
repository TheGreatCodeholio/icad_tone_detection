class AudioLoadError(Exception):
    """Raised when the input audio cannot be loaded or decoded."""
    pass

class FrequencyExtractionError(Exception):
    """Raised when frequency extraction fails."""
    pass

class ToneDetectionError(Exception):
    """Raised when tone detection (MDC/DTMF) fails."""
    pass

class FFmpegNotFoundError(Exception):
    """Raised when FFmpeg is not installed or not found in PATH."""
    pass