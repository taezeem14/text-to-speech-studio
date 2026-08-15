"""Text to Speech Studio - Modern Desktop Suite.

Full-featured desktop application with multi-tab interface:
- 🎙️ Single Narrator Studio with Live Text Analytics & Presets
- 🎭 Multi-Speaker Dialogue Lab & Voice Mapper
- 🔍 Voice Explorer & Live Audition Lab
- ⚡ Batch File Processing Studio
- 📜 Generation History & Custom Preset Manager
- 🎵 Interactive Audio Player & Waveform Visualizer
"""

from __future__ import annotations

import asyncio
import datetime
import math
import os
import queue
import random
import re
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Optional

from tts_engine import (
    BUILTIN_PRESETS,
    DEFAULT_VOICE,
    HistoryItem,
    SynthesisResult,
    TTSStudioEngine,
)

# Hide pygame welcome banner
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


class TTSStudioGUI:
    """Advanced Tkinter GUI for Text to Speech Studio."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Text to Speech Studio v2.0 - Neural TTS & Dialogue Suite")
        self.root.geometry("960x740")
        self.root.minsize(800, 600)

        self.engine = TTSStudioEngine()
        self.event_queue: "queue.Queue[tuple[str, Any]]" = queue.Queue()

        self.busy = False
        self.last_audio_path: Optional[str] = None
        self._music_playing = False
        self._visualizer_running = False
        self._visualizer_bars = [0.1] * 32
        self._all_voices: List[Dict[str, Any]] = []

        # Playback backend initialization
        self._init_audio_backend()

        # Build Theme & UI
        self._setup_theme()
        self._build_main_ui()

        # Polling loops
        self.root.after(100, self._poll_events)
        self.root.after(200, self._poll_audio_state)
        self.root.after(50, self._animate_waveform)

        # Async background voice loader
        threading.Thread(target=self._load_voices_worker, daemon=True).start()

    # -------------------------------------------------------- Theme & Styling

    def _setup_theme(self) -> None:
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # Color Palette
        self.c_bg = "#12151b"
        self.c_card = "#1a1f2c"
        self.c_sidebar = "#161a24"
        self.c_accent = "#00d2ff"
        self.c_accent_purple = "#9d4edd"
        self.c_accent_green = "#00f59b"
        self.c_text = "#f0f6fc"
        self.c_subtext = "#8b949e"
        self.c_border = "#30363d"
        self.c_btn_bg = "#21262d"
        self.c_btn_hover = "#30363d"

        self.root.configure(bg=self.c_bg)

        # Styles configuration
        self.style.configure(".", background=self.c_bg, foreground=self.c_text, font=("Segoe UI", 10))
        self.style.configure("TFrame", background=self.c_bg)
        self.style.configure("Card.TFrame", background=self.c_card, relief="flat")
        self.style.configure("TNotebook", background=self.c_bg, borderwidth=0)
        self.style.configure(
            "TNotebook.Tab",
            background=self.c_sidebar,
            foreground=self.c_subtext,
            padding=[14, 8],
            font=("Segoe UI", 10, "bold"),
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", self.c_card)],
            foreground=[("selected", self.c_accent)],
        )

        self.style.configure("TLabel", background=self.c_bg, foreground=self.c_text)
        self.style.configure("Card.TLabel", background=self.c_card, foreground=self.c_text)
        self.style.configure("Sub.TLabel", background=self.c_card, foreground=self.c_subtext, font=("Segoe UI", 9))
        self.style.configure("Accent.TLabel", background=self.c_card, foreground=self.c_accent, font=("Segoe UI", 10, "bold"))

        # Buttons
        self.style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            background=self.c_accent,
            foreground="#000000",
            padding=[12, 6],
        )
        self.style.configure(
            "Secondary.TButton",
            font=("Segoe UI", 9),
            background=self.c_btn_bg,
            foreground=self.c_text,
            padding=[10, 5],
        )

        # Scale / Sliders
        self.style.configure("Horizontal.TScale", background=self.c_card, troughcolor=self.c_bg)

        # Treeview
        self.style.configure(
            "Treeview",
            background=self.c_card,
            foreground=self.c_text,
            fieldbackground=self.c_card,
            rowheight=26,
            font=("Segoe UI", 9),
        )
        self.style.configure("Treeview.Heading", background=self.c_sidebar, foreground=self.c_accent, font=("Segoe UI", 9, "bold"))
        self.style.map("Treeview", background=[("selected", "#2d3748")])

    # ------------------------------------------------------------- UI Layout

    def _build_main_ui(self) -> None:
        # Header banner
        header = tk.Frame(self.root, bg=self.c_sidebar, height=54, highlightbackground=self.c_border, highlightthickness=1)
        header.pack(fill="x", side="top")

        title_lbl = tk.Label(
            header,
            text="TEXT TO SPEECH STUDIO",
            bg=self.c_sidebar,
            fg=self.c_accent,
            font=("Segoe UI", 13, "bold"),
            padx=16,
            pady=10,
        )
        title_lbl.pack(side="left")

        sub_lbl = tk.Label(
            header,
            text="Neural AI Speech • Synchronized Subtitles • Multi-Speaker Dialogue",
            bg=self.c_sidebar,
            fg=self.c_subtext,
            font=("Segoe UI", 9),
        )
        sub_lbl.pack(side="left", padx=8)

        self.header_status = tk.Label(
            header,
            text="[ Ready ]",
            bg=self.c_sidebar,
            fg=self.c_accent_green,
            font=("Segoe UI", 9, "bold"),
            padx=16,
        )
        self.header_status.pack(side="right")

        # Main Notebook Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=10)

        # 5 Studio Tabs
        self.tab_studio = ttk.Frame(self.notebook, style="Card.TFrame")
        self.tab_dialogue = ttk.Frame(self.notebook, style="Card.TFrame")
        self.tab_voices = ttk.Frame(self.notebook, style="Card.TFrame")
        self.tab_batch = ttk.Frame(self.notebook, style="Card.TFrame")
        self.tab_history = ttk.Frame(self.notebook, style="Card.TFrame")

        self.notebook.add(self.tab_studio, text=" Single Studio ")
        self.notebook.add(self.tab_dialogue, text=" Dialogue Lab ")
        self.notebook.add(self.tab_voices, text=" Voice Directory ")
        self.notebook.add(self.tab_batch, text=" Batch Studio ")
        self.notebook.add(self.tab_history, text=" History & Presets ")

        self._build_studio_tab()
        self._build_dialogue_tab()
        self._build_voices_tab()
        self._build_batch_tab()
        self._build_history_tab()

        # Bottom Audio Visualizer & Player Dock
        self._build_player_dock()

    # -------------------------------------------------- Tab 1: Single Studio

    def _build_studio_tab(self) -> None:
        frame = tk.Frame(self.tab_studio, bg=self.c_card, padx=14, pady=12)
        frame.pack(fill="both", expand=True)

        # Top tools & Preset bar
        preset_bar = tk.Frame(frame, bg=self.c_card)
        preset_bar.pack(fill="x", side="top", pady=(0, 8))

        tk.Label(preset_bar, text="Audio Preset:", bg=self.c_card, fg=self.c_accent, font=("Segoe UI", 9, "bold")).pack(side="left")
        self.preset_var = tk.StringVar(value="-- Select Preset --")
        self.preset_combo = ttk.Combobox(preset_bar, textvariable=self.preset_var, state="readonly", width=26)
        self.preset_combo.pack(side="left", padx=(6, 12))
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_selected)

        # Quick clean tools
        tk.Button(
            preset_bar,
            text="Strip Markdown",
            bg=self.c_btn_bg,
            fg=self.c_text,
            relief="flat",
            font=("Segoe UI", 8),
            command=self._clean_markdown,
        ).pack(side="left", padx=2)
        tk.Button(
            preset_bar,
            text="Strip Notes []",
            bg=self.c_btn_bg,
            fg=self.c_text,
            relief="flat",
            font=("Segoe UI", 8),
            command=self._clean_brackets,
        ).pack(side="left", padx=2)
        tk.Button(
            preset_bar,
            text="Clear",
            bg=self.c_btn_bg,
            fg=self.c_text,
            relief="flat",
            font=("Segoe UI", 8),
            command=self._clear_studio_text,
        ).pack(side="right")
        tk.Button(
            preset_bar,
            text="Load File",
            bg=self.c_btn_bg,
            fg=self.c_text,
            relief="flat",
            font=("Segoe UI", 8),
            command=self._load_studio_file,
        ).pack(side="right", padx=4)

        # Main Text Editor Area
        editor_frame = tk.Frame(frame, bg="#0d1117", highlightbackground=self.c_border, highlightthickness=1)
        editor_frame.pack(fill="both", expand=True)

        self.studio_text = tk.Text(
            editor_frame,
            wrap="word",
            undo=True,
            font=("Segoe UI", 11),
            bg="#0d1117",
            fg="#e6edf3",
            insertbackground=self.c_accent,
            selectbackground="#264f78",
            relief="flat",
            padx=10,
            pady=10,
        )
        studio_scroll = ttk.Scrollbar(editor_frame, orient="vertical", command=self.studio_text.yview)
        self.studio_text.configure(yscrollcommand=studio_scroll.set)
        self.studio_text.pack(side="left", fill="both", expand=True)
        studio_scroll.pack(side="right", fill="y")
        self.studio_text.bind("<<Modified>>", self._on_studio_text_modified)

        # Live Text Analytics Bar
        self.metrics_bar = tk.Frame(frame, bg=self.c_card, pady=6)
        self.metrics_bar.pack(fill="x")

        self.metrics_var = tk.StringVar(value="Words: 0 | Chars: 0 | Estimated Duration: ~0.0s | Reading Level: Standard")
        tk.Label(self.metrics_bar, textvariable=self.metrics_var, bg=self.c_card, fg=self.c_subtext, font=("Segoe UI", 9)).pack(side="left")

        # Controls Grid
        ctrl = tk.Frame(frame, bg=self.c_card, pady=8)
        ctrl.pack(fill="x")
        ctrl.columnconfigure(1, weight=1)
        ctrl.columnconfigure(3, weight=1)

        # Voice Selector
        tk.Label(ctrl, text="Voice:", bg=self.c_card, fg=self.c_text, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=4)
        self.studio_voice_var = tk.StringVar(value=DEFAULT_VOICE)
        self.studio_voice_combo = ttk.Combobox(ctrl, textvariable=self.studio_voice_var, width=38)
        self.studio_voice_combo.grid(row=0, column=1, columnspan=2, sticky="ew", padx=6, pady=4)

        # Speed (Rate)
        tk.Label(ctrl, text="Speed:", bg=self.c_card, fg=self.c_text, font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=4)
        self.studio_rate_var = tk.IntVar(value=0)
        self.rate_scale = ttk.Scale(
            ctrl,
            from_=-50,
            to=100,
            variable=self.studio_rate_var,
            command=self._on_rate_change,
        )
        self.rate_scale.grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        self.studio_rate_lbl = tk.Label(ctrl, text="+0%", bg=self.c_card, fg=self.c_accent, width=6, font=("Segoe UI", 9, "bold"))
        self.studio_rate_lbl.grid(row=1, column=2, sticky="w")

        # Pitch Shift
        tk.Label(ctrl, text="Pitch:", bg=self.c_card, fg=self.c_text, font=("Segoe UI", 9, "bold")).grid(row=1, column=3, sticky="w", padx=(12, 0))
        self.studio_pitch_var = tk.IntVar(value=0)
        self.pitch_scale = ttk.Scale(
            ctrl,
            from_=-50,
            to=50,
            variable=self.studio_pitch_var,
            command=self._on_pitch_change,
        )
        self.pitch_scale.grid(row=1, column=4, sticky="ew", padx=6, pady=4)
        self.studio_pitch_lbl = tk.Label(ctrl, text="+0Hz", bg=self.c_card, fg=self.c_accent_purple, width=6, font=("Segoe UI", 9, "bold"))
        self.studio_pitch_lbl.grid(row=1, column=5, sticky="w")

        # Subtitle check & File Output row
        out_row = tk.Frame(frame, bg=self.c_card, pady=4)
        out_row.pack(fill="x")

        self.subtitles_var = tk.BooleanVar(value=True)
        sub_check = tk.Checkbutton(
            out_row,
            text="Generate Subtitles (.SRT & .VTT)",
            variable=self.subtitles_var,
            bg=self.c_card,
            fg=self.c_text,
            selectcolor=self.c_bg,
            activebackground=self.c_card,
            activeforeground=self.c_accent,
            font=("Segoe UI", 9),
        )
        sub_check.pack(side="left")

        self.auto_name_var = tk.BooleanVar(value=True)
        auto_check = tk.Checkbutton(
            out_row,
            text="Auto File Name",
            variable=self.auto_name_var,
            bg=self.c_card,
            fg=self.c_text,
            selectcolor=self.c_bg,
            activebackground=self.c_card,
            activeforeground=self.c_accent,
            font=("Segoe UI", 9),
            command=self._toggle_auto_name,
        )
        auto_check.pack(side="left", padx=12)

        self.studio_output_var = tk.StringVar(value="output.mp3")
        self.studio_out_entry = tk.Entry(
            out_row,
            textvariable=self.studio_output_var,
            bg="#0d1117",
            fg=self.c_text,
            relief="flat",
            font=("Segoe UI", 9),
            state="disabled",
        )
        self.studio_out_entry.pack(side="left", fill="x", expand=True, padx=4)

        self.browse_btn = tk.Button(
            out_row,
            text="Browse...",
            bg=self.c_btn_bg,
            fg=self.c_text,
            relief="flat",
            font=("Segoe UI", 9),
            state="disabled",
            command=self._browse_studio_output,
        )
        self.browse_btn.pack(side="right")

        # Action Buttons Row
        action_row = tk.Frame(frame, bg=self.c_card, pady=8)
        action_row.pack(fill="x")

        self.generate_btn = tk.Button(
            action_row,
            text="GENERATE SPEECH & SUBTITLES",
            bg=self.c_accent,
            fg="#000000",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=18,
            pady=6,
            command=self._on_generate_studio,
        )
        self.generate_btn.pack(side="left")

        self.play_studio_btn = tk.Button(
            action_row,
            text="Play Audio",
            bg=self.c_btn_bg,
            fg=self.c_text,
            font=("Segoe UI", 10),
            relief="flat",
            padx=14,
            pady=6,
            command=self._on_play_last,
        )
        self.play_studio_btn.pack(side="left", padx=8)

        self.reveal_btn = tk.Button(
            action_row,
            text="Open Folder",
            bg=self.c_btn_bg,
            fg=self.c_text,
            font=("Segoe UI", 10),
            relief="flat",
            padx=12,
            pady=6,
            command=self._reveal_last_file,
        )
        self.reveal_btn.pack(side="left")

    # -------------------------------------------------- Tab 2: Dialogue Lab

    def _build_dialogue_tab(self) -> None:
        frame = tk.Frame(self.tab_dialogue, bg=self.c_card, padx=14, pady=12)
        frame.pack(fill="both", expand=True)

        top = tk.Frame(frame, bg=self.c_card)
        top.pack(fill="x", side="top", pady=(0, 8))

        tk.Label(
            top,
            text="Multi-Speaker Script Dialogue Studio",
            bg=self.c_card,
            fg=self.c_accent_purple,
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")

        tk.Button(
            top,
            text="Load Demo Script",
            bg=self.c_btn_bg,
            fg=self.c_accent,
            relief="flat",
            font=("Segoe UI", 9),
            command=self._load_sample_dialogue,
        ).pack(side="right")

        tk.Label(
            frame,
            text="Write dialogue using '[Speaker | Voice]: Text' or 'Speaker: Text'. Lines will be synthesized with individual voices and stitched seamlessly!",
            bg=self.c_card,
            fg=self.c_subtext,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 6))

        # Script Editor Area
        editor_frame = tk.Frame(frame, bg="#0d1117", highlightbackground=self.c_border, highlightthickness=1)
        editor_frame.pack(fill="both", expand=True)

        self.dialogue_text = tk.Text(
            editor_frame,
            wrap="word",
            undo=True,
            font=("Consolas", 10),
            bg="#0d1117",
            fg="#e6edf3",
            insertbackground=self.c_accent,
            selectbackground="#264f78",
            relief="flat",
            padx=10,
            pady=10,
        )
        d_scroll = ttk.Scrollbar(editor_frame, orient="vertical", command=self.dialogue_text.yview)
        self.dialogue_text.configure(yscrollcommand=d_scroll.set)
        self.dialogue_text.pack(side="left", fill="both", expand=True)
        d_scroll.pack(side="right", fill="y")

        # Bottom Options
        opts = tk.Frame(frame, bg=self.c_card, pady=8)
        opts.pack(fill="x")

        self.dialogue_gen_btn = tk.Button(
            opts,
            text="COMPILE & GENERATE MASTER DIALOGUE",
            bg=self.c_accent_purple,
            fg="#ffffff",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=16,
            pady=6,
            command=self._on_generate_dialogue,
        )
        self.dialogue_gen_btn.pack(side="left")

        self.dialogue_play_btn = tk.Button(
            opts,
            text="Play Master Audio",
            bg=self.c_btn_bg,
            fg=self.c_text,
            font=("Segoe UI", 10),
            relief="flat",
            padx=12,
            pady=6,
            command=self._on_play_last,
        )
        self.dialogue_play_btn.pack(side="left", padx=8)

    # ------------------------------------------------ Tab 3: Voice Explorer

    def _build_voices_tab(self) -> None:
        frame = tk.Frame(self.tab_voices, bg=self.c_card, padx=14, pady=12)
        frame.pack(fill="both", expand=True)

        # Filters Bar
        filter_bar = tk.Frame(frame, bg=self.c_card)
        filter_bar.pack(fill="x", pady=(0, 8))

        tk.Label(filter_bar, text="Search:", bg=self.c_card, fg=self.c_text, font=("Segoe UI", 9, "bold")).pack(side="left")
        self.voice_search_var = tk.StringVar()
        self.voice_search_entry = tk.Entry(
            filter_bar,
            textvariable=self.voice_search_var,
            bg="#0d1117",
            fg=self.c_text,
            relief="flat",
            font=("Segoe UI", 9),
            width=22,
        )
        self.voice_search_entry.pack(side="left", padx=6)
        self.voice_search_var.trace_add("write", lambda *_: self._filter_voices_ui())

        tk.Label(filter_bar, text="Locale:", bg=self.c_card, fg=self.c_text, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(10, 0))
        self.voice_locale_var = tk.StringVar(value="All")
        self.voice_locale_combo = ttk.Combobox(filter_bar, textvariable=self.voice_locale_var, state="readonly", width=12)
        self.voice_locale_combo.pack(side="left", padx=6)
        self.voice_locale_combo.bind("<<ComboboxSelected>>", lambda *_: self._filter_voices_ui())

        tk.Label(filter_bar, text="Gender:", bg=self.c_card, fg=self.c_text, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(10, 0))
        self.voice_gender_var = tk.StringVar(value="All")
        self.voice_gender_combo = ttk.Combobox(
            filter_bar,
            textvariable=self.voice_gender_var,
            values=["All", "Female", "Male"],
            state="readonly",
            width=10,
        )
        self.voice_gender_combo.pack(side="left", padx=6)
        self.voice_gender_combo.bind("<<ComboboxSelected>>", lambda *_: self._filter_voices_ui())

        tk.Button(
            filter_bar,
            text="Refresh Voices",
            bg=self.c_btn_bg,
            fg=self.c_text,
            relief="flat",
            font=("Segoe UI", 9),
            command=self._refresh_voices,
        ).pack(side="right")

        # Treeview Voices Directory
        tree_frame = tk.Frame(frame, bg="#0d1117", highlightbackground=self.c_border, highlightthickness=1)
        tree_frame.pack(fill="both", expand=True)

        columns = ("short_name", "locale", "gender", "friendly_name")
        self.voices_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self.voices_tree.heading("short_name", text="Voice ID (ShortName)")
        self.voices_tree.heading("locale", text="Locale / Region")
        self.voices_tree.heading("gender", text="Gender")
        self.voices_tree.heading("friendly_name", text="Friendly Name")

        self.voices_tree.column("short_name", width=220)
        self.voices_tree.column("locale", width=120)
        self.voices_tree.column("gender", width=90)
        self.voices_tree.column("friendly_name", width=340)

        v_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.voices_tree.yview)
        self.voices_tree.configure(yscrollcommand=v_scroll.set)
        self.voices_tree.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")

        # Audition Toolbar
        audition_bar = tk.Frame(frame, bg=self.c_card, pady=8)
        audition_bar.pack(fill="x")

        tk.Button(
            audition_bar,
            text="AUDITION SELECTED VOICE",
            bg=self.c_accent_green,
            fg="#000000",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=5,
            command=self._on_audition_selected_voice,
        ).pack(side="left")

        tk.Button(
            audition_bar,
            text="Use In Studio",
            bg=self.c_btn_bg,
            fg=self.c_accent,
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=5,
            command=self._use_selected_voice_in_studio,
        ).pack(side="left", padx=8)

        self.audition_status_lbl = tk.Label(audition_bar, text="", bg=self.c_card, fg=self.c_subtext, font=("Segoe UI", 9))
        self.audition_status_lbl.pack(side="right")

    # -------------------------------------------------- Tab 4: Batch Studio

    def _build_batch_tab(self) -> None:
        frame = tk.Frame(self.tab_batch, bg=self.c_card, padx=14, pady=12)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="Batch Text File Converter",
            bg=self.c_card,
            fg=self.c_accent,
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 4))

        tk.Label(
            frame,
            text="Convert multiple .txt or .md files in queue into MP3 audio and subtitles automatically.",
            bg=self.c_card,
            fg=self.c_subtext,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 8))

        top_actions = tk.Frame(frame, bg=self.c_card)
        top_actions.pack(fill="x", pady=(0, 8))

        tk.Button(
            top_actions,
            text="+ Add Files",
            bg=self.c_btn_bg,
            fg=self.c_text,
            relief="flat",
            font=("Segoe UI", 9),
            command=self._add_batch_files,
        ).pack(side="left")

        tk.Button(
            top_actions,
            text="Clear Queue",
            bg=self.c_btn_bg,
            fg=self.c_text,
            relief="flat",
            font=("Segoe UI", 9),
            command=self._clear_batch_files,
        ).pack(side="left", padx=8)

        # Batch File List
        list_frame = tk.Frame(frame, bg="#0d1117", highlightbackground=self.c_border, highlightthickness=1)
        list_frame.pack(fill="both", expand=True)

        self.batch_listbox = tk.Listbox(
            list_frame,
            bg="#0d1117",
            fg=self.c_text,
            selectbackground="#264f78",
            relief="flat",
            font=("Segoe UI", 9),
        )
        b_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.batch_listbox.yview)
        self.batch_listbox.configure(yscrollcommand=b_scroll.set)
        self.batch_listbox.pack(side="left", fill="both", expand=True)
        b_scroll.pack(side="right", fill="y")

        # Action bottom
        b_bottom = tk.Frame(frame, bg=self.c_card, pady=8)
        b_bottom.pack(fill="x")

        self.batch_start_btn = tk.Button(
            b_bottom,
            text="START BATCH CONVERSION",
            bg=self.c_accent,
            fg="#000000",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=16,
            pady=6,
            command=self._start_batch_conversion,
        )
        self.batch_start_btn.pack(side="left")

        self.batch_progress_lbl = tk.Label(b_bottom, text="0 files queued", bg=self.c_card, fg=self.c_subtext, font=("Segoe UI", 9))
        self.batch_progress_lbl.pack(side="left", padx=12)

    # ------------------------------------------------ Tab 5: History & Presets

    def _build_history_tab(self) -> None:
        frame = tk.Frame(self.tab_history, bg=self.c_card, padx=14, pady=12)
        frame.pack(fill="both", expand=True)

        top = tk.Frame(frame, bg=self.c_card)
        top.pack(fill="x", pady=(0, 8))

        tk.Label(
            top,
            text="Audio Generation History",
            bg=self.c_card,
            fg=self.c_accent,
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")

        tk.Button(
            top,
            text="Clear History",
            bg=self.c_btn_bg,
            fg=self.c_text,
            relief="flat",
            font=("Segoe UI", 9),
            command=self._clear_history_ui,
        ).pack(side="right")

        # History Treeview
        tree_frame = tk.Frame(frame, bg="#0d1117", highlightbackground=self.c_border, highlightthickness=1)
        tree_frame.pack(fill="both", expand=True)

        columns = ("time", "mode", "voice", "words", "duration", "path")
        self.history_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self.history_tree.heading("time", text="Timestamp")
        self.history_tree.heading("mode", text="Mode")
        self.history_tree.heading("voice", text="Voice")
        self.history_tree.heading("words", text="Words")
        self.history_tree.heading("duration", text="Duration")
        self.history_tree.heading("path", text="Saved File Path")

        self.history_tree.column("time", width=140)
        self.history_tree.column("mode", width=80)
        self.history_tree.column("voice", width=160)
        self.history_tree.column("words", width=70)
        self.history_tree.column("duration", width=80)
        self.history_tree.column("path", width=360)

        h_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=h_scroll.set)
        self.history_tree.pack(side="left", fill="both", expand=True)
        h_scroll.pack(side="right", fill="y")

        # History actions
        h_actions = tk.Frame(frame, bg=self.c_card, pady=8)
        h_actions.pack(fill="x")

        tk.Button(
            h_actions,
            text="Play Selected",
            bg=self.c_btn_bg,
            fg=self.c_accent,
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=5,
            command=self._play_history_selected,
        ).pack(side="left")

        tk.Button(
            h_actions,
            text="Reveal File",
            bg=self.c_btn_bg,
            fg=self.c_text,
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=5,
            command=self._reveal_history_selected,
        ).pack(side="left", padx=8)

        self._refresh_history_tree()

    # ---------------------------------------- Bottom Visualizer & Audio Player

    def _build_player_dock(self) -> None:
        dock = tk.Frame(self.root, bg=self.c_sidebar, height=76, highlightbackground=self.c_border, highlightthickness=1, padx=14, pady=6)
        dock.pack(fill="x", side="bottom")

        # Visualizer canvas (Waveform animations)
        self.viz_canvas = tk.Canvas(dock, bg="#0d1117", height=42, width=220, highlightthickness=0)
        self.viz_canvas.pack(side="left", padx=(0, 14))

        # Status text & Now Playing
        status_box = tk.Frame(dock, bg=self.c_sidebar)
        status_box.pack(side="left", fill="both", expand=True)

        self.status_title = tk.Label(status_box, text="Ready", bg=self.c_sidebar, fg=self.c_text, font=("Segoe UI", 9, "bold"))
        self.status_title.pack(anchor="w")

        self.status_detail = tk.Label(status_box, text="Load text or pick a preset to synthesize", bg=self.c_sidebar, fg=self.c_subtext, font=("Segoe UI", 8))
        self.status_detail.pack(anchor="w")

        # Play/Stop master button
        self.dock_play_btn = tk.Button(
            dock,
            text="PLAY",
            bg=self.c_accent,
            fg="#000000",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=18,
            pady=6,
            command=self._on_play_last,
        )
        self.dock_play_btn.pack(side="right")


    # ------------------------------------------------------- Audio Playback

    def _init_audio_backend(self) -> None:
        """Initialize playback system (pygame with fallback)."""
        self._has_pygame = False
        try:
            import pygame

            pygame.mixer.init(frequency=24000)
            self._has_pygame = True
        except Exception:
            self._has_pygame = False

    def _play_audio(self, filepath: str) -> None:
        """Play audio file using pygame or native OS player."""
        if not filepath or not os.path.exists(filepath):
            messagebox.showinfo("Audio not found", "No audio file is available to play.")
            return

        self._stop_audio()
        self.last_audio_path = filepath

        if self._has_pygame:
            try:
                import pygame

                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=24000)
                pygame.mixer.music.load(filepath)
                pygame.mixer.music.play()
                self._music_playing = True
                self._visualizer_running = True
                self._update_playback_ui(playing=True)
                return
            except Exception:
                pass

        # Fallback to Windows native media player via PowerShell
        def _win_play() -> None:
            try:
                cmd = f"powershell -c (New-Object Media.SoundPlayer '{filepath}').PlaySync()"
                subprocess.run(cmd, shell=True)
                self.event_queue.put(("playback_ended", None))
            except Exception:
                pass

        self._music_playing = True
        self._visualizer_running = True
        self._update_playback_ui(playing=True)
        threading.Thread(target=_win_play, daemon=True).start()

    def _stop_audio(self) -> None:
        """Stop all audio playback."""
        self._music_playing = False
        self._visualizer_running = False
        if self._has_pygame:
            try:
                import pygame

                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
            except Exception:
                pass
        self._update_playback_ui(playing=False)

    def _update_playback_ui(self, playing: bool) -> None:
        txt = "⏹️ STOP" if playing else "▶️ PLAY"
        self.dock_play_btn.config(text=txt, bg=self.c_accent_purple if playing else self.c_accent)
        if hasattr(self, "play_studio_btn"):
            self.play_studio_btn.config(text="⏹️ Stop Audio" if playing else "▶️ Play Audio")

    def _poll_audio_state(self) -> None:
        """Poll pygame or background player to detect song end."""
        if self._music_playing and self._has_pygame:
            try:
                import pygame

                if not pygame.mixer.music.get_busy():
                    self._stop_audio()
            except Exception:
                self._stop_audio()
        self.root.after(200, self._poll_audio_state)

    def _animate_waveform(self) -> None:
        """Draw dynamic neon waveform audio bars on canvas."""
        self.viz_canvas.delete("all")
        w, h = 220, 42
        num_bars = 28
        bar_w = (w - (num_bars * 2)) / num_bars

        for i in range(num_bars):
            if self._visualizer_running:
                # Dynamic animated wave
                t = datetime.datetime.now().timestamp() * 8
                target = abs(math.sin(t + i * 0.35)) * 0.85 + random.uniform(0.05, 0.15)
                self._visualizer_bars[i] = self._visualizer_bars[i] * 0.4 + target * 0.6
            else:
                self._visualizer_bars[i] = max(0.05, self._visualizer_bars[i] * 0.8)

            bar_h = max(2, self._visualizer_bars[i] * (h - 8))
            x0 = i * (bar_w + 2) + 4
            y0 = (h - bar_h) / 2
            x1 = x0 + bar_w
            y1 = y0 + bar_h

            color = self.c_accent if not self._visualizer_running else (self.c_accent_green if i % 2 == 0 else self.c_accent)
            self.viz_canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")

        self.root.after(50, self._animate_waveform)

    # ----------------------------------------------------- Event Handling

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.event_queue.get_nowait()
                if kind == "voices_loaded":
                    self._on_voices_loaded(payload)
                elif kind == "synthesis_done":
                    self._on_synthesis_complete(payload)
                elif kind == "synthesis_error":
                    self._on_synthesis_error(payload)
                elif kind == "status_update":
                    self.status_detail.config(text=str(payload))
                elif kind == "playback_ended":
                    self._stop_audio()
                elif kind == "batch_progress":
                    self.batch_progress_lbl.config(text=str(payload))
                elif kind == "batch_done":
                    messagebox.showinfo("Batch Complete", str(payload))
                    self.batch_start_btn.config(state="normal")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _load_voices_worker(self) -> None:
        try:
            voices = self.engine.list_voices_sync()
            self.event_queue.put(("voices_loaded", voices))
        except Exception as exc:
            self.event_queue.put(("status_update", f"Voice loading notice: {exc}"))

    def _on_voices_loaded(self, voices: List[Dict[str, Any]]) -> None:
        self._all_voices = voices
        voice_names = [v.get("ShortName", "") for v in voices]
        self.studio_voice_combo["values"] = voice_names
        if DEFAULT_VOICE in voice_names:
            self.studio_voice_var.set(DEFAULT_VOICE)

        # Populate preset combo
        presets = self.engine.get_all_presets()
        preset_names = [f"{pid} ({data.get('name')})" for pid, data in presets.items()]
        self.preset_combo["values"] = preset_names

        # Populate Locale filter
        locales = sorted(list(set(v.get("Locale", "") for v in voices if v.get("Locale"))))
        self.voice_locale_combo["values"] = ["All"] + locales

        # Populate voice explorer tree
        self._filter_voices_ui()
        self.header_status.config(text=f"● {len(voices)} Voices Loaded", fg=self.c_accent_green)

    # ---------------------------------------------------- Studio Actions

    def _on_preset_selected(self, _event: Any = None) -> None:
        val = self.preset_var.get()
        if not val or "--" in val:
            return
        pid = val.split(" ")[0].strip()
        presets = self.engine.get_all_presets()
        if pid in presets:
            p = presets[pid]
            if p.get("voice"):
                self.studio_voice_var.set(p["voice"])
            if "rate" in p:
                rate_num = int(re.sub(r"[^0-9-]", "", p["rate"]) or "0")
                self.studio_rate_var.set(rate_num)
                self._on_rate_change(rate_num)
            if "pitch" in p:
                pitch_num = int(re.sub(r"[^0-9-]", "", p["pitch"]) or "0")
                self.studio_pitch_var.set(pitch_num)
                self._on_pitch_change(pitch_num)

            self.status_detail.config(text=f"Applied preset: {p.get('name')}")

    def _on_rate_change(self, val: Any) -> None:
        num = int(float(val))
        self.studio_rate_lbl.config(text=f"{num:+d}%")
        self._update_text_metrics()

    def _on_pitch_change(self, val: Any) -> None:
        num = int(float(val))
        self.studio_pitch_lbl.config(text=f"{num:+d}Hz")

    def _on_studio_text_modified(self, _event: Any = None) -> None:
        if self.studio_text.edit_modified():
            self._update_text_metrics()
            if self.auto_name_var.get():
                raw = self.studio_text.get("1.0", "end-1c").strip()
                self.studio_output_var.set(self.engine.generate_auto_filename(raw))
            self.studio_text.edit_modified(False)

    def _update_text_metrics(self) -> None:
        text = self.studio_text.get("1.0", "end-1c").strip()
        rate_str = f"{self.studio_rate_var.get():+d}%"
        m = self.engine.analyze_text(text, rate_str)
        self.metrics_var.set(
            f"Words: {m.word_count} | Chars: {m.char_count} | Estimated Duration: ~{m.estimated_duration_seconds}s | Complexity: {m.reading_grade_level}"
        )

    def _clean_markdown(self) -> None:
        text = self.studio_text.get("1.0", "end-1c")
        cleaned = re.sub(r"[#*_`~>\[\]]", "", text)
        self.studio_text.delete("1.0", "end")
        self.studio_text.insert("1.0", cleaned)
        self._update_text_metrics()

    def _clean_brackets(self) -> None:
        text = self.studio_text.get("1.0", "end-1c")
        cleaned = re.sub(r"\[.*?\]|\(.*?\)", "", text)
        self.studio_text.delete("1.0", "end")
        self.studio_text.insert("1.0", cleaned)
        self._update_text_metrics()

    def _clear_studio_text(self) -> None:
        self.studio_text.delete("1.0", "end")
        self._update_text_metrics()

    def _load_studio_file(self) -> None:
        fpath = filedialog.askopenfilename(filetypes=[("Text & Markdown", "*.txt;*.md"), ("All Files", "*.*")])
        if fpath:
            try:
                content = Path(fpath).read_text(encoding="utf-8")
                self.studio_text.delete("1.0", "end")
                self.studio_text.insert("1.0", content)
                self._update_text_metrics()
            except Exception as exc:
                messagebox.showerror("Error loading file", str(exc))

    def _toggle_auto_name(self) -> None:
        is_auto = self.auto_name_var.get()
        state = "disabled" if is_auto else "normal"
        self.studio_out_entry.config(state=state)
        self.browse_btn.config(state=state)
        if is_auto:
            raw = self.studio_text.get("1.0", "end-1c").strip()
            self.studio_output_var.set(self.engine.generate_auto_filename(raw))

    def _browse_studio_output(self) -> None:
        p = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3 Audio", "*.mp3"), ("All Files", "*.*")],
            initialfile=self.studio_output_var.get(),
        )
        if p:
            self.studio_output_var.set(p)

    def _on_generate_studio(self) -> None:
        if self.busy:
            return
        text = self.studio_text.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showwarning("No Text", "Please enter or paste text to convert.")
            return

        voice = self.studio_voice_var.get() or DEFAULT_VOICE
        rate = f"{self.studio_rate_var.get():+d}%"
        pitch = f"{self.studio_pitch_var.get():+d}Hz"
        output = self.studio_output_var.get().strip() or "output.mp3"
        gen_subs = self.subtitles_var.get()

        self._stop_audio()
        self.busy = True
        self.generate_btn.config(state="disabled")
        self.status_title.config(text=f"Generating with {voice}...")
        self.status_detail.config(text="Contacting neural speech engine...")

        def _worker() -> None:
            try:
                res = self.engine.synthesize_sync(
                    text=text,
                    voice=voice,
                    output_path=output,
                    rate=rate,
                    pitch=pitch,
                    generate_subtitles=gen_subs,
                )
                self.event_queue.put(("synthesis_done", res))
            except Exception as exc:
                self.event_queue.put(("synthesis_error", str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_synthesis_complete(self, result: SynthesisResult) -> None:
        self.busy = False
        self.generate_btn.config(state="normal")
        if hasattr(self, "dialogue_gen_btn"):
            self.dialogue_gen_btn.config(state="normal")
        self.last_audio_path = result.audio_path
        self.status_title.config(text=f"✓ Saved: {Path(result.audio_path).name}")
        sub_info = f" + Subtitles ({Path(result.srt_path).name})" if result.srt_path else ""
        self.status_detail.config(text=f"Duration: ~{result.duration_estimate_sec}s | Words: {result.word_count}{sub_info}")
        self._refresh_history_tree()
        self._play_audio(result.audio_path)

    def _on_synthesis_error(self, err: str) -> None:
        self.busy = False
        self.generate_btn.config(state="normal")
        if hasattr(self, "dialogue_gen_btn"):
            self.dialogue_gen_btn.config(state="normal")
        messagebox.showerror("Synthesis Failed", err)
        self.status_title.config(text="Synthesis Failed")
        self.status_detail.config(text=err)

    def _on_play_last(self) -> None:
        if self._music_playing:
            self._stop_audio()
        else:
            if self.last_audio_path:
                self._play_audio(self.last_audio_path)
            else:
                messagebox.showinfo("Nothing to Play", "Generate an audio track first.")

    def _reveal_last_file(self) -> None:
        if self.last_audio_path and os.path.exists(self.last_audio_path):
            folder = os.path.abspath(os.path.dirname(self.last_audio_path))
            if sys.platform == "win32":
                os.system(f'explorer /select,"{os.path.abspath(self.last_audio_path)}"')
            else:
                os.system(f'open "{folder}"')
        else:
            messagebox.showinfo("File not found", "No generated file found.")

    # ---------------------------------------------------- Dialogue Actions

    def _load_sample_dialogue(self) -> None:
        sample = (
            "# Multi-Speaker Script Example\n"
            "[Narrator | en-US-ChristopherNeural]: Welcome to Text to Speech Studio v2.0.\n"
            "[Alice | en-US-JennyNeural | rate=+5%]: Hey Bob! Did you see how realistic these neural voices sound?\n"
            "[Bob | en-US-GuyNeural | rate=+0% | pitch=-4Hz]: I sure did, Alice! And it automatically synchronizes subtitles for every single line.\n"
            "[Narrator | en-US-ChristopherNeural]: Ready to create your own podcast, audiobook, or video voiceover in seconds."
        )
        self.dialogue_text.delete("1.0", "end")
        self.dialogue_text.insert("1.0", sample)

    def _on_generate_dialogue(self) -> None:
        if self.busy:
            return
        script = self.dialogue_text.get("1.0", "end-1c").strip()
        if not script:
            messagebox.showwarning("No Script", "Write or load a dialogue script first.")
            return

        self._stop_audio()
        self.busy = True
        self.dialogue_gen_btn.config(state="disabled")
        self.status_title.config(text="Compiling dialogue master track...")

        def _worker() -> None:
            try:
                res = asyncio.run(
                    self.engine.synthesize_dialogue(
                        script_text=script,
                        generate_subtitles=True,
                    )
                )
                self.event_queue.put(("synthesis_done", res))
            except Exception as exc:
                self.event_queue.put(("synthesis_error", str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    # ------------------------------------------------- Voice Explorer Actions

    def _filter_voices_ui(self) -> None:
        q = self.voice_search_var.get().lower().strip()
        loc = self.voice_locale_var.get()
        gen = self.voice_gender_var.get()

        for item in self.voices_tree.get_children():
            self.voices_tree.delete(item)

        for v in self._all_voices:
            s_name = v.get("ShortName", "")
            v_loc = v.get("Locale", "")
            v_gen = v.get("Gender", "")
            f_name = v.get("FriendlyName", "")

            if loc != "All" and loc != v_loc:
                continue
            if gen != "All" and gen != v_gen:
                continue
            if q and (q not in s_name.lower() and q not in f_name.lower() and q not in v_loc.lower()):
                continue

            self.voices_tree.insert("", "end", values=(s_name, v_loc, v_gen, f_name))

    def _refresh_voices(self) -> None:
        self.header_status.config(text="● Refreshing voices...", fg=self.c_accent)
        threading.Thread(
            target=lambda: self.event_queue.put(("voices_loaded", self.engine.list_voices_sync(force_refresh=True))),
            daemon=True,
        ).start()

    def _on_audition_selected_voice(self) -> None:
        selected = self.voices_tree.selection()
        if not selected:
            messagebox.showinfo("Select a Voice", "Please select a voice from the table to audition.")
            return

        v_id = self.voices_tree.item(selected[0])["values"][0]
        self.audition_status_lbl.config(text=f"Auditioning {v_id}...")

        def _worker() -> None:
            try:
                sample_path = f"sample_{v_id}.mp3"
                res = self.engine.synthesize_sync(
                    text=f"Hi there! I am {v_id}. Ready to speak your text with natural human quality.",
                    voice=v_id,
                    output_path=sample_path,
                )
                self.last_audio_path = res.audio_path
                self._play_audio(res.audio_path)
                self.event_queue.put(("status_update", f"Auditioning: {v_id}"))
            except Exception as exc:
                self.event_queue.put(("synthesis_error", str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _use_selected_voice_in_studio(self) -> None:
        selected = self.voices_tree.selection()
        if not selected:
            return
        v_id = self.voices_tree.item(selected[0])["values"][0]
        self.studio_voice_var.set(v_id)
        self.notebook.select(self.tab_studio)
        self.status_detail.config(text=f"Voice selected for studio: {v_id}")

    # ---------------------------------------------------- Batch Actions

    def _add_batch_files(self) -> None:
        paths = filedialog.askopenfilenames(filetypes=[("Text & Markdown", "*.txt;*.md"), ("All Files", "*.*")])
        for p in paths:
            self.batch_listbox.insert("end", p)
        self.batch_progress_lbl.config(text=f"{self.batch_listbox.size()} files queued")

    def _clear_batch_files(self) -> None:
        self.batch_listbox.delete(0, "end")
        self.batch_progress_lbl.config(text="0 files queued")

    def _start_batch_conversion(self) -> None:
        count = self.batch_listbox.size()
        if count == 0:
            messagebox.showinfo("Queue Empty", "Add text files to the batch queue first.")
            return

        out_dir = filedialog.askdirectory(title="Select Output Directory for Batch Audio")
        if not out_dir:
            return

        files = [self.batch_listbox.get(i) for i in range(count)]
        voice = self.studio_voice_var.get() or DEFAULT_VOICE
        self.batch_start_btn.config(state="disabled")

        def _worker() -> None:
            done = 0
            for idx, fpath in enumerate(files, 1):
                try:
                    p = Path(fpath)
                    text = p.read_text(encoding="utf-8").strip()
                    if not text:
                        continue
                    out_f = Path(out_dir) / f"{p.stem}.mp3"
                    self.event_queue.put(("batch_progress", f"Processing [{idx}/{count}]: {p.name}"))
                    self.engine.synthesize_sync(text=text, voice=voice, output_path=str(out_f), generate_subtitles=True)
                    done += 1
                except Exception as exc:
                    self.event_queue.put(("status_update", f"Batch error on {fpath}: {exc}"))

            self.event_queue.put(("batch_done", f"Successfully converted {done} of {count} files in batch!"))

        threading.Thread(target=_worker, daemon=True).start()

    # --------------------------------------------------- History Actions

    def _refresh_history_tree(self) -> None:
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        for h in self.engine.get_history():
            self.history_tree.insert(
                "",
                "end",
                values=(h.timestamp, h.mode, h.voice, h.word_count, f"{h.duration_sec}s", h.audio_path),
            )

    def _play_history_selected(self) -> None:
        selected = self.history_tree.selection()
        if not selected:
            return
        audio_path = self.history_tree.item(selected[0])["values"][5]
        self._play_audio(audio_path)

    def _reveal_history_selected(self) -> None:
        selected = self.history_tree.selection()
        if not selected:
            return
        audio_path = str(self.history_tree.item(selected[0])["values"][5])
        if os.path.exists(audio_path):
            if sys.platform == "win32":
                os.system(f'explorer /select,"{os.path.abspath(audio_path)}"')
            else:
                os.system(f'open "{os.path.dirname(audio_path)}"')

    def _clear_history_ui(self) -> None:
        if messagebox.askyesno("Clear History", "Are you sure you want to clear your generation history?"):
            self.engine.clear_history()
            self._refresh_history_tree()


def main() -> None:
    root = tk.Tk()
    TTSStudioGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
