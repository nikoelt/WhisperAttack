import os
import sys
import ctypes
import socket
import threading
import time
import logging
import subprocess
import unicodedata
import tempfile
import keyboard
import torch
import whisper
import sounddevice as sd
import soundfile as sf
import pyperclip
import re

###############################################################################
# CONFIG
###############################################################################
HOST = '127.0.0.1'
PORT = 65432

# Ensure the script is running with admin privileges
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit()

# Use the system's temporary folder for the WAV file
TEMP_DIR = tempfile.gettempdir()
AUDIO_FILE = os.path.join(TEMP_DIR, "whisper_temp_recording.wav")

VOICEATTACK_EXE = r"C:\Program Files (x86)\VoiceAttack\VoiceAttack.exe"
SAMPLE_RATE = 16000

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

###############################################################################
# NUMBER / TEXT PROCESSING HELPERS
###############################################################################
word_to_digit_map = {
    "zero": "0",
    "one": "1",
    "wun": "1",
    "two": "2",
    "three": "3",
    "tree": "3",
    "four": "4",
    "five": "5",
    "fife": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "niner": "9",
    "ten": "10",
    # Honeypot Bias
    "to": "2",
    "for": "4",
    "gulf": "Golf",
    "gold": "Golf",
    "mic": "Mike",
    "wosky": "Whiskey",
    "Weske": "Whiskey",
    "atel": "Hotel",
}

def replace_spelled_numbers_with_digits(text):
    """
    Replace spelled-out numbers (e.g., 'one', 'two') with digits ('1', '2').
    Uses case-insensitive matching on word boundaries.
    """
    for word, digit in word_to_digit_map.items():
        pattern = r"\b" + word + r"\b"
        text = re.sub(pattern, digit, text, flags=re.IGNORECASE)
    return text

def custom_cleanup_text(text):
    """
    Clean up the recognized text by:
    1. Normalizing the text.
    2. Replacing hyphens with spaces for easier processing of sequences.
    3. Replacing spelled-out numbers with digits.
    4. Removing unnecessary spaces between digits.
    5. Removing unwanted characters (punctuation, special symbols, etc.).
    """
    # Normalize unicode
    text = unicodedata.normalize('NFC', text.strip())

    # Replace hyphens with spaces for easier processing
    text = text.replace('-', ' ')

    # Replace spelled-out numbers and specific terms with their mapped values
    text = replace_spelled_numbers_with_digits(text)

    # Remove any non-word (a-z0-9_) and non-space characters except periods
    text = re.sub(r"[^\w\s.]", "", text)

    # Remove spaces between digits (e.g., "9 0" => "90")
    text = re.sub(r"(?<=\d)\s+(?=\d)", "", text)
    
    # Remove extra spaces between words
    text = re.sub(r"\s+", " ", text).strip()

    return text

###############################################################################
# WHISPER LOADING
###############################################################################
def load_whisper_model(device='GPU', model_size='small'):
    """
    Load the Whisper model once. Return the model object.
    """
    logging.info(f"Loading Whisper model ({model_size}), device={device}")
    if device.upper() == "GPU" and torch.cuda.is_available():
        return whisper.load_model(model_size).to('cuda')
    else:
        return whisper.load_model(model_size).to('cpu')

###############################################################################
# WHISPER SERVER
###############################################################################
class WhisperServer:
    def __init__(self, model, device='GPU'):
        self.model = model
        self.device = device
        self.recording = False
        self.audio_file = AUDIO_FILE
        self.wave_file = None
        self.stream = None
        self.stop_event = threading.Event()

    def start_recording(self):
        """
        Start recording to a local WAV file.
        """
        if self.recording:
            logging.warning("Already recording—ignoring start command.")
            return

        logging.info("Starting recording...")

        # Open SoundFile for writing (overwrite if exists)
        self.wave_file = sf.SoundFile(
            self.audio_file,
            mode='w',
            samplerate=SAMPLE_RATE,
            channels=1,
            subtype='FLOAT'
        )

        def audio_callback(indata, frames, time_info, status):
            if status:
                logging.warning(f"Audio Status: {status}")
            self.wave_file.write(indata)

        # Create the InputStream
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32',
            callback=audio_callback
        )
        self.stream.start()
        self.recording = True

    def stop_and_transcribe(self):
        """
        Stop recording, close the WAV file, transcribe, and send text to VoiceAttack.
        """
        if not self.recording:
            logging.warning("Not currently recording—ignoring stop command.")
            return

        logging.info("Stopping recording...")
        # Stop the stream
        self.stream.stop()
        self.stream.close()
        self.stream = None

        # Close the WAV file
        self.wave_file.close()
        self.wave_file = None
        self.recording = False

        # Delay to ensure OS flushes WAV file
        time.sleep(0.01)

        # Check file existence & size
        logging.info(f"Checking if file exists: {self.audio_file}")
        if os.path.exists(self.audio_file):
            size = os.path.getsize(self.audio_file)
            logging.info(f"File exists, size = {size} bytes")
        else:
            logging.error("File does NOT exist according to os.path.exists()!")

        # Transcribe
        recognized_text = self.transcribe_audio(self.audio_file)
        if recognized_text:
            self.send_to_voiceattack(recognized_text)
        else:
            logging.info("No transcription result.")

    def transcribe_audio(self, audio_path):
        """
        Use the loaded Whisper model to transcribe the audio file.
        """
        try:
            logging.info(f"Transcribing {audio_path}...")
            result = self.model.transcribe(
                audio_path, 
                language='en', 
                suppress_tokens="0,11,13,30",
                initial_prompt="This is for aviation use. Recognize phonetic alphabet, and output numbers as digits, not words",
            )
            # Now post-process the recognized text
            text = result["text"]
            logging.info(f"Raw transcription result: {text}")
            
            # Clean up/suppress hyphens, handle spelled-out numbers, etc.
            cleaned_text = custom_cleanup_text(text)

            logging.info(f"Final cleaned transcription: {cleaned_text}")
            return cleaned_text

        except Exception as e:
            logging.error(f"Failed to transcribe audio: {e}")
            return ""

    def send_to_voiceattack(self, text):
        """
        Copy text to clipboard and optionally invoke VoiceAttack with the recognized text.
        """
        # Copy to clipboard
        pyperclip.copy(text)
        logging.info("Text copied to clipboard using pyperclip.")
        try:
            keyboard.press_and_release('ctrl+alt+p')
            logging.info("DCS Kneeboard Populated")
        except Exception as e:
            logging.error(f"Failed to simulate keyboard shortcut: {e}")

        # If you want VoiceAttack to receive the recognized text as a command
        if os.path.isfile(VOICEATTACK_EXE):
            try:
                logging.info(f"Sending recognized text to VoiceAttack: {text}")
                subprocess.call([
                    VOICEATTACK_EXE,
                    '-command',
                    text
                ])
            except Exception as e:
                logging.error(f"Error calling VoiceAttack: {e}")
        else:
            logging.warning(f"VoiceAttack.exe not found at: {VOICEATTACK_EXE}")

    def handle_command(self, cmd):
        """
        Handle incoming socket commands from VoiceAttack or any other client.
        """
        cmd = cmd.strip().lower()
        logging.info(f"Received command: {cmd}")
        if cmd == "start":
            self.start_recording()
        elif cmd == "stop":
            self.stop_and_transcribe()
        elif cmd == "shutdown":
            logging.info("Received shutdown command. Stopping server.")
            self.stop_event.set()
        else:
            logging.warning(f"Unknown command: {cmd}")

    def run_server(self):
        """
        Main loop to run a socket server and respond to commands.
        """
        logging.info(f"Starting socket server on {HOST}:{PORT}...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            s.settimeout(1.0)  # 1s timeout so we can check stop_event occasionally

            while not self.stop_event.is_set():
                try:
                    conn, addr = s.accept()
                    with conn:
                        data = conn.recv(1024).decode('utf-8')
                        if data:
                            self.handle_command(data)
                except socket.timeout:
                    continue
                except Exception as e:
                    logging.error(f"Socket error: {e}")
                    continue

        # If we're still recording when we exit, stop gracefully
        if self.recording:
            self.stop_and_transcribe()

        logging.info("Server has shut down cleanly.")

###############################################################################
# MAIN
###############################################################################
def main():
    # Load Whisper model only once
    model = load_whisper_model(device='GPU', model_size='small')  # or 'base', 'medium', etc.

    # Create and run the server
    server = WhisperServer(model, device='GPU')
    server.run_server()

if __name__ == "__main__":
    main()
