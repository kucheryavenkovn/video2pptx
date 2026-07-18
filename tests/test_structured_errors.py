# FILE: tests/test_structured_errors.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for OperationError — typed error envelope with trace_id, to_dict, from_exception
#   SCOPE: OperationError construction, to_dict, from_exception
#   DEPENDS: pytest, video2pptx.debug.errors
#   LINKS: V-M-STRUCTURED-ERRORS, M-STRUCTURED-ERRORS
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from video2pptx.debug.errors import OperationError


class TestOperationError:
    def test_construction(self):
        err = OperationError(type="TestError", message="something went wrong", stage="detect")
        assert err.type == "TestError"
        assert err.message == "something went wrong"
        assert err.stage == "detect"
        assert err.recoverable is False
        assert err.trace_id == ""

    def test_to_dict_excludes_empty(self):
        err = OperationError(type="TestError", message="fail")
        d = err.to_dict()
        assert d["type"] == "TestError"
        assert d["message"] == "fail"
        assert "stage" not in d
        assert "recoverable" not in d
        assert "trace_id" not in d
        assert "details" not in d

    def test_to_dict_includes_optionals(self):
        err = OperationError(
            type="VideoDecodeError",
            message="cannot decode",
            stage="detect",
            recoverable=True,
            trace_id="abc123",
            details={"path": "test.mp4"},
        )
        d = err.to_dict()
        assert d["recoverable"] is True
        assert d["trace_id"] == "abc123"
        assert d["details"]["path"] == "test.mp4"

    def test_from_exception_captures_traceback(self):
        try:
            raise ValueError("bad value")
        except ValueError as exc:
            err = OperationError.from_exception(exc, stage="align", trace_id="def456")
        assert err.type == "ValueError"
        assert err.stage == "align"
        assert err.trace_id == "def456"
        assert "traceback" in err.details
        assert "bad value" in err.message
