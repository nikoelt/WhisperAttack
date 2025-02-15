import sys
import os
import subprocess
import pkg_resources

# Set the working directory to the script's folder.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ------------- AUTO-INSTALL MISSING DEPENDENCIES -------------
REQUIRED_PACKAGES = [
    "openai-whisper",
    "sounddevice",
    "soundfile",   # note: the actual PyPI package name is "SoundFile"
    "rapidfuzz",
    "pyperclip",
    "keyboard",
    "torch",
    "text2digits"
]

def install_missing_packages():
    """Check if each required package is installed; if not, install it."""
    python_exe = sys.executable
    installed_packages = {pkg.key for pkg in pkg_resources.working_set}
    missing = []
    for package in REQUIRED_PACKAGES:
        # For case-insensitivity in package name checks.
        if package.lower() not in installed_packages:
            if package.lower() == "torch":
                # Install the torch package from the PyTorch channel with CUDA support.
                subprocess.check_call(
                    [python_exe, "-m", "pip", "install", "torch", "--index-url", "https://download.pytorch.org/whl/cu118"]
                )
            else:
                missing.append(package)
    # Install any other missing packages
    if missing:
        print(f"Installing missing packages: {missing}")
        subprocess.check_call(
            [python_exe, "-m", "pip", "install", "--upgrade"] + missing
        )
    else:
        print("All required packages are already installed.")

# First, auto-install the required Python packages.
install_missing_packages()

# Re-import modules to ensure they’re available in the current session.
import ctypes
import socket
import threading
import time
import logging
import unicodedata
import tempfile
import keyboard
import torch
import whisper
import sounddevice as sd
import soundfile as sf
import pyperclip
import re
from rapidfuzz import process
from text2digits import text2digits

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

###############################################################################
# ENSURE FFmpeg IS INSTALLED
###############################################################################
def ensure_ffmpeg_installed():
    """
    Checks if FFmpeg is installed.
    If not, attempts to install it using winget.
    This function assumes the script is running with administrative privileges.
    """
    try:
        subprocess.run(["ffmpeg", "-version"],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,
                       check=True)
        logging.info("FFmpeg is already installed.")
    except Exception:
        logging.info("FFmpeg not found. Attempting to install FFmpeg using winget...")
        # Verify that winget is available.
        try:
            subprocess.run(["winget", "--version"],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           check=True)
        except Exception:
            logging.error("Winget is not available. Please install FFmpeg manually from https://ffmpeg.org/download.html")
            return
        try:
            subprocess.check_call(["winget", "install", "--id=ffmpeg.ffmpeg", "-e"])
            logging.info("FFmpeg installation completed.")
        except Exception as e:
            logging.error(f"Failed to install FFmpeg via winget: {e}")

###############################################################################
# CONFIG
###############################################################################
HOST = '127.0.0.1'
PORT = 65432

# Text-file paths for configuration, word mappings, and fuzzy words
CONFIGURATION_SETTINGS_FILE = "settings.cfg"
FUZZY_WORDS_TEXT_FILE = "fuzzy_words.txt"
WORD_MAPPINGS_TEXT_FILE = "word_mappings.txt"

# Library to convert textual numbers to their numerical values
t2d = text2digits.Text2Digits()

###############################################################################
# ADMIN PRIVILEGES CHECK AND RE-LAUNCH
###############################################################################
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

if not is_admin():
    # Build a properly quoted command line from sys.argv
    params = " ".join(f'"{arg}"' for arg in sys.argv)
    ret = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, None, 1
    )
    if ret <= 32:
        print("Error: Failed to elevate privileges.")
        input("Press Enter to exit...")
    sys.exit()

# With admin rights confirmed, ensure FFmpeg is installed.
ensure_ffmpeg_installed()

# Use the system's temporary folder for the WAV file.
TEMP_DIR = tempfile.gettempdir()
AUDIO_FILE = os.path.join(TEMP_DIR, "whisper_temp_recording.wav")
SAMPLE_RATE = 16000

###############################################################################
# PHONETIC ALPHABET
###############################################################################
phonetic_alphabet = [
    "Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf",
    "Hotel", "India", "Juliet", "Kilo", "Lima", "Mike", "November",
    "Oscar", "Papa", "Quebec", "Romeo", "Sierra", "Tango", "Uniform",
    "Victor", "Whiskey", "X-ray", "Yankee", "Zulu",
]

###############################################################################
# FUZZY MATCH + CLEANUP
###############################################################################
def correct_dcs_and_phonetics_separately(
    text,
    dcs_list,
    phonetic_list,
    dcs_threshold=85,
    phonetic_threshold=80
):
    """
    Applies fuzzy matching for DCS callsigns and the phonetic alphabet.
    """
    tokens = text.split()
    corrected_tokens = []
    dcs_lower = [x.lower() for x in dcs_list]
    phon_lower = [x.lower() for x in phonetic_list]

    for token in tokens:
        if len(token) < 6:
            corrected_tokens.append(token)
            continue

        t_lower = token.lower()
        dcs_match = process.extractOne(t_lower, dcs_lower, score_cutoff=dcs_threshold)
        phon_match = process.extractOne(t_lower, phon_lower, score_cutoff=phonetic_threshold)
        best_token = token
        best_score = 0

        if dcs_match is not None:
            match_name_dcs, score_dcs, _ = dcs_match
            if score_dcs > best_score:
                best_score = score_dcs
                for orig in dcs_list:
                    if orig.lower() == match_name_dcs:
                        best_token = orig
                        break

        if phon_match is not None:
            match_name_phon, score_phon, _ = phon_match
            if score_phon > best_score:
                best_score = score_phon
                for orig in phonetic_list:
                    if orig.lower() == match_name_phon:
                        best_token = orig
                        break

        corrected_tokens.append(best_token)
    return " ".join(corrected_tokens)

def replace_word_mappings(word_mappings, text):
    """
    Replace transcribed words with custom words from their mapped values.
    """
    for word, replacement in word_mappings.items():
        pattern = rf"\b{re.escape(word)}\b"
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def custom_cleanup_text(text, word_mappings):
    """
    Performs several cleanup steps on the transcribed text.
    """
    text = unicodedata.normalize('NFC', text.strip())
    text = replace_word_mappings(word_mappings, text)
    text = t2d.convert(text)
    text = re.sub(r"(?<=\d)-(?=\d)", " ", text)
    text = re.sub(r'\b0\d+\b', lambda x: ' '.join(x.group()), text)
    text = re.sub(r"([^\w\s.])([\s-])", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

###############################################################################
# WHISPER SERVER
###############################################################################
class WhisperServer:
    def __init__(self):
        self.model = None
        self.recording = False
        self.audio_file = AUDIO_FILE
        self.wave_file = None
        self.stream = None
        self.stop_event = threading.Event()

        # Will be loaded from text files:
        self.config = {}
        self.dcs_airports = []
        self.word_mappings = {}

        # Location to the VoiceAttack executable
        self.voiceattack = None

        self.load_configuration()
        self.load_custom_word_files()
        self.load_whisper_model()

    def load_configuration(self):
        """
        Loads configuration settings.
        """
        if os.path.isfile(CONFIGURATION_SETTINGS_FILE):
            try:
                with open(CONFIGURATION_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        parts = line.split('=', maxsplit=1)
                        if len(parts) == 2:
                            source, target = parts
                            self.config[source.strip()] = target.strip()
                logging.info(f"Loaded configuration: {self.config}")
            except Exception as e:
                logging.error(f"Failed to load configuration settings from {CONFIGURATION_SETTINGS_FILE}: {e}")

        voiceattack_location = self.config.get("voiceattack_location", "")
        if os.path.isfile(voiceattack_location):
            self.voiceattack = voiceattack_location
        else:
            logging.error(f"VoiceAttack could not be located at: '{voiceattack_location}'")

    def load_custom_word_files(self):
        """
        Loads fuzzy words and word mappings from text files.
        """
        if os.path.isfile(WORD_MAPPINGS_TEXT_FILE):
            try:
                with open(WORD_MAPPINGS_TEXT_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        parts = line.split('=', maxsplit=1)
                        if len(parts) == 2:
                            aliases, target = parts
                            target = target.strip()
                            list(map(lambda alias: self.word_mappings.update({ alias: target }), aliases.split(';')))
                logging.info(f"Loaded word mappings: {self.word_mappings}")
            except Exception as e:
                logging.error(f"Failed to load word mappings from {WORD_MAPPINGS_TEXT_FILE}: {e}")
        else:
            logging.warning(f"{WORD_MAPPINGS_TEXT_FILE} not found; no custom word mappings loaded.")

        if os.path.isfile(FUZZY_WORDS_TEXT_FILE):
            try:
                with open(FUZZY_WORDS_TEXT_FILE, 'r', encoding='utf-8') as f:
                    self.dcs_airports = [
                        line.strip() for line in f
                        if line.strip() and not line.strip().startswith('#')
                    ]
                logging.info(f"Loaded fuzzy words: {self.dcs_airports}")
            except Exception as e:
                logging.error(f"Failed to load fuzzy words from {FUZZY_WORDS_TEXT_FILE}: {e}")
        else:
            logging.warning(f"{FUZZY_WORDS_TEXT_FILE} not found; fuzzy matching list is empty.")

    def load_whisper_model(self):
        """
        Loads the Whisper model.
        """
        whisper_model = self.config.get("whisper_model", "small.en")
        whisper_device = self.config.get("whisper_device", "CPU")
        logging.info(f"Loading Whisper model ({whisper_model}), device={whisper_device}")
        if whisper_device.upper() == "GPU" and torch.cuda.is_available():
            self.model = whisper.load_model(whisper_model).to('cuda')
        else:
            self.model = whisper.load_model(whisper_model).to('cpu')

    def start_recording(self):
        if self.recording:
            logging.warning("Already recording—ignoring start command.")
            return
        logging.info("Starting recording...")
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
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32',
            callback=audio_callback
        )
        self.stream.start()
        self.recording = True

    def stop_and_transcribe(self):
        if not self.recording:
            logging.warning("Not currently recording—ignoring stop command.")
            return
        logging.info("Stopping recording...")
        self.stream.stop()
        self.stream.close()
        self.stream = None
        self.wave_file.close()
        self.wave_file = None
        self.recording = False
        time.sleep(0.01)
        logging.info(f"Checking if file exists: {self.audio_file}")
        if os.path.exists(self.audio_file):
            size = os.path.getsize(self.audio_file)
            logging.info(f"File exists, size = {size} bytes")
        else:
            logging.error("File does NOT exist according to os.path.exists()!")
        recognized_text = self.transcribe_audio(self.audio_file)
        if recognized_text:
            self.send_to_voiceattack(recognized_text)
        else:
            logging.info("No transcription result.")

    def transcribe_audio(self, audio_path):
        try:
            logging.info(f"Transcribing {audio_path}...")
            result = self.model.transcribe(
                audio_path,
                language='en',
                suppress_tokens="0,11,13,30,986",
                initial_prompt=(
                    "This is aviation-related speech for DCS Digital Combat Simulator, "
                    "Expect references to airports in Caucasus Georgia and Russia. Expect callsigns like Enfield, Springfield, Uzi, Colt, Dodge, "
                    "Ford, Chevy, Pontiac, Army Air, Apache, Crow, Sioux, Gatling, Gunslinger, "
                    "Hammerhead, Bootleg, Palehorse, Carnivor, Saber, Hawg, Boar, Pig, Tusk, Viper, "
                    "Venom, Lobo, Cowboy, Python, Rattler, Panther, Wolf, Weasel, Wild, Ninja, Jedi, "
                    "Hornet, Squid, Ragin, Roman, Sting, Jury, Joker, Ram, Hawk, Devil, Check, Snake, "
                    "Dude, Thud, Gunny, Trek, Sniper, Sled, Best, Jazz, Rage, Tahoe, Bone, Dark, Vader, "
                    "Buff, Dump, Kenworth, Heavy, Trash, Cargo, Ascot, Overlord, Magic, Wizard, Focus, "
                    "Darkstar, Texaco, Arco, Shell, Axeman, Darknight, Warrior, Pointer, Eyeball, "
                    "Moonbeam, Whiplash, Finger, Pinpoint, Ferret, Shaba, Playboy, Hammer, Jaguar, "
                    "Deathstar, Anvil, Firefly, Mantis, Badger. Also expect usage of the phonetic "
                    "alphabet Alpha, Bravo, Charlie, X-ray. "
                )
            )
            raw_text = result["text"]
            logging.info(f"Raw transcription result: '{raw_text}'")
            if raw_text.strip() == "[BLANK_AUDIO]" or raw_text.strip() == "":
                return
            cleaned_text = custom_cleanup_text(raw_text, self.word_mappings)
            fuzzy_corrected_text = correct_dcs_and_phonetics_separately(
                cleaned_text,
                self.dcs_airports,
                phonetic_alphabet,
                dcs_threshold=85,
                phonetic_threshold=80
            )
            logging.info(f"Cleaned transcription: {cleaned_text}")
            logging.info(f"Fuzzy-corrected transcription: {fuzzy_corrected_text}")
            return fuzzy_corrected_text
        except Exception as e:
            logging.error(f"Failed to transcribe audio: {e}")
            return ""

    def send_to_voiceattack(self, text):
        """
        Sends the transcribed text to VoiceAttack or copies it to the clipboard
        if the text starts with the trigger phrase.
        """
        trigger_phrase = "note "
        if text.lower().startswith(trigger_phrase):
            text_for_kneeboard = text[5:].strip()
            pyperclip.copy(text_for_kneeboard)
            logging.info("Text copied to clipboard for DCS kneeboard.")
            try:
                keyboard.press_and_release('ctrl+alt+p')
                logging.info("DCS kneeboard populated")
            except Exception as e:
                logging.error(f"Failed to simulate keyboard shortcut: {e}")
            return
        if self.voiceattack is None:
            logging.error("VoiceAttack not found so command will not be sent")
            return
        try:
            logging.info(f"Sending recognized text to VoiceAttack: {text}")
            subprocess.call([self.voiceattack, '-command', text])
        except Exception as e:
            logging.error(f"Error calling VoiceAttack: {e}")

    def handle_command(self, cmd):
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
        logging.info(f"Starting socket server on {HOST}:{PORT}...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            s.settimeout(1.0)
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
        if self.recording:
            self.stop_and_transcribe()
        logging.info("Server has shut down cleanly.")

###############################################################################
# MAIN
###############################################################################
def main():
    server = WhisperServer()
    server.run_server()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        input("An unhandled exception occurred. Press Enter to exit...")
    else:
        input("Press Enter to exit...")
