# WhisperAttack - OpenAI Whisper for VoiceAttack

This repository provides a single-server approach for using OpenAI Whisper locally with VoiceAttack, replacing Windows Speech Recognition with a fully offline, GPU-accelerated blazing fast and accurate AI speech recognition engine

This is a fork for further integration of **KneeboardWhisper** by the amazing creator [@BojoteX](https://github.com/BojoteX). A special thank you goes to [@hradec](https://github.com/hradec), whose original script used Google Voice Recognition, [@SeaTechNerd83](https://github.com/SeaTechNerd83) for helping combine the two approaches and creating a VA plugin and finally [@sleighzy](https://github.com/sleighzy) for VAICOM implementation and the lengthy list of bug fixes and enchancements that would fill this page

In short, SeaTechNerd83 and I combined the two scripts to run voice commands through Whisper using BojoteX's code and then pushed it into VoiceAttack using hradec's code. To speed this up, I unified the codebase into one file and made it run a server to send commands to VoiceAttack. WhisperAttack will run on any Nvidia GPU with 6GB or more of VRAM and will run along with DCS (performance tuning may be required for lower VRAM cards) although absolute minimum spec GPU has not yet been confirmed, RTX 2060 6gb and GTX 1070 8gb have been confirmed working stutter free alongside DCS in VR.

---

## Features

- **OpenAI Whisper models**:
  - Loads the Whisper model once on GPU or CPU.
  - Records mic audio on demand (via socket commands).
  - Transcribes the `.wav` file using Whisper.
  - Sends recognized text into VoiceAttack.
  - Pushes transcribed text to clipboard - (perfect for voice to text DCS Chat...)

- **VoiceAttack Command Plugin**
  - Sends "start", "stop", or "shutdown" commands to the server directly through VoiceAttack.

- **Advantages:**
  - No repeated model loads (faster, especially with larger Whisper models).
  - Push-to-Talk style workflow with VoiceAttack press & release.
  - Extremely accurate voice recognition (No more VoiceAttack misunderstanding you!)

---

## VAICOM integration

Instructions for integrating with VAICOM can be located in the [VAICOM INTEGRATION](./VAICOM%20PRO/VAICOM_INTEGRATION.md) documentation.

A VoiceAttack profile for Whisper VAICOM integration is available in this repository and linked from those instructions.

---

## Requirements

- **VoiceAttack**
  - [voiceattack.com](https://voiceattack.com)
  - Plugins Enabled

- **GPU (Optional, but Recommended)**
  - Whisper runs faster on an NVIDIA GPU with CUDA.
  - When using GPU if CUDA is not available then an error will be logged and this will fallback to CPU

---

## Installation

1. Download the latest release [WhisperAttack v1.2.0.zip file from the Google drive](https://drive.google.com/drive/folders/1FVzbkNPFoeAnuNfpr_ZCUOOrDVRkiV_a?usp=sharing) and unarchive anywhere on your computer, e.g. `C:\Program Files\WhisperAttack`
1. A shortcut can be created to the `WhisperAttack.exe` application

---

## Configuration

### settings.cfg

The `settings.cfg` file contains configuration for WhisperAttack.

The default values should cover most cases but can be changed:

- `whisper_model` - The Whisper model to use, `small.en` by default. See the table at the bottom of the README file for options.
  - A smaller size can be specified for reducing the amount of VRAM used, e.g. `base.en` or `tiny.en`
- `whisper_device` - Which device to run the Whisper transcription process on, `GPU` (default) or `CPU`
- `voiceattack_location` - The full path to your VoiceAttack executable file if you have installed VoiceAttack in a non-default location.
- `theme` - To display the WhisperAttack UI in light or dark mode. Valid values: 
  - `default` - this will use the current theme you have set for Windows
  - `dark` - dark mode
  - `light` - light mode

### word_mappings.txt

The `word_mappings.txt` file contains keys and values that can be used to replace a spoken word with another word. For example, if the transcription often outputs "Inter" when you are saying "Enter" then this can be added as a word placement.

The word replacement configuration also supports specifying multiple words to be replaced with a single word, these are separated by a semicolon `;`. In the example below saying either "gulf" or "gold" would be replaced with "Golf".

```
gulf;gold=Golf
inter=Inter
```

WhisperAttack needs to be restarted after making changes to this file. New word mappings can be added via the configuration screen and do not require a restart.

---

## Running the Whisper Server

Double click the `WhisperAttack.exe` file or shortcut. This will open an application window and start the server.

The application window will display startup logging information, the raw text transcribed from the speech, and the final cleaned up command ot text that was sent to VoiceAttack or DCS. The window can be closed, and then shown again from the menu in the WhisperAttack icon in the Windows system tray. WhisperAttack will continue running even when the window is closed.

WhisperAttack will have completed loading once the "Server started and listening" message is displayed.

```
Loading Whisper model (small.en), device=GPU ...
Server started and listening on 127.0.0.1:65432...
```

![whisperattack_voiceattack](./screenshots/WhisperAttack%20UI%20and%20VoiceAttack.png)

A WhisperAttack icon will be placed in your Windows system tray. Right-clicking this will give options to show the WhisperAttack window, or to exit the application.

![whisperattack_systemtrayicon](./screenshots/WhisperAttack%20system%20tray.png)

Closing VoiceAttack will also stop and close WhisperAttack.

**NOTE:** There may be a slow startup time for the Whisper Model to download. This process only needs to take place once (unless you change the Whisper Model to be used)

The Whisper server will output logs to the `C:\Users\username\AppData\Local\WhisperAttack\WhisperAttack.log` file.

---

## Configuring VoiceAttack

Pre-configured Voice Attack Profile is added to the release for your convenience. It is recommended to read through the steps below to understand how whisper injections actually work!

### 1. Disable all speech recognition within VoiceAttack

<img width="825" alt="Disable_speech_recognition" src="https://github.com/user-attachments/assets/1bf08530-4a05-4b19-92a5-560879b50936" />

<img width="840" alt="VoiceAttack_startup" src="https://github.com/user-attachments/assets/fc0bfd3c-d0aa-4501-95ce-a31fa9c78790" />

### 2. Enable Plugin support in VoiceAttack

Go to **Options → General → Enable Plugin Support**.

![EnablePluginsVA](https://github.com/user-attachments/assets/8bb6faf2-4aa4-416b-99cd-6b9b2a6c0097)

### 3. Place Plugin in VoiceAttack Apps folder

After extracting the .zip file, Locate the `WhisperAttackServerCommand` folder and copy the entire folder

![image](https://github.com/user-attachments/assets/dcd75f43-b957-4551-86bf-650468586834)

Locate the VoiceAttack Apps Folder

![image](https://github.com/user-attachments/assets/413de21d-e7a8-4086-ad9f-c97354716ab3)

Paste the entire `WhisperAttackServerCommand` folder into the Apps folder

![image](https://github.com/user-attachments/assets/fd856417-34b7-4f39-b3a9-bf4ea0e79871)

If the plugin is enabled and active and everything is set up correctly, VoiceAttack should give these messages on startup:

![image](https://github.com/user-attachments/assets/287e0a3c-7891-40a1-96bf-842f26dccd77)


### 4. Create Recording commands

In VoiceAttack, go to **Edit Profile**.

#### New Command for "Start Whisper Recording":

- **When this command executes:**
  - Go to **Other → Advancced → Execute an External Plugin Function**.
  - **Plugin**: Point it to 'WASC V0.1beta'
  - **Plugin Context:**

```
Start Whisper Recording
```

Assign a joystick or key press to this command (e.g., "Joystick Button 14 (pressed)").

![Whisperattackreadme](https://github.com/user-attachments/assets/ee96bc06-8fe6-45b0-9999-076eb0e0cc00)

#### Another Command for "Stop Whisper Recording":

Same steps, except the **Parameters** is:

```
Stop Whisper Recording
```

Assign the same joystick button but check **"Shortcut is invoked only when released."**

![Whisperattackreadme1](https://github.com/user-attachments/assets/9c84d4f8-00c0-4525-8cda-0c0ddda24298)

---
## Adding new word mappings

Word mappings can be added to WhisperAttack so that when these words are found within transcribed sentences they will be replaced with the replacement word you provide. This can aid with replacing words that are consistently transcribed incorrectly into the word you actually want.

Click the Add word mapping button to open this configuration screen. Multiple aliases can be entered, separated by semicolons, for a single replacement.

![whisperattack_addwordmapping](./screenshots/WhisperAttack%20add%20new%20word%20mapping.png)

---
## Clipboard & DCS Kneeboard Integration - Optional

This script preserves BojoteX original vision for the code and copies the commands into clipboard for use with the Kneeboard.
The original repo can be found here: [https://github.com/BojoteX/KneeboardWhisper](https://github.com/BojoteX/KneeboardWhisper?tab=readme-ov-file#troubleshooting)

Do the following to enable DCS Kneeboard to transcribe what you say:
Once completed, you must say "Note" followed by what you would like to transcribe to kneeboard/clipboard

![assignments](https://github.com/user-attachments/assets/6528e6a7-4114-4fdb-a1bc-1ed68bd6a1f8)

![kneeboardwhisper](https://github.com/user-attachments/assets/71874a7d-5c09-4b8c-b174-8693653ac82f)

---

## Troubleshooting

### Library cublas64_12.dll is not found

If the below below is displayed in the logs then ensure that CUDA 12 is available, e.g. by installing the [CUDA Toolkit 12](https://developer.nvidia.com/cuda-downloads)

```console
ERROR - Failed to transcribe audio: Library cublas64_12.dll is not found or cannot be loaded
```

### ValueError: Requested int8_float16 compute type ###

For some GPUs which do not support certain compute types, i.e. do not have tensor cores, the below message will be output to the logs:

```
WARNING - GPU does not have tensor cores, major=6, minor=1
```

WhisperAttack can detect this and will fallback on supported values for cuda cores.

If however the below error message is displayed then the `settings.cfg` file can be updated.

```console
ValueError: Requested int8_float16 compute type, but the target device or backend do not support efficient int8_float16 computation.
```

The `settings.cfg` file can be updated to add the below entry:

```console
whisper_core_type=standard
```

---

## Performance (AI Model)

If WhisperAttack is causing significant studders, It is likely that the current model is overloading your VRAM. If this is the case, studders can be alleviated by changing the model size (extra information on the models is available in the table below) in the `settings.cfg` file as follows:

```console
whisper_model=base.en
```

- Using smaller models will reduce VRAM and compute costs. See below for a full speed breakdown
- First activation with a new AI model will prompt the model to be downloaded which may take an extended amount of time depending on internet speed.

---

## Available models and languages

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

Enjoy your local (offline) speech recognition with OpenAI Whisper + VoiceAttack! If you run into issues, open an issue or check the logs for clues.
