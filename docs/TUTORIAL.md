# FrameLab Tutorial

A step-by-step walkthrough from first launch to real-world use cases.

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

## Part 2: Use Case — Frame Breakdown

**What you'll do:** Upload a single cinematic still and get a structured technical analysis — composition, lighting, and optics — without writing any prompt.

**Best for:** Learning cinematography, building mood boards, studying reference frames.

### Steps

1. In **Phase 1**, click **Original Reference Media** and upload a single image (PNG, JPG, JPEG, or WEBP).
2. The image preview appears below the uploader.
3. In the sidebar, select **System Prompt Preset → Frame Breakdown**, then click **Load**.
4. Leave the **Initial Prompt** text box empty — the Frame Breakdown system prompt is self-contained and drives the analysis directly.
5. Click **Analyze**.
6. The streamed analysis appears in the right column.

### What You Get

The output follows a fixed structure:

- **Narrative Description** — A concise paragraph covering visual story, mood, color palette, and spatial relationships.
- **Composition & Geometry** — Perspective, shot size, balance, leading lines.
- **Lighting & Photometry** — Luminance, direction, color temperature, quality.
- **Optics & Sensor Specifications** — Focal length, depth of field, lens character, camera format.

> **No Phase 2 needed.** This use case is a single-pass analysis. Proceed to Part 3 for a workflow that uses the refinement loop.

---

## Part 3: Use Case — Shotlist Script

**What you'll do:** Upload 2–3 reference images (character poses, location shots, props) and generate a full shooting script with lookbook breakdown and numbered shot list. Then refine it in Phase 2.

**Best for:** Pre-production planning, turning a visual concept into a camera-ready screenplay.

### Phase 1: Generate the Shotlist

1. In **Phase 1**, upload 2–3 reference images — for example, a character portrait, a location wide shot, and a key prop close-up.
2. The thumbnail strip shows compact previews. Click **Manage media tags** to rename tags from defaults (`@image1`, `@image2`) to descriptive names like `@detective`, `@alley`, `@knife`.
3. In the sidebar, select **System Prompt Preset → Shotlist Script Builder**, then click **Load**.
4. In the **Initial Prompt** text area, describe your scene concept. For example:

   > *"A tense confrontation in a rain-soaked alley at night. The detective (image 1) corners the suspect (image 2) near a dumpster (image 3). The scene starts calm and escalates to a chase."*

5. Click **Analyze**.

### What You Get

The output has two parts:

- **Part 1: Scene Header (Lookbook)** — Aesthetic mood, theme, location, time, lighting, sound atmosphere, key props, character descriptions (referencing your media tags), staging, and shot map.
- **Part 2: Screenplay (Shot List)** — A numbered shot-by-shot script using standard screenplay format with shot sizes (WS, MS, CU, ECU), angles (HIGH, LOW, DUTCH), and movement (STATIC, DOLLY, HANDHELD, PUSH-IN).

### Phase 2: Refine the Script

After Phase 1 completes, the **Phase 2** panel appears below.

1. In the **Refinement Notes** text area, type specific revision instructions. For example:

   > *"Add more extreme close-ups on the suspect's hands during the confrontation. Slow the pacing in the first beat — hold the wide shot longer before cutting in. Add SFX for distant thunder."*

2. Click **Run Refinement**.
3. The refined script appears in the Phase 2 output column, building on the original analysis.

> **Tip:** You can run Phase 2 multiple times. Each refinement builds on the previous output. Use the **Refinement Notes Preset** dropdown to load structured correction templates, or type freeform instructions.

---

## Part 4: Use Case — Video-to-Screenplay

**What you'll do:** Upload a video clip and convert it into a chronological, production-ready screenplay. Optionally add reference images for context.

**Best for:** Transcribing existing footage, creating shot documentation from dailies, building screenplays from reference material.

### Phase 1: Generate the Screenplay

1. In **Phase 1**, upload an **MP4** file (max 30 MB).
2. Optionally upload 1–2 reference images alongside the video — for example, a location reference or a character sheet. Use **Manage media tags** to give them clear names.
3. In the sidebar, select **System Prompt Preset → Video-to-Screenplay**, then click **Load**.
4. In the **Initial Prompt** text area, describe what you want extracted. For example:

   > *"Convert this video into a detailed hybrid screenplay. Focus on accurate dialogue transcription, shot-by-shot camera breakdown, and sound design notes. Mark any unclear audio as [inaudible]."*

5. Click **Analyze**.

### What You Get

The output follows this structure:

- **Summary paragraph** — A single continuous overview of the full video's visual and audible progression.
- **Screenplay** — Chronological shot-by-shot script with timecodes, framing, camera movement, action description, dialogue (exact transcription where audible), audio cues, on-screen text, and transitions.

> **Note:** Video analysis uses more tokens than image analysis. Monitor the usage caption below the output.

### Optional Phase 2

If you want to refine the screenplay:

1. Upload a comparison or corrected version of the video/images in the **Phase 2** uploader.
2. Add refinement notes — for example, *"Clarify the dialogue attribution in the second scene. The speaker is the woman, not the man. Add more ambient sound descriptions."*
3. Click **Run Refinement**.

---

## Part 5: Advanced Features

### 5.1 Output Actions

Below each output (Phase 1 and Phase 2):

- **Copy Plain Text** — Strips markdown formatting for clean paste into documents.
- **Copy Markdown** — Preserves the full markdown structure.
- **✏️ Edit** — Opens a dialog to manually revise the output. After editing, the usage caption shows "Edited by user".
- **Usage caption** — Shows input/output/total token counts when available from the provider.

### 5.2 POS Highlighting (Optional)

FrameLab can highlight parts of speech in English outputs using spaCy.

1. Check **Highlight POS (EN only): verbs / adjectives / nouns** below the output.
2. Use the **POS types to highlight** multiselect to choose which tags appear:
   - **Verb** → red background
   - **Adjective** → blue background
   - **Noun** → green background
3. The highlighted text renders in the output area. Plain text copy remains unmodified.

> **Note:** This requires the spaCy `en_core_web_sm` model (installed via `uv sync`). It only works on English text.

### 5.3 Multiple Media & Tagging

When uploading multiple files in a single phase:

1. A **thumbnail strip** shows compact previews.
2. Click **Manage media tags** to open a dialog with full-size previews.
3. Rename tags from defaults (`@image1`, `@video1`) to descriptive names like `@hero-shot` or `@reference-clip`.
4. Click **Apply tags**. Tags appear in the Request Transparency payload.

> **Tip:** Duplicate tags trigger a warning. Use unique names for clarity.

### 5.4 Request Transparency

Each phase has a collapsed **🔎 Request Transparency** expander. Expand it to see:

- **Metadata line:** Provider, endpoint, model, reasoning effort.
- **Payload chips:** What's being sent — system prompt, reference media, prompt/context, previous output (Phase 2), correction notes.

This helps you verify exactly what the model receives before clicking Analyze or Run Refinement.

### 5.5 Session Request Logging

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

### System Prompt Presets

| Preset | Best For |
|--------|----------|
| **Frame Breakdown** | Structured film-frame analysis (narrative, composition, lighting, optics) |
| **Shotlist Script Builder** | Turning concepts into camera-ready shooting scripts |
| **Video Prompt Planner** | Multi-shot directorial scripts with sonic/motion choreography |
| **Film Mentor** | Creative coaching bridging traditional filmmaking and AI |
| **Video-to-Screenplay** | Converting video footage into production-ready screenplays |

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