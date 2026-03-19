from __future__ import annotations

import os
import tomllib
from pathlib import Path

import pytest
from openai import OpenAI

from llm_streaming import stream_response


class _Placeholder:
    def __init__(self) -> None:
        self.values: list[str] = []

    def markdown(self, value: str) -> None:
        self.values.append(value)

    def caption(self, value: str) -> None:
        self.values.append(value)

    def empty(self) -> None:
        return None


def _load_config() -> dict:
    config_path = Path("config.toml")
    if not config_path.exists():
        return {}
    with config_path.open("rb") as f:
        return tomllib.load(f)


def _resolve_live_provider_settings() -> tuple[str, str, str]:
    cfg = _load_config()
    providers = cfg.get("providers", {}) if isinstance(cfg, dict) else {}
    defaults = cfg.get("defaults", {}) if isinstance(cfg, dict) else {}

    provider_id = os.environ.get("TEST_PROVIDER", "").strip() or str(defaults.get("provider", "")).strip()
    provider = providers.get(provider_id, {}) if isinstance(providers, dict) else {}

    base_url = os.environ.get("TEST_BASE_URL", "").strip() or str(provider.get("base_url", "")).strip()
    model = os.environ.get("TEST_MODEL", "").strip() or str(provider.get("default_model", "")).strip()
    env_key_name = str(provider.get("env_key", "")).strip()

    api_key = os.environ.get("TEST_API_KEY", "").strip()
    if not api_key and env_key_name:
        api_key = os.environ.get(env_key_name, "").strip()
    if not api_key:
        api_key = os.environ.get("LLM_API_KEY", "").strip()

    return base_url, model, api_key


def _is_ci_environment() -> bool:
    ci_flags = [
        os.environ.get("CI", ""),
        os.environ.get("GITHUB_ACTIONS", ""),
        os.environ.get("STREAMLIT_CLOUD", ""),
    ]
    return any(str(flag).strip().lower() in {"1", "true", "yes"} for flag in ci_flags)


@pytest.mark.live
def test_live_smoke_stream_response_minimal_contract() -> None:
    if _is_ci_environment():
        pytest.skip("Live smoke test is disabled in CI/cloud environments by policy.")

    if os.environ.get("FRAMELAB_ENABLE_LIVE_TESTS", "").strip() != "1":
        pytest.skip(
            "Live smoke test requires explicit opt-in. Set FRAMELAB_ENABLE_LIVE_TESTS=1 to enable."
        )

    base_url, model, api_key = _resolve_live_provider_settings()
    if not api_key or not model:
        pytest.skip(
            "Live smoke test skipped. Provide TEST_API_KEY (or provider env key/LLM_API_KEY) and TEST_MODEL "
            "or set a valid default provider/model in config.toml."
        )

    provider_id = os.environ.get("TEST_PROVIDER", "").strip() or "config.default"
    print(
        "[LIVE TEST] REAL API CALL ENABLED "
        f"provider={provider_id} base_url={base_url or '(provider default)'} model={model}",
        flush=True,
    )

    client = OpenAI(api_key=api_key, base_url=base_url or None)
    thought_placeholder = _Placeholder()
    answer_placeholder = _Placeholder()

    answer, thought, usage, prefer_responses_api = stream_response(
        client=client,
        model=model,
        messages=[{"role": "user", "content": "Reply briefly with a smoke-test acknowledgment."}],
        thought_placeholder=thought_placeholder,
        answer_placeholder=answer_placeholder,
        prefer_responses_api=True,
    )

    assert isinstance(answer, str)
    assert answer.strip() != ""
    assert isinstance(thought, str)
    assert usage is None or isinstance(usage, dict)
    assert isinstance(prefer_responses_api, bool)
