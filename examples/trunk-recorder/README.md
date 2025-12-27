# Using icad_tone_detection with Trunk-Recorder

This example demonstrates how to integrate `icad_tone_detection` with
Trunk-Recorder using a filesystem watcher.

Some Trunk-Recorder installations do not support `callEndScript`, and
audio is written asynchronously under `tr-project/audio`. This approach
provides a safe, non-blocking way to run tone detection on completed WAV
files without modifying Trunk-Recorder or the ICAD library.

---

## Overview

The workflow is:

1. Trunk-Recorder writes WAV files to disk
2. A filesystem watcher monitors the audio directory
3. When a WAV file finishes writing, tone detection is triggered
4. Results are appended to a log file

This decouples tone detection from Trunk-Recorder internals and works
across restarts.

---

## Files

- `watch_wav_inotify.py`  
  Watches a Trunk-Recorder audio directory for newly written WAV files
  using inotify and launches tone detection.

- `tone_detect_call.py`  
  Runs `icad_tone_detection` on a single WAV file and appends results
  to a log file.

---

## Requirements

- Linux system with inotify support
- Python 3.10–3.12
- `ffmpeg` available in PATH
- Trunk-Recorder configured to write WAV files
- `icad_tone_detection` installed in a virtual environment

---

## Configuration

Before running, update the following placeholders in the scripts:

- `/path/to/tr-project/audio/site`  
  Root directory where Trunk-Recorder writes WAV files

- `/path/to/venv/bin/python`  
  Python interpreter inside the virtual environment

- `/path/to/tone_detect_call.py`  
  Path to the tone detection script

- `/path/to/tones.log`  
  Log file for detection results

You may also adjust the WAV filename regex to match your system’s
naming conventions.

---

## Notes

- This example is **not part of Trunk-Recorder**
- It does not require modifying Trunk-Recorder
- Assumes WAV files are written atomically
- `close_write` is used to detect recording completion
- Linux-only (uses inotify)

---

## Running

The watcher script can be run under `systemd`, `tmux`, or `screen`
depending on your environment.

This example is intended as a reference implementation and can be
extended to parse sidecar JSON metadata, map tones to stations, or
forward alerts to external systems.
