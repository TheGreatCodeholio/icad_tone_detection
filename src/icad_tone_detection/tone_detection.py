import json
import subprocess
import statistics
from typing import List, Optional, Tuple, Dict, Any
from collections import Counter, defaultdict

import numpy as np
from pydub import AudioSegment

def _close_to_any(f: float, pool: set[float], tol_hz: float) -> bool:
    return any(abs(f - p) <= tol_hz for p in pool)

def group_center(freq_group):
    """Return a robust center freq (median of non-zero samples) for a group tuple (s,e,len,freqs)."""
    freqs = [f for f in freq_group[3] if f > 0]
    return statistics.median(freqs) if freqs else 0.0

def group_is_stable(freq_group, bw_hz=25.0):
    """Ensure the group's instantaneous freq doesn't wander too much (reduces false matches)."""
    freqs = [f for f in freq_group[3] if f > 0]
    if len(freqs) < 2:
        return False
    med = statistics.median(freqs)
    return all(abs(f - med) <= bw_hz for f in freqs)

def separated_enough(f1, f2, min_separation_hz=40.0):
    """Two tones must be meaningfully distinct (not tiny drift of same tone)."""
    if f1 <= 0 or f2 <= 0:
        return False
    return abs(f1 - f2) >= min_separation_hz

def _robust_mode(vals: List[float], bin_size: float = 5.0) -> float:
    """Histogram-ish mode, robust to outliers."""
    from collections import Counter
    if not vals:
        return 0.0
    bins = Counter(int(v // bin_size) for v in vals)
    top_bin = max(bins.items(), key=lambda kv: kv[1])[0]
    in_bin = [v for v in vals if int(v // bin_size) == top_bin]
    return float(statistics.median(in_bin)) if in_bin else float(statistics.median(vals))

def within_tolerance(f1, f2, tolerance=0.02):
    if f1 is None or f2 is None:
        return False
    denom = max(1.0, max(abs(f1), abs(f2)))   # symmetric & avoids tiny denom
    return abs(f1 - f2) / denom <= tolerance

def detect_two_tone_tones(
        frequency_matches,
        min_tone_a_length=0.7,
        min_tone_b_length=2.7,
        max_gap_between_a_b=0.35,      # NEW: keep A→B contiguous-ish
        tone_bw_hz=25.0,               # NEW: intra-group stability band
        min_pair_separation_hz=40.0    # NEW: ensure A and B are truly different
):

    if min_tone_a_length <= 0:
        raise ValueError("min_tone_a_length must be > 0")
    if min_tone_b_length <= 0:
        raise ValueError("min_tone_b_length must be > 0")
    if max_gap_between_a_b < 0:
        raise ValueError("max_gap_between_a_b must be >= 0")
    if tone_bw_hz <= 0:
        raise ValueError("tone_bw_hz must be > 0")
    if min_pair_separation_hz <= 0:
        raise ValueError("min_pair_separation_hz must be > 0")

    two_tone_matches = []
    tone_id = 0
    last = None

    if not frequency_matches:
        return two_tone_matches

    for cur in frequency_matches:
        # Must be non-zero group and stable
        if not cur[3] or cur[3][0] <= 0 or not group_is_stable(cur, bw_hz=tone_bw_hz):
            continue

        cur_dur = cur[1] - cur[0]
        if last is None:
            # cache only if stable and non-zero
            last = cur if cur_dur >= min_tone_a_length else None
            continue

        # last must be stable, non-zero
        if not last[3] or last[3][0] <= 0 or not group_is_stable(last, bw_hz=tone_bw_hz):
            last = cur if cur_dur >= min_tone_a_length else None
            continue

        last_dur = last[1] - last[0]
        gap = max(0.0, cur[0] - last[1])
        fa = group_center(last)
        fb = group_center(cur)

        if (last_dur >= min_tone_a_length and
                cur_dur  >= min_tone_b_length and
                gap <= max_gap_between_a_b and
                separated_enough(fa, fb, min_pair_separation_hz)):

            tone_id += 1
            two_tone_matches.append({
                "tone_id": f'qc_{tone_id}',
                "detected": [round(fa,1), round(fb,1)],
                "tone_a_length": round(last[2], 3),
                "tone_b_length": round(cur[2], 3),
                "start": last[0],
                "end": cur[1]
            })
            # reset; avoid overlapping chains (optional)
            last = None
        else:
            # move window: current can become next A if long enough
            last = cur if cur_dur >= min_tone_a_length else None

    return two_tone_matches


def detect_long_tones(
        frequency_matches,
        min_duration: float = 3.1,
        tone_bw_hz: float = 25.0,
        min_freq_hz: float = 200.0,
):
    """
    Report stable, single-frequency long tones on the *already time-filtered* groups.
    """
    if min_duration <= 0:
        raise ValueError("min_duration must be > 0")
    if tone_bw_hz <= 0:
        raise ValueError("tone_bw_hz must be > 0")

    long_tone_matches = []
    for start, end, duration, freqs in frequency_matches:
        if not freqs:
            continue
        # robust center/stability using your helpers
        if not group_is_stable((start, end, duration, freqs), bw_hz=tone_bw_hz):
            continue
        center = group_center((start, end, duration, freqs))
        if center <= min_freq_hz:
            continue
        if duration >= min_duration:
            long_tone_matches.append({
                "tone_id": f"lt_{len(long_tone_matches) + 1}",
                "detected": round(center, 1),
                "start": start,
                "end": end,
                "length": duration,
            })

    return long_tone_matches

def detect_pulsed_single_tone(
        frequency_matches: List[Tuple[float, float, float, List[float]]],
        *,
        bw_hz: float = 25.0,               # ±Hz counted as ON around the inferred center
        min_cycles: int = 6,               # required ON→OFF repetitions
        min_on_ms: int = 120,              # ON duration bounds (ms)
        max_on_ms: int = 900,
        min_off_ms: int = 25,              # OFF duration bounds (ms)
        max_off_ms: int = 350,
        time_resolution_ms: int = 50,      # must match your STFT hop
        auto_center_band: Tuple[float, float] = (200.0, 3000.0),  # where to search for center
        mode_bin_hz: float = 5.0           # histogram bin for robust mode
) -> List[Dict[str, Any]]:
    """
    Detect pulsed single-tone patterns like ON/OFF/ON/OFF around an inferred center frequency.

    Returns list of dicts shaped like other detectors:
      {
        "tone_id": "pl_1",
        "detected": 1010.1,   # inferred center (Hz)
        "start": 2.31,
        "end": 5.12,
        "length": 2.81,
        "cycles": 8,
        "on_ms_median": 180,
        "off_ms_median": 95
      }
    """
    if bw_hz <= 0:
        raise ValueError("bw_hz must be > 0")
    if mode_bin_hz <= 0:
        raise ValueError("mode_bin_hz must be > 0")
    if min_on_ms > max_on_ms:
        raise ValueError("min_on_ms must be <= max_on_ms")
    if min_off_ms > max_off_ms:
        raise ValueError("min_off_ms must be <= max_off_ms")
    lo, hi = auto_center_band
    if not (lo < hi):
        raise ValueError("auto_center_band must be (low < high)")

    if not frequency_matches:
        return []

    # ---- Build fixed-step timeline (t, f_center_per_group) ----
    step = time_resolution_ms / 1000.0
    timeline: List[Tuple[float, float]] = []
    for start, end, dur, freqs in frequency_matches:
        # center per group; 0 if OFF/noisy
        nz = [f for f in freqs if lo <= f <= hi]
        f = float(statistics.median(nz)) if len(nz) else 0.0
        t = start
        while t < end - 1e-12:
            timeline.append((round(t, 3), f))
            t += step
    if not timeline:
        return []

    # ---- Auto-estimate center from "pulse-like" ON groups first (weighted by duration) ----
    on_min_s = min_on_ms / 1000.0
    on_max_s = max_on_ms / 1000.0
    weighted_bins = defaultdict(float)

    def stable_med(freqs: List[float], med: float) -> bool:
        return all(abs(f - med) <= bw_hz for f in freqs if f > 0)

    for (gs, ge, gd, freqs) in frequency_matches:
        if gd < on_min_s or gd > on_max_s:
            continue
        nz = [f for f in freqs if lo <= f <= hi]
        if len(nz) < 2:
            continue
        med = statistics.median(nz)
        if stable_med(nz, med):
            weighted_bins[int(med // mode_bin_hz)] += gd

    if weighted_bins:
        top_bin = max(weighted_bins.items(), key=lambda kv: kv[1])[0]
        center_candidates = []
        for (gs, ge, gd, freqs) in frequency_matches:
            nz = [f for f in freqs if lo <= f <= hi]
            if not nz:
                continue
            med = statistics.median(nz)
            if int(med // mode_bin_hz) == top_bin:
                center_candidates.append(med)
        center_hz = float(np.median(center_candidates))
    else:
        # Fallback: use modal bin from all timeline frames within band
        vals = [f for (_t, f) in timeline if lo <= f <= hi]
        if not vals:
            return []
        b = Counter(int(v // mode_bin_hz) for v in vals)
        top = max(b.items(), key=lambda kv: kv[1])[0]
        center_hz = float(np.median([v for v in vals if int(v // mode_bin_hz) == top]))

    def in_band(f: float) -> bool:
        return (f > 0.0) and (abs(f - center_hz) <= bw_hz)

    # ---- Build ON/OFF runs ----
    runs: List[Tuple[str, float, float]] = []
    cur_state: Optional[str] = None
    cur_start: Optional[float] = None

    for (t, f) in timeline:
        st = "on" if in_band(f) else "off"
        if cur_state is None:
            cur_state, cur_start = st, t
        elif st != cur_state:
            runs.append((cur_state, cur_start, t))
            cur_state, cur_start = st, t
    if cur_state is not None and cur_start is not None:
        runs.append((cur_state, cur_start, timeline[-1][0] + step))

    if len(runs) < 2:
        return []

    # ---- Scan for alternating cycles within cadence bounds ----
    hits: List[Dict[str, Any]] = []
    i, pl_id = 0, 1

    while i + 1 < len(runs):
        if runs[i][0] != "on":
            i += 1
            continue

        j = i
        cycles = 0
        on_ms_list: List[int] = []
        off_ms_list: List[int] = []

        while j + 1 < len(runs):
            on_run = runs[j]
            if on_run[0] != "on":
                break

            on_len_ms = int(round((on_run[2] - on_run[1]) * 1000))
            if not (min_on_ms <= on_len_ms <= max_on_ms):
                break
            on_ms_list.append(on_len_ms)

            if j + 1 >= len(runs):
                j += 1
                break

            off_run = runs[j + 1]
            if off_run[0] != "off":
                break

            off_len_ms = int(round((off_run[2] - off_run[1]) * 1000))
            if not (min_off_ms <= off_len_ms <= max_off_ms):
                j += 1
                break

            off_ms_list.append(off_len_ms)
            cycles += 1
            j += 2

        if cycles >= min_cycles:
            end_idx = max(i, j - 1) if j - 1 < len(runs) else i
            s = round(runs[i][1], 2)
            e = round(runs[end_idx][2], 2)
            hits.append({
                "tone_id": f"pl_{pl_id}",
                "detected": round(center_hz, 1),
                "start": s,
                "end": e,
                "length": round(e - s, 2),
                "cycles": cycles,
                "on_ms_median": int(np.median(on_ms_list)) if on_ms_list else 0,
                "off_ms_median": int(np.median(off_ms_list)) if off_ms_list else 0,
            })
            pl_id += 1
            i = max(j, i + 1)
        else:
            i += 1

    return hits

def detect_warble_tones(
        frequency_matches,
        interval_length,
        min_alternations,
        tone_bw_hz=25.0,
        min_pair_separation_hz=40.0
):
    if interval_length < 0: raise ValueError("interval_length must be >= 0")
    if min_alternations < 2: raise ValueError("min_alternations must be >= 2")
    if tone_bw_hz <= 0: raise ValueError("tone_bw_hz must be > 0")
    if min_pair_separation_hz <= 0: raise ValueError("min_pair_separation_hz must be > 0")
    if not frequency_matches: return []

    def close(a, b, tol): return abs(a - b) <= tol
    sequences, id_index = [], 1
    i = 0

    while i < len(frequency_matches):
        current_sequence = []
        current_tones = []  # the two tones we allow, stored as floats (not rounded)
        i0 = i

        while i < len(frequency_matches):
            g = frequency_matches[i]; i += 1
            # needs non-zero, ≥2 samples, stable
            if not g[3] or g[3][0] <= 0 or len(g[3]) < 2: break
            if not group_is_stable(g, bw_hz=tone_bw_hz): break

            f = group_center(g)  # keep raw center; round only for reporting
            if not current_sequence:
                current_sequence.append(g)
                current_tones = [f]
                continue

            last = current_sequence[-1]
            gap_ok = (g[0] - last[1]) <= (interval_length + 1e-6)
            if not gap_ok: break

            f_last = group_center(last)
            # Need alternation: reject repeats within tolerance
            if close(f, f_last, tone_bw_hz):
                break

            # Add second tone if we only have one so far
            if len(current_tones) < 2:
                if separated_enough(current_tones[0], f, min_pair_separation_hz):
                    current_tones.append(f)
                else:
                    break

            # From now on, f must be close to one of the two tones
            if not any(close(f, ct, tone_bw_hz) for ct in current_tones):
                break

            current_sequence.append(g)

        # Validate
        if len(current_sequence) >= min_alternations and len(current_tones) == 2:
            # canonicalize the two tones using medians of their occurrences
            lows, highs = [], []
            a, b = current_tones
            for gs, ge, gd, freqs in current_sequence:
                fc = group_center((gs, ge, gd, freqs))
                (lows if abs(fc - a) < abs(fc - b) else highs).append(fc)
            det = sorted([statistics.median(lows) if lows else a,
                          statistics.median(highs) if highs else b])

            sequences.append({
                "tone_id": f"hl_{id_index}",
                "detected": [round(det[0], 1), round(det[1], 1)],
                "start": current_sequence[0][0],
                "end":   current_sequence[-1][1],
                "length": round(current_sequence[-1][1] - current_sequence[0][0], 2),
                "alternations": len(current_sequence),
            })
            id_index += 1

    return sequences

def detect_mdc_tones(
        segment: AudioSegment,
        binary_path: str = "icad_decode",
        highpass_freq: int = 200,
        lowpass_freq: int = 4000,
) -> list[str]:
    """
    Decode MDC1200 (or Fleetsync) frames from a PyDub AudioSegment by piping raw audio to an external 'icad_decode' binary.

    :param segment:             A PyDub AudioSegment containing audio to decode.
    :param binary_path:          Path to the 'icad_decode' executable (default: 'icad_decode').
    :param highpass_freq:       Frequency in Hz for highpass filter (default: 200).
    :param lowpass_freq:        Frequency in Hz for lowpass filter (default: 4000).

    :return: mdc_matches list of dicts each dict representing a detected sequence of MDC1200 (or Fleetsync) frames.

    :raises FileNotFoundError:  If binary_path is not found on the system.
    :raises ValueError:         If the audio segment is empty or too short to process.
    :raises RuntimeError:       If 'icad_decode' fails to run properly or returns a nonzero exit code.
    """

    if highpass_freq < 0 or lowpass_freq < 0:
        raise ValueError("highpass_freq and lowpass_freq must be >= 0")
    if 0 < lowpass_freq <= highpass_freq:
        raise ValueError("lowpass_freq must be > highpass_freq (or set either to 0 to disable)")
    if not isinstance(binary_path, str) or not binary_path:
        raise ValueError("binary_path must be a non-empty string")

    mdc_matches = []


    # Check if the AudioSegment is non-empty
    if len(segment) == 0:
        raise ValueError("The provided AudioSegment is empty (0 ms). Nothing to decode.")

    # ----------------------------------------------------------------
    # 1) Resample, convert to mono, apply filters
    # ----------------------------------------------------------------

    # Apply high-pass and low-pass filters in PyDub
    # (Not identical to SoX, but usually good enough for typical use)
    if highpass_freq > 0:
        segment = segment.high_pass_filter(highpass_freq)
    if lowpass_freq > 0:
        segment = segment.low_pass_filter(lowpass_freq)

    # ----------------------------------------------------------------
    # 2) Convert from signed 8-bit -> unsigned 8-bit if needed
    # ----------------------------------------------------------------
    # If your decoder expects samples in the range 0..255 (unsigned), we must shift
    # the PyDub data (which is -128..+127 for 8-bit signed).
    raw_data = segment.raw_data
    #raw_data = bytes((s + 128) & 0xFF for s in raw_data)

    # ----------------------------------------------------------------
    # 3) Pipe the raw audio bytes into 'icad_decode' via subprocess
    # ----------------------------------------------------------------
    cmd = [binary_path, "-m", "mdc", "-"]  # '-' indicates reading from STDIN
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    except OSError as e:
        # Catch other OS-level errors (permissions, etc.)
        raise RuntimeError(f"Failed to execute '{binary_path}': {e}") from e

    # Send raw audio to icad_decode
    out, err = proc.communicate(input=raw_data)

    # Check return code
    if proc.returncode != 0:
        raise RuntimeError(
            f"'icad_decode' process exited with code {proc.returncode}.\n"
            f"stderr:\n{err.decode('utf-8', errors='replace')}"
        )

    # ----------------------------------------------------------------
    # 4) Process the icad_decode output
    # ----------------------------------------------------------------
    binary_stdout = out.decode("utf-8", errors="replace")
    lines = binary_stdout.strip().splitlines()

    for line in lines:
        print(line)
        try:
            obj = json.loads(line)
            mdc_matches.append(obj)
        except json.JSONDecodeError:
            pass

    return mdc_matches

def detect_dtmf_tones(
        segment: AudioSegment,
        binary_path: str = "icad_decode",
        highpass_freq: int = 0,
        lowpass_freq: int = 0,
        min_ms: int = 400,
        merge_ms: int = 75,
        start_offset_ms: int = -20,
        end_offset_ms: int = 20,
) -> list[str]:
    """
    Decode DTMF tones by piping raw audio to an external 'icad_decode' binary.

    :param segment: PyDub AudioSegment (16-bit, 16 kHz, mono recommended).
    :param binary_path: Path to the 'icad_decode' executable (default 'icad_decode').
    :param highpass_freq: Frequency (Hz) for high-pass filter. 0 or None to skip.
    :param lowpass_freq: Frequency (Hz) for low-pass filter. 0 or None to skip.
    :param min_ms: Minimum key press length (ms).
    :param merge_ms: Same-digit debounce/merge gap (ms).
    :param start_offset_ms: Presentation start offset (ms) applied by decoder.
    :param end_offset_ms: Presentation end offset (ms) applied by decoder.

    :return: dtmf_matches list of dicts, each representing a detected DTMF key press.
    :raises RuntimeError: if the decode process fails or returns non-zero.
    :raises ValueError: if the segment is empty.
    """

    if highpass_freq < 0 or lowpass_freq < 0:
        raise ValueError("highpass_freq and lowpass_freq must be >= 0")
    if 0 < lowpass_freq <= highpass_freq:
        raise ValueError("lowpass_freq must be > highpass_freq (or set either to 0 to disable)")
    if not isinstance(binary_path, str) or not binary_path:
        raise ValueError("binary_path must be a non-empty string")

    dtmf_matches = []

    # Check if the AudioSegment is non-empty
    if len(segment) == 0:
        raise ValueError("The provided AudioSegment is empty (0 ms). Nothing to decode.")

    # Apply High Pass Filter
    if highpass_freq and highpass_freq > 0:
        segment = segment.high_pass_filter(highpass_freq)

    # Apply Low Pass Filter
    if lowpass_freq and lowpass_freq > 0:
        segment = segment.low_pass_filter(lowpass_freq)

    raw_data = segment.raw_data

    # ----------------------------------------------------------------
    # 2) Pipe the raw audio bytes into 'icad_decode' via subprocess
    # ----------------------------------------------------------------
    cmd = [
        binary_path, "-m", "dtmf", "-",
        "--dtmf-min-ms", str(int(min_ms)),
        "--dtmf-merge-ms", str(int(merge_ms)),
        "--dtmf-start-offset-ms", str(int(start_offset_ms)),
        "--dtmf-end-offset-ms", str(int(end_offset_ms)),
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    except OSError as e:
        # Catch other OS-level errors (permissions, etc.)
        raise RuntimeError(f"Failed to execute '{binary_path}': {e}") from e

    # Send raw audio to icad_decode
    out, err = proc.communicate(input=raw_data)

    # Check return code
    if proc.returncode != 0:
        raise RuntimeError(
            f"'icad_decode' process exited with code {proc.returncode}.\n"
            f"stderr:\n{err.decode('utf-8', errors='replace')}"
        )

    # ----------------------------------------------------------------
    # 3) Process the icad_decode output
    # ----------------------------------------------------------------
    binary_stdout = out.decode("utf-8", errors="replace")
    lines = binary_stdout.strip().splitlines()

    for line in lines:
        try:
            obj = json.loads(line)
            dtmf_matches.append(obj)
        except json.JSONDecodeError:
            pass

    return dtmf_matches
