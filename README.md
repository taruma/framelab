# Cinebot

Lightweight multimodal AI web app built with **Python + Streamlit + OpenAI SDK**, designed for:

1. **Initial image analysis** (reference image + optional context)
2. **Correction loop** (new/incorrect image + correction notes)

The app streams responses live and can display model reasoning/thinking output (when the endpoint/model provides it).

---

## Features

- Minimal dependencies: only `streamlit` and `openai`
- OpenAI-compatible endpoint support via configurable **Base URL**
- Hybrid configuration fallback:
  - Sidebar input (if provided)
  - Otherwise defaults from `config.py`
- API key support from `.env` with sidebar override priority
- Externalized default system prompt via `system_prompt.txt`
- Uploaded image previews for both Phase 1 and Phase 2
- Real-time streaming output in UI
- Thought/reasoning stream shown in **Thought Process** expander
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
OPENAI_API_KEY=your_real_key
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

- **API Key**:
  - Sidebar input has highest priority
  - If left empty, app uses `OPENAI_API_KEY` from `.env`
- **Base URL / Endpoint**:
  - If sidebar is left empty, app uses `DEFAULT_BASE_URL` from `config.py`
  - You can override for OpenAI-compatible providers (local, OpenRouter, Groq, etc.)
- **Model Name**:
  - If sidebar is left empty, app uses `DEFAULT_MODEL` from `config.py`
- **Reasoning Effort**:
  - Options: `default`, `minimal`, `low`, `medium`, `high`
  - `default` sends no explicit reasoning effort parameter
  - `minimal` maps to `low` (compatibility alias for "least thinking")
  - `low`/`medium`/`high` send `reasoning_effort` for reasoning-capable models/providers
- **System Prompt Override (optional)**:
  - If empty, app uses default prompt content from `system_prompt.txt`

### 2) Phase 1 — Initial Analysis

- Upload **Original Reference Image**
- Uploaded image is shown as a preview
- Add **Additional Context** (optional)
- Click **Analyze**

Right panel shows:
- **Thought Process** (if `reasoning_content`/reasoning deltas are returned)
- Final streamed analysis

### 3) Phase 2 — Correction Loop

Appears only after Phase 1 completes.

- Upload **generated/incorrect image**
- Uploaded correction image is shown as a preview
- Add **Correction Notes** (what is wrong)
- Click **Submit Correction**

Model receives prior context and returns an updated analysis.

---

## Message / State Behavior

Correction flow follows this payload order:

1. `system` prompt (if provided)
2. `user`: original image + additional context
3. `assistant`: first analysis output
4. `user`: correction image + correction notes

This conversation is persisted in `st.session_state`:

- `phase1_done`
- `conversation_messages`
- `phase1_output`, `phase1_reasoning`
- `phase2_output`, `phase2_reasoning`

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
  - Ensure selected model supports image inputs and chat completions at your endpoint.

- **Image upload issues**
  - Supported: `png`, `jpg`, `jpeg`, `webp`.

---

## Security Notes

- API keys can be loaded from `.env` (`OPENAI_API_KEY`) or entered in the sidebar.
- Sidebar API key input overrides `.env` when both are present.
- Avoid sharing screenshots/logs containing secrets.
- For production deployment, use secret management (env vars / platform secret store).

---

## Project Files

- `run.py` — complete application (single-file architecture)
- `config.py` — default endpoint/model configuration
- `system_prompt.txt` — default system prompt content
- `.env.example` — sample env variable template
- `pyproject.toml` — minimal dependencies
- `AGENT.md` — contributor/iteration guide for future changes






