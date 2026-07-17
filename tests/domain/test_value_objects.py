# FILE: tests/domain/test_value_objects.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit tests for domain value objects: SlideId, TimeInterval, ArtifactRef.
#   SCOPE: Creation, invariants, parsing, rejection, immutability, round-trip, legacy migration.
#   DEPENDS: pytest, video2pptx.domain
#   LINKS: V-M-DOMAIN-VALUE
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import pytest

from video2pptx.domain import (
    ArtifactRef,
    SlideId,
    TimeInterval,
    ValidationError,
    migrate_legacy_artifact,
)

# ── SlideId ──────────────────────────────────────────────────────────────────


class TestSlideId:
    def test_new_generates_non_empty(self):
        sid = SlideId.new()
        assert sid.value
        assert len(sid.value) == 32
        assert int(sid.value, 16) >= 0

    def test_parse_round_trip(self):
        sid = SlideId.parse("abc123def456")
        assert sid.value == "abc123def456"
        assert str(sid) == "abc123def456"

    def test_equality_and_hash(self):
        a = SlideId("xyz")
        b = SlideId("xyz")
        c = SlideId("other")
        assert a == b
        assert hash(a) == hash(b)
        assert a != c

    def test_empty_rejected(self):
        with pytest.raises(ValidationError, match="non-empty"):
            SlideId("")

    def test_whitespace_rejected(self):
        with pytest.raises(ValidationError, match="non-empty"):
            SlideId("   ")

    def test_frozen(self):
        sid = SlideId("abc")
        with pytest.raises(Exception):
            sid.value = "changed"

    def test_two_new_are_distinct(self):
        a = SlideId.new()
        b = SlideId.new()
        assert a != b


# ── TimeInterval ─────────────────────────────────────────────────────────────


class TestTimeInterval:
    def test_normal(self):
        ti = TimeInterval(1.0, 5.0)
        assert ti.start == 1.0
        assert ti.end == 5.0
        assert ti.duration == 4.0

    def test_start_zero(self):
        ti = TimeInterval(0.0, 3.0)
        assert ti.duration == 3.0

    def test_end_equals_start_rejected(self):
        with pytest.raises(ValidationError):
            TimeInterval(5.0, 5.0)

    def test_negative_start_rejected(self):
        with pytest.raises(ValidationError, match=">= 0"):
            TimeInterval(-1.0, 5.0)

    def test_nan_rejected(self):
        with pytest.raises(ValidationError, match="NaN"):
            TimeInterval(float("nan"), 5.0)

    def test_inf_rejected(self):
        with pytest.raises(ValidationError, match="finite"):
            TimeInterval(0.0, float("inf"))

    def test_contains_boundary(self):
        ti = TimeInterval(2.0, 6.0)
        assert ti.contains(2.0)
        assert ti.contains(6.0)
        assert not ti.contains(1.9)
        assert not ti.contains(6.1)

    def test_overlaps(self):
        a = TimeInterval(0.0, 3.0)
        b = TimeInterval(2.0, 5.0)
        c = TimeInterval(4.0, 7.0)
        assert a.overlaps(b)
        assert not a.overlaps(c)

    def test_touches(self):
        a = TimeInterval(0.0, 3.0)
        b = TimeInterval(3.0, 6.0)
        assert a.touches(b)

    def test_touches_gap(self):
        a = TimeInterval(0.0, 3.0)
        b = TimeInterval(5.0, 8.0)
        assert not a.touches(b)

    def test_intersection(self):
        a = TimeInterval(0.0, 5.0)
        b = TimeInterval(3.0, 8.0)
        inter = a.intersection(b)
        assert inter is not None
        assert inter.start == 3.0
        assert inter.end == 5.0

    def test_intersection_disjoint(self):
        a = TimeInterval(0.0, 2.0)
        b = TimeInterval(5.0, 8.0)
        assert a.intersection(b) is None

    def test_shift(self):
        ti = TimeInterval(1.0, 4.0)
        shifted = ti.shift(2.0)
        assert shifted.start == 3.0
        assert shifted.end == 6.0
        assert ti.start == 1.0

    def test_with_start(self):
        ti = TimeInterval(1.0, 5.0)
        new = ti.with_start(2.0)
        assert new.start == 2.0
        assert new.end == 5.0

    def test_with_end(self):
        ti = TimeInterval(1.0, 5.0)
        new = ti.with_end(3.0)
        assert new.start == 1.0
        assert new.end == 3.0

    def test_frozen(self):
        ti = TimeInterval(1.0, 5.0)
        with pytest.raises(Exception):
            ti.start = 0.0

    def test_clamp(self):
        ti = TimeInterval(1.0, 10.0)
        clamped = ti.clamp(2.0, 8.0)
        assert clamped.start == 2.0
        assert clamped.end == 8.0


# ── ArtifactRef ──────────────────────────────────────────────────────────────


class TestArtifactRef:
    def test_valid_posix(self):
        ref = ArtifactRef.parse("slides/slide_001.png")
        assert ref.as_posix() == "slides/slide_001.png"

    def test_windows_separator_normalized(self):
        ref = ArtifactRef.parse("slides\\slide_001.png")
        assert ref.as_posix() == "slides/slide_001.png"

    def test_empty_rejected(self):
        with pytest.raises(ValidationError):
            ArtifactRef.parse("")

    def test_absolute_rejected(self):
        with pytest.raises(ValidationError, match="absolute"):
            ArtifactRef.parse("/slides/slide_001.png")

    def test_windows_absolute_rejected(self):
        with pytest.raises(ValidationError, match="absolute|traversal"):
            ArtifactRef.parse("D:\\project\\slides\\slide_001.png")

    def test_traversal_rejected(self):
        with pytest.raises(ValidationError, match="traversal"):
            ArtifactRef.parse("../escape.png")

    def test_double_prefix_rejected(self):
        with pytest.raises(ValidationError, match="double-prefix"):
            ArtifactRef.parse("slides/slides/slide_001.png")

    def test_resolve(self, tmp_path):
        ref = ArtifactRef.parse("deck.md")
        resolved = ref.resolve(tmp_path)
        assert resolved == tmp_path / "deck.md"

    def test_str_round_trip(self):
        ref = ArtifactRef.parse("alignment_report.json")
        assert str(ref) == "alignment_report.json"


class TestMigrateLegacyArtifact:
    def test_already_relative(self):
        ref = migrate_legacy_artifact("slides/slide_001.png", ".")
        assert ref.as_posix() == "slides/slide_001.png"

    def test_bare_filename_with_slides_dir(self, tmp_path):
        slides_dir = tmp_path / "slides"
        slides_dir.mkdir()
        (slides_dir / "slide_001.png").write_bytes(b"x")
        ref = migrate_legacy_artifact("slide_001.png", str(tmp_path))
        assert ref.as_posix() == "slides/slide_001.png"

    def test_absolute_inside_root(self, tmp_path):
        slides_dir = tmp_path / "slides"
        slides_dir.mkdir()
        img = slides_dir / "slide_002.png"
        img.write_bytes(b"x")
        ref = migrate_legacy_artifact(str(img), str(tmp_path))
        assert ref.as_posix() == "slides/slide_002.png"

    def test_absolute_outside_rejected(self, tmp_path):
        with pytest.raises(ValidationError, match="absolute|outside"):
            migrate_legacy_artifact("/nonexistent/slide.png", str(tmp_path))
