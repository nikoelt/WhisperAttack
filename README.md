# OpenAI Whisper Server for VoiceAttack - WhisperAttack

This is a fork for further integration of **KneeboardWhisper** by the amazing creator [@BojoteX](https://github.com/BojoteX). A special thank you goes to **hradec**, whose original script used Google Voice Recognition, and [@SeaTechNerd83](https://github.com/SeaTechNerd83) for helping combine the two approaches.

In short, [@SeaTechNerd83](https://github.com/SeaTechNerd83) and I combined the two scripts to run voice commands through Whisper using BojoteX's code and then pushed it into VoiceAttack using hradec's code. Unfortunately whilst the speech recognition was lightning fast we had wait for the terminal to launch python and speech engine etc... which took time. To speed this up, I unified the codebase into one file and made it run a server to send commands to VoiceAttack 

This repository provides a single-server approach for using OpenAI Whisper locally with VoiceAttack, replacing Windows Speech Recognition (or Google Speech) with a fully offline, GPU-accelerated recognition engine.

---

## Features

- **Single Server Script** (`whisper_server.py`):
  - Loads the Whisper model once on GPU or CPU.
  - Records mic audio on demand (via socket commands).
  - Transcribes the `.wav` file using Whisper.
  - Sends recognized text into VoiceAttack.

- **Simple Client Script** (`send_command.py`):
  - Sends "start", "stop", or "shutdown" commands to the server.

- **Advantages:**
  - No repeated model loads (faster, especially with larger Whisper models).
  - Push-to-Talk style workflow with VoiceAttack press & release.

---

## Requirements

- **Python 3.11 (or newer)**
  - Install from [python.org](https://python.org) or the Microsoft Store.

- **VoiceAttack**
  - [voiceattack.com](https://voiceattack.com)

- **FFmpeg** (must be in your PATH)
  - Needed by Whisper for audio decoding.
  - Install via:
    - `winget install ffmpeg`
    - Chocolatey: `choco install ffmpeg`
    - Or download from [ffmpeg.org](https://ffmpeg.org).

- **GPU (Optional, but Recommended)**
  - Whisper runs faster on an NVIDIA GPU with CUDA.

---

## Installation

### 1. Install Python Dependencies

Open a terminal and run:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu118
pip install openai-whisper sounddevice soundfile pyperclip
```

- `torch` from the `cu118` index is for CUDA (adjust for your GPU's toolkit version).
- `openai-whisper` is the Whisper engine.
- `sounddevice` & `soundfile` handle audio capture.
- `pyperclip` copies recognized text to the clipboard.

---

## How It Works

### `whisper_server.py`

- On startup:
  - Loads the Whisper model (e.g., `small`) on GPU or CPU.
  - Opens a socket server at `127.0.0.1:65432`.
  
- Commands:
  - `start`: Begin recording to `whisper_temp_recording.wav`.
  - `stop`: Stop recording, transcribe with Whisper, copy text to clipboard, send to VoiceAttack.
  - `shutdown`: Gracefully stops the server.

### `send_command.py`

- Sends a command (e.g., `start`, `stop`) to the server’s socket.
- Example usage:

```bash
python send_command.py start
# speak into your mic...
python send_command.py stop
```

---

## Running the Whisper Server

1. Open a terminal in the same folder as `whisper_server.py`.
2. Run:

```bash
python whisper_server.py
```

- You’ll see logs like:

```
2025-01-04 12:00:00 - INFO - Loading Whisper model (small), device=GPU
2025-01-04 12:00:03 - INFO - Starting socket server on 127.0.0.1:65432...
```

- Leave this terminal open. The server must keep running to handle start/stop commands.

---

## Configuring VoiceAttack

### 4.1 Create `send_command.py` Commands

- In VoiceAttack, go to **Edit Profile**.

#### New Command for "Start Whisper Recording":

- **When this command executes:**
  - Go to **Other → Windows → Run an application**.
  - **Application**: Point it to your `python.exe` (or the full path).
  - **Parameters:**

    ```
    "C:\Path\to\send_command.py" start
    ```

- Assign a joystick or key press to this command (e.g., "Joystick Button 14 (pressed)").

#### Another Command for "Stop Whisper Recording":

- Same steps, except the **Parameters** is:

    ```
    "C:\Path\to\send_command.py" stop
    ```

- Assign the same joystick button but check "Shortcut is invoked only when released."

#### Optional "Shutdown" Command

- Pass "shutdown" as the parameter:

    ```
    "C:\Path\to\send_command.py" shutdown
    ```

---

## Troubleshooting

- **WinError 2**:
  - Ensure `ffmpeg` is installed and in PATH. Run `ffmpeg -version` to verify.

- **No GPU**:
  - Check logs. If the server loads on CPU instead of GPU, verify PyTorch installation and GPU drivers.

- **No Recognized Text**:
  - Ensure your mic is set as the default input or specify a device index in `sounddevice.InputStream(...)`.

---

## Optional: DCS Kneeboard Integration

- After transcription, recognized text is copied to your clipboard.
- Bind a key (e.g., `CTRL+ALT+P`) in DCS to "paste into kneeboard."

---

## Final Notes

- Change the Whisper model by editing:

    ```python
    model = load_whisper_model(device='GPU', model_size='small')
    ```

- Use "tiny" or "base" for faster but less accurate recognition.
- Keep `whisper_server.py` running to use push-to-talk commands.

Enjoy your local (offline) speech recognition with OpenAI Whisper + VoiceAttack! If you run into issues, open an issue or check the logs for clues.
