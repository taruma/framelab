# FrameLab

FrameLab is a lightweight multimodal AI web app for cinematic image analysis. It accepts a reference image with optional context, streams detailed technical breakdowns (covering composition, lighting, and optics), and supports a correction loop where users can submit a new image with notes to refine the analysis. Built with Python + Streamlit + OpenAI SDK, it displays live streaming output, model reasoning/thinking, and token usage while supporting any OpenAI-compatible endpoint.

> **⚙️ Default Configuration**: Currently uses **BytePlus** endpoint (`https://ark.ap-southeast.bytepluses.com/api/v3`) with **seed-2-0-lite** model. Modify `config.py` or use the sidebar to change to your preferred provider and model.

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
- One-click copy buttons for Phase 1 and Phase 2 results (copied as plain text)
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
  - Options: `none`, `minimal`, `low`, `medium`, `high`
  - Default selected value on app load: `low`
  - Selected value is sent as-is to request reasoning effort settings
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
- Usage summary (`input`, `output`, `total` tokens) when provided by the endpoint/model
- A **Copy Output (plain text)** button for one-click copying without markdown formatting

### 3) Phase 2 — Correction Loop

Appears only after Phase 1 completes.

- Upload **generated/incorrect image**
- Uploaded correction image is shown as a preview
- Add **Correction Notes** (what is wrong)
- Click **Submit Correction**

Model receives prior context and returns an updated analysis.

Right panel also provides a **Copy Updated Analysis (plain text)** button for one-click copying of the latest corrected output.

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
- `phase1_usage`
- `phase2_output`, `phase2_reasoning`
- `phase2_usage`

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

- API keys can be loaded from `.env` (`OPENAI_API_KEY`) or entered in the sidebar.
- Sidebar API key input overrides `.env` when both are present.
- Avoid sharing screenshots/logs containing secrets.
- For production deployment, use secret management (env vars / platform secret store).

---

## Project Files

- `run.py` — Streamlit UI + app bootstrap (`uv run run.py`)
- `app_state.py` — session-state keys and initialization
- `conversation.py` — multimodal message construction/conversion helpers
- `llm_streaming.py` — streaming transport/delta parsing/fallback flow
- `config.py` — default endpoint/model configuration
- `system_prompt.txt` — default system prompt content
- `.env.example` — sample env variable template
- `pyproject.toml` — minimal dependencies
- `AGENTS.md` — contributor/iteration guide for future changes














