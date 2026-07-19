# FILE: tests/gui/test_timeline_interactions.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Phase 21 Wave 2 — SlideBlockItem click/hover/move/resize deferral and no virtual monkeypatches
#   ROLE: TEST
#   LINKS: M-GUI-TIMELINE3, V-M-GUI-TIMELINE3, Phase-21
# END_MODULE_CONTRACT

from __future__ import annotations

from types import MethodType

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsScene,
    QGraphicsSceneHoverEvent,
    QGraphicsSceneMouseEvent,
    QGraphicsView,
)

from video2pptx.gui.timeline3.items import SlideBlockItem
from video2pptx.gui.timeline3.view import TimelineView
from video2pptx.models import SlideSegment

pytestmark = pytest.mark.usefixtures("qapp")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def _process(app: QApplication, rounds: int = 8) -> None:
    for _ in range(rounds):
        app.processEvents()


def _make_item(
    *,
    x: float = 0.0,
    y: float = 0.0,
    w: float = 100.0,
    h: float = 24.0,
    index: int = 0,
    start: float = 0.0,
    end: float = 2.0,
    on_moved=None,
    on_resized=None,
    on_clicked=None,
) -> tuple[QGraphicsScene, QGraphicsView, SlideBlockItem]:
    scene = QGraphicsScene()
    view = QGraphicsView(scene)
    view._px_per_sec = 50.0  # type: ignore[attr-defined]
    item = SlideBlockItem(
        x,
        y,
        w,
        h,
        index,
        start,
        end,
        image_path="slides/slide_001.png",
        on_moved=on_moved,
        on_resized=on_resized,
        on_clicked=on_clicked,
    )
    scene.addItem(item)
    return scene, view, item


def _scene_mouse(
    *,
    typ: QEvent.Type,
    item_pos: QPointF,
    scene_pos: QPointF,
    button: Qt.MouseButton = Qt.MouseButton.LeftButton,
    buttons: Qt.MouseButton = Qt.MouseButton.LeftButton,
    modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
) -> QGraphicsSceneMouseEvent:
    ev = QGraphicsSceneMouseEvent(typ)
    ev.setPos(item_pos)
    ev.setScenePos(scene_pos)
    ev.setScreenPos(scene_pos.toPoint())
    ev.setButton(button)
    ev.setButtons(buttons)
    ev.setModifiers(modifiers)
    return ev


def test_slide_click_does_not_raise(qapp):
    clicks: list[tuple[str, int]] = []
    scene, view, item = _make_item(on_clicked=lambda path, idx: clicks.append((path, idx)))
    ev = _scene_mouse(
        typ=QEvent.Type.GraphicsSceneMousePress,
        item_pos=QPointF(50, 12),
        scene_pos=QPointF(50, 12),
    )
    item.mousePressEvent(ev)
    _process(qapp)
    assert clicks == [("slides/slide_001.png", 0)]


def test_slide_hover_does_not_raise(qapp):
    scene, view, item = _make_item()
    hover = QGraphicsSceneHoverEvent(QEvent.Type.GraphicsSceneHoverMove)
    hover.setPos(QPointF(50, 12))
    hover.setScenePos(QPointF(50, 12))
    item.hoverMoveEvent(hover)
    _process(qapp)


def test_slide_move_commit_is_deferred(qapp):
    calls: list[tuple[int, float, float]] = []
    call_depth: list[str] = []

    def on_moved(idx: int, s: float, e: float) -> None:
        call_depth.append("callback")
        calls.append((idx, s, e))

    scene, view, item = _make_item(on_moved=on_moved, start=0.0, end=2.0, w=100.0)
    press = _scene_mouse(
        typ=QEvent.Type.GraphicsSceneMousePress,
        item_pos=QPointF(50, 12),
        scene_pos=QPointF(50, 12),
        modifiers=Qt.KeyboardModifier.AltModifier,
    )
    item.mousePressEvent(press)
    item.setPos(25.0, 0.0)  # +0.5s at 50 px/sec
    call_depth.append("before_release")
    release = _scene_mouse(
        typ=QEvent.Type.GraphicsSceneMouseRelease,
        item_pos=QPointF(50, 12),
        scene_pos=QPointF(75, 12),
        buttons=Qt.MouseButton.NoButton,
        modifiers=Qt.KeyboardModifier.AltModifier,
    )
    item.mouseReleaseEvent(release)
    call_depth.append("after_release")
    # Callback must NOT have run yet (deferred to next event-loop tick)
    assert calls == []
    assert call_depth == ["before_release", "after_release"]
    _process(qapp)
    assert len(calls) == 1
    idx, new_start, new_end = calls[0]
    assert idx == 0
    assert new_start == pytest.approx(0.5, abs=0.05)
    assert new_end > new_start


def test_slide_resize_commit_is_deferred(qapp):
    calls: list[tuple[int, float, float]] = []

    def on_resized(idx: int, s: float, e: float) -> None:
        calls.append((idx, s, e))

    scene, view, item = _make_item(on_resized=on_resized, start=0.0, end=2.0, w=100.0, x=0.0)
    press = _scene_mouse(
        typ=QEvent.Type.GraphicsSceneMousePress,
        item_pos=QPointF(98, 12),
        scene_pos=QPointF(98, 12),
    )
    item.mousePressEvent(press)
    assert item._drag_mode == "resize_right"
    move = _scene_mouse(
        typ=QEvent.Type.GraphicsSceneMouseMove,
        item_pos=QPointF(120, 12),
        scene_pos=QPointF(120, 12),
        button=Qt.MouseButton.NoButton,
        buttons=Qt.MouseButton.LeftButton,
    )
    item.mouseMoveEvent(move)
    release = _scene_mouse(
        typ=QEvent.Type.GraphicsSceneMouseRelease,
        item_pos=QPointF(120, 12),
        scene_pos=QPointF(120, 12),
        buttons=Qt.MouseButton.NoButton,
    )
    item.mouseReleaseEvent(release)
    assert calls == []
    _process(qapp)
    assert len(calls) == 1
    idx, new_start, new_end = calls[0]
    assert idx == 0
    assert new_end > 2.0


def test_scene_rebuild_after_move_does_not_access_deleted_item(qapp):
    """Callback may clear the scene; deferred path must not touch deleted C++ item."""
    scene, view, item = _make_item(start=0.0, end=2.0, w=100.0)
    rebuilt: list[int] = []

    def on_moved(idx: int, s: float, e: float) -> None:
        rebuilt.append(1)
        scene.clear()

    item._on_moved = on_moved
    press = _scene_mouse(
        typ=QEvent.Type.GraphicsSceneMousePress,
        item_pos=QPointF(50, 12),
        scene_pos=QPointF(50, 12),
        modifiers=Qt.KeyboardModifier.AltModifier,
    )
    item.mousePressEvent(press)
    item.setPos(30.0, 0.0)
    release = _scene_mouse(
        typ=QEvent.Type.GraphicsSceneMouseRelease,
        item_pos=QPointF(50, 12),
        scene_pos=QPointF(80, 12),
        buttons=Qt.MouseButton.NoButton,
        modifiers=Qt.KeyboardModifier.AltModifier,
    )
    item.mouseReleaseEvent(release)
    _process(qapp)
    assert rebuilt == [1]


def test_no_instance_virtual_method_monkeypatch(qapp):
    """Qt virtuals must remain class methods, not instance-bound monkeypatches."""
    scene, view, item = _make_item()
    for name in (
        "hoverMoveEvent",
        "mousePressEvent",
        "mouseReleaseEvent",
        "mouseMoveEvent",
    ):
        attr = getattr(item, name)
        assert isinstance(attr, MethodType), f"{name} is not a bound method"
        assert attr.__func__ is getattr(SlideBlockItem, name), f"{name} was monkeypatched on instance"
        assert name not in item.__dict__, f"{name} assigned on instance __dict__"


def test_edits_disabled_blocks_move_and_resize(qapp):
    moves: list = []
    scene, view, item = _make_item(on_moved=lambda *a: moves.append(a))
    item.set_edits_enabled(False)
    press = _scene_mouse(
        typ=QEvent.Type.GraphicsSceneMousePress,
        item_pos=QPointF(50, 12),
        scene_pos=QPointF(50, 12),
        modifiers=Qt.KeyboardModifier.AltModifier,
    )
    item.mousePressEvent(press)
    assert item._drag_mode is None
    assert moves == []


def test_timeline_view_set_edits_enabled_propagates(qapp):
    tv = TimelineView()
    slides = [
        SlideSegment(
            index=1,
            start=0.0,
            end=2.0,
            duration=2.0,
            representative_timestamp=1.0,
            image="slides/a.png",
        )
    ]
    tv.set_data(slides, markers=[], duration=10.0)
    assert tv.edits_enabled() is True
    assert all(i.edits_enabled() for i in tv._slide_items)
    tv.set_edits_enabled(False)
    assert tv.edits_enabled() is False
    assert all(not i.edits_enabled() for i in tv._slide_items)
