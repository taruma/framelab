# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
