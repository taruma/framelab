# FrameLab Interface Reference

A complete map of every UI element in FrameLab. For step-by-step usage, see [`TUTORIAL.md`](TUTORIAL.md).

---

## Top Section

### Hero Banner

![Hero banner at top of app](https://github.com/user-attachments/assets/59c41544-2b42-4dc5-9ec0-aea49303fcfe)
*Hero banner displaying the app title and branding.*

Displays the app title and branding. Content is loaded from `hero.md` in the project root.

### Notices Bar

![Notices badges below hero](https://github.com/user-attachments/assets/e8e072e7-5b65-4c10-9012-c79aeffa87cc)
*Notices bar showing announcement badges.*

Badges rendered from `config.toml` → `[[notices]]`. Each notice has:
- `text` — the message
- `icon` — emoji or Streamlit icon (e.g., `📰`, `:material/rocket_launch:`)
- `color` — badge color (`blue`, `green`, `orange`, `red`, `violet`, `gray`)
- `enabled` — show/hide toggle

Used for announcements, new model alerts, and tips.

---

## Sidebar

### API Setup (Expander)

![Sidebar API Setup expander](https://github.com/user-attachments/assets/06eb400d-0dee-4596-b7de-e5b9ac1eff83)
*API Setup section in the sidebar showing provider, key, endpoint, and model controls.*

| Element | Description |
|---------|-------------|
| **Provider** | Dropdown to select a provider (OpenAI, Gemini, OpenRouter, Claude, BytePlus, Xiaomi). Populated from `config.toml` → `[providers.*]`. |
| **API Key** | Password field. Paste your key here or leave blank to use `.env` / environment variables. Shows detected source (`sidebar input`, `.env (LLM_API_KEY)`, etc.). |
| **Base URL / Endpoint** | Text input, auto-filled from provider config. Override for custom proxies. |
| **Model** | Dropdown of preset models from provider config. Select or leave as default. |
| **Model Override** | Text input to type a custom model name. Takes precedence over the dropdown if non-empty. |
| **Reasoning Effort** | Dropdown: `none`, `minimal`, `low`, `medium`, `high`. Sent as-is to reasoning-capable models. |

### System Prompt

![Sidebar System Prompt section](https://github.com/user-attachments/assets/dd852a0b-d593-46dd-a3a7-64c3ecc2bb14)
*System Prompt section showing preset dropdown, Load button, and editable text area.*

| Element | Description |
|---------|-------------|
| **System Prompt Preset** | Dropdown listing `.txt` files from `prompts/system/`. Titles come from `.meta.toml` sidecars. |
| **Load** | Button to load the selected preset into the System Prompt text box. Manual edits in the text box are preserved until explicitly loaded. |
| **Description caption** | Shows the preset's `description` from its `.meta.toml` (if available). |
| **System Prompt** | Editable text area (180px height). This is the source of truth for the system prompt sent to the model. |
| **Open large editor** | Button to open a full-width dialog for comfortable editing. Dialog has **Apply** and **Cancel** buttons. |

### Session Request Logging

![Sidebar Session Request Logging section](https://github.com/user-attachments/assets/b0d37561-238c-4962-a525-847812b76640)
*Session Request Logging toggle and download button.*

| Element | Description |
|---------|-------------|
| **Enable request logging (session-only)** | Toggle to record request payloads and responses for the current browser session. |
| **Logged attempts** | Caption showing the count of recorded attempts. |
| **Download Session Logs (.json)** | Button to export all logged attempts as a JSON file. Disabled if no logs exist. |

---

## Main Layout

![Full app layout showing two columns](https://github.com/user-attachments/assets/09b88d3e-ce14-4598-8489-d2050efa7a96)
*Main two-column layout: inputs on the left, outputs on the right.*

The main area is a two-column layout (`[1, 1.2]` ratio). Phase 2 appears only after Phase 1 completes.

---

## Phase 1 — Primary Analysis

### Left Column (Inputs)

![Phase 1 input column](https://github.com/user-attachments/assets/63393a32-e9c7-4dbe-bcf5-c0cc8fbfaeef)
*Phase 1 left column showing media uploader, prompt presets, and Analyze button.*

| Element | Description |
|---------|-------------|
| **Original Reference Media** | File uploader accepting PNG, JPG, JPEG, WEBP, MP4. Supports single or multiple files. Video limit: 30 MB. |
| **Media preview** | Single file: full-width image or video player. Multiple files: compact thumbnail strip + "Manage media tags" button. |
| **Manage media tags** | Button (multiple files only). Opens a dialog with full-size previews and editable tag fields per item. Has **Apply tags** and **Cancel** buttons. |
| **Media tag warnings** | Yellow warning if duplicate tags are detected across uploaded items. |
| **Initial Prompt Preset** | Dropdown listing `.txt` files from `prompts/initial/`. |
| **Load** | Button next to the preset dropdown to load selected preset into the Initial Prompt text box. |
| **Description caption** | Shows the preset's `description` from its `.meta.toml`. |
| **Initial Prompt** | Editable text area (140px height). Your analysis request or context text. |
| **🔎 Request Transparency** | Collapsed expander. Shows metadata (provider, endpoint, model, reasoning effort) and payload chips (system, reference media, prompt/context). |
| **Analyze** | Primary action button. Sends Phase 1 request. Disabled while processing. |

### Right Column (Outputs)

![Phase 1 output column](https://github.com/user-attachments/assets/f723e267-849e-4782-9b15-1ac6d2584af0)
*Phase 1 right column showing Thought Process expander, streamed output, and copy/edit controls.*

| Element | Description |
|---------|-------------|
| **Highlight POS (EN only)** | Checkbox to enable part-of-speech highlighting. Default: off. |
| **POS types to highlight** | Multiselect (Verb, Adjective, Noun). Only active when POS highlighting is checked. |
| **Thought Process** | Expander showing chain-of-thought reasoning streamed from the model (when available). |
| **Output area** | Main streamed response rendered as markdown. |
| **POS note** | Caption showing which POS tags are highlighted (appears only when highlighting is active). |
| **Usage caption** | Token counts: input, output, total. Shows "not returned by this model/provider" if unavailable. Appends "Edited by user" if manually edited. |
| **✏️ Edit** | Button to open a dialog for manually revising the output. Dialog has **Submit changes** and **Cancel**. |
| **Copy Plain Text** | Button to copy output with markdown formatting stripped. |
| **Copy Markdown** | Button to copy the raw markdown output as-is. |
| **Copy status** | Brief "Copied plain text" / "Copied as-is" / "Copy failed" feedback below the buttons. |

---

## Phase 2 — Refinement Loop

![Phase 2 full view](https://github.com/user-attachments/assets/58d5362d-a5b0-4460-818c-2f8db0da1222)
*Phase 2 refinement panel appearing below Phase 1 after initial analysis completes.*

Appears only after Phase 1 completes. Layout mirrors Phase 1.

### Left Column (Inputs)

![Phase 2 input column](https://github.com/user-attachments/assets/b3ea31d6-6363-41d7-8978-9b2625f80467)
*Phase 2 left column showing correction media uploader, refinement notes preset, and Run Refinement button.*

| Element | Description |
|---------|-------------|
| **Correction Media** | File uploader (same formats as Phase 1). Upload generated/incorrect media for comparison. |
| **Media preview** | Same behavior as Phase 1. |
| **Manage media tags** | Same dialog as Phase 1, scoped to Phase 2 media. |
| **Refinement Notes Preset** | Dropdown listing `.txt` files from `prompts/correction/`. |
| **Load** | Button to load selected preset into Refinement Notes. |
| **Description caption** | Shows preset description. |
| **Refinement Notes** | Editable text area (120px height). Instructions for how the model should revise its prior analysis. |
| **🔎 Request Transparency** | Collapsed expander. Shows metadata + payload chips including "previous output" and "correction notes". |
| **Run Refinement** | Action button. Sends Phase 2 request with full conversation context. Disabled while processing. |

### Right Column (Outputs)

| Element | Description |
|---------|-------------|
| Same as Phase 1 output column | POS highlighting, Thought Process, output area, usage, Edit, Copy buttons. All scoped to Phase 2. |

---

## Dialogs

### Edit System Prompt

![Edit System Prompt dialog](https://github.com/user-attachments/assets/81965ed3-7194-4e74-a9c6-4f3c37065bfe)
*Dialog for editing the system prompt in a large text area.*

- **Trigger:** Sidebar → "Open large editor" button
- **Fields:** Large text area pre-filled with current system prompt
- **Buttons:** Apply (saves changes), Cancel (discards)

### Edit Phase 1 Output

![Edit Phase 1 Output dialog](https://github.com/user-attachments/assets/5858191b-8a36-4609-aa55-4ed7b08e3840)
*Dialog for manually revising Phase 1 output markdown.*

- **Trigger:** Phase 1 output → ✏️ Edit button
- **Fields:** Text area pre-filled with current Phase 1 output
- **Buttons:** Submit changes (updates output + conversation context), Cancel
- **Effect:** Sets "Edited by user" flag on usage caption

### Edit Phase 2 Output

- **Trigger:** Phase 2 output → ✏️ Edit button
- **Fields:** Text area pre-filled with current Phase 2 output
- **Buttons:** Submit changes (updates output + conversation context), Cancel
- **Effect:** Sets "Edited by user" flag on usage caption

### Manage Phase 1 Media Tags

![Manage Media Tags dialog](https://github.com/user-attachments/assets/4da0bea6-3ef7-4e4d-9446-ba0ab0a150ef)
*Dialog showing full-size media previews with editable tag fields.*

- **Trigger:** Phase 1 → "Manage media tags" button (multiple files only)
- **Content:** Full-size image/video preview per item, editable tag text input
- **Buttons:** Apply tags (saves tag map), Cancel

### Manage Phase 2 Media Tags

- **Trigger:** Phase 2 → "Manage media tags" button (multiple files only)
- **Content:** Same as Phase 1 dialog, scoped to Phase 2

---

## Processing State

![Processing state with spinner](https://github.com/user-attachments/assets/04b95117-2f12-4b4b-83d7-0c67972b8ead)
*App in processing state showing spinner and locked inputs.*

When a request is in progress:
- **Inputs are locked** — all form fields, buttons, and uploaders are disabled
- **Spinner** appears with "Generating response..." or "Running refinement..."
- **Pending action** prevents duplicate submissions

---

## Error Display

Errors appear at the bottom of the page via `st.error()`. Common messages:
- "Please provide an API key..."
- "Please provide a model name."
- "Uploaded video is too large..."
- "Analyze failed: ..." / "Correction failed: ..."

---

*For step-by-step usage, see [`TUTORIAL.md`](TUTORIAL.md).*