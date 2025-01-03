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

![image](https://github.com/user-attachments/assets/0c9019f9-1f93-49f6-bfa1-7b8ef653953f)

![image](https://github.com/user-attachments/assets/af645cba-fd8b-4761-a9fa-66d74f0bf37c)

- As a small bonus I included a bare voice attack profile that I used in testing. But you still need to edit it and point it to the correct locations where everything is placed!!!

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

### OPTIONAL FOR RUNNING AS ADMIN - Stopping UAC Messages When Running VoiceAttack as Admin

If you want to avoid UAC prompts every time a voice command is sent while running VoiceAttack as administrator, follow these steps:

---

## Overview

- Create a new Scheduled Task that runs `VoiceAttack.exe` with highest privileges.
- Optional: Create a desktop shortcut or a small batch/PowerShell script that triggers the scheduled task.

When you run the scheduled task (either manually or via a shortcut/script), Windows will launch VoiceAttack in elevated mode without prompting UAC each time.

---

### 1) Open Task Scheduler

- Press the **Windows key**, type **Task Scheduler**, and press Enter.
- Task Scheduler will open. On the left side, you’ll see a tree with "Task Scheduler Library," etc.

### 2) Create a New Task

1. In Task Scheduler, right-click on **Task Scheduler Library** in the left pane.
2. Choose **New Folder...** (optional) to keep tasks organized—for example, create a folder named `MyTasks`.
3. Right-click on the new folder (or **Task Scheduler Library** if you didn’t create a folder) and select **Create Task...** (not "Create Basic Task").

#### On the General Tab

- **Name**: Enter something like `VoiceAttackElevated`.
- **Description** (optional): "Run VoiceAttack as admin without UAC."
- **User account**: By default, it shows your current user. That’s fine.
- Select **Run whether user is logged on or not** if you want the task to work even if you’re not logged in. Otherwise, leave it at **Run only when user is logged on**.
- Check **Run with highest privileges**.
- **Configure for**: Windows 10 or Windows 11, whichever version you have.

#### You Do NOT Need Any Triggers

- We’re going to run this task manually (from a shortcut or script). You can skip the **Triggers** tab unless you want VoiceAttack to auto-run at login, etc.

#### On the Actions Tab

1. Click **New...**
2. **Action**: "Start a program."
3. **Program/script**: Browse to your `VoiceAttack.exe`. For example:

    ```
    C:\Program Files (x86)\VoiceAttack\VoiceAttack.exe
    ```

4. **Add arguments** (optional): If you have any command-line arguments for VoiceAttack, put them here.
5. **Start in** (optional): The folder in which VoiceAttack should start (often the same folder as the .exe).
6. Click **OK** to add this action.

#### Conditions / Settings

- Leave these at their defaults unless you have specific requirements.
- On **Conditions**: Uncheck "Start the task only if the computer is on AC power" if you want it to run on battery power.
- On **Settings**: Ensure "Allow task to be run on demand" is checked.

#### Save the Task

- Click **OK** at the bottom.
- If you chose "Run whether user is logged on or not," Windows will prompt for your password so it can store the credentials.

---

### 3) Test the Task in Task Scheduler

1. In Task Scheduler, locate your new task (`VoiceAttackElevated`) under the **Task Scheduler Library** (or your custom folder).
2. Right-click on the task and select **Run**.
3. VoiceAttack should launch without a UAC prompt.

- If you see a status of "Running" and then it disappears, check whether VoiceAttack actually launched (it might be running in the tray).

---

### 4) Create a Shortcut (Optional, but Recommended)

To simplify launching the task:

1. Right-click on the Desktop → **New → Shortcut**.
2. In "Type the location of the item," enter:

    ```
    schtasks.exe /run /tn "VoiceAttackElevated"
    ```

    - If you placed the task in a custom folder, include the path. For example:

        ```
        schtasks.exe /run /tn "MyTasks\VoiceAttackElevated"
        ```

3. Click **Next** → Name the shortcut (e.g., `VoiceAttack Elevated`).
4. Click **Finish**.

Double-clicking this shortcut will run the scheduled task, launching VoiceAttack with elevated privileges and no UAC prompt.

---

### 5) (Advanced) Start the Scheduled Task from Python or a Script

If you want to trigger the scheduled task programmatically (e.g., from `whisper_server.py` or `send_command.py`):

- Use this command in a script:

    ```bash
    schtasks.exe /run /tn "VoiceAttackElevated"
    ```

- Or in Python:

    ```python
    import subprocess

    subprocess.call(["schtasks", "/run", "/tn", "VoiceAttackElevated"])
    ```

---

### Troubleshooting

- **Task doesn’t run**: Check Task Scheduler’s "Last Run Result" column for error codes.
- **VoiceAttack not launching**: Verify the path to `VoiceAttack.exe` and ensure it hasn’t moved.
- **UAC prompt STILL appears**: Ensure:
  - "Run as administrator" is unchecked in the file properties of `VoiceAttack.exe`.
  - You are running the scheduled task (not the .exe directly).
- **Stored credentials issue**: If you chose "Run whether user is logged on or not" but didn’t store your credentials correctly, edit the task and re-enter your password.

---

Now, you can launch VoiceAttack as an administrator without seeing the UAC prompt, either manually, via a desktop shortcut, or programmatically from your scripts!


## Final Notes

- Change the Whisper model by editing:

    ```python
    model = load_whisper_model(device='GPU', model_size='small')
    ```

- Use "tiny" or "base" for faster but less accurate recognition.
- Keep `whisper_server.py` running to use push-to-talk commands.

Enjoy your local (offline) speech recognition with OpenAI Whisper + VoiceAttack! If you run into issues, open an issue or check the logs for clues.
