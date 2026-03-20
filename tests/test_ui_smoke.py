from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from app_state import PHASE1_DONE


def _find_button_by_key(app: AppTest, key: str):
    return next((button for button in app.button if button.key == key), None)


def _find_system_selectbox(app: AppTest):
    system_filenames = {p.name for p in Path("prompts/system").glob("*.txt")}
    for selectbox in app.selectbox:
        value = str(getattr(selectbox, "value", "")).strip()
        if value in system_filenames:
            return selectbox
    return None


def _find_textarea_by_key(app: AppTest, key: str):
    return next((text_area for text_area in app.text_area if text_area.key == key), None)


def test_phase1_sections_render_by_default() -> None:
    app = AppTest.from_file("run.py")
    app.run(timeout=20)

    subheaders = [s.value for s in app.subheader]
    assert ":material/photo_camera: Phase 1 · Primary Analysis" in subheaders
    assert ":material/description: Phase 1 Output" in subheaders
    assert ":material/sync_alt: Phase 2 · Refinement Loop" not in subheaders


def test_phase2_sections_visible_after_phase1_done_state() -> None:
    app = AppTest.from_file("run.py")
    app.session_state[PHASE1_DONE] = True
    app.run(timeout=20)

    subheaders = [s.value for s in app.subheader]
    assert ":material/sync_alt: Phase 2 · Refinement Loop" in subheaders
    assert ":material/auto_awesome: Refined Analysis" in subheaders


def test_analyze_without_media_does_not_require_upload() -> None:
    app = AppTest.from_file("run.py")
    app.run(timeout=20)

    analyze_button = next(button for button in app.button if getattr(button, "label", "") == "Analyze")
    analyze_button.click().run(timeout=20)

    errors = [e.value for e in app.error]
    assert all("Please upload an original reference media file." not in err for err in errors)


def test_system_prompt_textbox_prefilled_from_default_system_preset() -> None:
    app = AppTest.from_file("run.py")
    app.run(timeout=20)

    system_prompt_text = _find_textarea_by_key(app, "system_prompt_text")
    assert system_prompt_text is not None
    assert system_prompt_text.value.strip().startswith(
        "You are a cinematography and film-analysis assistant"
    )


def test_system_prompt_load_button_applies_selected_preset() -> None:
    app = AppTest.from_file("run.py")
    app.run(timeout=20)

    system_selectbox = _find_system_selectbox(app)
    assert system_selectbox is not None

    system_selectbox.set_value("11_shotlist_script.txt").run(timeout=20)

    load_system_button = _find_button_by_key(app, "load_system_preset")
    assert load_system_button is not None
    load_system_button.click().run(timeout=20)

    system_prompt_text = _find_textarea_by_key(app, "system_prompt_text")
    assert system_prompt_text is not None

    expected_start = (
        Path("prompts/system/11_shotlist_script.txt")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()[0]
    )
    assert system_prompt_text.value.strip().startswith(expected_start)


def test_system_prompt_large_editor_button_seeds_dialog_text_from_sidebar_text() -> None:
    app = AppTest.from_file("run.py")
    app.run(timeout=20)

    system_prompt_text = _find_textarea_by_key(app, "system_prompt_text")
    assert system_prompt_text is not None
    original_value = system_prompt_text.value

    open_large_editor = _find_button_by_key(app, "open_system_prompt_dialog")
    assert open_large_editor is not None

    open_large_editor.click().run(timeout=20)

    assert "system_prompt_edit_text" in app.session_state
    assert app.session_state["system_prompt_edit_text"] == original_value
