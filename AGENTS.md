# AGENTS.md

Guidance for future contributors/agents working on this repository.

---

## 1) Product Intent

Build and maintain a **lightweight multimodal analysis app** that:

1. Accepts a reference image + optional context
2. Produces a detailed streamed analysis
3. Supports a correction loop using a second image + correction notes

The app must remain easy to run and easy to modify.

---

## 2) Hard Constraints (Do Not Break)

- Keep dependencies minimal: **only `streamlit` and `openai`** (plus Python stdlib).
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
  - Sidebar config handling (API key, endpoint, model, reasoning effort, system prompt override)
  - Phase 1/Phase 2 orchestration and usage rendering
- `app_state.py`
  - Session-state key constants and `init_state()` defaults
- `conversation.py`
  - Multimodal message helpers and conversion to Responses API input format
- `llm_streaming.py`
  - Streaming transport and delta parsing
  - **Responses API first**, with automatic fallback to Chat Completions
- `config.py`
  - Default base URL and default model
- `system_prompt.txt`
  - Externalized default system prompt

---

## 4) UX Contract

Must preserve:

- Two-column layout in each phase.
- Phase 1 always visible.
- Phase 2 visible **only** after Phase 1 is complete.
- Right-side output order:
  1) `Thought Process` expander
  2) final streamed response
  3) usage caption (when provided)
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

Correction payload message order must remain:

1. System prompt (if provided)
2. User: original image + additional context
3. Assistant: first output
4. User: correction image + correction notes

Any refactor must preserve this logic.

---

## 6) API Compatibility Notes

- Default streaming path uses `client.responses.create(..., stream=True)`.
- If Responses API fails/unsupported, app automatically falls back to
  `client.chat.completions.create(..., stream=True)`.
- Different providers may vary in streaming/usage/reasoning fields; keep parsers resilient.
- If adding provider-specific compatibility, keep defaults simple and avoid adding non-essential dependencies.

---

## 7) Change Guidelines for Next Iterations

When making changes:

1. Preserve minimalism and readability.
2. Avoid architecture sprawl (no unnecessary modules/packages).
3. Keep UI labels aligned with user workflow language.
4. Ensure failures surface as clear `st.error(...)` messages.
5. Validate boot flow still works with `uv run run.py`.
6. Update `README.md` whenever behavior or setup changes.

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
- [ ] Phase 1 streams output live
- [ ] Thought Process expander updates when reasoning stream exists
- [ ] Phase 2 appears only after Phase 1
- [ ] Correction call includes prior assistant output in context
- [ ] Responses API path works, or fallback to Chat Completions works clearly
- [ ] Usage caption behavior is correct (shown when available, fallback message otherwise)
- [ ] `README.md` and `AGENTS.md` are up to date
