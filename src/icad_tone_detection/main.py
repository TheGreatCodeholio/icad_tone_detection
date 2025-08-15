import platform
import shutil
import stat
from importlib import resources
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple

import requests

from .audio_loader import load_audio
from .exceptions import AudioLoadError, FrequencyExtractionError, ToneDetectionError, FFmpegNotFoundError
from .frequency_extraction import FrequencyExtraction
from .tone_detection import (
    detect_long_tones,
    detect_warble_tones,
    detect_mdc_tones,
    detect_dtmf_tones,
    detect_pulsed_single_tone, detect_two_tone_tones,
)

__version__ = "2.8.4"


@dataclass
class ToneDetectionResult:
    two_tone_result: List[Dict]
    long_result: List[Dict]
    hi_low_result: List[Dict]
    pulsed_result: List[Dict]
    mdc_result: List[Dict]
    dtmf_result: List[Dict]



def _path_to_bin(folder: str, binary: str = "icad_decode"):
    return resources.files("icad_tone_detection").joinpath(f"bin/{folder}/{binary}")

def choose_decode_binary() -> str:
    system = platform.system().lower()
    arch   = platform.machine().lower()

    if system == "linux":
        if arch in ("x86_64", "amd64"):
            folder, binary = "linux_x86_64", "icad_decode"
        elif arch in ("aarch64", "arm64"):
            folder, binary = "linux_arm64", "icad_decode"
        elif arch.startswith("armv7"):
            folder, binary = "linux_armv7", "icad_decode"
        else:
            raise RuntimeError(f"Unsupported Linux architecture: {arch}")
        resource = _path_to_bin(folder, binary)

    elif system == "darwin":
        folder = "macos_arm64" if arch == "arm64" else "macos_x86_64"
        resource = _path_to_bin(folder, "icad_decode")

    elif system == "windows":
        if arch not in ("amd64", "x86_64"):
            raise RuntimeError(f"Unsupported Windows architecture: {arch}")
        resource = _path_to_bin("windows_x86_64", "icad_decode.exe")

    else:
        raise RuntimeError(f"Unsupported platform: {system}/{arch}")

    # Convert to string path for downstream code
    path_str = str(resource)

    if system != "windows":
        try:
            p = Path(path_str)
            p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except (FileNotFoundError, OSError):
            pass

    return path_str


def _outside_intervals(group, intervals: List[Tuple[float, float]]) -> bool:
    """Return True if (group_start, group_end) does NOT overlap any interval."""
    gs, ge = float(group[0]), float(group[1])
    for (s, e) in intervals:
        if not (ge <= s or gs >= e):
            return False
    return True

def _overlaps(a, b, guard=0.0):
    (s1,e1),(s2,e2) = a,b
    return not (e1 + guard <= s2 or e2 + guard <= s1)

def _intervals_from_hits(hits):
    # generic: uses start/end keys
    return [(h["start"], h["end"]) for h in hits]

def _qc_windows_from_hits(qc_hits, which="both", guard=0.0):
    # build AB windows specifically (so we can drop only B if desired)
    wins = []
    for h in qc_hits:
        s, e = float(h["start"]), float(h["end"])
        la, lb = float(h["tone_a_length"]), float(h["tone_b_length"])
        a_win = (s, s + la)
        b_win = (e - lb, e)
        if which in ("both","A"): wins.append(a_win)
        if which in ("both","B"):  wins.append(b_win)
    # optional: expand slightly
    return [(max(0.0, s-guard), e+guard) for (s,e) in wins]

def _filter_groups_outside(groups, windows, guard=0.0):
    if not windows: return groups
    outs = []
    for g in groups:
        win = (g[0], g[1])
        if any(_overlaps(win, w, guard) for w in windows):
            continue
        outs.append(g)
    return outs

def tone_detect(
        audio_path,
        matching_threshold=2.5,
        time_resolution_ms=50,

        # --- FrequencyExtraction knobs ---
        fe_freq_band: Tuple[float, float] = (200.0, 3000.0),
        fe_merge_short_gaps_ms: int = 0,
        fe_silence_below_global_db: float = -28.0,
        fe_snr_above_noise_db: float = 6.0,
        fe_abs_cap_hz: float = 15.0,
        fe_force_split_step_hz: float = 12.0,
        fe_split_lookahead_frames: int = 1,

        # --- Quick Call (two-tone A/B) ---
        tone_a_min_length=0.85,
        tone_b_min_length=2.6,
        two_tone_max_gap_between_a_b=0.35,
        two_tone_bw_hz=25.0,
        two_tone_min_pair_separation_hz=40.0,

        # --- Hi/Low (warble) ---
        hi_low_interval=0.2,
        hi_low_min_alternations=6,
        hi_low_tone_bw_hz=25.0,
        hi_low_min_pair_separation_hz=40.0,

        # --- Long tone ---
        long_tone_min_length=3.8,
        long_tone_bw_hz=25.0,

        # --- Pulsed single tone ---
        pulsed_bw_hz=25.0,
        pulsed_min_cycles=6,
        pulsed_min_on_ms=120,
        pulsed_max_on_ms=900,
        pulsed_min_off_ms=25,
        pulsed_max_off_ms=350,
        pulsed_auto_center_band: Tuple[float, float] = (200.0, 3000.0),
        pulsed_mode_bin_hz: float = 5.0,

        # --- Enable/disable detectors ---
        detect_pulsed=True,
        detect_two_tone=True,
        detect_long=True,
        detect_hi_low=True,

        # --- External decoders ---
        detect_mdc=True,
        mdc_high_pass=200,
        mdc_low_pass=4000,
        detect_dtmf=True,

        debug=False,
):
    """
    Detect paging-style tones in an audio file (local path, URL, or in-memory).

    This function runs a Short-Time Fourier Transform (STFT) frontend to extract per-frame
    dominant frequencies, then applies several pattern recognizers:

      • Pulsed single tone (ON/OFF/ON around an inferred center)
      • Two-tone “Quick Call” A→B (A is short, B is longer)
      • Long single tone
      • Hi–Low warble (alternating two distinct tones)
      • Optional external decoders: MDC1200/FleetSync, DTMF

    The pulsed detector (if enabled) runs first and masks its time windows so the other
    detectors don’t double-count the same energy.

    Parameters
    ----------
    audio_path : str | bytes | io.BytesIO | pydub.AudioSegment
        Path/URL/bytes-like object for audio readable by FFmpeg. Multi-channel audio is mixed to mono.

    matching_threshold : float, default 2.5
        Percentage tolerance used when grouping adjacent STFT frames into a continuous frequency group.
        Higher allows more drift before a new group is started.

    time_resolution_ms : int, default 50
        Hop size (and effective time resolution) of the STFT, in milliseconds. Smaller → finer time
        resolution but potentially noisier frequency estimates.

    # ----- Frequency-extraction (frontend) knobs -----
    fe_freq_band : (float, float), default (200.0, 3000.0)
        [Hz] Band to search for dominant peaks. Frames outside are ignored for peak-picking.

    fe_merge_short_gaps_ms : int, default 0
        Merge adjacent groups separated by ≤ this gap (ms). Helps when a single missing frame
        would otherwise split one logical tone into two groups.

    fe_silence_below_global_db : float, default -28.0
        A frame is considered OFF if its peak is this many dB below the file’s global peak.

    fe_snr_above_noise_db : float, default 6.0
        Additionally require the frame to be at least this many dB above a simple noise-floor estimate.

    fe_abs_cap_hz : float or None, default None
        Absolute cap on the dynamic, percent-based grouping tolerance (per-frame) in Hz. Prevents the
        allowed drift from becoming too large at high frequencies. If None, an internal default
        (≈30 Hz) is used.

    fe_force_split_step_hz : float or None, default None
        If the absolute step change between adjacent detected frames exceeds this threshold (Hz),
        force a group boundary even if the dynamic tolerance would have merged them. Useful to
        stop slowly-sliding tones from being lumped into one group. If None, disabled.

    fe_split_lookahead_frames : int, default 0
        When deciding a force-split based on `fe_force_split_step_hz`, look ahead up to N future frames
        to confirm the change. Helps avoid over-splitting caused by a single spurious frame.

    # ----- Two-tone (Quick Call) -----
    tone_a_min_length : float, default 0.85
        Minimum duration (seconds) of the A tone.

    tone_b_min_length : float, default 2.6
        Minimum duration (seconds) of the B tone.

    two_tone_max_gap_between_a_b : float, default 0.35
        Maximum allowed gap (seconds) between the end of A and start of B.

    two_tone_bw_hz : float, default 25.0
        [Hz] Intra-group stability band used to accept A/B groups.

    two_tone_min_pair_separation_hz : float, default 40.0
        [Hz] Minimum frequency separation between A and B to consider them distinct.

    # ----- Hi/Low warble -----
    hi_low_interval : float, default 0.2
        Maximum allowed gap (seconds) between alternating hi/low groups when assembling a sequence.

    hi_low_min_alternations : int, default 6
        Minimum number of alternating groups (hi,low,hi,low, …) to report a warble.

    hi_low_tone_bw_hz : float, default 25.0
        [Hz] Intra-group stability band used to accept warble groups.

    hi_low_min_pair_separation_hz : float, default 40.0
        [Hz] Minimum separation between the two alternating tones.

    # ----- Long tone -----
    long_tone_min_length : float, default 3.8
        Minimum duration (seconds) of a stable, single-frequency long tone.

    long_tone_bw_hz : float, default 25.0
        [Hz] Intra-group stability band used to accept long-tone groups.

    # ----- Pulsed single tone (auto-centered) -----
    pulsed_bw_hz : float, default 25.0
        [Hz] Allowed deviation around the inferred center for a frame to count as ON.

    pulsed_min_cycles : int, default 6
        Minimum number of ON→OFF repetitions required to report a hit.

    pulsed_min_on_ms : int, default 120
    pulsed_max_on_ms : int, default 900
        Bounds (milliseconds) for each ON pulse duration.

    pulsed_min_off_ms : int, default 25
    pulsed_max_off_ms : int, default 350
        Bounds (milliseconds) for the OFF gaps between pulses.

    pulsed_auto_center_band : (float, float), default (200.0, 3000.0)
        [Hz] Frequency band to search when auto-estimating the pulsed tone’s center.

    pulsed_mode_bin_hz : float, default 5.0
        [Hz] Histogram bin width used in robust mode selection for the auto-centered frequency.

    # ----- Enable/disable detectors -----
    detect_pulsed : bool, default True
        Enable/disable pulsed single-tone detection.

    detect_two_tone : bool, default True
        Enable/disable two-tone (Quick Call) detection.

    detect_long : bool, default True
        Enable/disable long tone detection.

    detect_hi_low : bool, default True
        Enable/disable hi–low warble detection.

    # ----- External decoders -----
    detect_mdc : bool, default True
        Enable/disable MDC1200/FleetSync decoder (external binary).

    mdc_high_pass : int, default 200
    mdc_low_pass  : int, default 4000
        [Hz] Optional prefilters applied before MDC/FleetSync decode.

    detect_dtmf : bool, default True
        Enable/disable DTMF decoder (external binary).

    debug : bool, default False
        If True, print a detailed dump of grouped frequencies and a summary of detections.

    Returns
    -------
    ToneDetectionResult
        Dataclass with fields:
          • pulsed_result : list[dict]
          • two_tone_result : list[dict]
          • long_result : list[dict]
          • hi_low_result : list[dict]
          • mdc_result : list[dict]
          • dtmf_result : list[dict]

    Raises
    ------
    FFmpegNotFoundError
        FFmpeg is missing from PATH.
    AudioLoadError
        The audio cannot be loaded or decoded.
    FrequencyExtractionError
        STFT processing or grouping failed.
    ToneDetectionError
        External decoders (MDC/DTMF) failed.

    Notes
    -----
    • For best results, use sample rates ≥ 16 kHz and avoid heavy compression.
    • `time_resolution_ms` should be compatible with the shortest cadence you want to detect
      (very short pulses often benefit from 25 ms).
    • The pulsed detector auto-centers within `pulsed_auto_center_band`; no fixed center is required.
    """


    if shutil.which("ffmpeg") is None:
        raise FFmpegNotFoundError(
            "FFmpeg is not installed or not found in system PATH. Please install FFmpeg to use this module."
        )
    icad_decode_path = choose_decode_binary()

    # ---- Load audio ----
    try:
        audio_segment, samples, frame_rate, duration_seconds = load_audio(audio_path)
    except ValueError as ve:
        raise AudioLoadError(f"Invalid input: {ve}") from ve
    except FileNotFoundError as fe:
        raise AudioLoadError(f"File not found: {fe}") from fe
    except requests.RequestException as re:
        raise AudioLoadError(f"HTTP error: {re}") from re
    except RuntimeError as ffmpeg_error:
        raise AudioLoadError(f"FFmpeg failed: {ffmpeg_error}") from ffmpeg_error
    except Exception as e:
        raise AudioLoadError(f"Unknown error: {type(e).__name__}: {e}") from e

    # ---- Extract per-frame dominant frequencies ----
    try:
        matched_frequencies = FrequencyExtraction(
            samples, frame_rate, duration_seconds,
            matching_threshold, time_resolution_ms,
            fe_freq_band=fe_freq_band,
            fe_merge_short_gaps_ms=fe_merge_short_gaps_ms,
            fe_silence_below_global_db=fe_silence_below_global_db,
            fe_snr_above_noise_db=fe_snr_above_noise_db,
            fe_abs_cap_hz=fe_abs_cap_hz,
            fe_force_split_step_hz=fe_force_split_step_hz,
            fe_split_lookahead_frames=fe_split_lookahead_frames,
        ).get_audio_frequencies()
    except Exception as e:
        raise FrequencyExtractionError(f"Frequency extraction failed on {audio_path}: {e}") from e

    # ---- Debug dump of matched groups ----
    if debug:
        if matched_frequencies:
            freq_lines = []
            for idx, (start, end, length, freq_list) in enumerate(matched_frequencies, start=1):
                freq_str = ", ".join(str(freq) for freq in freq_list)
                freq_lines.append(
                    f"  {idx:2d}) Start={start:.2f}s | End={end:.2f}s | Dur={length:.2f}s\n"
                    f"       Freqs: [{freq_str}]"
                )
            freq_summary = "\n".join(freq_lines)
        else:
            freq_summary = "  None"

        debug_info = f"""
############################################################
ICAD Tone Detection: DEBUG - v{__version__}
------------------------------------------------------------
Decode binary path:        {icad_decode_path}
Analyzing audio at:        {audio_path}

Matching Threshold:        {matching_threshold}%
Time Resolution (ms):      {time_resolution_ms}

[ Frequency Extraction (frontend) ]
  Band (Hz):               {fe_freq_band[0]}..{fe_freq_band[1]}
  Merge short gaps (ms):   {fe_merge_short_gaps_ms}
  Silence < global (dB):   {fe_silence_below_global_db}
  SNR above noise (dB):    {fe_snr_above_noise_db}
  Abs cap (Hz):            {fe_abs_cap_hz}
  Force-split step (Hz):   {fe_force_split_step_hz}
  Split lookahead (frames):{fe_split_lookahead_frames}

[ Two-Tone (Quick Call) ]
  Tone A min len (s):      {tone_a_min_length}
  Tone B min len (s):      {tone_b_min_length}
  A→B max gap (s):         {two_tone_max_gap_between_a_b}
  Tone BW (Hz):            {two_tone_bw_hz}
  Min A/B sep (Hz):        {two_tone_min_pair_separation_hz}
  Enabled:                 {detect_two_tone}

[ Long Tone ]
  Min length (s):          {long_tone_min_length}
  Tone BW (Hz):            {long_tone_bw_hz}
  Enabled:                 {detect_long}

[ Hi–Low Warble ]
  Interval (s):            {hi_low_interval}
  Min alternations:        {hi_low_min_alternations}
  Tone BW (Hz):            {hi_low_tone_bw_hz}
  Min pair sep (Hz):       {hi_low_min_pair_separation_hz}
  Enabled:                 {detect_hi_low}

[ Pulsed Single Tone ]
  Tone BW (Hz):            {pulsed_bw_hz}
  Min cycles:              {pulsed_min_cycles}
  ON range (ms):           {pulsed_min_on_ms}..{pulsed_max_on_ms}
  OFF range (ms):          {pulsed_min_off_ms}..{pulsed_max_off_ms}
  Auto-center band (Hz):   {pulsed_auto_center_band[0]}..{pulsed_auto_center_band[1]}
  Mode bin (Hz):           {pulsed_mode_bin_hz}
  Enabled:                 {detect_pulsed}

[ External Decoders ]
  MDC/FleetSync enabled:   {detect_mdc}
    High pass (Hz):        {mdc_high_pass}
    Low  pass (Hz):        {mdc_low_pass}
  DTMF enabled:            {detect_dtmf}

Total Duration (s):        {duration_seconds:.2f}
Sample Rate (Hz):          {frame_rate}
Guard (s):                 {0.5 * (time_resolution_ms / 1000.0):.3f}

Matched Frequencies ({len(matched_frequencies)} groups):
{freq_summary}
############################################################
"""
        print(debug_info)

    # ---- window guard ~ half a hop (prevents edge-touch overlaps) ----
    guard_s = 0.5 * (time_resolution_ms / 1000.0)

    # ---- 1) Pulsed FIRST ----
    if detect_pulsed:
        pulsed_result = detect_pulsed_single_tone(
            matched_frequencies,
            bw_hz=pulsed_bw_hz,
            min_cycles=pulsed_min_cycles,
            min_on_ms=pulsed_min_on_ms,
            max_on_ms=pulsed_max_on_ms,
            min_off_ms=pulsed_min_off_ms,
            max_off_ms=pulsed_max_off_ms,
            time_resolution_ms=time_resolution_ms,
            auto_center_band=pulsed_auto_center_band,
            mode_bin_hz=pulsed_mode_bin_hz,
        )
        pulsed_windows = _intervals_from_hits(pulsed_result)
        g1 = _filter_groups_outside(matched_frequencies, pulsed_windows, guard=guard_s)
    else:
        pulsed_result = []
        g1 = matched_frequencies

    # ---- 2) Two-tone on pulsed-filtered groups ----
    if detect_two_tone:
        two_tone_result = detect_two_tone_tones(
            g1,
            min_tone_a_length=tone_a_min_length,
            min_tone_b_length=tone_b_min_length,
            max_gap_between_a_b=two_tone_max_gap_between_a_b,
            tone_bw_hz=two_tone_bw_hz,
            min_pair_separation_hz=two_tone_min_pair_separation_hz,
        )
        # mask only B by default (prevents B→long collisions). Use which="both" if you want A masked too.
        qc_windows_B = _qc_windows_from_hits(two_tone_result, which="B", guard=guard_s)
        g2 = _filter_groups_outside(g1, qc_windows_B, guard=guard_s)
    else:
        two_tone_result = []
        g2 = g1

    # ---- 3) Long on groups with pulsed+QC(B) removed; then mask long windows ----
    if detect_long:
        long_result = detect_long_tones(
            g2,
            min_duration=long_tone_min_length,
            tone_bw_hz=long_tone_bw_hz,
            min_freq_hz=fe_freq_band[0],
        )
        long_windows = _intervals_from_hits(long_result)
        g3 = _filter_groups_outside(g2, long_windows, guard=guard_s)
    else:
        long_result = []
        g3 = g2

    # ---- 4) Hi/Low on groups with pulsed + QC(B) + long removed ----
    if detect_hi_low:
        hi_low_result = detect_warble_tones(
            g3,
            interval_length=hi_low_interval,
            min_alternations=hi_low_min_alternations,
            tone_bw_hz=hi_low_tone_bw_hz,
            min_pair_separation_hz=hi_low_min_pair_separation_hz,
        )
    else:
        hi_low_result = []

    # ---- 5) MDC / DTMF (raw audio) ----
    if detect_mdc:
        try:
            mdc_result = detect_mdc_tones(
                audio_segment,
                binary_path=icad_decode_path,
                highpass_freq=mdc_high_pass,
                lowpass_freq=mdc_low_pass
            )
        except Exception as e:
            raise ToneDetectionError(f"MDC detection failed: {e}") from e
    else:
        mdc_result = []

    if detect_dtmf:
        try:
            dtmf_result = detect_dtmf_tones(
                audio_segment,
                binary_path=icad_decode_path
            )
        except Exception as e:
            raise ToneDetectionError(f"DTMF detection failed: {e}") from e
    else:
        dtmf_result = []

    if debug:
        summary_info = f"""
------------------------------------------------------------
DETECTION SUMMARY
------------------------------------------------------------
Two-Tone (Quick Call): {len(two_tone_result)}
Long Tones:            {len(long_result)}
Hi-Low Warble:         {len(hi_low_result)}
Pulsed Single Tone:    {len(pulsed_result)}
MDC1200/FleetSync:     {len(mdc_result)}
DTMF:                  {len(dtmf_result)}
------------------------------------------------------------
"""
        print(summary_info)

    return ToneDetectionResult(
        two_tone_result=two_tone_result,
        long_result=long_result,
        hi_low_result=hi_low_result,
        pulsed_result=pulsed_result,
        mdc_result=mdc_result,
        dtmf_result=dtmf_result
    )
