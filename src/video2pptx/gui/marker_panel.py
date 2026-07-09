# FILE: src/video2pptx/gui/marker_panel.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Marker list panel — displays blue markers with timestamp, delete, re-snap, seek actions
#   SCOPE: QDialog with QTableWidget listing markers. Emits signals for marker actions.
#   DEPENDS: PySide6, M-GUI-MARKER-MANAGER
#   LINKS: M-GUI-MARKER-PANEL
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   MarkerPanel - QDialog with table of markers, delete/re-snap/seek buttons per row
# END_MODULE_MAP

from __future__ import annotations

from loguru import logger
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from video2pptx.gui.marker_manager import delete_marker, get_markers, resnap_marker
from video2pptx.project_manager import Project


class MarkerPanel(QDialog):
    # START_CONTRACT: MarkerPanel
    #   PURPOSE: QDialog displaying all markers in a table with per-row delete/re-snap buttons and seek-to-ts
    #   INPUTS: { project: Project }
    #   OUTPUTS: signals: marker_deleted(float), marker_resnapped(float), seek_requested(float)
    #   SIDE_EFFECTS: calls marker_manager functions (delete_marker, resnap_marker) which persist to project.json
    #   LINKS: M-GUI-MARKER-PANEL
    # END_CONTRACT: MarkerPanel

    marker_deleted = Signal(float)
    marker_resnapped = Signal(float)
    seek_requested = Signal(float)

    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project = project
        self.setWindowTitle("Markers")
        self.setMinimumSize(500, 300)
        self.setModal(False)
        self._setup_ui()
        self._refresh()

    # START_BLOCK_SETUP_UI
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QLabel("Double-click a row to seek to marker position")
        header.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(header)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Original TS", "Snapped TS", "Mode", "Actions"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.itemDoubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self._table, stretch=1)

        btn_row = QHBoxLayout()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self._refresh)
        btn_row.addWidget(btn_refresh)
        btn_row.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)
    # END_BLOCK_SETUP_UI

    # START_BLOCK_REFRESH
    def _refresh(self) -> None:
        markers = get_markers(self._project)
        self._table.setRowCount(len(markers))

        for row, m in enumerate(markers):
            orig = m.get("original_ts", 0)
            snapped = m.get("snapped_ts", 0)
            mode = m.get("snap_mode", "")

            orig_item = QTableWidgetItem(f"{orig:.3f}")
            orig_item.setData(Qt.ItemDataRole.UserRole, orig)
            self._table.setItem(row, 0, orig_item)

            snapped_item = QTableWidgetItem(f"{snapped:.3f}")
            self._table.setItem(row, 1, snapped_item)

            mode_item = QTableWidgetItem(mode)
            self._table.setItem(row, 2, mode_item)

            actions = QWidget()
            act_layout = QHBoxLayout(actions)
            act_layout.setContentsMargins(2, 2, 2, 2)

            btn_seek = QPushButton("Seek")
            btn_seek.setToolTip("Seek video to this marker position")
            btn_seek.clicked.connect(lambda checked, ts=snapped: self._on_seek(ts))
            act_layout.addWidget(btn_seek)

            btn_resnap = QPushButton("Re-snap")
            btn_resnap.setToolTip("Re-run snap on this marker")
            btn_resnap.clicked.connect(lambda checked, ts=orig: self._on_resnap(ts))
            act_layout.addWidget(btn_resnap)

            btn_del = QPushButton("Delete")
            btn_del.setToolTip("Delete this marker")
            btn_del.clicked.connect(lambda checked, ts=orig: self._on_delete(ts))
            act_layout.addWidget(btn_del)

            self._table.setCellWidget(row, 3, actions)
    # END_BLOCK_REFRESH

    # START_BLOCK_ACTIONS
    def _on_seek(self, ts: float) -> None:
        logger.info("[GUI-MarkerPanel][seek] Seeking | ts={:.3f}", ts)
        self.seek_requested.emit(ts)

    def _on_resnap(self, ts: float) -> None:
        updated = resnap_marker(self._project, ts)
        if updated:
            self.marker_resnapped.emit(updated.get("snapped_ts", ts))
            self._refresh()
            logger.info("[GUI-MarkerPanel][resnap] Done | ts={:.3f}", ts)

    def _on_delete(self, ts: float) -> None:
        if delete_marker(self._project, ts):
            self.marker_deleted.emit(ts)
            self._refresh()
            logger.info("[GUI-MarkerPanel][delete] Done | ts={:.3f}", ts)

    def _on_row_double_clicked(self, item: QTableWidgetItem) -> None:
        row = item.row()
        orig_item = self._table.item(row, 0)
        if orig_item is not None:
            ts = orig_item.data(Qt.ItemDataRole.UserRole)
            if isinstance(ts, float):
                self._on_seek(ts)
    # END_BLOCK_ACTIONS
