# AGENTS.md

Guidance for future contributors/agents working on this repository.

---

## 1) Product Intent

Build and maintain a **lightweight multimodal analysis app** that:

1. Accepts a reference image or video + optional context
2. Produces a detailed streamed analysis
3. Supports a refinement loop using a second image or video + refinement notes

The app must remain easy to run and easy to modify.

---

## 2) Hard Constraints (Do Not Break)

- Keep dependencies minimal: `streamlit` + `openai` as baseline, with approved optional POS-highlighting support via `spacy` + `en_core_web_sm`.
- POS highlighting must remain optional and default OFF (no extra NLP processing unless user enables it).
- Primary run command must remain: **`uv run run.py`**.
- Preserve OpenAI-compatible flexibility:
  - user-provided API key
  - user-provided base URL/endpoint
  - user-provided model name

Keep the current lightweight modular layout unless explicitly asked otherwise.

---

## 3) Current Architecture

- `run.py`
  - Streamlit UI layout and app bootstrap for `uv run run.py`
  - Sidebar config handling (provider preset, API key, endpoint, model, reasoning effort, system prompt override)
  - Phase 1/Phase 2 orchestration and usage rendering
  - Per-phase Request Transparency preview and processing-state locking
  - Optional EN POS highlighting for outputs (Verb/Adjective/Noun) with lazy/cached spaCy model loading
- `app_state.py`
  - Session-state key constants and `init_state()` defaults
- `conversation.py`
  - Multimodal message helpers and conversion to Responses API input format
- `llm_streaming.py`
  - Streaming transport and delta parsing
  - **Responses API first**, with automatic fallback to Chat Completions
- `config.toml`
  - Provider presets (endpoint/model), prompt directories, and default prompt selections
- `prompts/`
  - Folder-based preset sources for system, initial, and correction text
  - Optional `.meta.toml` sidecars (`title`, `description`, `order`) for UI labels/descriptions
- `system_prompt.txt`
  - Externalized default system prompt

---

## 4) UX Contract

Must preserve:

- Two-column layout in each phase.
- Phase 1 always visible.
- Phase 2 visible **only** after Phase 1 is complete.
- Per-phase **Request Transparency** expander (collapsed by default), with live-updating compact payload preview.
- Editable prompt textboxes for Phase 1 (Initial Prompt) and Phase 2 (Refinement Notes), with explicit preset load actions.
- Right-side output order:
  1) `Thought Process` expander
  2) final streamed response
  3) usage caption (when provided)
- One-click copy buttons for Phase 1 and Phase 2 outputs (plain text).
- Optional POS highlighting controls per output (EN only), with separate selection for Verb/Adjective/Noun.
- Highlighted rendering must not modify stored raw outputs; copy remains plain text.
- Streaming should feel live (incremental updates, not batch render).

---

## 5) Conversation/State Contract

Session keys currently used:

- `phase1_done`
- `conversation_messages`
- `phase1_output`, `phase1_reasoning`
- `phase1_usage`
- `phase2_output`, `phase2_reasoning`
- `phase2_usage`

Configuration/prompt precedence must remain:

- API key resolution: sidebar input → provider env key (`config.toml`) → `LLM_API_KEY` → legacy fallback
- System prompt resolution: manual override → selected system preset → config default system preset → `system_prompt.txt`
- Initial prompt and refinement notes source: editable textbox content (preset dropdown is loader input via explicit button)

Refinement payload message order must remain:

1. System prompt (if provided)
2. User: original image + additional context
3. Assistant: first output
4. User: refinement image + refinement notes

Any refactor must preserve this logic.

---

## 6) API Compatibility Notes

- Default streaming path uses `client.responses.create(..., stream=True)`.
- If Responses API fails/unsupported, app automatically falls back to
  `client.chat.completions.create(..., stream=True)`.
- Different providers may vary in streaming/usage/reasoning fields; keep parsers resilient.
- During active requests, inputs/actions should be locked to prevent duplicate submissions.
- If adding provider-specific compatibility, keep defaults simple and avoid adding non-essential dependencies.

Deployment note (spaCy model):

- For Streamlit Cloud/reproducible builds, install `en_core_web_sm` at build time via `requirements.txt` (model wheel URL), not runtime download.

---

## 7) Change Guidelines for Next Iterations

When making changes:

1. Preserve minimalism and readability.
2. Avoid architecture sprawl (no unnecessary modules/packages).
3. Keep UI labels aligned with user workflow language.
4. Ensure failures surface as clear `st.error(...)` messages.
5. Validate boot flow still works with `uv run run.py`.
6. Update `README.md` whenever behavior or setup changes.
7. Keep deep technical/runtime details in `docs/REFERENCE.md`; keep `README.md` concise and user-facing.
8. Ignore `uv.lock` for version/changelog tasks in this repository:
   - `uv.lock` is intentionally untracked/ignored.
   - Do not read, modify, or rely on `uv.lock` when bumping versions.
   - Use tracked files (e.g., `pyproject.toml`) and git commit history as source of truth.

---

## 8) Suggested Future Improvements (Optional)

Only implement if requested:

- Add “Reset conversation” button.
- Add export/download for final analysis and correction history.
- Add provider preset templates (OpenAI/OpenRouter/Groq/local) without hard-coding secrets.

---

## 9) Quick Acceptance Checklist

Before finishing any iteration, verify:

- [ ] `uv run run.py` starts app successfully
- [ ] Phase 1 accepts image/video and renders preview correctly (video = MP4)
- [ ] Phase 1 streams output live
- [ ] Thought Process expander updates when reasoning stream exists
- [ ] Phase 2 appears only after Phase 1
- [ ] Refinement call includes prior assistant output in context
- [ ] Request Transparency expander is present per phase and payload preview updates with current inputs
- [ ] Initial/Refinement preset loading populates editable textboxes; manual edits remain user-controlled
- [ ] Copy output buttons work for Phase 1 and Phase 2 plain-text results
- [ ] POS highlighting is optional/default OFF, and per-tag selection (Verb/Adjective/Noun) works when enabled
- [ ] Copy output remains plain text even when highlighted rendering is enabled
- [ ] Responses API path works, or fallback to Chat Completions works clearly
- [ ] Usage caption behavior is correct (shown when available, fallback message otherwise)
- [ ] `README.md` and `AGENTS.md` are up to date
