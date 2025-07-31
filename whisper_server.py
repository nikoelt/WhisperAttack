import os
import socket
import time
import logging
import subprocess
import unicodedata
import tempfile
import re
from threading import Event
from typing import Callable
import keyboard
import sounddevice as sd
import soundfile as sf
import pyperclip
from rapidfuzz import process
from text2digits import text2digits
from configuration import WhisperAttackConfiguration
from writer import WhisperAttackWriter
from theme import TAG_BLUE, TAG_GREEN, TAG_GREY, TAG_ORANGE, TAG_RED

###############################################################################
# CONFIG
###############################################################################
HOST = '127.0.0.1'
PORT = 65432

# Library to convert textual numbers to their numerical values
t2d = text2digits.Text2Digits()

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
    def __init__(self, config: WhisperAttackConfiguration, writer: WhisperAttackWriter, shutdown: Callable, exit_event: Event):
        self.config = config
        self.writer = writer
        self.exit_event = exit_event
        self.shutdown = shutdown
        self.model = None
        self.recording = False
        self.audio_file = AUDIO_FILE
        self.wave_file = None
        self.stream = None

        self.voiceattack = self.config.get_voiceattack()

    def load_whisper_model(self, config: WhisperAttackConfiguration) -> None:
        """
        Loads the Whisper model.
        """
        whisper_model = config.get_whisper_model()
        whisper_device = config.get_whisper_device()
        whisper_compute_type = config.get_whisper_compute_type()
        whisper_core_type = config.get_whisper_core_type()
        self.writer.write(f"Loading Whisper model ({whisper_model}), device={whisper_device} ...")
        import torch
        from faster_whisper import WhisperModel

        if whisper_device.upper() == "GPU":
            if torch.cuda.is_available():
                compute_type = whisper_compute_type
                if whisper_core_type.lower() == "standard":
                    compute_type = "int8"
                    logging.info("whisper_core_type is 'standard' so using compute_type '%s'", compute_type)
                device = torch.device("cuda")
                capability = torch.cuda.get_device_capability(device)
                major, minor = capability
                logging.info("GPU has cuda capability major=%s minor=%s", major, minor)
                # Tensor Cores are available on devices with compute capability 7.0 or higher
                if whisper_core_type.lower() == "tensor" and major < 7:
                    compute_type = "int8"
                    logging.warning("GPU does not have tensor cores, major=%s, minor=%s so using compute_type '%s'", major, minor, compute_type)
                logging.info("Loading Whisper model (%s), device=%s, core_type=%s, compute_type=%s ...", whisper_model, whisper_device, whisper_core_type, compute_type)
                self.model = WhisperModel(whisper_model, device="cuda", compute_type=compute_type)
                logging.info('Successfully loaded Whisper model')
                self.writer.write('Successfully loaded Whisper model', TAG_GREEN)
                return None

            logging.error("cuda not available so using CPU")
            self.writer.write("cuda not available so using CPU", TAG_RED)

        compute_type = "int8"
        logging.info("Loading Whisper model (%s), device=%s, compute_type=%s ...", whisper_model, "cpu", compute_type)
        self.model = WhisperModel(whisper_model, device="cpu", compute_type=compute_type)
        return None

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
            cleaned_text = custom_cleanup_text(raw_text, self.config.get_word_mappings())
            fuzzy_corrected_text = correct_dcs_and_phonetics_separately(
                cleaned_text,
                self.config.get_fuzzy_words(),
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
            self.shutdown()
        else:
            logging.warning("Unknown command: %s", cmd)
            self.writer.write(f"Unknown command: {cmd}", TAG_ORANGE)

    def run_server(self) -> None:
        """
        Starts a socket server and listens for incoming commands.
        """
        self.load_whisper_model(self.config)

        logging.info("Server started and listening on %s:%s", HOST, PORT)
        self.writer.write(f"Server started and listening on {HOST}:{PORT}", TAG_GREEN)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            s.settimeout(1.0)

            while not self.exit_event.is_set():
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
