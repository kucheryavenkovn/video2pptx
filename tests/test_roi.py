# FILE: tests/test_roi.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for ROI crop and ignore mask operations
#   SCOPE: ROI parsing, cropping, masking
#   DEPENDS: pytest, numpy, video2pptx.roi
#   LINKS: V-M-ROI, M-ROI
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

import numpy as np

from video2pptx.models import Roi
from video2pptx.roi import SlideRegion, parse_ignore_rois, parse_roi


def make_frame(h: int = 100, w: int = 200) -> np.ndarray:
    return np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)


class TestParseRoi:
    def test_none_returns_full(self):
        sr = parse_roi(None)
        assert sr.roi is None

    def test_auto_returns_full(self):
        sr = parse_roi("auto")
        assert sr.roi is None

    def test_full_returns_full(self):
        sr = parse_roi("full")
        assert sr.roi is None

    def test_manual_coords(self):
        sr = parse_roi("100,50,1800,1000")
        assert sr.roi is not None
        assert sr.roi.x1 == 100
        assert sr.roi.y1 == 50
        assert sr.roi.x2 == 1800
        assert sr.roi.y2 == 1000

    def test_manual_list(self):
        sr = parse_roi([120, 40, 1720, 980])
        assert sr.roi is not None
        assert sr.roi.x1 == 120
        assert sr.roi.y2 == 980

    def test_invalid_format_falls_back(self):
        sr = parse_roi("not-a-roi")
        assert sr.roi is None

    def test_coords_with_spaces(self):
        sr = parse_roi("100, 50, 1800, 1000")
        assert sr.roi is not None
        assert sr.roi.x2 == 1800


class TestSlideRegionCrop:
    def test_no_roi_returns_full(self):
        frame = make_frame(100, 200)
        sr = SlideRegion(roi=None)
        result = sr.crop(frame)
        assert result.shape == (100, 200, 3)

    def test_crop_with_roi(self):
        frame = make_frame(100, 200)
        sr = SlideRegion(roi=Roi(x1=10, y1=10, x2=100, y2=90))
        result = sr.crop(frame)
        assert result.shape[0] == 80
        assert result.shape[1] == 90

    def test_crop_clips_to_frame(self):
        frame = make_frame(100, 200)
        sr = SlideRegion(roi=Roi(x1=0, y1=0, x2=500, y2=500))
        result = sr.crop(frame)
        assert result.shape[0] == 100
        assert result.shape[1] == 200


class TestSlideRegionMask:
    def test_no_ignore_returns_copy(self):
        frame = make_frame()
        sr = SlideRegion(ignore_rois=[])
        result = sr.apply_masks(frame)
        assert np.array_equal(result, frame)

    def test_ignore_region_zeroed(self):
        frame = np.ones((100, 200, 3), dtype=np.uint8) * 255
        sr = SlideRegion(ignore_rois=[Roi(x1=0, y1=0, x2=50, y2=50)])
        result = sr.apply_masks(frame)
        assert np.all(result[:50, :50] == 0)
        assert np.all(result[60:, 60:] == 255)

    def test_ignore_clips_to_frame(self):
        frame = np.ones((100, 100, 3), dtype=np.uint8)
        sr = SlideRegion(ignore_rois=[Roi(x1=0, y1=0, x2=200, y2=200)])
        result = sr.apply_masks(frame)
        assert np.all(result == 0)


class TestParseIgnoreRois:
    def test_empty(self):
        assert parse_ignore_rois(None) == []
        assert parse_ignore_rois([]) == []

    def test_single_region(self):
        result = parse_ignore_rois([[1450, 720, 1900, 1080]])
        assert len(result) == 1
        assert result[0].x1 == 1450

    def test_multi_region(self):
        result = parse_ignore_rois([[0, 0, 100, 100], [200, 200, 300, 300]])
        assert len(result) == 2

    def test_invalid_length_skipped(self):
        result = parse_ignore_rois([[1, 2, 3]])
        assert result == []


class TestSlideRegionProcess:
    def test_crop_and_mask(self):
        frame = np.ones((200, 300, 3), dtype=np.uint8) * 255
        sr = SlideRegion(
            roi=Roi(x1=0, y1=0, x2=200, y2=200),
            ignore_rois=[Roi(x1=0, y1=0, x2=50, y2=50)],
        )
        result = sr.process(frame)
        assert result.shape == (200, 200, 3)
        assert np.all(result[:50, :50] == 0)
