OpenAI Whisper Server for VoiceAttack - WhisperAttack

This is a fork for further integration of KneeboardWhisper by the amazing creator @BojoteX.
A special thank you goes to hradec, whose original script used Google Voice Recognition, and @SeaTechNerd83 for helping combine the two approaches.

In short @SeaTechNerd83 and I combined the two scripts to run voice commands through Whisper using BojoteX code, and then push it into Voice Attack using hradec's code. Then to speed this up I unified the codebase into one file, made it run a server which sends commands to VoiceAttack

This repository provides a single-server approach for using OpenAI Whisper locally with VoiceAttack, replacing Windows Speech Recognition (or Google Speech) with a fully offline, GPU-accelerated recognition engine.
Features

    Single Server Script (whisper_server.py) that:
        Loads the Whisper model once on GPU or CPU.
        Records mic audio on demand (via socket commands).
        Transcribes the .wav file using Whisper.
        Sends recognized text into VoiceAttack.
    Simple Client Script (send_command.py) to send “start”, “stop”, or “shutdown” commands to the server.
    No repeated model loads (faster, especially if you use a larger Whisper model).
    Push-to-Talk style workflow with VoiceAttack press & release.

Requirements

    Python 3.11 (or newer)
        Install from python.org or the Microsoft Store.
    VoiceAttack
        voiceattack.com
    FFmpeg (must be in your PATH)
        Needed by Whisper for audio decoding.
        Install via winget install ffmpeg, Chocolatey (choco install ffmpeg), or from ffmpeg.org.
    GPU (Optional, but Recommended)
        Whisper runs faster on an NVIDIA GPU with CUDA.

1) Install Python Dependencies

Open a terminal and run:

pip install torch --index-url https://download.pytorch.org/whl/cu118
pip install openai-whisper sounddevice soundfile pyperclip

    torch from the cu118 index is for CUDA (adjust if your GPU uses a different toolkit version).
    openai-whisper is the Whisper engine.
    sounddevice & soundfile handle audio capture.
    pyperclip copies recognized text to the clipboard.

2) How It Works

    whisper_server.py:
        On startup, loads the Whisper model (e.g. small) either on GPU or CPU.
        Opens a socket server at 127.0.0.1:65432.
        Waits for commands:
            start → Begin recording to whisper_temp_recording.wav.
            stop → Stop recording, transcribe with Whisper, copy text to clipboard, send to VoiceAttack.
            shutdown → Gracefully stops the server.

    send_command.py:
        Tiny script that takes a command (e.g. start, stop) and sends it to the server’s socket.
        Example usage:

        python send_command.py start
        # speak into your mic...
        python send_command.py stop

        This approach replaces the older “two-script” pattern of recorder.py + transcriber.py.

3) Running the Whisper Server

    Open a terminal in the same folder as whisper_server.py.

    Run:

python whisper_server.py

You’ll see logs like:

    2025-01-04 12:00:00 - INFO - Loading Whisper model (small), device=GPU
    2025-01-04 12:00:03 - INFO - Starting socket server on 127.0.0.1:65432...

    Leave this terminal open. The server must keep running to handle start/stop commands.

4) Configuring VoiceAttack

You want VoiceAttack to send the “start” command when you press a button, and “stop” when you release it. That’s a push-to-talk style workflow.
4.1. Create send_command.py Commands

    In VoiceAttack, go to Edit Profile.

    New Command for “Start Whisper Recording”:
        When this command executes:
            Go to Other → Windows → Run an application.
            Application: point it to your python.exe (or the full path).
            Parameters:

        "C:\Path\to\send_command.py" start

        (Optional) “Wait until the launched application exits” can be unchecked if it’s a quick script.

Assign a joystick or key press to this command.

    For example, “Joystick Button 14 (pressed).”

Another Command for “Stop Whisper Recording”:

    Same steps, except the Parameters is:

        "C:\Path\to\send_command.py" stop

        Assign the same joystick button, but in VoiceAttack check “Shortcut is invoked only when released.”
        This ensures press = “start”, release = “stop.”

That’s it! Whenever you press the button, VoiceAttack calls send_command.py start. When you release, it calls send_command.py stop, the server records your mic audio and transcribes it.
4.2. Optional “Shutdown” Command

If you want a VoiceAttack command to stop whisper_server.py, do the same process but pass "shutdown":

"C:\Path\to\send_command.py" shutdown

This tells the server to gracefully exit.
5) UAC Prompts & Running VoiceAttack as Admin

If you must run VoiceAttack as administrator (for certain games) but get UAC pop-ups each time you call it from a script, you can avoid the prompts by using a Scheduled Task:

    Create a new Task in Task Scheduler:
        “Run with highest privileges.”
        Action: “Start a program,” pointing to VoiceAttack.exe.
        Uncheck “Run as admin” in the EXE’s file properties (or the settings of VoiceAttack like it was for me), letting the scheduled task handle elevation.
    Launch that scheduled task from a shortcut or schtasks /run /tn "VoiceAttackELEVATED" instead of directly running VoiceAttack.exe.
    This method bypasses UAC prompts every time. For details, see Microsoft docs.

6) Verifying It Works

    Start whisper_server.py in a terminal (or just double click the application)
    In VoiceAttack, press your assigned PTT button:
        Logs in the terminal: Received command: start → “Starting recording...”
    Release the button:
        Logs: “Stopping recording...” → “Transcribing...” → You’ll see recognized text printed → Sent to VoiceAttack.

Clipboard & VoiceAttack

    The recognized text is copied to your clipboard.
    whisper_server.py also calls VoiceAttack.exe -command "<recognized text>" if it finds VoiceAttack installed.
    VoiceAttack sees that text as a new command (unless you just want to see it in logs or kneeboard, etc.).

7) Troubleshooting

    WinError 2
        Usually means ffmpeg is missing or not in PATH. Install it and ensure ffmpeg -version works in a normal command prompt.
    No GPU
        Check logs: if it loads on CPU instead of GPU, you might not have the CUDA version of PyTorch or your drivers aren’t recognized.
    UAC Prompt
        Use the Scheduled Task approach above if you want to run VoiceAttack as admin without pop-ups.
    No recognized text
        Make sure your mic is the default input or specify a device index in the sounddevice.InputStream(...).

8) Optional: DCS Kneeboard Integration

If you want recognized text in DCS:

    It’s already in your clipboard after each transcription.
    Bind a key (e.g. CTRL+ALT+P) in DCS to “paste into kneeboard.”
    Press that key, or have VoiceAttack press it automatically after transcription, to paste your recognized text.

Final Notes

    Change the Whisper model by editing:

    model = load_whisper_model(device='GPU', model_size='small')

    Use "tiny" or "base" if you want faster (but potentially less accurate) recognition.
    Adjust your sample rate if needed, but 16000 Hz is standard for Whisper.
    Make sure you keep whisper_server.py running in the background the entire time you’re using push-to-talk commands.

Enjoy your local (offline) speech recognition with OpenAI Whisper + VoiceAttack—no more slow or inaccurate speech engines! If you run into issues, open an issue or check the logs for clues.
