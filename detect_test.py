#!/usr/bin/env python3
import json
import sys
from icad_tone_detection import tone_detect

if len(sys.argv) > 1:
    audio_path = sys.argv[1]
else:
    print("Requires a audio path provided. Either file path, or URL.")
    exit(0)

two_tone, long_tone, hl_tone = tone_detect(audio_path)

data_dict = {"two_tone": two_tone, "long_tone": long_tone, "hl_tone": hl_tone}

print(json.dumps(data_dict))
