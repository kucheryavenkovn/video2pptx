# GRACE graphs (generated)

Source artifacts:

- `requirements`: `D:/git/video2pptx/docs/requirements.xml` — **OK**
- `development_plan`: `D:/git/video2pptx/docs/development-plan.xml` — **OK**
- `knowledge_graph`: `D:/git/video2pptx/docs/knowledge-graph.xml` — **OK**
- `verification_plan`: `D:/git/video2pptx/docs/verification-plan.xml` — **OK**
- `technology`: `D:/git/video2pptx/docs/technology.xml` — **OK**
- `operational_packets`: `D:/git/video2pptx/docs/operational-packets.xml` — **OK**

Modules: **125** · depends: **258** · V-M: **66** · UC: **17** · Phases: **20** · Steps: **97**

Regenerate (DOT + PNG + SVG + Mermaid):

```powershell
python tools/grace_graphs/generate_grace_graphs.py --project-root .
```

PNG/SVG require [Graphviz](https://graphviz.org/) (`dot` on PATH).

## Diagrams

### overview

- Graphviz DOT: [`dot/overview.dot`](dot/overview.dot)
- SVG: [`svg/overview.svg`](svg/overview.svg)
- PNG: [`png/overview.png`](png/overview.png)

![GRACE Overview](png/overview.png)

- Mermaid: [`mermaid/overview.mmd`](mermaid/overview.mmd)
- Mermaid (preview): [`mermaid/overview.md`](mermaid/overview.md)

**GRACE Overview** — nodes=8 edges=7

```mermaid
%% GRACE Overview
flowchart TB
  CriticalFlows["CriticalFlows<br/>18"]
  CrossLinks["CrossLinks<br/>187"]
  DataFlows["DataFlows<br/>26"]
  DependsEdges["depends_on<br/>258"]
  Modules["Modules<br/>125"]
  Phases["Phases<br/>20"]
  UseCases["UseCases<br/>17"]
  Verifications["Verifications<br/>66"]

  Modules -->|has| DependsEdges
  Modules -->|verified_by| Verifications
  Modules -->|linked| CrossLinks
  UseCases -->|related| DataFlows
  UseCases -->|covered_by| CriticalFlows
  Phases -->|implements| Modules
  CriticalFlows -->|checks| Verifications
```

### modules-deps

- Graphviz DOT: [`dot/modules-deps.dot`](dot/modules-deps.dot)
- SVG: [`svg/modules-deps.svg`](svg/modules-deps.svg)
- PNG: [`png/modules-deps.png`](png/modules-deps.png)

![GRACE Module Dependencies](png/modules-deps.png)

- Mermaid: [`mermaid/modules-deps.mmd`](mermaid/modules-deps.mmd)
- Mermaid (preview): [`mermaid/modules-deps.md`](mermaid/modules-deps.md)

**GRACE Module Dependencies** — nodes=125 edges=256

_Large graph (125 nodes) — open Mermaid / SVG / PNG._

### modules-deps-core

- Graphviz DOT: [`dot/modules-deps-core.dot`](dot/modules-deps-core.dot)
- SVG: [`svg/modules-deps-core.svg`](svg/modules-deps-core.svg)
- PNG: [`png/modules-deps-core.png`](png/modules-deps-core.png)

![GRACE Module Dependencies](png/modules-deps-core.png)

- Mermaid: [`mermaid/modules-deps-core.mmd`](mermaid/modules-deps-core.mmd)
- Mermaid (preview): [`mermaid/modules-deps-core.md`](mermaid/modules-deps-core.md)

**GRACE Module Dependencies** — nodes=40 edges=44

```mermaid
%% GRACE Module Dependencies
flowchart LR
  M_ADAPTERS["M-ADAPTERS<br/>LegacyPortAdapters<br/>[implemented]"]
  M_ANALYSIS_SCALE["M-ANALYSIS-SCALE<br/>AnalysisScale<br/>[implemented]"]
  M_APP_ALIGN["M-APP-ALIGN<br/>AlignmentService<br/>[implemented]"]
  M_APP_AUTO["M-APP-AUTO<br/>AutoService<br/>[implemented]"]
  M_APP_BOOTSTRAP["M-APP-BOOTSTRAP<br/>ApplicationServicesBootstrap<br/>[active]"]
  M_APP_DETECT["M-APP-DETECT<br/>DetectionService<br/>[implemented]"]
  M_APP_ERRORS["M-APP-ERRORS<br/>"]
  M_APP_EXPORT["M-APP-EXPORT<br/>ExportService<br/>[implemented]"]
  M_APP_IDENTITY["M-APP-IDENTITY<br/>ApplicationIdentity<br/>[active]"]
  M_APP_INPUT_RESOLVER["M-APP-INPUT-RESOLVER<br/>InputResolver<br/>[active]"]
  M_APP_LLM["M-APP-LLM<br/>LlmEnrichmentService<br/>[planned]"]
  M_APP_NOTES["M-APP-NOTES<br/>NotesService<br/>[implemented]"]
  M_APP_PREVIEW["M-APP-PREVIEW<br/>PreviewService<br/>[implemented]"]
  M_APP_PROJECT["M-APP-PROJECT<br/>ProjectService<br/>[planned]"]
  M_APP_SERVICE["M-APP-SERVICE<br/>AppService<br/>[partial]"]
  M_APP_SERVICE_CONTEXT["M-APP-SERVICE-CONTEXT<br/>"]
  M_APP_VALIDATE["M-APP-VALIDATE<br/>ValidationService<br/>[implemented]"]
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

  M_CLI -->|depends_on| M_CONFIG
  M_CLI -->|depends_on| M_DETECT_SLIDES
  M_BACKENDS -->|depends_on| M_BACKEND_OPENCV
  M_BACKENDS -->|depends_on| M_BACKEND_PYAV
  M_DETECT_SLIDES -->|depends_on| M_DEDUPE
  M_DETECT_SLIDES -->|depends_on| M_DETECT_METRICS
  M_DEBUG_MCP -->|depends_on| M_DEBUG_ACTION
  M_APP_SERVICE -->|depends_on| M_DETECT_SLIDES
  M_APP_SERVICE -->|depends_on| M_AUTO_ALIGN
  M_CANONICAL_COMMANDS -->|depends_on| M_APP_SERVICE
  M_APP_INPUT_RESOLVER -->|depends_on| M_APP_ERRORS
  M_DESKTOP_BOOTSTRAP -->|depends_on| M_APP_BOOTSTRAP
  M_DETECT_BENCHMARK -->|depends_on| M_DETECT_SLIDES
  M_DETECT_BENCHMARK -->|depends_on| M_DETECT_METRICS
  M_DETECT_PERF_DECISION -->|depends_on| M_DETECT_BENCHMARK
  M_DETECT_TARGET_DISCRIMINATION_R2 -->|depends_on| M_DETECT_PERF_DECISION
  M_DETECT_TARGET_DISCRIMINATION_R2 -->|depends_on| M_BACKEND_PYAV
  M_ANALYSIS_SCALE -->|depends_on| M_CONFIG
  M_CLI_ADAPTER -->|depends_on| M_APP_BOOTSTRAP
  M_CLI_ADAPTER -->|depends_on| M_APP_PREVIEW
  M_CLI_ADAPTER -->|depends_on| M_APP_DETECT
  M_CLI_ADAPTER -->|depends_on| M_APP_ALIGN
  M_CLI_ADAPTER -->|depends_on| M_APP_NOTES
  M_CLI_ADAPTER -->|depends_on| M_APP_EXPORT
  M_CLI_ADAPTER -->|depends_on| M_APP_VALIDATE
  M_CLI_ADAPTER -->|depends_on| M_APP_AUTO
  M_APP_BOOTSTRAP -->|depends_on| M_ADAPTERS
  M_APP_BOOTSTRAP -->|depends_on| M_APP_AUTO
  M_APP_LLM -->|depends_on| M_DOMAIN_PROJECT
  M_APP_PROJECT -->|depends_on| M_DOMAIN_PROJECT
  M_APP_DETECT -->|depends_on| M_DOMAIN_PROJECT
  M_APP_ALIGN -->|depends_on| M_DOMAIN_PROJECT
  M_APP_AUTO -->|depends_on| M_APP_DETECT
  M_APP_AUTO -->|depends_on| M_APP_ALIGN
  M_APP_AUTO -->|depends_on| M_APP_NOTES
  M_APP_AUTO -->|depends_on| M_APP_EXPORT
  M_APP_AUTO -->|depends_on| M_APP_VALIDATE
  M_APP_NOTES -->|depends_on| M_DOMAIN_PROJECT
  M_APP_EXPORT -->|depends_on| M_DOMAIN_PROJECT
  M_APP_VALIDATE -->|depends_on| M_DOMAIN_PROJECT
  M_APP_PREVIEW -->|depends_on| M_DOMAIN_PROJECT
  M_APP_BOOTSTRAP -->|depends_on| M_APP_PROJECT
  M_APP_BOOTSTRAP -->|depends_on| M_APP_LLM
  M_BACKEND_PYAV -->|depends_on| M_BACKENDS
```

### modules-verification

- Graphviz DOT: [`dot/modules-verification.dot`](dot/modules-verification.dot)
- SVG: [`svg/modules-verification.svg`](svg/modules-verification.svg)
- PNG: [`png/modules-verification.png`](png/modules-verification.png)

![GRACE Modules ↔ Verification](png/modules-verification.png)

- Mermaid: [`mermaid/modules-verification.mmd`](mermaid/modules-verification.mmd)
- Mermaid (preview): [`mermaid/modules-verification.md`](mermaid/modules-verification.md)

**GRACE Modules ↔ Verification** — nodes=262 edges=160

_Large graph (262 nodes) — open Mermaid / SVG / PNG._

### use-cases-flows

- Graphviz DOT: [`dot/use-cases-flows.dot`](dot/use-cases-flows.dot)
- SVG: [`svg/use-cases-flows.svg`](svg/use-cases-flows.svg)
- PNG: [`png/use-cases-flows.png`](png/use-cases-flows.png)

![GRACE Use Cases ↔ Flows](png/use-cases-flows.png)

- Mermaid: [`mermaid/use-cases-flows.mmd`](mermaid/use-cases-flows.mmd)
- Mermaid (preview): [`mermaid/use-cases-flows.md`](mermaid/use-cases-flows.md)

**GRACE Use Cases ↔ Flows** — nodes=62 edges=51

```mermaid
%% GRACE Use Cases ↔ Flows
flowchart LR
  DF_001["DF-001<br/>DetectPipeline"]
  DF_002["DF-002<br/>ExportMDPipeline"]
  DF_003["DF-003<br/>LlmProcessPipeline"]
  DF_004["DF-004<br/>NotesPipeline"]
  DF_005["DF-005<br/>DetectSlidesPipeline"]
  DF_006["DF-006<br/>RoiToolFlow"]
  DF_007["DF-007<br/>CreateProject"]
  DF_008["DF-008<br/>DetectInProject"]
  DF_009["DF-009<br/>ViewTimeline"]
  DF_010["DF-010<br/>LLMProcessInGUI"]
  DF_011["DF-011<br/>ProjectLifecycleMenu"]
  DF_012["DF-012<br/>SettingsConfiguration"]
  DF_013["DF-013<br/>VideoPlayback"]
  DF_014["DF-014<br/>TimelineGreenMarkers"]
  DF_015["DF-015<br/>TimelineBlueMarkers"]
  DF_APP_01["DF-APP-01<br/>RevisionSafeApplicationUseCase"]
  DF_CLI_ADAPTER["DF-CLI-ADAPTER<br/>CliApplicationDispatch"]
  DF_E2E_01["DF-E2E-01<br/>McpWriteOperationLifecycle"]
  DF_E2E_02["DF-E2E-02<br/>CanonicalDetectStage"]
  DF_E2E_03["DF-E2E-03<br/>AutoPipelineModes"]
  DF_E2E_04["DF-E2E-04<br/>AutoAlignCoordinated"]
  DF_E2E_05["DF-E2E-05<br/>VerificationStepProtocol"]
  DF_GUI_PIPELINE["DF-GUI-PIPELINE<br/>GuiPipelineFlow"]
  DF_GUI_PROJECT["DF-GUI-PROJECT<br/>GuiProjectFlow"]
  DF_GUI_TIMELINE["DF-GUI-TIMELINE<br/>GuiTimelineFlow"]
  DF_PERSIST_01["DF-PERSIST-01<br/>CanonicalProjectLoadSave"]
  Phase_20["Phase-20"]
  UC_001["UC-001<br/>Runs video2pptx detect with video + subtitles (all-in-one)"]
  UC_002["UC-002<br/>Runs video2pptx export-md with slides.json"]
  UC_003["UC-003<br/>Applies --debug flag during detect"]
  UC_004["UC-004<br/>Runs video2pptx llm-process with slides.json + slides images"]
  UC_005["UC-005<br/>Runs video2pptx detect-slides with video only (no subtitles)"]
  UC_006["UC-006<br/>Runs video2pptx notes with slides.json + subtitles"]
  UC_007["UC-007<br/>Runs video2pptx roi-tool with a video file"]
  UC_008["UC-008<br/>Creates a new project via CLI or GUI"]
  UC_009["UC-009<br/>Opens an existing project and runs slide detection via GUI"]
  UC_010["UC-010<br/>Views detected slides on a timeline and inspects subtitle te"]
  UC_011["UC-011<br/>Opens Settings dialog and edits LLM system prompt"]
  UC_012["UC-012<br/>Selects GPU/decoder backend in Settings"]
  UC_013["UC-013<br/>Uses menu bar: File > New/Open/Close/Save Project, Import Vi"]
  UC_014["UC-014<br/>Opens Project Settings and App Settings from Edit menu"]
  UC_015["UC-015<br/>Plays video with subtitle overlay in GUI, controls playback "]
  UC_016["UC-016<br/>Views green detected markers on timeline, clicks to open sli"]
  UC_017["UC-017<br/>Chooses analysis quality in Project Settings (fast / detaile"]
  VF_001["VF-001<br/>DetectHappyPath"]
  VF_002["VF-002<br/>ExportMDPath"]
  VF_003["VF-003<br/>GPUAutoFallback"]
  VF_004["VF-004<br/>ExportPptxPath"]
  VF_005["VF-005<br/>NotesProcessingPath"]
  VF_006["VF-006<br/>DetectSlidesNoSubtitles"]
  VF_007["VF-007<br/>NotesPostProcess"]
  VF_008["VF-008<br/>RoiToolVisualSelect"]
  VF_009["VF-009<br/>ProjectCreateOpen"]
  VF_010["VF-010<br/>DetectInProject"]
  VF_011["VF-011<br/>TimelineInteraction"]
  VF_012["VF-012<br/>SettingsLLMPrompt"]
  VF_013["VF-013<br/>BackendSelection"]
  VF_014["VF-014<br/>MenuBarActions"]
  VF_015["VF-015<br/>ProjectAppSettings"]
  VF_016["VF-016<br/>VideoPlaybackSubtitles"]
  VF_017["VF-017<br/>TimelineGreenBlueMarkers"]
  VF_018["VF-018<br/>SmartSnapModes"]

  UC_001 -->|related_flow| DF_001
  UC_002 -->|related_flow| DF_002
  UC_004 -->|related_flow| DF_003
  UC_005 -->|related_flow| DF_005
  UC_006 -->|related_flow| DF_004
  UC_008 -->|related_flow| DF_007
  UC_009 -->|related_flow| DF_008
  UC_010 -->|related_flow| DF_009
  UC_011 -->|related_flow| DF_010
  UC_013 -->|related_flow| DF_011
  UC_014 -->|related_flow| DF_012
  UC_015 -->|related_flow| DF_013
  UC_016 -->|related_flow| DF_014
  UC_016 -->|related_flow| DF_015
  UC_017 -->|related_flow| Phase_20
  VF_001 -->|uses| UC_001
  VF_001 -->|data_flow| DF_001
  VF_002 -->|uses| UC_002
  VF_002 -->|data_flow| DF_002
  VF_003 -->|uses| UC_001
  VF_003 -->|data_flow| DF_001
  VF_004 -->|uses| UC_002
  VF_004 -->|data_flow| DF_002
  VF_005 -->|uses| UC_001
  VF_005 -->|data_flow| DF_002
  VF_006 -->|uses| UC_005
  VF_006 -->|data_flow| DF_005
  VF_007 -->|uses| UC_006
  VF_007 -->|data_flow| DF_004
  VF_008 -->|uses| UC_007
  VF_008 -->|data_flow| DF_006
  VF_009 -->|uses| UC_008
  VF_009 -->|data_flow| DF_007
  VF_010 -->|uses| UC_009
  VF_010 -->|data_flow| DF_008
  VF_011 -->|uses| UC_010
  VF_011 -->|data_flow| DF_009
  VF_012 -->|uses| UC_011
  VF_012 -->|data_flow| DF_010
  VF_013 -->|uses| UC_012
  VF_014 -->|uses| UC_013
  VF_014 -->|data_flow| DF_011
  VF_015 -->|uses| UC_014
  VF_015 -->|data_flow| DF_012
  VF_016 -->|uses| UC_015
  VF_016 -->|data_flow| DF_013
  VF_017 -->|uses| UC_016
  VF_017 -->|data_flow| DF_014
  VF_017 -->|data_flow| DF_015
  VF_018 -->|uses| UC_016
  VF_018 -->|data_flow| DF_015
```

### phases-steps

- Graphviz DOT: [`dot/phases-steps.dot`](dot/phases-steps.dot)
- SVG: [`svg/phases-steps.svg`](svg/phases-steps.svg)
- PNG: [`png/phases-steps.png`](png/phases-steps.png)

![GRACE Phases and Steps](png/phases-steps.png)

- Mermaid: [`mermaid/phases-steps.mmd`](mermaid/phases-steps.mmd)
- Mermaid (preview): [`mermaid/phases-steps.md`](mermaid/phases-steps.md)

**GRACE Phases and Steps** — nodes=184 edges=183

_Large graph (184 nodes) — open Mermaid / SVG / PNG._

### cross-links

- Graphviz DOT: [`dot/cross-links.dot`](dot/cross-links.dot)
- SVG: [`svg/cross-links.svg`](svg/cross-links.svg)
- PNG: [`png/cross-links.png`](png/cross-links.png)

![GRACE CrossLinks (knowledge-graph)](png/cross-links.png)

- Mermaid: [`mermaid/cross-links.mmd`](mermaid/cross-links.mmd)
- Mermaid (preview): [`mermaid/cross-links.md`](mermaid/cross-links.md)

**GRACE CrossLinks (knowledge-graph)** — nodes=38 edges=80

```mermaid
%% GRACE CrossLinks (knowledge-graph)
flowchart LR
  M_BACKENDS["M-BACKENDS"]
  M_CLI["M-CLI"]
  M_CONFIG["M-CONFIG"]
  M_DEBUG_EXPORT["M-DEBUG-EXPORT"]
  M_DEDUPE["M-DEDUPE"]
  M_DETECT_METRICS["M-DETECT-METRICS"]
  M_DETECT_PERF_DECISION["M-DETECT-PERF-DECISION"]
  M_DETECT_SLIDES["M-DETECT-SLIDES"]
  M_FRAME_FEATURES["M-FRAME-FEATURES"]
  M_GUI_APPCONFIG["M-GUI-APPCONFIG"]
  M_GUI_MAIN["M-GUI-MAIN"]
  M_GUI_MARKER_PANEL["M-GUI-MARKER-PANEL"]
  M_GUI_MENUBAR["M-GUI-MENUBAR"]
  M_GUI_SETTINGS["M-GUI-SETTINGS"]
  M_GUI_SETTINGS_PROJECT["M-GUI-SETTINGS-PROJECT"]
  M_GUI_STATUS["M-GUI-STATUS"]
  M_GUI_SUBTITLE_EDITOR["M-GUI-SUBTITLE-EDITOR"]
  M_GUI_SUBTITLE_OVERLAY["M-GUI-SUBTITLE-OVERLAY"]
  M_GUI_TIMELINE["M-GUI-TIMELINE"]
  M_GUI_TIMELINE3["M-GUI-TIMELINE3"]
  M_GUI_VIDEOPLAYER["M-GUI-VIDEOPLAYER"]
  M_GUI_WORKER["M-GUI-WORKER"]
  M_LLM_CLIENT["M-LLM-CLIENT"]
  M_LLM_ORCHESTRATOR["M-LLM-ORCHESTRATOR"]
  M_MD_EXPORT["M-MD-EXPORT"]
  M_MODELS["M-MODELS"]
  M_NOTES["M-NOTES"]
  M_NOTES_PROCESSOR["M-NOTES-PROCESSOR"]
  M_PIPELINE["M-PIPELINE"]
  M_PPTX_EXPORT["M-PPTX-EXPORT"]
  M_PROJECT["M-PROJECT"]
  M_ROI["M-ROI"]
  M_ROI_TOOL["M-ROI-TOOL"]
  M_SEGMENTER["M-SEGMENTER"]
  M_SLIDE_ANALYZER["M-SLIDE-ANALYZER"]
  M_SLIDE_DETECTOR["M-SLIDE-DETECTOR"]
  M_SUBTITLES["M-SUBTITLES"]
  M_VIDEO_DECODE["M-VIDEO-DECODE"]

  M_CLI -->|reads config, passes to pipeline| M_CONFIG
  M_CLI -->|orchestrates| M_VIDEO_DECODE
  M_CLI -->|orchestrates| M_SLIDE_DETECTOR
  M_CLI -->|orchestrates| M_SEGMENTER
  M_CLI -->|orchestrates| M_SUBTITLES
  M_CLI -->|orchestrates| M_MD_EXPORT
  M_CLI -->|orchestrates| M_PPTX_EXPORT
  M_CLI -->|orchestrates| M_DEDUPE
  M_CLI -->|orchestrates| M_ROI
  M_CLI -->|orchestrates via slide_detector| M_FRAME_FEATURES
  M_CLI -->|orchestrates| M_DEBUG_EXPORT
  M_CLI -->|orchestrates for notes| M_NOTES_PROCESSOR
  M_CLI -->|orchestrates for llm-process| M_LLM_CLIENT
  M_CLI -->|orchestrates for llm-process| M_LLM_ORCHESTRATOR
  M_CLI -->|orchestrates for llm-process and notes| M_SLIDE_ANALYZER
  M_CLI -->|delegates detect-slides command| M_DETECT_SLIDES
  M_CLI -->|delegates notes command| M_NOTES
  M_CLI -->|delegates roi-tool command| M_ROI_TOOL
  M_CLI -->|delegates project subcommands| M_PROJECT
  M_PROJECT -->|uses Project model| M_MODELS
  M_PROJECT -->|uses LlmConfig, DetectionConfig| M_CONFIG
  M_PIPELINE -->|implements| M_CLI
  M_VIDEO_DECODE -->|selects and uses| M_BACKENDS
  M_SLIDE_DETECTOR -->|extracts and compares| M_FRAME_FEATURES
  M_SLIDE_DETECTOR -->|crops and masks| M_ROI
  M_SEGMENTER -->|deduplicates after segmentation| M_DEDUPE
  M_DEDUPE -->|uses for comparison| M_FRAME_FEATURES
  M_MD_EXPORT -->|reads SlidesDocument| M_MODELS
  M_PPTX_EXPORT -->|reads SlidesDocument| M_MODELS
  M_PPTX_EXPORT -->|uses for notes cleanup| M_NOTES_PROCESSOR
  M_DEBUG_EXPORT -->|reads SlideSegment| M_MODELS
  M_SLIDE_ANALYZER -->|uses for vision calls| M_LLM_CLIENT
  M_LLM_ORCHESTRATOR -->|loads/unloads model| M_LLM_CLIENT
  M_LLM_ORCHESTRATOR -->|calls for each slide| M_SLIDE_ANALYZER
  M_LLM_ORCHESTRATOR -->|uses for transcript rephrase| M_NOTES_PROCESSOR
  M_DETECT_SLIDES -->|uses for frame iteration| M_VIDEO_DECODE
  M_DETECT_SLIDES -->|uses for change detection| M_SLIDE_DETECTOR
  M_DETECT_SLIDES -->|builds intervals| M_SEGMENTER
  M_DETECT_SLIDES -->|deduplicates| M_DEDUPE
  M_DETECT_SLIDES -->|crops and masks| M_ROI
  M_DETECT_SLIDES -->|Phase-18 TwoPassDetection: 3-to-2 passes…| M_DETECT_PERF_DECISION
  M_DETECT_PERF_DECISION -->|Phase-18 TwoPassDetection: baseline iden…| M_DETECT_METRICS
  M_NOTES -->|parses and aligns cues| M_SUBTITLES
  M_NOTES -->|cleans and formats notes| M_NOTES_PROCESSOR
  M_ROI_TOOL -->|extracts frame| M_VIDEO_DECODE
  M_GUI_MAIN -->|controls project lifecycle| M_PROJECT
  M_GUI_MAIN -->|embeds and populates| M_GUI_TIMELINE
  M_GUI_MAIN -->|opens settings dialog| M_GUI_SETTINGS
  M_GUI_MAIN -->|creates and starts workers| M_GUI_WORKER
  M_GUI_MAIN -->|calls via worker| M_DETECT_SLIDES
  M_GUI_MAIN -->|calls via worker| M_NOTES
  M_GUI_MAIN -->|queries available backends| M_BACKENDS
  M_GUI_MAIN -->|creates and shows marker panel| M_GUI_MARKER_PANEL
  M_GUI_MAIN -->|opens project settings dialog| M_GUI_SETTINGS_PROJECT
  M_GUI_MAIN -->|embeds TimelineWidget (V3 multi-track)| M_GUI_TIMELINE3
  M_GUI_MAIN -->|uses StatusBarManager for progress displ…| M_GUI_STATUS
  M_GUI_MAIN -->|opens SubtitleEditorDialog on context me…| M_GUI_SUBTITLE_EDITOR
  M_GUI_TIMELINE3 -->|reads SlideSegment list, SlideSegment.ma…| M_MODELS
  M_GUI_TIMELINE3 -->|emits signals for add_manual_slide, seek…| M_GUI_MAIN
  M_GUI_TIMELINE3 -->|uses quick_extract/quick_visual_distance…| M_FRAME_FEATURES
  M_GUI_WORKER -->|QuickDetectWorker uses quick_mode=True f…| M_DETECT_SLIDES
  M_GUI_WORKER -->|QuickDetectWorker uses quick_extract/qui…| M_FRAME_FEATURES
  M_GUI_WORKER -->|reads notes_mode config| M_GUI_APPCONFIG
  M_GUI_STATUS -->|attached to MainWindow.statusBar()| M_GUI_MAIN
  M_GUI_TIMELINE -->|reads SlideSegment list| M_MODELS
  M_GUI_SETTINGS -->|reads/writes project config| M_PROJECT
  M_GUI_SETTINGS -->|reads LlmConfig, DetectionConfig default…| M_CONFIG
  M_GUI_SETTINGS -->|queries available backends| M_BACKENDS
  M_GUI_SETTINGS -->|shows SYSTEM_PROMPT_REPHRASE| M_NOTES_PROCESSOR
  M_GUI_WORKER -->|runs detection in background thread| M_DETECT_SLIDES
  M_GUI_WORKER -->|runs notes in background thread| M_NOTES
  M_GUI_WORKER -->|runs LLM processing in background thread| M_LLM_ORCHESTRATOR
  M_GUI_WORKER -->|updates project state on completion| M_PROJECT
  M_GUI_WORKER -->|PreviewWorker uses for fast frame iterat…| M_VIDEO_DECODE
  M_GUI_WORKER -->|PreviewWorker uses for scoring| M_FRAME_FEATURES
  M_GUI_MENUBAR -->|sends project lifecycle commands| M_PROJECT
  M_GUI_MENUBAR -->|installed in MainWindow menuBar()| M_GUI_MAIN
  M_GUI_VIDEOPLAYER -->|emits positionChanged for sync| M_GUI_SUBTITLE_OVERLAY
  M_GUI_VIDEOPLAYER -->|embedded in central area| M_GUI_MAIN
  M_GUI_SUBTITLE_OVERLAY -->|positioned over QVideoWidget| M_GUI_VIDEOPLAYER
```

