#!/usr/bin/env python3
import argparse
import json
from icad_tone_detection import tone_detect


def main():
    parser = argparse.ArgumentParser(description='Run tone detection on an audio file.')

    # Audio path
    parser.add_argument('-p', '--audio_path', type=str, required=True,
                        help='Path or URL to the audio file')

    # Detection parameters
    parser.add_argument('-t', '--matching_threshold', type=float, default=2.5,
                        help='Matching threshold percentage (default: 2.5)')
    parser.add_argument('-r', '--time_resolution_ms', type=int, default=50,
                        help='Time resolution in ms (default: 50)')
    parser.add_argument('-a', '--tone_a_min_length', type=float, default=0.85,
                        help='Min length of tone A in seconds (default: 0.85)')
    parser.add_argument('-b', '--tone_b_min_length', type=float, default=2.6,
                        help='Min length of tone B in seconds (default: 2.6)')
    parser.add_argument('-i', '--hi_low_interval', type=float, default=0.2,
                        help='Max interval between hi-low tones in seconds (default: 0.2)')
    parser.add_argument('-n', '--hi_low_min_alternations', type=int, default=6,
                        help='Min number of hi-low alternations (default: 6)')
    parser.add_argument('-l', '--long_tone_min_length', type=float, default=3.8,
                        help='Min length of a long tone in seconds (default: 3.8)')

    # MDC and DTMF detection flags
    parser.add_argument('--detect_mdc', action='store_true', default=True,
                        help='Enable MDC/FleetSync detection (default: True)')
    parser.add_argument('--mdc_high_pass', type=int, default=200,
                        help='High-pass filter frequency for MDC (default: 200 Hz)')
    parser.add_argument('--mdc_low_pass', type=int, default=4000,
                        help='Low-pass filter frequency for MDC (default: 4000 Hz)')
    parser.add_argument('--detect_dtmf', action='store_true', default=True,
                        help='Enable DTMF detection (default: True)')

    # Debug
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Enable debug mode (prints additional info)')

    args = parser.parse_args()

    detect_result = tone_detect(
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
        debug=args.debug
    )

    # Construct a dictionary of all the detected tones
    data_dict = {
        "two_tone": detect_result.two_tone_result,
        "long_tone": detect_result.long_result,
        "hi_low": detect_result.hi_low_result,
        "mdc": detect_result.mdc_result,
        "dtmf": detect_result.dtmf_result
    }

    # Print the complete JSON result
    print(json.dumps(data_dict, indent=2))


if __name__ == '__main__':
    main()