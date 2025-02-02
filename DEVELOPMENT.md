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
PS D:\src\github\WhisperAttack> Set-ExecutionPolicy Unrestricted -Scope Process
```

### PyInstaller

The Python PyInstaller will be used to build the application.

Install PyInstaller to build the exe file.

```console
PS D:\src\github\WhisperAttack> pip install pyinstaller
```

### Building the application

Create the Python virtual environment so that dependencies are installed here to keep separate from the global ones.

```console
PS D:\src\github\WhisperAttack> python -m venv .venv
```

Activate the virtual environment so you're working in it. Your command prompt will now have a `(.venv)` prefix so that you know it is active.

```console
PS D:\src\github\WhisperAttack> .venv\Scripts\activate
```

Install the Python dependencies required by WhisperAttack.

```console
(.venv) PS D:\src\github\WhisperAttack> pip install -r requirements.txt
```

Run PyInstaller to create an executable of WhisperAttack, this will be created in the `dist` directory.

```console
(.venv) PS D:\src\github\WhisperAttack> pyinstaller --onefile whisper_server.py
```

### Running the application

Copy the `dist\whisper_server.exe` file into the same directory containing the `settings.cfg`, `word_mappings.txt`, and `fuzzy_words.txt` files so that it can locate these when it is run.

Double-click the `whisper_server.exe` file to run it. It may take a little while the first time it runs as it downloads the Whisper model.

Check the `C:\Users\username\AppData\Local\WhisperAttack\WhisperAttack.log` file. You may need to close and reopen the log file if your editor does not automatically update when lines are added to the file.

### Cleaning up after the build

Once you are happy with the executable and do not need to rebuild with any further changes you can run the below command to deactivate the virtual environment and then close the terminal.

```console
(.venv) PS D:\src\github\WhisperAttack> .\.venv\Scripts\deactivate.bat
```
