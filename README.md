# icad_tone_detection
Python Library For Scanner Tone Detection

## Requirements:
ffmpeg

## Installation:
`pip install git+https://github.com/TheGreatCodeholio/icad_tone_detection.git`

## Usage:
- File path can be URL or file path. 

```python
from icad_tone_detection import tone_detect

two_tone, long_tone, hl_tone = tone_detect('/path/to/file.mp3')

print(f"Two Tone: {two_tone}\nLong Tone: {long_tone}\nHigh Low: {hl_tone}")
```