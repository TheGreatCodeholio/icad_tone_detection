# icad_tone_detection

[![PyPI version](https://badge.fury.io/py/icad_tone_detection.svg)](https://badge.fury.io/py/icad_tone_detection)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python library for extracting scanner radio tones from scanner audio. This includes Two-Tone (Quick Call), Long Tones, Hi-Low “warble” tones, MDC1200/FleetSync, and DTMF signals. The library uses STFT-based frequency extraction as well as an included external decoder binary (`icad_decode`) to process advanced signals like MDC1200 and DTMF.

---

## Features

- **Easy-to-use** main function `tone_detect` for detecting:
    - Two-Tone / Quick Call tones
    - Long tones
    - Hi-Low / warble tones
    - MDC1200 / FleetSync
    - DTMF
- **Flexible audio input**: Local file paths, URLs, raw byte data, `io.BytesIO`, or existing `pydub.AudioSegment`.
- **Automatic resampling** to PCM 16bit @16 kHz mono for consistent detection.
- **Cross-platform** included binaries for MDC/DTMF decoding:
    - Windows (x86_64)
    - Linux (x86_64, ARM64)
    - macOS (ARM64)
- **Configurable** detection thresholds and parameters.

---

## Installation

```bash
pip install icad_tone_detection
```

### Requirements

- Python 3.10 or later.
- [ffmpeg](https://ffmpeg.org/) (must be installed and available on the system `PATH`).
- The following Python packages (automatically installed if not present):
    - `numpy>=1.26.4`
    - `requests>=2.31.0`
    - `pydub>=0.25.1`
    - `scipy>=1.12.0`

---

## Getting Started

Here is a quick example on how to use the `tone_detect` function:

```python
from icad_tone_detection import tone_detect

# Point to an audio file (can be local .wav, .mp3, URL, or BytesIO, etc.)
audio_path = "my_scanner_recording.wav"

# Detect various tones
result = tone_detect(
audio_path=audio_path,
matching_threshold=2.5,   # % difference threshold for grouping frequencies
time_resolution_ms=50,    # STFT window hop in ms
tone_a_min_length=0.85,   # Minimum A-tone length for Quick Call
tone_b_min_length=2.6,    # Minimum B-tone length for Quick Call
hi_low_interval=0.2,      # Maximum gap between warble tones
hi_low_min_alternations=6,# Minimum alternations for hi-low
long_tone_min_length=3.8, # Minimum length for long tone
detect_mdc=True,          # Enable MDC1200/FleetSync detection
mdc_high_pass=200,        # High-pass frequency for MDC decoding
mdc_low_pass=4000,        # Low-pass frequency for MDC decoding
detect_dtmf=True,         # Enable DTMF detection
debug=False               # Print debug info
)

# Results are available in the ToneDetectionResult object:
print("Two-Tone/QuickCall:", result.two_tone_result)
print("Long Tones:", result.long_result)
print("Hi-Low/Warble Tones:", result.hi_low_result)
print("MDC1200/FleetSync:", result.mdc_result)
print("DTMF:", result.dtmf_result)
```

---

## Inputs Supported

The `tone_detect` function can handle:

1. **String** pointing to:
    - A local file path (e.g., `"audio.wav"`)
    - A URL (e.g., `"https://example.com/audio.wav"`)
2. **Bytes** or **bytearray** objects (raw audio data).
3. **File-like objects** (`io.BytesIO`, open file handle, etc.).
4. **`pydub.AudioSegment`** objects.

If you pass a local file path or a URL, the library will attempt to read the audio file and then convert it to a standard 16 kHz mono WAV internally using `ffmpeg`. For raw byte data or file-like objects, it similarly uses `ffmpeg` to resample on the fly.

---

## Function Reference

### `tone_detect(...)`

```python
def tone_detect(audio_path, matching_threshold=2.5, time_resolution_ms=50,
tone_a_min_length=0.85, tone_b_min_length=2.6,
hi_low_interval=0.2, hi_low_min_alternations=6,
long_tone_min_length=3.8, detect_mdc=True, mdc_high_pass=200,
mdc_low_pass=4000, detect_dtmf=True, debug=False):
"""
Loads audio from various sources including local path, URL, BytesIO object, or a PyDub AudioSegment.

    Parameters:
        audio_path: string or other supported input types
        matching_threshold (float): ...
        time_resolution_ms (int): ...
        tone_a_min_length (float): ...
        tone_b_min_length (float): ...
        hi_low_interval (float): ...
        hi_low_min_alternations (int): ...
        long_tone_min_length (float): ...
        detect_mdc (bool): ...
        mdc_high_pass (int): ...
        mdc_low_pass (int): ...
        detect_dtmf (bool): ...
        debug (bool): ...
    
    Returns:
        ToneDetectionResult with:
          - two_tone_result
          - long_result
          - hi_low_result
          - mdc_result
          - dtmf_result
    """
    pass
```

**Parameters**
- **audio_path** (various types):  
  The source of audio. Can be a string (path or URL), bytes, `BytesIO`, or `AudioSegment`.
- **matching_threshold** (float):  
  The percentage threshold for grouping frequencies, e.g. `2.5` means frequencies within ±2.5% are considered matching.  
  *Default: 2.5*
- **time_resolution_ms** (int):  
  The time window hop (in ms) used by STFT. Smaller = finer resolution but heavier computation.  
  *Default: 50*
- **tone_a_min_length** (float):  
  Minimum length (seconds) of Tone A for Two-Tone detection.  
  *Default: 0.85*
- **tone_b_min_length** (float):  
  Minimum length (seconds) of Tone B for Two-Tone detection.  
  *Default: 2.6*
- **hi_low_interval** (float):  
  Maximum allowed gap (seconds) between consecutive alternating hi-low warble tones.  
  *Default: 0.2*
- **hi_low_min_alternations** (int):  
  Minimum number of alternations for a hi-low warble sequence.  
  *Default: 6*
- **long_tone_min_length** (float):  
  Minimum length (seconds) for a long tone detection.  
  *Default: 3.8*
- **detect_mdc** (bool):  
  Whether to attempt detecting MDC1200/FleetSync frames.  
  *Default: True*
- **mdc_high_pass** (int):  
  Frequency (Hz) of the high-pass filter for MDC detection.  
  *Default: 200*
- **mdc_low_pass** (int):  
  Frequency (Hz) of the low-pass filter for MDC detection.  
  *Default: 4000*
- **detect_dtmf** (bool):  
  Whether to attempt detecting DTMF signals.  
  *Default: True*
- **debug** (bool):  
  Enable debug info (prints STFT matches, config details, etc.).  
  *Default: False*

**Returns**  
A `ToneDetectionResult` object with the fields:
- `two_tone_result`
- `long_result`
- `hi_low_result`
- `mdc_result`
- `dtmf_result`

Each field holds a list of detected tones or an empty list if none found.

**Result Caveats**

The result includes timestamps in the file where the tones were detected as `start` and `end`. 
These may not align with the original audio due to internal conversions from your input to PCM 16bit @16kHz Mono. If 
those timestamps are important make sure the input matches those requirements.

---

## Command-Line Example

There is an example script called `detect_test.py` under the `examples/` folder. Usage:

```bash
python examples/detect_test.py -p my_scanner_recording.wav \
--matching_threshold 2.5 \
--time_resolution_ms 25 \
--tone_a_min_length 0.7 \
--tone_b_min_length 2.7 \
--long_tone_min_length 3.8 \
--debug
```

This script prints out the detected tone data in JSON to stdout.

---

## Example Audio Files

Under `examples/example_audio`, you can find sample WAV files demonstrating:
- **`dtmf_example.wav`**
- **`hi_low_example.wav`**
- **`long_tone_example.wav`**
- **`mdc_example.wav`**
- **`two_tone_example.wav`**

Use them to experiment with the library.

---

## Platform Binaries

The `icad_decode` binary is automatically chosen depending on your OS/architecture:
- `linux_x86_64`
- `linux_arm64`
- `macos_arm64`
- `windows_x86_64`

On non-Windows systems, the library will automatically `chmod +x` the binary when needed.

If your platform is not supported, you will see a `RuntimeError`. Currently, only the above architectures and operating systems are supported.

---

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

---

## Contributing / Issues

Contributions, bug reports, and feature requests are welcome. Please open issues or submit pull requests on [GitHub](https://github.com/thegreatcodeholio/icad_tone_detection).

---

### Links

- **Homepage**: [GitHub Repository](https://github.com/thegreatcodeholio/icad_tone_detection)
- **Issue Tracker**: [GitHub Issues](https://github.com/thegreatcodeholio/icad_tone_detection/issues)

---

> **Author**: [TheGreatCodeholio](mailto:ian@icarey.net)  
> **Version**: 2.5  
> **Python versions**: 3.10+  
> **License**: MIT