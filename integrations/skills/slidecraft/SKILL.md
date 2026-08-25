---
name: slidecraft
description: Use Slidecraft tools to create, revise, validate, resume, and deliver editable PowerPoint presentations. Use when a user shares presentation material or asks to continue an existing Slidecraft project.
---

# Slidecraft

Slidecraft gives the host agent reliable presentation operations. The agent supplies the intelligence. Slidecraft stores evidence and decisions, searches local collections, measures images, constructs editable PowerPoint objects, and validates outputs.

## Ownership boundary

The host agent owns every decision that requires interpretation or design judgment. This includes clarifications, source interpretation, constraint classification, storyline, slide allocation, slide roles, header and footer content, semantic structure, reusable-resource selection, visual review, semantic mapping, reconstruction routes, canonical asset mapping, connector intent, and refinement groups.

Slidecraft owns mechanical work. This includes file ingestion, source locators, candidate search, schemas, provenance, artifact freshness, pixel measurement, bounded geometry changes, Office-safe text fitting, PowerPoint construction, package validation, and deterministic quality gates.

Never let a lexical score, filename, keyword, nearest object, raster contour, or first search result make a semantic decision. Search scores are discovery evidence. The agent inspects candidates in context and records the final choice with a rationale. Exact upstream asset IDs resolve directly.

Do not recreate reasoning inside Python or ask Slidecraft to infer a decision that the host agent can make from the conversation and artifacts.

## Start or continue

- When the user supplies a project name, ID, or folder, call `slidecraft_open_project` first. Use `create_if_missing` only when the user clearly intends new work. For a new project, pass the Agent's current workspace as `location` unless the user chose another folder.
- For a new body of work, create a project in the user's chosen folder. Use the managed default location when they express no preference.
- Convert the agreed conversation, audience, materials, constraints, desired result, density, and optional slide count into `slidecraft_prepare_deck`. Author the plan from the returned planning brief, then call the same tool with `deck_plan`.
- For existing work, inspect the workspace before calling any mutating capability.
- Treat `deliverables/` and `sources/` as user-facing. Treat `.slidecraft/` as durable Agent evidence that stays hidden during ordinary interaction.
- Never infer progress from filenames alone. Use artifact freshness, lifecycle, validation, and dependencies.

## Clarify before planning

Reason over the complete request and materials. Decide whether any unanswered question could materially change the deck. If so, ask up to three concise questions through the Agent app before preparing the brief. Record the answers, skipped choices, and delegated decisions in the brief.

Keep the set small. Avoid visual-style questions, details already answered by source material, and questions the Agent can safely decide. Make every question easy to answer and offer delegation to the Agent. If the user skips, record the delegation and continue using best judgment.

Use a host-native structured input surface when one is available. Ordinary conversational questions are a valid fallback.

## Plan and retrieve

- Author the deck plan with the host reasoning model. Slidecraft validates IDs, source coverage, route compatibility, available system layouts, asset policies, and deck length.
- Choose low-information structural slide roles when a stable system layout serves the communication job. Choose image generation for information-bearing slides. Supply the compatible route and layout ID in the plan.
- Author slide-specific header and footer content when deck chrome is enabled. Geometry and style come from configuration.
- For each generated slide, author the semantic design using the prepared prompt.
- Call `slidecraft_generate_slide` with the semantic design to obtain visual-reference, icon, and reusable-component candidates. Inspect their metadata and previews when useful.
- Author `resource_selection` with `authored_by: agent_reasoning`, stable candidate IDs, and a concise rationale for each choice. Select no more than the configured visual-reference limit.
- Use exact user or upstream assets when their identity is known. Choose canonical icon substitutions only through agent reasoning over the full affected set.

## Generate, understand, and reconstruct

- Preserve exact source content, provenance, constraints, and canonical assets.
- Inspect uploaded images and diagrams with the host's visual understanding before planning. Store the source-grounded interpretation as material content while retaining the original path. Path-only visual materials remain pending and cannot be silently reduced to file metadata.
- Register external model outputs before consuming them downstream.
- Keep candidate revisions separate until the applicable acceptance policy passes.
- Recompute stale descendants before publishing.
- Let image generation own informative slide composition. Use deterministic system layouts for covers and section dividers.
- After deck planning, call `slidecraft_generate_slide` for each information-bearing job. Follow its returned semantic-design, resource-selection, and image-generation phases.
- Call `slidecraft_measure_slide` with the Agent-authored visual analysis. It compiles the semantic scene and runs deterministic measurement.
- Assemble only when every planned slide has been reconstructed. Let `slidecraft_render_deck` derive and validate deck-plan order.
- During semantic mapping, identify authored objects and groups at PowerPoint granularity. Select a reconstruction route for every entity. Map icon slots to the exact Agent-selected upstream asset. Audit connector ownership, topology, direction, and clean native routing from relationship meaning and layout feasibility.
- After measurement, reason over the slide as a designed system. Author a refinement plan with `authored_by: agent_reasoning`. Name only peer groups that should align or normalize. An empty `alignment_groups` list is correct when no movement is warranted.
- Call `slidecraft_reconstruct_slide` with that plan. Slidecraft will reject movements that break containment, clearance, text fit, z-order, semantic order, or connector topology.
- Preserve the slide-understanding and editable-reconstruction contracts for text, canonical assets, icon slots, connectors, grouping, measurement evidence, native reconstruction, and validation.
- Return editable PowerPoint files and user-relevant reports under `deliverables/`.
- Call `slidecraft_open_project` again when you need fresh project facts. Interpret its progress and validation attention yourself. It never chooses the next action.
- Treat semantic reasoning and visual understanding as host-Agent work. The only configurable model connection in the current product is image generation. Register every Agent-authored result, inspect project facts when useful, and continue through your own reasoning.
- Review generated-image candidates autonomously against content, design, and reconstruction contracts. Accept strong candidates. When a material failure exists, reject the candidate and regenerate with a focused preservation-first correction.
- Never request operating-system authorization, credentials, or downloads during an active run. Report a structured capability state and use an available fallback.

## Project assets

Treat chat uploads, console uploads, and files placed directly in `sources/assets/` as entries in one project asset catalog. Adding an asset is catalog-only. It does not change the active deck plan, invalidate artifacts, or trigger generation.

When the user asks to use a newly available asset, inspect its semantic role and propose or apply the smallest planning change. In a multi-slide deck, `available` and `preferred` assets are allocated by the planner to suitable slides. `required_somewhere` means at least one suitable placement. It never means every slide. Slide-specific mandatory use exists only when the user explicitly names a slide or accepts a slide-level allocation.

## Interaction

If the user asks to stop, stop invoking capabilities. If they later ask to continue, inspect the workspace and proceed from the latest valid artifacts. Do not expose internal masks, contours, OCR fragments, or logs unless the user asks for technical evidence or diagnosis.

Use the six workflow tools when the host provides the Slidecraft MCP server. Python integrations can import the matching functions from `slidecraft.agent_workflows`.

The guided installer registers the MCP server so the Agent app starts it when needed. If the MCP connection is unavailable and shell access exists, import the six public functions from `slidecraft` and continue through the same workflow. Do not ask the user to manage an internal server process. When the user asks to see the dashboard, run `slidecraft console` and open the local page for them.

When the user asks for an output, call `slidecraft_open_project` and select from its deliverables and reviewable artifacts. Return the editable PowerPoint for final-deck requests. Return plans, generated slides, decisions, or reports for progress reviews. Do not require the user to know artifact keys or local paths.
