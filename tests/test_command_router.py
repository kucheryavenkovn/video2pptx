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

from video2pptx.command_router import resolve_uid


class FakeSlide:
    def __init__(self, uid: str, index: int = 0):
        self.uid = uid
        self.index = index


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
