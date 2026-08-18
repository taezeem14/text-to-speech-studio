"""Comprehensive Automated Test Suite for Text-to-Speech Studio."""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from tts_engine import BUILTIN_PRESETS, DEFAULT_VOICE, TTSStudioEngine


class TestTTSStudioEngine(unittest.TestCase):
    """Test suite covering TTS Studio core engine, subtitles, and dialogue."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.mkdtemp(prefix="tts_test_")
        cls.engine = TTSStudioEngine(data_dir=cls.temp_dir)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_01_text_metrics(self) -> None:
        text = "Hello world! This is a comprehensive test of Text to Speech Studio. It measures speaking speed."
        metrics = self.engine.analyze_text(text, rate_str="+10%")
        self.assertGreater(metrics.word_count, 10)
        self.assertGreater(metrics.char_count, 50)
        self.assertGreater(metrics.estimated_duration_seconds, 1.0)
        self.assertTrue(
            "Elementary" in metrics.reading_grade_level or "Standard" in metrics.reading_grade_level
        )

    def test_02_presets(self) -> None:
        presets = self.engine.get_all_presets()
        self.assertIn("tiktok", presets)
        self.assertIn("podcast", presets)
        self.assertIn("trailer", presets)
        self.assertIn("storyteller", presets)

        # Test custom preset creation
        self.engine.save_custom_preset("custom_hero", "Hero Voice", "Heroic tone", "en-US-GuyNeural", "+10%", "+5Hz")
        presets_after = self.engine.get_all_presets()
        self.assertIn("custom_hero", presets_after)
        self.assertEqual(presets_after["custom_hero"]["voice"], "en-US-GuyNeural")

    def test_03_dialogue_parser(self) -> None:
        script = (
            "[Narrator | en-US-ChristopherNeural]: Once upon a time.\n"
            "[Alice | en-US-JennyNeural | rate=+5%]: Hello there!\n"
            "Bob: Nice to meet you."
        )
        lines = self.engine.parse_dialogue_script(script)
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0].speaker, "Narrator")
        self.assertEqual(lines[0].voice, "en-US-ChristopherNeural")
        self.assertEqual(lines[1].speaker, "Alice")
        self.assertEqual(lines[1].voice, "en-US-JennyNeural")
        self.assertEqual(lines[1].rate, "+5%")
        self.assertEqual(lines[2].speaker, "Bob")

    def test_04_single_synthesis_and_subtitles(self) -> None:
        out_file = Path(self.temp_dir) / "test_single.mp3"
        res = self.engine.synthesize_sync(
            text="Hello from the automated test suite! Audio generation is operational.",
            voice=DEFAULT_VOICE,
            output_path=str(out_file),
            generate_subtitles=True,
        )
        self.assertTrue(out_file.exists())
        self.assertGreater(len(res.audio_bytes), 1000)
        self.assertIsNotNone(res.srt_subtitles)
        self.assertIsNotNone(res.srt_path)
        self.assertTrue(Path(res.srt_path).exists())
        self.assertTrue(Path(res.vtt_path).exists())

        # Verify SRT format
        srt_content = Path(res.srt_path).read_text(encoding="utf-8")
        self.assertIn("-->", srt_content)
        self.assertIn("Hello from", srt_content)

    def test_05_dialogue_synthesis(self) -> None:
        script = (
            "[Narrator | en-US-ChristopherNeural]: Scene one.\n"
            "[Alice | en-US-JennyNeural]: Testing dialogue generator.\n"
            "[Bob | en-US-GuyNeural]: Confirmed working."
        )
        out_file = Path(self.temp_dir) / "test_dialogue.mp3"
        res = asyncio.run(
            self.engine.synthesize_dialogue(
                script_text=script,
                output_path=str(out_file),
                generate_subtitles=True,
            )
        )
        self.assertTrue(out_file.exists())
        self.assertGreater(len(res.audio_bytes), 2000)
        self.assertIsNotNone(res.srt_path)
        self.assertTrue(Path(res.srt_path).exists())
        srt_text = Path(res.srt_path).read_text(encoding="utf-8")
        self.assertIn("[Alice]", srt_text)
        self.assertIn("[Bob]", srt_text)

    def test_06_voice_filtering(self) -> None:
        voices = asyncio.run(self.engine.filter_voices(locale="en-US", gender="Female"))
        self.assertGreater(len(voices), 0)
        for v in voices:
            self.assertEqual(v.get("Gender"), "Female")
            self.assertIn("en-us", v.get("Locale", "").lower())


if __name__ == "__main__":
    unittest.main()
