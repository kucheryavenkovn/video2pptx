# FILE: tests/test_command_router.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for canonical slide CRUD — resolve_uid, slide_add, slide_delete, slide_move
#   SCOPE: resolve_uid 1-based → uid, slide_add/delete/move success/failure paths
#   DEPENDS: pytest, video2pptx.command_router
#   LINKS: V-M-CANONICAL-COMMANDS
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from video2pptx.command_router import resolve_uid, slide_move, slide_resize


class FakeSlide:
    def __init__(self, uid: str, index: int = 0):
        self.uid = uid
        self.index = index


class FakeProjectModel:
    def __init__(self):
        self.project_data = type(
            "Project",
            (),
            {"slides": [FakeSlide("abc", 1), FakeSlide("def", 2)]},
        )()
        self.calls = []

    def move_slide(self, uid, start, end):
        self.calls.append(("move", uid, start, end))

    def resize_slide(self, uid, end):
        self.calls.append(("resize", uid, end))


class TestResolveUid:
    def test_by_uid_found(self):
        slides = [FakeSlide("abc"), FakeSlide("def")]
        assert resolve_uid(slides, uid="abc") == "abc"

    def test_by_uid_not_found(self):
        slides = [FakeSlide("abc")]
        assert resolve_uid(slides, uid="xyz") is None

    def test_by_index_found(self):
        slides = [FakeSlide("abc", 1), FakeSlide("def", 2)]
        assert resolve_uid(slides, index=1) == "abc"
        assert resolve_uid(slides, index=2) == "def"

    def test_by_index_out_of_range(self):
        slides = [FakeSlide("abc", 1)]
        assert resolve_uid(slides, index=5) is None

    def test_by_index_zero_based(self):
        slides = [FakeSlide("abc", 1)]
        assert resolve_uid(slides, index=0) is None

    def test_no_args(self):
        assert resolve_uid([]) is None


def test_move_routes_public_index_as_stable_uid():
    model = FakeProjectModel()
    result = slide_move(model, start=1.0, end=2.0, index=2)
    assert result == {"success": True, "uid": "def"}
    assert model.calls == [("move", "def", 1.0, 2.0)]


def test_resize_routes_uid_without_zero_based_conversion():
    model = FakeProjectModel()
    result = slide_resize(model, end=3.0, uid="abc")
    assert result == {"success": True, "uid": "abc"}
    assert model.calls == [("resize", "abc", 3.0)]
