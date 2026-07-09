# FILE: src/video_slide_md/gui/video_player.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: QMediaPlayer + QVideoWidget with transport controls (play/pause/stop, seek, volume, timecode)
#   SCOPE: QWidget with embedded QVideoWidget, transport bar, position/state/duration signals
#   DEPENDS: PySide6.QtMultimedia
#   LINKS: M-GUI-VIDEOPLAYER
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   VideoPlayerWidget - QWidget with QVideoWidget, transport bar, playback controls
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

from loguru import logger
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
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
    #   PURPOSE: QWidget with QVideoWidget and transport controls — play, pause, stop, seek, volume, timecode
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
        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)

        self._overlay: QWidget | None = None
        self._is_playing = False
        self._setup_ui()
        self._connect_signals()

    # START_BLOCK_SETUP_UI
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Video display
        self._video_widget = QVideoWidget()
        self._video_widget.setMinimumSize(320, 240)
        self._video_widget.setStyleSheet("background-color: #1e1e1e;")
        self._player.setVideoOutput(self._video_widget)
        layout.addWidget(self._video_widget)

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

    def set_overlay_widget(self, overlay: QWidget) -> None:
        self._overlay = overlay
        self._overlay.setParent(self)
        self._overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._position_overlay()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._position_overlay()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._position_overlay()

    def _position_overlay(self) -> None:
        if self._overlay is not None:
            self._overlay.setGeometry(self._video_widget.geometry())
            self._overlay.raise_()
    # END_BLOCK_UTILITY
