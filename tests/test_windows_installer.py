# FILE: tests/test_windows_installer.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Protect accepted Windows installer payload and directive integrity
#   SCOPE: Static checks for canonical bundle, README, icon, and removed invalid sections
#   DEPENDS: pytest, pathlib
#   LINKS: V-REF-WIN-INSTALLER
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   test_installer_contains_accepted_payload_once - verifies bundle and README payloads
#   test_installer_has_one_canonical_icon_directive - verifies unique canonical setup icon
#   test_installer_omits_invalid_legacy_sections - verifies removed invalid installer sections
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v0.1.0 - Added accepted installer payload and uniqueness recovery checks
# END_CHANGE_SUMMARY

from pathlib import Path

INSTALLER = (
    Path(__file__).parents[1]
    / "packaging"
    / "windows"
    / "installer"
    / "video2pptx.iss"
)


def _installer_text() -> str:
    return INSTALLER.read_text(encoding="utf-8")


def test_installer_contains_accepted_payload_once():
    text = _installer_text()
    assert text.count('Source: "..\\..\\..\\README.md";') == 1
    assert text.count('Source: "..\\..\\..\\dist\\windows\\Video2PPTX\\*";') == 1


def test_installer_has_one_canonical_icon_directive():
    directives = [
        line.strip()
        for line in _installer_text().splitlines()
        if line.strip().startswith("SetupIconFile=")
    ]
    assert directives == ["SetupIconFile=..\\..\\..\\assets\\branding\\Video2PPTX.ico"]


def test_installer_omits_invalid_legacy_sections():
    text = _installer_text()
    assert "[UninstallRun]" not in text
    assert "[Registry]" not in text
    assert ".v2pp" not in text
