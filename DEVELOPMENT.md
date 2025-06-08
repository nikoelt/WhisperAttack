# Building a WhisperAttack Server Executable

These instructions document how to build an application executable (exe) version of Whisper Attack. This can be run as a standard application without needing to install Python or any Python packages.

## Requirements

- **Python 3.11** (must be in your PATH)
  - Install from [python.org](https://www.python.org/downloads/release/python-3119), use [this link](https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe) for the Windows (64-bit) installer.
  - NOTE! v3.12 3.13 etc... will NOT work - PyTorch only provides official wheels for Python 3.8 → 3.11

![python](https://github.com/user-attachments/assets/1b23945c-2635-40ea-a8b1-51bbfbe2a7b4)

## Logging

Because the executable won't be running as a console application the logging needs to go to a file so that it can be viewed. The log file will be written to `C:\Users\username\AppData\Local\WhisperAttack\WhisperAttack.log` file. The log file will be overwritten every time the WhisperAttack server is started.

## Running the WhisperAtack Python app locally

WhisperAttack can be run locally without needing to build an executable during development.

Install the dependencies using the below command:

```console
pip install -r requirements.txt
```

**NOTE:** These dependencies should be removed prior to building the executable as per the instructions for starting with a clean environment.

Run WhisperAttack using the below command:

```console
python whisper_attack.py
```

## Creating the executable file

The commands below will build an executable version of the WhisperAttack server.

### PowerShell

The command prompt will be prefixed with `PS` to show that this is a PowerShell terminal. The commands below are being run from within the directory containing the WhisperAttack source code, in this example it is `D:\src\github\WhisperAttack`.

Allow PowerShell to execute the command to activate the Python virtual environment. The `-Scope Process` means that it is allowed just for this process, e.g. if run from within Visual Studio Code, vs. being set globally which could be a security risk.

```console
Set-ExecutionPolicy Unrestricted -Scope Process
```

### Starting with a clean environment

When PyInstaller builds the application it will look in your local Python library paths, as well as the paths in the virtual environment
to locate the packages it needs. To ensure that you have a clean environment you should uninstall any packages in your local cache.

Run the below command to uninstall the packages that will be reinstalled as part of the build. Accept all prompts to remove packages.

```command
pip uninstall -r requirements.txt
```

### Building the application

Create the Python virtual environment so that dependencies are installed here to keep separate from the global ones.

```console
python -m venv .venv
```

Activate the virtual environment so you're working in it. Your command prompt will now have a `(.venv)` prefix so that you know it is active.

```console
.venv\Scripts\Activate.ps1
```

Install PyInstaller so that it can build the executable. This must be done after activating the virtual environment
so that it can locate the dependencies in the virtual environment.

```console
pip install pyinstaller
```

Install the Python dependencies required by WhisperAttack.

```console
pip install -r requirements.txt
```

Run PyInstaller to create an executable of WhisperAttack, this will be created in the `dist\whisper_attack` directory.

The `--noconsole` parameter means that when WhisperAttack is run no window is displayed. A WhisperAttack icon will be displayed in the Windows system tray.

```console
pyinstaller --onedir --noconsole whisper_attack.py
```

### Packaging the application

Copy the following files into the `dist\whisper_attack` directory as these must be located beside the executable

- settings.cfg
- fuzzy_words.txt
- word_mappings.txt
- whisper_attack_icon.png
- add_icon.png

The `whisper_attack` folder, and all its contents (including the `_internal` folder), can be moved to the location of your choice. Rename `whisper_attack.exe` to `WhisperAttack.exe`.

The contents of the `whisper_attack` folder can be zipped up if needing to distribute.

### Running the application

Double-click the `WhisperAttack.exe` file to run it. It may take a little while the first time it runs, especially if it is downloading the Whisper model if it was not already installed.

An application window will be opened when it has started up and display logging information information. Full information is also logged to the `C:\Users\username\AppData\Local\WhisperAttack\WhisperAttack.log` file. You may need to close and reopen the log file if your editor does not automatically update when lines are added to the file.

The application can be exited using either by right-clicking the WhisperAttack icon in the system tray, or by closing VoiceAttack.

### Cleaning up after the build

Once you are happy with the executable and do not need to rebuild with any further changes you can run the below command to deactivate the virtual environment and then close the terminal.

```console
.\.venv\Scripts\deactivate.bat
```

Delete the `.venv`, `build`, and `dist` directories.
