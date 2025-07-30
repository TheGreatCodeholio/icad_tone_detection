#!/usr/bin/env python3
"""
CLI wrapper for icad_tone_detection.

Usage example:

    icad-tone-detect alarm.wav --detect_mdc false --debug
"""
from __future__ import annotations
import argparse
import json
import sys

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

    if isinstance(value, bool):  # already a bool (rare)
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


# --------------------------------------------------------------------------- #
# CLI                                                                        #
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="icad-tone-detect",
        description="Detect two-tone, long-tone, warble, MDC/FleetSync and "
                    "DTMF in an audio file."
    )

    # Positional for the audio input (path or URL)
    p.add_argument("audio_path", type=str,
                   help="Path or URL of the audio file to analyse")

    # Numeric / float parameters
    p.add_argument("--matching_threshold",  "-t", type=float, default=2.5,
                   help="Matching threshold percentage (default: 2.5)")
    p.add_argument("--time_resolution_ms",  "-r", type=int,   default=50,
                   metavar="MS",
                   help="Time resolution of STFT in ms (default: 50)")
    p.add_argument("--tone_a_min_length",   "-a", type=float, default=0.85,
                   metavar="SEC",
                   help="Min length of tone-A (default: 0.85)")
    p.add_argument("--tone_b_min_length",   "-b", type=float, default=2.6,
                   metavar="SEC",
                   help="Min length of tone-B (default: 2.6)")
    p.add_argument("--long_tone_min_length","-l",type=float, default=3.8,
                   metavar="SEC",
                   help="Min length of a long tone (default: 3.8)")
    p.add_argument("--hi_low_interval",     "-i", type=float, default=0.2,
                   metavar="SEC",
                   help="Max interval between hi/low (default: 0.2)")
    p.add_argument("--hi_low_min_alternations", "-n", type=int, default=6,
                   metavar="NUM",
                   help="Min hi/low alternations (default: 6)")

    # Boolean parameters now expect an explicit value
    p.add_argument("--detect_mdc",
                   type=str2bool,
                   default=True,
                   metavar="{true|false}",
                   help="Enable/disable MDC/FleetSync detection (default: true)")
    p.add_argument("--mdc_high_pass", type=int, default=200,
                   help="High-pass filter for MDC (default: 200 Hz)")
    p.add_argument("--mdc_low_pass",  type=int, default=4000,
                   help="Low-pass filter for MDC (default: 4000 Hz)")

    p.add_argument("--detect_dtmf",
                   type=str2bool,
                   default=True,
                   metavar="{true|false}",
                   help="Enable/disable DTMF detection (default: true)")

    # Debug flag (still traditional store_true because it’s a flag-like switch)
    p.add_argument("-d", "--debug", action="store_true",
                   help="Verbose debug output")

    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    result = tone_detect(
        audio_path=args.audio_path,
        matching_threshold=args.matching_threshold,
        time_resolution_ms=args.time_resolution_ms,
        tone_a_min_length=args.tone_a_min_length,
        tone_b_min_length=args.tone_b_min_length,
        hi_low_interval=args.hi_low_interval,
        hi_low_min_alternations=args.hi_low_min_alternations,
        long_tone_min_length=args.long_tone_min_length,
        detect_mdc=args.detect_mdc,
        mdc_high_pass=args.mdc_high_pass,
        mdc_low_pass=args.mdc_low_pass,
        detect_dtmf=args.detect_dtmf,
        debug=args.debug,
    )

    # Pretty JSON output
    print(json.dumps({
        "two_tone":  result.two_tone_result,
        "long_tone": result.long_result,
        "hi_low":    result.hi_low_result,
        "mdc":       result.mdc_result,
        "dtmf":      result.dtmf_result,
    }, indent=2))


if __name__ == "__main__":         # allow `python cli.py …` for quick tests
    sys.exit(main())
