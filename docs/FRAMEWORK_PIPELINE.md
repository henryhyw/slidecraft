# Framework pipeline

## Purpose

This document defines the supported system contract. The pipeline accepts authoritative slide content and configurable deck rules, generates a designed slide region, preserves useful upstream knowledge, interprets the generated image, and reconstructs an editable PowerPoint slide.

The central principle is simple.

> Generation decides the visual composition. Reconstruction restores semantic objects through stable contracts, canonical assets, measured geometry, and native PowerPoint behavior.

The machine-readable version of this policy is [`config/framework_pipeline.json`](../config/framework_pipeline.json). Deck design values are project inputs. A regression example lives in [`tests/fixtures/architecture/design_config.json`](../tests/fixtures/architecture/design_config.json).

## End-to-end system

```text
Maintained resources                 Configured deck rules
Visual Reference Library               Slide size and excluded regions
Pictogram and Icon Library          Deck chrome and title treatment
Known Element Library               Typography and color roles
Canonical identity assets           Icon slots and connector style
Style presets                        Validation tolerances
              \                      /
               \                    /
                         Semantic planning
                         exact content stays authoritative
                              ↓
                    Reference and asset retrieval
                              ↓
                 Prompt assembly and visual generation
                              ↓
                       Material-failure review
                              ↓
                  Final image plus upstream handoff
                              ↓
                         Semantic mapping
                         Pixel measurement
                              ↓
                    Reconstruction contract
                              ↓
                  Known element reconstruction
                 New element reconstruction
                              ↓
                 Reasoning-guided normalization
                              ↓
                Deck chrome and native validation
                              ↓
                         Editable PPTX
```

The generation review and native validation are pipeline quality gates. They do not add conceptual architecture stages.

## Information ownership

| Information | Owner | Lifecycle |
| --- | --- | --- |
| Slide objective and exact content | Per-slide input | Supplied for each slide |
| Explicit layout or asset requirements | Per-slide input | Supplied only when needed |
| Slide dimensions and exclusions | Deck design configuration | Shared across a deck or selected deck variant |
| Header, footer, title, typography, colors, density, icon slots, and connectors | Deck design configuration | Maintained and versioned |
| Visual reference pages | Visual Reference Library | Maintained reference collection |
| Canonical pictograms and logos | Icon Library and asset store | Maintained with stable IDs and provenance |
| Reusable editable constructions | Known Element Library | Grows over time |
| Semantic design | Semantic planning runtime output | Derived for each slide |
| Selected references and assets | Resource retrieval runtime output | Derived for each slide and retained |
| Visual composition | Image model | Derived for each candidate image |
| Semantic entities and relationships | Semantic mapping | Derived from the final image and upstream state |
| Pixel geometry and visual evidence | Visual measurement | Derived from the final image |
| Editable object implementation | Editable reconstruction | Derived from the reconstruction contract |

This division prevents three common failures. Exact content cannot be replaced by a paraphrase. Visual-reference styling cannot become an accidental layout copy. Generated pixels cannot become the sole source of truth when exact upstream information exists.

## Runtime input

Every slide begins with a `SlideRequest` containing the following information.

- Slide objective
- Exact source content
- Optional explicit human constraints
- Optional user-provided canonical assets
- Slide role, section, audience, confidentiality, and deck metadata when available

The exact source content is authoritative throughout the pipeline. OCR supports source mapping and measurement. It never replaces the source content.

## Deck design configuration

`DeckConfig` controls consistency across the deck. The current sample uses a 2048 by 1152 pixel slide with 41 pixel header and footer exclusions. The generated region is 2048 by 1070 pixels and begins at full-slide y coordinate 41.

The exclusion resolver supports configured values, adaptive values, and configured values with adaptive fallback. Future design-system-aware derivation can use the same adapter boundary without changing prompt assembly or downstream coordinate transforms.

The title sits inside the generation region. Its anchor, maximum width, font, nominal size, alignment, line allowance, and minimum body gap come from deck design configuration. Image generation never creates the header or footer.

Deck chrome is applied after reconstruction. A reasoning adapter may choose a configured variant such as content slide, section divider, title slide, or appendix. Geometry and visual treatment become deterministic after variant selection.

## Semantic planning semantic planning

The semantic planner receives the slide objective, exact source content, and explicit human constraints. It produces the following package.

- Main message
- Required information
- Semantic relationships
- Hierarchy and relative emphasis
- Reading logic
- Supporting information
- Layout-agnostic visual intent

The planner can express sequence, comparison, hierarchy, grouping, parallelism, causality, contribution, dependency, and input-output logic. It does not normally choose coordinates, column widths, cards, or precise components. Image generation owns those design decisions unless the user explicitly constrains them.

The current architecture sample uses a host-brain semantic plan through a generic provider-neutral contract. The planner builds semantic units, proposes multiple communication structures, scores them, selects one, and verifies exact-source traceability. A standalone managed-provider adapter can later call the same prompt and return the same schema.

## Resource retrieval reference retrieval

### Visual references

The current framework uses three fixed visual reference pages. They provide evidence about typography, information density, whitespace, alignment, hierarchy, color use, diagram language, component styling, and design sophistication. Their text and layouts cannot be reused as slide content.

Scalable library deployments replace the starter set with `visual_reference_retriever_v1` backed by the Visual Reference Library.

### Icons and pictograms

The current framework uses Tabler Icons Outline through `canonical_icon_retriever_v1`. Retrieval considers the semantic role of each icon and selects a coherent set with distinct roles and consistent visual language.

Selection follows this order.

1. Restore the exact upstream canonical asset when its identity is known.
2. Select an individual library substitute when one role lacks an exact asset.
3. Select all affected substitutions jointly when set-level coherence and role distinction require it.

Each selected asset retains its stable ID, semantic role, candidate alternatives, library provenance, canonical SVG path, intrinsic aspect ratio, and requirement status.

### User-provided assets

User assets follow the same normalized asset contract as library icons. A configurable requirement field marks each asset as mandatory or optional. The current OpenAI, OpenCV, and PowerPoint assets are mandatory and are restored from their exact SVG files during reconstruction.

Image generation receives semantic descriptions of these assets. It does not require their source files as attached images. The canonical files remain available downstream.

## Asset normalization and icon slots

Every replaceable icon receives an authoritative rectangular slot. The orchestration layer calculates slot dimensions from the generation canvas, the asset's semantic size role, the source SVG aspect ratio, and configured inset padding. The generation prompt includes the calculated dimensions and tolerance.

The slot controls these properties.

- Allocated position and size
- Center
- Internal padding
- External clearance
- Relationship to nearby labels and components
- Z-order

The generated glyph inside the slot is semantic evidence. Its tight bounding box, visual center, contours, and stroke geometry do not control reconstruction.

Editable reconstruction loads the canonical SVG, computes explicit proportional contain geometry from the SVG viewBox, maximizes it inside the padded slot, and centers it. Stretching and cropping are prohibited. The current aspect-ratio tolerance is 0.001.

The configured pictogram treatment uses a pale warm-tint rectangular surface with an orange Tabler-style outline icon above it. Protected identity assets retain canonical colors. A slot surface stays when it is part of the designed component and disappears when it only communicates placement.

## Visual generation prompt assembly and generation

Prompt assembly is modular. It combines the following packages in a stable order.

1. Generation task and derived canvas
2. Configured title rules
3. Semantic design intent
4. Exact authoritative content
5. Normalized assets and icon slot dimensions
6. Visual reference guidance
7. Configured style system
8. Design responsibility and freedom
9. Output quality requirements

The image model owns body composition, spatial organization, grouping, scale, component design, connector depiction, asset adaptation, whitespace, and detailed visual structure.

The image prompt excludes reconstruction object IDs, OpenCV routing details, SAM reconstruction logic, PowerPoint object routes, geometry fitting instructions, z-order schemas, and internal scene representations. Technology names may still appear when they are part of the slide's content.

## Generation review and edit orchestration

The reviewer receives the candidate image, exact content, semantic design, references, deck design configuration, and asset manifest. It checks material failures in communication, hierarchy, relationships, content fidelity, visual-reference fidelity, legibility, and visual quality.

The reviewer returns strict structured output with a pass or edit decision, material issues, and a delta-only edit instruction. It does not restate the complete configuration.

When editing is needed, the main orchestrator appends an invariant envelope containing the following constraints.

- Canvas and exclusion rules
- Exact title and title treatment
- Exact source content
- Semantic relationships
- Style rules
- Mandatory asset roles
- Icon slot dimensions
- Preservation boundary

This keeps the reviewer focused on diagnosis and keeps configuration authority in the main orchestration flow.

## Reconstruction handoff

The reconstruction handoff contains more than the final PNG.

- Final target image
- Full slide dimensions
- Header and footer exclusions
- Generation-region size and full-slide offset
- Deck chrome configuration
- Exact title text and title configuration
- Exact source content
- Semantic design
- Selected asset IDs, descriptions, candidates, provenance, canonical paths, and intrinsic geometry
- Icon slot configuration
- Connector configuration and clarity thresholds
- Style configuration
- Visual reference identities, paths, and hashes
- Pipeline policy contract

Slide understanding can therefore map a rendered placeholder to a known candidate asset and map a text region to exact source content. It does not need to rediscover either item from pixels alone.

## Slide understanding parallel understanding

### Semantic mapping semantic mapping

Semantic mapping identifies meaningful PowerPoint-style entities and their relationships. It recognizes text, tables, charts, icons, images, shapes, connectors, groups, and novel visual structures. It avoids creating reconstruction entities from every visible contour.

The semantic scene records the following information where relevant.

- Identity and semantic role
- Parent and child ownership
- Related entities
- Source-content mapping
- Known, canonical, reusable, novel, or raster classification
- Approximate placement
- Overlap and z-order
- Reconstruction significance

### Visual measurement pixel measurement

OpenCV handles deterministic measurements such as bounding boxes, lines, edges, colors, fills, strokes, text geometry, and ordinary contours. SAM 2 is used selectively when an irregular filled boundary benefits from a mask. Thin line art primarily uses OpenCV evidence.

The following records normally remain measurement evidence.

- OCR words and raster line fragments
- SAM masks
- Raw contours
- Edge fragments
- Generated icon glyph paths
- Arrowhead contours
- Incidental anti-aliasing boundaries

These records never become PowerPoint objects unless semantic mapping identifies an independently authored visual object.

### Images

A meaningful photograph, generated illustration, map, screenshot, or texture panel becomes one `image` entity. Internal objects and text remain pixels in that entity unless they are visibly overlaid and independently authored.

Editable reconstruction restores an exact upstream image when available. Otherwise Slide understanding exports a screenshot crop that Editable reconstruction embeds as one PowerPoint picture object.

### Connector graph extraction

Connectors are reconstructed from relationship intent and spatial placement. Slide understanding identifies every source, every target, directionality, relationship type, and topology cardinality. Supported topologies include one-to-one, one-to-many branch, many-to-one merge, and many-to-many shared junction.

Pixel analysis retains approximate anchors, junctions, route orientation, routing corridor, stroke, corner treatment, and arrowhead treatment. Exact generated connector paths are non-authoritative for ordinary relationship notation.

Raster fragments that express one relationship system are consolidated into one semantic connector graph.

## Editable reconstruction reconstruction routes

### Known element reconstruction

Known semantic elements use their clean, editable implementation.

| Input | Preferred PowerPoint output |
| --- | --- |
| Authored text | Native textbox |
| Tabular structure | Native table |
| Chart with authoritative data | Native editable chart |
| Canonical icon or logo | Canonical SVG |
| Known reusable structure | Known Element Library construction |
| Upstream image | Canonical picture asset |

### New or redesigned element reconstruction

New visual elements follow a constrained route order.

1. Standard PowerPoint primitive
2. Native connector composition
3. Fitted freeform or Bezier geometry
4. Raster fallback

Semantic equivalence does not authorize a redesigned glyph or shape. Geometry evidence configures the actual target structure. Raster fallback is reserved for visuals that cannot be expressed faithfully and editably through cleaner routes.

## Native text reconstruction

Text is reconstructed as authored blocks. The exact source text, true paragraph structure, semantic role, configured font style, alignment, and measured outer textbox form the primary contract.

Raster line count and line extents support fitting. They do not create artificial line breaks or blank spaces. One logical block normally becomes one native textbox.

Every important PowerPoint text property is explicit. This includes font family, size, weight, color, internal margins, wrapping, autofit, line spacing, paragraph spacing, and vertical anchor.

The outer textbox geometry cannot expand to solve overflow. Fitting first reduces internal margins and spacing within configured limits, then chooses the largest readable font size that fits. Peer text roles are solved jointly so repeated stage titles, card titles, body blocks, and labels remain consistent.

Microsoft PowerPoint for Mac is the canonical development renderer because Office text metrics and defaults can differ from LibreOffice or other renderers.

The constructor converts measured image pixels through the actual slide scale. Font size, margins, paragraph spacing, and stroke width use `slide_width_inches × 72 / source_width_px`. Treating measured pixels as 96-DPI CSS pixels is invalid and inflates typography on high-resolution generation canvases.

PowerPoint automation is permission-gated on macOS. It is activated only through the explicit `slidecraft authorize-powerpoint` setup command. Ordinary runs never invoke a permission probe. They use package-level validation or record that native Office validation was skipped.

## Native connector reconstruction

Editable reconstruction compiles each semantic connector graph into native PowerPoint connector objects. Ordinary raster paths, separate arrowhead shapes, and arbitrary fitted connector silhouettes are prohibited.

The router follows these rules.

- Prefer horizontal and vertical segments.
- Use straight, elbow, curved, branch, merge, or shared-junction structures according to semantic topology.
- Attach endpoints to semantically valid source and target anchors.
- Use a shared trunk and junction for branch or merge systems when appropriate.
- Keep terminal approach segments straight when the final junction and target anchor share an axis.
- Remove redundant final bends.
- Keep ordinary routes within the configured bend limit.
- Avoid text and peer component crossings.
- Normalize peer routes when the relationship system implies repetition.
- Enforce minimum arrowhead dimensions and clear terminal segments.
- Use nonrendering routing ports only as implementation aids. They do not become reconstruction entities.

The current consulting connector preset uses a 4 pixel orange stroke, large PowerPoint triangle arrowheads, 20 by 18 pixel target dimensions, and a minimum 18 pixel visible endpoint.

## Tables, charts, and novel geometry

Native tables require explicit rows, columns, merged regions, subrows, cell ownership, cell margins, fills, borders, and text settings. A shape-and-text composition is allowed when PowerPoint table limitations prevent faithful output.

Editable charts require authoritative data and chart semantics. A configurable chart is preferred. Shape composition is a fallback when the slide contains a chart-like illustration without recoverable data.

Standard primitives represent rectangles, lines, circles, connectors, and familiar shapes. OpenCV geometry supports thin line structures. Fitted freeforms or Bezier paths are used only for portions that standard primitives cannot express. SAM masks mainly support irregular filled boundaries.

## Z-order and grouping

Slide understanding combines semantic ownership with measured overlap evidence. Editable reconstruction preserves the resulting layer order.

Logical hierarchy does not require a PowerPoint group object at every level. A PowerPoint group is created when it improves editability, preserves a reusable structure, or keeps a meaningful multi-part object together. Evidence-only records never create shapes.

## Reasoning-guided normalization

After initial reconstruction, the constructor treats the slide as a designed system and applies bounded corrections.

Allowed corrections include centering a child in its intended container, normalizing repeated anchors, aligning peers, normalizing repeated insets, simplifying connector routing, centering contain-fitted icons, and jointly normalizing peer typography.

The pass cannot invent content, create a new conceptual layout, expand measured textbox geometry, or substitute an aesthetic alternative. Every adjustment should be explainable as consistency, clearance, alignment, legibility, or fidelity.

The reasoning layer first emits explicit alignment intents. Each intent identifies semantic peers, the alignment basis, the parent container for every peer, the proposed anchor, and a confidence score. Typical anchors include top, bottom, center, text baseline, and parent-relative inset. Repeated objects in different containers should usually use parent-relative anchors.

The deterministic solver then treats measured geometry as a strong initial condition. It may translate a complete semantic group by a small amount. It preserves object dimensions, internal group geometry, z-order, text content, and semantic ownership. The default movement cap is 16 px and 20 percent of the object's smaller dimension, whichever is lower.

Every proposed move must keep the object inside its parent, preserve minimum clearance, create no new collision, preserve connector topology, and keep text within its existing box. Attached native connectors are rerouted after an accepted move. A proposal is accepted only when it materially reduces the declared alignment error. Failed checks trigger rollback.

For the current architecture slide, the GPT Image 2 and OpenCV + SAM 2 technology badges form one peer group. Their normalization anchor is the bottom inset within their respective stage containers. The badge background, canonical logo, and label move together as rigid groups. This corrects the visible level difference without changing either stage layout or either badge's internal composition.

Text alignment follows the same mechanism. Peer textboxes can share a parent-relative left inset, top inset, centerline, or baseline. The outer boxes keep their measured width and height. Typography fitting runs after geometry normalization, and any resulting overflow cancels the move.

## Deck chrome and multi-slide behavior

Header and footer regions are deterministic deck elements. Image generation never draws them. Editable reconstruction applies the selected chrome variant after reconstructing the generated region.

For a multi-slide deck, the same deck design configuration governs dimensions, chrome, title treatment, typography, color roles, icon treatment, and connector defaults. Per-slide metadata can select a permitted chrome variant. The renderer then applies the selected variant consistently.

## Quality gates

The current release requires the following checks before accepting a reconstructed slide.

1. All authoritative content appears once in the intended semantic role.
2. Every required semantic relationship is present.
3. Visual reference content has not been reused as slide content.
4. Every mandatory asset maps to a canonical asset or an explicit substitute decision.
5. Every replaceable icon uses a detected or inferred slot with uncertainty recorded.
6. Canonical icons preserve aspect ratio, remain centered, and stay inside padded slots.
7. Text does not overflow in Microsoft PowerPoint.
8. Peer typography is consistent unless a documented split is necessary.
9. Connector topology matches the semantic graph.
10. Ordinary connectors use native PowerPoint connector objects.
11. Arrowheads are legible and unnecessary bends are removed.
12. Parent-child ownership, overlap, and z-order are complete.
13. Every PowerPoint object maps to a reconstruction unit.
14. Evidence records emit no PowerPoint objects.
15. A Microsoft PowerPoint native render is produced for compatibility validation.

## Failure handling

| Failure | Automatic response |
| --- | --- |
| Missing exact source content | Stop before generation and request authoritative content |
| Missing mandatory canonical asset | Record the failure and use configured semantic substitution only when allowed |
| Weak icon match | Select affected icons jointly as a coherent set and record alternatives |
| No visible icon slot | Infer a slot from its parent component, record uncertainty, and apply configured padding |
| Ambiguous connector fragments | Resolve the relationship graph from semantic context and nearby anchors, then use the simplest valid native route |
| Text overflow in PowerPoint | Reduce margins and spacing within limits, then solve font size within the immutable box |
| Native table cannot match structure | Use aligned native shapes and textboxes with a reconstruction report entry |
| Irregular geometry lacks a clean editable fit | Use a fitted freeform, then raster fallback if fidelity remains inadequate |
| Missing upstream image | Embed the Slide understanding screenshot crop as one picture |

## Replaceable adapters

The following boundaries allow implementation upgrades without changing downstream contracts.

- Reasoning model adapter
- Header and footer exclusion resolver
- Deck chrome variant selector
- Visual reference retriever
- Canonical icon retriever
- Image generation adapter
- VLM review adapter
- Slide understanding semantic mapping adapter
- OpenCV and SAM measurement adapter
- PowerPoint constructor
- Native PowerPoint renderer

## Current implementation map

| Concern | Current implementation |
| --- | --- |
| Packaged deck design baseline | [`deck_design.json`](../src/slidecraft/defaults/deck_design.json) |
| Versioned pipeline policy | [`framework_pipeline.json`](../src/slidecraft/defaults/framework_pipeline.json) |
| Full-deck planning and structural routes | [`deck/`](../src/slidecraft/deck/) |
| Generation preparation orchestration | [`pipeline.py`](../src/slidecraft/orchestration/pipeline.py) |
| Tabler icon retrieval | [`icon_retrieval.py`](../src/slidecraft/orchestration/icon_retrieval.py) |
| Reviewer configuration | [`review_prompt.py`](../src/slidecraft/orchestration/review_prompt.py) |
| Edit prompt composition | [`edit_prompt.py`](../src/slidecraft/orchestration/edit_prompt.py) |
| Slide understanding semantic compiler | [`compiler.py`](../src/slidecraft/semantic_mapping/compiler.py) |
| Slide understanding measurement and fusion | [`measure_visual_scene.py`](../scripts/measure_visual_scene.py) |
| Editable reconstruction contract assembly | [`contract.py`](../src/slidecraft/reconstruction/contract.py) |
| Text authoring and fitting | [`text_fit.py`](../src/slidecraft/reconstruction/text_fit.py) |
| Constructor scene compilation | [`scene.py`](../src/slidecraft/reconstruction/scene.py) |
| Portable PowerPoint construction | [`scene_to_pptx.mjs`](../js/scene_to_pptx.mjs) |
| PowerPoint native rendering | [`scripts/render_with_powerpoint_mac.py`](../scripts/render_with_powerpoint_mac.py) |
| Agent capability and resumability surface | [`agent.py`](../src/slidecraft/agent.py) |

## Coverage boundaries

The policies above are explicit and versioned. Current coverage has these boundaries.

- Semantic planning supports host results and an OpenAI-compatible structured provider.
- Visual-reference retrieval uses local metadata and a maximum of three selected pages.
- Icon retrieval uses a lightweight Tabler keyword matcher.
- Semantic mapping accepts a host VLM result or an OpenAI-compatible structured vision provider.
- Native PowerPoint rendering exists as an optional explicitly authorized validation route. An automatic compare-and-refit loop is outside the certified direct-construction path.
- Reusable component manifests and previews are supported. Direct editable component import stays disabled until that implementation route passes constructor conformance tests.

Unsupported optional routes remain retrieval evidence and use a supported reconstruction path. They never publish partial output as successful.

## Acceptance definition

The framework is ready as a pipeline architecture when these conditions hold.

- Every run emits a versioned orchestration state and reconstruction handoff.
- Exact content, semantic design, selected assets, deck design configuration, and visual reference identities survive generation.
- Slide understanding separates reconstruction units from pixel evidence.
- Editable reconstruction routes every reconstruction unit to an explicit editable implementation or documented fallback.
- Icons use canonical SVGs and slot-based placement.
- Connectors use semantic graphs and native PowerPoint connectors.
- Text uses authored blocks and passes native PowerPoint overflow checks.
- Deck chrome is deterministic and excluded from image generation.
- All quality gates produce inspectable reports.
