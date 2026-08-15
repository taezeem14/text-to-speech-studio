"""Text-to-Speech Studio Core Engine.

High-performance, async-first neural speech synthesis engine powered by
Microsoft Edge's neural voices. Supports subtitle extraction (SRT/VTT),
multi-speaker dialogue scripts, curated voice presets, text metrics,
and export history.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import edge_tts

DEFAULT_VOICE = "en-US-ChristopherNeural"

# Curated voice presets for popular content creation styles
BUILTIN_PRESETS: Dict[str, Dict[str, Any]] = {
    "tiktok": {
        "name": "TikTok / Reel Narrator",
        "description": "High-energy, punchy, crisp narration for short-form video",
        "voice": "en-US-AvaNeural",
        "rate": "+15%",
        "pitch": "+0Hz",
        "volume": "+0%",
    },
    "podcast": {
        "name": "Podcast Host",
        "description": "Deep, warm, engaging broadcast quality",
        "voice": "en-US-ChristopherNeural",
        "rate": "+0%",
        "pitch": "-5Hz",
        "volume": "+0%",
    },
    "storyteller": {
        "name": "Audiobook Storyteller",
        "description": "Expressive British accent, immersive storytelling cadence",
        "voice": "en-GB-SoniaNeural",
        "rate": "-5%",
        "pitch": "+0Hz",
        "volume": "+0%",
    },
    "trailer": {
        "name": "Epic Movie Trailer",
        "description": "Deep, cinematic, heavyweight dramatic tone",
        "voice": "en-US-GuyNeural",
        "rate": "-12%",
        "pitch": "-18Hz",
        "volume": "+15%",
    },
    "calm_asmr": {
        "name": "Meditative Calm / ASMR",
        "description": "Gentle, soothing, relaxed pace for meditation & sleep stories",
        "voice": "en-US-JennyNeural",
        "rate": "-20%",
        "pitch": "-4Hz",
        "volume": "-5%",
    },
    "news_anchor": {
        "name": "Breaking News Anchor",
        "description": "Authoritative, crisp, neutral journalistic cadence",
        "voice": "en-US-EricNeural",
        "rate": "+6%",
        "pitch": "+0Hz",
        "volume": "+0%",
    },
    "cyberpunk_ai": {
        "name": "Sci-Fi AI / Cyberpunk",
        "description": "Sharp, electronic, hyper-articulate digital voice",
        "voice": "en-US-AnaNeural",
        "rate": "+10%",
        "pitch": "+22Hz",
        "volume": "+5%",
    },
    "anime_upbeat": {
        "name": "Anime Energetic",
        "description": "Bubbly, youthful, high-spirited voice acting tone",
        "voice": "en-US-AriaNeural",
        "rate": "+18%",
        "pitch": "+16Hz",
        "volume": "+0%",
    },
    "hindi_rj": {
        "name": "Hindi Radio RJ",
        "description": "Energetic, expressive Hindi/Hinglish radio host",
        "voice": "hi-IN-MadhurNeural",
        "rate": "+6%",
        "pitch": "+0Hz",
        "volume": "+0%",
    },
    "spanish_latam": {
        "name": "Spanish Narration (LatAm)",
        "description": "Warm, authentic Latin American Spanish storytelling",
        "voice": "es-MX-JorgeNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "volume": "+0%",
    },
    "french_chic": {
        "name": "French Parisian Narration",
        "description": "Elegant, smooth Parisian French diction",
        "voice": "fr-FR-HenriNeural",
        "rate": "-4%",
        "pitch": "+0Hz",
        "volume": "+0%",
    },
    "japanese_anime": {
        "name": "Japanese Anime Voice",
        "description": "Polished, expressive Tokyo Japanese voice",
        "voice": "ja-JP-NanamiNeural",
        "rate": "+5%",
        "pitch": "+8Hz",
        "volume": "+0%",
    },
}


@dataclass
class TextMetrics:
    """Detailed analytics on text content."""
    char_count: int
    char_count_no_spaces: int
    word_count: int
    sentence_count: int
    estimated_duration_seconds: float
    reading_grade_level: str


@dataclass
class DialogueLine:
    """A single speaker line in a dialogue script."""
    speaker: str
    text: str
    voice: str
    rate: str = "+0%"
    pitch: str = "+0Hz"
    volume: str = "+0%"
    pause_after_ms: int = 350


@dataclass
class SynthesisResult:
    """Result of speech synthesis."""
    audio_path: str
    audio_bytes: bytes
    duration_estimate_sec: float
    character_count: int
    word_count: int
    voice: str
    srt_subtitles: Optional[str] = None
    vtt_subtitles: Optional[str] = None
    srt_path: Optional[str] = None
    vtt_path: Optional[str] = None


@dataclass
class HistoryItem:
    """Historical record of an audio generation."""
    id: str
    timestamp: str
    text_preview: str
    voice: str
    audio_path: str
    duration_sec: float
    char_count: int
    word_count: int
    has_subtitles: bool
    mode: str = "single"  # 'single', 'dialogue', 'batch'


class TTSStudioEngine:
    """Core synthesis and processing engine for Text-to-Speech Studio."""

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self.data_dir = Path(data_dir or Path.home() / ".tts_studio")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.presets_file = self.data_dir / "custom_presets.json"
        self.history_file = self.data_dir / "history.json"
        self.voices_cache_file = self.data_dir / "voices_cache.json"

        self._cached_voices: Optional[List[Dict[str, Any]]] = None
        self._custom_presets: Dict[str, Dict[str, Any]] = self._load_custom_presets()
        self._history: List[HistoryItem] = self._load_history()

    # ------------------------------------------------------------------ Metrics

    @staticmethod
    def analyze_text(text: str, rate_str: str = "+0%") -> TextMetrics:
        """Calculate word count, characters, sentences, and estimated duration."""
        stripped = text.strip()
        if not stripped:
            return TextMetrics(0, 0, 0, 0, 0.0, "N/A")

        char_count = len(stripped)
        char_no_spaces = len(re.sub(r"\s+", "", stripped))
        words = re.findall(r"\b\w+\b", stripped)
        
        # CJK fallback: if very few words detected but many characters, estimate by character count
        cjk_chars = len(re.findall(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', stripped))
        if cjk_chars > len(words) * 2:
            word_count = max(len(words), cjk_chars)
        else:
            word_count = len(words)

        sentences = [s for s in re.split(r'[.!?。！？।؟]+', stripped) if s.strip()]
        sentence_count = max(1, len(sentences))

        # Base speaking rate is ~150 words per minute (2.5 words/sec)
        rate_modifier = 1.0
        match = re.match(r"([+-]?\d+)%", rate_str.strip())
        if match:
            rate_modifier = 1.0 + (int(match.group(1)) / 100.0)
            rate_modifier = max(0.2, rate_modifier)

        wpm = 150.0 * rate_modifier
        duration_sec = (word_count / wpm) * 60.0 if word_count > 0 else 0.0

        # Rough Flesch-Kincaid / Automated Readability estimate
        if word_count > 0 and sentence_count > 0:
            avg_sentence_len = word_count / sentence_count
            avg_word_len = char_no_spaces / word_count
            ari = 4.71 * avg_word_len + 0.5 * avg_sentence_len - 21.43
            if ari < 6:
                grade = "Easy (Elementary)"
            elif ari < 10:
                grade = "Standard (High School)"
            elif ari < 14:
                grade = "Advanced (College)"
            else:
                grade = "Academic / Complex"
        else:
            grade = "Standard"

        return TextMetrics(
            char_count=char_count,
            char_count_no_spaces=char_no_spaces,
            word_count=word_count,
            sentence_count=sentence_count,
            estimated_duration_seconds=round(duration_sec, 2),
            reading_grade_level=grade,
        )

    # ------------------------------------------------------------------ Voices

    async def list_voices(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch all available Microsoft Edge neural voices (with local cache)."""
        if self._cached_voices and not force_refresh:
            return self._cached_voices

        # Check disk cache if not expired (< 7 days)
        if self.voices_cache_file.exists() and not force_refresh:
            try:
                mtime = os.path.getmtime(self.voices_cache_file)
                age_days = (datetime.datetime.now().timestamp() - mtime) / 86400.0
                if age_days < 7:
                    with open(self.voices_cache_file, "r", encoding="utf-8") as f:
                        self._cached_voices = json.load(f)
                        return self._cached_voices
            except Exception:
                pass

        try:
            voices = await edge_tts.list_voices()
            self._cached_voices = voices
            self._atomic_json_write(self.voices_cache_file, voices)
            return voices
        except Exception as exc:
            if self._cached_voices:
                return self._cached_voices
            if self.voices_cache_file.exists():
                with open(self.voices_cache_file, "r", encoding="utf-8") as f:
                    self._cached_voices = json.load(f)
                return self._cached_voices
            raise RuntimeError(f"Cannot list voices and no cache available: {exc}") from exc

    def list_voices_sync(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Synchronous wrapper for list_voices."""
        try:
            return asyncio.run(self.list_voices(force_refresh=force_refresh))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self.list_voices(force_refresh=force_refresh))
            finally:
                loop.close()

    async def filter_voices(
        self,
        locale: Optional[str] = None,
        gender: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Filter voices by locale, gender, or search keyword."""
        voices = await self.list_voices()
        results = []
        q = (search_query or "").lower().strip()
        loc = (locale or "").lower().strip()
        gen = (gender or "").lower().strip()

        for v in voices:
            v_short = v.get("ShortName", "")
            v_friendly = v.get("FriendlyName", "")
            v_loc = v.get("Locale", "").lower()
            v_gen = v.get("Gender", "").lower()

            if loc and loc not in v_loc:
                continue
            if gen and gen != v_gen:
                continue
            if q and (q not in v_short.lower() and q not in v_friendly.lower() and q not in v_loc):
                continue

            results.append(v)

        return sorted(results, key=lambda v: v.get("ShortName", ""))

    # ---------------------------------------------------------------- Synthesis

    def _normalize_tts_param(self, value: str, suffix: str) -> str:
        """Normalize rate/pitch/volume params to edge-tts format (+N% or +NHz)."""
        value = value.strip()
        if not value:
            return f"+0{suffix}"
        # Already properly formatted
        if re.match(r'^[+-]\d+' + re.escape(suffix) + r'$', value):
            return value
        # Has number but missing sign
        m = re.match(r'^(\d+)' + re.escape(suffix) + r'?$', value)
        if m:
            return f"+{m.group(1)}{suffix}"
        # Negative without suffix
        m = re.match(r'^(-\d+)' + re.escape(suffix) + r'?$', value)
        if m:
            return f"{m.group(1)}{suffix}"
        return f"+0{suffix}"

    async def synthesize(
        self,
        text: str,
        voice: str = DEFAULT_VOICE,
        output_path: Optional[str] = None,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%",
        generate_subtitles: bool = False,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> SynthesisResult:
        """Synthesize text into neural MP3 audio with optional SRT/VTT subtitles."""
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Input text cannot be empty.")

        if output_path is None:
            output_path = self.generate_auto_filename(cleaned_text)

        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if progress_cb:
            progress_cb(f"Connecting to neural speech service with voice {voice}...")

        rate = self._normalize_tts_param(rate, '%')
        pitch = self._normalize_tts_param(pitch, 'Hz')
        volume = self._normalize_tts_param(volume, '%')

        communicate = edge_tts.Communicate(
            text=cleaned_text,
            voice=voice,
            rate=rate,
            pitch=pitch,
            volume=volume,
        )

        audio_bytes = bytearray()
        submaker = edge_tts.SubMaker() if generate_subtitles else None

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes.extend(chunk["data"])
            elif generate_subtitles and submaker is not None:
                if chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                    submaker.feed(chunk)

        # Write audio file
        with open(out_path, "wb") as f:
            f.write(audio_bytes)

        srt_text: Optional[str] = None
        vtt_text: Optional[str] = None
        srt_file: Optional[str] = None
        vtt_file: Optional[str] = None

        if generate_subtitles and submaker is not None:
            srt_raw = submaker.get_srt()
            if srt_raw.strip():
                srt_text = srt_raw
                vtt_text = self._convert_srt_to_vtt(srt_raw)

                srt_file = str(out_path.with_suffix(".srt"))
                vtt_file = str(out_path.with_suffix(".vtt"))

                with open(srt_file, "w", encoding="utf-8") as f:
                    f.write(srt_text)
                with open(vtt_file, "w", encoding="utf-8") as f:
                    f.write(vtt_text)

        metrics = self.analyze_text(cleaned_text, rate)

        result = SynthesisResult(
            audio_path=str(out_path.resolve()),
            audio_bytes=bytes(audio_bytes),
            duration_estimate_sec=metrics.estimated_duration_seconds,
            character_count=metrics.char_count,
            word_count=metrics.word_count,
            voice=voice,
            srt_subtitles=srt_text,
            vtt_subtitles=vtt_text,
            srt_path=srt_file,
            vtt_path=vtt_file,
        )

        # Save to history
        self._record_history(
            text=cleaned_text,
            voice=voice,
            audio_path=result.audio_path,
            duration=result.duration_estimate_sec,
            char_count=result.character_count,
            word_count=result.word_count,
            has_subs=bool(generate_subtitles and srt_file),
            mode="single",
        )

        if progress_cb:
            progress_cb(f"Speech saved successfully to {out_path.name}")

        return result

    def synthesize_sync(self, *args: Any, **kwargs: Any) -> SynthesisResult:
        """Synchronous wrapper for synthesize."""
        try:
            return asyncio.run(self.synthesize(*args, **kwargs))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self.synthesize(*args, **kwargs))
            finally:
                loop.close()

    # -------------------------------------------------------- Dialogue Script

    @staticmethod
    def parse_dialogue_script(
        script_text: str,
        default_voice_map: Optional[Dict[str, str]] = None,
    ) -> List[DialogueLine]:
        """Parse a multi-speaker script.

        Supported syntax formats:
            [Narrator | en-US-ChristopherNeural | rate=+0% | pitch=+0Hz]: Once upon a time...
            [Alice | en-US-JennyNeural]: Hello Bob!
            Alice: How are you today?
            Bob: I am great!
        """
        voice_map = default_voice_map or {}
        lines: List[DialogueLine] = []

        raw_lines = script_text.strip().split("\n")
        for raw_line in raw_lines:
            line_str = raw_line.strip()
            if not line_str or line_str.startswith("#"):
                continue

            # Bracket format: [Speaker | Voice? | params?]: Text
            bracket_match = re.match(r"^\[(.*?)\]\s*:\s*(.+)$", line_str)
            if bracket_match:
                header, text_content = bracket_match.group(1).strip(), bracket_match.group(2).strip()
                tokens = [t.strip() for t in header.split("|")]
                speaker = tokens[0]
                voice = voice_map.get(speaker, DEFAULT_VOICE)
                rate = "+0%"
                pitch = "+0Hz"
                volume = "+0%"

                for token in tokens[1:]:
                    if token.startswith("rate="):
                        rate = token.split("=", 1)[1]
                    elif token.startswith("pitch="):
                        pitch = token.split("=", 1)[1]
                    elif token.startswith("volume="):
                        volume = token.split("=", 1)[1]
                    elif "Neural" in token or "-" in token:
                        voice = token

                lines.append(
                    DialogueLine(
                        speaker=speaker,
                        text=text_content,
                        voice=voice,
                        rate=rate,
                        pitch=pitch,
                        volume=volume,
                    )
                )
                continue

            # Colon format: Speaker: Text
            colon_match = re.match(r"^([^\s:][^:]*?)\s*:\s*(.+)$", line_str)
            if colon_match:
                speaker = colon_match.group(1).strip()
                text_content = colon_match.group(2).strip()
                voice = voice_map.get(speaker, DEFAULT_VOICE)
                lines.append(DialogueLine(speaker=speaker, text=text_content, voice=voice))
                continue

            # Fallback narration line
            lines.append(DialogueLine(speaker="Narrator", text=line_str, voice=voice_map.get("Narrator", DEFAULT_VOICE)))

        return lines

    async def synthesize_dialogue(
        self,
        script_text: str,
        output_path: Optional[str] = None,
        default_voice_map: Optional[Dict[str, str]] = None,
        generate_subtitles: bool = True,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> SynthesisResult:
        """Synthesize a multi-speaker conversation into a master audio track and subtitles."""
        parsed_lines = self.parse_dialogue_script(script_text, default_voice_map)
        if not parsed_lines:
            raise ValueError("Script does not contain any valid dialogue lines.")

        if output_path is None:
            first_words = re.sub(r"[^A-Za-z0-9]+", "_", parsed_lines[0].text[:30]).strip("_")
            output_path = f"dialogue_{first_words}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"

        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        master_audio_bytes = bytearray()
        all_srt_entries: List[str] = []
        current_time_ms = 0
        srt_counter = 1
        total_words = 0
        total_chars = 0

        total_lines = len(parsed_lines)
        for idx, line in enumerate(parsed_lines, start=1):
            if progress_cb:
                progress_cb(f"Synthesizing [{idx}/{total_lines}] {line.speaker} ({line.voice})...")

            comm = edge_tts.Communicate(
                text=line.text,
                voice=line.voice,
                rate=line.rate,
                pitch=line.pitch,
                volume=line.volume,
            )

            segment_audio = bytearray()
            segment_submaker = edge_tts.SubMaker() if generate_subtitles else None

            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    segment_audio.extend(chunk["data"])
                elif generate_subtitles and segment_submaker is not None:
                    if chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                        segment_submaker.feed(chunk)

            # Append audio bytes
            master_audio_bytes.extend(segment_audio)

            # Calculate segment duration (approx from audio byte rate for 24kHz MP3 mono: ~6000 bytes/sec)
            seg_duration_ms = int((len(segment_audio) / 6000.0) * 1000)
            if seg_duration_ms < 500:
                seg_duration_ms = 500

            # Subtitle offset calculation
            if generate_subtitles and segment_submaker is not None:
                srt_data = segment_submaker.get_srt()
                if srt_data.strip():
                    for block in srt_data.strip().split("\n\n"):
                        block_lines = block.split("\n")
                        if len(block_lines) >= 3:
                            time_match = re.match(
                                r"(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)",
                                block_lines[1],
                            )
                            if time_match:
                                start_ms = self._srt_time_to_ms(time_match.group(1)) + current_time_ms
                                end_ms = self._srt_time_to_ms(time_match.group(2)) + current_time_ms
                                sub_text = "\n".join(block_lines[2:])

                                all_srt_entries.append(
                                    f"{srt_counter}\n"
                                    f"{self._ms_to_srt_time(start_ms)} --> {self._ms_to_srt_time(end_ms)}\n"
                                    f"[{line.speaker}] {sub_text}"
                                )
                                srt_counter += 1

            current_time_ms += seg_duration_ms
            total_words += len(re.findall(r"\b\w+\b", line.text))
            total_chars += len(line.text)

        # Write combined audio file
        with open(out_path, "wb") as f:
            f.write(master_audio_bytes)

        srt_content = "\n\n".join(all_srt_entries) + "\n" if all_srt_entries else None
        vtt_content = self._convert_srt_to_vtt(srt_content) if srt_content else None
        srt_file = None
        vtt_file = None

        if srt_content:
            srt_file = str(out_path.with_suffix(".srt"))
            vtt_file = str(out_path.with_suffix(".vtt"))
            with open(srt_file, "w", encoding="utf-8") as f:
                f.write(srt_content)
            with open(vtt_file, "w", encoding="utf-8") as f:
                f.write(vtt_content or "")

        result = SynthesisResult(
            audio_path=str(out_path.resolve()),
            audio_bytes=bytes(master_audio_bytes),
            duration_estimate_sec=round(current_time_ms / 1000.0, 2),
            character_count=total_chars,
            word_count=total_words,
            voice="Multi-Speaker",
            srt_subtitles=srt_content,
            vtt_subtitles=vtt_content,
            srt_path=srt_file,
            vtt_path=vtt_file,
        )

        self._record_history(
            text=f"Dialogue: {len(parsed_lines)} lines across {len(set(l.speaker for l in parsed_lines))} speakers",
            voice="Multi-Speaker",
            audio_path=result.audio_path,
            duration=result.duration_estimate_sec,
            char_count=total_chars,
            word_count=total_words,
            has_subs=bool(srt_file),
            mode="dialogue",
        )

        if progress_cb:
            progress_cb(f"Master dialogue saved to {out_path.name}")

        return result

    # ------------------------------------------------------------- Presets

    def get_all_presets(self) -> Dict[str, Dict[str, Any]]:
        """Return combined built-in and user-defined presets."""
        combined = dict(BUILTIN_PRESETS)
        combined.update(self._custom_presets)
        return combined

    def save_custom_preset(
        self,
        preset_id: str,
        name: str,
        description: str,
        voice: str,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%",
    ) -> None:
        """Save a new user-defined voice preset."""
        clean_id = re.sub(r"[^a-zA-Z0-9_-]", "_", preset_id).lower()
        self._custom_presets[clean_id] = {
            "name": name,
            "description": description,
            "voice": voice,
            "rate": rate,
            "pitch": pitch,
            "volume": volume,
        }
        self._atomic_json_write(self.presets_file, self._custom_presets)

    def delete_custom_preset(self, preset_id: str) -> bool:
        """Delete a custom user preset."""
        if preset_id in self._custom_presets:
            del self._custom_presets[preset_id]
            self._atomic_json_write(self.presets_file, self._custom_presets)
            return True
        return False

    def _load_custom_presets(self) -> Dict[str, Dict[str, Any]]:
        if self.presets_file.exists():
            try:
                with open(self.presets_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    # ------------------------------------------------------------- History

    def get_history(self) -> List[HistoryItem]:
        """Return recent synthesis history."""
        return list(self._history)

    def clear_history(self) -> None:
        """Clear all stored history."""
        self._history = []
        if self.history_file.exists():
            try:
                self.history_file.unlink()
            except Exception:
                pass

    def _record_history(
        self,
        text: str,
        voice: str,
        audio_path: str,
        duration: float,
        char_count: int,
        word_count: int,
        has_subs: bool,
        mode: str,
    ) -> None:
        item = HistoryItem(
            id=datetime.datetime.now().strftime("%Y%m%d%H%M%S%f"),
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            text_preview=(text[:80] + "...") if len(text) > 80 else text,
            voice=voice,
            audio_path=audio_path,
            duration_sec=duration,
            char_count=char_count,
            word_count=word_count,
            has_subtitles=has_subs,
            mode=mode,
        )
        self._history.insert(0, item)
        self._history = self._history[:100]  # keep latest 100
        try:
            self._atomic_json_write(self.history_file, [asdict(h) for h in self._history])
        except Exception:
            pass

    def _load_history(self) -> List[HistoryItem]:
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    items = []
                    for item in data:
                        try:
                            items.append(HistoryItem(**item))
                        except (TypeError, KeyError):
                            continue
                    return items
            except Exception:
                return []
        return []

    # ------------------------------------------------------------- Helpers

    def _atomic_json_write(self, filepath: Path, data: Any) -> None:
        """Write JSON atomically via temp file + rename."""
        tmp_path = filepath.with_suffix('.tmp')
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp_path.replace(filepath)

    @staticmethod
    def generate_auto_filename(text: str) -> str:
        """Create a sanitized readable file name from text + timestamp."""
        clean = re.sub(r'[^\w\s]+', ' ', text, flags=re.UNICODE)
        clean = re.sub(r'[<>:"/\\|?*]+', '', clean)
        words = clean.split()
        base = "_".join(words[:4])[:40].strip("_") or "speech"
        return f"{base}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"

    @staticmethod
    def _convert_srt_to_vtt(srt_content: str) -> str:
        """Convert SRT string into WebVTT format."""
        vtt_lines = ["WEBVTT\n"]
        for line in srt_content.strip().split("\n"):
            if "-->" in line:
                line = line.replace(",", ".")
            vtt_lines.append(line)
        return "\n".join(vtt_lines) + "\n"

    @staticmethod
    def _srt_time_to_ms(srt_time: str) -> int:
        """Parse 'HH:MM:SS,mmm' to milliseconds."""
        parts = re.split(r"[:,.]", srt_time.strip())
        if len(parts) == 4:
            h, m, s, ms = map(int, parts)
            return (h * 3600 + m * 60 + s) * 1000 + ms
        return 0

    @staticmethod
    def _ms_to_srt_time(total_ms: int) -> str:
        """Convert milliseconds into 'HH:MM:SS,mmm'."""
        total_ms = max(0, total_ms)
        ms = total_ms % 1000
        total_seconds = total_ms // 1000
        seconds = total_seconds % 60
        total_minutes = total_seconds // 60
        minutes = total_minutes % 60
        hours = total_minutes // 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"
