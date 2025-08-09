#!/usr/bin/env python3
"""
CLI wrapper for icad_tone_detection.

Examples:

  # Show help
  icad-tone-detect --help

  # Analyze a file with custom pulsed and warble settings
  icad-tone-detect alarm.wav \
    --detect_pulsed true \
    --pulsed_bw_hz 20 \
    --pulsed_min_cycles 6 \
    --pulsed_min_on_ms 120 --pulsed_max_on_ms 900 \
    --pulsed_min_off_ms 25  --pulsed_max_off_ms 350 \
    --hi_low_interval 0.2 --hi_low_min_alternations 6 \
    --debug
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Tuple

from icad_tone_detection import tone_detect


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #
def str2bool(value: str) -> bool:
    """
    Convert common string representations of truthy / falsy values to bool.

    Accepted truthy values:  "true", "yes", "y", "1"
    Accepted falsy values:   "false", "no", "n", "0"
    """
    true_set  = {"true", "yes", "y", "1"}
    false_set = {"false", "no", "n", "0"}

    if isinstance(value, bool):
        return value

    v = value.strip().lower()
    if v in true_set:
        return True
    if v in false_set:
        return False

    raise argparse.ArgumentTypeError(
        f"Boolean value expected; got '{value}'. "
        f"Use one of: {', '.join(sorted(true_set | false_set))}"
    )


def float_pair(text: str) -> Tuple[float, float]:
    """
    Parse 'LOW,HIGH' or 'LOW HIGH' into a (low, high) float tuple.
    """
    parts = [p for chunk in text.replace(",", " ").split() for p in [chunk] if p]
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("Expected two floats: 'LOW,HIGH' or 'LOW HIGH'")
    low, high = map(float, parts)
    if not (low < high):
        raise argparse.ArgumentTypeError("LOW must be < HIGH")
    return (low, high)


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="icad-tone-detect",
        description="Detect pulsed single-tone, two-tone (Quick Call), long tones, "
                    "hi–low warble, MDC/FleetSync, and DTMF in an audio file."
    )

    # Positional for the audio input (path or URL)
    p.add_argument("audio_path", type=str,
                   help="Path or URL of the audio file to analyse")

    # -------- Core STFT / grouping --------
    p.add_argument("--matching_threshold", "-t", type=float, default=2.5,
                   help="Matching threshold percentage for grouping frames (default: 2.5)")
    p.add_argument("--time_resolution_ms", "-r", type=int, default=50, metavar="MS",
                   help="STFT hop size / time resolution in ms (default: 50)")

    # -------- FrequencyExtraction knobs --------
    p.add_argument("--fe_freq_band", type=float_pair, default=(200.0, 3000.0),
                   metavar="LOW,HIGH",
                   help="Band [Hz] to search for dominant peaks, e.g. '200,3000' (default: 200,3000)")
    p.add_argument("--fe_merge_short_gaps_ms", type=int, default=0, metavar="MS",
                   help="Merge adjacent groups separated by ≤ MS (default: 0 = disabled)")
    p.add_argument("--fe_silence_below_global_db", type=float, default=-28.0, metavar="dB",
                   help="Mark frame OFF if its peak is this many dB below global peak (default: -28)")
    p.add_argument("--fe_snr_above_noise_db", type=float, default=6.0, metavar="dB",
                   help="Additional SNR above estimated noise floor (default: 6)")

    # -------- Two-tone (Quick Call) --------
    p.add_argument("--tone_a_min_length", "-a", type=float, default=0.85, metavar="SEC",
                   help="Minimum A-tone length (default: 0.85 s)")
    p.add_argument("--tone_b_min_length", "-b", type=float, default=2.6, metavar="SEC",
                   help="Minimum B-tone length (default: 2.6 s)")
    p.add_argument("--two_tone_max_gap_between_a_b", type=float, default=0.35, metavar="SEC",
                   help="Max gap between A end and B start (default: 0.35 s)")
    p.add_argument("--two_tone_bw_hz", type=float, default=25.0, metavar="HZ",
                   help="Intra-group stability band for A/B (default: 25 Hz)")
    p.add_argument("--two_tone_min_pair_separation_hz", type=float, default=40.0, metavar="HZ",
                   help="Minimum separation between A and B (default: 40 Hz)")

    # -------- Hi/Low (warble) --------
    p.add_argument("--hi_low_interval", "-i", type=float, default=0.2, metavar="SEC",
                   help="Max interval between alternating tones (default: 0.2 s)")
    p.add_argument("--hi_low_min_alternations", "-n", type=int, default=6, metavar="NUM",
                   help="Minimum alternations in a warble (default: 6)")
    p.add_argument("--hi_low_tone_bw_hz", type=float, default=25.0, metavar="HZ",
                   help="Intra-group stability band for warble groups (default: 25 Hz)")
    p.add_argument("--hi_low_min_pair_separation_hz", type=float, default=40.0, metavar="HZ",
                   help="Minimum separation between the two alternating tones (default: 40 Hz)")

    # -------- Long tone --------
    p.add_argument("--long_tone_min_length", "-l", type=float, default=3.8, metavar="SEC",
                   help="Minimum long-tone duration (default: 3.8 s)")
    p.add_argument("--long_tone_bw_hz", type=float, default=25.0, metavar="HZ",
                   help="Intra-group stability band for long tones (default: 25 Hz)")

    # -------- Pulsed single-tone (auto-centered) --------
    p.add_argument("--pulsed_bw_hz", type=float, default=25.0, metavar="HZ",
                   help="±Hz counted as ON around inferred center (default: 25 Hz)")
    p.add_argument("--pulsed_min_cycles", type=int, default=6, metavar="N",
                   help="Minimum ON→OFF repetitions (default: 6)")
    p.add_argument("--pulsed_min_on_ms", type=int, default=120, metavar="MS",
                   help="Minimum ON duration (default: 120 ms)")
    p.add_argument("--pulsed_max_on_ms", type=int, default=900, metavar="MS",
                   help="Maximum ON duration (default: 900 ms)")
    p.add_argument("--pulsed_min_off_ms", type=int, default=25, metavar="MS",
                   help="Minimum OFF duration (default: 25 ms)")
    p.add_argument("--pulsed_max_off_ms", type=int, default=350, metavar="MS",
                   help="Maximum OFF duration (default: 350 ms)")
    p.add_argument("--pulsed_auto_center_band", type=float_pair, default=(200.0, 3000.0),
                   metavar="LOW,HIGH",
                   help="Band [Hz] to auto-estimate pulsed center, e.g. '200,3000' (default: 200,3000)")
    p.add_argument("--pulsed_mode_bin_hz", type=float, default=5.0, metavar="HZ",
                   help="Histogram bin width for robust center estimate (default: 5 Hz)")

    # -------- Detector toggles --------
    p.add_argument("--detect_pulsed", type=str2bool, default=True, metavar="{true|false}",
                   help="Enable/disable pulsed single-tone detector (default: true)")
    p.add_argument("--detect_two_tone", type=str2bool, default=True, metavar="{true|false}",
                   help="Enable/disable two-tone detector (default: true)")
    p.add_argument("--detect_long", type=str2bool, default=True, metavar="{true|false}",
                   help="Enable/disable long-tone detector (default: true)")
    p.add_argument("--detect_hi_low", type=str2bool, default=True, metavar="{true|false}",
                   help="Enable/disable hi–low warble detector (default: true)")

    # -------- External decoders --------
    p.add_argument("--detect_mdc", type=str2bool, default=True, metavar="{true|false}",
                   help="Enable/disable MDC/FleetSync detection (default: true)")
    p.add_argument("--mdc_high_pass", type=int, default=200,
                   help="High-pass filter for MDC (default: 200 Hz)")
    p.add_argument("--mdc_low_pass", type=int, default=4000,
                   help="Low-pass filter for MDC (default: 4000 Hz)")

    p.add_argument("--detect_dtmf", type=str2bool, default=True, metavar="{true|false}",
                   help="Enable/disable DTMF detection (default: true)")

    # -------- Misc --------
    p.add_argument("-d", "--debug", action="store_true",
                   help="Verbose debug output")

    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    result = tone_detect(
        audio_path=args.audio_path,

        # Core STFT / grouping
        matching_threshold=args.matching_threshold,
        time_resolution_ms=args.time_resolution_ms,

        # FrequencyExtraction knobs
        fe_freq_band=args.fe_freq_band,
        fe_merge_short_gaps_ms=args.fe_merge_short_gaps_ms,
        fe_silence_below_global_db=args.fe_silence_below_global_db,
        fe_snr_above_noise_db=args.fe_snr_above_noise_db,

        # Two-tone
        tone_a_min_length=args.tone_a_min_length,
        tone_b_min_length=args.tone_b_min_length,
        two_tone_max_gap_between_a_b=args.two_tone_max_gap_between_a_b,
        two_tone_bw_hz=args.two_tone_bw_hz,
        two_tone_min_pair_separation_hz=args.two_tone_min_pair_separation_hz,

        # Hi/Low warble
        hi_low_interval=args.hi_low_interval,
        hi_low_min_alternations=args.hi_low_min_alternations,
        hi_low_tone_bw_hz=args.hi_low_tone_bw_hz,
        hi_low_min_pair_separation_hz=args.hi_low_min_pair_separation_hz,

        # Long tone
        long_tone_min_length=args.long_tone_min_length,
        long_tone_bw_hz=args.long_tone_bw_hz,

        # Pulsed single-tone (auto-centered)
        pulsed_bw_hz=args.pulsed_bw_hz,
        pulsed_min_cycles=args.pulsed_min_cycles,
        pulsed_min_on_ms=args.pulsed_min_on_ms,
        pulsed_max_on_ms=args.pulsed_max_on_ms,
        pulsed_min_off_ms=args.pulsed_min_off_ms,
        pulsed_max_off_ms=args.pulsed_max_off_ms,
        pulsed_auto_center_band=args.pulsed_auto_center_band,
        pulsed_mode_bin_hz=args.pulsed_mode_bin_hz,

        # Detector toggles
        detect_pulsed=args.detect_pulsed,
        detect_two_tone=args.detect_two_tone,
        detect_long=args.detect_long,
        detect_hi_low=args.detect_hi_low,

        # External decoders
        detect_mdc=args.detect_mdc,
        mdc_high_pass=args.mdc_high_pass,
        mdc_low_pass=args.mdc_low_pass,
        detect_dtmf=args.detect_dtmf,

        # Misc
        debug=args.debug,
    )

    print(json.dumps({
        "pulsed":    result.pulsed_result,
        "two_tone":  result.two_tone_result,
        "long_tone": result.long_result,
        "hi_low":    result.hi_low_result,
        "mdc":       result.mdc_result,
        "dtmf":      result.dtmf_result,
    }, indent=2))


if __name__ == "__main__":
    sys.exit(main())
