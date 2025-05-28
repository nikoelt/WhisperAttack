import os
import logging
from theme import THEME_DEFAULT

# Text-file paths for configuration, word mappings, and fuzzy words
CONFIGURATION_SETTINGS_FILE = "settings.cfg"
FUZZY_WORDS_TEXT_FILE = "fuzzy_words.txt"
WORD_MAPPINGS_TEXT_FILE = "word_mappings.txt"

class ConfigurationError(Exception):
    """
    Basic exception class for errors loading configuration
    """

class WhisperAttackConfiguration:
    """
    A class to read and write the WhisperAttack configuration
    """
    def __init__(self):
        self.config = self.load_configuration()
        self.word_mappings = self.load_word_mappings()
        self.fuzzy_words = self.load_fuzzy_words()

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
        else:
            raise ConfigurationError("The configuration settings.cfg file could not be found")

        logging.info("Loaded configuration: %s", config)
        return config
    
    def get_configuration(self) -> dict[str, str]:
        """
        Return the full configuration
        """
        return self.config
    
    def get_voiceattack(self) -> str | None:
        """
        Returns the path to the VoiceAttack executable after validating
        that it is present at the location specified in the configuration.
        """
        voiceattack_location = self.config.get("voiceattack_location", "")
        if os.path.isfile(voiceattack_location):
            return voiceattack_location
        logging.error("VoiceAttack could not be located at: '%s'", voiceattack_location)
        return None
    
    def load_word_mappings(self) -> dict[str, str]:
        """
        Loads word mappings from text files.
        """
        word_mappings = {}
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
                            list(map(lambda alias: word_mappings.update({ alias: target }), aliases.split(';')))
                logging.info("Loaded word mappings: %s", word_mappings)
            except Exception as e:
                logging.error("Failed to load word mappings from %s: %s", WORD_MAPPINGS_TEXT_FILE, e)
        else:
            logging.warning("%s not found; no custom word mappings loaded.", WORD_MAPPINGS_TEXT_FILE)
        return word_mappings
    
    def load_fuzzy_words(self) -> list[str]:
        """
        Loads fuzzy words from text files.
        """
        fuzzy_words = []
        if os.path.isfile(FUZZY_WORDS_TEXT_FILE):
            try:
                with open(FUZZY_WORDS_TEXT_FILE, 'r', encoding='utf-8') as f:
                    fuzzy_words = [
                        line.strip() for line in f
                        if line.strip() and not line.strip().startswith('#')
                    ]
            except Exception as e:
                logging.error("Failed to load fuzzy words from %s: %s", FUZZY_WORDS_TEXT_FILE, e)
        else:
            logging.warning("%s not found; fuzzy matching list is empty.", FUZZY_WORDS_TEXT_FILE)
        return fuzzy_words

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
            except Exception as e:
                logging.error("Failed to add new word mapping to %s: %s", WORD_MAPPINGS_TEXT_FILE, e)
        else:
            logging.warning("%s not found; no custom word mappings loaded.", WORD_MAPPINGS_TEXT_FILE)
    
    def get_word_mappings(self) -> dict[str, str]:
        """
        Returns the keyword mappings
        """
        return self.word_mappings
    
    def get_fuzzy_words(self) -> list[str]:
        """
        Returns the fuzzy words list
        """
        return self.fuzzy_words
    
    def get_whisper_model(self) -> str:
        """
        Returns the Whisper model to use for speech-to-text
        """
        return self.config.get("whisper_model", "small.en")
    
    def get_whisper_device(self) -> str:
        """
        Returns the device to use for processing speech-to-text
        GPU or CPU, defaults to GPU
        """
        return self.config.get("whisper_device", "GPU")
    
    def get_whisper_core_type(self) -> str:
        """
        Returns type of GPU cores used for the compute type for processing
        Tensor Cores are available on devices with compute capability 7.0 or higher
        tensor or standard, defaults to tensor
        """
        return self.config.get("whisper_core_type", "tensor")
    
    def get_theme(self) -> str:
        """
        Returns the name of the theme to be used when displaying
        UI elements. When the configuration is set to "default" then
        the name returned will be the current Windows theme.
        """
        return self.config.get("theme", THEME_DEFAULT)