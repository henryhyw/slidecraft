# Product and Runtime Architecture

## Recommended product form

Build the system so people can create editable presentations through the Agent app they already use, with four access surfaces.

1. A Python SDK for direct integration and testing
2. A CLI for individual users and automation
3. An MCP server for Codex and other Agent hosts
4. An optional local dashboard for central management

All four surfaces call the same capability layer and read the same durable project artifacts. The dashboard does not own session progression.

The runtime is a modular local package with typed contracts, ordinary project files, and separate workers only where execution requirements differ. This keeps installation understandable while allowing image generation, local computer vision, and PowerPoint rendering to evolve independently.

The conversational and resumable execution contract is defined in [`AGENTIC_RUN_MODEL.md`](../AGENTIC_RUN_MODEL.md). The user normally speaks to an Agent. CLI, SDK, and MCP expose the same typed capabilities and versioned artifacts. The dashboard presents a human-readable view of the same state.

## Core architectural decision

Use the host agent as the primary control plane in agent-host mode. The framework supplies typed reasoning capabilities, deterministic workers, artifact persistence, freshness checks, and quality gates. A standalone background runner can be added as an optional adapter.

```text
User, dashboard, CLI, SDK, or MCP
              ↓
       Stateless adapter
              ↓
   Typed capability layer
              ↓
  Typed stage activities and approval gates
              ↓
  Project ledger, libraries, providers
```

The host Agent chooses which capability to call and when. Capabilities return typed results and artifacts. The framework records dependencies and validates freshness so an Agent can stop, inspect, revise, and continue without a central state machine. The dashboard and MCP adapter are stateless views over the same local project ledger.

A future hosted service may add queues and scheduling as an optional adapter. Agent-host mode does not require Temporal or another workflow server.

## User interaction model

### Primary objects

The interface exposes the following durable objects.

| Object | Meaning |
| --- | --- |
| Workspace | Organization-level libraries, providers, policies, and secrets |
| Project | A body of related deck work and project-specific assets |
| Deck | Shared design system, title, chrome, and validation configuration |
| Slide | Objective, exact source content, constraints, and slide assets |
| Run | One execution of the pipeline against a slide version |
| Artifact | Prompt, image, semantic map, contract, PPTX, render, or report |
| Library item | Versioned visual reference, icon, known component, or style preset |

### Human interaction points

The normal path needs one initial interaction and no routine intervention.

1. The user creates or selects a project and deck profile.
2. The user submits slide intent, exact content, optional constraints, and optional assets.
3. The Agent resolves configuration and invokes the relevant capabilities.
4. The Agent applies automatic gates, repair, retry, and escalation policies using recorded evidence.
5. The user receives the PPTX, final render, reports, and reviewable project history.

Optional checkpoints can be enabled at semantic plan approval, generated-image approval, or reconstruction approval. They are policies, not mandatory architecture stages.

### Integration surfaces

The CLI supports installation, configuration, the dashboard, local debugging, and CI.

```text
slidecraft init
slidecraft console
slidecraft check-install
```

The MCP server exposes six complete presentation tools for opening a project, preparing a deck, generating a slide, measuring a slide, reconstructing a slide, and rendering the deck. The host Agent decides when to call each tool. Interruption simply stops further calls. Continuation starts by reopening the project.

## Configuration system

### Configuration precedence

Configuration resolves from broad defaults to narrow overrides.

```text
System defaults
    ↓
Organization or workspace profile
    ↓
Project profile
    ↓
Deck profile
    ↓
Slide overrides
    ↓
Run overrides
```

Each resolved run stores a frozen configuration snapshot. Later changes to a library or deck profile cannot silently change an existing run.

### Configuration domains

| Domain | Typical values |
| --- | --- |
| Canvas | Slide size, units, generation region, coordinate transforms |
| Deck chrome | Header, footer, page number, confidentiality, section variants |
| Title | Anchor, width, font, weight, nominal size, color, wrapping, body gap |
| Typography | Display and body fonts, role hierarchy, sizing bounds, spacing |
| Color | Brand colors, role-based palette, tints, neutrals, contrast rules |
| Style | Density, whitespace, component surfaces, shape language, icon treatment |
| Icons | Library provider, slot sizes, padding, contain fitting, recoloring, mandatory policy |
| Connectors | Route family, stroke, corner style, arrowheads, bend and clearance limits |
| Reconstruction | Route preferences, raster policy, grouping, z-order, refinement bounds |
| Models | Provider IDs, model capabilities, timeouts, budgets, fallback chains |
| Compute | Local, remote, or automatic placement, devices, checkpoints, memory limits |
| Review | Materiality thresholds, automatic retries, approval gates |
| Validation | Text overflow, asset ratio, topology, fidelity, and native render thresholds |

### Example deck profile

```yaml
schema_version: 1.0.0
extends: consulting-base

canvas:
  size_px: [2048, 1152]
  exclusions:
    mode: configured_with_adaptive_fallback
    header_px: 41
    footer_px: 41

title:
  font_family: Georgia
  nominal_size_px: 76
  allowed_lines: [1, 2]
  minimum_gap_to_body_px: 36

libraries:
  visual_references: workspace://visual-references/pwc-consulting
  icons: workspace://icons/tabler-outline
  components: workspace://components/consulting-v1

models:
  reasoning: default_reasoner
  vision: default_vlm
  image_generation: default_image_generator
  segmentation: auto_segmenter

compute:
  mode: auto
  prefer_local_for: [opencv, segmentation]

interaction:
  require_generation_approval: false
  require_reconstruction_approval: false
  escalate_on_material_failure: true
```

Secrets such as API keys do not belong in these files. They should use environment variables, an operating-system keychain, or a deployment secret store.

## Maintained library connectors

The system needs three first-class maintained libraries and one runtime asset store.

### Visual Reference Library

Visual reference items contain a whole-slide preview, source deck reference, embedding, tags, slide role, information density, dominant structures, style profile, provenance, license, and version.

The library search indexes semantic intent, slide role, content density, relationship pattern, and style compatibility. The Agent inspects the candidates and chooses the pages that guide visual generation and review. They do not become content unless the slide explicitly requests reuse.

### Pictogram and Icon Library

Icon items contain a stable asset ID, SVG, semantic concepts, aliases, style family, stroke width, viewBox, protected-color policy, recoloring rules, provenance, license, and version.

Exact upstream identities resolve directly. Library search then returns semantic candidates. The Agent resolves substitutions jointly for coverage, distinction, and style consistency.

### Known Component Library

This library stores reusable editable constructions such as maps, process patterns, maturity scales, matrices, callout systems, organization structures, KPI blocks, legends, and complex consulting visuals.

Each component needs more than a thumbnail.

```yaml
component_id: consulting_map_world_v2
version: 2.1.0
semantic_roles: [world_map, geographic_distribution, country_highlight]
recognition_signature:
  concepts: [geography, countries, regions]
  visual_features: [map silhouette, geographic labels]
parameters:
  highlighted_regions:
    type: array
  base_fill:
    type: color
  highlight_fill:
    type: color
  show_labels:
    type: boolean
reconstruction_factory: components.maps.world_map_v2
editable_object_types: [freeform, textbox, group]
connection_ports: []
preview: previews/consulting_map_world_v2.png
source: components/consulting_map_world_v2.pptx
```

Slide understanding emits a semantic description and candidate component matches. The Agent chooses a certified known component when it fits the authored object and required parameters are available. Editable reconstruction applies measured placement and appearance, then configures it from exact upstream content. Other cases use an Agent-selected native, fitted-geometry, or raster route.

The known component library should store editable factories or source PowerPoint fragments. A preview image alone is insufficient.

### Runtime Asset Store

User uploads enter a project-scoped asset store. Each upload records its stable ID, semantic role, description, requirement status, protected treatment, provenance, hash, original file, normalized preview, and allowed transformations.

Mandatory and optional status is configurable per slide. The original file remains available through reconstruction.

## Common library interface

All maintained libraries should implement a shared retrieval interface.

```python
class LibraryProvider(Protocol):
    async def search(self, query: SemanticQuery, limit: int) -> list[Candidate]: ...
    async def get(self, item_id: str, version: str | None = None) -> LibraryItem: ...
    async def resolve(self, reference: AssetReference) -> ResolvedAsset: ...
    async def list_versions(self, item_id: str) -> list[VersionInfo]: ...
```

Provider implementations can use a local folder, Postgres with vector search, a cloud asset service, SharePoint, Google Drive, or another maintained repository. The pipeline consumes typed results and remains storage-neutral.

## Agent and worker architecture

### Reasoning agents

| Agent | Responsibility | Output |
| --- | --- | --- |
| Intake agent | Resolve objective, content completeness, constraints, and assets | Validated `SlideRequest` |
| Semantic planner | Derive message, relationships, hierarchy, and visual intent | `SemanticDesign` |
| Retrieval planner | Form semantic searches and reconcile candidate sets | `RetrievalPlan` |
| Generation reviewer | Diagnose material generation failures | `ReviewDecision` |
| Semantic mapper | Identify meaningful entities and map upstream sources | `SemanticScene` |
| Reconstruction planner | Select known, native, fitted, or raster routes | `ReconstructionContract` |
| Refinement agent | Identify semantic peer groups and propose bounded alignment and normalization intents | `RefinementPlan` |
| Normalization solver | Validate movement bounds, parent containment, clearances, text fit, and rollback conditions | `NormalizationReport` |
| Preflight agent | Produce the concise approval summary and detailed generation package | `GenerationPreflight` |
| Approval gate | Release external generation only for an approved package fingerprint | `GenerationApproval` |
| Attachment ingestor | Register chat uploads in the project asset store with provenance and usage class | `IngestedAsset` |
| QA agent | Interpret validation failures and select retry or escalation policy | `GateDecision` |

Each reasoning task has a narrow prompt, typed input, structured output, validation, budget, timeout, and retry policy. The host Agent invokes mutating capabilities explicitly. There is no separate workflow state for an Agent to advance.

### Deterministic workers

| Worker | Responsibility |
| --- | --- |
| Prompt assembler | Compose generation and edit prompts from typed packages |
| Visual-reference and asset indexer | Create metadata, previews, embeddings, and hashes |
| OpenCV worker | Measure boxes, lines, edges, colors, and text geometry |
| Segmentation worker | Produce selective masks for requested irregular regions |
| Screenshot worker | Extract raster fallback regions |
| PowerPoint constructor | Emit native objects, canonical assets, groups, and z-order |
| PowerPoint renderer | Export through Microsoft PowerPoint where available |
| Validation worker | Run text, asset, connector, hierarchy, and package checks |

## Model connection

The Agent application owns language reasoning and visual understanding. Slidecraft accepts the resulting structured decisions through MCP and validates them before use.

Image generation is the only separately configurable model connection. The Agent can use its own image tool. When that tool is unavailable, or when the user selects a connected service, Slidecraft calls the configured OpenAI or OpenAI-compatible image endpoint.

```python
class ImageGenerationProvider(Protocol):
    async def generate(self, request: ImageGenerationRequest) -> ImageArtifact: ...
    async def edit(self, request: ImageEditRequest) -> ImageArtifact: ...
```

The image connection records its model ID, supported dimensions, timeout, credential reference, and provenance. The presentation domain remains independent from a single vendor SDK.

## OpenCV and segmentation execution

Users should not select hardware for ordinary runs. A compute broker resolves execution automatically.

### Capability discovery

At worker startup, the broker records these capabilities.

- OpenCV version and supported codecs
- Available CPU cores and memory
- Apple MPS availability
- CUDA device and memory when present
- Installed segmentation checkpoints
- Remote segmentation provider availability
- Expected input size and estimated workload

### Automatic placement policy

```text
Ordinary deterministic measurement
    → local OpenCV CPU worker

Selective irregular-object mask
    → local MPS or CUDA when available and checkpoint is ready
    → local CPU when expected latency remains acceptable
    → configured remote segmentation worker when local execution is unavailable or exceeds policy

No useful segmentation case
    → skip segmentation
```

The policy should consider data privacy, device capability, model readiness, image size, queue latency, cost, and deadline. The selected backend and timing are recorded in the run report.

### Worker registration

Desktop installations can run a local worker that registers capabilities with the orchestrator. A hosted deployment can run CPU and GPU worker pools. Activities are routed by capability tags such as `opencv`, `sam2-mps`, `sam2-cuda`, `powerpoint-mac`, and `powerpoint-windows`.

This gives users automatic local acceleration while preserving a remote fallback.

## Artifact lifecycle

```text
source and configuration artifacts
  ↓
derived artifact revisions
  ↓
candidate or active lifecycle
  ↓
fresh or stale dependency result
  ↓
validation evidence
```

The core does not impose a global run state machine. Each capability records inputs, outputs, configuration snapshot, producer, dependencies, reason, and timestamps. The host Agent chooses the next capability from conversation intent and current workspace evidence.

Long-running work remains recoverable because activities write immutable artifacts before reporting completion. External model calls and file construction use idempotency keys. A future background runner can maintain operational queue states without changing the artifact contract.

## REST interface

The API can expose the following resource families.

```text
POST   /v1/projects
POST   /v1/decks
POST   /v1/decks/{deck_id}/slides
POST   /v1/assets
POST   /v1/runs
GET    /v1/runs/{run_id}
GET    /v1/runs/{run_id}/events
GET    /v1/runs/{run_id}/artifacts
POST   /v1/capabilities/{capability_name}
POST   /v1/libraries/{library}/search
GET    /v1/libraries/{library}/items/{item_id}
```

Run events can use server-sent events or WebSockets. The API should return artifact IDs and signed download links instead of embedding large files in JSON.

## Storage model

Use a relational database for metadata and an object store for files.

### Relational data

- Workspaces, projects, decks, slides, and versions
- Runs, stages, transitions, approvals, and failures
- Configuration profiles and frozen snapshots
- Library metadata, embeddings, versions, and licenses
- Asset identities, hashes, roles, and provenance
- Entity graphs and reconstruction unit summaries

### Object storage

- Source documents and user uploads
- Visual reference previews and source decks
- Canonical SVGs and known-component packages
- Generated and edited images
- Masks and debug overlays
- Semantic maps and reconstruction contracts
- PPTX files, native renders, and reports

Artifacts should be content-addressed where practical. Every report should include hashes and source references.

## Observability and governance

Every model activity records provider, model, prompt-definition version, structured output, token or image usage where available, latency, retries, and validation result. Sensitive prompts and source content follow workspace retention policy.

Every library item records provenance, license, owner, version, and permitted transformations. Protected logos retain their original geometry and colors according to policy.

The framework should support per-workspace budgets, provider allowlists, data-residency rules, and local-only execution for sensitive projects.

## Suggested repository layout

```text
slidecraft/
  apps/
    api/
    cli/
    mcp/
    worker/
  domain/
    models/
    contracts/
    policies/
  workflows/
    slide_workflow.py
    activities/
  agents/
    intake/
    semantic_planner/
    generation_reviewer/
    semantic_mapper/
    reconstruction_planner/
    refinement/
    qa/
  providers/
    reasoning/
    vision/
    image_generation/
    segmentation/
    rendering/
  libraries/
    visual_references/
    icons/
    components/
    assets/
  cv/
    opencv/
    segmentation/
  reconstruction/
    text/
    tables/
    charts/
    icons/
    components/
    connectors/
    geometry/
    images/
  validation/
  storage/
  config/
  tests/
```

## Delivery phases

### Phase 1, implemented foundation

Maintain the typed Python package, configuration resolution, local artifact graph, Python capability API, JSON CLI adapter, and existing end-to-end pipeline workers. Add remaining stage capabilities as their typed contracts stabilize.

### Phase 2, Agent integrations

Harden the current MCP adapter and add host configuration examples for Codex, Claude, Copilot, and other MCP clients. Complete user assets, library provider interfaces, and capability-level approval policies. Move the fixed visual-reference set and Tabler index behind those interfaces.

### Phase 3

Add Temporal, Postgres, and object storage. Register local and hosted workers by capability. Add model provider profiles, secret management, retries, idempotency, tracing, and budgets.

### Phase 4

Build the maintained Visual Reference Library, Icon Library, and Known Component Library with indexing, versioning, provenance, previews, and editable reconstruction factories.

### Phase 5

Automate VLM semantic mapping, native PowerPoint render comparison, bounded refitting, multi-slide deck consistency, and library learning from accepted reconstructions.

## Current implementation slice

The first real project increment should implement one vertical path.

1. Six task-oriented MCP tools
2. Matching Python workflows for shell-capable Agent fallback
3. Typed request, configuration, semantic scene, and constructor scene contracts
4. Versioned artifact graph with candidate, active, superseded, rejected, fresh, and stale semantics
5. Existing end-to-end workers hidden behind the six workflows
6. Local folder providers for visual references, Tabler icons, known components, and user assets
7. Automatic OpenCV and SAM capability detection
8. MCP v2 STDIO integration registered by the guided installer

This slice supports Agent-controlled local operation before distributed infrastructure is introduced.
