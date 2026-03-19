# Testing Framework

This document describes the test architecture for FrameLab.

Goal: keep tests **simple, fast, and useful** for regression safety when adding/changing features.

## Principles

1. **Offline by default**
   - Core test suite must not require real provider/API access.
   - CI runs only deterministic offline tests.
2. **Contract-focused**
   - Verify message shape, parser behavior, fallback logic, and state defaults.
   - Avoid overfitting to exact LLM wording.
3. **Minimal complexity**
   - Small test files mapped to app modules.
   - Limited helper abstractions.

## Test layers (Balanced strategy)

### Layer A — Unit/Contract Tests (offline)

- `tests/test_conversation.py`
  - `to_data_url`
  - `make_user_message`
  - `messages_to_responses_input`
- `tests/test_llm_streaming_parsers.py`
  - usage normalization
  - chat/responses delta extraction
  - schema mismatch detection helper
- `tests/test_llm_streaming_fallback.py`
  - Responses success path
  - fallback to Chat Completions
  - auto-disable behavior for known provider schema mismatch
- `tests/test_run_helpers.py`
  - helper contracts (`truncate_words`, `validate_media_size`, markdown plain-text conversion, transparency preview builders)
- `tests/test_app_state.py`
  - session key defaults and non-overwrite behavior

### Layer B — UI smoke tests (offline, minimal)

- `tests/test_ui_smoke.py` uses `streamlit.testing.v1.AppTest` to validate critical app flow:
  - Phase 1 visible by default
  - Phase 2 hidden until `phase1_done`
  - basic required-input error path for Analyze

### Layer C — Optional live LLM smoke (opt-in)

- `tests/test_live_llm_smoke.py` is marked `@pytest.mark.live`
- Not part of default CI/offline run.
- Purpose: quick sanity check against a real provider with minimal assertions.
- Requires explicit opt-in env flag: `FRAMELAB_ENABLE_LIVE_TESTS=1`
- Auto-skips in CI/cloud environments.
- Pytest auto-loads local `.env` via `tests/conftest.py`.

## Provider strategy for live smoke tests

Live smoke provider settings resolve in this order:

1. `TEST_PROVIDER` (optional explicit override)
2. otherwise `config.toml` → `defaults.provider`

Then model/base URL are resolved from env override first, then selected provider config:

- `TEST_MODEL` → provider `default_model`
- `TEST_BASE_URL` → provider `base_url`

API key resolution for live smoke:

1. `TEST_API_KEY`
2. selected provider env key from `config.toml` (e.g. `OPENROUTER_API_KEY`)
3. `LLM_API_KEY`

If required values are missing, live smoke is skipped.

## Running tests

Default offline suite (recommended for development and CI):

```bash
uv run pytest
```

Run offline explicitly (equivalent to default):

```bash
uv run pytest -q -m "not live"
```

Run only live smoke (explicit local opt-in):

```bash
uv run pytest --live
```

Set `FRAMELAB_ENABLE_LIVE_TESTS=1` in local `.env` (copied from `.env.example`) to enable live execution.

## Contribution checklist for changes

When changing behavior, keep regression safety strong:

1. New feature → add/update at least one test.
2. Bug fix → add regression test that covers the bug scenario.
3. Any message/fallback/state contract change → update corresponding contract tests.

## CI policy

CI runs only offline suite:

- `uv run pytest`

This keeps PR checks fast, deterministic, and provider-independent.
