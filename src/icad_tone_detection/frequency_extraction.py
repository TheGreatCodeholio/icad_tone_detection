from scipy.signal import stft
import numpy as np


class FrequencyExtraction:
    """
        A class for extracting frequencies from audio samples using Short-Time Fourier Transform (STFT).

        Attributes:
            samples (np.array): The audio samples.
            frame_rate (int): The sampling rate of the audio.
            duration_seconds (float): The duration of the audio in seconds.
            matching_threshold (float): The percentage threshold used to determine if two frequencies
                are considered a match. For example, a threshold of 2 means that two frequencies are considered matching
                if they are within 2% of each other.
            time_resolution_ms (int): The time resolution in milliseconds for the STFT. Default is 100ms.
    """

    def __init__(self, samples, frame_rate, duration_seconds, matching_threshold, time_resolution_ms):
        """
        Initializes the FrequencyExtraction class with audio data.

         Parameters:
            - samples (np.array): The audio samples.
            - frame_rate (int): The sampling rate of the audio.
            - duration_seconds (float): The duration of the audio in seconds.
            - matching_threshold (float): The percentage threshold used to determine if two frequencies
               are considered a match.
            - time_resolution_ms (int): The time resolution in milliseconds for the STFT. Default is 100ms.
         """
        self.samples = samples
        self.frame_rate = frame_rate
        self.duration_seconds = duration_seconds
        self.time_resolution_ms = time_resolution_ms
        self.matching_threshold = matching_threshold

    def get_audio_frequencies(self):
        """
        Extracts frequencies from the audio data using STFT.

        Returns:
            list: A list of tuples, each containing the start time and a list of matching frequencies, or None if an error occurs.
        """
        try:
            window = 'hann'
            n_fft = 2048  # Number of FFT points

            # Calculate hop_length based on the desired time resolution
            hop_length = int(self.frame_rate * self.time_resolution_ms / 1000)

            # Perform the STFT
            frequencies, _, zxx = stft(self.samples, self.frame_rate, window=window, nperseg=n_fft,
                                       noverlap=n_fft - hop_length)
            amplitude = np.abs(zxx)  # Get the magnitude of the STFT coefficients

            # Convert amplitude to decibels
            amplitude_db = self.amplitude_to_decibels(amplitude, np.max(amplitude))

            # Detect the frequency with the highest amplitude at each time step
            detected_frequencies = frequencies[np.argmax(amplitude_db, axis=0)]

            matching_frequencies = self.match_frequencies(detected_frequencies.tolist())

            return matching_frequencies

        except Exception as e:
            print(f"Error extracting frequencies: {e}")
            return None

    @staticmethod
    def amplitude_to_decibels(amplitude, reference_value):
        """
        Converts amplitude to decibels relative to a reference value.

        Parameters:
            amplitude (np.array): The amplitude of the frequencies.
            reference_value (float): The reference value for the conversion.

        Returns:
            np.array: The amplitude in decibels.
        """
        # Ensure the reference is not zero to avoid division by zero
        reference_value = np.maximum(reference_value, 1e-20)
        return 20 * np.log10(np.maximum(amplitude, 1e-20) / reference_value)

    def match_frequencies(self, detected_frequencies):
        """
        Identifies and groups matching frequencies from a list of detected frequencies based on the matching threshold.
        Each group's start time, end time, and the matching frequencies are returned.

        Parameters:
            detected_frequencies (list of float): The detected frequencies from the audio sample.

        Returns:
            list of tuples: Each tuple contains the start time, end time, and a list of matching frequencies.
        """
        if not detected_frequencies:
            return []

        try:
            frequencies = [round(f, 1) for f in detected_frequencies]
            matching_frequencies = []
            current_match = [frequencies[0]]
            start_index = 0  # Initialize start index for the first frequency

            for i in range(1, len(frequencies)):
                threshold = frequencies[i - 1] * self.matching_threshold / 100
                if abs(frequencies[i] - frequencies[i - 1]) <= threshold:
                    current_match.append(frequencies[i])
                else:
                    if len(current_match) >= 2:
                        # Calculate start and end times for the current match
                        start_time = round(start_index * self.duration_seconds / len(frequencies), 3)
                        end_time = round(i * self.duration_seconds / len(frequencies), 3)
                        matching_frequencies.append((start_time, end_time, current_match))
                    current_match = [frequencies[i]]
                    start_index = i  # Update start index for the new match

            # Handle the last group of matching frequencies
            if len(current_match) >= 2:
                start_time = round(start_index * self.duration_seconds / len(frequencies), 3)
                end_time = round(len(frequencies) * self.duration_seconds / len(
                    frequencies), 3)  # End time for the last frequency
                matching_frequencies.append((start_time, end_time, current_match))

            return matching_frequencies
        except Exception as e:
            print(f"Error matching frequencies: {e}")
            return []
