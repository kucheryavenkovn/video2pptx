# FILE: tests/test_debug_action.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit tests for @mcp_action decorator + ActionRegistry
#   SCOPE: Decorator metadata, registry scan, tools list, call dispatch, type schema conversion
#   DEPENDS: video2pptx.debug.action_registry, pytest
#   LINKS: V-M-DEBUG-ACTION
# END_MODULE_CONTRACT

from __future__ import annotations

import pytest

from video2pptx.debug.action_registry import ActionRegistry, mcp_action


class FakeActions:
    """Fake class with @mcp_action decorated methods for testing."""

    @mcp_action(name="do_thing", desc="Does a thing")
    def _on_do_thing(self) -> None:
        self._called = True

    @mcp_action(name="seek", desc="Seek to position")
    def _on_seek(self, ts: float) -> None:
        self._seek_ts = ts

    def _not_an_action(self) -> None:
        """This should not be picked up."""
        pass


class TestMcpAction:
    def test_metadata_attached(self) -> None:
        assert hasattr(FakeActions._on_do_thing, "_mcp_meta")
        meta = FakeActions._on_do_thing._mcp_meta
        assert meta["name"] == "do_thing"
        assert meta["desc"] == "Does a thing"

    def test_auto_name_from_method(self) -> None:
        @mcp_action()
        def _my_action(self) -> None:
            pass

        assert _my_action._mcp_meta["name"] == "my_action"


class TestActionRegistry:
    def test_scan_finds_actions(self) -> None:
        fake = FakeActions()
        registry = ActionRegistry(fake)
        assert registry.has("do_thing")
        assert registry.has("seek")
        assert not registry.has("_not_an_action")

    def test_tools_list(self) -> None:
        fake = FakeActions()
        registry = ActionRegistry(fake)
        tools = registry.tools()
        names = {t["name"] for t in tools}
        assert "do_thing" in names
        assert "seek" in names
        assert len(tools) == 2

    def test_input_schema(self) -> None:
        fake = FakeActions()
        registry = ActionRegistry(fake)
        schema = registry._actions["seek"]["schema"]
        assert schema["type"] == "object"
        assert "ts" in schema["properties"]
        assert schema["properties"]["ts"]["type"] == "number"

    def test_call_dispatches(self) -> None:
        fake = FakeActions()
        registry = ActionRegistry(fake)
        registry.call("do_thing")
        assert fake._called is True

    def test_call_with_args(self) -> None:
        fake = FakeActions()
        registry = ActionRegistry(fake)
        registry.call("seek", {"ts": 42.0})
        assert fake._seek_ts == 42.0

    def test_call_unknown(self) -> None:
        registry = ActionRegistry(FakeActions())
        with pytest.raises(KeyError):
            registry.call("nonexistent")

    def test_scan_multiple_instances(self) -> None:
        registry = ActionRegistry()
        a = FakeActions()
        b = FakeActions()
        registry.scan(a)
        registry.scan(b)
        assert registry.has("do_thing")

    def test_actions_not_change_between_scans(self) -> None:
        fake = FakeActions()
        registry = ActionRegistry()
        assert not registry.has("do_thing")
        registry.scan(fake)
        assert registry.has("do_thing")
