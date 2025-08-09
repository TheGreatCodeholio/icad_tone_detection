#!/usr/bin/env python3
import argparse
import json
from icad_tone_detection import tone_detect


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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run tone detection on an audio file."
    )

    # Audio path
    p.add_argument(
        "-p", "--audio_path", type=str, required=True,
        help="Path or URL to the audio file"
    )

    # STFT & grouping
    p.add_argument(
        "-t", "--matching_threshold", type=float, default=2.5,
        help="Matching threshold percentage for grouping (default: 2.5)"
    )
    p.add_argument(
        "-r", "--time_resolution_ms", type=int, default=50,
        help="STFT hop size / time resolution in ms (default: 50)"
    )

    # ---- FrequencyExtraction knobs ----
    p.add_argument(
        "--fe_freq_band_low", type=float, default=200.0,
        help="Lower bound of peak-pick band in Hz (default: 200.0)"
    )
    p.add_argument(
        "--fe_freq_band_high", type=float, default=3000.0,
        help="Upper bound of peak-pick band in Hz (default: 3000.0)"
    )
    p.add_argument(
        "--fe_merge_short_gaps_ms", type=int, default=0,
        help="Merge adjacent groups separated by ≤ this gap (ms). 0 = disabled (default: 0)"
    )
    p.add_argument(
        "--fe_silence_below_global_db", type=float, default=-28.0,
        help="Frame OFF if below this many dB from file global peak (default: -28.0)"
    )
    p.add_argument(
        "--fe_snr_above_noise_db", type=float, default=6.0,
        help="Require frame ≥ this many dB above noise-floor estimate (default: 6.0)"
    )

    # ---- Two-tone (Quick Call) ----
    p.add_argument(
        "-a", "--tone_a_min_length", type=float, default=0.85,
        help="Min length of tone A in seconds (default: 0.85)"
    )
    p.add_argument(
        "-b", "--tone_b_min_length", type=float, default=2.6,
        help="Min length of tone B in seconds (default: 2.6)"
    )
    p.add_argument(
        "--two_tone_max_gap_between_a_b", type=float, default=0.35,
        help="Max A→B gap in seconds (default: 0.35)"
    )
    p.add_argument(
        "--two_tone_bw_hz", type=float, default=25.0,
        help="Intra-group stability band in Hz (default: 25.0)"
    )
    p.add_argument(
        "--two_tone_min_pair_separation_hz", type=float, default=40.0,
        help="Min A/B separation in Hz (default: 40.0)"
    )

    # ---- Hi/Low (warble) ----
    p.add_argument(
        "-i", "--hi_low_interval", type=float, default=0.2,
        help="Max interval between hi/low groups in seconds (default: 0.2)"
    )
    p.add_argument(
        "-n", "--hi_low_min_alternations", type=int, default=6,
        help="Min number of hi/low alternations (default: 6)"
    )
    p.add_argument(
        "--hi_low_tone_bw_hz", type=float, default=25.0,
        help="Intra-group stability band for warble in Hz (default: 25.0)"
    )
    p.add_argument(
        "--hi_low_min_pair_separation_hz", type=float, default=40.0,
        help="Min separation between the two alternating tones in Hz (default: 40.0)"
    )

    # ---- Long tone ----
    p.add_argument(
        "-l", "--long_tone_min_length", type=float, default=3.8,
        help="Min length of a long tone in seconds (default: 3.8)"
    )
    p.add_argument(
        "--long_tone_bw_hz", type=float, default=25.0,
        help="Intra-group stability band for long tone in Hz (default: 25.0)"
    )

    # ---- Pulsed single tone (auto-centered) ----
    p.add_argument(
        "--pulsed_bw_hz", type=float, default=25.0,
        help="±Hz around inferred center to count frames as ON (default: 25.0)"
    )
    p.add_argument(
        "--pulsed_min_cycles", type=int, default=6,
        help="Min ON→OFF repetitions (default: 6)"
    )
    p.add_argument(
        "--pulsed_min_on_ms", type=int, default=120,
        help="Min ON duration in ms (default: 120)"
    )
    p.add_argument(
        "--pulsed_max_on_ms", type=int, default=900,
        help="Max ON duration in ms (default: 900)"
    )
    p.add_argument(
        "--pulsed_min_off_ms", type=int, default=25,
        help="Min OFF duration in ms (default: 25)"
    )
    p.add_argument(
        "--pulsed_max_off_ms", type=int, default=350,
        help="Max OFF duration in ms (default: 350)"
    )
    p.add_argument(
        "--pulsed_center_low", type=float, default=200.0,
        help="Auto-center search band low Hz (default: 200.0)"
    )
    p.add_argument(
        "--pulsed_center_high", type=float, default=3000.0,
        help="Auto-center search band high Hz (default: 3000.0)"
    )
    p.add_argument(
        "--pulsed_mode_bin_hz", type=float, default=5.0,
        help="Histogram bin width for robust mode (default: 5.0)"
    )

    # ---- Detector toggles ----
    p.add_argument(
        "--detect_pulsed", type=str2bool, default=True, metavar="{true|false}",
        help="Enable/disable pulsed single-tone detection (default: true)"
    )
    p.add_argument(
        "--detect_two_tone", type=str2bool, default=True, metavar="{true|false}",
        help="Enable/disable two-tone detection (default: true)"
    )
    p.add_argument(
        "--detect_long", type=str2bool, default=True, metavar="{true|false}",
        help="Enable/disable long-tone detection (default: true)"
    )
    p.add_argument(
        "--detect_hi_low", type=str2bool, default=True, metavar="{true|false}",
        help="Enable/disable hi–low warble detection (default: true)"
    )

    # ---- External decoders ----
    p.add_argument(
        "--detect_mdc", type=str2bool, default=True, metavar="{true|false}",
        help="Enable/disable MDC/FleetSync detection (default: true)"
    )
    p.add_argument(
        "--mdc_high_pass", type=int, default=200,
        help="High-pass filter for MDC (Hz) (default: 200)"
    )
    p.add_argument(
        "--mdc_low_pass", type=int, default=4000,
        help="Low-pass filter for MDC (Hz) (default: 4000)"
    )
    p.add_argument(
        "--detect_dtmf", type=str2bool, default=True, metavar="{true|false}",
        help="Enable/disable DTMF detection (default: true)"
    )

    # Debug
    p.add_argument(
        "-d", "--debug", action="store_true",
        help="Verbose debug output"
    )

    return p


def main():
    args = build_parser().parse_args()

    detect_result = tone_detect(
        audio_path=args.audio_path,

        # STFT & grouping
        matching_threshold=args.matching_threshold,
        time_resolution_ms=args.time_resolution_ms,

        # FrequencyExtraction
        fe_freq_band=(args.fe_freq_band_low, args.fe_freq_band_high),
        fe_merge_short_gaps_ms=args.fe_merge_short_gaps_ms,
        fe_silence_below_global_db=args.fe_silence_below_global_db,
        fe_snr_above_noise_db=args.fe_snr_above_noise_db,

        # Two-tone
        tone_a_min_length=args.tone_a_min_length,
        tone_b_min_length=args.tone_b_min_length,
        two_tone_max_gap_between_a_b=args.two_tone_max_gap_between_a_b,
        two_tone_bw_hz=args.two_tone_bw_hz,
        two_tone_min_pair_separation_hz=args.two_tone_min_pair_separation_hz,

        # Hi/Low
        hi_low_interval=args.hi_low_interval,
        hi_low_min_alternations=args.hi_low_min_alternations,
        hi_low_tone_bw_hz=args.hi_low_tone_bw_hz,
        hi_low_min_pair_separation_hz=args.hi_low_min_pair_separation_hz,

        # Long tone
        long_tone_min_length=args.long_tone_min_length,
        long_tone_bw_hz=args.long_tone_bw_hz,

        # Pulsed single tone
        pulsed_bw_hz=args.pulsed_bw_hz,
        pulsed_min_cycles=args.pulsed_min_cycles,
        pulsed_min_on_ms=args.pulsed_min_on_ms,
        pulsed_max_on_ms=args.pulsed_max_on_ms,
        pulsed_min_off_ms=args.pulsed_min_off_ms,
        pulsed_max_off_ms=args.pulsed_max_off_ms,
        pulsed_auto_center_band=(args.pulsed_center_low, args.pulsed_center_high),
        pulsed_mode_bin_hz=args.pulsed_mode_bin_hz,

        # Toggles
        detect_pulsed=args.detect_pulsed,
        detect_two_tone=args.detect_two_tone,
        detect_long=args.detect_long,
        detect_hi_low=args.detect_hi_low,

        # External decoders
        detect_mdc=args.detect_mdc,
        mdc_high_pass=args.mdc_high_pass,
        mdc_low_pass=args.mdc_low_pass,
        detect_dtmf=args.detect_dtmf,

        debug=args.debug,
    )

    data_dict = {
        "pulsed":   detect_result.pulsed_result,
        "two_tone": detect_result.two_tone_result,
        "long_tone": detect_result.long_result,
        "hi_low":   detect_result.hi_low_result,
        "mdc":      detect_result.mdc_result,
        "dtmf":     detect_result.dtmf_result,
    }

    print(json.dumps(data_dict, indent=2))


if __name__ == "__main__":
    main()
