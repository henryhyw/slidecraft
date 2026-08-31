# SlidePoise workflow

## 1. Resolve intent and propose the plan
Determine the audience question, dominant message, exact content, semantic relationships, hierarchy, evidence and source obligations, required assets, slide role, assumptions, exclusions, unresolved questions, and explicit requirements. Author `work/slide-intent.json`.

Apply `user-language.md` to every user-facing field. Preserve the user's wording where it carries intent or voice. Internal evidence may stay technical when the default Panel surface presents a clear display label and purpose.

The plan is a complete information contract for one slide. Its shape follows the content. A comparison may define comparison dimensions, a system may define entities and relationships, and an argument may define claims and evidence. Do not turn every array into a numbered sequence. Do not use the project's production pipeline as a default content structure.

### Human gate: plan
Present the direction in concise language and state that the next step is resource retrieval. Do not inspect/select packaged resources until the user explicitly approves. Record the decision in `work/human-approvals.json`.

## 2. Resolve config/profile
Load the framework config from the external SlidePoise home, select one isolated external profile, and apply explicit session overrides with `scripts/resolve_config.py`. Config and profile values control the visual system. They do not dictate the exact slide composition.

## 3. Retrieve resources and build the generation context sheet
After plan approval, inspect packaged catalogs plus relevant current-chat/user uploads. Select useful visual references, component precedents, icons/images, and other candidate assets by semantic/visual fit.

Author `work/resource-selection.draft.json`, then run `scripts/prepare_resource_context.py`. It resolves profile-core references and component metadata, validates budgets, writes final `work/resource-selection.json`, and creates `work/generation-context-sheet.png`.

The sheet serves two roles:
- the human-facing review artifact for the style-and-assets gate
- an image-generation input after approval

It begins with the captured Profile, resolved typography, palette, density, icon treatment, their creative-freedom modes, and any slide-specific visual direction. The resource pool follows below it. SVG icons must appear as real artwork, not placeholder text.

### Human gate: style & assets
Present the combined sheet plus a concise summary. Ask the user to confirm the visual direction and the resource pool together. If the user requests a style or asset change, resolve the config, update the pool, and rebuild the sheet. Do not call image generation until this combined artifact is approved.

## 4. Prepare the first-generation handoff
After plan + resources are approved, run `scripts/prepare_generation.py`. It compiles the exact resolved canvas, profile hard rules/guidance, intent, approved resource pool, context-sheet path, and generation budget into `work/generation-contract.json` and `work/generation-brief.md`.

Use the brief as authoritative. Do not weaken NON-NEGOTIABLE/profile constraints during the image call.

For a profile using `full_context_sheet`, pass the approved context sheet to the image model. Known identity assets remain canonical downstream; the sheet teaches the model what assets/references are available and what slots/visual language are plausible.

## 5. Generate and obtain image approval
Use the host image-generation capability described in `references/runtime-host.md`. Generate exactly one initial candidate.

The active profile may permit **novel illustrations** in addition to native presentation geometry and known assets. Treat illustrative freedom as profile/slide-role guidance rather than a universal on/off switch. A restrained/compliance/data-heavy slide should normally contain none or very little; a conceptual/creative slide may justify more.

Visually inspect the actual candidate and present it to the user.

### Human gate: image
If approved, freeze the image. If rejected with concrete visual/layout/style changes, edit the existing candidate with the same host image-edit capability and preserve every unspecified element. If a change alters the plan or asset pool, route back through the relevant earlier gate first. Never automatically explore alternate candidates.

## 6. Author the semantic map
Only after image approval, inspect the accepted image and author `work/semantic-map.json` plus reconstruction handoff.

Map meaningful PPT-level entities, not raster fragments. Keep semantic role separate from visual `text_style_role`. Every emitting entity needs an explicit `geometry_policy` and `z` layer. Every meaningful text entity needs `typography_group`, `target_font_size_px`, and an explicit style authority. Every meaningful icon or icon slot needs `icon_treatment_group` and `icon_inset_fraction`. Author connector owners, direction, family, route mode, arrowhead treatment, junction style, and any shared junction explicitly.

Classify image-like regions by source:
- known packaged/retrieved/user asset: `kind: image` + `upstream_asset_id`;
- allowed profile raster role such as a proprietary gradient: `kind: image` + appropriate role;
- generated illustration with no canonical source: `kind: image`, `visual_source_class: novel_illustration`, no `upstream_asset_id`;
- editable irregular native geometry: use `novel_visual`/freeform rather than the raster-illustration class.

Run `scripts/collect_semantic_evidence.py` before measurement to collect objective structural facts. Give the accepted image, semantic map, profile, handoff, and collected facts to the reasoning review. The script does not issue a semantic or visual verdict.

## 7. Resolve the conditional novel-illustration branch
If no `novel_illustration` entities exist, mark `illustrations.status=not_applicable` and continue.

Read `raster-composition.md` and inspect originals at their intended output size. Author per-object `raster_decision` records. If all are reused, no extra creative call is needed. For objects explicitly selected as `refine`, run `scripts/prepare_illustration_refinement.py`. It creates:
- borderless `work/illustration-source-board.png` for the image model;
- labeled `work/illustration-review-board.png` for the user;
- deterministic slot manifest;
- refinement brief carrying semantic roles, aspect ratios, active style/profile guidance.

### Conditional human gate: illustrations
Ask whether the user wants to refine the candidates in one extra focused image call, keep the original crops, replace with approved/native alternatives, or remove selected items. No refinement call without explicit confirmation.

If refinement is approved, send the borderless board + refinement brief to the host image-generation/edit capability. The returned board must preserve the arrangement/aspect ratios, improve semantic/visual fidelity, and avoid labels/borders/cross-slot composition.

Run `scripts/extract_refined_illustrations.py`, then `scripts/apply_illustration_sources.py`. The refined raster changes only the image source; target slide bboxes remain those of the approved full-slide composition.

If refinement is declined, default to original crops unless the user chose a replacement/removal. If a refinement output is bad, do not silently spend another call; fall back or ask.

## 8. OpenCV measurement, optional SAM evidence, and host corrections
Before measurement, run `scripts/check_illustration_gate.py`.

Measure the accepted full-slide target with OpenCV using the active semantic map. Geometry, color evidence, contours, text ink, and source crops come from the approved target. If an image entity has `raster_source_override`, use that raster as its reconstruction pixel source while keeping measured geometry from the approved slide.

For an irregular filled object whose boundary benefits from segmentation, the host Agent may add an eligible `segmentation_role` and `segmentation_preference: sam_if_available`. In `auto` mode the measurement runtime writes SAM candidate masks when the configured checkpoint is available and otherwise records a clean OpenCV fallback. It never chooses the highest-scoring mask as visual authority. Inspect the candidates, record `sam_candidate_index` for a useful boundary, then remeasure. Without that decision, OpenCV remains active. Use `required` only when candidate production is explicitly required.

Measurement preserves positions unless the host supplies explicit `geometry_adjustments` after visual inspection. Corrections bind their original boxes. Code verifies structural safety without imposing an aesthetic movement limit. No script discovers peers or chooses alignment targets. The Agent must inspect the resulting overlay and check containment and declared non-overlap relationships.

Visually compare accepted image + OpenCV overlay. If ownership/mapping is wrong, revise semantic mapping and remeasure.

## 9. Freeze geometry
After measurement review, substantive object allocation and measured geometry are frozen. Do not aesthetically redistribute, reflow, simplify, or align downstream.

Connector topology is a semantic exception: verify the intended relationship and reconstruct correct owner ports/routes even if the raster connector path was wrong. Do not move owner boxes to preserve a bad generated connector.

## 10. Build contract and reconstruct
Build the reconstruction contract from fresh measurement, resolved config/profile, and exact asset handoff. The runtime:
- fits every declared typography group at one common safe point size;
- restores exact assets without stretching;
- reconstructs coherent icon treatment groups;
- adapts optional chart/table component grammar to real authored data/content;
- preserves unspecified/proprietary raster regions instead of inventing unsupported editable stops;
- inserts novel-illustration original/refined rasters into frozen bboxes with aspect-preserving contain-fit when requested;
- computes connectors from frozen semantic owners;
- requires every meaningful visible entity to emit or have a distinct emitted render owner.

## 11. Apply master frame, render, and visually review
Apply enabled header/footer content through Slide Master/layout inheritance. Slide number uses a native slide-number field.

Render the PPTX. Prefer the packaged `render-preview` path when LibreOffice is available; otherwise use the host's native PPTX renderer. Compare the substantive generation region directly against the accepted target and inspect the full frame separately.

The host Agent judges fidelity, text hierarchy, asset treatment, raster quality, connector routing, collisions, density, whitespace, and overall professional quality. Reconstruction is translation, not redesign.

## 12. Release
Only after generation, measurement, and reconstruction visual reviews are accepted, and the conditional illustration gate is resolved when applicable, collect the release evidence. The evidence collector reports facts and structural blockers. The host Agent makes the release decision after inspecting the accepted target and rendered PowerPoint. No programmatic pass substitutes for that reasoning.
