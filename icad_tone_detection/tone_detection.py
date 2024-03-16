def detect_quickcall(frequency_matches):
    qc2_matches = []
    tone_id = 0
    last_set = None
    for x in frequency_matches:
        if last_set is None and len(x[2]) >= 8 and 0 not in x[2] and 0.0 not in x[2]:
            last_set = x
        else:
            if len(x[2]) >= 8 and 0 not in x[2] and 0.0 not in x[2]:
                if len(last_set[2]) <= 12 and len(x[2]) >= 28:
                    tone_data = {"tone_id": f'qc_{tone_id + 1}', "detected": [last_set[2][0], x[2][0]],
                                 "start": last_set[0], "end": x[1]}
                    tone_id += 1
                    qc2_matches.append(tone_data)
                    last_set = x
                else:
                    last_set = x

    return qc2_matches


def detect_long_tones(frequency_matches, detected_quickcall):
    tone_id = 0
    long_tone_matches = []
    excluded_frequencies = set([])

    if not frequency_matches:
        return long_tone_matches
    last_set = frequency_matches[0]
    # add detected quick call tones to a list, so we can exclude them from long tone matches.
    for ttd in detected_quickcall:
        excluded_frequencies.update(ttd["detected"][:2])

    for x in frequency_matches:
        if len(x[2]) >= 10:
            if 12 >= len(last_set) >= 8 and len(x[2]) >= 20:
                last_set = x[2]
            elif len(x[2]) >= 15:
                if x[2][0] == 0 or x[2][0] == 0.0:
                    continue
                if x[2][0] in excluded_frequencies:
                    continue

                if x[2][0] > 250:
                    tone_data = {"tone_id": f'lt_{tone_id + 1}', "detected": x[2][0], "start": round(x[0], 3),
                                 "end": round(x[1], 3)}
                    tone_id += 1
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

    if not frequency_matches:
        raise ValueError("The frequency_matches list cannot be empty.")

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
