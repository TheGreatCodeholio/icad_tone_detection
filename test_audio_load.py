from icad_tone_detection.audio_loader import load_audio

url = "https://trunk-player.s3.amazonaws.com/3-1744937667_482106250.m4a"

audio_segment, samples, frame_rate, duration_seconds = load_audio(url)
