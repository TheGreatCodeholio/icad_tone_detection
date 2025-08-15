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

### Defaults work for most recordings

The built-in defaults are intentionally **neutral** and should work well on typical scanner audio (8–16 kHz mono, moderate noise). In many cases you can just call tone detection with no extra knobs and get solid results. All detectors are enabled by default, and the frontend (STFT + grouping) aims to avoid over- or under-segmenting tones.

Use the simplest call first:

```python
from icad_tone_detection import tone_detect

result = tone_detect("my_scanner_recording.wav")
print(result.pulsed_result)
print(result.two_tone_result)
```

Or via CLI:

```bash
icad-tone-detect my_scanner_recording.wav --debug
```

**Only tweak parameters if you have a specific problem** (e.g., very drifty tones, very brisk pulses, or unusually noisy/quiet recordings).

**When to tweak (quick guide):**
- **Very fast pulses** → lower `time_resolution_ms` from `50` to `25`.
- **Tone drift gets merged** (e.g., 992/950 collapsing) → set `fe_abs_cap_hz=20–24`, and optionally `fe_force_split_step_hz≈18` with `fe_split_lookahead_frames=2`.
- **Too many weak frames pass** (noisy audio) → make gating **stricter** by raising `fe_silence_below_global_db` (e.g., `-24` dB) or increasing `fe_snr_above_noise_db` (e.g., `8` dB).
- **Real tones get gated out** (very quiet recording) → make gating **looser** by lowering `fe_silence_below_global_db` (e.g., `-32` dB) or decreasing `fe_snr_above_noise_db` (e.g., `4` dB).
- **Two-tone pairs too wide/tight** → adjust `two_tone_bw_hz` (typical `20–30` Hz) and ensure `two_tone_min_pair_separation_hz` (default `40` Hz) fits your system.

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
  --pulsed_bw_hz 25 \
  --pulsed_min_cycles 6 \
  --pulsed_min_on_ms 120  --pulsed_max_on_ms 900 \
  --pulsed_min_off_ms 25  --pulsed_max_off_ms 350 \
  --pulsed_auto_center_band 200,3000 \
  --pulsed_mode_bin_hz 5 \
  \
  --detect_two_tone true \
  --tone_a_min_length 0.85 --tone_b_min_length 2.6 \
  --two_tone_bw_hz 25 --two_tone_min_pair_separation_hz 40 \
  \
  --detect_hi_low true \
  --hi_low_interval 0.2 --hi_low_min_alternations 6 \
  --hi_low_tone_bw_hz 25 --hi_low_min_pair_separation_hz 40 \
  \
  --detect_long true \
  --long_tone_min_length 3.8 --long_tone_bw_hz 25 \
  \
  --detect_mdc false --detect_dtmf true \
  \
  --time_resolution_ms 50 --matching_threshold 2.5 \
  --fe_freq_band 200,3000 \
  --fe_merge_short_gaps_ms 0 \
  --fe_silence_below_global_db -28 --fe_snr_above_noise_db 6 \
  \
  # FE refinements to keep stepped pairs from merging:
  --fe_abs_cap_hz 30 \
  --fe_force_split_step_hz 18 \
  --fe_split_lookahead_frames 2 \
  \
  --debug
```

---

## Example output (debug mode)

```text
############################################################
ICAD Tone Detection: DEBUG - v2.8.3
------------------------------------------------------------
Decode binary path:        /opt/icad/bin/linux_x86_64/icad_decode
Analyzing audio at:        /captures/2025-08-09_call_173.wav

Matching Threshold:        2.5%
Time Resolution (ms):      50

-- Frequency Extraction (frontend) --
  Search band (Hz):        200.0..3000.0
  Merge short gaps ≤ ms:   0
  Silence below global:    -28.0 dB
  SNR above noise floor:   +6.0 dB
  Abs cap (Hz):            30.0
  Force-split step (Hz):   18.0
  Split lookahead frames:  2

-- Two-Tone (Quick Call) --
  A min length (s):        0.85
  B min length (s):        2.60
  Max A→B gap (s):         0.35
  Intra-band width (Hz):   25.0
  Min A/B separation (Hz): 40.0

-- Long Tone --
  Min length (s):          3.80
  Intra-band width (Hz):   25.0

-- Hi–Low Warble --
  Interval (s):            0.20
  Min alternations:        6
  Intra-band width (Hz):   25.0
  Min pair separation (Hz):40.0

-- Pulsed Single Tone (auto-centered) --
  Band (Hz):               200.0..3000.0
  Mode bin width (Hz):     5.0
  BW around center (Hz):   ±25.0
  Min cycles:              6
  ON range (ms):           120..900
  OFF range (ms):          25..350

-- External Decoders --
  MDC/FleetSync:           disabled (hp=200 Hz, lp=4000 Hz)
  DTMF:                    enabled

Total Duration (s):        39.42
Sample Rate (Hz):          16000

Matched Frequencies (8 groups):
  1) Start=2.31s  | End=5.24s  | Dur=2.93s
       Freqs: [1009.9, 1010.4, 1010.2, 1010.1, 1010.1, 1010.0, 1010.1, 1009.8, 1010.3, 1010.2]
  2) Start=5.24s  | End=5.31s  | Dur=0.07s
       Freqs: [0.0, 0.0]                       # OFF
  3) Start=5.31s  | End=8.18s  | Dur=2.87s
       Freqs: [473.3, 473.2, 473.2, 473.4, 473.2, 473.3, 473.2, 473.3, 473.2]
  4) Start=8.18s  | End=8.22s  | Dur=0.04s
       Freqs: [0.0]                            # OFF
  5) Start=8.22s  | End=11.10s | Dur=2.88s
       Freqs: [809.9, 810.0, 810.1, 809.9, 810.0, 810.0, 810.1, 810.0, 810.0]
  6) Start=12.00s | End=12.08s | Dur=0.08s
       Freqs: [770.1, 770.0, 770.1, 769.9]
  7) Start=12.35s | End=12.43s | Dur=0.08s
       Freqs: [1206.9, 1207.1, 1207.0, 1206.8]
  8) Start=20.52s | End=23.34s | Dur=2.82s
       Freqs: [954.7, 954.9, 955.1, 954.8, 955.0, 954.9, 954.8, 954.9, 954.9]

############################################################
Masked intervals
  Pulsed windows:          [2.31–5.24], [20.52–23.34]
  Two-tone B windows:      [8.22–11.10]
  Long-tone windows:       (none)
############################################################

------------------------------------------------------------
DETECTION SUMMARY
------------------------------------------------------------
Two-Tone (Quick Call): 1
Long Tones:            0
Hi-Low Warble:         0
Pulsed Single Tone:    2
MDC1200/FleetSync:     0   (disabled)
DTMF:                  2
------------------------------------------------------------

{
  "pulsed": [
    {
      "tone_id": "pl_1",
      "detected": 1010.1,
      "start": 2.31, "end": 5.24, "length": 2.93,
      "cycles": 8,
      "on_ms_median": 180, "off_ms_median": 92
    },
    {
      "tone_id": "pl_2",
      "detected": 955.0,
      "start": 20.52, "end": 23.34, "length": 2.82,
      "cycles": 7,
      "on_ms_median": 160, "off_ms_median": 85
    }
  ],
  "two_tone": [
    {
      "tone_id": "qc_1",
      "detected": [473.3, 810.0],
      "tone_a_length": 0.91, "tone_b_length": 2.88,
      "start": 5.31, "end": 11.10
    }
  ],
  "long_tone": [],
  "hi_low": [],
  "mdc": [],
  "dtmf": [
    { "digit": "5", "start": 12.00, "end": 12.08 },
    { "digit": "9", "start": 12.35, "end": 12.43 }
  ]
}
```

---

## Python API — `tone_detect()` signature

```python
result = tone_detect(
  audio_path="my.wav",          # path / URL / BytesIO / AudioSegment

  # STFT & grouping
  matching_threshold=2.5,       # % tolerance for grouping frames
  time_resolution_ms=50,        # STFT hop size in ms

  # Frequency-extraction (frontend)
  fe_freq_band=(200.0, 3000.0),         # Hz band to search for peaks
  fe_merge_short_gaps_ms=0,             # merge groups separated by ≤ this gap (ms)
  fe_silence_below_global_db=-28.0,     # OFF if frame is this many dB below global peak
  fe_snr_above_noise_db=6.0,            # require SNR above simple noise floor
  fe_abs_cap_hz=None,                   # cap dynamic tolerance (e.g., 30.0) or None
  fe_force_split_step_hz=None,          # force split if step > Hz (e.g., 18.0) or None
  fe_split_lookahead_frames=0,          # confirm forced split with lookahead

  # Quick Call (two-tone)
  tone_a_min_length=0.85,               # sec – min A-tone
  tone_b_min_length=2.6,                # sec – min B-tone
  two_tone_max_gap_between_a_b=0.35,    # sec – max gap A→B
  two_tone_bw_hz=25.0,                  # Hz – intra-group stability
  two_tone_min_pair_separation_hz=40.0, # Hz – min A/B separation

  # Hi/Low warble
  hi_low_interval=0.2,                  # sec – max gap between alternations
  hi_low_min_alternations=6,            # min alternations
  hi_low_tone_bw_hz=25.0,               # Hz – intra-group stability
  hi_low_min_pair_separation_hz=40.0,   # Hz – min separation between tones

  # Long tone
  long_tone_min_length=3.8,             # sec – min duration
  long_tone_bw_hz=25.0,                 # Hz – intra-group stability

  # Pulsed single tone (auto-centered)
  pulsed_bw_hz=25.0,                    # Hz ± deviation counted as ON
  pulsed_min_cycles=6,                  # min ON→OFF cycles
  pulsed_min_on_ms=120,                 # ms – ON min
  pulsed_max_on_ms=900,                 # ms – ON max
  pulsed_min_off_ms=25,                 # ms – OFF min
  pulsed_max_off_ms=350,                # ms – OFF max
  pulsed_auto_center_band=(200.0, 3000.0),  # Hz band to auto-estimate center
  pulsed_mode_bin_hz=5.0,               # Hz bin width for robust center mode

  # Detector toggles
  detect_pulsed=True,
  detect_two_tone=True,
  detect_long=True,
  detect_hi_low=True,

  # External decoders
  detect_mdc=True,                      # MDC1200 / FleetSync
  mdc_high_pass=200,                    # Hz
  mdc_low_pass=4000,                    # Hz
  detect_dtmf=True,

  debug=False,
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

MIT © TheGreatCodeholio • Version 2.8.4 • Python 3.9+
