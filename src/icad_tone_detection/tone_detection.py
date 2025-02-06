import json
import shutil
import subprocess

from pydub import AudioSegment


def detect_two_tone(frequency_matches, min_tone_a_length=0.7, min_tone_b_length=2.7):
    two_tone_matches = []
    tone_id = 0
    last_set = None
    if not frequency_matches or len(frequency_matches) < 1:
        return two_tone_matches

    for current_set in frequency_matches:
        if all(f > 0 for f in current_set[3]):  # Ensure frequencies are non-zero
            current_duration = current_set[1] - current_set[0]  # Calculate the duration of the current tone

            if last_set is None:
                last_set = current_set
            else:
                last_duration = last_set[1] - last_set[0]  # Calculate the duration of the last tone
                # Check if the last tone is a valid A tone and the current is a valid B tone
                if last_duration >= min_tone_a_length and current_duration >= min_tone_b_length:
                    tone_data = {
                        "tone_id": f'qc_{tone_id + 1}',
                        "detected": [last_set[3][0], current_set[3][0]],  # Frequency values of A and B tones
                        "tone_a_length": last_set[2],
                        "tone_b_length": current_set[2],
                        "start": last_set[0],  # Start time of tone A
                        "end": current_set[1]  # End time of tone B
                    }
                    tone_id += 1
                    two_tone_matches.append(tone_data)
                # Update last_set to current_set for next iteration
                last_set = current_set

    return two_tone_matches


def detect_long_tones(frequency_matches, detected_quickcall, min_duration=2.0):
    long_tone_matches = []
    excluded_frequencies = set([0.0])  # Initializing with 0.0 Hz to exclude it

    # Add detected quick call tones to the excluded list
    for quickcall in detected_quickcall:
        excluded_frequencies.update(quickcall["detected"][:2])

    for start, end, duration, frequencies in frequency_matches:
        if not frequencies:
            continue

        current_frequency = frequencies[0]

        # Skip the loop iteration if the current frequency is in the excluded frequencies
        if current_frequency in excluded_frequencies or current_frequency <= 500:
            continue

        # Check if the duration meets the minimum requirement
        if duration >= min_duration:
            tone_data = {
                "tone_id": f"lt_{len(long_tone_matches) + 1}",
                "detected": current_frequency,
                "start": start,
                "end": end,
                "length": duration
            }
            long_tone_matches.append(tone_data)

    return long_tone_matches


def within_tolerance(frequency1, frequency2, tolerance=0.02):
    """
    Check if two frequencies are within a specified tolerance percentage.

    Parameters:
    - frequency1: The first frequency to compare.
    - frequency2: The second frequency to compare.
    - tolerance: The tolerance threshold as a percentage.

    Returns:
    - A boolean indicating whether the two frequencies are within the specified tolerance.
    """
    if frequency1 is None or frequency2 is None:
        return False
    return abs(frequency1 - frequency2) / frequency1 <= tolerance


def detect_warble_tones(frequency_matches, interval_length, min_alternations):
    """
    Extract sequences of alternating warble tones from a list of frequency matches.

    Parameters:
    - frequency_matches: A list of tuples, each containing start time, end time, and a list of frequencies.
    - interval_length: The maximum allowed interval in seconds between consecutive tones.
    - min_alternations: The minimum number of alternations for a sequence to be considered valid.

    Returns:
    - A list of dictionaries, each representing a detected sequence of warble tones with its details.
    """
    sequences = []
    id_index = 1

    i = 0
    while i < len(frequency_matches):
        current_sequence = []
        current_tones = []

        while i < len(frequency_matches):
            group = frequency_matches[i]
            if not group[3] or group[3][0] <= 0 or len(group[3]) < 2:
                i += 1
                continue

            freq = group[3][0]

            if not current_sequence:
                # Start a new sequence with the current group
                current_sequence.append(group)
                current_tones.append(freq)
            else:
                last_group = current_sequence[-1]
                last_freq = last_group[3][0]

                # Check that the new frequency alternates with the previous one
                # and it's within the time interval limit
                if freq != last_freq and group[0] - last_group[1] <= interval_length:
                    if len(current_tones) < 2:
                        # If we have less than 2 tones, add the new tone
                        current_tones.append(freq)
                    if freq in current_tones:
                        # Add to sequence if it continues the alternation pattern
                        current_sequence.append(group)
                    else:
                        # Break the sequence if a new, third tone is introduced
                        break
                else:
                    # Break the sequence if the same frequency repeats or interval exceeded
                    break

            i += 1

        # Check if the current sequence is valid before proceeding
        if len(current_sequence) >= min_alternations:
            if len(current_tones) == 2:  # Ensure exactly two tones are alternating
                sequences.append({
                    "tone_id": f"hl_{id_index}",
                    "detected": list(current_tones),
                    "start": current_sequence[0][0],
                    "end": current_sequence[-1][1],
                    "length": round(current_sequence[-1][1] - current_sequence[0][0], 2),
                    "alternations": len(current_sequence)
                })
                id_index += 1

        # Move to the next possible sequence start
        if i < len(frequency_matches) and not current_sequence:
            i += 1  # Increment only if no sequence was started to avoid getting stuck

    return sequences

def detect_mdc_tones(
        segment: AudioSegment,
        binary_path: str = "icad_decode",
        highpass_freq: int = 200,
        lowpass_freq: int = 4000,
        require_unsigned_8bit: bool = True
) -> list[str]:
    """
    Decode MDC1200 (or Fleetsync) frames from a PyDub AudioSegment by piping raw audio to an external 'icad_decode' binary.

    :param segment:             A PyDub AudioSegment containing audio to decode.
    :param binary_path:          Path to the 'icad_decode' executable (default: 'icad_decode').
    :param highpass_freq:       Frequency in Hz for highpass filter (default: 200).
    :param lowpass_freq:        Frequency in Hz for lowpass filter (default: 4000).
    :param require_unsigned_8bit:
                                Whether to shift samples from signed 8-bit (PyDub default) to unsigned 8-bit.
                                If True, each sample is shifted by +128. If your icad_decode can handle signed 8-bit,
                                set this to False. (default: True)

    :return: mdc_matches list of dicts each dict representing a detected sequence of MDC1200 (or Fleetsync) frames.

    :raises FileNotFoundError:  If binary_path is not found on the system.
    :raises ValueError:         If the audio segment is empty or too short to process.
    :raises RuntimeError:       If 'icad_decode' fails to run properly or returns a nonzero exit code.
    """

    mdc_matches = []


    # Check if the AudioSegment is non-empty
    if len(segment) == 0:
        raise ValueError("The provided AudioSegment is empty (0 ms). Nothing to decode.")

    # ----------------------------------------------------------------
    # 1) Resample, convert to mono, apply filters
    # ----------------------------------------------------------------
    # Convert to 22050 Hz, mono, 16-bit (PyDub uses signed 8-bit by default)
    segment = segment.set_frame_rate(22050)
    segment = segment.set_channels(1)
    segment = segment.set_sample_width(2)  # 16-bit, *signed* in PyDub

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
    if require_unsigned_8bit:
        raw_data = bytes((s + 128) & 0xFF for s in raw_data)

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
        try:
            obj = json.loads(line)
            mdc_matches.append(obj)
        except json.JSONDecodeError:
            pass

    return mdc_matches

def detect_dtmf_tones(
        segment: AudioSegment,
        binary_path: str = "icad_decode"
) -> list[str]:
    """
    Decode dtmf tones from a PyDub AudioSegment by piping raw audio to an external 'decode' binary.

    :param segment:             A PyDub AudioSegment containing audio to decode.
    :param binary_path:          Path to the 'icad_decode' executable (default: 'icad_decode').

    :return: dtmf_matches list of dicts each dict representing a detected dtmf key press.

    :raises FileNotFoundError:  If binary_path is not found on the system.
    :raises ValueError:         If the audio segment is empty or too short to process.
    :raises RuntimeError:       If 'icad_decode' fails to run properly or returns a nonzero exit code.
    """

    dtmf_matches = []

    # Check if the AudioSegment is non-empty
    if len(segment) == 0:
        raise ValueError("The provided AudioSegment is empty (0 ms). Nothing to decode.")

    # ----------------------------------------------------------------
    # 1) Resample, convert to mono, apply filters
    # ----------------------------------------------------------------
    # Convert to 22050 Hz, mono, 16-bit
    segment = segment.set_frame_rate(22050) # 22050 frame rate
    segment = segment.set_channels(1) # Mono
    segment = segment.set_sample_width(2)  # 16-bit, *signed* in PyDub

    raw_data = segment.raw_data

    # ----------------------------------------------------------------
    # 2) Pipe the raw audio bytes into 'icad_decode' via subprocess
    # ----------------------------------------------------------------
    cmd = [binary_path, "-m", "dtmf", "-"]  # '-' indicates reading from STDIN
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