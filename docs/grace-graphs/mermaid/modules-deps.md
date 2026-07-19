# GRACE Module Dependencies

```mermaid
%% GRACE Module Dependencies
flowchart LR
  M_ADAPTERS["M-ADAPTERS<br/>LegacyPortAdapters<br/>[implemented]"]
  M_ANALYSIS_QUALITY["M-ANALYSIS-QUALITY<br/>AnalysisQualityPresets<br/>[implemented]"]
  M_ANALYSIS_SCALE["M-ANALYSIS-SCALE<br/>AnalysisScale<br/>[implemented]"]
  M_APP_ALIGN["M-APP-ALIGN<br/>AlignmentService<br/>[implemented]"]
  M_APP_AUTO["M-APP-AUTO<br/>AutoService<br/>[implemented]"]
  M_APP_BOOTSTRAP["M-APP-BOOTSTRAP<br/>ApplicationServicesBootstrap<br/>[active]"]
  M_APP_BUILD_META["M-APP-BUILD-META<br/>BuildMeta<br/>[active]"]
  M_APP_COMMON["M-APP-COMMON<br/>ApplicationCommon<br/>[implemented]"]
  M_APP_DETECT["M-APP-DETECT<br/>DetectionService<br/>[implemented]"]
  M_APP_EXPORT["M-APP-EXPORT<br/>ExportService<br/>[implemented]"]
  M_APP_IDENTITY["M-APP-IDENTITY<br/>ApplicationIdentity<br/>[active]"]
  M_APP_INPUT_RESOLVER["M-APP-INPUT-RESOLVER<br/>InputResolver<br/>[active]"]
  M_APP_LLM["M-APP-LLM<br/>LlmEnrichmentService<br/>[planned]"]
  M_APP_NOTES["M-APP-NOTES<br/>NotesService<br/>[implemented]"]
  M_APP_PREVIEW["M-APP-PREVIEW<br/>PreviewService<br/>[implemented]"]
  M_APP_PROJECT["M-APP-PROJECT<br/>ProjectService<br/>[planned]"]
  M_APP_SERVICE["M-APP-SERVICE<br/>AppService<br/>[partial]"]
  M_APP_VALIDATE["M-APP-VALIDATE<br/>ValidationService<br/>[implemented]"]
  M_ARCH_OVERVIEW["M-ARCH-OVERVIEW<br/>ArchitectureOverview<br/>[planned]"]
  M_ATOMIC_JSON["M-ATOMIC-JSON<br/>AtomicJson<br/>[planned]"]
  M_AUTO_ALIGN["M-AUTO-ALIGN<br/>AutoAlign<br/>[partial]"]
  M_BACKEND_OPENCV["M-BACKEND-OPENCV<br/>OpenCVBackend<br/>[implemented]"]
  M_BACKEND_PYAV["M-BACKEND-PYAV<br/>PyAVBackend<br/>[implemented]"]
  M_BACKENDS["M-BACKENDS<br/>Backends<br/>[implemented]"]
  M_CANONICAL_COMMANDS["M-CANONICAL-COMMANDS<br/>CommandRouter<br/>[planned]"]
  M_CLI["M-CLI<br/>CLI<br/>[implemented]"]
  M_CLI_ADAPTER["M-CLI-ADAPTER<br/>CliAdapter<br/>[active]"]
  M_COLAB["M-COLAB<br/>ColabDeployment<br/>[implemented]"]
  M_CONFIG["M-CONFIG<br/>Config<br/>[implemented]"]
  M_CONFIRM_POLICY["M-CONFIRM-POLICY<br/>ConfirmPolicy<br/>[planned]"]
  M_DEBUG_ACTION["M-DEBUG-ACTION<br/>ActionRegistry<br/>[implemented]"]
  M_DEBUG_EXPORT["M-DEBUG-EXPORT<br/>DebugExport<br/>[implemented]"]
  M_DEBUG_MCP["M-DEBUG-MCP<br/>McpServer<br/>[implemented]"]
  M_DEDUPE["M-DEDUPE<br/>Dedupe<br/>[implemented]"]
  M_DESKTOP_BOOTSTRAP["M-DESKTOP-BOOTSTRAP<br/>DesktopBootstrap<br/>[active]"]
  M_DETECT_BENCHMARK["M-DETECT-BENCHMARK<br/>DetectBenchmarkPlan<br/>[active]"]
  M_DETECT_METRICS["M-DETECT-METRICS<br/>DetectMetrics<br/>[active]"]
  M_DETECT_PERF_DECISION["M-DETECT-PERF-DECISION<br/>BottleneckDecision<br/>[done]"]
  M_DETECT_SLIDES["M-DETECT-SLIDES<br/>DetectSlides<br/>[implemented]"]
  M_DETECT_TARGET_DISCRIMINATION_R2["M-DETECT-TARGET-DISCRIMINATION-R2<br/>TargetOptimizationDiscriminationR2<br/>[verified]"]
  M_DOMAIN_EVENTS["M-DOMAIN-EVENTS<br/>DomainEvents<br/>[planned]"]
  M_DOMAIN_PROJECT["M-DOMAIN-PROJECT<br/>ProjectAggregate<br/>[implemented]"]
  M_DOMAIN_SLIDE["M-DOMAIN-SLIDE<br/>SlideEntity<br/>[implemented]"]
  M_DOMAIN_STATE["M-DOMAIN-STATE<br/>PipelineState<br/>[implemented]"]
  M_DOMAIN_VALUE["M-DOMAIN-VALUE<br/>ValueObjects<br/>[implemented]"]
  M_E2E_RUNNER["M-E2E-RUNNER<br/>McpE2eRunner<br/>[partial]"]
  M_E2E_SCENARIOS["M-E2E-SCENARIOS<br/>E2eScenarios<br/>[planned]"]
  M_E2E_SNAPSHOT["M-E2E-SNAPSHOT<br/>Snapshot<br/>[planned]"]
  M_FILE_REPO["M-FILE-REPO<br/>FileProjectRepository<br/>[implemented]"]
  M_FRAME_FEATURES["M-FRAME-FEATURES<br/>FrameFeatures<br/>[implemented]"]
  M_GITHUB_PROVIDER["M-GITHUB-PROVIDER<br/>GitHubReleaseProvider<br/>[implemented]"]
  M_GOLDEN_MEAN_DECISION["M-GOLDEN-MEAN-DECISION<br/>GoldenMeanDecision<br/>[done]"]
  M_GOLDEN_MEAN_SWEEP["M-GOLDEN-MEAN-SWEEP<br/>GoldenMeanSweep<br/>[implemented]"]
  M_GUI_ABOUT["M-GUI-ABOUT<br/>AboutDialog<br/>[active]"]
  M_GUI_APPCONFIG["M-GUI-APPCONFIG<br/>AppConfigManager<br/>[pending]"]
  M_GUI_CANONICAL_BUTTONS["M-GUI-CANONICAL-BUTTONS<br/>CanonicalButtons<br/>[planned]"]
  M_GUI_DEBUG_DOCK["M-GUI-DEBUG-DOCK<br/>DebugDock<br/>[implemented]"]
  M_GUI_HELP_MENU["M-GUI-HELP-MENU<br/>HelpMenu<br/>[active]"]
  M_GUI_LOG_BRIDGE["M-GUI-LOG-BRIDGE<br/>LogBridge<br/>[implemented]"]
  M_GUI_MAIN["M-GUI-MAIN<br/>MainWindow<br/>[implemented]"]
  M_GUI_MARKER_MANAGER["M-GUI-MARKER-MANAGER<br/>MarkerManager<br/>[pending]"]
  M_GUI_MARKER_PANEL["M-GUI-MARKER-PANEL<br/>MarkerPanel<br/>[implemented]"]
  M_GUI_MENUBAR["M-GUI-MENUBAR<br/>MenuBar<br/>[pending]"]
  M_GUI_PIPELINE_CTRL["M-GUI-PIPELINE-CTRL<br/>PipelineController<br/>[active]"]
  M_GUI_PIPELINE_WORKER["M-GUI-PIPELINE-WORKER<br/>GuiPipelineWorker<br/>[active]"]
  M_GUI_PROJECT_CTRL["M-GUI-PROJECT-CTRL<br/>ProjectController<br/>[active]"]
  M_GUI_ROI_SELECTOR["M-GUI-ROI-SELECTOR<br/>RoiSelector<br/>[implemented]"]
  M_GUI_SETTINGS["M-GUI-SETTINGS<br/>SettingsDialog<br/>[implemented]"]
  M_GUI_SETTINGS_APP["M-GUI-SETTINGS-APP<br/>AppSettingsDialog<br/>[pending]"]
  M_GUI_SETTINGS_PROJECT["M-GUI-SETTINGS-PROJECT<br/>ProjectSettingsDialog<br/>[pending]"]
  M_GUI_SIGNAL_SPY["M-GUI-SIGNAL-SPY<br/>SignalSpy<br/>[implemented]"]
  M_GUI_SMART_SNAP["M-GUI-SMART-SNAP<br/>SmartSnap<br/>[pending]"]
  M_GUI_STATUS["M-GUI-STATUS<br/>StatusBarManager<br/>[implemented]"]
  M_GUI_SUBTITLE_EDITOR["M-GUI-SUBTITLE-EDITOR<br/>SubtitleEditor<br/>[implemented]"]
  M_GUI_SUBTITLE_OVERLAY["M-GUI-SUBTITLE-OVERLAY<br/>SubtitleOverlay<br/>[pending]"]
  M_GUI_TIMELINE["M-GUI-TIMELINE<br/>TimelineWidget<br/>[implemented]"]
  M_GUI_TIMELINE_CTRL["M-GUI-TIMELINE-CTRL<br/>TimelineController<br/>[active]"]
  M_GUI_TIMELINE_V2["M-GUI-TIMELINE-V2<br/>TimelineV2<br/>[pending]"]
  M_GUI_TIMELINE3["M-GUI-TIMELINE3<br/>Timeline3<br/>[implemented]"]
  M_GUI_UPDATE_CTRL["M-GUI-UPDATE-CTRL<br/>GuiUpdateController<br/>[implemented]"]
  M_GUI_VIDEOPLAYER["M-GUI-VIDEOPLAYER<br/>VideoPlayer<br/>[pending]"]
  M_GUI_WINDOW_UI["M-GUI-WINDOW-UI<br/>MainWindowUiBuilder<br/>[active]"]
  M_GUI_WORKER["M-GUI-WORKER<br/>Workers<br/>[implemented]"]
  M_LLM_CLIENT["M-LLM-CLIENT<br/>LlmClient<br/>[implemented]"]
  M_LLM_ORCHESTRATOR["M-LLM-ORCHESTRATOR<br/>LlmOrchestrator<br/>[implemented]"]
  M_MCP_ADAPTER["M-MCP-ADAPTER<br/>McpServiceAdapter<br/>[implemented]"]
  M_MCP_COMPOSITION["M-MCP-COMPOSITION<br/>McpComposition<br/>[implemented]"]
  M_MCP_OPERATIONS["M-MCP-OPERATIONS<br/>McpOperations<br/>[planned]"]
  M_MCP_READ_TOOLS["M-MCP-READ-TOOLS<br/>McpReadTools<br/>[planned]"]
  M_MCP_RELIABILITY["M-MCP-RELIABILITY<br/>McpReliability<br/>[planned]"]
  M_MCP_WRITE_TOOLS["M-MCP-WRITE-TOOLS<br/>McpWriteTools<br/>[planned]"]
  M_MD_EXPORT["M-MD-EXPORT<br/>MarkdownExport<br/>[implemented]"]
  M_MODELS["M-MODELS<br/>Models<br/>[implemented]"]
  M_NOTES["M-NOTES<br/>Notes<br/>[implemented]"]
  M_NOTES_PROCESSOR["M-NOTES-PROCESSOR<br/>NotesProcessor<br/>[implemented]"]
  M_OPERATION_REGISTRY["M-OPERATION-REGISTRY<br/>OperationRegistry<br/>[implemented]"]
  M_PERSIST_DETECTION["M-PERSIST-DETECTION<br/>DetectionConfigPersistence<br/>[active]"]
  M_PERSIST_DTO["M-PERSIST-DTO<br/>PersistenceDtoV2<br/>[implemented]"]
  M_PERSIST_MIGRATIONS["M-PERSIST-MIGRATIONS<br/>PersistenceMigrations<br/>[implemented]"]
  M_PHASE19_PLAN["M-PHASE19-PLAN<br/>Phase19Plan<br/>[done]"]
  M_PIPELINE["M-PIPELINE<br/>PipelineOrchestrator<br/>[implemented]"]
  M_PIPELINE_STATES["M-PIPELINE-STATES<br/>PipelineStates<br/>[partial]"]
  M_PORT_ALIGNMENT["M-PORT-ALIGNMENT<br/>AlignmentPort<br/>[implemented]"]
  M_PORT_DETECTOR["M-PORT-DETECTOR<br/>SlideDetectorPort<br/>[implemented]"]
  M_PORT_EVENTS["M-PORT-EVENTS<br/>EventBus<br/>[planned]"]
  M_PORT_EXPORT["M-PORT-EXPORT<br/>PresentationExporterPort<br/>[implemented]"]
  M_PORT_LLM["M-PORT-LLM<br/>LlmEnricherPort<br/>[planned]"]
  M_PORT_NOTES["M-PORT-NOTES<br/>NotesProcessorPort<br/>[implemented]"]
  M_PORT_PREVIEW["M-PORT-PREVIEW<br/>PreviewAnalyzerPort<br/>[implemented]"]
  M_PORT_REPO["M-PORT-REPO<br/>ProjectRepository<br/>[implemented]"]
  M_PPTX_EXPORT["M-PPTX-EXPORT<br/>PptxExport<br/>[implemented]"]
  M_PROJECT["M-PROJECT<br/>ProjectManager<br/>[implemented]"]
  M_PROJECT_MODEL["M-PROJECT-MODEL<br/>ProjectModel<br/>[implemented]"]
  M_PROJECT_VALIDATOR["M-PROJECT-VALIDATOR<br/>ProjectValidator<br/>[planned]"]
  M_ROI["M-ROI<br/>ROI<br/>[implemented]"]
  M_ROI_TOOL["M-ROI-TOOL<br/>RoiTool<br/>[implemented]"]
  M_SEGMENTER["M-SEGMENTER<br/>Segmenter<br/>[implemented]"]
  M_SLIDE_ANALYZER["M-SLIDE-ANALYZER<br/>SlideAnalyzer<br/>[implemented]"]
  M_SLIDE_DETECTOR["M-SLIDE-DETECTOR<br/>SlideDetector<br/>[implemented]"]
  M_STRUCTURED_ERRORS["M-STRUCTURED-ERRORS<br/>StructuredErrors<br/>[planned]"]
  M_SUBTITLES["M-SUBTITLES<br/>Subtitles<br/>[implemented]"]
  M_TIMELINE_MODEL["M-TIMELINE-MODEL<br/>TimelineModel<br/>[implemented]"]
  M_UI_STATE_READER["M-UI-STATE-READER<br/>UiStateReader<br/>[planned]"]
  M_UPDATE_CHECKER["M-UPDATE-CHECKER<br/>UpdateChecker<br/>[implemented]"]
  M_VIDEO_DECODE["M-VIDEO-DECODE<br/>VideoDecode<br/>[implemented]"]

  M_CLI -->|depends_on| M_CONFIG
  M_CLI -->|depends_on| M_DETECT_SLIDES
  M_CLI -->|depends_on| M_NOTES
  M_CLI -->|depends_on| M_ROI_TOOL
  M_CLI -->|depends_on| M_PROJECT
  M_CONFIG -->|depends_on| M_MODELS
  M_VIDEO_DECODE -->|depends_on| M_BACKENDS
  M_BACKENDS -->|depends_on| M_BACKEND_OPENCV
  M_BACKENDS -->|depends_on| M_BACKEND_PYAV
  M_ROI -->|depends_on| M_MODELS
  M_FRAME_FEATURES -->|depends_on| M_ROI
  M_SLIDE_DETECTOR -->|depends_on| M_FRAME_FEATURES
  M_SLIDE_DETECTOR -->|depends_on| M_ROI
  M_SLIDE_DETECTOR -->|depends_on| M_DETECT_METRICS
  M_SEGMENTER -->|depends_on| M_MODELS
  M_DEDUPE -->|depends_on| M_MODELS
  M_DEDUPE -->|depends_on| M_FRAME_FEATURES
  M_SUBTITLES -->|depends_on| M_MODELS
  M_MD_EXPORT -->|depends_on| M_MODELS
  M_PPTX_EXPORT -->|depends_on| M_MODELS
  M_PPTX_EXPORT -->|depends_on| M_NOTES_PROCESSOR
  M_NOTES_PROCESSOR -->|depends_on| M_MODELS
  M_DEBUG_EXPORT -->|depends_on| M_MODELS
  M_LLM_CLIENT -->|depends_on| M_CONFIG
  M_SLIDE_ANALYZER -->|depends_on| M_LLM_CLIENT
  M_SLIDE_ANALYZER -->|depends_on| M_MODELS
  M_LLM_ORCHESTRATOR -->|depends_on| M_LLM_CLIENT
  M_LLM_ORCHESTRATOR -->|depends_on| M_SLIDE_ANALYZER
  M_LLM_ORCHESTRATOR -->|depends_on| M_NOTES_PROCESSOR
  M_DETECT_SLIDES -->|depends_on| M_VIDEO_DECODE
  M_DETECT_SLIDES -->|depends_on| M_SLIDE_DETECTOR
  M_DETECT_SLIDES -->|depends_on| M_SEGMENTER
  M_DETECT_SLIDES -->|depends_on| M_DEDUPE
  M_DETECT_SLIDES -->|depends_on| M_ROI
  M_DETECT_SLIDES -->|depends_on| M_MODELS
  M_DETECT_SLIDES -->|depends_on| M_DETECT_METRICS
  M_NOTES -->|depends_on| M_MODELS
  M_NOTES -->|depends_on| M_SUBTITLES
  M_NOTES -->|depends_on| M_NOTES_PROCESSOR
  M_ROI_TOOL -->|depends_on| M_VIDEO_DECODE
  M_PROJECT -->|depends_on| M_MODELS
  M_PROJECT -->|depends_on| M_CONFIG
  M_PROJECT -->|depends_on| M_ATOMIC_JSON
  M_GUI_MAIN -->|depends_on| M_PROJECT
  M_GUI_MAIN -->|depends_on| M_GUI_TIMELINE3
  M_GUI_MAIN -->|depends_on| M_GUI_SETTINGS
  M_GUI_MAIN -->|depends_on| M_GUI_WORKER
  M_GUI_MAIN -->|depends_on| M_DETECT_SLIDES
  M_GUI_MAIN -->|depends_on| M_NOTES
  M_GUI_MAIN -->|depends_on| M_BACKENDS
  M_GUI_MAIN -->|depends_on| M_GUI_SETTINGS_PROJECT
  M_GUI_MAIN -->|depends_on| M_GUI_STATUS
  M_GUI_MAIN -->|depends_on| M_GUI_SUBTITLE_EDITOR
  M_GUI_TIMELINE -->|depends_on| M_MODELS
  M_GUI_SETTINGS -->|depends_on| M_PROJECT
  M_GUI_SETTINGS -->|depends_on| M_CONFIG
  M_GUI_SETTINGS -->|depends_on| M_BACKENDS
  M_GUI_SETTINGS -->|depends_on| M_NOTES_PROCESSOR
  M_GUI_WORKER -->|depends_on| M_DETECT_SLIDES
  M_GUI_WORKER -->|depends_on| M_NOTES
  M_GUI_WORKER -->|depends_on| M_LLM_ORCHESTRATOR
  M_GUI_WORKER -->|depends_on| M_PROJECT
  M_GUI_WORKER -->|depends_on| M_FRAME_FEATURES
  M_GUI_WORKER -->|depends_on| M_VIDEO_DECODE
  M_GUI_SUBTITLE_EDITOR -->|depends_on| M_LLM_CLIENT
  M_GUI_SUBTITLE_EDITOR -->|depends_on| M_CONFIG
  M_GUI_SUBTITLE_EDITOR -->|depends_on| M_PROJECT
  M_GUI_SMART_SNAP -->|depends_on| M_FRAME_FEATURES
  M_GUI_SMART_SNAP -->|depends_on| M_VIDEO_DECODE
  M_GUI_SMART_SNAP -->|depends_on| M_MODELS
  M_GUI_MARKER_MANAGER -->|depends_on| M_PROJECT
  M_GUI_MARKER_MANAGER -->|depends_on| M_GUI_SMART_SNAP
  M_GUI_SETTINGS_PROJECT -->|depends_on| M_CONFIG
  M_GUI_SETTINGS_PROJECT -->|depends_on| M_PROJECT
  M_GUI_SETTINGS_APP -->|depends_on| M_CONFIG
  M_GUI_SETTINGS_APP -->|depends_on| M_GUI_APPCONFIG
  M_GUI_SETTINGS_APP -->|depends_on| M_BACKENDS
  M_GUI_SUBTITLE_OVERLAY -->|depends_on| M_GUI_VIDEOPLAYER
  M_GUI_TIMELINE_V2 -->|depends_on| M_MODELS
  M_GUI_TIMELINE_V2 -->|depends_on| M_GUI_MARKER_MANAGER
  M_GUI_TIMELINE3 -->|depends_on| M_MODELS
  M_GUI_MENUBAR -->|depends_on| M_PROJECT
  M_GUI_MARKER_PANEL -->|depends_on| M_GUI_MARKER_MANAGER
  M_GUI_MARKER_PANEL -->|depends_on| M_PROJECT
  M_TIMELINE_MODEL -->|depends_on| M_MODELS
  M_PROJECT_MODEL -->|depends_on| M_PROJECT
  M_PROJECT_MODEL -->|depends_on| M_TIMELINE_MODEL
  M_GUI_DEBUG_DOCK -->|depends_on| M_GUI_LOG_BRIDGE
  M_GUI_DEBUG_DOCK -->|depends_on| M_TIMELINE_MODEL
  M_GUI_DEBUG_DOCK -->|depends_on| M_PROJECT_MODEL
  M_GUI_SIGNAL_SPY -->|depends_on| M_GUI_LOG_BRIDGE
  M_DEBUG_MCP -->|depends_on| M_PROJECT_MODEL
  M_DEBUG_MCP -->|depends_on| M_TIMELINE_MODEL
  M_DEBUG_MCP -->|depends_on| M_GUI_LOG_BRIDGE
  M_DEBUG_MCP -->|depends_on| M_DEBUG_ACTION
  M_COLAB -->|depends_on| M_PIPELINE
  M_COLAB -->|depends_on| M_PPTX_EXPORT
  M_APP_SERVICE -->|depends_on| M_DETECT_SLIDES
  M_APP_SERVICE -->|depends_on| M_AUTO_ALIGN
  M_APP_SERVICE -->|depends_on| M_NOTES
  M_APP_SERVICE -->|depends_on| M_MD_EXPORT
  M_APP_SERVICE -->|depends_on| M_PPTX_EXPORT
  M_APP_SERVICE -->|depends_on| M_PROJECT_VALIDATOR
  M_AUTO_ALIGN -->|depends_on| M_SUBTITLES
  M_AUTO_ALIGN -->|depends_on| M_MODELS
  M_CONFIRM_POLICY -->|depends_on| M_STRUCTURED_ERRORS
  M_MCP_OPERATIONS -->|depends_on| M_OPERATION_REGISTRY
  M_MCP_OPERATIONS -->|depends_on| M_APP_SERVICE
  M_MCP_OPERATIONS -->|depends_on| M_STRUCTURED_ERRORS
  M_MCP_OPERATIONS -->|depends_on| M_CONFIRM_POLICY
  M_MCP_READ_TOOLS -->|depends_on| M_PROJECT_MODEL
  M_MCP_READ_TOOLS -->|depends_on| M_TIMELINE_MODEL
  M_MCP_READ_TOOLS -->|depends_on| M_UI_STATE_READER
  M_MCP_WRITE_TOOLS -->|depends_on| M_MCP_OPERATIONS
  M_MCP_WRITE_TOOLS -->|depends_on| M_APP_SERVICE
  M_MCP_WRITE_TOOLS -->|depends_on| M_CANONICAL_COMMANDS
  M_UI_STATE_READER -->|depends_on| M_GUI_MAIN
  M_PROJECT_VALIDATOR -->|depends_on| M_PROJECT
  M_PROJECT_VALIDATOR -->|depends_on| M_MD_EXPORT
  M_PROJECT_VALIDATOR -->|depends_on| M_PPTX_EXPORT
  M_PIPELINE_STATES -->|depends_on| M_PROJECT
  M_CANONICAL_COMMANDS -->|depends_on| M_PROJECT_MODEL
  M_CANONICAL_COMMANDS -->|depends_on| M_APP_SERVICE
  M_GUI_PROJECT_CTRL -->|depends_on| M_APP_BOOTSTRAP
  M_GUI_PROJECT_CTRL -->|depends_on| M_DOMAIN_PROJECT
  M_GUI_PIPELINE_CTRL -->|depends_on| M_GUI_PIPELINE_WORKER
  M_GUI_PIPELINE_CTRL -->|depends_on| M_APP_BOOTSTRAP
  M_GUI_PIPELINE_CTRL -->|depends_on| M_APP_PREVIEW
  M_GUI_PIPELINE_CTRL -->|depends_on| M_APP_DETECT
  M_GUI_PIPELINE_CTRL -->|depends_on| M_APP_ALIGN
  M_GUI_PIPELINE_CTRL -->|depends_on| M_APP_NOTES
  M_GUI_PIPELINE_CTRL -->|depends_on| M_APP_EXPORT
  M_GUI_PIPELINE_CTRL -->|depends_on| M_APP_AUTO
  M_GUI_TIMELINE_CTRL -->|depends_on| M_APP_BOOTSTRAP
  M_GUI_TIMELINE_CTRL -->|depends_on| M_DOMAIN_PROJECT
  M_GUI_PIPELINE_WORKER -->|depends_on| M_APP_BOOTSTRAP
  M_GUI_WINDOW_UI -->|depends_on| M_GUI_MAIN
  M_GUI_WINDOW_UI -->|depends_on| M_GUI_MENUBAR
  M_GUI_WINDOW_UI -->|depends_on| M_GUI_VIDEOPLAYER
  M_GUI_WINDOW_UI -->|depends_on| M_GUI_TIMELINE3
  M_GUI_CANONICAL_BUTTONS -->|depends_on| M_GUI_MAIN
  M_GUI_CANONICAL_BUTTONS -->|depends_on| M_APP_SERVICE
  M_MCP_RELIABILITY -->|depends_on| M_DEBUG_MCP
  M_MCP_RELIABILITY -->|depends_on| M_OPERATION_REGISTRY
  M_E2E_RUNNER -->|depends_on| M_MCP_OPERATIONS
  M_E2E_RUNNER -->|depends_on| M_MCP_READ_TOOLS
  M_E2E_RUNNER -->|depends_on| M_E2E_SNAPSHOT
  M_E2E_SNAPSHOT -->|depends_on| M_MCP_READ_TOOLS
  M_E2E_SCENARIOS -->|depends_on| M_E2E_RUNNER
  M_E2E_SCENARIOS -->|depends_on| M_E2E_SNAPSHOT
  M_PERSIST_DETECTION -->|depends_on| M_DOMAIN_PROJECT
  M_PERSIST_DETECTION -->|depends_on| M_PERSIST_DTO
  M_GUI_ABOUT -->|depends_on| M_APP_IDENTITY
  M_GUI_HELP_MENU -->|depends_on| M_GUI_ABOUT
  M_GUI_HELP_MENU -->|depends_on| M_APP_IDENTITY
  M_DESKTOP_BOOTSTRAP -->|depends_on| M_GUI_MAIN
  M_DESKTOP_BOOTSTRAP -->|depends_on| M_APP_BOOTSTRAP
  M_DETECT_BENCHMARK -->|depends_on| M_DETECT_SLIDES
  M_DETECT_BENCHMARK -->|depends_on| M_DETECT_METRICS
  M_DETECT_PERF_DECISION -->|depends_on| M_DETECT_BENCHMARK
  M_DETECT_TARGET_DISCRIMINATION_R2 -->|depends_on| M_DETECT_PERF_DECISION
  M_DETECT_TARGET_DISCRIMINATION_R2 -->|depends_on| M_SLIDE_DETECTOR
  M_DETECT_TARGET_DISCRIMINATION_R2 -->|depends_on| M_SEGMENTER
  M_DETECT_TARGET_DISCRIMINATION_R2 -->|depends_on| M_BACKEND_PYAV
  M_ANALYSIS_SCALE -->|depends_on| M_CONFIG
  M_GOLDEN_MEAN_SWEEP -->|depends_on| M_ANALYSIS_SCALE
  M_GOLDEN_MEAN_SWEEP -->|depends_on| M_DETECT_SLIDES
  M_GOLDEN_MEAN_SWEEP -->|depends_on| M_DETECT_METRICS
  M_GOLDEN_MEAN_DECISION -->|depends_on| M_GOLDEN_MEAN_SWEEP
  M_PHASE19_PLAN -->|depends_on| M_DETECT_PERF_DECISION
  M_DOMAIN_PROJECT -->|depends_on| M_DOMAIN_VALUE
  M_DOMAIN_SLIDE -->|depends_on| M_DOMAIN_VALUE
  M_DOMAIN_EVENTS -->|depends_on| M_DOMAIN_VALUE
  M_ADAPTERS -->|depends_on| M_PORT_PREVIEW
  M_ADAPTERS -->|depends_on| M_PORT_DETECTOR
  M_ADAPTERS -->|depends_on| M_PORT_ALIGNMENT
  M_ADAPTERS -->|depends_on| M_PORT_NOTES
  M_ADAPTERS -->|depends_on| M_PORT_EXPORT
  M_MCP_ADAPTER -->|depends_on| M_MCP_COMPOSITION
  M_MCP_ADAPTER -->|depends_on| M_APP_PREVIEW
  M_MCP_ADAPTER -->|depends_on| M_APP_DETECT
  M_MCP_ADAPTER -->|depends_on| M_APP_ALIGN
  M_MCP_ADAPTER -->|depends_on| M_APP_NOTES
  M_MCP_ADAPTER -->|depends_on| M_APP_EXPORT
  M_MCP_ADAPTER -->|depends_on| M_APP_AUTO
  M_MCP_COMPOSITION -->|depends_on| M_ADAPTERS
  M_MCP_COMPOSITION -->|depends_on| M_FILE_REPO
  M_MCP_COMPOSITION -->|depends_on| M_APP_PREVIEW
  M_MCP_COMPOSITION -->|depends_on| M_APP_DETECT
  M_MCP_COMPOSITION -->|depends_on| M_APP_ALIGN
  M_MCP_COMPOSITION -->|depends_on| M_APP_NOTES
  M_MCP_COMPOSITION -->|depends_on| M_APP_EXPORT
  M_MCP_COMPOSITION -->|depends_on| M_APP_AUTO
  M_CLI_ADAPTER -->|depends_on| M_APP_BOOTSTRAP
  M_CLI_ADAPTER -->|depends_on| M_APP_PREVIEW
  M_CLI_ADAPTER -->|depends_on| M_APP_DETECT
  M_CLI_ADAPTER -->|depends_on| M_APP_ALIGN
  M_CLI_ADAPTER -->|depends_on| M_APP_NOTES
  M_CLI_ADAPTER -->|depends_on| M_APP_EXPORT
  M_CLI_ADAPTER -->|depends_on| M_APP_VALIDATE
  M_CLI_ADAPTER -->|depends_on| M_APP_AUTO
  M_APP_BOOTSTRAP -->|depends_on| M_FILE_REPO
  M_APP_BOOTSTRAP -->|depends_on| M_ADAPTERS
  M_APP_BOOTSTRAP -->|depends_on| M_APP_AUTO
  M_APP_LLM -->|depends_on| M_PORT_REPO
  M_APP_LLM -->|depends_on| M_PORT_LLM
  M_APP_LLM -->|depends_on| M_DOMAIN_PROJECT
  M_PORT_LLM -->|depends_on| M_DOMAIN_PROJECT
  M_APP_PROJECT -->|depends_on| M_DOMAIN_PROJECT
  M_APP_PROJECT -->|depends_on| M_PORT_REPO
  M_APP_DETECT -->|depends_on| M_DOMAIN_PROJECT
  M_APP_DETECT -->|depends_on| M_PORT_REPO
  M_APP_DETECT -->|depends_on| M_PORT_DETECTOR
  M_APP_ALIGN -->|depends_on| M_DOMAIN_PROJECT
  M_APP_ALIGN -->|depends_on| M_PORT_REPO
  M_APP_ALIGN -->|depends_on| M_PORT_ALIGNMENT
  M_APP_AUTO -->|depends_on| M_APP_DETECT
  M_APP_AUTO -->|depends_on| M_APP_ALIGN
  M_APP_AUTO -->|depends_on| M_APP_NOTES
  M_APP_AUTO -->|depends_on| M_APP_EXPORT
  M_APP_AUTO -->|depends_on| M_APP_VALIDATE
  M_APP_NOTES -->|depends_on| M_PORT_REPO
  M_APP_NOTES -->|depends_on| M_PORT_NOTES
  M_APP_NOTES -->|depends_on| M_DOMAIN_PROJECT
  M_APP_EXPORT -->|depends_on| M_PORT_REPO
  M_APP_EXPORT -->|depends_on| M_PORT_EXPORT
  M_APP_EXPORT -->|depends_on| M_DOMAIN_PROJECT
  M_APP_VALIDATE -->|depends_on| M_PORT_REPO
  M_APP_VALIDATE -->|depends_on| M_DOMAIN_PROJECT
  M_PORT_REPO -->|depends_on| M_DOMAIN_PROJECT
  M_PERSIST_DTO -->|depends_on| M_DOMAIN_VALUE
  M_PERSIST_MIGRATIONS -->|depends_on| M_PERSIST_DTO
  M_PERSIST_MIGRATIONS -->|depends_on| M_DOMAIN_VALUE
  M_FILE_REPO -->|depends_on| M_PORT_REPO
  M_FILE_REPO -->|depends_on| M_PERSIST_DTO
  M_FILE_REPO -->|depends_on| M_PERSIST_MIGRATIONS
  M_FILE_REPO -->|depends_on| M_DOMAIN_PROJECT
  M_PORT_PREVIEW -->|depends_on| M_DOMAIN_VALUE
  M_PORT_DETECTOR -->|depends_on| M_DOMAIN_VALUE
  M_PORT_ALIGNMENT -->|depends_on| M_DOMAIN_PROJECT
  M_PORT_NOTES -->|depends_on| M_DOMAIN_PROJECT
  M_PORT_EXPORT -->|depends_on| M_DOMAIN_PROJECT
  M_APP_PREVIEW -->|depends_on| M_PORT_REPO
  M_APP_PREVIEW -->|depends_on| M_PORT_PREVIEW
  M_APP_PREVIEW -->|depends_on| M_DOMAIN_PROJECT
  M_PORT_EVENTS -->|depends_on| M_DOMAIN_EVENTS
  M_UPDATE_CHECKER -->|depends_on| M_APP_IDENTITY
  M_GUI_UPDATE_CTRL -->|depends_on| M_UPDATE_CHECKER
  M_GUI_UPDATE_CTRL -->|depends_on| M_GUI_APPCONFIG
  M_LLM_ORCHESTRATOR -->|depends_on| M_MODELS
  M_GUI_MAIN -->|depends_on| M_GUI_TIMELINE
  M_GUI_UPDATE_CTRL -->|depends_on| M_APP_IDENTITY
  M_APP_BOOTSTRAP -->|depends_on| M_APP_PROJECT
  M_APP_BOOTSTRAP -->|depends_on| M_APP_LLM
  M_BACKEND_PYAV -->|depends_on| M_BACKENDS
  M_BACKEND_PYAV -->|depends_on| M_VIDEO_DECODE
```
