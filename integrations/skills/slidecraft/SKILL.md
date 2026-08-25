---
name: slidecraft
description: Create, revise, reconstruct, validate, and resume traceable editable slide decks with the Slidecraft capability framework. Use when a user provides presentation materials or asks to work on an existing Slidecraft project.
---

# Slidecraft

Use Slidecraft as a composable capability system. Interpret the user's intent and choose the smallest useful operations. Do not force a fixed sequence when the user asks to inspect, revise, regenerate, or continue selected work.

## Start or continue

- When the user supplies a project name, ID, or folder, call `resolve_project` first. Use `create_if_missing` only when the user clearly intends new work.
- For a new body of work, create a project in the user's chosen folder. Use the managed default location when they express no preference.
- Convert the agreed conversation, audience, materials, constraints, desired result, density, and optional slide count into one `set_deck_brief` call. This lets an MCP-only host begin without writing internal files.
- For existing work, inspect the workspace before calling any mutating capability.
- Treat `deliverables/` and `sources/` as user-facing. Treat `.slidecraft/` as durable Agent evidence that stays hidden during ordinary interaction.
- Never infer progress from filenames alone. Use artifact freshness, lifecycle, validation, and dependencies.

## Clarify before planning

Before deck planning, prepare optional high-value clarifications. Ask only questions whose answers can materially change the audience decision, desired action, governing answer, complication, scope, baseline, proof requirement, stakeholder sensitivity, or success criterion.

Keep the set small. Avoid visual-style questions, details already answered by source material, and questions the Agent can safely decide. Make every question easy to answer and offer delegation to the Agent. If the user skips, record the delegation and continue using best judgment.

Use a host-native structured input surface when one is available. Ordinary conversational questions are a valid fallback.

## Operate the pipeline

- Preserve exact source content, provenance, constraints, and canonical assets.
- Inspect uploaded images and diagrams with the host's visual understanding before planning. Store the source-grounded interpretation as material content while retaining the original path. Path-only visual materials remain pending and cannot be silently reduced to file metadata.
- Register external model outputs before consuming them downstream.
- Keep candidate revisions separate until the applicable acceptance policy passes.
- Recompute stale descendants before publishing.
- Let image generation own informative slide composition. Use deterministic system layouts for covers and section dividers.
- After deck planning, call `prepare_slide` for each information-bearing job. Use its semantic-planning prompt with the host reasoning model, then call `prepare_generation` with the resulting structured semantic design.
- Assemble only when every planned slide has a fresh constructor scene. Let `render_pptx` derive and validate deck-plan order.
- Preserve the slide-understanding and editable-reconstruction contracts for text, canonical assets, icon slots, connectors, grouping, measurement evidence, native reconstruction, and validation.
- Return editable PowerPoint files and user-relevant reports under `deliverables/`.
- Call `workflow_status` after each material capability completes. Execute its highest-priority next action until the status is `complete` or the user explicitly stops.
- Treat external model boundaries as Agent work. Use a host-native model when available and use the configured provider fallback otherwise. Register the result, then continue from `workflow_status`.
- Review generated-image candidates autonomously against content, design, and reconstruction contracts. Accept passing candidates. Reject and regenerate failed candidates with a preservation-first correction.
- Never request operating-system authorization, credentials, or downloads during an active run. Report a structured capability state and use an available fallback.

## Project assets

Treat chat uploads, console uploads, and files placed directly in `sources/assets/` as entries in one project asset catalog. Adding an asset is catalog-only. It does not change the active deck plan, invalidate artifacts, or trigger generation.

When the user asks to use a newly available asset, inspect its semantic role and propose or apply the smallest planning change. In a multi-slide deck, `available` and `preferred` assets are allocated by the planner to suitable slides. `required_somewhere` means at least one suitable placement. It never means every slide. Slide-specific mandatory use exists only when the user explicitly names a slide or accepts a slide-level allocation.

## Interaction

If the user asks to stop, stop invoking capabilities. If they later ask to continue, inspect the workspace and proceed from the latest valid artifacts. Do not expose internal masks, contours, OCR fragments, or logs unless the user asks for technical evidence or diagnosis.

Use MCP tools when the host provides the Slidecraft server. Otherwise use the Python capability API or `slidecraft agent-call`. The business behavior and artifact contracts are the same across transports.

When the user asks for an output, call `project_detail` and select from its deliverables and reviewable artifacts. Return the editable PowerPoint for final-deck requests. Return plans, generated slides, decisions, or reports for progress reviews. Do not require the user to know artifact keys or local paths.
