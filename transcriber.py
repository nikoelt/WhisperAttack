import argparse
import logging
import os
import re
import socket
import subprocess
import time
import unicodedata
import warnings

import pyperclip
import soundfile as sf
import torch
import whisper
from wcwidth import wcswidth

warnings.filterwarnings("ignore")

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

###############################################################################
# CONFIG
###############################################################################
AUDIO_FILE = r".\sample.wav"  # The recorded audio to transcribe
VOICEATTACK_EXE = r"C:\Program Files (x86)\VoiceAttack\VoiceAttack.exe"

###############################################################################
# STOP SIGNAL (To tell recorder.py to stop)
###############################################################################
def send_stop_signal(host="127.0.0.1", port=65432):
    """
    Connect to the recorder.py socket server and send "stop".
    Recorder.py should then stop capturing and close the WAV file.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall(b'stop')
            logging.info("Stop signal sent.")
    except ConnectionRefusedError:
        logging.warning("Recorder is not running (connection refused).")
    except Exception as e:
        logging.error(f"Failed to send stop signal: {e}")

###############################################################################
# TEXT FORMATTING LOGIC (Optional)
###############################################################################
def justify_line(words, line_length):
    if len(words) == 1:
        # If there's only one word, just left-justify
        return words[0].ljust(line_length)

    total_words_length = sum(wcswidth(word) for word in words)
    total_spaces = line_length - total_words_length
    gaps = len(words) - 1
    spaces_between_words = [total_spaces // gaps] * gaps

    # Distribute extra spaces from left to right
    for i in range(total_spaces % gaps):
        spaces_between_words[i] += 1

    line = ''
    for i, word in enumerate(words[:-1]):
        line += word + (' ' * spaces_between_words[i])
    line += words[-1]  # last word
    return line

def process_text(text, line_length=53):
    """
    Break and justify text so each line is up to `line_length`.
    """
    text = unicodedata.normalize('NFC', text)
    words = re.findall(r'\S+|\n', text)

    lines = []
    current_words = []
    current_len = 0

    for word in words:
        if word == '\n':
            if current_words:
                line = justify_line(current_words, line_length)
                lines.append(line)
                current_words = []
                current_len = 0
            # Add a blank line
            lines.append(' ' * line_length)
            continue

        word_len = wcswidth(word)
        # If adding the next word exceeds line length, justify the current line
        if current_len + word_len + len(current_words) > line_length:
            line = justify_line(current_words, line_length)
            lines.append(line)
            current_words = [word]
            current_len = word_len
        else:
            current_words.append(word)
            current_len += word_len

    # Justify the last line (left-justified)
    if current_words:
        last_line = ' '.join(current_words).ljust(line_length)
        lines.append(last_line)

    # Append a final blank line if desired
    lines.append(' ' * line_length)
    return lines

###############################################################################
# WAIT FOR AUDIO FILE (OPTIONAL)
###############################################################################
def wait_for_file(filepath, timeout=10):
    """
    Wait up to `timeout` seconds for the file to stop growing in size,
    meaning the recorder is done writing to it.
    """
    start_time = time.time()
    last_size = -1
    while True:
        if os.path.exists(filepath):
            current_size = os.path.getsize(filepath)
            if current_size > 0 and current_size == last_size:
                logging.info("Audio file is ready for processing.")
                return True
            last_size = current_size
        else:
            logging.warning(f"Audio file {filepath} does not exist.")
        if (time.time() - start_time) > timeout:
            logging.error(f"Timeout waiting for audio file: {filepath}")
            return False
        time.sleep(0.1)

###############################################################################
# TRANSCRIBE + SEND TO VOICEATTACK
###############################################################################
def transcribe_and_send_to_voiceattack(
    audio_file_path=AUDIO_FILE,
    voiceattack_exe_path=VOICEATTACK_EXE,
    device_preference='CPU'
):
    """
    1) Wait for the audio file to be ready (optional).
    2) Load a Whisper model (CPU or GPU).
    3) Transcribe the WAV.
    4) Copy text to clipboard & optional logging.
    5) Send recognized text to VoiceAttack.
    """
    # 1) Wait for file to be finalized
    if not wait_for_file(audio_file_path):
        logging.error(f"Error: {audio_file_path} not ready or empty.")
        return

    # 2) Load Whisper model
    logging.info(f"Using device: {device_preference}")
    try:
        if device_preference.upper() == 'GPU' and torch.cuda.is_available():
            model = whisper.load_model("small").to("cuda")
            logging.info("Whisper model loaded on GPU.")
        else:
            model = whisper.load_model("small").to("cpu")
            logging.info("Whisper model loaded on CPU.")
    except Exception as e:
        logging.error(f"Failed to load Whisper model: {e}")
        return

    # 3) Transcribe
    try:
        audio_data, sample_rate = sf.read(audio_file_path, dtype='float32')
        result = model.transcribe(audio_data, language='en')
        recognized_text = unicodedata.normalize('NFC', result["text"].strip())
    except Exception as e:
        logging.error(f"Failed to transcribe audio: {e}")
        return

    # 4) Optional text formatting & logging
    formatted_lines = process_text(recognized_text)  
    logging.info("TRANSCRIPTION RESULT:")
    for line in formatted_lines:
        logging.info(f"'{line}'")
    # Copy to clipboard
    pyperclip.copy(recognized_text)

    # 5) Send recognized text to VoiceAttack
    if recognized_text:
        if not os.path.isfile(voiceattack_exe_path):
            logging.error(f"VoiceAttack.exe not found at {voiceattack_exe_path}")
            return
        try:
            subprocess.call([
                voiceattack_exe_path,
                '-command',
                recognized_text
            ])
            logging.info(f"Sent recognized text to VoiceAttack: {recognized_text}")
        except Exception as e:
            logging.error(f"Error calling VoiceAttack: {e}")
    else:
        logging.info("No recognized text to send to VoiceAttack.")

###############################################################################
# MAIN
###############################################################################
def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio with Whisper and send commands to VoiceAttack."
    )
    parser.add_argument('--device', choices=['CPU', 'GPU'], default='GPU',
                        help="Force use of CPU or GPU.")
    parser.add_argument('--skip-stop', action='store_true',
                        help="Skip sending 'stop' to the recorder.")
    args = parser.parse_args()

    # If we do NOT skip, send a "stop" to the recorder
    if not args.skip_stop:
        send_stop_signal()

    # Finally, transcribe & send to VoiceAttack
    transcribe_and_send_to_voiceattack(
        audio_file_path=AUDIO_FILE,
        device_preference=args.device
    )

if __name__ == "__main__":
    main()
