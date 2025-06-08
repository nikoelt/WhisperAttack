from tkinter import NORMAL, DISABLED, END
from ttkbootstrap.scrolled import ScrolledText
from theme import TAG_BLACK, TAG_BLUE, TAG_GREEN, TAG_GREY, TAG_ORANGE, TAG_RED, theme_config

class WhisperAttackWriter:
    """
    A class used to write to the text area within the WhisperAttack window.
    """
    def __init__(self, theme: str, text_area: ScrolledText):
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
        self.text_area.text.configure(state=NORMAL)
        self.text_area.insert(END, text + "\n", tag)
        self.text_area.see(END)
        self.text_area.text.configure(state=DISABLED)

    def write_dict(self, dictionary: dict[str, str], tag = TAG_BLACK) -> None:
        """
        Write the dictionary as a formatted set of keys and values.
        """
        for key, value in dictionary.items():
            self.write(f"{key}: {value}", tag)