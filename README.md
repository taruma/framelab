# ✨ FrameLab

[![Latest Release](https://img.shields.io/github/v/release/taruma/framelab?style=flat-square&label=version)](https://github.com/taruma/framelab/releases/latest)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square)

**FrameLab** is a lightweight multimodal AI app for cinematic analysis.
Bring text, images, or video, get streamed insights, then refine in a second pass.

🌐 **Use it on the web:** [framelab.streamlit.app](https://framelab.streamlit.app)

> [!TIP]
> 🔐 **Keep your API key secure:** FrameLab does not provide API credits. To run analyses (local or web), bring your own compatible API key in the sidebar, never share keys/screenshots publicly, and monitor token usage/cost on your provider account.

> [!IMPORTANT]
> **Vibecoding Disclaimer**: This project is built using an AI-assisted "vibecoding" approach (rapid iteration with human supervision). It is experimental, may contain bugs, and could break unintentionally during updates. Use it as a creative tool, but keep your expectations grounded.

---

https://github.com/user-attachments/assets/5dd8a80b-d9d8-4150-a4a5-7bdca75738cc

*Cinematic analysis in action.*

---

## Why people use FrameLab

- **Text-only or multimodal** workflow (images/videos are optional)
- **Two-phase flow**: Primary Analysis → Refinement Loop
- **Live streaming output** with a Thought Process panel when available
- **Prompt and output editing** directly in the UI
- **Copy actions** for both plain text and markdown
- **Provider flexibility** via OpenAI-compatible endpoints

---

## Quick Start

FrameLab uses [`uv`](https://docs.astral.sh/uv/) for dependency + runtime management.

```bash
git clone https://github.com/taruma/framelab.git
cd framelab
uv sync
uv run run.py
```

Optional (recommended):

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Then add your key to `.env` (for example `LLM_API_KEY=...`) or paste it in the sidebar at runtime.

---

## How it works

1. **Configure in the sidebar**
   - Choose provider/model and set API key/endpoint as needed.
   - Load a prompt preset, then edit it freely.

2. **Phase 1 — Primary Analysis**
   - Add optional reference media + prompt/context, then click **Analyze**.

3. **Phase 2 — Refinement Loop**
   - Add refinement notes and optional follow-up media to iterate on the result.

### Feature flags

- **Since v2.1.0:** POS highlighting controls are feature-gated and hidden by default.
- To enable locally, set this in `config.toml`:

```toml
[features]
pos_highlighting = true
```

---

## Prompt presets

You can customize behavior without editing app code:

- `prompts/system/`
- `prompts/initial/`
- `prompts/correction/`

Optional: add `name.meta.toml` sidecars (`title`, `description`, `order`) for cleaner UI labels.

---

## Documentation

- [`docs/INTERFACE.md`](docs/INTERFACE.md) — complete map of every UI element
- [`docs/TUTORIAL.md`](docs/TUTORIAL.md) — step-by-step walkthrough from first launch to advanced workflows
- [`docs/REFERENCE.md`](docs/REFERENCE.md) — technical/runtime details, advanced config, API behavior, contracts, troubleshooting
- [`docs/TESTING.md`](docs/TESTING.md) — testing strategy and commands
- [`CHANGELOG.md`](CHANGELOG.md) — release history and detailed changes
- [`AGENTS.md`](AGENTS.md) — AI contributor/agent rules and architecture constraints

---

## License

Distributed under the MIT License. See `LICENSE` for details.

---

Built with ❤️ by **Taruma Sakti** · Vibecoding with Cline + GPT-5.3-Codex




























