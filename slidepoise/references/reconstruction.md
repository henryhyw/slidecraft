# Reconstruction rules

## Native-first routes
Use native PowerPoint text, shapes, tables, charts, and connector graphs when their semantics are known. Restore exact canonical SVG/image assets selected upstream.

Use a fitted freeform only for a meaningful editable irregular shape that cannot be represented by a standard PowerPoint primitive. Use a screenshot crop for a genuine raster/illustrative region when no exact reusable asset exists and editable decomposition would invent unsupported structure. This raster route is also appropriate for a proprietary/profile gradient whose exact editable stops are not specified and no canonical gradient asset is available.

## Profile authority
The resolved profile contributes exact design values and hard rules before reconstruction. The accepted generated image remains the source of truth for composition and non-canonical visual details. Once accepted, its substantive geometry is frozen: reconstruction must not aesthetically realign, redistribute, simplify, or delete meaningful content.

If a profile rule conflicts with a generated candidate, that conflict should normally have been caught during generation review. Mechanical evidence collection may report explicit violations that can be established without visual judgement. The reasoning gate decides the response.

## Text
First distinguish native presentation text from lettering owned by a raster. Read `raster-composition.md` for intrinsic lettering, expressive handwriting, clean plates, and overlapping foreground text.

The host Agent assigns semantic `role`, visual `text_style_role`, logical textbox region, a non-empty `typography_group`, and `target_font_size_px` for every meaningful text entity. `role` describes meaning. `text_style_role` selects the configured style and readability policy. `typography_group` records the font-size hierarchy and content level. Textboxes at one content level share one group and one target size even when their wording or box dimensions differ. Shared role names alone do not establish visual peerhood. The Agent can assign different groups when local hierarchy calls for it and must explain that choice in its review. A singleton level still has a group. Members of a group must use one `text_style_role`. The fitting runtime may reduce a shared target to prevent overflow. It never increases the Agent's target because a box has spare room.

OpenCV supplies text-ink and foreground/background evidence. The deterministic fitter finds the largest safe size that fits every member of each declared typography group and applies that exact point size to all members. Missing groups are invalid; the runtime must never fall back to fitting an ungrouped textbox independently. It never emits a known non-fitting fallback or silently shrinks one peer independently. If one member cannot fit at the configured readability floor, reconstruction fails so the host Agent can revise the text allocation, wording, or hierarchy assignment upstream.

The resolved profile may restrict font families, italics, tracking, or text colours. When such restrictions are mechanically checkable, semantic-map evidence should report them early so the reasoning gate can correct the map before reconstruction.

Observed italic and tracking treatments use `style_hint.italic` and `style_hint.char_spacing_px`. Tracking is measured in accepted-image pixels and participates in text fitting. These controls do not identify a font automatically. Compare actual rendered weight, spacing, baseline, and line breaks before accepting a substitution.

Check fonts in the renderer as well as in PowerPoint. A correct font-family string in the PPTX does not establish that the preview renderer found that font. When a host needs a Fontconfig file, keep it in the run or external environment, pass it through `render-preview --font-config`, and retain the font-family choice with the case. Do not put machine-specific font paths or proprietary font binaries in the skill.

## Novel illustrations
A `kind: image`, `visual_source_class: novel_illustration` entity is a generated raster with no canonical upstream asset. Its geometry comes from the approved slide and OpenCV measurement. Its pixel source may be either the original accepted-slide crop or a user-approved refined raster.

If `raster_source_override` is present, treat that file as the authoritative pixel source for reconstruction while preserving the entity's measured slide bbox. Use aspect-preserving contain-fit and center it in the frozen box. Do not stretch the refined raster or move neighboring content to accommodate it.

Novel illustration refinement does not reopen slide composition. It only upgrades the raster source inside an already approved slot. If a refined source is not good enough, fall back to the original crop unless the user explicitly requests another change.

## Assets and user uploads
The reconstruction handoff retains the exact canonical path/ID chosen by the host Agent. Exact user/current-chat assets are first-class canonical assets. Preserve intrinsic aspect ratio and contain-fit them into their Agent-authored logical slot by default. Do not stretch an asset to mimic a generated placeholder. If the fit leaves a materially wrong composition, revise the slot or upstream design and rerun.

## Icons
SlidePoise uses the existing icon pipeline for icons and pictograms alike. Do not introduce a second asset/entity concept just to distinguish those brand terms.

The logical icon slot is separate from the designed surface. Always use the Agent-authored slot for canonical-asset fitting and layout constraints. Every meaningful icon or icon slot also carries an `icon_treatment_group` that represents its local peer-level treatment family. Emit a surface only when `slot_surface.visible` is true because the accepted design intentionally uses a real icon background surface. A faint generation-only localization boundary is scaffolding and must map to `slot_surface.visible=false`. When the icon is meant to sit on a larger colored parent panel or card, omit any white slot box so the icon background remains transparent and the parent colour shows through. Members of one `icon_treatment_group` must reconstruct with one coherent glyph treatment family and one coherent surface treatment. Apply the peer group's explicit profile treatment to every member while preserving canonical glyph geometry.

For a recolourable proxy, use `style_hint.glyph_color` or `style_hint.glyph_gradient`; do not assign both. Exact profile assets should preserve their canonical artwork. A profile may constrain proxy colours/gradients and visible surface fills. Do not add a default badge, holding shape, surface, scaffold border, or white knockout tile that was not part of the accepted design.

## Reusable components
A chart or table may carry an optional `component_id` referencing the selected profile's private component catalog. The host Agent assigns this only when the accepted target actually uses that component grammar.

A component is not copied verbatim. Start from its generic constructor defaults, then override with the entity's real data/content, category/series or row/column count, labels, geometry, and any visual differences visible in the accepted target. The native donor PPTX/slide remains an authoritative editable precedent and provenance source, not sample content to paste. If adaptation would make the precedent misleading or awkward, omit `component_id` and reconstruct normally.

## Data visualisation
When an editable chart has authored data but no explicit series colours, use the resolved profile's chart colour defaults rather than PowerPoint's theme colours. Explicit Agent-authored chart colours remain authoritative only when they are compatible with the selected profile or an intentional profile exception.

## Shape geometry
### Authored paths and stacking

For an intentional editable curve, a shape entity may use `shape: authored_path`, `reconstruction_route: fitted_freeform`, and `path_commands_px`. Each command uses absolute accepted-image pixel coordinates. `M` and `L` carry `point`, `C` carries `control1`, `control2`, and `point`, and `Z` closes a path. Omit `Z` for open rules and arrows. The host chooses control points through visual inspection. The runtime only transforms and emits them.

An explicit numeric `z` controls stacking, with lower values behind higher ones. Inspect text, raster repairs, and original crop overlaps in the rendered slide. Do not let kind defaults conceal an intended layer order.

A freeform arrow remains an editable path. It does not automatically attach to moved objects. Use the semantic connector route when owner binding is required and disclose that distinction in examples.

### Rounded geometry

The host Agent visually classifies rounded-rectangle intent and records the observed radius. The runtime translates that radius into an editable PowerPoint roundRect adjustment. It applies only PowerPoint's technical half-short-side limit. Code does not impose an aesthetic rounding cap.

The final visual review must compare silhouettes. An in-range radius is only mechanical evidence and does not establish fidelity.

## Layout integrity and survival
Only the host Agent decides which independent content regions must not overlap. Record those pairs in the semantic map. The runtime enforces the declared pairs after canonical asset placement and text fitting.

Every meaningful visible entity in the accepted target must survive reconstruction. It must either emit its own PowerPoint object or explicitly identify a distinct emitted `render_owner` that replaces/owns it. `measurement_evidence` may be non-emitting only when `meaningful_visible=false`. Never remove an entity merely because a canonical asset is unavailable or because the Agent thinks the slide would be simpler without it; such a candidate should have been rejected upstream.

## Alignment
The host inspects the measured overlay and authors any necessary local corrections in `geometry_adjustments`. Runtime applies those exact, version-checked decisions. Without a decision it keeps the measured position. It does not infer peers, choose median anchors, snap nearby objects, or decide whether a movement is visually appropriate. Re-render and inspect after every correction batch. Return material compositional changes to the user image gate.

## Master frame
The substantive image excludes enabled header/footer regions. Reconstruction maps that image into the derived generation region, then the renderer creates inherited frame content through the PowerPoint Slide Master/layout hierarchy.

PowerPoint slides do not expose a native slide-header placeholder, so header text/rules are master-layer inherited elements. Footer text/rules are also inherited master/layout elements. Slide number uses PowerPoint's native slide-number field on the master. These frame elements must not be emitted as ordinary slide objects.
