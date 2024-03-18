# icad_tone_detection
Python Library For Scanner Tone Detection

## Requirements:
ffmpeg

## Installation:
`pip install icad_tone_detection`

## Usage:
- File path can be URL or file path.

```python
from icad_tone_detection import tone_detect

detect_result = tone_detect('/path/to/file.mp3')

print(
    f"Two Tone: {detect_result.two_tone_result}\nLong Tone: {detect_result.two_tone_result.long_tone_result}\nHigh Low: {detect_result.hi_low_result}")
```