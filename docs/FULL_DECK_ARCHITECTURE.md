# Full-deck architecture

## Planning contract

The host Agent reads the project materials, decides authority and required use, and determines whether the evidence supports credible planning. It starts from the audience, desired outcome, explicit constraints, density, and an optional page-count range. The Agent compares plausible storylines, chooses one governing thought, creates purposeful sections, and assigns one communication job to every slide. It shares the proposed slide count and per-slide messages during collaborative work, then stores the accepted storyboard as an ordinary project file.

Visual source material is interpreted by the host's visual understanding before planning. The interpretation remains paired with the original path and hash. Image semantics come from visual inspection, while filenames and dimensions remain supporting metadata.

The skill guides editorial review of relevance, evidence, sequence, and audience value. Lightweight file schemas help the Agent keep identifiers and handoffs consistent. The Agent records editorial assessments alongside the plan.

## Shared deck design

Each project receives `.slidecraft/deck_design.json` from the packaged baseline. The dashboard and configuration system can override its user-facing style choices. Every direct reconstruction writes the effective resolved design used for that slide, so the Agent and dashboard can inspect the same downstream inputs. The design controls the following deck-wide properties.

- Full slide dimensions and generation exclusions
- Header, footer, page number, and slide variants
- Title anchor, width, typography, wrapping, and body clearance
- Typography roles and half-point Office-safe fitting
- Color roles, surfaces, icon treatment, and connector policy
- Density, whitespace, normalization, and validation rules

Every generated content slide and deterministic structural slide consumes the resolved project design. Resolved header and footer content can be merged into the reconstruction handoff, including the project label, slide title, confidentiality text, project footer, date, and page number. Construction checks the mechanical consistency required by the selected routes.

## Slide routing

Low-information structural roles use packaged native layouts. The supported roles are cover, agenda, section divider, statement, closing, and appendix divider. Their scenes are created during deck planning, use normalized layout recipes, and pass the same Office-safe text-fit policy used by reconstructed content.

Information-bearing slides can use image generation. The host Agent creates the structured semantic design, reads the resources selected in the shared project context, and chooses the final visual inputs. It authors the image-generation and reconstruction handoffs according to the skill.

This routing keeps covers and transitions consistent across the deck. It also lets the image model choose the most effective visual form for substantive content.

## Content-slide execution

The Agent composes the workflow from the user's request and durable project facts.

1. Prepare the slide request and semantic prompt.
2. Create and register the semantic design.
3. Search visual inspiration, icons, and components, then reason over the candidates and select the useful resources.
4. Generate and review the content-region image.
5. Map meaningful entities and semantic connector topology.
6. Measure geometry with OpenCV and selective optional segmentation.
7. Compile reconstruction routes and a constructor scene.
8. Apply bounded alignment, typography, icon-slot, and connector normalization.

The dashboard presents this progression through the same project files and durable artifact ledger used by the Agent.

## Assembly and coherence

`slidecraft render-scenes` receives constructor scenes in the order selected by the Agent. The Agent verifies that the sequence matches the accepted storyboard. The constructor checks supported objects and package integrity before writing the editable PowerPoint.

Package integrity and constructor conformance remain mandatory. Native Microsoft PowerPoint rendering is an optional additional gate when the user has authorized local automation.

## Controlled variants

Deck consistency allows intentional page silhouettes. Structural layouts are selected from one maintained system, section accents stay inside the frozen palette, and image-generated bodies retain composition freedom inside the same title, typography, icon, connector, and chrome language.

## Current coverage boundary

The Agent-host path is wired through editable PowerPoint assembly. Known-component manifests can be retrieved and previewed. A component is selected for direct restoration only after its editable implementation route is certified. Until then, it stays as semantic evidence and the slide uses a supported native, fitted-geometry, or raster route.
