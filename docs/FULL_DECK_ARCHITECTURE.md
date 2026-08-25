# Full-deck architecture

## Planning contract

The host Agent starts from audience, desired outcome, project materials, explicit constraints, density, and an optional page-count range. It records that conversational result through `set_deck_brief`, which works through MCP without direct hidden-file access. `plan_deck` asks a structured reasoning model to compare plausible storylines, choose one governing thought, create purposeful sections, allocate every authoritative source atom, and assign one communication job to every slide.

Visual source material is interpreted by the host's visual understanding before planning. The interpretation remains paired with the original path and hash. Path-only images remain explicitly pending, so filename and dimension metadata cannot masquerade as semantic evidence.

The plan validator enforces unique ordered slide IDs, valid sections and dependencies, complete authoritative-source allocation, requested page-count bounds, required asset placement, and a passing planner self-evaluation.

## Shared deck design

Each project receives `.slidecraft/deck_design.json` from the packaged baseline. The dashboard and configuration system can override its user-facing style choices. Planning stores a frozen design snapshot that controls the following deck-wide properties.

- Full slide dimensions and generation exclusions
- Header, footer, page number, and slide variants
- Title anchor, width, typography, wrapping, and body clearance
- Typography roles and half-point Office-safe fitting
- Color roles, surfaces, icon treatment, and connector policy
- Density, whitespace, normalization, and validation rules

Every generated content slide and every deterministic structural slide consumes the same snapshot. Resolved header and footer content is merged into the reconstruction contract, including the project label, slide title, confidentiality text, project footer, date, and page number. Final assembly rejects mismatched design identities, canvases, backgrounds, repeated text-role styles, connector minimums, or deterministic deck chrome.

## Slide routing

Low-information structural roles use packaged native layouts. The supported roles are cover, agenda, section divider, statement, closing, and appendix divider. Their scenes are created during deck planning, use normalized layout recipes, and pass the same Office-safe text-fit policy used by reconstructed content.

Every information-bearing slide uses image generation. `prepare_slide` compiles its deck job and allocated source atoms into an authoritative slide request plus a semantic-planning prompt. The host Agent creates the structured semantic design, then `prepare_generation` retrieves resources and assembles the image-generation and reconstruction handoffs.

This routing keeps covers and transitions consistent across the deck. It also lets the image model choose the most effective visual form for substantive content.

## Content-slide execution

The Agent follows the durable actions returned by `workflow_status`.

1. Prepare the slide request and semantic prompt.
2. Create and register the semantic design.
3. Retrieve visual inspiration, icons, components, and slide assets.
4. Generate and review the content-region image.
5. Map meaningful entities and semantic connector topology.
6. Measure geometry with OpenCV and selective optional segmentation.
7. Compile reconstruction routes and a constructor scene.
8. Apply bounded alignment, typography, icon-slot, and connector normalization.

The dashboard does not own this progression. It reads and edits the same project files and durable artifact ledger used by the Agent.

## Assembly and coherence

`render_pptx` reads the active deck plan and derives the required constructor-scene keys in page order. It rejects missing, extra, reordered, stale, or invalid scenes. It then checks the frozen design identity, shared canvas, background, structural routing, repeated typography roles, canonical asset roles, connector visibility policy, and exact header and footer geometry before invoking the certified PptxGenJS constructor.

Package integrity and constructor conformance remain mandatory. Native Microsoft PowerPoint rendering is an optional additional gate when the user has authorized local automation.

## Controlled variants

Deck consistency allows intentional page silhouettes. Structural layouts are selected from one maintained system, section accents stay inside the frozen palette, and image-generated bodies retain composition freedom inside the same title, typography, icon, connector, and chrome language.

## Current coverage boundary

The Agent-host path is wired through editable PowerPoint assembly. Known-component manifests can be retrieved and previewed. A component is selected for direct restoration only after its editable implementation route is certified. Until then, it stays as semantic evidence and the slide uses a supported native, fitted-geometry, or raster route.
