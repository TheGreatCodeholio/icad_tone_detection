#!/usr/bin/env python3
import sys
from datetime import datetime
from icad_tone_detection import tone_detect

LOG_FILE = "/path/to/tones.log
wav_path = sys.argv[1]
talkgroup = sys.argv[2] if len(sys.argv) > 2 else "scanner"

result = tone_detect(
    wav_path,
    detect_mdc=False,
    detect_dtmf=False,

    # Tuned for your system
    fe_freq_band=(300, 2000),
    fe_silence_below_global_db=-34,
    fe_snr_above_noise_db=3,

    tone_a_min_length=0.6,
    tone_b_min_length=2.0,
    two_tone_bw_hz=20,
    two_tone_min_pair_separation_hz=35,

    debug=False
)

ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

lines = []

for t in result.two_tone_result:
    a, b = t["detected"]
    lines.append(
        f"{ts} | TG {talkgroup} | TWO-TONE | "
        f"A={a:.1f}Hz ({t['tone_a_length']:.2f}s) "
        f"B={b:.1f}Hz ({t['tone_b_length']:.2f}s)"
    )

if not lines:
    lines.append(f"{ts} | TG {talkgroup} | NO_TONES")

with open(LOG_FILE, "a") as f:
    for line in lines:
        f.write(line + "\n")
