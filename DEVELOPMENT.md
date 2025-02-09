# Building a WhisperAttack Server Executable

These instructions document how to build an application executable (exe) version of Whisper Attack. This can be run as a standard application without needing to install Python or any Python packages.

## Logging

Because the executable won't be running as a console application the logging needs to go to a file so that it can be viewed. The log file will be written to `C:\Users\username\AppData\Local\WhisperAttack\WhisperAttack.log` file. The log file will be overwritten every time the WhisperAttack server is started.

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

**NOTE**: If you want to run the `whisper_server.py` file locally without building and running an executable you can reinstall these using the below command:

```console
pip install -r requirements.txt
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

Run PyInstaller to create an executable of WhisperAttack, this will be created in the `dist\whisper_server` directory.

The `--noconsole` parameter means that when WhisperAttack is run no window is displayed. A WhisperAttack icon will be displayed in the Windows system tray.

```console
pyinstaller --onedir --noconsole whisper_server.py
```

### Packaging the application

Copy the following files into the `dist\whisper_server` directory as these must be located beside the executable

- settings.cfg
- word_mappings.txt
- fuzzy_words.txt
- whisper_attack_icon.png

The `whisper_server` folder, and all its contents (including the `_internal` folder), can be moved to the location of your choice.

The contents of the `whisper_server` folder can be zipped up if needing to distribute.

### Running the application

Double-click the `whisper_server.exe` file to run it. It may take a little while the first time it runs as it downloads the Whisper model.

Check the `C:\Users\username\AppData\Local\WhisperAttack\WhisperAttack.log` file. You may need to close and reopen the log file if your editor does not automatically update when lines are added to the file.

The application can be exited using either by right-clicking the WhisperAttack icon in the system tray, or by closing VoiceAttack.

### Cleaning up after the build

Once you are happy with the executable and do not need to rebuild with any further changes you can run the below command to deactivate the virtual environment and then close the terminal.

```console
.\.venv\Scripts\deactivate.bat
```
