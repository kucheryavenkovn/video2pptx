# video2pptx — Product Roadmap and Current Direction

## Purpose of this document

This is a **human-readable** representation of how the `video2pptx` product
develops over time.

- It explains the development of the project through **user-visible results**,
  not through internal module counts or lint counters.
- It **does not replace** `docs/development-plan.xml`.
- It **does not replace** `docs/requirements.xml`.
- It **does not replace** `docs/verification-plan.xml`.
- It **does not replace** `docs/knowledge-graph.xml`.
- Exact technical statuses, module dependencies, and verification gates live in
  the GRACE artifacts listed above.
- Whenever this Markdown disagrees with the technical data, the **current
  GRACE artifacts and their evidence are the single source of truth**.

This roadmap is updated after a **change of product direction** or after a
**meaningful accepted result**. It is **not** updated after every change of
lint counters, autonomy counters, or intermediate verification iterations —
those values are volatile and must be read dynamically through
`/project-status`.

---

## 1. Product Promise

The user provides a video recording and, when available, subtitles. The
application:

1. Detects slide intervals automatically.
2. Extracts representative images for each interval.
3. Links each interval to the matching speech fragment by timestamps.
4. Produces a presentation or a structured set of notes that the user can
   review, correct, and export.

In short: **video + subtitles → slides, transcript segments, and an exportable
presentation.**

---

## 2. Primary User Journey

```text
Video and subtitles
→ create or open a project
→ automatic slide detection
→ review and correct the result
→ process notes
→ export to Markdown or PPTX
→ reopen the project later without losing state
```

Everything between "create project" and "reopen project" must be reproducible
and lossless. The user must not need to redo detection, alignment, or export
just because they closed the window.

---

## 3. Product Evolution

The product grew through several stages. Each stage delivered a concrete
user-visible result; later stages build on top of earlier ones.

### Basic CLI Pipeline

The first usable form of the product. It delivered:

- video decoding;
- finding visual changes between frames;
- building slide intervals from those changes;
- saving representative screenshots for each interval;
- processing subtitles (SRT / VTT);
- exporting the result to Markdown (Marp) and PPTX.

**User-visible result of this stage:**

> A user can run a command on a video with subtitles and receive a Markdown
> deck, a PPTX deck, and a set of slide images describing what was shown on
> screen.

### Projects and Persistence

Turning a one-shot script into a resumable workflow. It introduced:

- `project.json` as the canonical source of truth for a project;
- persistent storage of video path, subtitle path, detection settings, and
  pipeline state;
- the ability to close a project and reopen it later;
- the ability to rerun only the operation the user actually needs (e.g. only
  re-export, only re-align), without redoing the whole pipeline.

**User-visible result of this stage:**

> The user can stop work and continue later from the exact same state.
> Repeated work costs only the operation that actually needs rerunning.

### Graphical User Interface

A desktop interface so the user does not need the command line. It introduced:

- a video player;
- subtitle rendering;
- a timeline;
- detected slide markers and user-placed manual markers;
- viewing and correcting slides (add, resize, move, set frame, delete);
- a settings dialog;
- running operations via buttons instead of CLI arguments.

**User-visible result of this stage:**

> A non-developer user can perform the full workflow with the mouse, review the
> detected result visually, and correct mistakes before export.

### Shared Application Services Architecture

This is a **technical foundation**, not a standalone user feature. It is
documented here because it changes the trust model of the product.

GUI, CLI, and MCP (the agent-facing interface) were all moved onto a **single
canonical execution path** for operations. The same command produces the same
result regardless of which interface started it.

What this means in plain language:

- clicking "Detect" in the GUI;
- running the detect command in the CLI;
- invoking the detect MCP tool from an external agent;

…must all run the same application service and produce the same persisted
state, the same artifacts, and the same observable pipeline state.

This is infrastructure that **protects the user** from "it works in one
interface but not in another" situations. It is not advertised to the user as
a standalone feature.

### Testing and Stabilization

A sustained effort to keep the product trustworthy as it grew. Coverage spans:

- **Domain tests** — pure domain rules behave as specified.
- **Service tests** — application services produce the expected persisted
  state and artifacts.
- **Persistence tests** — projects save, reopen, and round-trip without
  losing state.
- **GUI tests** — the interface reflects canonical state and routes every
  write through the repository.
- **CLI tests** — the CLI is a thin transport over the same services.
- **MCP tests** — MCP tools dispatch through the same services and respect
  operation lifecycle.
- **E2E tests** — full workflows behave end-to-end through the real GUI + MCP
  transport.
- **Architecture-constraint tests** — forbidden layer boundaries are not
  crossed.

**User-visible problem these tests prevent:**

> The user reruns an operation and silently gets a different result, loses
> state after close/reopen, or sees the GUI disagree with what is actually
> persisted on disk.

### Windows Packaging

Turning the source tree into an installable Windows application. It covers:

- building the application into a standalone bundle;
- producing a Windows installer;
- versioning releases;
- publishing through GitHub Releases;
- checking for updates from inside the application;
- clean-machine verification (the bundle must install and run on a Windows
  machine that does not have Python preinstalled).

**User-visible result of this stage:**

> A Windows user installs `video2pptx` like any other desktop application,
> without installing Python, without cloning source, and without a terminal.

### Phase 18 Performance Investigation

This stage is documented with its **accepted result, unchanged**. Do not
reinterpret the decision from this roadmap.

- Performance was measured on the canonical benchmark.
- The number of passes over the video was reduced from **three to two**.
- The main bottleneck was identified as the **decode/frame pipeline**.
- Three optimization candidates were investigated — **C1, C2, and C3**.
- **None** of the candidates passed the parity gate, the stability gate, **and**
  the performance gate at the same time.
- The accepted terminal outcome is
  **`T3_NO_EVIDENCE_SUPPORTED_TARGET_OPTIMIZATION`**.
- **`selected_optimization=NONE`** — no targeted optimization is implemented.
- **Step 18.5 is not started.** It remains planned / blocked.
- **F-0103 remains open as non-blocking technical debt.**
- The causality of `codec_context` is **not proven**. It is recorded as a
  leading hypothesis, not as an isolated cause.

The technical phrasing of this decision is **not** restated here. The
authoritative wording lives in `docs/development-plan.xml`,
`docs/verification-plan.xml`, `docs/knowledge-graph.xml`, and `docs/findings.md`
(F-0103).

### Phase 19 — Analysis Resolution & Golden Mean

**Status: planned** (plan branch; no production code until approval).

A **new** performance/quality research track that does **not** reopen Phase 18.

- Motivation: detector decisions already use 48×48 features, but Pass 1 still
  processes full-resolution RGB after ROI; screenshots need full res only in Pass 2.
- Lever: `analysis_max_side` (analysis path only) × `sample_fps` grid sweep.
- Method: hard quality gates (missed ≤5%, false_split ≤10%, timestamp budget);
  golden mean = best speedup among passers; screenshots stay full-res.
- Outcome: selected defaults **or** documented `selected_analysis_scale=NONE`.
- Plan: `docs/plans/phase19-analysis-resolution-golden-mean.md`
- Finding: F-0104 (analysis resolution not discriminated in Phase 18)

### GRACE Stabilization

A body of work whose purpose is **trust in the engineering frame itself**, not
a user feature. It exists to:

- remove contradictions between evidence and module/phase statuses;
- restore broken or stale XML references;
- connect modules to the verification entries that actually cover them;
- prevent the next agent from building on top of a false statement;
- keep a large project navigable and reviewable.

> GRACE is the primary engineering frame of this project and must remain the
> source of technical structure, contracts, and verification.

GRACE is **not** optional bureaucracy. It is the mechanism that lets later work
depend on earlier work without re-deriving it.

---

## 4. Current User-Visible Capabilities

Only capabilities that are confirmed by passing evidence are listed here.

- Creating a project and opening an existing project.
- Working with a video file and a subtitle file (SRT / VTT).
- Automatic detection of slide intervals from the video.
- Saving representative screenshots for each detected interval.
- Reviewing and correcting slides through the GUI (add, resize, move, set
  frame, delete).
- Forming notes by linking detected intervals to transcript fragments.
- Exporting to Markdown (Marp) and PPTX.
- Reopening a project later without losing state.

Anything not listed here is **not** announced as ready, even if related code
exists.

---

## 5. Current Technical State

There is a difference between several kinds of "status" that must not be
confused:

- **Product status** — what the user can actually do today (see
  Section 4).
- **Technical status** — which modules are implemented, planned, or blocked.
- **Test status** — which behaviors are covered by reproducible passing tests.
- **GRACE integrity status** — whether the artifacts (graph, plan,
  verification plan) are internally consistent with the code and with each
  other.
- **Autonomy readiness** — whether an autonomous agent can be safely pointed
  at the next module without first having to reconcile contradictory metadata.

These are **independent**. A product can be working well for users while GRACE
integrity has open issues, and a perfectly clean GRACE graph does not by
itself prove that a user-facing feature works.

**Current lint, warning, and autonomy counters are intentionally not embedded
in this roadmap.** They change frequently and become stale immediately. The
current numbers must be read on demand through the `/project-status` command,
which combines the roadmap with live `git` and `grace status` data.

---

## 6. Current Accepted Result

The current accepted result of Phase 18 is:

> Terminal outcome `T3_NO_EVIDENCE_SUPPORTED_TARGET_OPTIMIZATION`,
> `selected_optimization=NONE`.

This is a **negative but useful** result. Specifically:

- The investigation ended without selecting an optimization — this is **not a
  bug** and **not a failure of process**.
- It is the result of applying strict parity, stability, and performance gates
  consistently to every candidate.
- No new targeted optimization should be implemented unless a new
  **evidence-supported** solution appears — i.e. a candidate that demonstrably
  satisfies all three gates, or a controlled experiment that isolates a
  previously-unisolated cause.

Step 18.5 must not be restarted on the basis of a "feel" that something should
be faster.

---

## 7. Current Work

Current work is focused on raising the reliability of **GRACE verification
metadata**, not on shipping a new user-facing feature. The work consists of
making sure that:

- every command referenced by a verification entry points at a test that
  actually exists;
- verification documentation does not contradict the actual state of the
  repository;
- evidence describes what was observed, not what was assumed;
- reports correspond to the underlying GRACE data at the HEAD they claim to
  describe.

This is **not** a new user-visible feature. It is the maintenance of the
engineering frame so that future user-visible features can be built on top of
trustworthy metadata instead of contradictory claims.

A side effect of skipping this work would be: agents and humans making
decisions on the basis of stale or incorrect statuses, which historically
caused wasted effort and false announcements of completion.

---

## 8. Next User-Visible Milestone

> The user downloads the Windows installer, installs `video2pptx`, opens a
> video and subtitles, runs the automatic scenario, receives a correct PPTX,
> closes the application, and then reopens the project without losing state.

Success criteria for this milestone:

- The application installs on a clean Windows machine.
- No manual Python installation is required to run it.
- A project can be created and opened.
- The main automatic scenario (detect → align → notes → export) completes.
- The produced PPTX opens correctly in a presentation tool.
- After closing and reopening the application, the project state is preserved.
- When something goes wrong, errors are shown to the user in an understandable
  way (not as a raw traceback).

This milestone is product-level. It depends on packaging, persistence, the
canonical service path, and error presentation working together — not on any
single module.

---

## 9. Relationship with GRACE

Each artifact answers a different question. They are complementary, not
redundant.

| Artifact / command | Question it answers |
| --- | --- |
| `docs/product-roadmap.md` | Where is the product going? |
| `docs/requirements.xml` | What is required? |
| `docs/development-plan.xml` | What modules and phases is this made of? |
| `docs/verification-plan.xml` | How is it verified? |
| `docs/knowledge-graph.xml` | Where is the implementation, and how are elements connected? |
| `grace status` | What is the machine state of GRACE right now? |
| `/project-status` | What does all of this mean for a human and for the product? |

`/project-status` is a **human-facing** layer over the lower-level GRACE
output. It does not weaken or replace `grace status`; it explains it.

---

## 10. Status Reporting Vocabulary

When reporting status (either in this roadmap or via `/project-status`), every
piece of work is classified as one of the following types. The vocabulary is
fixed.

- **`USER_VISIBLE_FEATURE`**
  A feature the end user can observe and use. Changes the user-visible
  function directly.
- **`BUG_FIX`**
  A correction of incorrect user-visible behavior. Changes the user-visible
  function directly.
- **`PRODUCT_SUPPORTING_TECHNICAL_WORK`**
  Internal technical work that enables or protects a user-visible feature but
  is not itself a user-facing function. Does not change the user-visible
  function directly.
- **`TEST`**
  Adds or repairs an automated test. Does not change the user-visible function
  directly; changes confidence in it.
- **`VERIFICATION_DOCUMENTATION`**
  Updates verification metadata so that it accurately describes existing tests
  and evidence. Does not change the user-visible function directly; changes
  trust in what is reported.
- **`GRACE_METADATA`**
  Repairs graph, plan, or contract metadata so that navigation and dependency
  claims are correct. Does not change the user-visible function directly.
- **`RESEARCH`**
  An investigation that may or may not produce a change. May inform a future
  user-visible feature; by itself does not change one.
- **`RELEASE_ENGINEERING`**
  Packaging, installer, release publishing, update checking, and
  clean-machine verification. Directly affects whether the user can install
  and run the product at all.

A reduction of a lint counter is **not** a user-visible result under any of
these types. It is at most an indicator that some
`GRACE_METADATA` / `VERIFICATION_DOCUMENTATION` work took effect.
