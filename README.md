# icad_tone_detection

[![PyPI version](https://badge.fury.io/py/icad_tone_detection.svg)](https://pypi.org/project/icad_tone_detection)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Detect **Two-Tone (Quick Call)**, **Pulsed Single-Tone** (On/Off Beeps), **Long Tones**, **Hi–Low warble tones**, **MDC1200 / FleetSync**, and **DTMF** in scanner-audio recordings.  
The heavy DSP is performed by a bundled native binary (`icad_decode`), while the Python wrapper handles audio I/O and STFT-based frequency extraction.

---

## Features

- **Single function**: `tone_detect()` or CLI tool `icad-tone-detect`
- **Tone types**:
  - Pulsed single-tone
  - Two-Tone / Quick Call
  - Long tones
  - Hi–Low warble tones
  - MDC1200 / FleetSync
  - DTMF
- **Flexible inputs**: File path, URL, `bytes`, `BytesIO`, or `pydub.AudioSegment`
- **Automatic resample** to 16 kHz mono PCM via FFmpeg
- **Fully configurable**: All thresholds & detection params exposed as keyword args or CLI flags
- **Binaries included** for:
  - Linux (`x86_64`, `arm64`, `armv7`)
  - macOS (`x86_64`, `arm64`)
  - Windows (`x86_64`)

---

## Installation

```bash
pip install icad_tone_detection
```

> **Requires:** Python 3.9+ and `ffmpeg` in `PATH`.

---

## Quick start — Python

```python
from icad_tone_detection import tone_detect

result = tone_detect("my_scanner_recording.wav")
print(result.pulsed_result)
print(result.two_tone_result)
```

---

## Quick start — CLI

```bash
# Show help
icad-tone-detect --help

# Analyze a file with MDC disabled
icad-tone-detect my.wav --detect_mdc false --debug
```

Boolean flags accepted: `true/false`, `yes/no`, or `1/0`.

---

## Full CLI example

```bash
icad-tone-detect my_scanner_recording.wav \
--detect_pulsed true \
--pulsed_center_hz 1010 --pulsed_bw_hz 25 \
--pulsed_min_cycles 6 \
--pulsed_min_on_ms 120  --pulsed_max_on_ms 900 \
--pulsed_min_off_ms 25  --pulsed_max_off_ms 350 \
--detect_two_tone true \
--tone_a_min_length 0.85 --tone_b_min_length 2.6 \
--detect_hi_low true --hi_low_interval 0.2 --hi_low_min_alternations 6 \
--detect_long true --long_tone_min_length 3.8 \
--detect_mdc false --detect_dtmf true \
--time_resolution_ms 50 --matching_threshold 2.5 \
--debug
```

---

## Example output (debug mode)

```text
############################################################
ICAD Tone Detection: DEBUG - v2.8.0
------------------------------------------------------------
Decode binary path:        /…/bin/linux_arm64/icad_decode
Analyzing audio at:        my_scanner_recording.wav
Matching Threshold:        2.5%
Time Resolution (ms):      50
… (trimmed) …
------------------------------------------------------------
DETECTION SUMMARY
------------------------------------------------------------
Two-Tone (Quick Call): 1
Long Tones:            0
Hi-Low Warble:         0
Pulsed Single Tone:    3
MDC1200/FleetSync:     0   (disabled)
DTMF:                  2
------------------------------------------------------------
{
"pulsed": [
{
"tone_id": "pl_1",
"detected": 1010.1,
"start": 2.31, "end": 5.12, "length": 2.81,
"cycles": 8,
"on_ms_median": 180, "off_ms_median": 95
}
],
"two_tone": [
{
"tone_id": "qc_1",
"detected": [473.2, 810.0],
"tone_a_length": 0.90, "tone_b_length": 2.84,
"start": 6.23, "end": 9.07
}
],
"long_tone": [],
"hi_low": [],
"mdc": [],
"dtmf": [
{ "digit": "5", "start": 12.01, "end": 12.08 },
{ "digit": "9", "start": 12.35, "end": 12.42 }
]
}
```

---

## Python API — `tone_detect()` signature

```python
result = tone_detect(
audio_path="my.wav",          # path / URL / BytesIO / AudioSegment

    # STFT & grouping
    matching_threshold=2.5,       # % tolerance for grouping freqs
    time_resolution_ms=50,        # STFT hop size in ms

    # Quick Call (two-tone)
    tone_a_min_length=0.85,       # sec – min A-tone
    tone_b_min_length=2.6,        # sec – min B-tone

    # Hi/Low warble
    hi_low_interval=0.2,          # sec – max gap between hi/low groups
    hi_low_min_alternations=6,    # min alternations

    # Long tone
    long_tone_min_length=3.8,     # sec – min duration

    # Pulsed single-tone (~1 kHz)
    pulsed_center_hz=None,        # Hz – None=auto estimate (200–3000 Hz)
    pulsed_bw_hz=25.0,            # Hz ± deviation counted as ON
    pulsed_min_cycles=6,          # min ON→OFF cycles
    pulsed_min_on_ms=120,         # ms – ON min
    pulsed_max_on_ms=900,         # ms – ON max
    pulsed_min_off_ms=25,         # ms – OFF min
    pulsed_max_off_ms=350,        # ms – OFF max

    # Detector toggles
    detect_pulsed=True,
    detect_two_tone=True,
    detect_long=True,
    detect_hi_low=True,

    # External decoders
    detect_mdc=True,              # MDC1200 / FleetSync
    mdc_high_pass=200,            # Hz
    mdc_low_pass=4000,            # Hz
    detect_dtmf=True,

    debug=False
)
```

---

## Result object

`tone_detect()` returns a `ToneDetectionResult` dataclass with:

- `pulsed_result` — Pulsed single-tone hits: `tone_id`, `detected`, `start`, `end`, `length`, `cycles`, `on_ms_median`, `off_ms_median`
- `two_tone_result` — Quick-Call matches: `tone_id`, `detected` `[A,B]`, `tone_a_length`, `tone_b_length`, `start`, `end`
- `long_result` — Long tone hits: `tone_id`, `detected`, `length`, `start`, `end`
- `hi_low_result` — Warble sequences: `tone_id`, `detected` `[low,high]`, `alternations`, `length`, `start`, `end`
- `mdc_result` — Decoded frames from external MDC/FleetSync decoder (if enabled)
- `dtmf_result` — Decoded DTMF presses (if enabled)

---

## Platforms & binaries

| OS      | Architectures        | Wheel folder name              |
|---------|----------------------|---------------------------------|
| Linux   | x86_64, arm64, armv7 | `linux_x86_64`, `linux_arm64`, `linux_armv7` |
| macOS   | x86_64, arm64        | `macos_x86_64`, `macos_arm64`  |
| Windows | x86_64               | `windows_x86_64`               |

---

## Example audio

Sample WAV files are in `examples/example_audio/`.

---

## Contributing

Issues and pull requests welcome: [GitHub repo](https://github.com/thegreatcodeholio/icad_tone_detection)

---

## License

MIT © TheGreatCodeholio • Version 2.8.1 • Python 3.9+
