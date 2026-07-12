# FILE: tests/test_bootstrap.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Module-local tests for ApplicationServices neutral composition root.
#   SCOPE: Service instantiation, lazy creation, shared context, all service types
#   DEPENDS: video2pptx.bootstrap, video2pptx.application.services
#   LINKS: M-APP-BOOTSTRAP
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   TestApplicationServices - verify lazy creation, shared context, all service types
# END_MODULE_MAP

from __future__ import annotations

from video2pptx.bootstrap import ApplicationServices


class TestApplicationServices:
    def test_default_construction(self) -> None:
        svc = ApplicationServices()
        assert svc.context is not None
        assert svc.repository is not None

    def test_context_has_repository(self) -> None:
        svc = ApplicationServices()
        assert svc.context.repository is svc.repository

    def test_preview_service_is_lazy(self) -> None:
        svc = ApplicationServices()
        assert svc._preview is None
        _ = svc.preview_service
        assert svc._preview is not None

    def test_detection_service_is_lazy(self) -> None:
        svc = ApplicationServices()
        assert svc._detect is None
        _ = svc.detection_service
        assert svc._detect is not None

    def test_alignment_service_is_lazy(self) -> None:
        svc = ApplicationServices()
        assert svc._align is None
        _ = svc.alignment_service
        assert svc._align is not None

    def test_notes_service_is_lazy(self) -> None:
        svc = ApplicationServices()
        assert svc._notes is None
        _ = svc.notes_service
        assert svc._notes is not None

    def test_export_service_is_lazy(self) -> None:
        svc = ApplicationServices()
        assert svc._export is None
        _ = svc.export_service
        assert svc._export is not None

    def test_validation_service_is_lazy(self) -> None:
        svc = ApplicationServices()
        assert svc._validate is None
        _ = svc.validation_service
        assert svc._validate is not None

    def test_auto_service_is_lazy(self) -> None:
        svc = ApplicationServices()
        assert svc._auto is None
        _ = svc.auto_service
        assert svc._auto is not None

    def test_auto_service_has_all_sub_services(self) -> None:
        svc = ApplicationServices()
        auto = svc.auto_service
        assert auto._preview is svc.preview_service
        assert auto._detect is svc.detection_service
        assert auto._align is svc.alignment_service
        assert auto._notes is svc.notes_service
        assert auto._export is svc.export_service
        assert auto._validate is svc.validation_service

    def test_same_instance_returns_same_services(self) -> None:
        svc = ApplicationServices()
        assert svc.preview_service is svc.preview_service
        assert svc.detection_service is svc.detection_service
        assert svc.alignment_service is svc.alignment_service

    def test_context_injected_into_services(self) -> None:
        svc = ApplicationServices()
        detect = svc.detection_service
        assert detect._ctx is svc.context

    def test_all_service_types_present(self) -> None:
        svc = ApplicationServices()
        _ = svc.preview_service
        _ = svc.detection_service
        _ = svc.alignment_service
        _ = svc.notes_service
        _ = svc.export_service
        _ = svc.validation_service
        _ = svc.auto_service
        # All created without error
