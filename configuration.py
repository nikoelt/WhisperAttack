import os
import logging
from theme import THEME_DEFAULT

class ConfigurationError(Exception):
    """
    Exception class for errors reading and writing configuration
    """

class ConfigurationWarning(Exception):
    """
    Warning class for errors reading configuration
    """

class WhisperAttackConfiguration:
    """
    A class to read and write the WhisperAttack configuration.
    Default configuration is loaded from the application directory,
    custom configuration is loaded from the AppData\Local\WhisperAttack
    directory and is combined with the default configuration.
    """
    def __init__(self, app_location: str, app_data_location: str):
        default_config = self.load_configuration(app_location)
        custom_config = self.load_configuration(app_data_location, False)
        self.config = default_config | custom_config

        default_word_mappings = self.load_word_mappings(app_location)
        custom_word_mappings = self.load_word_mappings(app_data_location, False)
        self.word_mappings = default_word_mappings | custom_word_mappings

        default_fuzzy_words = self.load_fuzzy_words(app_location)
        custom_fuzzy_words = self.load_fuzzy_words(app_data_location, False)
        self.fuzzy_words = [*default_fuzzy_words, *custom_fuzzy_words]

    def load_configuration(self, location: str, default = True) -> dict[str, str]:
        """
        Loads configuration settings.
        """
        logging.info("Loading %s configuration...", "default" if default else "custom")
        config = {}
        settings_file = os.path.join(location, "settings.cfg")
        if os.path.isfile(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        parts = line.split('=', maxsplit=1)
                        if len(parts) == 2:
                            source, target = parts
                            config[source.strip()] = target.strip()
            except Exception as error:
                logging.error("Failed to load configuration settings from '%s': %s", settings_file, error)
                raise ConfigurationError("Failed to load configuration settings") from error
        elif default:
            logging.error("File not found: '%s'", settings_file)
            raise ConfigurationError("The configuration settings.cfg file could not be found")

        logging.info("Loaded configuration: %s", config)
        return config

    def load_word_mappings(self, location: str, default = True) -> dict[str, str]:
        """
        Loads word mappings from text files.
        """
        logging.info("Loading %s word mappings...", "default" if default else "custom")
        word_mappings = {}
        word_mappings_file = os.path.join(location, "word_mappings.txt")
        if os.path.isfile(word_mappings_file):
            try:
                with open(word_mappings_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        parts = line.split('=', maxsplit=1)
                        if len(parts) == 2:
                            aliases, target = parts
                            target = target.strip()
                            list(map(lambda alias: word_mappings.update({ alias: target }), aliases.split(';')))
            except Exception as error:
                logging.error("Failed to load word mappings from '%s': %s", word_mappings_file, error)
                raise ConfigurationError("Failed to load word mappings") from error
        elif default:
            logging.error("File not found: '%s'", word_mappings_file)
            raise ConfigurationError("The word_mappings.txt file could not be found.")

        logging.info("Loaded word mappings:")
        for key, value in word_mappings.items():
            logging.info("%s: %s", key, value)
        return word_mappings

    def load_fuzzy_words(self, location: str, default = True) -> list[str]:
        """
        Loads fuzzy words from text files.
        """
        logging.info("Loading %s fuzzy words...", "default" if default else "custom")
        fuzzy_words = []
        fuzzy_words_file = os.path.join(location, "fuzzy_words.txt")
        if os.path.isfile(fuzzy_words_file):
            try:
                with open(fuzzy_words_file, 'r', encoding='utf-8') as f:
                    fuzzy_words = [
                        line.strip() for line in f
                        if line.strip() and not line.strip().startswith('#')
                    ]
            except Exception as error:
                logging.error("Failed to load fuzzy words from '%s': %s", fuzzy_words_file, error)
                raise ConfigurationError("Failed to load fuzzy words from fuzzy_words.txt") from error
        elif default:
            logging.error("File not found: '%s'", fuzzy_words_file)
            raise ConfigurationError("The fuzzy_words.txt file could not found.")

        logging.info("Loaded fuzzy words: %s", fuzzy_words)
        return fuzzy_words

    def add_word_mapping(self, location: str, aliases: str, replacement: str) -> None:
        """
        Adds a new alias and replacement to the word mappings
        """
        if aliases.strip() == "":
            return None

        list(map(lambda alias: self.word_mappings.update({ alias: replacement }), aliases.split(';')))
        word_mappings_file = os.path.join(location, "word_mappings.txt")
        try:
            with open(word_mappings_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{aliases}={replacement}")
                f.close()
            logging.info("Added aliases: %s", aliases)
            logging.info("Added replacement: %s", replacement)
        except Exception as error:
            logging.error("Failed to add new word mapping to word_mappings.txt file: %s", error)
            raise ConfigurationError("Failed to add new word mapping to word_mappings.txt file") from error

    def get_configuration(self) -> dict[str, str]:
        """
        Return the full configuration
        """
        return self.config

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
    
    def get_whisper_compute_type(self) -> str:
        """
        Returns the compute type to be used when loading the Whisper model
        """
        return self.config.get("whisper_compute_type", "default")

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
