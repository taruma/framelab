# AGENT.md

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

- Keep implementation in **single-file `run.py`** unless explicitly asked otherwise.
- Keep dependencies minimal: **only `streamlit` and `openai`** (plus Python stdlib).
- Primary run command must remain: **`uv run run.py`**.
- Preserve OpenAI-compatible flexibility:
  - user-provided API key
  - user-provided base URL/endpoint
  - user-provided model name

---

## 3) Current Architecture (run.py)

- `init_state()`
  - Initializes Streamlit session keys for phase state and outputs.
- `to_data_url(uploaded_file)`
  - Converts uploaded image bytes to base64 `data:` URL.
- `make_user_message(image_file, text)`
  - Builds multimodal user message with text + image.
- `extract_deltas(chunk)`
  - Extracts normal content deltas and reasoning deltas from streaming chunks.
- `stream_response(...)`
  - Executes streaming chat completion and updates UI placeholders live.
- `render()`
  - Full UI: sidebar config, phase 1, phase 2, validation, state writes.
- `__main__` block
  - Handles `uv run run.py` bootstrap and avoids Streamlit runtime recursion.

---

## 4) UX Contract

Must preserve:

- Two-column layout in each phase.
- Phase 1 always visible.
- Phase 2 visible **only** after Phase 1 is complete.
- Right-side output order:
  1) `Thought Process` expander
  2) final streamed response
- Streaming should feel live (incremental updates, not batch render).

---

## 5) Conversation/State Contract

Session keys currently used:

- `phase1_done`
- `conversation_messages`
- `phase1_output`, `phase1_reasoning`
- `phase2_output`, `phase2_reasoning`

Correction payload message order must remain:

1. System prompt (if provided)
2. User: original image + additional context
3. Assistant: first output
4. User: correction image + correction notes

Any refactor must preserve this logic.

---

## 6) API Compatibility Notes

- App currently uses `client.chat.completions.create(..., stream=True)`.
- Different providers may vary in reasoning fields; current parser handles common variants:
  - `delta.content`
  - `delta.reasoning_content`
  - `delta.reasoning`
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

- Add optional Responses API mode fallback while preserving current default.
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
- [ ] `README.md` and `AGENT.md` are up to date
