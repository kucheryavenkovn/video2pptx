# FILE: src/video2pptx/gui/roi_selector.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Visual ROI selector dialog — user draws rectangles over video frame to define ignore ROIs
#   SCOPE: Modal QDialog with QLabel + QRubberBand, emits list of [x1,y1,x2,y2] rectangles
#   DEPENDS: PySide6
#   LINKS: M-GUI-ROI-SELECTOR
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   RoiSelectorDialog - modal dialog for selecting ignore regions on a video frame
#   RectItem - helper data class for a single ROI rectangle
# END_MODULE_MAP

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from loguru import logger
from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRubberBand,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


@dataclass
class RectItem:
    x1: int
    y1: int
    x2: int
    y2: int

    def to_csv(self) -> str:
        return f"{self.x1},{self.y1},{self.x2},{self.y2}"

    def normalized(self) -> RectItem:
        x1, x2 = (self.x1, self.x2) if self.x1 <= self.x2 else (self.x2, self.x1)
        y1, y2 = (self.y1, self.y2) if self.y1 <= self.y2 else (self.y2, self.y1)
        return RectItem(x1, y1, x2, y2)

    def to_tuple(self) -> tuple[int, int, int, int]:
        n = self.normalized()
        return (n.x1, n.y1, n.x2, n.y2)


class RoiSelectorDialog(QDialog):
    # START_CONTRACT: RoiSelectorDialog
    #   PURPOSE: QDialog with video frame preview, rubber-band selection, and ROI list
    #   INPUTS: { frame_pixmap: QPixmap }
    #   OUTPUTS: Signal: rois_selected(list[tuple[int,int,int,int]]) on accept
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-ROI-SELECTOR
    # END_CONTRACT: RoiSelectorDialog

    rois_selected = Signal(list)

    _PEN_COLOR: ClassVar[str] = "#00FF00"

    def __init__(self, frame_pixmap: QPixmap, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._frame_pixmap = frame_pixmap
        self._rects: list[RectItem] = []
        self._origin: QRect | None = None
        self._rubber_band: QRubberBand | None = None

        self.setWindowTitle("Select Ignore ROIs")
        self.setMinimumSize(800, 600)
        self.setModal(True)
        self._setup_ui()

    # START_BLOCK_SETUP_UI
    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)

        # Left: scrollable image area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self._image_label = QLabel()
        self._image_label.setPixmap(self._frame_pixmap)
        self._image_label.setMouseTracking(True)
        self._image_label.mousePressEvent = self._on_mouse_press  # type: ignore[method-assign]
        self._image_label.mouseMoveEvent = self._on_mouse_move  # type: ignore[method-assign]
        self._image_label.mouseReleaseEvent = self._on_mouse_release  # type: ignore[method-assign]

        scroll.setWidget(self._image_label)
        layout.addWidget(scroll, stretch=1)

        # Right: ROI list + buttons
        right = QVBoxLayout()

        self._roi_list = QListWidget()
        self._roi_list.setMinimumWidth(200)
        right.addWidget(QLabel("Regions:"))
        right.addWidget(self._roi_list, stretch=1)

        btn_delete = QPushButton("Delete Selected")
        btn_delete.clicked.connect(self._on_delete_selected)
        right.addWidget(btn_delete)

        btn_clear = QPushButton("Clear All")
        btn_clear.clicked.connect(self._on_clear_all)
        right.addWidget(btn_clear)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        right.addWidget(buttons)

        layout.addLayout(right)
    # END_BLOCK_SETUP_UI

    # START_BLOCK_MOUSE_EVENTS
    def _on_mouse_press(self, event) -> None:
        self._origin = QRect(event.pos(), event.pos())
        self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self._image_label)
        self._rubber_band.setGeometry(self._origin)
        self._rubber_band.show()

    def _on_mouse_move(self, event) -> None:
        if self._rubber_band is not None and self._origin is not None:
            self._rubber_band.setGeometry(
                QRect(self._origin.topLeft(), event.pos()).normalized()
            )

    def _on_mouse_release(self, event) -> None:
        if self._rubber_band is not None and self._origin is not None:
            rect = QRect(self._origin.topLeft(), event.pos()).normalized()
            if rect.width() > 5 and rect.height() > 5:
                item = RectItem(
                    rect.x(), rect.y(),
                    rect.x() + rect.width(), rect.y() + rect.height(),
                )
                self._rects.append(item)
                self._add_rect_to_list(item)
                self._repaint_pixmap()
            self._rubber_band.hide()
            self._rubber_band = None
            self._origin = None
    # END_BLOCK_MOUSE_EVENTS

    # START_BLOCK_ROI_ACTIONS
    def _add_rect_to_list(self, rect: RectItem) -> None:
        item = QListWidgetItem(rect.to_csv())
        item.setData(Qt.ItemDataRole.UserRole, len(self._rects) - 1)
        self._roi_list.addItem(item)

    def _on_delete_selected(self) -> None:
        for item in self._roi_list.selectedItems():
            idx = item.data(Qt.ItemDataRole.UserRole)
            if idx is not None and 0 <= idx < len(self._rects):
                self._rects.pop(idx)
            self._roi_list.takeItem(self._roi_list.row(item))
        self._reindex_list()
        self._repaint_pixmap()

    def _on_clear_all(self) -> None:
        self._rects.clear()
        self._roi_list.clear()
        self._repaint_pixmap()

    def _reindex_list(self) -> None:
        for i in range(self._roi_list.count()):
            self._roi_list.item(i).setData(Qt.ItemDataRole.UserRole, i)

    def _repaint_pixmap(self) -> None:
        pix = self._frame_pixmap.copy()
        painter = QPainter(pix)
        pen = QPen(Qt.GlobalColor.green)
        pen.setWidth(2)
        painter.setPen(pen)
        for r in self._rects:
            n = r.normalized()
            painter.drawRect(n.x1, n.y1, n.x2 - n.x1, n.y2 - n.y1)
        painter.end()
        self._image_label.setPixmap(pix)
    # END_BLOCK_ROI_ACTIONS

    # START_BLOCK_ON_ACCEPT
    def _on_accept(self) -> None:
        tuples = [r.to_tuple() for r in self._rects]
        logger.info(
            "[GUI-RoiSelector][_on_accept] ROIs selected | count={} rois={}",
            len(tuples),
            tuples,
        )
        self.rois_selected.emit(tuples)
        self.accept()
    # END_BLOCK_ON_ACCEPT
