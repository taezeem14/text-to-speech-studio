"""GUI for converting text to speech and saving it as an MP3.

Built with Tkinter (bundled with Python) + edge-tts. In-app MP3 playback
uses pygame (installed via requirements.txt).

Run with:
    python tts_gui.py
"""

import asyncio
import datetime
import os
import queue
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import edge_tts

# pygame prints a support banner on import; hide it until we actually need it.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

DEFAULT_VOICE = "en-US-ChristopherNeural"


class TTSApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Text to Speech Studio")
        self.root.geometry("760x640")
        self.root.minsize(560, 480)

        self.event_queue: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self.busy = False
        self.last_output: str | None = None
        self.auto_name_var = tk.BooleanVar(value=True)
        self._music_playing = False

        self._build_ui()

        # Start polling for background-thread results, then load the voice list.
        self.root.after(100, self._poll_events)
        self.root.after(250, self._poll_music)
        threading.Thread(target=self._load_voices, daemon=True).start()
        self._on_auto_name_toggle()  # apply the default auto-name state

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=10)
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        # --- Text input (big, accepts long dialogues) ---
        header = ttk.Frame(main)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="Your text (paste as much as you like):").grid(row=0, column=0, sticky="w")
        self.char_var = tk.StringVar(value="0 characters")
        ttk.Label(header, textvariable=self.char_var).grid(row=0, column=1, sticky="e")

        text_frame = ttk.Frame(main)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        self.text_widget = tk.Text(text_frame, wrap="word", undo=True, font=("Segoe UI", 11))
        scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=scroll.set)
        self.text_widget.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.text_widget.bind("<<Modified>>", self._on_modified)

        # --- Controls ---
        controls = ttk.Frame(main)
        controls.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Voice:").grid(row=0, column=0, sticky="w")
        self.voice_var = tk.StringVar(value=DEFAULT_VOICE)
        self.voice_combo = ttk.Combobox(controls, textvariable=self.voice_var, width=40)
        self.voice_combo.grid(row=0, column=1, sticky="ew", padx=(5, 5))
        ttk.Button(controls, text="Refresh", command=self._refresh_voices).grid(row=0, column=2, sticky="e")

        ttk.Label(controls, text="Speed:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.rate_var = tk.IntVar(value=0)
        rate = ttk.Scale(
            controls, from_=-50, to=50, variable=self.rate_var,
            command=lambda _v: self.rate_label.config(text=f"{self.rate_var.get():+d}%"),
        )
        rate.grid(row=1, column=1, sticky="ew", padx=(5, 5), pady=(8, 0))
        self.rate_label = ttk.Label(controls, text="+0%", width=6, anchor="e")
        self.rate_label.grid(row=1, column=2, sticky="e", pady=(8, 0))

        ttk.Label(controls, text="Pitch:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.pitch_var = tk.StringVar(value="+0Hz")
        ttk.Entry(controls, textvariable=self.pitch_var).grid(row=2, column=1, sticky="ew", padx=(5, 5), pady=(8, 0))
        ttk.Label(controls, text="e.g. +20Hz / -20Hz").grid(row=2, column=2, sticky="e", pady=(8, 0))

        ttk.Label(controls, text="Save as:").grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.output_var = tk.StringVar(value="output.mp3")
        self.output_entry = ttk.Entry(controls, textvariable=self.output_var)
        self.output_entry.grid(row=3, column=1, sticky="ew", padx=(5, 5), pady=(8, 0))
        self.browse_btn = ttk.Button(controls, text="Browse\u2026", command=self._browse_output)
        self.browse_btn.grid(row=3, column=2, sticky="e", pady=(8, 0))

        # --- Auto-name option ---
        ttk.Checkbutton(
            controls, text="Auto-generate file name", variable=self.auto_name_var,
            command=self._on_auto_name_toggle,
        ).grid(row=4, column=0, sticky="w")
        ttk.Label(controls, text="uses your text + timestamp").grid(
            row=4, column=1, columnspan=2, sticky="w", padx=(5, 0)
        )

        # --- Action buttons ---
        buttons = ttk.Frame(main)
        buttons.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        self.generate_btn = ttk.Button(buttons, text="Generate MP3", command=self._on_generate)
        self.generate_btn.pack(side="left")
        self.preview_btn = ttk.Button(buttons, text="Play", command=self._on_preview)
        self.preview_btn.pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Clear", command=self._clear_text).pack(side="left", padx=(8, 0))

        # --- Status bar ---
        self.status_var = tk.StringVar(value="Loading voices\u2026")
        ttk.Label(main, textvariable=self.status_var, relief="sunken", anchor="w", padding=(6, 3)).grid(
            row=5, column=0, sticky="ew", pady=(10, 0)
        )

    # ------------------------------------------------------------ handlers

    def _on_modified(self, _event: object = None) -> None:
        if self.text_widget.edit_modified():
            length = len(self.text_widget.get("1.0", "end-1c"))
            self.char_var.set(f"{length} characters")
            self.text_widget.edit_modified(False)

    def _clear_text(self) -> None:
        self.text_widget.delete("1.0", "end")

    def _browse_output(self) -> None:
        if self.auto_name_var.get():
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3 audio", "*.mp3"), ("All files", "*.*")],
            initialfile=self.output_var.get().strip() or "output.mp3",
        )
        if path:
            self.output_var.set(path)

    def _on_generate(self) -> None:
        if self.busy:
            return
        text = self.text_widget.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showwarning("No text", "Type or paste some text first.")
            return
        voice = self.voice_var.get().strip() or DEFAULT_VOICE
        rate = f"{self.rate_var.get():+d}%"
        pitch = self.pitch_var.get().strip() or "+0Hz"
        output = self._resolve_output_name(text)
        self.output_var.set(output)

        # Stop any in-app playback before regenerating the file.
        self._stop_playback()

        self.busy = True
        self.generate_btn.config(state="disabled")
        self.status_var.set(f"Generating speech with {voice} \u2026")
        threading.Thread(target=self._synthesize, args=(text, voice, output, rate, pitch), daemon=True).start()

    def _on_preview(self) -> None:
        """Play the last generated MP3 inside the app (no external player)."""
        if self._music_playing:
            self._stop_playback()
            return
        if not (self.last_output and os.path.exists(self.last_output)):
            messagebox.showinfo("Nothing to play", "Generate an MP3 first.")
            return
        try:
            import pygame
        except ImportError:
            messagebox.showerror(
                "Playback unavailable",
                "In-app playback needs pygame.\nInstall it with:\n    pip install pygame",
            )
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000)  # edge-tts outputs 24 kHz audio
            pygame.mixer.music.load(self.last_output)
            pygame.mixer.music.play()
            self._music_playing = True
            self.preview_btn.config(text="Stop")
        except Exception as exc:
            messagebox.showerror("Playback failed", str(exc))

    def _stop_playback(self) -> None:
        """Stop in-app playback and reset the Play button."""
        self._music_playing = False
        self.preview_btn.config(text="Play")
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass

    def _poll_music(self) -> None:
        """Reset the Play button once the track finishes."""
        if self._music_playing:
            try:
                import pygame
                if not pygame.mixer.get_init() or not pygame.mixer.music.get_busy():
                    self._music_playing = False
                    self.preview_btn.config(text="Play")
            except Exception:
                self._music_playing = False
                self.preview_btn.config(text="Play")
        self.root.after(250, self._poll_music)

    def _on_auto_name_toggle(self) -> None:
        """Enable/disable manual file naming based on the Auto-name checkbox."""
        if self.auto_name_var.get():
            self.output_entry.config(state="disabled")
            self.browse_btn.config(state="disabled")
            self.output_var.set(
                self._generate_auto_name(self.text_widget.get("1.0", "end-1c").strip())
            )
        else:
            self.output_entry.config(state="normal")
            self.browse_btn.config(state="normal")

    def _generate_auto_name(self, text: str) -> str:
        """Build a unique file name from the first words of the text + timestamp."""
        words = re.sub(r"[^A-Za-z0-9 ]+", " ", text).split()
        base = "_".join(words[:4])[:40].strip("_") or "narration"
        return f"{base}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"

    def _resolve_output_name(self, text: str) -> str:
        """Return the final output name: auto-generated or the manually typed one."""
        if self.auto_name_var.get():
            return self._generate_auto_name(text)
        output = self.output_var.get().strip() or "output.mp3"
        if not output.lower().endswith(".mp3"):
            output += ".mp3"
        return output

    def _refresh_voices(self) -> None:
        self.status_var.set("Loading voices\u2026")
        threading.Thread(target=self._load_voices, daemon=True).start()

    # ------------------------------------------------------- background work

    def _load_voices(self) -> None:
        try:
            voices = asyncio.run(edge_tts.list_voices())
            self.event_queue.put(("voices", sorted(v["ShortName"] for v in voices)))
        except Exception as exc:
            self.event_queue.put(("voices_error", str(exc)))

    def _synthesize(self, text: str, voice: str, output: str, rate: str, pitch: str) -> None:
        try:
            communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
            asyncio.run(communicate.save(output))
            self.event_queue.put(("done", output))
        except Exception as exc:
            self.event_queue.put(("error", str(exc)))

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.event_queue.get_nowait()
                if kind == "voices":
                    voices = payload  # type: ignore[assignment]
                    self.voice_combo["values"] = voices
                    if DEFAULT_VOICE in voices:
                        self.voice_var.set(DEFAULT_VOICE)
                    self.status_var.set(f"Loaded {len(voices)} voices.")
                elif kind == "voices_error":
                    self.status_var.set(f"Could not load voices: {payload}")
                elif kind == "done":
                    self.last_output = str(payload)
                    self.status_var.set(f"Saved: {payload}")
                    self.busy = False
                    self.generate_btn.config(state="normal")
                elif kind == "error":
                    messagebox.showerror("Synthesis failed", str(payload))
                    self.status_var.set("Synthesis failed.")
                    self.busy = False
                    self.generate_btn.config(state="normal")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)


def main() -> None:
    root = tk.Tk()
    TTSApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
