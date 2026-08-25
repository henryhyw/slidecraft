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
- Inspect every source with the host Agent's document, data, and visual capabilities. Author concise source facts and interpretations with stable locators, authority, required-use decisions, exclusions, and provenance. Decide whether the grounded evidence supports credible planning. Ask a high-value question only when the answer could materially change the result.
- For a new or substantially replanned deck, read [references/planning.md](references/planning.md) for the brief contract and planning-quality standard.
- Convert the agreed conversation, audience, Agent-authored source evidence, constraints, desired result, density, and optional slide count into `slidecraft_prepare_deck`. Author the plan from the returned planning brief, then call the same tool with `deck_plan`.
- For existing work, inspect the workspace before calling any mutating capability.
- Treat `assets/`, `materials/`, and `deliverables/` as user-facing. Treat `.slidecraft/` as durable Agent evidence that stays hidden during ordinary interaction.
- `slidecraft_open_project` returns the discovered project visuals. Visually inspect every item marked `needs_agent_description`. In the next `slidecraft_prepare_deck` brief, include a `visual_assets` entry with its `asset_id`, a concise source-grounded `description`, `semantic_role`, and deck-level `usage_policy`. This updates the existing catalog entry without copying the file. Use the description and source context when planning its slide allocation. Never plan from the filename alone.
- Never infer progress from filenames alone. Use artifact freshness, lifecycle, validation, and dependencies.

## Work with the user before planning

Choose the collaboration posture from the request. For a new deck, use a collaborative posture unless the user explicitly delegates uninterrupted execution. The Agent app owns this conversational state. Slidecraft does not store an approval workflow.

In collaborative work, inspect the sources and complete any material research first. Share a concise synthesis that covers the evidence, research implications, proposed audience and decision, objective, governing direction, constraints, and important assumptions. Ask up to three easy questions only when the answers could materially change the story. Use a host-native structured input surface when available and ordinary conversation otherwise.

After resolving those questions, show one user-facing planning proposal before slide generation. Combine the recommended slide count, storyline phases, conclusion-led message for every slide, principal evidence allocation, required-topic placement, assumptions, and exclusions. Invite correction. The Agent may store the agreed brief and plan through `slidecraft_prepare_deck` after this discussion.

When the user explicitly delegates the work, make the same decisions with the same quality standard and continue without waiting. Surface the research synthesis, brief, storyboard, or plan when it helps the user or when they request it.

## Plan and retrieve

- Author the deck plan with the host reasoning model. Slidecraft validates IDs, source coverage, route compatibility, available system layouts, asset policies, and deck length.
- Build the plan around the audience's decision or consequential question. Compare plausible storylines and choose a specific governing answer supported by the evidence.
- Make the slide-message chain recover the complete argument. Every information-bearing slide needs a distinct claim, proof obligation, and reason to follow the preceding slide.
- Integrate required topics where they prove feasibility, economics, risk, or implications. Avoid a product tour, internal component inventory, or checklist structure unless it directly serves the audience's purpose.
- Consolidate overlapping claims and respect the configured density. A high-density consulting deck should carry several related evidence units per content slide.
- Choose low-information structural slide roles when a stable system layout serves the communication job. Choose image generation for information-bearing slides. Supply the compatible route and layout ID in the plan.
- Author slide-specific header and footer content when deck chrome is enabled. Geometry and style come from configuration.
- For each generated slide, author the semantic design using the prepared prompt.
- Call `slidecraft_generate_slide` with the semantic design to obtain visual-reference, icon, and reusable-component candidates. Inspect their metadata and previews when useful.
- Respect the configured icon search scope returned with the icon candidates. When online retrieval is enabled, Slidecraft searches the official Tabler collection and caches candidate SVGs locally. When it is disabled, choose only from the local icon collection. In both modes, inspect the candidate set and make the semantic choice yourself.
- Author `resource_selection` with `authored_by: agent_reasoning`, stable candidate IDs, and a concise rationale for each choice. Select no more than the configured visual-reference limit.
- Use exact user or upstream assets when their identity is known. Choose canonical icon substitutions only through agent reasoning over the full affected set.

## Generate, understand, and reconstruct

- Preserve exact source content, provenance, constraints, and canonical assets.
- Read uploaded images and diagrams with the host's visual understanding before planning. Store the Agent-authored interpretation with the original path and source locator. Decide how much evidence is relevant and whether it is sufficient for the requested deck.
- Register external model outputs before consuming them downstream.
- Keep candidate revisions separate until the applicable acceptance policy passes.
- Recompute stale descendants before publishing.
- Let image generation own informative slide composition. Use deterministic system layouts for covers and section dividers.
- After deck planning, call `slidecraft_generate_slide` for each information-bearing job. Follow its returned semantic-design, resource-selection, and image-generation phases.
- Call `slidecraft_measure_slide` with the Agent-authored visual analysis. It compiles the semantic scene and runs deterministic measurement.
- Reconstruct slides independently. Each `slidecraft_reconstruct_slide` call produces an editable one-slide PowerPoint under `deliverables/slides/` and refreshes `deliverables/current_deck.pptx` from every fresh reconstructed slide in plan order. Keep the current deck as the consolidated progress view. Let `slidecraft_render_deck` derive and validate final deck-plan completeness when every intended slide is ready.
- During semantic mapping, identify authored objects and groups at PowerPoint granularity. Select a reconstruction route for every entity. Map icon slots and supplied project images to the exact Agent-selected upstream asset. Use a screenshot crop for image content created by the image model. Audit connector ownership, topology, direction, and clean native routing from relationship meaning and layout feasibility.
- After measurement, reason over the slide as a designed system. Author a refinement plan with `authored_by: agent_reasoning`. Name only peer groups that should align or normalize. An empty `alignment_groups` list is correct when no movement is warranted.
- Call `slidecraft_reconstruct_slide` with that plan. Slidecraft will reject movements that break containment, clearance, text fit, z-order, semantic order, or connector topology.
- Preserve the slide-understanding and editable-reconstruction contracts for text, canonical assets, icon slots, connectors, grouping, measurement evidence, native reconstruction, and validation.
- Return editable PowerPoint files and user-relevant reports under `deliverables/`.
- Call `slidecraft_open_project` again when you need fresh project facts. Interpret its progress and validation attention yourself. It never chooses the next action.
- Treat semantic reasoning and visual understanding as host-Agent work. The only configurable model connection in the current product is image generation. Register every Agent-authored result, inspect project facts when useful, and continue through your own reasoning.
- Review generated-image candidates autonomously against content, design, and reconstruction contracts. Accept strong candidates. When a material failure exists, reject the candidate and regenerate with a focused preservation-first correction.
- Never request operating-system authorization, credentials, or downloads during an active run. Report a structured capability state and use an available fallback.

## Project assets

Treat chat uploads, console uploads, and files placed directly in `assets/` as entries in one project visual catalog. This includes logos, screenshots, photographs, illustrations, and other images that may appear in slides. Adding an asset is catalog-only. It does not change the active deck plan, invalidate artifacts, or trigger generation.

The host Agent visually annotates newly discovered project visuals before deck planning. A useful annotation says what the image visibly contains, what role it can serve in the presentation, and whether it is simply available, preferred, or required. Actual slide selection remains a separate planning decision.

When the user asks to use a newly available asset, inspect its semantic role and propose or apply the smallest planning change. In a multi-slide deck, `available` and `preferred` assets are allocated by the planner to suitable slides. `required_somewhere` means at least one suitable placement. It never means every slide. Slide-specific mandatory use exists only when the user explicitly names a slide or accepts a slide-level allocation.

For each slide, author an asset allocation for every selected project visual. Mark it optional when the image model may use it and mandatory when it must appear. Choose `icon_slot` for a compact icon or identity mark. Choose `image_region` for a screenshot, photograph, illustration, or other full visual. Slidecraft attaches every selected project visual to the generation request with its intrinsic aspect ratio and exact-content protection. During reconstruction, map a detected image to the selected asset only when the visual evidence and upstream role support that exact identity.

## Interaction

If the user asks to stop, stop invoking capabilities. If they later ask to continue, inspect the workspace and proceed from the latest valid artifacts. Do not expose internal masks, contours, OCR fragments, or logs unless the user asks for technical evidence or diagnosis.

Use the six workflow tools when the host provides the Slidecraft MCP server. Python integrations can import the matching functions from `slidecraft.agent_workflows`.

The guided installer registers the MCP server so the Agent app starts it when needed. If the MCP connection is unavailable and shell access exists, import the six public functions from `slidecraft` and continue through the same workflow. Do not ask the user to manage an internal server process. When the user asks to see the dashboard, run `slidecraft console` and open the local page for them.

When the user asks for an output, call `slidecraft_open_project` and select from its deliverables and reviewable artifacts. Return the editable PowerPoint for final-deck requests. Return plans, generated slides, decisions, or reports for progress reviews. Do not require the user to know artifact keys or local paths.
