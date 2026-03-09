# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2026-03-09

### Changed

- Made Phase 1 and Phase 2 prompt fields editable in the UI so users can tune instructions per run without leaving the workflow.
- Cleaned up request transparency preview presentation for a clearer, more compact phase action experience.

## [1.1.0] - 2026-03-09

### Added

- Provider presets via `config.toml` for endpoint/model selection (e.g., BytePlus/OpenAI/Gemini/OpenRouter)
- Unified API key env fallback flow with `LLM_API_KEY` plus provider-specific key compatibility
- Hero landing section (`hero.md`) with FrameLab branding and two-phase workflow guide
- API Setup section wrapped in an expander for cleaner sidebar/UI layout
- Per-phase Request Transparency preview panel showing provider, endpoint, model, reasoning setting, and compact payload preview
- UI processing state controls to lock inputs/buttons during active analysis and prevent duplicate submissions
- Hero badges (latest release, MIT license, Python 3.11+) and creator credit line

### Changed

- Request transparency previews are now rendered inline with each phase action panel for clearer workflow alignment
- Setup/configuration docs now reflect provider preset workflow and unified env-key handling
- Added `requirements.txt` for pip-based installs and set Poetry package mode to dependency-management-only (`package-mode = false`)

### Fixed

- Improved phase layout consistency by removing placeholder-based transparency rendering and placing action buttons after each inline preview

## [1.0.0] - 2026-03-08

### Added

- Initial release of FrameLab, a lightweight multimodal AI web app for cinematic image analysis
- Minimal dependencies: only `streamlit` and `openai`
- OpenAI-compatible endpoint support via configurable Base URL
- Hybrid configuration fallback: sidebar input → .env → config.py defaults
- API key support with sidebar override priority
- Externalized default system prompt via `system_prompt.txt`
- Uploaded image previews for Phase 1 and Phase 2
- Real-time streaming output in UI
- Thought/reasoning stream shown in expandable section
- One-click copy buttons for Phase 1 and Phase 2 results (plain text)
- Token usage summary (input/output/total) when provided by endpoint
- Responses API support with automatic Chat Completions fallback
- Transport path display (Responses API or Chat Completions fallback)
- Auto-disable Responses API when provider reports schema mismatch
- Two-phase workflow:
  - Phase 1: Initial image analysis
  - Phase 2: Correction loop with new image + notes
- Session-based conversation memory
- Reasoning effort configuration (none/minimal/low/medium/high)
- Error handling with underlying exception messages for debugging
