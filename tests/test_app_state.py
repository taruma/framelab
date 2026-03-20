from __future__ import annotations

import app_state


def test_init_state_sets_expected_defaults(monkeypatch) -> None:
    fake_session: dict = {}
    monkeypatch.setattr(app_state.st, "session_state", fake_session)

    app_state.init_state()

    assert fake_session[app_state.PHASE1_DONE] is False
    assert fake_session[app_state.CONVERSATION_MESSAGES] == []
    assert fake_session[app_state.PHASE1_OUTPUT] == ""
    assert fake_session[app_state.PHASE1_REASONING] == ""
    assert fake_session[app_state.PHASE1_USAGE] is None
    assert fake_session[app_state.PHASE2_OUTPUT] == ""
    assert fake_session[app_state.PHASE2_REASONING] == ""
    assert fake_session[app_state.PHASE2_USAGE] is None
    assert fake_session[app_state.PREFER_RESPONSES_API] is True
    assert fake_session[app_state.IS_PROCESSING] is False
    assert fake_session[app_state.PENDING_ACTION] is None
    assert fake_session[app_state.LAST_ERROR] == ""
    assert fake_session[app_state.REQUEST_LOGGING_ENABLED] is False
    assert fake_session[app_state.REQUEST_LOGS] == []


def test_init_state_does_not_override_existing_values(monkeypatch) -> None:
    fake_session = {
        app_state.PHASE1_DONE: True,
        app_state.PHASE1_OUTPUT: "existing",
    }
    monkeypatch.setattr(app_state.st, "session_state", fake_session)

    app_state.init_state()

    assert fake_session[app_state.PHASE1_DONE] is True
    assert fake_session[app_state.PHASE1_OUTPUT] == "existing"
