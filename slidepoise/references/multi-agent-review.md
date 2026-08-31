# Multi-Agent Review

Use this review layer when the host exposes subagents. It strengthens independent reasoning at selected checkpoints while preserving SlidePoise's ordered workflow and three human approval gates.

## Operating model

The root Agent remains the SlidePoise host Agent and owns the final decision. A reviewer is a bounded, read-only critic. It inspects frozen checkpoint artifacts and returns findings. It never edits the run, advances a gate, selects resources, generates an image, or accepts visual quality.

Do not split the entire pipeline across agents. Most SlidePoise stages depend on the exact output of the previous stage and share one mutable run folder. Use subagents where an independent reading can expose an omission or a mistaken assumption.

## Review checkpoints

### Plan review

Give the reviewer the user request, resolved profile, relevant profile guidance, and draft slide intent. Ask it to find:

- missed or contradicted user instructions
- missing front-half workflow stages such as communication planning, profile resolution, or retrieval
- claims unsupported by the current project
- visual structure prescribed before the user requested or approved it
- wording that would fail in the intended publication context

The reviewer must distinguish communication structure from visual layout. A plan may define hierarchy, relationships, evidence, and obligations. It should not assign content to left, right, top, bottom, cards, lanes, or a fixed diagram unless the user explicitly requested that level of structure.

### Style and asset review

Give the reviewer the approved plan, resolved profile, resolved style snapshot, resource selection draft, candidate provenance, and combined context sheet. Ask it to check semantic coverage, profile fit, creative-freedom boundaries, exact user assets, source licensing, unnecessary assets, and whether the selected pool prematurely dictates a layout.

### Semantic-map review

Give the reviewer the accepted slide, semantic map, reconstruction handoff, and profile. Ask it to inspect meaningful object coverage, render ownership, intrinsic raster lettering, connector semantics, typography and icon peer groups, canonical asset mappings, and likely reconstruction failure modes.

### Reconstruction review

Give the reviewer the accepted slide, rendered PPTX, visual comparison, constructor scene, and reconstruction contract. Ask it to identify material visual differences, editability losses, unexplained rasterization, connector defects, text fitting problems, and unsupported patch coordinates.

## Finding contract

Each finding contains:

- `id`
- `severity` as `material`, `important`, or `minor`
- `criterion`
- `evidence`
- `recommended_action`

The root Agent records one disposition for every material or important finding:

- `accepted` with the resulting revision
- `rejected` with concrete evidence
- `deferred` only when user input or an unavailable dependency is genuinely required

For plan, resources, and semantic mapping, use one independent review followed by one root-Agent correction pass. Do not create an open-ended critic loop. After the correction, the root Agent checks that the cited issues were addressed and proceeds to the applicable human gate. If a material disagreement still requires a new user decision, stop and ask the user.

Reconstruction is stricter because the released PowerPoint must have no unresolved material visual issue. A reviewer may inspect visual fidelity while another inspects editability, text, connectors, and raster boundaries. Corrections remain focused on concrete findings. After two unsuccessful correction rounds, return to the appropriate upstream artifact or ask the user. Do not continue an automatic review loop.

## Availability fallback

If subagents are unavailable, the root Agent performs the same checklist in a separate review pass and records `review_mode: single_agent_fallback`. This fallback preserves the contract but does not claim independence.

## Limits

Multi-Agent review improves coverage. It does not guarantee correctness. Evaluate it against real SlidePoise cases and track whether it catches known failures without producing excessive false alarms.
