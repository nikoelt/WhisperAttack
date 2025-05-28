from typing import Callable
from tkinter import StringVar, font, LEFT
from ttkbootstrap import Window, Toplevel, Button, Frame, Label, Entry

class WhisperAttackWordMappings:
    """
    A class used to display a UI and handle the adding of new word mappings.
    """
    def __init__(self, root: Window, add_work_mapping: Callable[[str, str], None]):
        self.add_word_mapping = add_work_mapping

         # Center the modal over the parent window
        modal_width = 800
        modal_height = 300
        parent_x = root.winfo_x()
        parent_y = root.winfo_y()
        parent_width = root.winfo_width()
        parent_height = root.winfo_height()
        x = parent_x + (parent_width // 2) - (modal_width // 2)
        y = parent_y + (parent_height // 2) - (modal_height // 2)

        modal = Toplevel(
            title="Add word mapping",
            size=(800, 300),
            position=(x, y),
            transient=root
        )
        modal.grab_set()

        aliases = StringVar()
        replacement = StringVar()

        custom_font = font.Font(family="GG Sans", size=11)
        aliases_frame = Frame(modal)
        aliases_frame.pack(pady=15, padx=10, fill="x")
        Label(aliases_frame, text="Aliases").pack(side=LEFT, padx=5)
        Entry(
            aliases_frame,
            textvariable=aliases,
            font=custom_font
        ).pack(side=LEFT, fill="x", expand=True, padx=5)
        replacement_frame = Frame(modal)
        replacement_frame.pack(pady=15, padx=10, fill="x")
        Label(replacement_frame, text="Replacement").pack(side=LEFT, padx=5)
        Entry(
            replacement_frame,
            textvariable=replacement,
            font=custom_font
        ).pack(side=LEFT, fill="x", expand=True, padx=5)

        def add_new_word_mapping() -> None:
            self.add_word_mapping(aliases.get(), replacement.get())
            modal.destroy()

        button_frame = Frame(modal)
        button_frame.pack(pady=50, padx=10, fill="x")
        Button(
            button_frame,
            text="Ok",
            style="primary.TButton",
            command=add_new_word_mapping
        ).pack(side=LEFT, padx=10)
        Button(
            button_frame,
            text="Cancel",
            style="secondary.TButton",
            command=modal.destroy
        ).pack(side=LEFT, padx=10)
