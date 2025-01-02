# OpenAI Whisper integration for VoiceAttack 

This is a fork for further integration of **KneeboardWhisper** by the amazing creator [@BojoteX](https://github.com/BojoteX/KneeboardWhisper).  
A special thank you goes to **hradec**, whose original script used Google Voice Recognition, and **@SeaTechNerd83** for helping combine the two approaches.

In short @SeaTechNerd83 and I combined the two scripts to run voice commands through Whisper using BokoteX code, and then push it into Voice Attack using hradec's code

### What’s Different?
We replaced Google Speech Recognition with **OpenAI Whisper** for **local** (offline) speech recognition. This means:
1. **No reliance on online services** (beyond the first-time model download).
2. **Better accuracy** than older Windows Speech Recognition.
3. **Ability to leverage your GPU** for much faster transcription.

> **Note:** On first launch, Whisper will auto-download any missing model(s). This can take time. You can also experiment with different model sizes—like `tiny` or `base`—for faster speed (though possibly less accuracy).

---

## Overview

This guide helps you set up a system to:
- **Record** your voice in **DCS World** (or any simulator) using **VoiceAttack**.
- **Transcribe** that audio with **Whisper**.
- (Optionally) **Paste** the text into the DCS Kneeboard via `CTRL+ALT+P` or any other binding.

![Kneeboard Whisper](https://raw.githubusercontent.com/BojoteX/KneeboardWhisper/main/kneeboardwhisper.png)

1. **`recorder.py`**: Captures your audio into `sample.wav`.
2. **`transcriber.py`**: Stops the recorder (if needed), runs Whisper locally to transcribe `sample.wav`, copies the text to your clipboard, and sends recognized text as a **VoiceAttack** command.

---

## Prerequisites

1. **Python 3.11**  
   - Install from the Microsoft Store or [python.org](https://www.python.org/downloads/).
2. **VoiceAttack**  
   - Needed for controlling scripts and issuing commands in your simulator/game.
3. **DCS World** (optional, if you want to paste transcribed text into kneeboard).
4. **NVIDIA GPU** (recommended)  
   - Whisper can run on CPU, but GPU (CUDA) provides a big speed boost.

---

## Step 1: Install Python 3.11

1. Open the **Microsoft Store** and install **Python 3.11**, or download from [python.org](https://www.python.org/downloads/).
2. Verify the installation by opening a command prompt (`Win + R`, type `cmd`) and running:

   ```bash
   python --version
   ```

   It should show **Python 3.11.x**.

---

## Step 2: Install Required Python Modules

Open a **command prompt** and install the following:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu118
pip install openai-whisper sounddevice soundfile pyperclip keyboard wcwidth
```

- **`torch`** from the `cu118` index enables **CUDA** GPU support (if you have an NVIDIA card).
- **`openai-whisper`** is the local transcription engine.
- **`sounddevice`** & **`soundfile`** handle audio capture/playback.
- **`pyperclip`** for copying recognized text to the clipboard.
- **`keyboard`** for advanced hotkey or automation in scripts.
- **`wcwidth`** for neat text justification (optional).

---

## Step 3: Configure VoiceAttack

You’ll create **two** commands in VoiceAttack—one to **start** recording and one to **stop & transcribe**:

1. **Command 1**: Start Recording
   - **Press** your chosen joystick or keyboard button.
   - Action: **Run an Application** → select `recorder.py`.
   - This launches `recorder.py` to capture your voice in the background.

2. **Command 2**: Stop & Transcribe
   - **Release** that same joystick or keyboard button.
   - Action: **Run an Application** → select `transcriber.py`.
   - This stops the recorder (if it’s running), finalizes `sample.wav`, transcribes it with Whisper, and feeds the recognized text to VoiceAttack as a command.

> **Pro Tip**: In the VoiceAttack command editor, under “When I press/release this button,” look for **“Shortcut is invoked only when all keys are released”** to have the second command fire on release.

---

## Step 4: (Optional) DCS Kneeboard Integration

If you want to paste transcribed text directly into your **DCS Kneeboard**:

1. In DCS, bind **`CTRL+ALT+P`** (or any shortcut) to the kneeboard paste function.
2. By default, the transcribed text is already copied to your clipboard.
3. Press `CTRL+ALT+P` in-game, or let VoiceAttack trigger it, to paste the text into your kneeboard.

![Assignments](https://raw.githubusercontent.com/BojoteX/KneeboardWhisper/main/assignments.png)

---

## Step 5: Test It

### Method 1: Manual Terminal Test

1. Open two terminals in the folder with your scripts.
2. In the first terminal:

   ```bash
   python recorder.py
   ```

   You can talk into your mic; it records to `sample.wav`.

3. In the second terminal:

   ```bash
   python transcriber.py --device GPU
   ```

   This stops the recorder, transcribes with Whisper on GPU, copies to clipboard, and calls VoiceAttack with the recognized text.

### Method 2: VoiceAttack

- **Press** your assigned PTT button → `recorder.py` starts capturing.
- **Release** the button → `transcriber.py` runs, transcribes, and sends the text to VoiceAttack.

---

## Troubleshooting

1. **Torch Fallback to CPU**  
   - If you see logs saying “Whisper model loaded on CPU,” your GPU might be unavailable or `torch.cuda.is_available()` is `False`. Confirm you installed the CUDA build of PyTorch and have proper GPU drivers.

2. **VoiceAttack.exe Not Found**  
   - Check that `transcriber.py` has the correct path to `VoiceAttack.exe`, e.g.:  
     ```
     C:\Program Files (x86)\VoiceAttack\VoiceAttack.exe
     ```

3. **No Clipboard Copy**  
   - Ensure `pyperclip` is installed. Some systems might block or restrict clipboard usage.

4. **DCS Keybind**  
   - If you’re not seeing pasted text in DCS, confirm that `CTRL+ALT+P` is actually set in the DCS controls.

---

## Final Notes

- **Model Sizes**: For faster recognition, try `tiny` or `base`. For more accurate results, use `small`, `medium`, or `large`.  
- **First-Time Whisper Download**: The first run might take a while to download the model. Subsequent runs should be faster.
- **Goodbye Windows Speech**: This fully replaces older Windows or Google-based speech recognition with a local, GPU-accelerated solution.

Enjoy your improved local speech recognition with **VoiceAttack + Whisper**!
```
