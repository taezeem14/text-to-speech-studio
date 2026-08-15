"""Text to Speech Web Studio - Modern Browser Interface & REST API.

A standalone, zero-dependency local web studio with glassmorphism UI,
real-time Web Audio API visualizer, multi-speaker dialogue builder,
instant MP3 / SRT / VTT downloads, and REST API endpoints.

Run with:
    python web_studio.py
"""

from __future__ import annotations

import asyncio
import json
import mimetypes
import os
import re
import sys
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

from tts_engine import BUILTIN_PRESETS, DEFAULT_VOICE, TTSStudioEngine

engine = TTSStudioEngine()
STATIC_OUTPUT_DIR = Path("web_output")
STATIC_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Text to Speech Studio v2.0 • Neural AI Voice Suite</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>
    :root {
      --bg: #0b0f17;
      --card-bg: rgba(22, 28, 45, 0.75);
      --card-border: rgba(255, 255, 255, 0.08);
      --accent: #00d2ff;
      --accent-purple: #9d4edd;
      --accent-green: #00f59b;
      --accent-glow: rgba(0, 210, 255, 0.35);
      --text: #f0f6fc;
      --subtext: #8b949e;
      --input-bg: rgba(13, 17, 23, 0.85);
      --font-main: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--bg);
      background-image: 
        radial-gradient(at 0% 0%, rgba(0, 210, 255, 0.12) 0px, transparent 50%),
        radial-gradient(at 100% 100%, rgba(157, 78, 221, 0.12) 0px, transparent 50%);
      color: var(--text);
      font-family: var(--font-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }

    /* Top Navbar */
    header {
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      background: rgba(11, 15, 23, 0.85);
      border-bottom: 1px solid var(--card-border);
      padding: 14px 28px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .logo-badge {
      background: linear-gradient(135deg, var(--accent), var(--accent-purple));
      color: #000;
      font-weight: 800;
      font-size: 14px;
      padding: 6px 12px;
      border-radius: 8px;
      letter-spacing: 0.5px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }

    .brand h1 {
      font-size: 18px;
      font-weight: 700;
      letter-spacing: -0.3px;
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: rgba(0, 245, 155, 0.1);
      border: 1px solid rgba(0, 245, 155, 0.3);
      color: var(--accent-green);
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
    }
    .status-dot {
      width: 7px;
      height: 7px;
      background: var(--accent-green);
      border-radius: 50%;
      box-shadow: 0 0 8px var(--accent-green);
    }

    /* Container */
    main {
      flex: 1;
      max-width: 1200px;
      width: 100%;
      margin: 0 auto;
      padding: 24px 20px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    /* Navigation Tabs */
    .tabs-nav {
      display: flex;
      gap: 10px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 10px;
    }

    .tab-btn {
      background: transparent;
      border: 1px solid transparent;
      color: var(--subtext);
      font-family: var(--font-main);
      font-size: 14px;
      font-weight: 600;
      padding: 8px 18px;
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .tab-btn:hover {
      color: var(--text);
      background: rgba(255, 255, 255, 0.04);
    }
    .tab-btn.active {
      color: var(--accent);
      background: rgba(0, 210, 255, 0.1);
      border-color: rgba(0, 210, 255, 0.25);
    }

    /* Studio Card */
    .glass-card {
      background: var(--card-bg);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid var(--card-border);
      border-radius: 18px;
      padding: 24px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.3);
    }

    .tab-content { display: none; }
    .tab-content.active { display: block; }

    /* Text Editor Area */
    .editor-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      flex-wrap: wrap;
      gap: 10px;
    }

    .presets-row {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }

    .preset-pill {
      background: var(--input-bg);
      border: 1px solid var(--card-border);
      color: var(--subtext);
      font-size: 12px;
      padding: 4px 10px;
      border-radius: 14px;
      cursor: pointer;
      transition: 0.2s;
    }
    .preset-pill:hover, .preset-pill.active {
      color: var(--accent);
      border-color: var(--accent);
      background: rgba(0, 210, 255, 0.08);
    }

    textarea {
      width: 100%;
      height: 180px;
      background: var(--input-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      color: var(--text);
      font-family: var(--font-main);
      font-size: 15px;
      line-height: 1.6;
      padding: 16px;
      outline: none;
      resize: vertical;
      transition: border-color 0.2s;
    }
    textarea:focus {
      border-color: var(--accent);
      box-shadow: 0 0 16px rgba(0, 210, 255, 0.15);
    }

    .metrics-bar {
      display: flex;
      gap: 16px;
      margin-top: 8px;
      font-size: 12px;
      color: var(--subtext);
      flex-wrap: wrap;
    }
    .metrics-bar span b { color: var(--text); }

    /* Controls Grid */
    .controls-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-top: 20px;
    }

    .control-item {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    label {
      font-size: 13px;
      font-weight: 600;
      color: var(--subtext);
      display: flex;
      justify-content: space-between;
    }

    select, input[type="text"] {
      background: var(--input-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      color: var(--text);
      font-family: var(--font-main);
      font-size: 14px;
      padding: 10px 12px;
      outline: none;
    }
    select:focus, input[type="text"]:focus {
      border-color: var(--accent);
    }

    input[type="range"] {
      accent-color: var(--accent);
      cursor: pointer;
    }

    /* Buttons & Actions */
    .action-row {
      display: flex;
      gap: 12px;
      margin-top: 24px;
      align-items: center;
      flex-wrap: wrap;
    }

    .btn-primary {
      background: linear-gradient(135deg, #00d2ff, #0077ff);
      color: #000;
      border: none;
      font-family: var(--font-main);
      font-weight: 700;
      font-size: 14px;
      padding: 12px 24px;
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.2s;
      box-shadow: 0 4px 20px rgba(0, 210, 255, 0.3);
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .btn-primary:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 24px rgba(0, 210, 255, 0.45);
    }
    .btn-primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      transform: none;
    }

    .btn-secondary {
      background: var(--input-bg);
      border: 1px solid var(--card-border);
      color: var(--text);
      font-family: var(--font-main);
      font-weight: 600;
      font-size: 13px;
      padding: 10px 16px;
      border-radius: 8px;
      cursor: pointer;
      transition: 0.2s;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .btn-secondary:hover {
      border-color: var(--accent);
      color: var(--accent);
    }

    /* Player & Visualizer Bar */
    .player-dock {
      margin-top: 24px;
      background: rgba(13, 17, 23, 0.95);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 16px 20px;
      display: flex;
      align-items: center;
      gap: 20px;
      flex-wrap: wrap;
    }

    canvas#visualizer {
      width: 240px;
      height: 48px;
      background: #080b10;
      border-radius: 8px;
    }

    audio {
      flex: 1;
      height: 40px;
      min-width: 240px;
    }

    /* Voice Explorer Table */
    .voice-table-wrap {
      max-height: 440px;
      overflow-y: auto;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      margin-top: 14px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      text-align: left;
    }
    th {
      background: var(--input-bg);
      padding: 10px 14px;
      color: var(--accent);
      font-weight: 600;
      position: sticky;
      top: 0;
    }
    td {
      padding: 10px 14px;
      border-top: 1px solid var(--card-border);
      color: var(--text);
    }
    tr:hover td {
      background: rgba(255, 255, 255, 0.02);
    }

    .tag-gender {
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 600;
    }
    .tag-female { background: rgba(255, 105, 180, 0.15); color: #ff69b4; }
    .tag-male { background: rgba(0, 210, 255, 0.15); color: #00d2ff; }

    /* Subtitles Box */
    .subtitles-preview {
      background: #080b10;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 12px;
      font-family: var(--font-mono);
      font-size: 12px;
      color: #7ee787;
      max-height: 160px;
      overflow-y: auto;
      margin-top: 14px;
      white-space: pre-wrap;
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <span class="logo-badge"><i class="fa-solid fa-microphone-lines"></i> TTS 2.0</span>
      <h1>Text to Speech Studio</h1>
    </div>
    <div class="status-badge">
      <div class="status-dot"></div>
      <span id="headerStatus">Neural Voices Active (100% Free)</span>
    </div>
  </header>

  <main>
    <div class="tabs-nav">
      <button class="tab-btn active" onclick="switchTab('studio')"><i class="fa-solid fa-microphone-lines"></i> Single Studio</button>
      <button class="tab-btn" onclick="switchTab('dialogue')"><i class="fa-solid fa-comments"></i> Dialogue Lab</button>
      <button class="tab-btn" onclick="switchTab('voices')"><i class="fa-solid fa-list-ul"></i> Voice Directory</button>
      <button class="tab-btn" onclick="switchTab('api')"><i class="fa-solid fa-code"></i> REST API</button>
    </div>

    <!-- TAB 1: SINGLE STUDIO -->
    <section id="tab-studio" class="tab-content active">
      <div class="glass-card">
        <div class="editor-header">
          <div class="presets-row" id="presetPills">
            <span style="font-size: 12px; color: var(--subtext); font-weight: 600;"><i class="fa-solid fa-sliders"></i> Presets:</span>
            <!-- Populated via JS -->
          </div>
        </div>

        <textarea id="textInput" placeholder="Type or paste your text here to convert into ultra-realistic neural speech..."></textarea>
        
        <div class="metrics-bar">
          <span>Words: <b id="wordCount">0</b></span>
          <span>Characters: <b id="charCount">0</b></span>
          <span>Estimated Duration: <b id="estDuration">~0.0s</b></span>
          <span>Reading Level: <b id="readingGrade">Standard</b></span>
        </div>

        <div class="controls-grid">
          <div class="control-item">
            <label for="voiceSelect">Neural Voice</label>
            <select id="voiceSelect"></select>
          </div>
          <div class="control-item">
            <label>Speaking Speed: <span id="rateLabel" style="color:var(--accent);">+0%</span></label>
            <input type="range" id="rateSlider" min="-50" max="100" value="0">
          </div>
          <div class="control-item">
            <label>Pitch Shift: <span id="pitchLabel" style="color:var(--accent-purple);">+0Hz</span></label>
            <input type="range" id="pitchSlider" min="-50" max="50" value="0">
          </div>
        </div>

        <div class="action-row">
          <button id="generateBtn" class="btn-primary" onclick="generateSpeech()">
            <i class="fa-solid fa-bolt"></i> <span>Synthesize Speech & Subtitles</span>
          </button>
          <div id="downloadLinks" style="display: none; gap: 8px;">
            <a id="mp3Download" class="btn-secondary" href="#" download><i class="fa-solid fa-download"></i> Download MP3</a>
            <a id="srtDownload" class="btn-secondary" href="#" download><i class="fa-solid fa-closed-captioning"></i> Download SRT</a>
            <a id="vttDownload" class="btn-secondary" href="#" download><i class="fa-solid fa-file-lines"></i> Download VTT</a>
          </div>
        </div>

        <div id="playerDock" class="player-dock" style="display: none;">
          <canvas id="visualizer"></canvas>
          <audio id="audioPlayer" controls></audio>
        </div>

        <div id="subtitlesBox" class="subtitles-preview" style="display: none;"></div>
      </div>
    </section>

    <!-- TAB 2: DIALOGUE LAB -->
    <section id="tab-dialogue" class="tab-content">
      <div class="glass-card">
        <h3 style="font-size: 16px; margin-bottom: 8px; color: var(--accent-purple); display:flex; align-items:center; gap:8px;">
          <i class="fa-solid fa-comments"></i> Multi-Speaker Script Dialogue Studio
        </h3>
        <p style="font-size: 13px; color: var(--subtext); margin-bottom: 14px;">
          Compose full conversational scripts. Each character is rendered with their own voice and stitched into a seamless master track with synchronized subtitles!
        </p>

        <textarea id="dialogueInput" style="height: 220px; font-family: var(--font-mono); font-size: 13px;">[Narrator | en-US-ChristopherNeural]: In a world where AI speech was expensive and slow, a new studio emerged.
[Alice | en-US-JennyNeural]: Wait, Bob! You mean we can build entire podcasts and video dialogues for free?
[Bob | en-US-GuyNeural | rate=+5%]: Exactly Alice! With over 400 neural voices and automatic SRT subtitles.
[Narrator | en-US-ChristopherNeural]: Text to Speech Studio v2.0. Uncapped. Free forever.</textarea>

        <div class="action-row">
          <button id="dialogueBtn" class="btn-primary" style="background: linear-gradient(135deg, #9d4edd, #00d2ff);" onclick="generateDialogue()">
            <i class="fa-solid fa-wand-magic-sparkles"></i> <span>Compile Master Dialogue</span>
          </button>
          <div id="dialogueDownloads" style="display: none; gap: 8px;">
            <a id="dialogueMp3" class="btn-secondary" href="#" download><i class="fa-solid fa-download"></i> Master Audio</a>
            <a id="dialogueSrt" class="btn-secondary" href="#" download><i class="fa-solid fa-closed-captioning"></i> Dialogue SRT</a>
          </div>
        </div>

        <div id="dialoguePlayerDock" class="player-dock" style="display: none;">
          <audio id="dialogueAudio" controls style="width: 100%;"></audio>
        </div>
      </div>
    </section>

    <!-- TAB 3: VOICE DIRECTORY -->
    <section id="tab-voices" class="tab-content">
      <div class="glass-card">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
          <h3 style="font-size: 16px; display:flex; align-items:center; gap:8px;">
            <i class="fa-solid fa-list-ul"></i> Microsoft Edge Neural Voice Catalog
          </h3>
          <input type="text" id="voiceSearch" placeholder="Search voices by country, language, name..." style="width: 280px;" oninput="filterVoicesTable()">
        </div>

        <div class="voice-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Voice ID</th>
                <th>Locale</th>
                <th>Gender</th>
                <th>Friendly Name</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody id="voiceTableBody">
              <!-- Populated via JS -->
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- TAB 4: REST API DOCS -->
    <section id="tab-api" class="tab-content">
      <div class="glass-card">
        <h3 style="font-size: 16px; margin-bottom: 8px; color: var(--accent); display:flex; align-items:center; gap:8px;">
          <i class="fa-solid fa-code"></i> Developer REST API Endpoints
        </h3>
        <p style="font-size: 13px; color: var(--subtext); margin-bottom: 16px;">
          Integrate neural TTS directly into your apps, bots, Discord servers, and content automation pipelines.
        </p>

        <div style="display: flex; flex-direction: column; gap: 14px;">
          <div style="background: var(--input-bg); padding: 14px; border-radius: 8px; border: 1px solid var(--card-border);">
            <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 6px;">
              <span style="background: #00d2ff; color:#000; font-weight:700; font-size:11px; padding:2px 6px; border-radius:4px;">POST</span>
              <code style="color:var(--text); font-family:var(--font-mono);">/api/synthesize</code>
            </div>
            <p style="font-size: 12px; color: var(--subtext);">Body: <code>{"text": "Hello world", "voice": "en-US-ChristopherNeural", "rate": "+0%", "subtitles": true}</code></p>
          </div>

          <div style="background: var(--input-bg); padding: 14px; border-radius: 8px; border: 1px solid var(--card-border);">
            <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 6px;">
              <span style="background: #9d4edd; color:#fff; font-weight:700; font-size:11px; padding:2px 6px; border-radius:4px;">POST</span>
              <code style="color:var(--text); font-family:var(--font-mono);">/api/dialogue</code>
            </div>
            <p style="font-size: 12px; color: var(--subtext);">Body: <code>{"script": "[Alice]: Hi!\n[Bob]: Hello!"}</code></p>
          </div>

          <div style="background: var(--input-bg); padding: 14px; border-radius: 8px; border: 1px solid var(--card-border);">
            <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 6px;">
              <span style="background: #00f59b; color:#000; font-weight:700; font-size:11px; padding:2px 6px; border-radius:4px;">GET</span>
              <code style="color:var(--text); font-family:var(--font-mono);">/api/voices</code>
            </div>
            <p style="font-size: 12px; color: var(--subtext);">Returns full array of available neural voices with gender and locale tags.</p>
          </div>
        </div>
      </div>
    </section>
  </main>


  <script>
    let allVoices = [];
    let presets = {};
    let audioCtx, analyser, dataArray, canvas, canvasCtx, sourceNode;

    function switchTab(tabId) {
      document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
      document.getElementById('tab-' + tabId).classList.add('active');
      event.currentTarget.classList.add('active');
    }

    async function init() {
      setupVisualizer();
      setupTextInput();

      // Fetch presets & voices
      try {
        const [pRes, vRes] = await Promise.all([fetch('/api/presets'), fetch('/api/voices')]);
        presets = await pRes.json();
        allVoices = await vRes.json();

        renderPresets();
        renderVoiceSelect();
        renderVoiceTable(allVoices);
      } catch (err) {
        console.error('Init error:', err);
      }
    }

    function renderPresets() {
      const pillContainer = document.getElementById('presetPills');
      for (const [id, data] of Object.entries(presets)) {
        const btn = document.createElement('button');
        btn.className = 'preset-pill';
        btn.textContent = data.name;
        btn.onclick = () => applyPreset(id);
        pillContainer.appendChild(btn);
      }
    }

    function applyPreset(pid) {
      const p = presets[pid];
      if (!p) return;
      if (p.voice) document.getElementById('voiceSelect').value = p.voice;
      if (p.rate) {
        const rVal = parseInt(p.rate) || 0;
        document.getElementById('rateSlider').value = rVal;
        document.getElementById('rateLabel').textContent = (rVal >= 0 ? '+' : '') + rVal + '%';
      }
      if (p.pitch) {
        const pVal = parseInt(p.pitch) || 0;
        document.getElementById('pitchSlider').value = pVal;
        document.getElementById('pitchLabel').textContent = (pVal >= 0 ? '+' : '') + pVal + 'Hz';
      }
      updateMetrics();
    }

    function renderVoiceSelect() {
      const select = document.getElementById('voiceSelect');
      select.innerHTML = '';
      allVoices.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.ShortName;
        opt.textContent = `${v.ShortName} (${v.Locale}, ${v.Gender})`;
        if (v.ShortName === 'en-US-ChristopherNeural') opt.selected = true;
        select.appendChild(opt);
      });
    }

    function renderVoiceTable(voices) {
      const tbody = document.getElementById('voiceTableBody');
      tbody.innerHTML = '';
      voices.slice(0, 150).forEach(v => {
        const tr = document.createElement('tr');
        const isFem = v.Gender === 'Female';
        tr.innerHTML = `
          <td style="font-family:var(--font-mono); font-weight:600; color:var(--accent);">${v.ShortName}</td>
          <td>${v.Locale}</td>
          <td><span class="tag-gender ${isFem ? 'tag-female' : 'tag-male'}">${v.Gender}</span></td>
          <td style="color:var(--subtext);">${v.FriendlyName}</td>
          <td>
            <button class="btn-secondary" style="padding:4px 10px; font-size:11px;" onclick="auditionVoice('${v.ShortName}')"><i class="fa-solid fa-volume-high"></i> Audition</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    function filterVoicesTable() {
      const q = document.getElementById('voiceSearch').value.toLowerCase().trim();
      const filtered = allVoices.filter(v => 
        v.ShortName.toLowerCase().includes(q) ||
        v.Locale.toLowerCase().includes(q) ||
        v.FriendlyName.toLowerCase().includes(q)
      );
      renderVoiceTable(filtered);
    }

    function setupTextInput() {
      const textInput = document.getElementById('textInput');
      const rateSlider = document.getElementById('rateSlider');
      const pitchSlider = document.getElementById('pitchSlider');

      textInput.addEventListener('input', updateMetrics);
      rateSlider.addEventListener('input', (e) => {
        const val = e.target.value;
        document.getElementById('rateLabel').textContent = (val >= 0 ? '+' : '') + val + '%';
        updateMetrics();
      });
      pitchSlider.addEventListener('input', (e) => {
        const val = e.target.value;
        document.getElementById('pitchLabel').textContent = (val >= 0 ? '+' : '') + val + 'Hz';
      });
    }

    function updateMetrics() {
      const text = document.getElementById('textInput').value.trim();
      const chars = text.length;
      const words = text ? text.split(/\s+/).length : 0;
      const rateVal = parseInt(document.getElementById('rateSlider').value) || 0;
      const rateMod = 1.0 + (rateVal / 100.0);
      const duration = words > 0 ? ((words / (150 * rateMod)) * 60).toFixed(1) : '0.0';

      document.getElementById('charCount').textContent = chars;
      document.getElementById('wordCount').textContent = words;
      document.getElementById('estDuration').textContent = `~${duration}s`;
    }

    async function generateSpeech() {
      const text = document.getElementById('textInput').value.trim();
      if (!text) return alert('Please enter some text to synthesize.');

      const voice = document.getElementById('voiceSelect').value;
      const rate = (parseInt(document.getElementById('rateSlider').value) >= 0 ? '+' : '') + document.getElementById('rateSlider').value + '%';
      const pitch = (parseInt(document.getElementById('pitchSlider').value) >= 0 ? '+' : '') + document.getElementById('pitchSlider').value + 'Hz';

      const btn = document.getElementById('generateBtn');
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> <span>Synthesizing Neural Audio...</span>';

      try {
        const res = await fetch('/api/synthesize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, voice, rate, pitch, subtitles: true })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.error || 'Synthesis error');

        // Play audio
        const audio = document.getElementById('audioPlayer');
        audio.src = data.audio_url;
        document.getElementById('playerDock').style.display = 'flex';
        audio.play();

        // Download links
        document.getElementById('downloadLinks').style.display = 'flex';
        document.getElementById('mp3Download').href = data.audio_url;
        if (data.srt_url) {
          document.getElementById('srtDownload').href = data.srt_url;
          document.getElementById('srtDownload').style.display = 'inline-flex';
        }
        if (data.vtt_url) {
          document.getElementById('vttDownload').href = data.vtt_url;
          document.getElementById('vttDownload').style.display = 'inline-flex';
        }

        // Show subtitles
        if (data.srt_text) {
          const sBox = document.getElementById('subtitlesBox');
          sBox.style.display = 'block';
          sBox.textContent = data.srt_text;
        }

      } catch (err) {
        alert('Synthesis failed: ' + err.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-bolt"></i> <span>Synthesize Speech & Subtitles</span>';
      }
    }

    async function generateDialogue() {
      const script = document.getElementById('dialogueInput').value.trim();
      if (!script) return alert('Please enter a dialogue script.');

      const btn = document.getElementById('dialogueBtn');
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> <span>Compiling Dialogue Track...</span>';

      try {
        const res = await fetch('/api/dialogue', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ script })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.error || 'Dialogue error');

        const audio = document.getElementById('dialogueAudio');
        audio.src = data.audio_url;
        document.getElementById('dialoguePlayerDock').style.display = 'flex';
        audio.play();

        document.getElementById('dialogueDownloads').style.display = 'flex';
        document.getElementById('dialogueMp3').href = data.audio_url;
        if (data.srt_url) {
          document.getElementById('dialogueSrt').href = data.srt_url;
        }
      } catch (err) {
        alert('Dialogue generation failed: ' + err.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> <span>Compile Master Dialogue</span>';
      }
    }

    async function auditionVoice(voiceId) {
      try {
        const res = await fetch('/api/synthesize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: `Hi! This is a neural sample of ${voiceId}. Ready to voice your next big project!`,
            voice: voiceId
          })
        });
        const data = await res.json();
        if (data.audio_url) {
          const audio = new Audio(data.audio_url);
          audio.play();
        }
      } catch (err) {
        alert('Audition error: ' + err.message);
      }
    }

    function setupVisualizer() {
      canvas = document.getElementById('visualizer');
      canvasCtx = canvas.getContext('2d');
      const audio = document.getElementById('audioPlayer');

      audio.onplay = () => {
        if (!audioCtx) {
          audioCtx = new (window.AudioContext || window.webkitAudioContext)();
          analyser = audioCtx.createAnalyser();
          analyser.fftSize = 64;
          sourceNode = audioCtx.createMediaElementSource(audio);
          sourceNode.connect(analyser);
          analyser.connect(audioCtx.destination);
          dataArray = new Uint8Array(analyser.frequencyBinCount);
        }
        drawWaveform();
      };
    }

    function drawWaveform() {
      if (!analyser) return;
      requestAnimationFrame(drawWaveform);
      analyser.getByteFrequencyData(dataArray);

      canvasCtx.fillStyle = '#080b10';
      canvasCtx.fillRect(0, 0, canvas.width, canvas.height);

      const barWidth = (canvas.width / dataArray.length) * 2;
      let x = 0;

      for (let i = 0; i < dataArray.length; i++) {
        const barHeight = (dataArray[i] / 255) * (canvas.height - 4);
        const gradient = canvasCtx.createLinearGradient(0, canvas.height, 0, 0);
        gradient.addColorStop(0, '#00d2ff');
        gradient.addColorStop(1, '#9d4edd');

        canvasCtx.fillStyle = gradient;
        canvasCtx.fillRect(x, canvas.height - barHeight, barWidth - 1, barHeight);
        x += barWidth + 1;
      }
    }

    window.onload = init;
  </script>
</body>
</html>
"""


class WebStudioHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for Web Studio & REST API."""

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        if path == "/api/voices":
            try:
                voices = engine.list_voices_sync()
                self._send_json(voices)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)
            return

        if path == "/api/presets":
            presets = engine.get_all_presets()
            self._send_json(presets)
            return

        if path.startswith("/static/"):
            fname = path[len("/static/"):]
            fpath = STATIC_OUTPUT_DIR / fname
            if fpath.exists():
                ctype, _ = mimetypes.guess_type(str(fpath))
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", ctype or "application/octet-stream")
                self.send_header("Content-Length", str(fpath.stat().st_size))
                self.end_headers()
                with open(fpath, "rb") as f:
                    self.wfile.write(f.read())
                return
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            data = json.loads(body.decode("utf-8"))
        except Exception:
            data = {}

        if path == "/api/synthesize":
            text = data.get("text", "").strip()
            if not text:
                self._send_json({"success": False, "error": "Text is required."}, status=400)
                return

            voice = data.get("voice", DEFAULT_VOICE)
            rate = data.get("rate", "+0%")
            pitch = data.get("pitch", "+0Hz")
            subtitles = bool(data.get("subtitles", True))

            out_filename = engine.generate_auto_filename(text)
            out_path = STATIC_OUTPUT_DIR / out_filename

            try:
                res = engine.synthesize_sync(
                    text=text,
                    voice=voice,
                    output_path=str(out_path),
                    rate=rate,
                    pitch=pitch,
                    generate_subtitles=subtitles,
                )
                self._send_json(
                    {
                        "success": True,
                        "audio_url": f"/static/{out_filename}",
                        "srt_url": f"/static/{Path(res.srt_path).name}" if res.srt_path else None,
                        "vtt_url": f"/static/{Path(res.vtt_path).name}" if res.vtt_path else None,
                        "srt_text": res.srt_subtitles,
                        "duration_sec": res.duration_estimate_sec,
                        "words": res.word_count,
                    }
                )
            except Exception as exc:
                self._send_json({"success": False, "error": str(exc)}, status=500)
            return

        if path == "/api/dialogue":
            script = data.get("script", "").strip()
            if not script:
                self._send_json({"success": False, "error": "Script is required."}, status=400)
                return

            out_filename = f"dialogue_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            out_path = STATIC_OUTPUT_DIR / out_filename

            try:
                res = asyncio.run(
                    engine.synthesize_dialogue(
                        script_text=script,
                        output_path=str(out_path),
                        generate_subtitles=True,
                    )
                )
                self._send_json(
                    {
                        "success": True,
                        "audio_url": f"/static/{out_filename}",
                        "srt_url": f"/static/{Path(res.srt_path).name}" if res.srt_path else None,
                        "vtt_url": f"/static/{Path(res.vtt_path).name}" if res.vtt_path else None,
                        "duration_sec": res.duration_estimate_sec,
                        "words": res.word_count,
                    }
                )
            except Exception as exc:
                self._send_json({"success": False, "error": str(exc)}, status=500)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "API route not found")

    def _send_json(self, data: Any, status: int = 200) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:
        # Keep console output neat
        pass


def run_web_studio(port: int = 7860, open_browser: bool = True) -> None:
    """Launch the Web Studio HTTP server."""
    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, WebStudioHandler)
    url = f"http://localhost:{port}"

    print("=" * 65)
    print(f"🎙️  Text to Speech Web Studio v2.0 is LIVE!")
    print(f"🔗  URL: {url}")
    print(f"📁  Outputs: {STATIC_OUTPUT_DIR.resolve()}")
    print("=" * 65)

    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Web Studio...")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7860
    run_web_studio(port=port)
