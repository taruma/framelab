from __future__ import annotations

from streamlit.testing.v1 import AppTest

from app_state import PHASE1_DONE


def test_phase1_sections_render_by_default() -> None:
    app = AppTest.from_file("run.py")
    app.run(timeout=20)

    subheaders = [s.value for s in app.subheader]
    assert "Phase 1 · Initial Analysis" in subheaders
    assert "Phase 1 Output" in subheaders
    assert "Phase 2 · Correction Flow" not in subheaders


def test_phase2_sections_visible_after_phase1_done_state() -> None:
    app = AppTest.from_file("run.py")
    app.session_state[PHASE1_DONE] = True
    app.run(timeout=20)

    subheaders = [s.value for s in app.subheader]
    assert "Phase 2 · Correction Flow" in subheaders
    assert "Updated Analysis" in subheaders


def test_analyze_without_media_shows_error() -> None:
    app = AppTest.from_file("run.py")
    app.run(timeout=20)

    # Button order at first render: Load, Analyze
    app.button[1].click().run(timeout=20)

    errors = [e.value for e in app.error]
    expected_error_fragments = [
        "Please upload an original reference media file.",
        "Please provide an API key",
        "Please provide a model name.",
    ]
    assert any(
        any(fragment in err for fragment in expected_error_fragments)
        for err in errors
    )
