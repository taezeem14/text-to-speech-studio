# Text to Speech Studio

Convert text into natural-sounding speech (MP3) using **Microsoft Edge's neural voices** — no API key required, just an internet connection.

Works two ways:
- **GUI** (`tts_gui.py`) — paste text, pick a voice, adjust speed/pitch, auto-name the file, and play it back right inside the app.
- **CLI** (`text_to_speech.py`) — quick scripted conversion from the terminal.

## Features

- 100+ neural voices across many languages (filterable by locale)
- Speed (−50% to +50%) and pitch controls
- **Auto file naming** — generates a unique name from your text + timestamp, or name files manually
- **In-app MP3 playback** — preview with the built-in player, no external software needed
- No API keys or accounts required

## Requirements

- Python 3.10+
- An internet connection (voices are synthesized by Microsoft Edge's online service)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### GUI

```bash
python tts_gui.py
```

On Windows you can also double-click `start_gui.bat`.

1. Type or paste your text
2. Pick a voice, adjust speed/pitch if you like
3. Click **Generate MP3** — the file is saved and ready to play
4. Click **Play** to hear it instantly, **Stop** to interrupt

### CLI

```bash
# Basic
python text_to_speech.py "Hello, welcome to my video."

# From a file, with a custom voice, slower pace
python text_to_speech.py --file script.txt --output narration.mp3 --voice en-US-AriaNeural --rate -10%

# List voices for a locale
python text_to_speech.py --list-voices --locale en-US
```

## Project layout

```
tts-studio/
├── tts_gui.py          # Tkinter GUI (auto-naming + in-app playback)
├── text_to_speech.py   # Command-line tool
├── requirements.txt    # edge-tts, pygame
└── start_gui.bat       # Windows launcher shortcut
```

## Contributing

Open source, welcome to contribute! Feel free to open issues and pull requests. Please keep changes small and focused, and make sure the code still runs with `python -m py_compile tts_gui.py text_to_speech.py`.

## License

[MIT](LICENSE)
