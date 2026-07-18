# FILE: tests/test_ui_state.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for UI state reader — read_ui_state with/without main_window
#   SCOPE: Default state, button state reading
#   DEPENDS: pytest, video2pptx.gui.ui_state
#   LINKS: V-M-UI-STATE-READER, M-UI-STATE-READER
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from video2pptx.gui.ui_state import read_ui_state


class TestUiStateReader:
    def test_default_state(self):
        state = read_ui_state()
        assert state["window_title"] == ""
        assert state["busy"] is False
        assert state["current_operation"] is None
        assert len(state["buttons"]) == 8
        for btn in state["buttons"].values():
            assert btn["visible"] is False
            assert btn["enabled"] is False

    def test_all_button_names_present(self):
        state = read_ui_state()
        expected = {"quick_preview", "detect", "auto_align", "process_notes",
                     "auto", "export_md", "export_pptx", "save"}
        assert set(state["buttons"].keys()) == expected
