# def detect_quickcall(frequency_matches):
#     qc2_matches = []
#     tone_id = 0
#     last_set = None
#     if not frequency_matches or len(frequency_matches) < 1:
#         return qc2_matches
#     for x in frequency_matches:
#         if last_set is None and len(x[2]) >= 8 and 0 not in x[2] and 0.0 not in x[2]:
#             last_set = x
#         else:
#             if len(x[2]) >= 8 and 0 not in x[2] and 0.0 not in x[2]:
#                 if len(last_set[2]) <= 12 and len(x[2]) >= 28:
#                     tone_data = {"tone_id": f'qc_{tone_id + 1}', "detected": [last_set[2][0], x[2][0]],
#                                  "start": last_set[0], "end": x[1]}
#                     tone_id += 1
#                     qc2_matches.append(tone_data)
#                     last_set = x
#                 else:
#                     last_set = x
#
#     return qc2_matches


def detect_two_tone(frequency_matches, min_tone_a_length=0.8, min_tone_b_length=2.8):
    two_tone_matches = []
    tone_id = 0
    last_set = None
    if not frequency_matches or len(frequency_matches) < 1:
        return two_tone_matches

    for current_set in frequency_matches:
        if all(f > 0 for f in current_set[2]):  # Ensure frequencies are non-zero
            current_duration = current_set[1] - current_set[0]  # Calculate the duration of the current tone

            if last_set is None:
                last_set = current_set
            else:
                last_duration = last_set[1] - last_set[0]  # Calculate the duration of the last tone
                # Check if the last tone is a valid A tone and the current is a valid B tone
                if last_duration >= min_tone_a_length and current_duration >= min_tone_b_length:
                    tone_data = {
                        "tone_id": f'qc_{tone_id + 1}',
                        "detected": [last_set[2][0], current_set[2][0]],  # Frequency values of A and B tones
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

    for start, end, frequencies in frequency_matches:
        duration = end - start
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


# def extract_warble_tones(frequency_matches, interval_length, min_alternations):
#     """
#     Extract sequences of alternating tones (warble tones) from detected tones,
#     following the specified process.
#
#     Parameters:
#     detected_tones (list of tuples): Detected tones with start time, end time, and frequencies.
#     interval_length (float): The maximum allowed interval in seconds between alternating tones.
#     min_alternations (int): The minimum number of alternations for a sequence to be considered valid.
#
#     Returns:
#     list of dicts: Extracted warble tones with details including start, end, and tones.
#     """
#     sequences = []
#     id_index = 1
#     current_index = 0
#     new_sequence = []
#     # Iterate over frequency matches
#     for index, group in enumerate(frequency_matches):
#         if index + 3 >= len(frequency_matches):
#             if len(new_sequence) >= min_alternations:
#                 new_detection = {
#                     "hl_id": id_index,
#                     "tones": [new_sequence[0][2][0], new_sequence[1][2][0]],
#                     "start": new_sequence[0][0],
#                     "end": new_sequence[-1][0]
#                 }
#                 sequences.append(new_detection)
#                 new_sequence.clear()
#                 id_index += 1
#             break
#
#         if index != current_index:
#             continue
#
#         group_a = frequency_matches[index]
#         group_b = frequency_matches[index + 1]
#         group_c = frequency_matches[index + 2]
#         group_d = frequency_matches[index + 3]
#
#         group_a_tone = group_a[2][0]
#         group_b_tone = group_b[2][0]
#         group_c_tone = group_c[2][0]
#         group_d_tone = group_d[2][0]
#
#         if 0 in (group_a_tone, group_b_tone, group_c_tone, group_d_tone) or 0.0 in (
#                 group_a_tone, group_b_tone, group_c_tone, group_d_tone):
#             current_index += 1
#             if len(new_sequence) >= min_alternations:
#                 new_detection = {
#                     "hl_id": id_index,
#                     "tones": [new_sequence[0][2][0], new_sequence[1][2][0]],
#                     "start": new_sequence[0][0],
#                     "end": new_sequence[-1][0]
#                 }
#                 sequences.append(new_detection)
#                 new_sequence.clear()
#                 id_index += 1
#             continue
#
#         if group_a_tone == group_b_tone or group_c_tone == group_d_tone:
#             current_index += 1
#             if len(new_sequence) >= min_alternations:
#                 new_detection = {
#                     "hl_id": id_index,
#                     "tones": [new_sequence[0][2][0], new_sequence[1][2][0]],
#                     "start": new_sequence[0][0],
#                     "end": new_sequence[-1][0]
#                 }
#                 sequences.append(new_detection)
#                 new_sequence.clear()
#                 id_index += 1
#             continue
#
#         # if any group has less 2 frequencies continue it can't be a warble tone.
#         if len(group_a[2]) < 2 or len(group_b[2]) < 2 or len(group_c[2]) < 2 or len(group_d[2]) < 2:
#             current_index += 1
#             if len(new_sequence) >= min_alternations:
#                 new_detection = {
#                     "hl_id": id_index,
#                     "tones": [new_sequence[0][2][0], new_sequence[1][2][0]],
#                     "start": new_sequence[0][0],
#                     "end": new_sequence[-1][0]
#                 }
#                 sequences.append(new_detection)
#                 new_sequence.clear()
#                 id_index += 1
#             continue
#
#         # check to see if our groups occurred within the threshold interval length threshold
#         if not (group_b[0] - group_a[1] <= interval_length) and (group_c[0] - group_b[1] <= interval_length) and (group_d[0] - group_c[1] <= interval_length):
#             current_index += 1
#             if len(new_sequence) >= min_alternations:
#                 new_detection = {
#                     "hl_id": id_index,
#                     "tones": [new_sequence[0][2][0], new_sequence[1][2][0]],
#                     "start": new_sequence[0][0],
#                     "end": new_sequence[-1][0]
#                 }
#                 sequences.append(new_detection)
#                 new_sequence.clear()
#                 id_index += 1
#             continue
#
#         # if group a and c don't match continue
#         if not within_tolerance(group_a_tone, group_c_tone):
#             current_index += 1
#             if len(new_sequence) >= min_alternations:
#                 new_detection = {
#                     "hl_id": id_index,
#                     "tones": [new_sequence[0][2][0], new_sequence[1][2][0]],
#                     "start": new_sequence[0][0],
#                     "end": new_sequence[-1][0]
#                 }
#                 sequences.append(new_detection)
#                 new_sequence.clear()
#                 id_index += 1
#             continue
#
#         # if group b and d don't match continue
#         if not within_tolerance(group_b_tone, group_d_tone):
#             current_index += 1
#             if len(new_sequence) >= min_alternations:
#                 new_detection = {
#                     "hl_id": id_index,
#                     "tones": [new_sequence[0][2][0], new_sequence[1][2][0]],
#                     "start": new_sequence[0][0],
#                     "end": new_sequence[-1][0]
#                 }
#                 sequences.append(new_detection)
#                 new_sequence.clear()
#                 id_index += 1
#             continue
#
#         # we have a potential match
#         new_sequence.append(group_a)
#         new_sequence.append(group_b)
#         new_sequence.append(group_c)
#         new_sequence.append(group_d)
#
#         current_index += 4
#
#     return sequences

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

    if not frequency_matches or len(frequency_matches) < 1:
        return sequences

    i = 0
    while i < len(frequency_matches):
        current_sequence = []

        while i < len(frequency_matches):
            group = frequency_matches[i]
            # Ensure there are frequencies to evaluate
            if not group[2]:
                i += 1
                break

            freq = group[2][0]

            # Skip groups with invalid frequencies or not enough tones
            if freq <= 0 or len(group[2]) < 2:
                i += 1
                break

            if not current_sequence:
                current_sequence.append(group)
            else:
                group_a = current_sequence[-1]
                tone_a = group_a[2][0]

                tone_b = freq

                # Check for the next group, if it exists
                if i + 1 < len(frequency_matches):
                    group_c = frequency_matches[i + 1]
                    tone_c = group_c[2][0]

                    # Ensure current tone does not match the adjacent tones directly
                    if tone_a == tone_b or tone_b == tone_c:
                        i += 1
                        break

                    # Check for alternation with a tolerance
                    if len(current_sequence) >= 2:
                        previous_alt_tone = current_sequence[-2][2][0]
                        if within_tolerance(tone_b, previous_alt_tone) and group[0] - group_a[1] < interval_length:
                            current_sequence.append(group)
                        else:
                            i += 1
                            break
                    else:
                        current_sequence.append(group)
                else:
                    # Handle the last group
                    current_sequence.append(group)
                    break

            i += 1

        # Validate and append the sequence if it meets the criteria
        if len(current_sequence) >= min_alternations * 2:
            sequences.append({
                "tone_id": f"hl_{id_index}",
                "detected": [current_sequence[0][2][0], current_sequence[1][2][0]],
                "start": current_sequence[0][0],
                "end": current_sequence[-1][1]
            })
            id_index += 1

    return sequences
