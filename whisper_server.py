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
from faster_whisper import WhisperModel
import sounddevice as sd
import soundfile as sf
import pyperclip
import re
from rapidfuzz import process
from text2digits import text2digits
import pystray
from PIL import Image

# Set the working directory to the script's folder.
# NOTE: this is currently commented out as this breaks when run
# as an executable as it attempts to set this to the _internal directory,
# which does not contain the icon, settings.cfg, and other config files
# os.chdir(os.path.dirname(os.path.abspath(__file__)))

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

# Use the system's temporary folder for the WAV file.
TEMP_DIR = tempfile.gettempdir()
AUDIO_FILE = os.path.join(TEMP_DIR, "whisper_temp_recording.wav")

SAMPLE_RATE = 16000

# Logging
LOCAL_APPDATA_DIR = os.getenv('LOCALAPPDATA')
WHISPER_APPDATA_DIR = os.path.join(LOCAL_APPDATA_DIR , "WhisperAttack")
# Create the AppData directory for WhisterAttack if it does not already exist
os.makedirs(WHISPER_APPDATA_DIR, exist_ok=True)
LOG_FILE = os.path.join(WHISPER_APPDATA_DIR, "WhisperAttack.log")
logging.basicConfig(filename=LOG_FILE, filemode='w', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
                            source, target = parts
                            self.word_mappings[source.strip()] = target.strip()
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

    ###############################################################################
    # WHISPER LOADING
    ###############################################################################
    def load_whisper_model(self):
        """
        Load the Whisper model once. Return the model object.
        """
        whisper_model = self.config.get("whisper_model", "base")
        whisper_device = self.config.get("whisper_device", "CPU")
        logging.info(f"Loading Whisper model ({whisper_model}), device={whisper_device}")
        
        if whisper_device.upper() == "GPU":
            if torch.cuda.is_available():
                self.model = WhisperModel(whisper_model, device="cuda", compute_type="int8_float16")
                return
            else:
                logging.error("cuda not available so using CPU")
        
        self.model = WhisperModel(whisper_model, device="cpu", compute_type="int8")

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
            segments, info = self.model.transcribe(
                audio_path,
                language='en',
                beam_size=5,
                suppress_tokens=[0,11,13,30,986],
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

            raw_text = ""
            for segment in segments:
                raw_text += f"{segment.text}"

            logging.info(f"Raw transcription result: '{raw_text}'")

            # Ignore blank audio as nothing has been recorded
            if raw_text.strip() == "[BLANK_AUDIO]" or raw_text.strip() == "":
                return

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
        If text starts with the trigger phrase "note ", then:
          1) Remove that phrase from text
          2) Send ONLY to the kneeboard (not to VoiceAttack)
        Otherwise, send the text to VoiceAttack as usual
        """
        trigger_phrase = "note "

        # Check for trigger phrase in a case-insensitive manner
        if text.lower().startswith(trigger_phrase):
            # Strip out the phrase so it doesn't go anywhere else
            text_for_kneeboard = text[5:].strip()

            # Copy the resulting text to the clipboard
            pyperclip.copy(text_for_kneeboard)
            logging.info("Text copied to clipboard for DCS kneeboard.")

            # Simulate kneeboard hotkeys
            try:
                keyboard.press_and_release('ctrl+alt+p')
                logging.info("DCS kneeboard populated")
            except Exception as e:
                logging.error(f"Failed to simulate keyboard shortcut: {e}")

            # Do NOT send to VoiceAttack if trigger word "note " was used
            return

        if self.voiceattack is None:
            logging.error(f"VoiceAttack not found so command will not be sent")
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
            shut_down(icon)
        else:
            logging.warning(f"Unknown command: {cmd}")

    def run_server(self):
        logging.info(f"Server started and listening on {HOST}:{PORT}...")
        print(f"Server started and listening on {HOST}:{PORT}...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            s.settimeout(1.0)

            while not exit_event.is_set():
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

def startup(icon):
    # Display the system tray icon
    icon.visible = True
    # Start the WhisperAttack server
    server = WhisperServer()
    server.run_server()

def shut_down(icon):
    logging.info("Shutting down server...")
    print("Shutting down server...")
    # Stop the whisper server
    exit_event.set()
    icon.visible = False
    icon.stop()
    sys.exit()

###############################################################################
# MAIN
###############################################################################
def main():
     # This event is used to stop the loop.
    global exit_event
    exit_event = threading.Event()
    global icon

    image = Image.open("whisper_attack_icon.png")
    icon = pystray.Icon(
        "WA", image, "WhisperAttack",
        menu=pystray.Menu(pystray.MenuItem("Exit", shut_down))
    )
    # Start the system tray icon and pass it the whisper attack
    # startup callback handler to start the server running.
    icon.run(setup=startup)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Server error: {e}")
        import traceback
        traceback.print_exc()
        shut_down(icon)
