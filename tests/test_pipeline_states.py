# FILE: tests/test_pipeline_states.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for ProjectState pipeline flags — new flags, stale downstream marking, skip behavior
#   SCOPE: ProjectState field defaults, mark_stale_downstream, update_project_state
#   DEPENDS: pytest, video2pptx.project_manager
#   LINKS: V-M-PIPELINE-STATES, M-DOMAIN-STATE, M-PIPELINE-STATES
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from video2pptx.project_manager import Project, ProjectState, update_project_state


class TestPipelineStates:
    def test_default_state(self):
        s = ProjectState()
        assert s.preview_done is False
        assert s.detect_done is False
        assert s.align_done is False
        assert s.notes_done is False
        assert s.md_exported is False
        assert s.pptx_exported is False
        assert s.auto_done is False
        assert s.detect_stale is True
        assert s.align_stale is True
        assert s.notes_stale is True
        assert s.md_stale is True
        assert s.pptx_stale is True

    def test_mark_stale_downstream_detect(self):
        s = ProjectState(detect_done=True, align_done=True, notes_done=True, md_exported=True, pptx_exported=True)
        s.mark_stale_downstream("detect")
        assert s.detect_stale is True  # detect itself became stale
        assert s.align_stale is True
        assert s.notes_stale is True
        assert s.md_stale is True
        assert s.pptx_stale is True
        # All downstream done flags cleared
        assert s.align_done is False
        assert s.notes_done is False
        assert s.md_exported is False
        assert s.pptx_exported is False
        assert s.auto_done is False

    def test_mark_stale_downstream_align(self):
        s = ProjectState(
            align_done=True, notes_done=True, md_exported=True, pptx_exported=True,
            align_stale=False, notes_stale=False, md_stale=False, pptx_stale=False,
        )
        s.mark_stale_downstream("align")
        # align_stale unchanged (upstream clears it); notes/md/pptx become stale
        assert s.align_stale is False
        assert s.notes_stale is True
        assert s.md_stale is True
        assert s.pptx_stale is True
        assert s.notes_done is False
        assert s.md_exported is False

    def test_mark_stale_downstream_notes(self):
        s = ProjectState(
            notes_done=True, md_exported=True, pptx_exported=True,
            notes_stale=False, md_stale=False, pptx_stale=False,
        )
        s.mark_stale_downstream("notes")
        assert s.notes_stale is False
        assert s.md_stale is True
        assert s.pptx_stale is True

    def test_mark_stale_unknown_stage(self):
        s = ProjectState()
        s.mark_stale_downstream("nonexistent")
        assert s.detect_stale is True

    def test_update_project_state_sets_new_flags(self, tmp_path):
        proj = Project(name="test", state=ProjectState())
        proj_dir = tmp_path / "testproj"
        proj_dir.mkdir()
        result = update_project_state(proj, preview_done=True, _stage="preview")
        assert result.state.preview_done is True

    def test_update_project_state_stale_on_re_detect(self, tmp_path):
        proj = Project(name="test", state=ProjectState(detect_done=True, align_done=True, notes_done=True))
        proj_dir = tmp_path / "testproj2"
        proj_dir.mkdir()
        update_project_state(proj, detect_done=True, _stage="detect")
        assert proj.state.detect_done is True
        assert proj.state.notes_done is False
