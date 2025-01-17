import sys
import subprocess
import pkg_resources

# ------------- AUTO-INSTALL MISSING DEPENDENCIES -------------
REQUIRED_PACKAGES = [
    "whisper",
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
    installed_packages = {pkg.key for pkg in pkg_resources.working_set}
    missing = []
    for package in REQUIRED_PACKAGES:
        # For case-insensitivity in package name checks
        # e.g., SoundFile is listed as soundfile in 'installed_packages'
        if package.lower() not in installed_packages:
            missing.append(package)

    if missing:
        print(f"Installing missing packages: {missing}")
        python_exe = sys.executable
        subprocess.check_call(
            [python_exe, "-m", "pip", "install", "--upgrade"] + missing
        )
    else:
        print("All required packages are already installed.")

# Attempt to install missing packages
install_missing_packages()

# Now that we've attempted to install them, re-import everything
# to ensure they’re actually present in the current session.
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
from rapidfuzz import process
from text2digits import text2digits

###############################################################################
# CONFIG
###############################################################################
HOST = '127.0.0.1'
PORT = 65432

# Text-file paths for fuzzy words + word mappings
FUZZY_WORDS_TEXT_FILE = "fuzzy_words.txt"
WORD_MAPPINGS_TEXT_FILE = "word_mappings.txt"

# Library to convert textual numbers to their numerical values
t2d = text2digits.Text2Digits()

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
    Applies fuzzy matching for your loaded DCS callsigns (dcs_list)
    and the phonetic_alphabet. Each token is compared to both lists.
    Whichever is the best match wins.
    """
    tokens = text.split()
    corrected_tokens = []

    dcs_lower = [x.lower() for x in dcs_list]
    phon_lower = [x.lower() for x in phonetic_list]

    for token in tokens:
        # If it's super short, skip
        if len(token) < 3:
            corrected_tokens.append(token)
            continue

        t_lower = token.lower()

        dcs_match = process.extractOne(
            t_lower, dcs_lower, score_cutoff=dcs_threshold
        )
        phon_match = process.extractOne(
            t_lower, phon_lower, score_cutoff=phonetic_threshold
        )

        best_token = token
        best_score = 0

        # Check DCS match
        if dcs_match is not None:
            match_name_dcs, score_dcs, _ = dcs_match
            if score_dcs > best_score:
                best_score = score_dcs
                for orig in dcs_list:
                    if orig.lower() == match_name_dcs:
                        best_token = orig
                        break

        # Check phonetic match
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
    Replace transcribed words with custom words from their
    mapped values. (E.g., "gulf" -> "Golf", "tawa" -> "Tower")
    Uses case-insensitive matching on word boundaries.
    """
    for word, replacement in word_mappings.items():
        pattern = rf"\b{re.escape(word)}\b"
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def custom_cleanup_text(text, word_mappings):
    """
    1. Normalize the text.
    2. Replace words with custom mapped values.
    3. Remove punctuation except periods.
    4. Remove extra spaces between digits.
    5. Remove extra whitespace.
    """
    # Normalize unicode
    text = unicodedata.normalize('NFC', text.strip())

    # Replace words with custom terms
    text = replace_word_mappings(word_mappings, text)

    # Convert textual numbers to their numerical value.
    # "500 thousand two hundred and ninety four" => 500294
    text = t2d.convert(text)

    # Replace dashes between digits with spaces (e.g., "1-2" => "1 2")
    text = re.sub(r"(?<=\d)-(?=\d)", " ", text)

    # This regex finds numbers that start with '0' and adds spaces between each digit
    text = re.sub(r'\b0\d+\b', lambda x: ' '.join(x.group()), text)
    
    # Remove any non-word (a-z0-9_) and non-space characters except periods
    text = re.sub(r"[^\w\s.]", "", text)

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

        # Will be loaded from text files:
        self.dcs_airports = []
        self.word_mappings = {}

        # Load data from the text files
        self.load_custom_word_files()

    def load_custom_word_files(self):
        """
        Loads:
          - Fuzzy words (DCS callsigns, airports, etc.) from fuzzy_words.txt
          - Word mappings (e.g., "zero=0", "tawa=Tower") from word_mappings.txt
        """

        # 1) Load word mappings
        if os.path.isfile(WORD_MAPPINGS_TEXT_FILE):
            try:
                with open(WORD_MAPPINGS_TEXT_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines or commented lines
                        if not line or line.startswith('#'):
                            continue
                        # Must be "source=target"
                        parts = line.split('=', maxsplit=1)
                        if len(parts) == 2:
                            source, target = parts
                            self.word_mappings[source.strip()] = target.strip()
                logging.info(f"Loaded word mappings: {self.word_mappings}")
            except Exception as e:
                logging.error(f"Failed to load word mappings from {WORD_MAPPINGS_TEXT_FILE}: {e}")
        else:
            logging.warning(f"{WORD_MAPPINGS_TEXT_FILE} not found; no custom word mappings loaded.")

        # 2) Load fuzzy words
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
            # Less directive prompt => doesn't forcibly push phonetic expansions:
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
            logging.info(f"Raw transcription result: {raw_text}")

            # Step 1: general cleanup
            cleaned_text = custom_cleanup_text(raw_text, self.word_mappings)

            # Step 2: partial fuzzy match for your loaded DCS words + phonetic
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
        If text contains the trigger phrase "copy", then:
          1) Remove that phrase from text
          2) Send ONLY to the kneeboard (not to VoiceAttack)
        Otherwise, send the text to VoiceAttack as usual
        """

        trigger_phrase = "copy"

        # Check for trigger phrase in a case-insensitive manner
        if trigger_phrase in text.lower():
            # Strip out the phrase so it doesn't go anywhere else
            pattern = re.compile(re.escape(trigger_phrase), re.IGNORECASE)
            text_for_kneeboard = pattern.sub("", text).strip()

            # Copy the resulting text to the clipboard
            pyperclip.copy(text_for_kneeboard)
            logging.info("Text copied to clipboard for kneeboard.")

            # Simulate kneeboard hotkeys
            try:
                keyboard.press_and_release('ctrl+alt+p')
                logging.info("DCS Kneeboard Populated")
            except Exception as e:
                logging.error(f"Failed to simulate keyboard shortcut: {e}")

            # Do NOT send to VoiceAttack if "write this down" was used
            return

        # If no "write this down" phrase, proceed normally
        if os.path.isfile(VOICEATTACK_EXE):
            try:
                logging.info(f"Sending recognized text to VoiceAttack: {text}")
                subprocess.call([VOICEATTACK_EXE, '-command', text])
            except Exception as e:
                logging.error(f"Error calling VoiceAttack: {e}")
        else:
            logging.warning(f"VoiceAttack.exe not found at: {VOICEATTACK_EXE}")

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
    model = load_whisper_model(device='GPU', model_size='small.en')
    server = WhisperServer(model, device='GPU')
    server.run_server()

if __name__ == "__main__":
    main()
