# Privacy Screen — using Python

Privacy Screen is a lightweight Windows desktop utility for projector privacy. Press a configurable global hotkey (default: `F8`) to collect normal application windows from the external display onto the laptop, then cover the projector with a solid black, always-on-top window. The laptop remains usable.

The app does not disconnect the projector or cable. If Windows starts in Duplicate mode, the app temporarily changes to Extend and returns to Duplicate when privacy is disabled. If Windows is already extended, it stays extended when privacy is disabled.

## Features

- Configurable global hotkey, including combinations such as `Ctrl+Shift+P`
- Automatic external-screen detection, with an optional specific-projector selection
- Automatic Duplicate → Extend → Duplicate switching
- Moves visible application windows from the projector to the laptop before covering it
- Preserves Extended mode when it was already active
- Correct placement for monitors with negative coordinates and mixed DPI scaling
- Borderless, black, always-on-top overlay
- System tray menu for Toggle, Settings, and Exit
- Settings saved under `%APPDATA%\PrivacyScreen\settings.json`
- Small, maintainable Python modules with no keyboard-hook package

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer

## Run from source

Open Command Prompt or PowerShell in this folder, then run:

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

The settings window appears on the first run. Keep **Automatic external screen** unless you have multiple external displays, enter a hotkey, and click **Save**. Closing the settings window keeps the application in the system tray.

## Normal use

1. Connect the projector in either **Duplicate** or **Extend** mode.
2. Press `F8`. If necessary, Windows changes to Extend. Visible application windows on the projector move to the laptop, then the projector turns black.
3. Press `F8` again. The black overlay closes. Windows returns to Duplicate only if that was the starting mode; otherwise Extended mode remains active.

A brief flicker during either display-mode change is normal. Windows may rearrange some application windows when changing modes.

## Build a Windows EXE

The easiest option is to double-click `build.bat`. It creates a virtual environment, installs pinned dependencies, and builds:

```text
dist\PrivacyScreen.exe
```

Alternatively, build manually:

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "PrivacyScreen" main.py
```

Copy `dist\PrivacyScreen.exe` wherever you want. No Python installation is required on the destination computer.

## Optional: launch at sign-in

1. Press `Win+R` and enter `shell:startup`.
2. Create a shortcut to `PrivacyScreen.exe` in that folder.

## Notes

- If Windows reports that a hotkey cannot be registered, another application is already using it. Choose another combination.
- Windows may prevent the app from moving elevated Administrator windows or exclusive full-screen games. Normal browser, email, Office, and desktop application windows are supported.
- Full-screen applications using exclusive display mode can appear above normal desktop windows. Borderless-windowed mode is recommended in that case.
- The overlay intentionally hides the mouse pointer only while it is over the black window.

## Project structure

```text
PrivacyScreen/
├── main.py                       Application entry point
├── build.bat                     One-click EXE build
├── requirements.txt              Runtime and build dependencies
└── privacy_screen/
    ├── app.py                    UI and application coordination
    ├── config.py                 Persistent settings
    ├── display_mode.py           Duplicate/Extend switching
    ├── models.py                 Monitor model
    ├── overlay.py                Black topmost overlay
    ├── tray.py                   System tray integration
    └── windows_api.py            Monitor enumeration and global hotkey
```
