#!/usr/bin/env python3
import subprocess
import time
import re
from pathlib import Path

WATCH_DIR = Path("/path/to/trunkrecorder/audio/pscsite4")
LOG_FILE = "/path/to/icad/tones.log"
PYTHON = "/path/to/venv/bin/python"
DETECT_SCRIPT = "/path/to/icad/tone_detect_call.py"

# Only match these WAVs
WAV_RE = re.compile(r".*\.wav$")

def process_wav(wav_path: Path):
    # Extract talkgroup from filename if needed later
    # You can also parse JSON if desired
    print(f"[icad] Processing {wav_path}")

    subprocess.Popen(
        [PYTHON, DETECT_SCRIPT, str(wav_path), "scanner"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
"""
Watches for completed WAV files using inotify.

Assumptions:
- Trunk-Recorder writes WAV files atomically
- The close_write event indicates recording completion
- Linux system with inotify support
"""

def main():
    print("[icad] Watching for new WAV files...")

    proc = subprocess.Popen(
        [
            "inotifywait",
            "-m",
            "-r",
            "-e", "close_write",
            "--format", "%f",
            str(WATCH_DIR),
        ],
        stdout=subprocess.PIPE,
        text=True,
    )

    for line in proc.stdout:
        filename = line.strip()
        if WAV_RE.match(filename):
            full_path = next(WATCH_DIR.rglob(filename), None)
            if full_path:
                process_wav(full_path)

if __name__ == "__main__":
    main()
