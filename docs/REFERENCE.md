# FrameLab Technical Reference

This document preserves the detailed behavior and implementation-oriented notes that were previously in `README.md`.

If you just want to run the app, start with [`README.md`](../README.md).

---

## Scope

FrameLab is a lightweight multimodal analysis app that:

1. Accepts one or more reference image/video items plus optional context
2. Streams a detailed model analysis
3. Supports an optional refinement loop with one or more additional image/video items + refinement notes

Primary run command:

```bash
uv run run.py
```

---

## Tech Stack

- Python 3.11+
- Streamlit
- OpenAI Python SDK
- Optional POS highlighting support: `spacy` + `en_core_web_sm`
- Runtime/dependency management: `uv`

---

## Setup

### Existing repository

```bash
uv sync
uv run run.py
```

Optional environment file:

```bash
copy .env.example .env
```

```env
LLM_API_KEY=your_real_key
```

### New folder bootstrap

```bash
uv init
uv add streamlit openai spacy "en_core_web_sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"
uv run run.py
```

---

## Runtime UX Contract

### Workflow

- **Phase 1** is always visible.
- **Phase 2** appears only after Phase 1 completes.
- Both phases support image/video upload preview (single or multiple files).
- For multi-media uploads, each item gets an editable tag/annotation field.

### Right-panel output order (per phase)

1. `Thought Process` expander (when reasoning exists)
2. Final streamed response
3. Usage caption (when usage metadata is available)

### Request Transparency

- One expander per phase
- Collapsed by default
- Shows request metadata and compact payload preview
- Preview is live-updated from current input state
- For multiple media items, preview includes media summary + media-tag mapping chip.
- For single media items, preview keeps legacy compact behavior (kind only).

### Copy behavior

- Phase 1 and Phase 2 provide one-click copy actions
- Copy output is plain text, even when highlighted rendering is enabled

### Optional POS highlighting (EN)

- Default: OFF
- Tag selection: Verb / Adjective / Noun
- spaCy model lazy-loads only when highlighting is enabled
- Highlight rendering does not overwrite stored raw output

---

## Configuration and Precedence

### Provider/API settings

- Presets are defined in `config.toml` (endpoint/model/provider env key)
- Sidebar can override endpoint/model/key at runtime

API key resolution order:

1. Sidebar API key input
2. Provider env key from `config.toml`
3. `LLM_API_KEY`
4. Legacy fallback keys

### Prompt selection precedence

System prompt resolution:

1. Manual override text (sidebar)
2. Selected system preset content
3. Config default system preset (`config.toml`)
4. `system_prompt.txt` fallback

Initial prompt and refinement notes:

- Source of truth is editable textbox content
- Preset dropdown is a loader source via explicit **Load** action

---

## Prompt Presets

Directories:

- `prompts/system/`
- `prompts/initial/`
- `prompts/correction/`

Each preset is a `.txt` file. Optional sidecar metadata:

```text
name.txt
name.meta.toml
```

Supported metadata fields:

- `title` (display label)
- `description` (helper copy)
- `order` (sorting priority)

Config defaults live in `[prompts]` in `config.toml`:

```toml
[prompts]
system_dir = "prompts/system"
initial_dir = "prompts/initial"
correction_dir = "prompts/correction"
default_system = "02_general_assist.txt"
default_initial = "10_image_deepdive.txt"
default_correction = "10_refine_with_image.txt"
```

---

## Message/Conversation Contract

### User media payload composition

- Single-media behavior remains backward compatible:
  - user text (if any)
  - one `image_url` or `video_url` content item
- Multi-media behavior (2+ items):
  - user text (if any)
  - for each media item, appended in-order as:
    1. tag text (`Media tag: @... (source: filename)`)
    2. media payload (`image_url` or `video_url`)
- This ensures each media is explicitly paired with an alias/tag in both:
  - Chat Completions payload
  - Responses API-converted payload (`input_text` + `input_image/input_video`)

Default media tags:

- Images: `@image1`, `@image2`, ...
- Videos: `@video1`, `@video2`, ...

Users can edit these tags in the UI before submit.

Refinement payload message order:

1. `system` prompt (if provided)
2. `user`: original media (single/multi) + additional context
3. `assistant`: first output
4. `user`: refinement media (single/multi) + refinement notes

Session state keys:

- `phase1_done`
- `conversation_messages`
- `phase1_output`, `phase1_reasoning`, `phase1_usage`
- `phase2_output`, `phase2_reasoning`, `phase2_usage`

---

## Streaming/API Compatibility

- Primary path: `client.responses.create(..., stream=True)`
- Fallback path: `client.chat.completions.create(..., stream=True)`
- App surfaces transport path and underlying errors when available
- For known provider schema mismatch cases, Responses API may be auto-disabled for the current session

Provider behavior varies in reasoning and usage stream fields; parsers are intentionally defensive.

---

## Troubleshooting

- **No reasoning shown**: Some providers/models do not emit reasoning deltas.
- **401/auth issues**: Verify API key and endpoint are from the same provider.
- **Model unsupported**: Confirm model accepts selected media type (image/MP4).
- **Usage not shown**: Some providers omit usage in streaming mode.
- **Phase 2 failure only**: Payload can be larger due to prior output + additional media/notes.
- **Media limits**:
  - Supported images: `png`, `jpg`, `jpeg`, `webp`
  - Supported video: `mp4`
  - App-level MP4 limit: 30 MB (provider/Streamlit limits may be stricter)
- **POS highlighting issues**:
  - Ensure dependencies are synced (`uv sync`) so `spacy==3.8.2` and `en_core_web_sm` are installed
  - Highlighting is English-oriented and may be imperfect for multilingual output

### Streamlit Cloud note (spaCy)

Install `en_core_web_sm` at build time via `requirements.txt` wheel URL (do not depend on runtime download).

---

## Security Notes

- API keys can come from `.env` or sidebar input
- Sidebar key overrides environment key for the running session
- Avoid sharing logs/screenshots containing secrets
- Use platform secret stores for production deployments

---

## Project File Map

- `run.py` — Streamlit UI/bootstrap/orchestration
- `app_state.py` — session-state key defaults
- `conversation.py` — multimodal message helpers and conversion
- `llm_streaming.py` — streaming transport and fallback parsing
- `config.toml` — provider presets and prompt defaults/directories
- `prompts/**` — prompt presets and optional `.meta.toml` sidecars
- `system_prompt.txt` — fallback system prompt source
- `AGENTS.md` — contributor/agent implementation guidance

---

For contributor rules and architectural constraints, see [`AGENTS.md`](../AGENTS.md).