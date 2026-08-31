# Selective illustration refinement

Read `raster-composition.md` before selecting sources. A generated raster is eligible for consideration when it is neither a canonical asset nor faithfully reconstructable native geometry. Eligibility alone does not justify regeneration.

Inspect original crops at intended output scale and review relevant details. Record an explicit `raster_decision` for each meaningful novel illustration. Reuse sharp, sufficiently resolved originals. Select `refine` only for a visible problem worth editing. Keep intrinsic lettering inside its raster owner. Handle overlapping editable text through the clean-plate route.

## Selected source board

Run `scripts/prepare_illustration_refinement.py` after those decisions. Only entities selected for `refine` enter the board. Others retain their original sources. The borderless model-input board contains no added labels. A separate labeled review board supports user approval. Board enlargement is a presentation aid and does not prove that source detail has improved.

Ask approval for the identified entities and one focused edit. Record their `entity_ids` under the illustrations approval. Reusing accepted original crops does not require an additional creative-call gate. The three main plan, resource, and image gates remain unchanged.

## Focused edit and extraction

Send the selected source board and brief to the host image editor. Preserve subject, intrinsic lettering, aspect ratio, arrangement, and local appearance. Do not add external labels or merge slots. The edit may repair small generation defects, so it must be inspected as a new asset.

Run `scripts/extract_refined_illustrations.py` to crop known slots. Visually compare each returned asset with its original at intended output scale before applying it. If rejected, keep the original and update its decision. Do not silently spend another call.

Run `scripts/apply_illustration_sources.py` only for accepted selected items. It attaches `raster_source_override` without changing the measured placement. Inspect the reconstructed result for changed intrinsic text, lost grain, halos, color drift, crop edges, and residual foreground text.

Clean plates use the original panel or full-canvas coordinate system and targeted image editing. Do not send them through the isolated refinement-board path.
