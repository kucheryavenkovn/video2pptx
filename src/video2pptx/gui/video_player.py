# FILE: src/video2pptx/gui/video_player.py
# VERSION: 0.3.0
# START_MODULE_CONTRACT
#   PURPOSE: QMediaPlayer + QGraphicsVideoItem with transport controls — render subtitles on video via QGraphicsScene
#   SCOPE: QWidget with embedded graphics view, transport bar, position/state/duration signals, subtitle overlay, keyboard navigation (arrows, Space)
#   DEPENDS: PySide6.QtMultimedia
#   LINKS: M-GUI-VIDEOPLAYER
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   VideoPlayerWidget - QWidget with QGraphicsView, QGraphicsVideoItem, subtitle text, playback controls, keyboard seeking
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

from loguru import logger
from PySide6.QtCore import QSizeF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPixmap, QResizeEvent, QTextOption
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStyle,
    QVBoxLayout,
    QWidget,
)


class VideoPlayerWidget(QWidget):
    # START_CONTRACT: VideoPlayerWidget
    #   PURPOSE: QGraphicsView + QGraphicsVideoItem + subtitle text overlay with transport controls
    #   INPUTS: { video_path: Path | None }
    #   OUTPUTS: signals: positionChanged(float seconds), stateChanged(str), durationChanged(float)
    #   SIDE_EFFECTS: loads video file, may use GPU decoding via QtMultimedia
    #   LINKS: M-GUI-VIDEOPLAYER
    # END_CONTRACT: VideoPlayerWidget

    positionChanged = Signal(float)  # seconds
    stateChanged = Signal(str)  # playing | paused | stopped
    durationChanged = Signal(float)  # seconds

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)

        self._is_playing = False
        self._setup_ui()
        self._connect_signals()

        self._slide_pixmap: QGraphicsPixmapItem | None = None

    # START_BLOCK_SETUP_UI
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Graphics scene for video + subtitle overlay
        self._scene = QGraphicsScene(self)
        self._video_item = QGraphicsVideoItem()
        self._video_item.setSize(QSizeF(320, 240))
        self._scene.addItem(self._video_item)
        self._player.setVideoOutput(self._video_item)

        # Subtitle text item — rendered above video with word wrap
        self._subtitle_item = QGraphicsTextItem()
        self._subtitle_item.setZValue(1)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self._subtitle_item.setFont(font)
        self._subtitle_item.setDefaultTextColor(Qt.GlobalColor.white)
        opt = self._subtitle_item.document().defaultTextOption()
        opt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        opt.setWrapMode(QTextOption.WrapMode.WordWrap)
        self._subtitle_item.document().setDefaultTextOption(opt)
        self._scene.addItem(self._subtitle_item)

        # Graphics view
        self._view = QGraphicsView(self._scene)
        self._view.setMinimumSize(320, 240)
        self._view.setStyleSheet("background-color: #1e1e1e; border: none;")
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._view.setFrameShape(QGraphicsView.Shape.NoFrame)
        layout.addWidget(self._view, stretch=1)

        # Transport bar
        transport = QHBoxLayout()

        self._play_btn = QPushButton()
        self._play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self._play_btn.setToolTip("Play / Pause")
        transport.addWidget(self._play_btn)

        self._stop_btn = QPushButton()
        self._stop_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self._stop_btn.setToolTip("Stop")
        transport.addWidget(self._stop_btn)

        # Time counter
        self._time_label = QLabel("00:00 / 00:00")
        self._time_label.setMinimumWidth(100)
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        transport.addWidget(self._time_label)

        # Seek slider
        self._seek_slider = QSlider(Qt.Orientation.Horizontal)
        self._seek_slider.setRange(0, 0)
        transport.addWidget(self._seek_slider, stretch=1)

        # Volume slider
        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(50)
        self._volume_slider.setToolTip("Volume")
        self._volume_slider.setFixedWidth(100)
        transport.addWidget(self._volume_slider)

        layout.addLayout(transport)

        # Click on view to gain keyboard focus
        self._view.mousePressEvent = self._on_view_mouse_press  # type: ignore[method-assign]
    # END_BLOCK_SETUP_UI

    # START_BLOCK_CONNECT_SIGNALS
    def _connect_signals(self) -> None:
        self._play_btn.clicked.connect(self._on_play_pause)
        self._stop_btn.clicked.connect(self.stop)
        self._seek_slider.sliderMoved.connect(self._on_seek)
        self._volume_slider.valueChanged.connect(self._on_volume_changed)

        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)
    # END_BLOCK_CONNECT_SIGNALS

    # START_BLOCK_PLAYBACK_CONTROLS
    def load_video(self, video_path: str | Path) -> None:
        path = Path(video_path)
        if not path.is_file():
            logger.warning(f"[GUI-VideoPlayer][load_video] Video not found | path={path}")
            return

        from PySide6.QtCore import QUrl
        self._player.setSource(QUrl.fromLocalFile(str(path.resolve())))
        logger.info(f"[GUI-VideoPlayer][load_video] Loaded | path={path}")
        self._play_btn.setEnabled(True)

    def play(self) -> None:
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        self._player.stop()
        self._seek_slider.setValue(0)
        self._time_label.setText("00:00 / 00:00")
        self._is_playing = False

    def _on_play_pause(self) -> None:
        if self._is_playing:
            self._player.pause()
        else:
            self._player.play()

    def _on_seek(self, position: int) -> None:
        self._player.setPosition(position)

    def _on_volume_changed(self, value: int) -> None:
        self._audio_output.setVolume(value / 100.0)
    # END_BLOCK_PLAYBACK_CONTROLS

    # START_BLOCK_SIGNAL_HANDLERS
    def _on_position_changed(self, ms: int) -> None:
        seconds = ms / 1000.0
        total_sec = self._player.duration() / 1000.0
        self._seek_slider.setValue(ms)
        self._time_label.setText(
            f"{self._fmt_time(seconds)} / {self._fmt_time(total_sec)}"
        )
        self.positionChanged.emit(seconds)

    def _on_duration_changed(self, ms: int) -> None:
        self._seek_slider.setRange(0, ms)
        self.durationChanged.emit(ms / 1000.0)

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._is_playing = False
            self._play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.stateChanged.emit("stopped")

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._is_playing = True
            self._play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.stateChanged.emit("playing")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self._is_playing = False
            self._play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.stateChanged.emit("paused")
        else:
            self._is_playing = False
            self._play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.stateChanged.emit("stopped")
    # END_BLOCK_SIGNAL_HANDLERS

    # START_BLOCK_UTILITY
    @staticmethod
    def _fmt_time(seconds: float) -> str:
        if seconds <= 0 or not seconds:
            return "00:00"
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02d}:{s:02d}"

    def player(self) -> QMediaPlayer:
        return self._player

    def clear_video(self) -> None:
        self._player.setSource(None)
        self._time_label.setText("00:00 / 00:00")
        self._seek_slider.setRange(0, 0)
        self._is_playing = False

    def set_subtitle_text(self, text: str | None) -> None:
        if text:
            self._subtitle_item.setHtml(
                f'<div style="background: rgba(0,0,0,180); color: white; '
                f'padding: 6px 12px; border-radius: 4px;">{text}</div>'
            )
            # Set text width to video width for wrapping
            vr = self._video_item.boundingRect()
            tw = max(vr.width() - 20, 50)
            self._subtitle_item.setTextWidth(tw)
            # Center at bottom of video
            br = self._subtitle_item.boundingRect()
            x = (vr.width() - br.width()) / 2
            y = vr.height() - br.height() - 10
            self._subtitle_item.setPos(x, y)
            self._subtitle_item.show()
        else:
            self._subtitle_item.setHtml("")
            self._subtitle_item.hide()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._fit_scene()

    def _fit_scene(self) -> None:
        if self._scene is None or self._view is None:
            return
        self._scene.setSceneRect(self._view.rect())
        # Fit video item to view width, keep aspect ratio
        vw = self._view.width()
        vh = self._view.height()
        if vw > 0 and vh > 0:
            self._video_item.setSize(QSizeF(vw, vh))
    # START_BLOCK_KEYBOARD_NAV
    def _on_view_mouse_press(self, event) -> None:
        self._view.setFocus()
        # Call original handler if needed
        QGraphicsView.mousePressEvent(self._view, event)

    def keyPressEvent(self, event: QKeyEvent | None) -> None:  # noqa: N802
        if event is None:
            super().keyPressEvent(event)
            return

        key = event.key()
        modifiers = event.modifiers()

        # Space -> play/pause
        if key == Qt.Key.Key_Space:
            self._on_play_pause()
            event.accept()
            return

        # Arrow seeking
        if key == Qt.Key.Key_Left:
            delta = -30.0 if (modifiers & Qt.KeyboardModifier.ControlModifier) else -5.0
            self.seek_relative(delta)
            event.accept()
            return

        if key == Qt.Key.Key_Right:
            delta = 30.0 if (modifiers & Qt.KeyboardModifier.ControlModifier) else 5.0
            self.seek_relative(delta)
            event.accept()
            return

        # Volume
        if key == Qt.Key.Key_Up:
            v = min(100, self._volume_slider.value() + 10)
            self._volume_slider.setValue(v)
            event.accept()
            return

        if key == Qt.Key.Key_Down:
            v = max(0, self._volume_slider.value() - 10)
            self._volume_slider.setValue(v)
            event.accept()
            return

        super().keyPressEvent(event)

    def seek_relative(self, delta_seconds: float) -> None:
        current = self._player.position()
        new_pos = max(0, current + int(delta_seconds * 1000))
        self._player.setPosition(new_pos)

    def duration(self) -> float:
        return self._player.duration() / 1000.0
    # END_BLOCK_KEYBOARD_NAV

    # START_BLOCK_SLIDE_IMAGE
    def show_slide_image(self, path: str, label: str = "") -> None:
        self.hide_slide_image()
        pix = QPixmap(path)
        if pix.isNull():
            logger.warning(f"[GUI-VideoPlayer][show_slide_image] Cannot load: {path}")
            return
        self._slide_pixmap = QGraphicsPixmapItem()
        vr = self._video_item.boundingRect()
        scaled = pix.scaled(
            int(vr.width()),
            int(vr.height()),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._slide_pixmap.setPixmap(scaled)
        pr = self._slide_pixmap.boundingRect()
        self._slide_pixmap.setPos((vr.width() - pr.width()) / 2, (vr.height() - pr.height()) / 2)
        self._slide_pixmap.setZValue(2)
        self._scene.addItem(self._slide_pixmap)

        if label:
            self._slide_label = QGraphicsTextItem(label)
            font = QFont()
            font.setPointSize(18)
            font.setBold(True)
            self._slide_label.setFont(font)
            self._slide_label.setDefaultTextColor(QColor(76, 175, 80))
            self._slide_label.setZValue(3)
            self._slide_label.setPos(12, 8)
            self._scene.addItem(self._slide_label)
        else:
            self._slide_label = None

        logger.info(f"[GUI-VideoPlayer][show_slide_image] Showing | path={path} label={label}")

    def hide_slide_image(self) -> None:
        if self._slide_pixmap is not None:
            self._scene.removeItem(self._slide_pixmap)
            self._slide_pixmap = None
        if hasattr(self, '_slide_label') and self._slide_label is not None:
            self._scene.removeItem(self._slide_label)
            self._slide_label = None
    # END_BLOCK_SLIDE_IMAGE
