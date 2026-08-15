"""Convert text into speech and save it as an MP3 file.

Uses Microsoft Edge's neural text-to-speech voices (via the edge-tts library).
Requires an internet connection. No API key needed.

Usage examples:
    python text_to_speech.py "Hello, welcome to my video."
    python text_to_speech.py --file script.txt --output narration.mp3
    python text_to_speech.py --text "..." --voice en-US-AriaNeural --rate -10%
    python text_to_speech.py --list-voices --locale en-US
"""

import argparse
import asyncio
import sys

import edge_tts

DEFAULT_VOICE = "en-US-ChristopherNeural"


async def synthesize(text: str, voice: str, output_path: str, rate: str, pitch: str) -> None:
    """Generate speech for `text` and save it as an MP3 file."""
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)


async def list_voices(locale: str | None) -> None:
    """Print all available voices, optionally filtered by locale (e.g. en-US)."""
    voices = await edge_tts.list_voices()
    if locale:
        voices = [v for v in voices if v["Locale"].lower() == locale.lower()]
    for v in sorted(voices, key=lambda v: v["ShortName"]):
        print(f'{v["ShortName"]}  ({v["Locale"]}, {v["Gender"]})  - {v["FriendlyName"]}')


def load_text(text: str | None, file_path: str | None) -> str:
    """Get the text to convert: from the --text/positional arg or a file."""
    if text and file_path:
        sys.exit("Error: provide either text or --file, not both.")
    if file_path:
        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read().strip()
        except OSError as exc:
            sys.exit(f"Error: could not read file {file_path!r}: {exc}")
    if not text:
        sys.exit("Error: provide the text to convert (as an argument or via --file).")
    return text


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert text to speech and save it as an MP3 file (uses Microsoft Edge neural voices).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("text", nargs="?", help="The text to convert to speech.")
    parser.add_argument("--file", help="Read the text from a UTF-8 text file instead.")
    parser.add_argument("--output", "-o", default="output.mp3", help="Output MP3 file path (default: output.mp3).")
    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help=f"Voice to use (default: {DEFAULT_VOICE}). Run with --list-voices to see all.",
    )
    parser.add_argument("--rate", default="+0%", help="Speaking rate, e.g. +10%% (faster) or -15%% (slower). Default: +0%%.")
    parser.add_argument("--pitch", default="+0Hz", help="Pitch shift, e.g. +20Hz (higher) or -20Hz (lower). Default: +0Hz.")
    parser.add_argument("--list-voices", action="store_true", help="List available voices and exit.")
    parser.add_argument("--locale", help="Filter --list-voices by locale, e.g. en-US, de-DE, es-ES.")
    args = parser.parse_args()

    if args.list_voices:
        asyncio.run(list_voices(args.locale))
        return

    text = load_text(args.text, args.file)
    print(f"Synthesizing {len(text)} characters with voice {args.voice!r} ...")
    try:
        asyncio.run(synthesize(text, args.voice, args.output, args.rate, args.pitch))
    except Exception as exc:  # edge-tts raises on network errors / bad voices
        sys.exit(f"Error: speech synthesis failed: {exc}")
    print(f"Saved speech to {args.output}")


if __name__ == "__main__":
    main()
