<div align="center">

# Text to Speech Studio

Convert text into natural-sounding MP3 speech using **Microsoft Edge's neural voices**.
No API keys. No accounts. No cost — just an internet connection.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-windows%20%7C%20macOS%20%7C%20linux-lightgrey)](#installation)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/alwolfie/text-to-speech-studio/pulls)

<!-- After creating your GitHub repo, add live badges, e.g.:
[![GitHub stars](https://img.shields.io/github/stars/alwolfie/text-to-speech-studio?style=social)](https://github.com/alwolfie/text-to-speech-studio)
[![GitHub contributors](https://img.shields.io/github/contributors/alwolfie/text-to-speech-studio)](https://github.com/alwolfie/text-to-speech-studio/graphs/contributors)
-->

</div>

---

## Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
  - [GUI](#gui)
  - [Command line](#command-line)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **100+ neural voices** across many languages and locales, filterable by region
- **Full voice controls** — speaking rate (−50% to +50%) and pitch shift
- **Auto file naming** — generates a unique, readable name from your text plus a timestamp; manual naming also available
- **In-app MP3 playback** — preview your audio with the built-in player, no external software needed
- **Two interfaces** — a friendly GUI and a scriptable command-line tool
- **Zero configuration** — no API keys, no accounts, no local model downloads

## Screenshots

<!-- TODO: Add a screenshot of the GUI here, e.g.
![GUI](screenshots/gui.png)
-->

## Requirements

- **Python 3.10+**
- **An internet connection** — speech is synthesized by Microsoft Edge's online neural voices service

## Installation

```bash
git clone https://github.com/alwolfie/text-to-speech-studio.git
cd text-to-speech-studio
pip install -r requirements.txt
```

## Usage

### GUI

```bash
python tts_gui.py
```

On Windows, you can also double-click `start_gui.bat`.

1. Type or paste your text into the editor
2. Pick a voice, and adjust speed/pitch if you like
3. Click **Generate MP3** — the file is saved to disk
4. Click **Play** to hear it instantly inside the app, **Stop** to interrupt

The **Auto-generate file name** checkbox (on by default) creates unique names like
`hello_welcome_to_my_video_20260815_143022.mp3`; uncheck it to name files yourself.

### Command line

```bash
# Basic conversion
python text_to_speech.py "Hello, welcome to my video."

# Read text from a file, custom voice, slower pace
python text_to_speech.py --file script.txt --output narration.mp3 \
    --voice en-US-AriaNeural --rate -10%

# List available voices (optionally filtered by locale)
python text_to_speech.py --list-voices --locale en-US
```

**CLI reference**

| Option | Description | Default |
| --- | --- | --- |
| `text` | Text to convert to speech (positional) | — |
| `--file` | Read the text from a UTF-8 file instead | — |
| `-o, --output` | Output MP3 file path | `output.mp3` |
| `--voice` | Voice to use (see `--list-voices`) | `en-US-ChristopherNeural` |
| `--rate` | Speaking rate, e.g. `+10%` (faster), `-15%` (slower) | `+0%` |
| `--pitch` | Pitch shift, e.g. `+20Hz` (higher), `-20Hz` (lower) | `+0Hz` |
| `--list-voices` | List available voices and exit | — |
| `--locale` | Filter `--list-voices` by locale, e.g. `en-US`, `de-DE` | — |

## Project Structure

```
text-to-speech-studio/
├── tts_gui.py          # Tkinter GUI (auto-naming + in-app playback)
├── text_to_speech.py   # Command-line tool
├── requirements.txt    # Python dependencies
├── start_gui.bat       # Windows launcher
├── README.md
└── LICENSE
```

## Contributing

Contributions are welcome! This is a small, beginner-friendly project — a great
place to make your first open-source contribution.

- **Found a bug or want a feature?** Open an issue.
- **Want to fix it yourself?** Fork the repo, make your change, and submit a pull request.
- Keep changes small and focused, and verify your code compiles:
  `python -m py_compile tts_gui.py text_to_speech.py`

## License

This project is licensed under the [MIT License](LICENSE).
