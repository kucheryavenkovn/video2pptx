# FILE: tests/test_confirm_policy.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for confirm policy — destructive ops require confirm=true
#   SCOPE: require_confirm, is_destructive, ConfirmRequiredError
#   DEPENDS: pytest, video2pptx.debug.confirm
#   LINKS: V-M-CONFIRM-POLICY, M-CONFIRM-POLICY
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

import pytest

from video2pptx.debug.confirm import (
    ConfirmRequiredError,
    is_destructive,
    require_confirm,
)


class TestConfirmPolicy:
    def test_is_destructive_known(self):
        assert is_destructive("detect") is True
        assert is_destructive("slide_delete") is True
        assert is_destructive("app_shutdown") is True

    def test_is_destructive_non(self):
        assert is_destructive("get_project") is False
        assert is_destructive("project_create") is False

    def test_require_confirm_raises_on_missing(self):
        with pytest.raises(ConfirmRequiredError, match="detect"):
            require_confirm("detect", {})

    def test_require_confirm_raises_on_false(self):
        with pytest.raises(ConfirmRequiredError):
            require_confirm("detect", {"confirm": False})

    def test_require_confirm_accepts_true(self):
        require_confirm("detect", {"confirm": True})

    def test_require_confirm_passes_non_destructive(self):
        require_confirm("get_project", {})

    def test_require_confirm_none_args(self):
        with pytest.raises(ConfirmRequiredError):
            require_confirm("detect", None)
