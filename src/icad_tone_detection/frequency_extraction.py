from typing import Tuple

from scipy.signal import stft
import numpy as np

from icad_tone_detection.exceptions import FrequencyExtractionError


class FrequencyExtraction:
    """
    Extract dominant per-frame frequencies with OFF gating and stable grouping.
    """

    def __init__(
            self,
            samples,
            frame_rate,
            duration_seconds,
            matching_threshold,
            time_resolution_ms,
            *,
            fe_freq_band: Tuple[float, float] = (200.0, 3000.0),
            fe_merge_short_gaps_ms: int = 0,
            fe_silence_below_global_db: float = -28.0,
            fe_snr_above_noise_db: float = 6.0,
    ):
        self.samples = samples
        self.frame_rate = frame_rate
        self.duration_seconds = duration_seconds
        self.time_resolution_ms = time_resolution_ms
        self.matching_threshold = matching_threshold
        self.fe_freq_band = fe_freq_band
        self.fe_merge_short_gaps_ms = fe_merge_short_gaps_ms
        self.fe_silence_below_global_db = fe_silence_below_global_db
        self.fe_snr_above_noise_db = fe_snr_above_noise_db

    # --------- helpers ---------
    @staticmethod
    def _parabolic_interpolate(y_minus, y0, y_plus):
        """
        Parabolic interpolation of the peak position around an FFT bin.
        Returns delta in [-0.5, +0.5] bins (0 means at the center bin).
        """
        denom = (y_minus - 2.0 * y0 + y_plus)
        if denom == 0:
            return 0.0
        return 0.5 * (y_minus - y_plus) / denom

    def _pick_nfft(self, hop):
        target = max(256, min(4096, 2 * hop))
        return int(2 ** round(np.log2(target)))

    # --------- main API ---------
    def get_audio_frequencies(self):
        """
        Extracts per-frame dominant frequencies using STFT with:
          - window length tied to time_resolution_ms (less smearing)
          - band-limited peak search (default 300–3000 Hz)
          - silence gating (quiet frames → 0.0)
          - quadratic peak interpolation (sub-bin accuracy)
          - end times corrected by +frame_step
          - optional short-gap merging in grouping
        """
        try:
            # ---- 1) Hop/window ----
            hop_length = max(1, int(self.frame_rate * self.time_resolution_ms / 1000.0))
            n_fft = self._pick_nfft(hop_length)

            # ---- 2) STFT (no padding) ----
            freqs, times, Zxx = stft(
                self.samples,
                fs=self.frame_rate,
                window="hann",
                nperseg=n_fft,
                noverlap=max(0, n_fft - hop_length),
                boundary=None,
                padded=False,
            )
            mag = np.abs(Zxx)  # (freq_bins, frames)
            if mag.size == 0:
                return []

            # Frame step (seconds) — with boundary=None times are spaced by hop/fs
            step_s = times[1] - times[0] if len(times) > 1 else hop_length / float(self.frame_rate)

            # ---- 3) Band-limit search ----
            fmin, fmax = self.fe_freq_band
            band = (freqs >= fmin) & (freqs <= fmax)
            if not np.any(band):
                band = np.ones_like(freqs, dtype=bool)
            bf = freqs[band]
            bm = mag[band, :]  # (band_bins, frames)

            # ---- 4) Silence gating vs global peak & noise floor ----
            eps = 1e-20
            frame_peaks = np.maximum(bm.max(axis=0), eps)
            global_peak = float(np.max(frame_peaks))
            if global_peak <= eps:
                return []

            rel_db = 20.0 * np.log10(frame_peaks / global_peak + eps)  # per-frame dB below global
            q20 = float(np.quantile(rel_db, 0.20))
            noise_floor_db = float(np.median(rel_db[rel_db <= q20])) if np.any(rel_db <= q20) else -60.0

            is_silent = (rel_db < self.fe_silence_below_global_db) | (rel_db < (noise_floor_db + self.fe_snr_above_noise_db))

            # ---- 5) Dominant bin + parabolic interpolation for non-silent frames ----
            peak_idx = np.argmax(bm, axis=0)  # (frames,)
            detected = np.zeros_like(peak_idx, dtype=float)

            # bin width:
            df = bf[1] - bf[0] if len(bf) > 1 else self.frame_rate / n_fft

            for t in range(bm.shape[1]):
                if is_silent[t]:
                    detected[t] = 0.0
                    continue
                k = int(peak_idx[t])
                # edge-safe neighbors
                k0 = max(0, min(k, bm.shape[0] - 1))
                km = max(0, k0 - 1)
                kp = min(bm.shape[0] - 1, k0 + 1)
                # parabolic interpolation on magnitudes
                delta = self._parabolic_interpolate(bm[km, t], bm[k0, t], bm[kp, t])
                delta = float(np.clip(delta, -0.5, 0.5))
                detected[t] = bf[k0] + delta * df

            # ---- 6) Group adjacent frames into (start, end, dur, freqs) ----
            #    + correct end time by +step_s so ranges represent [start, end)
            matching = self.match_frequencies(
                detected.tolist(), times, step_s=step_s, merge_short_gaps_ms=self.fe_merge_short_gaps_ms
            )
            return matching or []

        except Exception as e:
            raise FrequencyExtractionError(f"Failed to extract frequencies using STFT: {e}") from e

    # --------- grouping utilities ---------
    def dynamic_threshold(self, frequencies, index):
        """
        Dynamic tolerance (percent of previous). If previous is 0.0, force a split.
        Also clamp to an absolute cap so high freqs don't get huge ranges.
        """
        prev_f = frequencies[max(0, index - 1)]
        if prev_f <= 0.0:
            return 0.0
        # percent-based tolerance
        pct_tol = abs(prev_f) * self.matching_threshold / 100.0
        # absolute cap (prevents massive windows at high f); ~30 Hz is good for pager-like tones
        abs_cap_hz = 30.0
        return min(pct_tol, abs_cap_hz)

    def calculate_times(self, start_index, end_index, time_samples, step_s):
        """
        Start is the time-center of the first frame; end is the END of the last frame.
        """
        start_time = float(round(time_samples[start_index], 3))
        # end index is inclusive of a frame; add one frame step to mark end boundary
        end_time = float(round(time_samples[end_index] + step_s, 3))
        return start_time, end_time

    @staticmethod
    def amplitude_to_decibels(amplitude, reference_value):
        reference_value = np.maximum(reference_value, 1e-20)
        return 20 * np.log10(np.maximum(amplitude, 1e-20) / reference_value)

    def match_frequencies(self, detected_frequencies, time_samples, *, step_s, merge_short_gaps_ms=0):
        """
        Group consecutive frames whose detected fundamental stays within a dynamic threshold.
        Zero frames (OFF) always break groups, forming their own OFF groups (freq=0.0).
        Optionally merge gaps shorter than `merge_short_gaps_ms`.
        Returns: list of (start, end, duration, [freqs...])
        """
        if not detected_frequencies:
            return []

        try:
            freqs = [round(float(f), 1) for f in detected_frequencies]
            groups = []
            cur = [freqs[0]]
            start_i = 0

            def flush(s_i, e_i, seq):
                s, e = self.calculate_times(s_i, e_i, time_samples, step_s)
                return (s, e, round(e - s, 3), seq)

            for i in range(1, len(freqs)):
                # If either current or previous is 0.0, force boundary (separates ON/OFF cleanly)
                if (freqs[i] == 0.0) != (freqs[i - 1] == 0.0):
                    if len(cur) >= 1:
                        groups.append(flush(start_i, i - 1, cur))
                    cur = [freqs[i]]
                    start_i = i
                    continue

                thr = self.dynamic_threshold(freqs, i)
                if abs(freqs[i] - freqs[i - 1]) <= thr:
                    cur.append(freqs[i])
                else:
                    groups.append(flush(start_i, i - 1, cur))
                    cur = [freqs[i]]
                    start_i = i

            # last group
            groups.append(flush(start_i, len(freqs) - 1, cur))

            # Optional: merge tiny gaps between same-state groups (e.g., 1 missing frame)
            if merge_short_gaps_ms and len(groups) >= 2:
                merged = []
                i = 0
                gap_thresh = merge_short_gaps_ms / 1000.0
                while i < len(groups):
                    if i == len(groups) - 1:
                        merged.append(groups[i])
                        break
                    s1, e1, d1, f1 = groups[i]
                    s2, e2, d2, f2 = groups[i + 1]
                    same_state = (f1[0] == 0.0 and f2[0] == 0.0) or (f1[0] != 0.0 and f2[0] != 0.0)
                    gap = max(0.0, s2 - e1)
                    if same_state and gap <= gap_thresh:
                        # merge
                        merged.append((s1, e2, round(e2 - s1, 3), f1 + f2))
                        i += 2
                    else:
                        merged.append(groups[i])
                        i += 1
                groups = merged

            return groups

        except Exception as e:
            raise FrequencyExtractionError(f"Error matching frequencies: {e}") from e
