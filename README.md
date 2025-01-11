# WhisperAttack - OpenAI Whisper for VoiceAttack

This repository provides a single-server approach for using OpenAI Whisper locally with VoiceAttack, replacing Windows Speech Recognition with a fully offline, GPU-accelerated blazing fast and accurate AI speech recognition engine

This is a fork for further integration of **KneeboardWhisper** by the amazing creator [@BojoteX](https://github.com/BojoteX). A special thank you goes to [@hradec](https://github.com/hradec), whose original script used Google Voice Recognition, [@SeaTechNerd83](https://github.com/SeaTechNerd83) for helping combine the two approaches and finally [@Sleighzy](https://github.com/sleighzy) for VAICOM implementation and the lengthy list of bug fixes and enchancements that would fill this page

In short, SeaTechNerd83 and I combined the two scripts to run voice commands through Whisper using BojoteX's code and then pushed it into VoiceAttack using hradec's code. To speed this up, I unified the codebase into one file and made it run a server to send commands to VoiceAttack. The Script will run on any Turing or newer architecture Nvidia GPU with 6GB or more of VRAM will run this script along with DCS (performance tuning may be required for lower VRAM cards) although absolute minimum spec GPU has not yet been confirmed

![image](https://github.com/user-attachments/assets/26c79d80-d95a-4c31-be9a-dd5f61d36245)




---



## Features

- **Single Server Script** (`whisper_server.py`):
  - Loads the Whisper model once on GPU or CPU.
  - Records mic audio on demand (via socket commands).
  - Transcribes the `.wav` file using Whisper.
  - Sends recognized text into VoiceAttack.
  - Pushes transcribed text to clipboard - (perfect for voice to text DCS Chat...)

- **Simple Client Script** (`send_command.py`):
  - Sends "start", "stop", or "shutdown" commands to the server.

- **Advantages:**
  - No repeated model loads (faster, especially with larger Whisper models).
  - Push-to-Talk style workflow with VoiceAttack press & release.
  - Extremely accurate voice recognition (No more VoiceAttack misunderstanding you!)


### VAICOM works but is still being tested and we are still learning how to best use this script with VAICOM. If you wish to help test VAICOM with the Whisper AI script, you can get more information in the VR4DCS discord server

---




## Requirements

- **Python 3.11** (must be in your PATH)
  - Install from [python.org]([https://www.python.org/downloads/release/python-3119](https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe)
  - NOTE! v3.12 3.13 etc... will NOT work - PyTorch only provides official wheels for Python 3.8 → 3.11

![python](https://github.com/user-attachments/assets/1b23945c-2635-40ea-a8b1-51bbfbe2a7b4)


- **VoiceAttack**
  - [voiceattack.com](https://voiceattack.com)

- **FFmpeg** (must be in your PATH)
  - Needed by Whisper for audio decoding.
  - Install via opening terminal and:
    - `winget install ffmpeg`

- **GPU (Optional, but Recommended)**
  - Whisper runs faster on an NVIDIA GPU with CUDA.




---




## Installation

### 1. Install Python Dependencies

Open a terminal and run:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu118
pip install openai-whisper sounddevice soundfile pyperclip keyboard
```

- `torch` from the `cu118` index is for CUDA (adjust for your GPU's toolkit version).
- `openai-whisper` is the Whisper engine.
- `sounddevice` & `soundfile` handle audio capture.
- `pyperclip` copies recognized text to the clipboard.
- `keyboard` is used to populate the DCS kneeboard with the text via the associated key binding

---



## Running the Whisper Server
1. Double click whisper_server.py

- You’ll see logs like:

```
2025-01-04 12:00:00 - INFO - Loading Whisper model (small), device=GPU
2025-01-04 12:00:03 - INFO - Starting socket server on 127.0.0.1:65432...
```

- Leave this terminal open. The server must keep running to handle start/stop commands.

NOTE: Make sure to wait for the Whisper Model to download. This process only needs to take place once (unless you change Whisper Models)

![image](https://github.com/user-attachments/assets/3cd88c7f-05a9-4afc-ae6a-9402e564c3df)

---

## Configuring VoiceAttack

Pre-configured Voice Attack Profile is added to the release for your convinience. You must modify it to point to where you have placed WhisperAttack on your computer. 
It is recommended to read through the steps below to understand how whisper injections actually work!

### 1. Disable all speech recognition within VoiceAttack

<img width="825" alt="Disable_speech_recognition" src="https://github.com/user-attachments/assets/1bf08530-4a05-4b19-92a5-560879b50936" />

<img width="840" alt="VoiceAttack_startup" src="https://github.com/user-attachments/assets/fc0bfd3c-d0aa-4501-95ce-a31fa9c78790" />

### 2. Create `send_command.py` Commands

In VoiceAttack, go to **Edit Profile**.

#### New Command for "Start Whisper Recording":

- **When this command executes:**
  - Go to **Other → Windows → Run an application**.
  - **Application**: Point it to 'send_command.py'
  - **Parameters:**

   ```
    start
    ```
   
- Assign a joystick or key press to this command (e.g., "Joystick Button 14 (pressed)").

![image](https://github.com/user-attachments/assets/df309ad5-c3be-40ef-98ce-c3c6c0c8e307)


#### Another Command for "Stop Whisper Recording":

- Same steps, except the **Parameters** is:

    ```
    stop
    ```

- Assign the same joystick button but check "Shortcut is invoked only when released."

![image](https://github.com/user-attachments/assets/895a8585-334d-4d98-9143-f88e8a267f07)
![image](https://github.com/user-attachments/assets/4b8d6980-9bf0-43c6-b9f6-d85a14b5e70b)

---
## DCS Kneeboard Integration - Optional

This script preserves BojoteX original vision for the code and copies the commands into clipboard for use with the Kneeboard.
The original repo can be found here: [https://github.com/BojoteX/KneeboardWhisper](https://github.com/BojoteX/KneeboardWhisper?tab=readme-ov-file#troubleshooting)

Do the following to enable DCS Kneeboard to transcribe what you say:

![assignments](https://github.com/user-attachments/assets/6528e6a7-4114-4fdb-a1bc-1ed68bd6a1f8)

![kneeboardwhisper](https://github.com/user-attachments/assets/71874a7d-5c09-4b8c-b174-8693653ac82f)

---

## How It Works

### `whisper_server.py`

- **On startup:**
  - Loads the Whisper model (e.g., `small`) on GPU or CPU.
  - Opens a socket server at `127.0.0.1:65432`.
  
- **Commands:**
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


# Troubleshooting

### File Found And Not Found
- If the Whisper server fails to transcribe the audio file and exhibits something similar to this:
```
File exists, size = 98256 bytes
Transcribing C:\Users\XXXXXX\AppData\Local\Temp\whisper_temp_recording.wav...
Failed to transcribe audio: [WinError 2] The system cannot find the file specified
No transcription result.
```
- This means FFmpeg is not installed either on your system or in the PATH (see requirements section for FFmpeg download) and making FFmpeg available in the PATH on your system should remedy the issue.

### Could not find a version that satisfies the requirement torch
- If you get a an error like this:
```
ip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
Looking in indexes: https://download.pytorch.org/whl/cu118
ERROR: Could not find a version that satisfies the requirement torch (from versions: none)
ERROR: No matching distribution found for torch
```
- Then check your Python version. PyTorch only provides official wheels for Python 3.8 → 3.11 (64-bit) on Windows. As of January 2025 latest version of Python is 3.13.# and this version will not work!

### UAC Popups
### Running as admin is not recommended! VAICOM users excepted
- **Perform steps as outlined in [Stopping UAC Messages](#stopping-uac-messages-when-running-voiceattack-as-admin) below**
  
---

# Advanced Configuration

## Adding back Punctuation

If you look at whisper_server.py code, you see the following call:

``result = self.model.transcribe(audio_path, language='en', suppress_tokens="0,11,13,30")``

You’d modify it to:

```result = self.model.transcribe(audio_path, language='en')```

Everything else stays the same. Whisper will then start adding punctuation symbols when decoding the transcribed text. Further discussions can be found here: https://github.com/openai/whisper/discussions/589

## Performance (AI Model)
- If WhisperAttack is causing significant studders, It is likely that the current model is overloading your VRAM. If this is the case, studders can be alleviated by reducing the model size (extra information on the models is available in the table below) in the `whisper_server.py` file as follows: 
- Change the Whisper model by changing "small" to another model (see table) inside the python script as found:

    ```python
    model = load_whisper_model(device='GPU', model_size='small')
    ```

- Using smaller models will reduce VRAM and compute costs. See below for a full speed breakdown
- First activation with a new AI model will prompt the model to be downloaded which may take an extended amount of time depending on internet speed.

### Available models and languages

There are six model sizes, four with English-only versions, offering speed and accuracy tradeoffs.
Below are the names of the available models and their approximate memory requirements and inference speed relative to the large model.
The relative speeds below are measured by transcribing English speech on a A100, and the real-world speed may vary significantly depending on many factors including the language, the speaking speed, and the available hardware.

|  Size  | Parameters | English-only model | Multilingual model | Required VRAM | Relative speed |
|:------:|:----------:|:------------------:|:------------------:|:-------------:|:--------------:|
|  tiny  |    39 M    |     `tiny.en`      |       `tiny`       |     ~1 GB     |      ~10x      |
|  base  |    74 M    |     `base.en`      |       `base`       |     ~1 GB     |      ~7x       |
| small  |   244 M    |     `small.en`     |      `small`       |     ~2 GB     |      ~4x       |
| medium |   769 M    |    `medium.en`     |      `medium`      |     ~5 GB     |      ~2x       |
| large  |   1550 M   |        N/A         |      `large`       |    ~10 GB     |       1x       |
| turbo  |   809 M    |        N/A         |      `turbo`       |     ~6 GB     |      ~8x       |

The `.en` models for English-only applications tend to perform better, especially for the `tiny.en` and `base.en` models. We observed that the difference becomes less significant for the `small.en` and `medium.en` models.
Additionally, the `turbo` model is an optimized version of `large-v3` that offers faster transcription speed with a minimal degradation in accuracy.

Whisper's performance varies widely depending on the language. The figure below shows a performance breakdown of `large-v3` and `large-v2` models by language, using WERs (word error rates) or CER (character error rates, shown in *Italic*) evaluated on the Common Voice 15 and Fleurs datasets. Additional WER/CER metrics corresponding to the other models and datasets can be found in Appendix D.1, D.2, and D.4 of [the paper](https://arxiv.org/abs/2212.04356), as well as the BLEU (Bilingual Evaluation Understudy) scores for translation in Appendix D.3.

## Stopping UAC Messages When Running VoiceAttack as Admin

### Running VoiceAttack as administrator is not recommended. Do not do these steps unless you need to run VA with admin privileges (aka VAICOM) ###

- Download Vallhala Release
- WhisperAttack will now ask for UAC Permission to run elevated


Enjoy your local (offline) speech recognition with OpenAI Whisper + VoiceAttack! If you run into issues, open an issue or check the logs for clues.
