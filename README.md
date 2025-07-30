# icad_tone_detection

[![PyPI version](https://badge.fury.io/py/icad_tone_detection.svg)](https://pypi.org/project/icad_tone_detection)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Detect Two-Tone (Quick Call), long tones, hi-low *warble* tones, MDC1200 / FleetSync and DTMF in scanner-audio recordings.  
The heavy DSP is performed by an included native binary (`icad_decode`) while the Python layer handles audio I/O and STFT-based frequency extraction.

---

## Features

- **Single call** `tone_detect()` *or* the CLI `icad-tone-detect`.
- **Tone types**: Two-Tone / Quick Call, long, warble, MDC1200 / FleetSync, DTMF.
- **Flexible inputs**: local path, URL, `bytes`, `BytesIO`, or a `pydub.AudioSegment`.
- **Automatic resample** to 16 kHz mono PCM via FFmpeg.
- **Tweakable**: every threshold & filter exposed as a keyword arg / CLI flag.
- **Binaries included**
  - Linux `x86-64`, `arm64`, `armv7`
  - macOS Intel & Apple Silicon
  - Windows `x86-64`

---

## Installation

```bash
pip install icad_tone_detection
```

> *Requires **Python 3.9 +** and **FFmpeg** in `PATH`.*

---

## Quick start (Python)

```python
from icad_tone_detection import tone_detect

result = tone_detect("my_scanner_recording.wav")
print(result.two_tone_result)
```

---

## Quick start (CLI)

An executable **`icad-tone-detect`** is added to your `$PATH`:

```bash
# show help
icad-tone-detect --help

# analyse a file with MDC disabled
icad-tone-detect my.wav --detect_mdc false --debug
```

Boolean flags accept **true/false • yes/no • 1/0**.

---

## Full CLI example

```bash
icad-tone-detect my_scanner_recording.wav \
--detect_mdc false    --detect_dtmf true \
--time_resolution_ms 25 --tone_a_min_length 0.7 \
--tone_b_min_length 2.7 --long_tone_min_length 3.8 \
--debug
```

Typical output with debug ⇣

```text
D############################################################
ICAD Tone Detection: DEBUG - v2.7.0
------------------------------------------------------------
Decode binary path:        /…/bin/linux_arm64/icad_decode
Analyzing audio at:        my_scanner_recording.wav
Matching Threshold:        2.5%
Time Resolution (ms):      25
… (trimmed) …
############################################################
------------------------------------------------------------
DETECTION SUMMARY
------------------------------------------------------------
Two-Tone (Quick Call): 1
Long Tones:            0
Hi-Low Warble:         0
MDC1200/FleetSync:     0   (disabled)
DTMF:                  3
------------------------------------------------------------
{
  "two_tone": [
    {
      "tone_a_freq": 473.2,
      "tone_b_freq": 810.0,
      "start": 1.23,
      "end": 4.07
    }
  ],
  "long_tone": [],
  "hi_low": [],
  "mdc": [],
  "dtmf": [
    { "digit": "5", "start": 7.01, "end": 7.08 },
    { "digit": "5", "start": 7.18, "end": 7.25 },
    { "digit": "9", "start": 7.35, "end": 7.42 }
  ]
}
```

---

## `tone_detect()` signature (API users)

```python
result = tone_detect(
  audio_path="my.wav",         # path / URL / BytesIO / AudioSegment
  matching_threshold=2.5,      # % tolerance for grouping freqs
  time_resolution_ms=50,       # STFT hop size in ms
  tone_a_min_length=0.85,      # sec  – min A-tone for Quick Call
  tone_b_min_length=2.6,       # sec  – min B-tone for Quick Call
  hi_low_interval=0.2,         # sec  – max gap between warble tones
  hi_low_min_alternations=6,   #       min hi/low swaps
  long_tone_min_length=3.8,    # sec  – min duration for long tone
  detect_mdc=True,             # toggle MDC1200 / FleetSync
  mdc_high_pass=200,           # Hz   – high-pass for MDC
  mdc_low_pass=4000,           # Hz   – low-pass  for MDC
  detect_dtmf=True,            # toggle DTMF decoding
  debug=False                  # print extra diagnostics
)  # -> ToneDetectionResult
```

See the doc-string for parameter details.

---

## Supported platforms & binaries

| OS      | Architectures | Folder inside wheel |
|---------|---------------|---------------------|
| Linux   | x86-64, arm64, armv7 | `linux_x86_64`, `linux_arm64`, `linux_armv7` |
| macOS   | x86-64, arm64 | `macos_x86_64`, `macos_arm64` |
| Windows | x86-64        | `windows_x86_64` |

The loader sets execute permissions automatically on Unix-like systems.  
On other CPUs you can compile your own binary and point the library to it via `ICAD_DECODE_PATH`.

---

## Example audio

Sample WAV files live in **`examples/example_audio/`** for quick testing.

---

## Contributing

Issues and pull-requests are welcome — visit the [GitHub repo](https://github.com/thegreatcodeholio/icad_tone_detection).

---

## License

MIT © TheGreatCodeholio • version 2.7.0 • Python 3.9 +
