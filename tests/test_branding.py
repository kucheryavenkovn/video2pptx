# FILE: tests/test_branding.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Verify Qt resource registration and AboutDialog logo loading
#   DEPENDS: PySide6, M-GUI-ABOUT
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


def test_icon_not_logo(qapp) -> None:
    _register()
    from PySide6.QtGui import QPixmap

    icon = QPixmap(":/branding/Video2PPTX-icon.png")
    logo = QPixmap(":/branding/Video2PPTX-logo.png")
    assert icon.size() != logo.size()


def test_null_pixmap_fallback(qapp) -> None:
    from PySide6.QtGui import QPixmap

    assert QPixmap(":/branding/nonexistent.png").isNull()


def test_about_dialog_opens(qapp, qtbot) -> None:
    _register()
    from video2pptx.application.identity import application_identity
    from video2pptx.gui.about_dialog import AboutDialog

    identity = application_identity()
    dlg = AboutDialog(identity)
    qtbot.addWidget(dlg)
    assert dlg.windowTitle() == f"About {identity.name}"


def test_about_dialog_logo_shown(qapp, qtbot) -> None:
    _register()
    from PySide6.QtWidgets import QLabel

    from video2pptx.application.identity import application_identity
    from video2pptx.gui.about_dialog import AboutDialog

    identity = application_identity()
    dlg = AboutDialog(identity)
    qtbot.addWidget(dlg)
    labels = dlg.findChildren(QLabel)
    logo = next(
        (lb for lb in labels if lb.pixmap() and not lb.pixmap().isNull()),
        None,
    )
    assert logo is not None, "AboutDialog should have a logo QLabel with non-null pixmap"
