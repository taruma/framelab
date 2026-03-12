# ✨ FrameLab

[![Latest Release](https://img.shields.io/github/v/release/taruma/framelab?style=flat-square&label=version)](https://github.com/taruma/framelab/releases/latest)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square)

**FrameLab** is a lightweight, multimodal AI analysis workbench designed for cinematic media. Whether you're analyzing composition, lighting, or technical optics, FrameLab provides a streamlined interface to get deep insights from your images and videos.

FrameLab is currently stable and aligned with its original product intent/goal.

> [!IMPORTANT]
> **Vibecoding Disclaimer**: This project is built using an AI-assisted "vibecoding" approach (rapid iteration with human supervision). It is experimental, may contain bugs, and could break unintentionally during updates. Use it as a creative tool, but keep your expectations grounded.

---

https://github.com/user-attachments/assets/5dd8a80b-d9d8-4150-a4a5-7bdca75738cc

*Cinematic analysis in action.*

---

## 🚀 Key Features

### 🎬 Multimodal Analysis
- **Image & Video Support**: Analyze images (PNG, JPG, WEBP) or MP4 videos up to 20MB.
- **Two-Phase Workflow**: Start with an initial analysis and refine it with an optional correction loop.
- **Cinematic Presets**: Built-in system prompts for film directors, script architects, and image critics.

### 🛠️ Developer & Power User Tools
- **Responses API Native**: Built to use the latest OpenAI Responses API with automatic fallback to Chat Completions.
- **Request Transparency**: Peek under the hood with a live-updating payload preview before you send requests.
- **Provider Presets**: Easily switch between OpenAI, Gemini, OpenRouter, BytePlus, or local endpoints via `config.toml`.
- **Reasoning Stream**: View the model's "thought process" in real-time for reasoning-capable models.

### 🎨 UI & Experience
- **Live Streaming**: Real-time output rendering for immediate feedback.
- **POS Highlighting**: Optional English Part-of-Speech highlighting (Verbs, Adjectives, Nouns) to help scan technical terminology.
- **One-Click Copy**: Clean "Copy to Clipboard" buttons for raw analysis text.

---

## ⚡ Quick Start

FrameLab uses `uv` for fast dependency and runtime management.

1. **Clone the repo:**
   ```bash
   git clone https://github.com/taruma/framelab.git
   cd framelab
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Set up your environment (optional but recommended):**
   ```bash
   # Windows (PowerShell / cmd)
   copy .env.example .env

   # macOS / Linux
   cp .env.example .env
   ```
   Then edit `.env` and add your `LLM_API_KEY`.

4. **Run the app:**
   ```bash
   uv run run.py
   ```

---

## 🕹️ How to Use

### Step 1: Configuration (Sidebar)
Configure your model settings in the sidebar. You can select from pre-configured **Providers** or manually override the API Key, Endpoint, and Model name.

### Step 2: Phase 1 — Initial Analysis
Upload your **Original Reference Media**, select an **Initial Prompt** (or write your own), and click **Analyze**. FrameLab will stream a detailed technical breakdown.

### Step 3: Phase 2 — Correction Loop (Optional)
If the analysis needs tweaking, upload a **Correction Image/Video** and provide **Correction Notes**. This sends the original context, the first answer, and your new media back to the model for a refined result.

---

## ⚙️ Advanced Configuration

### `config.toml`
The core of FrameLab's provider system. Edit this file to add new models, change default endpoints, or point to different prompt directories.

### Prompt Presets
FrameLab loads templates from the `prompts/` directory. You can add your own `.txt` files to:
- `prompts/system/` (System roles)
- `prompts/initial/` (Initial analysis tasks)
- `prompts/correction/` (Correction instructions)

*(Optional: Add a `.meta.toml` file next to your `.txt` to customize the title and description in the UI.)*

For deeper technical behavior (precedence rules, state contracts, fallback internals, troubleshooting), see [`docs/REFERENCE.md`](docs/REFERENCE.md).

---

## 🔬 Technical Notes

- **API Compatibility**: FrameLab defaults to the `client.responses.create` path. If your provider doesn't support it, the app automatically falls back to standard Chat Completions.
- **POS Highlighting**: Uses `spaCy`. It's off by default and only loads the `en_core_web_sm` model if you enable highlighting in the UI.
- **Session Memory**: Conversations are stored in Streamlit `session_state` and are cleared when you refresh the page.

---

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for more information.

---

## 🤝 Contributing

Public contributions are welcome, especially around prompt quality and creative workflows.

You can contribute by adding or improving presets in:

- `prompts/system/`
- `prompts/initial/`
- `prompts/correction/`

Optional: include a matching `.meta.toml` file (same base name) to improve UI title/description/order.

For technical/runtime details and behavior contracts, see [`docs/REFERENCE.md`](docs/REFERENCE.md).

---

Built with ❤️ by **Taruma Sakti** · Vibecoding with GPT-5.3-Codex







