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
import re
from tkinter import Tk, scrolledtext, Button, Label, Entry, Toplevel, PhotoImage, font, LEFT, NORMAL, DISABLED, END, WORD, E, W, EW, NSEW
import traceback
import keyboard
import sounddevice as sd
import soundfile as sf
import pyperclip
from rapidfuzz import process
from text2digits import text2digits
from pystray import Icon, Menu, MenuItem
from PIL import Image
from pid import PidFile, PidFileError
import darkdetect

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

# This event is used to stop the the server socket and shutdown.
exit_event = threading.Event()

###############################################################################
# ADMIN PRIVILEGES CHECK AND RE-LAUNCH
###############################################################################
def is_admin() -> bool:
    """
    Returns true if the user has admin privileges to run WhisperAttack.
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

if not is_admin():
    # Build a properly quoted command line from sys.argv
    PARAMS = " ".join(f'"{arg}"' for arg in sys.argv)
    ret = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, PARAMS, None, 1
    )
    if ret <= 32:
        print("Error: Failed to elevate privileges.")
        input("Press Enter to exit...")
    sys.exit()

# Use the system's temporary folder for the WAV file.
TEMP_DIR = tempfile.gettempdir()
AUDIO_FILE = os.path.join(TEMP_DIR, "whisper_temp_recording.wav")
SAMPLE_RATE = 16000

LOCAL_APPDATA_DIR = os.getenv('LOCALAPPDATA')
WHISPER_APPDATA_DIR = os.path.join(LOCAL_APPDATA_DIR , "WhisperAttack")
# Create the AppData directory for WhisterAttack if it does not already exist
os.makedirs(WHISPER_APPDATA_DIR, exist_ok=True)

def start_logging() -> None:
    """
    Start logging to the %LOCALAPPDATA%\WhisperAttack directory.
    """
    log_file = os.path.join(WHISPER_APPDATA_DIR, "WhisperAttack.log")
    logging.basicConfig(
        filename=log_file,
        filemode='w',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

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
    text: str,
    dcs_list: list[str],
    phonetic_list: list[str],
    dcs_threshold=85,
    phonetic_threshold=85
) -> str:
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

def replace_word_mappings(word_mappings: dict[str, str], text: str) -> str:
    """
    Replace transcribed words with custom words from their mapped values.
    """
    for word, replacement in word_mappings.items():
        pattern = rf"\b{re.escape(word)}\b"
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def custom_cleanup_text(text: str, word_mappings: dict[str, str]) -> str:
    """
    Performs several cleanup steps on the transcribed text.
    """
    text = unicodedata.normalize('NFC', text.strip())
    text = replace_word_mappings(word_mappings, text)
    text = t2d.convert(text)
    text = re.sub(r"(?<=\d)-(?=\d)", " ", text)
    text = re.sub(r'\b0\d+\b', lambda x: ' '.join(x.group()), text)
    text = re.sub(r"([^\w\d\s])*(?![\w\-\w])(?![^-])?", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

###############################################################################
# WHISPER SERVER
###############################################################################
class WhisperServer:
    """
    Class that runs a socket server to listen for incoming commands.
    Commands will start or stop the recording of audio to a wav file.
    Once recording has stopped the audio will be transcribed to text and
    sent to either VoiceAttack or the DCS kneeboard.
    """
    def __init__(self, config: dict[str, str], writer):
        self.writer = writer
        self.model = None
        self.recording = False
        self.audio_file = AUDIO_FILE
        self.wave_file = None
        self.stream = None

        # Will be loaded from text files:
        self.dcs_airports = []
        self.word_mappings = {}

        # Location to the VoiceAttack executable
        self.voiceattack = self.get_voiceattack(config)

        self.load_word_mappings()
        self.load_fuzzy_words()
        self.load_whisper_model(config)

    def get_voiceattack(self, config) -> str | None:
        """
        Returns the path to the VoiceAttack executable after validating
        that it is present at the location specified in the configuration.
        """
        voiceattack_location = config.get("voiceattack_location", "")
        if os.path.isfile(voiceattack_location):
            return voiceattack_location
        logging.error("VoiceAttack could not be located at: '%s'", voiceattack_location)
        self.writer.write(f"VoiceAttack could not be located at: '{voiceattack_location}'", TAG_RED)
        return None

    def load_word_mappings(self) -> None:
        """
        Loads word mappings from text files.
        """
        self.word_mappings = {}
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
                logging.info("Loaded word mappings: %s", self.word_mappings)
                self.writer.write("Loaded word mappings:", TAG_BLUE)
                self.writer.write_dict(self.word_mappings, TAG_GREY)
            except Exception as e:
                logging.error("Failed to load word mappings from %s: %s", WORD_MAPPINGS_TEXT_FILE, e)
                self.writer.write(f"Failed to load word mappings from {WORD_MAPPINGS_TEXT_FILE}: {e}", TAG_RED)
        else:
            logging.warning("%s not found; no custom word mappings loaded.", WORD_MAPPINGS_TEXT_FILE)
            self.writer.write(f"{WORD_MAPPINGS_TEXT_FILE} not found; no custom word mappings loaded.", TAG_ORANGE)

    def load_fuzzy_words(self) -> None:
        """
        Loads fuzzy words from text files.
        """
        if os.path.isfile(FUZZY_WORDS_TEXT_FILE):
            try:
                with open(FUZZY_WORDS_TEXT_FILE, 'r', encoding='utf-8') as f:
                    self.dcs_airports = [
                        line.strip() for line in f
                        if line.strip() and not line.strip().startswith('#')
                    ]
                self.writer.write("Loaded fuzzy words:", TAG_BLUE)
                self.writer.write(f"{self.dcs_airports}", TAG_GREY)
            except Exception as e:
                logging.error("Failed to load fuzzy words from %s: %s", FUZZY_WORDS_TEXT_FILE, e)
                self.writer.write(f"Failed to load fuzzy words from {FUZZY_WORDS_TEXT_FILE}: {e}", TAG_RED)
        else:
            logging.warning("%s not found; fuzzy matching list is empty.", FUZZY_WORDS_TEXT_FILE)
            self.writer.write(f"{FUZZY_WORDS_TEXT_FILE} not found; fuzzy matching list is empty.", TAG_ORANGE)

    def load_whisper_model(self, config) -> None:
        """
        Loads the Whisper model.
        """
        whisper_model = config.get("whisper_model", "small.en")
        whisper_device = config.get("whisper_device", "CPU")
        whisper_core_type = config.get("whisper_core_type", "tensor")
        logging.info("Loading Whisper model (%s), device=%s, core_type=%s ...", whisper_model, whisper_device, whisper_core_type)
        self.writer.write(f"Loading Whisper model ({whisper_model}), device={whisper_device} ...")
        import torch
        from faster_whisper import WhisperModel
        
        if whisper_device.upper() == "GPU":
            if torch.cuda.is_available():
                compute_type = "int8_float16"
                if whisper_core_type.lower() == "standard":
                    compute_type = "int8"
                device = torch.device("cuda")
                capability = torch.cuda.get_device_capability(device)
                major, minor = capability
                logging.info("GPU has cuda capability major=%s minor=%s", major, minor)
                # Tensor Cores are available on devices with compute capability 7.0 or higher
                if whisper_core_type.lower() == "tensor" and major < 7:
                    logging.warning("GPU does not have tensor cores, major=%s, minor=%s", major, minor)
                    compute_type = "int8"
                self.model = WhisperModel(whisper_model, device="cuda", compute_type=compute_type)
                logging.info('Successfully loaded Whisper model')
                self.writer.write('Successfully loaded Whisper model', TAG_GREEN)
                return None
            logging.error("cuda not available so using CPU")
            self.writer.write("cuda not available so using CPU", TAG_RED)
        self.model = WhisperModel(whisper_model, device="cpu", compute_type="int8")
        return None
    
    def add_word_mapping(self, aliases: str, replacement: str) -> None:
        """
        Adds a new alias and replacement to the word mappings
        """
        if aliases.strip() == "":
            return None

        list(map(lambda alias: self.word_mappings.update({ alias: replacement }), aliases.split(';')))
        if os.path.isfile(WORD_MAPPINGS_TEXT_FILE):
            try:
                with open(WORD_MAPPINGS_TEXT_FILE, 'a', encoding='utf-8') as f:
                    f.write(f"\n{aliases}={replacement}")
                    f.close()
                logging.info("Added aliases: %s", aliases)
                logging.info("Added replacement: %s", replacement)
                self.writer.write("Added new word mapping", TAG_BLUE)
                self.writer.write(f"{aliases}: {replacement}", TAG_GREY)
            except Exception as e:
                logging.error("Failed to add new word mapping to %s: %s", WORD_MAPPINGS_TEXT_FILE, e)
                self.writer.write(f"Failed to add new word mapping to {WORD_MAPPINGS_TEXT_FILE}: {e}", TAG_RED)
        else:
            logging.warning("%s not found; no custom word mappings loaded.", WORD_MAPPINGS_TEXT_FILE)
            self.writer.write(f"{WORD_MAPPINGS_TEXT_FILE} not found; no custom word mappings loaded.", TAG_ORANGE)

    def start_recording(self) -> None:
        """
        Begin recording to a wav file.
        """
        if self.recording:
            logging.info("Already recording—ignoring start command.")
            self.writer.write("Already recording—ignoring start command", TAG_ORANGE)
            return None
        logging.info("Starting recording...")
        self.writer.write("Starting recording...", TAG_GREY)
        self.wave_file = sf.SoundFile(
            self.audio_file,
            mode='w',
            samplerate=SAMPLE_RATE,
            channels=1,
            subtype='FLOAT'
        )
        def audio_callback(indata, _frames, _time_info, status):
            if status:
                logging.info("Audio Status: %s", status)
            self.wave_file.write(indata)
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32',
            callback=audio_callback
        )
        self.stream.start()
        self.recording = True
        return None

    def stop_and_transcribe(self) -> None:
        """
        Stops the currently running recording to then have this transcribed.
        """
        if not self.recording:
            logging.warning("Not currently recording—ignoring stop command.")
            self.writer.write("Not currently recording—ignoring stop command", TAG_ORANGE)
            return None
        logging.info("Stopping recording...")
        self.writer.write("Stopped recording", TAG_GREY)
        self.stream.stop()
        self.stream.close()
        self.stream = None
        self.wave_file.close()
        self.wave_file = None
        self.recording = False
        time.sleep(0.01)
        logging.info("Checking if file exists: %s", self.audio_file)
        if os.path.exists(self.audio_file):
            size = os.path.getsize(self.audio_file)
            logging.info("File exists, size = %s bytes", size)
        else:
            logging.error(("File does NOT exist according to os.path.exists()!"))
            self.writer.write("File does NOT exist according to os.path.exists()!", TAG_RED)
        recognized_text = self.transcribe_audio(self.audio_file)
        if recognized_text:
            self.send_to_voiceattack(recognized_text)
        else:
            logging.info("No transcription result.")
            self.writer.write("No transcription result", TAG_GREY)
        return None

    def transcribe_audio(self, audio_path: str) -> str | None:
        """
        Transcribes the recorded audio to text and then returns the final result
        after running it through functions to cleanup the raw text.
        """
        try:
            logging.info("Transcribing %s...", audio_path)
            segments, _ = self.model.transcribe(
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
                    "alphabet Alpha, Bravo, Charlie, X-ray."
                )
            )

            raw_text = ""
            for segment in segments:
                raw_text += f"{segment.text}"

            logging.info("Raw transcription result: '%s'", raw_text)
            self.writer.write(f"Raw transcribed text: '{raw_text}'", TAG_BLUE)
            # Ignore blank audio as nothing has been recorded
            if raw_text.strip() == "[BLANK_AUDIO]" or raw_text.strip() == "":
                return None
            cleaned_text = custom_cleanup_text(raw_text, self.word_mappings)
            fuzzy_corrected_text = correct_dcs_and_phonetics_separately(
                cleaned_text,
                self.dcs_airports,
                phonetic_alphabet,
                dcs_threshold=85,
                phonetic_threshold=85
            )
            logging.info("Cleaned transcription: %s", cleaned_text)
            logging.info("Fuzzy-corrected transcription: %s", fuzzy_corrected_text)
            return fuzzy_corrected_text
        except Exception as e:
            logging.error("Failed to transcribe audio: %s", e)
            self.writer.write(f"Failed to transcribe audio: {e}", TAG_RED)
            return None

    def send_to_voiceattack(self, text: str) -> None:
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
                self.writer.write(f"Sent text to DCS: {text_for_kneeboard}", TAG_GREEN)
                logging.info("DCS kneeboard populated")
            except Exception as e:
                logging.error("Failed to simulate keyboard shortcut: %s", e)
                self.writer.write(f"Failed to simulate keyboard shortcut: {e}", TAG_RED)

            # Do NOT send to VoiceAttack if trigger word "note " was used
            return
        if self.voiceattack is None:
            logging.error("VoiceAttack not found so command will not be sent")
            self.writer.write("VoiceAttack not found so command will not be sent", TAG_RED)
            return
        try:
            logging.info("Sending recognized text to VoiceAttack: %s", text)
            subprocess.call([self.voiceattack, '-command', text])
            self.writer.write(f"Sent text to VoiceAttack: {text}", TAG_GREEN)
        except Exception as e:
            logging.error("Error calling VoiceAttack: %s", e)
            self.writer.write(f"Error calling VoiceAttack: {e}", TAG_RED)

    def handle_command(self, cmd: str) -> None:
        """
        Triggers the operation for the associated command that was received.
        """
        cmd = cmd.strip().lower()
        logging.info("Received command: %s", cmd)
        if cmd == "start":
            self.start_recording()
        elif cmd == "stop":
            self.stop_and_transcribe()
        elif cmd == "shutdown":
            logging.info("Received shutdown command. Stopping server...")
            self.writer.write("Received shutdown command. Stopping server...")
            shut_down(icon)
        else:
            logging.warning("Unknown command: %s", cmd)
            self.writer.write(f"Unknown command: {cmd}", TAG_ORANGE)

    def run_server(self) -> None:
        """
        Starts a socket server and listens for incoming commands.
        """
        logging.info("Server started and listening on %s:%s", HOST, PORT)
        self.writer.write(f"Server started and listening on {HOST}:{PORT}", TAG_GREEN)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            s.settimeout(1.0)

            while not exit_event.is_set():
                try:
                    conn, _ = s.accept()
                    with conn:
                        data = conn.recv(1024).decode('utf-8')
                        if data:
                            self.handle_command(data)
                except socket.timeout:
                    continue
                except Exception as e:
                    logging.error("Socket error: %s", e)
                    self.writer.write(f"Socket error: {e}", TAG_RED)
                    continue
        if self.recording:
            self.stop_and_transcribe()

        logging.info("Server has shut down cleanly.")
        self.writer.write("Server has shut down cleanly.")

TAG_BLACK = 'black'
TAG_BLUE = 'blue'
TAG_GREEN = 'green'
TAG_GREY = 'grey'
TAG_ORANGE = 'orange'
TAG_RED = 'red'

THEME_DEFAULT = 'default'
THEME_DARK = 'dark'
THEME_LIGHT = 'light'

theme_config = {
    THEME_DARK: {
        TAG_BLACK: 'light grey',
        TAG_BLUE: '#7289DA',
        TAG_GREEN: '#4E9D4E',
        TAG_GREY: 'grey',
        TAG_ORANGE: '#FF981F',
        TAG_RED: '#F04747',
        'background': '#36393E'
    },
    THEME_LIGHT: {
        TAG_BLACK: 'black',
        TAG_BLUE: 'blue',
        TAG_GREEN: 'green',
        TAG_GREY: 'grey',
        TAG_ORANGE: 'orange',
        TAG_RED: 'red',
        'background': 'white'
    }
}

class ConfigurationError(Exception):
    """
    Basic exception class for errors loading configuration
    """

class WhisperAttack:
    """
    Class for the main WhisperAttack application.
    """
    def __init__(self, root: Tk):
        start_logging()

        self.config = self.load_configuration()
        self.root = root
        self.root.title("WhisperAttack")

        theme = self.get_theme()
        
        custom_font = font.Font(family="GG Sans", size=11)
        text_area = scrolledtext.ScrolledText(
            self.root,
            wrap=WORD,
            width=100,
            height=50,
            state=DISABLED
        )
        text_area.grid(row=0, column=0, sticky=NSEW, padx=10, pady=10)
        text_area.configure(bg=theme_config[theme]['background'], font=custom_font)

        self.add_icon = PhotoImage(file="add_icon.png")
        word_mappings_add_button = Button(
            self.root,
            font=custom_font,
            text="Add word mapping",
            image=self.add_icon,
            compound=LEFT,
            padx=5, pady=5,
            command=self.add_word_mapping
        )
        word_mappings_add_button.grid(row=1, column=0, sticky=W, pady=10, padx=10)

        self.reload_icon = PhotoImage(file="reload_icon.png")
        word_mappings_reload_button = Button(
            self.root,
            font=custom_font,
            text="Reload word mappings",
            image=self.reload_icon,
            compound=LEFT,
            padx=5, pady=5,
            command=self.reload_word_mappings
        )
        word_mappings_reload_button.grid(row=1, column=0, sticky=E, pady=10, padx=10)

        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)

        self.writer = WhisperAttackWriter(theme, text_area)
        self.writer.write("Loaded configuration:", TAG_BLUE)
        self.writer.write_dict(self.config, TAG_GREY)

        self.whisper_server = WhisperServer(self.config, self.writer)

        threading.excepthook = self.handle_exception
        threading.Thread(daemon=True, target=lambda: icon.run(setup=self.startup)).start()

    def load_configuration(self) -> dict[str, str]:
        """
        Loads configuration settings.
        """
        config = {}
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
                            config[source.strip()] = target.strip()
            except Exception as e:
                logging.error("Failed to load configuration settings from %s: %s", CONFIGURATION_SETTINGS_FILE, e)
                self.writer.write(f"Failed to load configuration settings from {CONFIGURATION_SETTINGS_FILE}: {e}", TAG_RED)
        else:
            raise ConfigurationError("The configuration settings.cfg file could not be found")

        logging.info("Loaded configuration: %s", config)
        return config
    
    def add_word_mapping(self) -> None:
        WhisperAttackWordMappings(self.root, self.whisper_server, self.writer)
    
    def reload_word_mappings(self) -> None:
        """
        Call the WhisperServer function to reload the word mappings.
        """
        self.whisper_server.load_word_mappings()

    def get_theme(self) -> str:
        """
        Returns the name of the theme to be used when displaying
        UI elements. When the configuration is set to "default" then
        the name returned will be the current Windows theme.
        """
        theme = self.config.get("theme", THEME_DEFAULT)
        if theme == THEME_DEFAULT:
            return darkdetect.theme().lower()
        return theme

    def startup(self, _icon) -> None:
        """
        Start the WhisperAttack server.
        """
        icon.visible = True
        self.whisper_server.run_server()

    def handle_exception(self, args) -> None:
        """
        Handle errors from the Whisper Server thread
        """
        trace = traceback.format_exc()
        logging.error("Server error: %s\n\n%s", args.exc_value, trace)
        open_modal(f"Unexpected server error: {args.exc_value}")
        shut_down(icon)

class WhisperAttackWriter:
    """
    A class used to write to the text area within the WhisperAttack window.
    """
    def __init__(self, theme: str, text_area: scrolledtext.ScrolledText):
        self.text_area = text_area
        style = theme_config[theme]
        self.text_area.tag_configure(TAG_BLACK, foreground=style[TAG_BLACK])
        self.text_area.tag_configure(TAG_BLUE, foreground=style[TAG_BLUE])
        self.text_area.tag_configure(TAG_GREEN, foreground=style[TAG_GREEN])
        self.text_area.tag_configure(TAG_GREY, foreground=style[TAG_GREY])
        self.text_area.tag_configure(TAG_ORANGE, foreground=style[TAG_ORANGE])
        self.text_area.tag_configure(TAG_RED, foreground=style[TAG_RED])

    def write(self, text: str, tag = TAG_BLACK) -> None:
        """
        Write a line to the text area.
        This sets the state to NORMAL so that it is writable then
        sets to DISABLED afterwards so that the text area is readonly
        """
        self.text_area.config(state=NORMAL)
        self.text_area.insert(END, text + "\n", tag)
        self.text_area.see(END)
        self.text_area.config(state=DISABLED)

    def write_dict(self, dictionary: dict[str, str], tag = TAG_BLACK) -> None:
        """
        Write the dictionary as a formatted set of keys and values.
        """
        for key, value in dictionary.items():
            self.write(f"{key}: {value}", tag)

class WhisperAttackWordMappings:
    """
    A class used to display a UI and handle the adding of new word mappings.
    """
    def __init__(self, root: Tk, whisper_server: WhisperServer, writer: WhisperAttackWriter):
        self.whisper_server = whisper_server
        self.writer = writer

        modal = Toplevel(root)
        modal.title = "Add word mapping"
        modal_width = 400
        modal_height = 120
        modal.geometry(f"{modal_width}x{modal_height}")
        modal.transient(root)
        modal.grab_set()
        # Center the modal over the parent window
        parent_x = root.winfo_x()
        parent_y = root.winfo_y()
        parent_width = root.winfo_width()
        parent_height = root.winfo_height()
        x = parent_x + (parent_width // 2) - (modal_width // 2)
        y = parent_y + (parent_height // 2) - (modal_height // 2)
        modal.geometry(f"{modal_width}x{modal_height}+{x}+{y}")

        Label(modal, text="Aliases").grid(row=0, sticky=E, padx=5)
        Label(modal, text="Replacement").grid(row=1, sticky=E, padx=5)

        modal.columnconfigure(1, weight=1)
        aliases_entry = Entry(modal)
        replacement_entry = Entry(modal)
        aliases_entry.grid(row=0, column=1, sticky=EW, padx=10, pady=10)
        replacement_entry.grid(row=1, column=1, sticky=EW, padx=10, pady=10)

        def add_word_mapping() -> None:
            aliases = aliases_entry.get()
            replacement = replacement_entry.get()
            self.whisper_server.add_word_mapping(aliases,replacement)
            modal.destroy()

        Button(modal, text="Cancel", command=modal.destroy).grid(row=3, column=0, sticky=W, padx=10, pady=5)
        Button(modal, text="Ok", command=add_word_mapping).grid(row=3, column=1, sticky=E, padx=10, pady=5)

def shut_down(_icon) -> None:
    """
    Shutdown the Whisper server and then exit the application.
    """
    logging.info("Shutting down server...")
    exit_event.set()
    icon.visible = False
    icon.stop()
    window.destroy()

def show_window(_icon, _item) -> None:
    """
    Show the window from the system tray.
    """
    window.after(0, window.deiconify)

def withdraw_window() -> None:
    """
    Hide the window when closed, returns it to the system tray.
    """
    window.withdraw()

def open_modal(message: str) -> None:
    """
    Open a modal dialog to display messages.
    """
    modal = Toplevel(window)
    modal.title("WhisperAttack")
    modal.geometry("800x300")
    label = Label(modal, text=message)
    label.pack(pady=20)
    close_button = Button(modal, text="Close", command=modal.destroy)
    close_button.pack(pady=10)
    modal.transient(window)
    modal.grab_set()
    window.wait_window(modal)

# The WhisperAttack window
window = Tk()
window.protocol('WM_DELETE_WINDOW', withdraw_window)

# The Whisper system tray icon
image = Image.open("whisper_attack_icon.png")
icon = Icon(
    "WA", image, "WhisperAttack",
    menu=Menu(MenuItem("Show", show_window), MenuItem("Exit", shut_down))
)

###############################################################################
# MAIN
###############################################################################
def main():
    """
    Run the WhisperAttack application.
    This is run using a lock file so that only one instance
    can be run at a time.
    """
    # Lock file to create to prevent multiple instances being run
    lock_file = os.path.join(WHISPER_APPDATA_DIR, 'whisper_attack')
    with PidFile(lock_file):
        WhisperAttack(window)
        window.mainloop()

if __name__ == "__main__":
    try:
        main()
    except PidFileError as pid_error:
        # Error means possibly another instance of application
        # is already running, this second attempt will be killed.
        open_modal("WhisperAttack is already running")
    except Exception as e:
        TRACE = traceback.format_exc()
        logging.error("Server error: %s\n\n%s", e, TRACE)
        open_modal(f"Unexpected server error: {e}")
        shut_down(icon)
