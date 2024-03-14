#!/usr/bin/env python3
import json
import sys
from icad_tone_detection import tone_detect

if len(sys.argv) > 1:
    audio_path = sys.argv[1]
else:
    print("Requires a audio path provided. Either file path, or URL.")
    exit(0)

detect_result = tone_detect(audio_path)

data_dict = {"two_tone": detect_result.two_tone_result, "long_tone": detect_result.long_result, "hl_tone": detect_result.hl_tone_result}

print(json.dumps(data_dict))
