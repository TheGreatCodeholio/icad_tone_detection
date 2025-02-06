#!/usr/bin/env python3
import argparse
import json
from icad_tone_detection import tone_detect


def main():
    parser = argparse.ArgumentParser(description='Run tone detection on an audio file.')
    parser.add_argument('-p', '--audio_path', type=str, help='Path to the audio file')
    parser.add_argument('-t', '--matching_threshold', type=float, default=2.5, help='Matching threshold percentage')
    parser.add_argument('-r', '--time_resolution_ms', type=int, default=25, help='Time resolution in ms')
    parser.add_argument('-a', '--tone_a_min_length', type=float, default=0.7, help='Min length of tone A in seconds')
    parser.add_argument('-b', '--tone_b_min_length', type=float, default=2.7, help='Min length of tone B in seconds')
    parser.add_argument('-i', '--hi_low_interval', type=float, default=0.2,
                        help='Max interval between hi-low tones in seconds')
    parser.add_argument('-n', '--hi_low_min_alternations', type=int, default=6,
                        help='Min number of hi-low alternations')
    parser.add_argument('-l', '--long_tone_min_length', type=float, default=3.8,
                        help='Min length of a long tone in seconds')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode')

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
        debug=args.debug
    )

    data_dict = {"two_tone": detect_result.two_tone_result, "long_tone": detect_result.long_result,
                 "hl_tone": detect_result.hi_low_result}

    print(json.dumps(data_dict))


if __name__ == '__main__':
    main()
