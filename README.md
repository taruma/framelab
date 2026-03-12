# FrameLab

FrameLab is a lightweight multimodal AI web app for cinematic image analysis. It accepts a reference image with optional context, streams detailed technical breakdowns (covering composition, lighting, and optics), and supports a correction loop where users can submit a new image with notes to refine the analysis. Built with Python + Streamlit + OpenAI SDK, it displays live streaming output, model reasoning/thinking, and token usage while supporting any OpenAI-compatible endpoint.

> **⚙️ Default Configuration**: Provider presets now live in `config.toml` (BytePlus, OpenAI, Gemini, OpenRouter). Update that file to add/edit endpoints and models.

---

## Features

- Minimal dependencies: only `streamlit` and `openai`
- OpenAI-compatible endpoint support via configurable **Base URL**
- Provider/model/endpoint presets from `config.toml`
- Sidebar override support for endpoint/model
- API key resolution order: sidebar → provider env key → `LLM_API_KEY` → legacy fallback
- Folder-based prompt presets for system/initial/correction prompts
- Optional per-preset metadata via `.meta.toml` (title/description/order)
- Config-driven default preset selection via `config.toml` (`[prompts]`)
- Sidebar/manual override precedence over selected presets
- Uploaded image previews for both Phase 1 and Phase 2
- Real-time streaming output in UI
- Thought/reasoning stream shown in **Thought Process** expander
- One-click copy buttons for Phase 1 and Phase 2 results (copied as plain text)
- Per-phase **Request Transparency** expander (collapsed by default) showing request metadata and compact payload preview
- Token usage summary (input/output/total) shown after successful responses when provider returns usage
- Default request path uses **Responses API** (`client.responses.create`)
- Automatic fallback to **Chat Completions** if Responses is unsupported/fails
- Displays transport path used per request (**Responses API** or **Chat Completions fallback**)
- Surfaces underlying exception messages when Responses/fallback fail for easier debugging
- Auto-disables Responses API for current session when provider reports schema mismatch (e.g. missing `input.status`)
- Two-phase workflow:
  - Phase 1: Analyze reference image
  - Phase 2: Submit correction image + notes
- Session-based conversation memory (`st.session_state`)

---

## Tech Stack

- Python 3.11+
- Streamlit
- OpenAI Python SDK
- Dependency/runtime management: `uv`

---

## Setup

### A) Existing project (this repository)

```bash
uv sync
uv run run.py
```

Create `.env` (optional but recommended):

```bash
copy .env.example .env
```

Then set your API key:

```env
LLM_API_KEY=your_real_key
```

### B) From scratch (new folder)

```bash
uv init
uv add streamlit openai
```

Then place `run.py` in the project root and start with:

```bash
uv run run.py
```

---

## How to Use

### 1) Configure model (sidebar)

- **Provider**:
  - Select from presets loaded from `config.toml` (BytePlus/OpenAI/Gemini/OpenRouter)
- **API Key**:
  - Sidebar input has highest priority
  - If empty, app uses provider-specific env key from `config.toml`
  - Fallback to `LLM_API_KEY` (and legacy fallbacks for compatibility)
- **Base URL / Endpoint**:
  - Pre-filled from selected provider preset
  - Can still be manually overridden
- **Model**:
  - Select from provider model list
  - Optional manual model override is available
- **Reasoning Effort**:
  - Options: `none`, `minimal`, `low`, `medium`, `high`
  - Default selected value on app load: `low`
  - Selected value is sent as-is to request reasoning effort settings
- **System Prompt Override (optional)**:
  - Select preset from dropdown (loaded from configured prompt folder)
  - If empty override, app uses selected preset content
  - If preset is unavailable, app falls back to `system_prompt.txt`

- **Initial Prompt Preset + Editable Textbox**:
  - Select a preset, then click **Load Initial Preset**
  - The loaded content is shown in the editable **Initial Prompt** textbox
  - You can review and modify the text before Analyze

- **Correction Notes Preset + Editable Textbox**:
  - Select a preset, then click **Load Correction Preset**
  - The loaded content is shown in the editable **Correction Notes** textbox
  - You can review and modify the text before Submit Correction

### 2) Phase 1 — Initial Analysis

- Upload **Original Reference Image**
- Uploaded image is shown as a preview
- Add **Additional Context** (optional)
- Click **Analyze**

Right panel shows:
- **Thought Process** (if `reasoning_content`/reasoning deltas are returned)
- Final streamed analysis
- Usage summary (`input`, `output`, `total` tokens) when provided by the endpoint/model
- A **Copy Output (plain text)** button for one-click copying without markdown formatting

Above the Phase 1 section, the app also shows a **🔎 Request Transparency** expander (collapsed by default):
- `⚙️ Request`: provider, endpoint, model, reasoning effort
- `📦 Payload`: compact one-line preview with distinct color segments (`system`, `image`, `context`), text truncated to 30 words
- Live-updates as inputs change, so users can verify what will be sent before clicking **Analyze**

The transparency panel now uses thinner text styling and richer visual emphasis (color + bold/italic/underline accents). Metadata fields are color-separated for quick scanning.

### 3) Phase 2 — Correction Loop

Appears only after Phase 1 completes.

- Upload **generated/incorrect image**
- Uploaded correction image is shown as a preview
- Add **Correction Notes** (what is wrong)
- Click **Submit Correction**

Model receives prior context and returns an updated analysis.

Right panel also provides a **Copy Updated Analysis (plain text)** button for one-click copying of the latest corrected output.

After the horizontal divider (before Phase 2 columns), the app shows the same **🔎 Request Transparency** expander for Phase 2, with payload preview sections for system prompt, original image token, prior assistant output, correction image token, and correction notes. This preview also live-updates from current Phase 2 inputs.

Each transparency block uses the native expander toggle only (cleaner UI, no extra control buttons).

---

## Message / State Behavior

Prompt behavior:

1. **System prompt** precedence:
   - Manual sidebar override textarea (if non-empty)
   - Selected preset file content (`.txt`)
   - Config default preset selection (`[prompts]` in `config.toml`, by filename)
   - Built-in fallback (`system_prompt.txt`)
2. **Initial prompt** and **Correction notes**:
   - Main source is the editable textbox
   - Preset dropdown acts as a loader source via **Load Preset** button
   - Textbox is seeded once from config default preset on first load

Correction flow follows this payload order:

1. `system` prompt (if provided)
2. `user`: original image + additional context
3. `assistant`: first analysis output
4. `user`: correction image + correction notes

This conversation is persisted in `st.session_state`:

- `phase1_done`
- `conversation_messages`
- `phase1_output`, `phase1_reasoning`
- `phase1_usage`
- `phase2_output`, `phase2_reasoning`
- `phase2_usage`

---

## Custom Prompt Presets

You can add your own prompt templates for all three prompt types.

### 1) Folder structure

- System prompts: `prompts/system/`
- Initial prompts: `prompts/initial/`
- Correction prompts: `prompts/correction/`

Each preset is a plain `.txt` file.

Example:

```text
prompts/system/product_photo_critic.txt
prompts/initial/quick_scene_summary.txt
prompts/correction/fix_lighting_focus.txt
```

### 2) Optional metadata (`.meta.toml`)

To improve dropdown labels and descriptions in UI, add a sidecar metadata file with the same base name:

```text
prompts/system/product_photo_critic.meta.toml
```

Example metadata:

```toml
title = "Product Photo Critic"
description = "Focuses on commercial product imaging quality, styling, and lighting consistency."
order = 20
```

Fields:
- `title` (optional): display name in dropdown
- `description` (optional): helper text below preset selector
- `order` (optional): sort priority (lower appears first)

If metadata is missing, the app uses filename-based labels.

### 3) Set defaults in `config.toml`

Configure preset directories and default files in `[prompts]`:

```toml
[prompts]
system_dir = "prompts/system"
initial_dir = "prompts/initial"
correction_dir = "prompts/correction"
default_system = "cinematic_analysis.txt"
default_initial = "detailed_technical_creative.txt"
default_correction = "refine_with_correction_image.txt"
```

`default_*` values must match exact filenames inside each folder.

### 4) Runtime behavior

- **System prompt**:
  1. Sidebar override textarea (if not empty)
  2. Selected system preset content
  3. Config default system preset selection
  4. `system_prompt.txt` fallback

- **Initial prompt** and **Correction notes**:
  - Main source is editable textbox
  - Preset dropdown + **Load** button injects template into textbox
  - Selecting dropdown alone does not overwrite textbox

### 5) Quick workflow to add a custom preset

1. Add new `.txt` file in the target folder.
2. (Optional) Add `.meta.toml` for title/description/order.
3. (Optional) Set it as default in `config.toml` (`default_system`, `default_initial`, or `default_correction`).
4. Restart app:

```bash
uv run run.py
```

---

## Troubleshooting

- **Runtime instance already exists**
  - Fixed in current `run.py` bootstrap logic.
  - Use exactly: `uv run run.py`

- **No Thought Process shown**
  - Not all models/providers return reasoning deltas.
  - Final answer stream still works.

- **401 / auth errors**
  - Verify API key and endpoint pair (key must match provider).

- **Model not found / unsupported multimodal input**
  - Ensure selected model supports image inputs at your endpoint.
  - App now tries Responses API first and falls back to Chat Completions automatically.

- **Responses API compatibility issues**
  - Some OpenAI-compatible providers/models may not fully support Responses stream events.
  - App will automatically retry the same request via Chat Completions.
  - UI now shows the underlying Responses error message and the final transport used.
  - If provider reports a known schema mismatch (for example missing `input.status`), Responses API is auto-disabled for the current session and app will use Chat Completions directly on next requests.

- **Phase 2 fails after Phase 1 succeeds**
  - This can still happen when Phase 2 payload is larger (prior answer + additional image + notes).
  - Check the displayed transport/error details in UI to identify whether failure is in Responses, fallback, or both.

- **Usage metrics not shown**
  - Some providers/models do not return usage in streaming mode.
  - App will show a fallback message when usage metadata is unavailable.

- **Image upload issues**
  - Supported: `png`, `jpg`, `jpeg`, `webp`.

---

## Security Notes

- API keys can be loaded from `.env` (`LLM_API_KEY` and/or provider-specific keys) or entered in the sidebar.
- Sidebar API key input overrides `.env` when both are present.
- Avoid sharing screenshots/logs containing secrets.
- For production deployment, use secret management (env vars / platform secret store).

---

## Project Files

- `run.py` — Streamlit UI + app bootstrap (`uv run run.py`)
- `app_state.py` — session-state keys and initialization
- `conversation.py` — multimodal message construction/conversion helpers
- `llm_streaming.py` — streaming transport/delta parsing/fallback flow
- `config.toml` — provider presets + prompt preset directories/defaults (`[prompts]`)
- `prompts/system/*.txt` — system prompt presets
- `prompts/initial/*.txt` — initial prompt presets
- `prompts/correction/*.txt` — correction note presets
- `*.meta.toml` (optional sidecar per preset) — UI metadata (`title`, `description`, `order`)
- `system_prompt.txt` — legacy fallback system prompt content
- `.env.example` — sample env variable template
- `pyproject.toml` — minimal dependencies
- `AGENTS.md` — contributor/iteration guide for future changes

























