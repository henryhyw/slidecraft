# Human approval gates

Use these gates in ChatGPT and Codex. The user controls when the workflow advances and when another creative image call is made. Never silently skip a gate.

## Gate 1 — plan approval
After intent planning, stop and present the complete information direction. Include the dominant message, content, semantic relationships, hierarchy, evidence obligations, known required assets, exclusions, and unresolved questions that matter. Do not assign a visual style or detailed composition unless the user already specified it.

State the proposed message and essential content in natural language. Ask whether the direction is accurate. Mention resource retrieval as the next action. Adapt the wording to the conversation and avoid a stock approval script.

Do not retrieve/select packaged resources until the user explicitly approves. Record the decision in `work/human-approvals.json`.

## Gate 2 — style and asset approval
After style resolution and resource selection, create `work/generation-context-sheet.png`. It must show the captured Profile, resolved style, creative-freedom settings, slide-specific visual direction, useful retrieved asset pool, selected visual references and component previews, and relevant user uploads together. Render real icon artwork, including SVGs. Keep the written style and resource summary alongside the sheet.

State what the user should inspect in the Style & Assets sheet. Ask whether the visual direction and material pool are right. Explain that approval sends the same context into generation. Adapt the wording to the actual choices shown.

Do not prepare/call generation until the user approves the sheet/resource set. If the user changes it, update `work/resource-selection.json`, rebuild the sheet, and ask again.

## Gate 3 — generated-image approval
Generate exactly one initial image, visually inspect the actual candidate, and show it to the user. Do not automatically regenerate because of the Agent's own preference.

Show the generated slide and ask whether to approve it or adjust it. Explain that approval freezes this composition for reconstruction. If the user wants changes, make clear that the current image will be edited.

If approved, freeze the image. If rejected with concrete changes, make exactly one targeted edit of the current candidate for that response, preserving every unspecified element. If rejected without instructions, ask what to change before another image call.

## Conditional gate — novel illustration refinement
After the approved slide is semantically mapped, inspect raster sources and record per-object reuse or editing decisions following `raster-composition.md`. Adequate original crops need no additional creative call. If no editing is selected, set `illustrations.status=not_applicable` and continue.

For selected edits, show the relevant review board or same-canvas clean-plate source and ask whether the user wants one additional focused edit. Record the approved `entity_ids`. Offer these choices naturally:
- refine them into cleaner/high-resolution slide-style rasters;
- keep the original slide crops;
- replace one or more with an already-approved asset/native approximation where sensible;
- remove one or more if the user explicitly wants them gone.

Explain which illustrative elements need a decision and why. Offer the applicable choices in ordinary language. Mention the extra image call only when refinement is available. Adapt the question to the actual elements and avoid repeating a fixed script.

Do not make the refinement call without explicit confirmation. One confirmation authorizes one refinement call. If the user declines without specifying another option, default to keeping the original crops.

## Approval artifact
Initialize `work/human-approvals.json` from `schemas/human-approvals.example.json`. Required hard gates are plan, resources, and image. `illustrations` requires approval with exact entity IDs when raster editing is selected. Original reuse does not reopen the image gate.

A direct affirmative response to the immediately preceding gate counts as approval. Silence does not. If a response says approve but also requests a change, apply/route the change first.

When plan changes, reset downstream resources/image/illustrations. When resources change, reset image/illustrations. When the approved image changes, reset illustrations.
