# FILE: tests/test_branding.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Verify Qt resource registration, AboutDialog logo, MainWindow branding
#   DEPENDS: PySide6, M-GUI-ABOUT, M-GUI-MAIN
#   ROLE: TEST
#   MAP_MODE: NONE
# END_MODULE_CONTRACT

from __future__ import annotations


def _register():
    import video2pptx.gui.resources.branding_rc  # noqa: F401


def test_icon_resource_resolves(qapp) -> None:
    _register()
    from PySide6.QtGui import QIcon

    icon = QIcon(":/branding/Video2PPTX-icon.png")
    assert not icon.isNull()
    pix = icon.pixmap(64, 64)
    assert not pix.isNull()


def test_logo_resource_resolves(qapp) -> None:
    _register()
    from PySide6.QtGui import QPixmap

    pix = QPixmap(":/branding/Video2PPTX-logo.png")
    assert not pix.isNull()


def test_null_pixmap_fallback(qapp) -> None:
    from PySide6.QtGui import QPixmap

    assert QPixmap(":/branding/nonexistent.png").isNull()


def test_about_dialog_logo_shown(qapp, qtbot) -> None:
    _register()
    from PySide6.QtWidgets import QLabel

    from video2pptx.application.identity import application_identity
    from video2pptx.gui.about_dialog import AboutDialog

    identity = application_identity()
    dlg = AboutDialog(identity)
    qtbot.addWidget(dlg)
    dlg.show()

    logo = dlg.findChild(QLabel, "aboutLogo")
    assert logo is not None, "aboutLogo QLabel must exist"
    assert logo.pixmap() is not None
    assert not logo.pixmap().isNull()
    assert logo.pixmap().width() > 0
    assert logo.pixmap().height() > 0


def test_about_dialog_title_hidden_when_logo_shown(qapp, qtbot) -> None:
    _register()
    from PySide6.QtWidgets import QLabel

    from video2pptx.application.identity import application_identity
    from video2pptx.gui.about_dialog import AboutDialog

    identity = application_identity()
    dlg = AboutDialog(identity)
    qtbot.addWidget(dlg)
    dlg.show()

    logo = dlg.findChild(QLabel, "aboutLogo")
    all_labels = dlg.findChildren(QLabel)
    title_label = next(
        (lb for lb in all_labels if lb.text() and "<b>" in lb.text()),
        None,
    )
    if logo and logo.pixmap() and not logo.pixmap().isNull():
        # Logo visible → title should be hidden
        if title_label:
            assert not title_label.isVisible()
    else:
        # Logo not visible → title must be visible
        assert title_label and title_label.isVisible()


def test_about_dialog_opens(qapp, qtbot) -> None:
    _register()
    from video2pptx.application.identity import application_identity
    from video2pptx.gui.about_dialog import AboutDialog

    identity = application_identity()
    dlg = AboutDialog(identity)
    qtbot.addWidget(dlg)
    assert dlg.windowTitle() == f"About {identity.name}"


class TestMainWindowBranding:
    def test_compact_logo_present(self, qapp, qtbot) -> None:
        _register()
        from PySide6.QtWidgets import QLabel

        from video2pptx.gui.main_window import MainWindow

        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        logo = window.findChild(QLabel, "applicationLogo")
        assert logo is not None, "applicationLogo QLabel must exist"

        # Verify pixmap
        if logo.pixmap():
            assert not logo.pixmap().isNull()
            w, h = logo.pixmap().width(), logo.pixmap().height()
            assert 150 <= w <= 250, f"logo width {w} outside compact bounds"
            assert 40 <= h <= 80, f"logo height {h} outside compact bounds"

        # Verify all header controls still present
        assert hasattr(window, "_video_label")
        assert hasattr(window, "_subs_label")
        assert hasattr(window, "_backend_label")
        assert hasattr(window, "_btn_detect")
        assert hasattr(window, "_btn_quick_preview")
        assert hasattr(window, "_btn_auto_align")
        assert hasattr(window, "_btn_process_notes")
        assert hasattr(window, "_btn_auto")
        assert hasattr(window, "_btn_export")
        assert hasattr(window, "_btn_save")

    def test_header_labels_visible(self, qapp, qtbot) -> None:
        _register()
        from video2pptx.gui.main_window import MainWindow

        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        assert window._video_label.isVisible()
        assert window._subs_label.isVisible()
        assert window._backend_label.isVisible()
