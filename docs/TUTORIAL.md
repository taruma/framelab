# FrameLab Tutorial

A step-by-step walkthrough from first launch to advanced workflows.

For a complete map of every UI element, see [`INTERFACE.md`](INTERFACE.md).

---

## Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) installed
- An API key from a supported provider (OpenAI, Gemini, OpenRouter, Claude, BytePlus, or Xiaomi)

---

## Part 1: Setup

### 1.1 Launch the App

```bash
git clone https://github.com/taruma/framelab.git
cd framelab
uv sync
uv run run.py
```

The app opens in your browser at `http://localhost:8501`.

### 1.2 Configure Your Environment (Recommended)

Copy the example env file and add your API key:

```bash
cp .env.example .env   # macOS/Linux
copy .env.example .env  # Windows
```

Then edit `.env`:

```
LLM_API_KEY=sk-your-key-here
```

This lets you skip pasting the key in the sidebar each session.

### 1.3 Configure Your Provider

In the **sidebar → API Setup**:

1. **Provider** — Select from the dropdown (e.g., OpenRouter, OpenAI, Gemini).
2. **API Key** — Paste your key, or leave blank if set in `.env`. The app shows which source it found.
3. **Base URL / Endpoint** — Auto-filled per provider. Override if using a custom proxy.
4. **Model** — Pick from the preset list or type a custom model name in "Model Override".
5. **Reasoning Effort** — Choose `none`, `minimal`, `low`, `medium`, or `high`.

> **Tip:** You can switch providers mid-session. The app remembers your streaming API preference automatically.

---

## Part 2: First Analysis

### 2.1 Text-Only Analysis (Simplest Case)

No images required — good for a first test.

1. Leave the **Original Reference Media** uploader empty.
2. In the **Initial Prompt** text area, type a request, for example:

   > *"Explain the key differences between shallow depth of field and deep depth of field in cinematography, with examples."*

3. Click **Analyze**.
4. Watch the output stream live in the right column.
5. Check the **Thought Process** expander for chain-of-thought reasoning (when available).

### 2.2 Image Analysis (Core Feature)

1. In **Phase 1**, click **Original Reference Media** and upload an image (PNG, JPG, JPEG, or WEBP).
2. The image preview appears below the uploader.
3. Click the **Initial Prompt Preset** dropdown and select **Image Deep Dive**, then click **Load**.
4. The prompt text box fills with a structured analysis request.
5. Click **Analyze**.
6. The streamed analysis appears in the right column.

### 2.3 Video Analysis

1. Upload an **MP4** file (max 30 MB) in the Phase 1 uploader.
2. Switch the system prompt to **Frame Breakdown** or **Video-to-Screenplay** (see 2.4).
3. In the Initial Prompt, describe what you want analyzed (e.g., *"Break down the camera movements and editing rhythm in this scene."*).
4. Click **Analyze**.

> **Note:** Video analysis uses more tokens. Monitor the usage caption below the output.

### 2.4 Switching System Prompt Presets

System prompts change the *persona and output structure* of the analysis. Try different ones:

| Preset | Best For |
|--------|----------|
| **Frame Breakdown** | Structured film-frame analysis (narrative, composition, lighting, optics) |
| **Shotlist Script Builder** | Turning concepts into camera-ready shooting scripts |
| **Video Prompt Planner** | Multi-shot directorial scripts with sonic/motion choreography |
| **Film Mentor** | Creative coaching bridging traditional filmmaking and AI |
| **Video-to-Screenplay** | Converting video footage into production-ready screenplays |

**How to switch:**

1. In the sidebar, open **System Prompt**.
2. Select a preset from the **System Prompt Preset** dropdown.
3. Click **Load**.
4. The text area updates. You can edit it further before running analysis.
5. Run Phase 1 again to see the different output style.

> **Tip:** Click **Open large editor** for a bigger editing window.

---

## Part 3: Refinement Loop

After Phase 1 completes, the **Phase 2** panel appears below.

### 3.1 Text-Only Refinement

1. In the **Refinement Notes** text area, type instructions like:

   > *"Focus more on the color grading and mood. Expand the lighting analysis."*

2. Click **Run Refinement**.

### 3.2 Media-Assisted Refinement

1. Upload a generated or comparison image/video in the **Correction Media** uploader.
2. Add refinement notes describing what should change.
3. Click **Run Refinement**.

> **How it works:** Phase 2 sends the full conversation context — system prompt, original media, your Phase 1 output, correction media, and refinement notes — so the model can revise its analysis.

### 3.3 Iterating Further

You can run Phase 2 multiple times. Each refinement builds on the previous output. Use the **Refinement Notes Preset** dropdown to load structured correction templates, or type freeform instructions.

---

## Part 4: Advanced Features

### 4.1 Output Actions

Below each output (Phase 1 and Phase 2):

- **Copy Plain Text** — Strips markdown formatting for clean paste into documents.
- **Copy Markdown** — Preserves the full markdown structure.
- **✏️ Edit** — Opens a dialog to manually revise the output. After editing, the usage caption shows "Edited by user".
- **Usage caption** — Shows input/output/total token counts when available from the provider.

### 4.2 POS Highlighting (Optional)

FrameLab can highlight parts of speech in English outputs using spaCy.

1. Check **Highlight POS (EN only): verbs / adjectives / nouns** below the output.
2. Use the **POS types to highlight** multiselect to choose which tags appear:
   - **Verb** → red background
   - **Adjective** → blue background
   - **Noun** → green background
3. The highlighted text renders in the output area. Plain text copy remains unmodified.

> **Note:** This requires the spaCy `en_core_web_sm` model (installed via `uv sync`). It only works on English text.

### 4.3 Multiple Media & Tagging

When uploading multiple files in a single phase:

1. A **thumbnail strip** shows compact previews.
2. Click **Manage media tags** to open a dialog with full-size previews.
3. Rename tags from defaults (`@image1`, `@video1`) to descriptive names like `@hero-shot` or `@reference-clip`.
4. Click **Apply tags**. Tags appear in the Request Transparency payload.

> **Tip:** Duplicate tags trigger a warning. Use unique names for clarity.

### 4.4 Request Transparency

Each phase has a collapsed **🔎 Request Transparency** expander. Expand it to see:

- **Metadata line:** Provider, endpoint, model, reasoning effort.
- **Payload chips:** What's being sent — system prompt, reference media, prompt/context, previous output (Phase 2), correction notes.

This helps you verify exactly what the model receives before clicking Analyze or Run Refinement.

### 4.5 Session Request Logging

For debugging or auditing:

1. In the sidebar, open **Session Request Logging**.
2. Toggle **Enable request logging (session-only)**.
3. Run analyses as normal. Each request/response is recorded.
4. Click **Download Session Logs (.json)** to export.

The JSON includes transport type, provider, endpoint, media filenames, request payload (base64 omitted), and response metadata.

---

## Quick Reference: Preset Directory

| Directory | Purpose |
|-----------|---------|
| `prompts/system/` | System prompt presets (persona/output structure) |
| `prompts/initial/` | Initial prompt presets (Phase 1 request templates) |
| `prompts/correction/` | Refinement note presets (Phase 2 request templates) |

Each `.txt` file can have an optional `.meta.toml` sidecar with `title`, `description`, and `order` fields for UI labels.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No API key found" | Set key in sidebar, `.env`, or environment variable (`LLM_API_KEY`, `API_KEY`, `OPENAI_API_KEY`) |
| "No providers found" | Check `config.toml` has at least one `[providers.xxx]` section |
| Video too large | Compress to under 30 MB or use a shorter clip |
| POS highlight error | Run `uv sync` to install spaCy and the model wheel |
| Streaming stops mid-response | Check provider status; try a different model or provider |
| Output looks wrong | Switch system prompt preset — different personas produce different analysis styles |

---

## Next Steps

- Read [`INTERFACE.md`](INTERFACE.md) for a complete map of every UI element.
- Read [`REFERENCE.md`](REFERENCE.md) for technical details, API behavior, and contracts.
- Browse `prompts/` to customize or create your own presets.
- Check [`CHANGELOG.md`](../CHANGELOG.md) for release history.

---

*Built with ❤️ by Taruma Sakti · Vibecoding with Cline + GPT-5.3-Codex*