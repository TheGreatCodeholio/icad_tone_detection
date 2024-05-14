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
