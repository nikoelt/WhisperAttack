import socket
import threading
import time
import logging
import subprocess
import os
import unicodedata
import tempfile

import torch
import whisper
import sounddevice as sd
import soundfile as sf
import pyperclip

###############################################################################
# CONFIG
###############################################################################
HOST = '127.0.0.1'
PORT = 65432

# Use the system's temporary folder for the WAV file
TEMP_DIR = tempfile.gettempdir()
AUDIO_FILE = os.path.join(TEMP_DIR, "whisper_temp_recording.wav")

VOICEATTACK_EXE = r"C:\Program Files (x86)\VoiceAttack\VoiceAttack.exe"
SAMPLE_RATE = 16000

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        time.sleep(0.1)

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
            result = self.model.transcribe(audio_path, language='en')
            text = unicodedata.normalize('NFC', result["text"].strip())
            logging.info(f"Transcription result: {text}")
            return text
        except Exception as e:
            logging.error(f"Failed to transcribe audio: {e}")
            return ""

    def send_to_voiceattack(self, text):
        """
        Copy text to clipboard and optionally invoke VoiceAttack with the recognized text.
        """
        # Copy to clipboard
        pyperclip.copy(text)

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
    model = load_whisper_model(device='GPU', model_size='small.en')  # or 'base', etc.

    # Create and run the server
    server = WhisperServer(model, device='GPU')
    server.run_server()

if __name__ == "__main__":
    main()
