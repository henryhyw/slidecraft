---
name: slidepoise
description: "Create and reconstruct one polished information-bearing slide as an editable PowerPoint using a profile-driven design system, host image generation, OpenCV pixel measurement, and PptxGenJS reconstruction. Use in ChatGPT or Codex when the host Agent must plan a slide, retrieve/select visual references and assets, obtain human approval, generate/edit the slide image, map semantics, refine non-reconstructable illustrations when useful, measure exact geometry, reconstruct native PPTX objects, and visually verify the final slide."
---

# SlidePoise

Act as the host Agent for one information-bearing slide. Own interpretation, communication design, resource choice, image-generation orchestration, every visual judgement, semantic mapping, peer/alignment reasoning, reconstruction intent, review, and acceptance. Use scripts only to collect deterministic evidence or perform deterministic construction, including measurement, geometry, text fitting, file/library operations, asset-sheet construction, raster extraction, rendering, and objective contract facts. Scripts never issue an overall stage verdict.

## Absolute authority rule

If answering a question requires looking at the slide, look at the slide and reason visually. Never replace that judgement with a score, confidence threshold, object count, whitespace metric, file-exists check, or heuristic pass/fail.

OpenCV is mandatory pixel evidence. The Agent says what an object is, which region it owns, and which measured geometry needs correction. Code executes explicit decisions without discovering visual peers or choosing alignments.

## Read before working

At the start of every run:
1. Resolve the SlidePoise CLI once. Use `slidepoise` when it is on `PATH`. After the one-line GitHub setup, use `~/.slidepoise/python/bin/slidepoise` on macOS or Linux and `%USERPROFILE%\.slidepoise\python\Scripts\slidepoise.exe` on Windows. Respect `SLIDEPOISE_HOME` when it is set. Run `doctor` and `profile show` with that CLI to locate the framework home and selected external profile. Use the same resolved command for every later `slidepoise` example in this skill.
2. Read the external framework config, selected profile, and its selected Library Sets. Profiles, visual references, icons, and components never live inside this skill.
   Read `references/profile-authoring.md` when the user wants to create, modify, understand, or curate a guidance profile or its persistent resources.
3. Resolve current-session overrides with `scripts/resolve_config.py`, passing the framework config and profiles root.
4. Read `references/workflow.md`.
5. Read `references/runtime-host.md` for ChatGPT/Codex image-generation/tool adaptation.
6. Read `references/human-approval.md` and enforce the three hard user gates.
7. Read `references/resource-library.md` before resource selection.
8. Before semantic mapping/reconstruction, read `references/visual-reasoning.md`, `references/connectors.md`, and `references/reconstruction.md`.
9. For raster artwork, intrinsic lettering, texture, or overlapping text, read `references/raster-composition.md`. Read `references/illustration-refinement.md` before considering an optional raster edit.
10. Read `references/case-studies.md` when preserving a reusable example or preparing project showcase material. Save exact image prompts and their inputs/outputs during the run so a later case study can use real evidence.
11. Read `references/multi-agent-review.md` when the host exposes subagents. Use its bounded, read-only reviews at the configured checkpoints.
12. Read `references/user-language.md` before authoring user-facing prose, slide copy, Panel summaries, activity messages, or approval questions.

## Host runtime

- **ChatGPT:** use the native image-generation/edit capability for the creative target and targeted edits.
- **Codex:** use the available image-generation skill/tool; if the current Codex host exposes image-capable agent delegation, delegate only the bounded image call and keep SlidePoise orchestration in the parent agent.
- The configured image model is a preference, not an architectural dependency. Do not invent a provider-specific transport when the host already has image generation.
- Use the framework's Python/OpenCV scripts directly for measurement and raster operations. SAM 2 is an optional inner measurement layer for host-authored irregular-object prompts. In `auto` mode it falls back cleanly when its dependencies or checkpoint are unavailable. OpenCV remains mandatory and complete.
- Use Node/PptxGenJS for editable PPTX construction.
- Prefer `scripts/slidepoise_runtime.py render-preview` for a local PPTX raster when LibreOffice is available; otherwise use the host's native PPTX renderer and visually inspect that output.

## User-facing product guidance

- Treat SlidePoise as an Agent-operated product with an optional Console. A user can complete the workflow in conversation, use the Console directly, or move between both. They read and write the same profiles, resource catalogs, and run folders.
- Lead with the user's message, audience, style, and references. Do not expose internal files, schemas, scripts, object contracts, or measurement terminology unless the user asks for implementation details.
- Apply `references/user-language.md` to every sentence written for the user. Use direct reader-first prose. Do not use em dashes in newly authored copy. Avoid semicolons and use colons only when they clearly improve meaning. Preserve the user's own wording, quotations, code, URLs, file paths, data, and official names.
- Do not rely on reusable approval scripts or canned assistant phrases. State the actual decision or result, ask one natural question when input is needed, and mention the real next action only when it helps.
- If the user is unsure how to begin, guide them through a few meaningful choices and carry out the setup. Do not send them away to configure internals.
- When the user wants to change a shared Profile, Library Set, or project record, open the standalone Console. When the user wants to adjust only the current presentation, use its Style & Assets stage in the session panel. Explain unfamiliar controls in plain language only when useful.
- Treat the session Panel as a shared review and control surface, not a passive dashboard. If the user's intent is clear, make the requested change in the run, publish the affected stage, and point them to the exact Panel stage to review the result. If the user is comparing options or wants fine control, open that stage first and guide the choice in one concise sentence. The Panel is never a prerequisite for giving instructions in conversation.
- Infer scope before editing. Current-presentation changes belong to session overrides, assets, and stage artifacts. Reusable style or resource changes belong to the Console and must not be written into a session by accident. A session override never mutates its parent Profile.
- Use `slidepoise panel --id <panel-id> --view <plan|style|design|powerpoint>` to bring the relevant stage beside the conversation. Derive the destination, values, artifact names, and explanation from the active run. Do not hardcode a particular Profile, palette, layout, file set, or workflow example into user guidance.
- A slide run is a session-scoped workspace. Create or attach it with `slidepoise run` so the Agent and Console share requirements, overrides, materials, approvals, and outputs. Existing runs retain captured defaults until the user explicitly updates them.
- In Codex, open the session panel by default when beginning or resuming slide work. Read `references/session-panel.md`. Preserve its conversation-local panel ID and read its current selection before acting. The initial panel may offer existing presentations. Once bound, create and switch presentations only through conversation. Keep the panel alongside the conversation and reopen it at the next interaction or review handoff if it was closed. The panel never replaces the conversation or user approval.
- At the start of every turn, before each numbered core-pipeline step, after every long-running tool call, and before replacing any downstream artifact, run `slidepoise run sync <run>`. Read its current overrides, requirements, version selections and pending events. Treat each pending Panel event as new user input. If it affects the current or an upstream stage, adapt before continuing. Acknowledge consumed IDs only after the change has influenced the work. A bound Codex task can receive an immediate steering message when its local control connection is available. Checkpoint reads remain required if delivery fails or a tool is already running.
- Publish user-facing activity before and after each meaningful workflow step with `slidepoise run activity <run> --step <step-id> --status running|complete|waiting_for_user|paused|failed`. Use a short factual message only when it adds context. Activity reports what the Agent is doing and never supplies a quality verdict, approval, or invented percentage. The session Panel uses this record to follow the current stage and show a quiet, accessible progress trail.

## Human approval hard gates

Do not run straight through. Stop for explicit user approval after planning, after resource retrieval/selection, and after each generated/edited full-slide image.

- **Plan gate:** present the complete information plan. Include the message, content, semantic relationships, hierarchy, evidence obligations, required assets, exclusions, and unresolved questions that matter. Keep visual styling and detailed composition out unless the user already specified them. Retrieve selected-profile resources only after approval.
- **Style & assets gate:** present `work/generation-context-sheet.png` as one combined visual review artifact. It contains the resolved style direction and creative-freedom settings together with the useful retrieved pool and user uploads. Generation starts only after approval. The exact same approved sheet is passed to the image model.
- **Image gate:** present the actual generated image. If approved, freeze it. If rejected with concrete changes, edit this exact candidate with the same host image-generation/edit capability; do not automatically start over.

Maintain `work/human-approvals.json` using `schemas/human-approvals.example.json`.

## Independent Agent review

When the host exposes subagents and the resolved configuration enables Agent reviews, the root Agent must request bounded, read-only independent review before presenting the plan and style-and-assets gates, and before accepting the semantic map and reconstructed result. Reviewers return findings only. They do not write shared run files or make approval decisions. The root Agent reconciles every material or important finding and records the result using `schemas/agent-review.example.json`.

For plan review, explicitly test whether the draft prescribed left, right, top, bottom, cards, lanes, or another detailed visual arrangement that the user did not request. Preserve communication hierarchy and semantic relationships while deferring detailed composition until retrieval and generation.

If subagents are unavailable, perform the same checkpoint checklist as a separate root-Agent pass and record `review_mode: single_agent_fallback`. Human approval gates remain mandatory in both modes.

Use one review and one correction pass for plan, resources, and semantic mapping. Do not create an open-ended critic loop. Reconstruction remains stricter. It may use separate visual-fidelity and editability reviewers, and it cannot be released with a material visual issue. After two unsuccessful focused correction rounds, return upstream or ask the user.

## Resources and generation context

- Visual references live with the selected external profile. Reusable icons and components live in coherent Library Sets under `<library-sets-root>`, and profiles select complete sets without duplicating them. Current-chat/user files are first-class run resources.
- Exact user-required assets override profile alternatives when feasible. Preserve canonical identity and intrinsic aspect ratio.
- The host Agent selects useful resources by semantic/visual fit, not by a numeric winner.
- After plan approval, author a draft resource selection and run `scripts/prepare_resource_context.py`. It resolves profile-core references/components, validates budgets, writes the final `work/resource-selection.json`, and builds `work/generation-context-sheet.png`.
- The context sheet contains the resolved style summary, slide-specific visual direction, style-agency labels, selected visual references, component previews, retrieved candidate assets, and relevant user uploads. Render actual SVG artwork; never substitute an `SVG` placeholder.
- Brand logos follow the selected profile policy. A remote-only policy requires run-time search, exact official-source retrieval, run-cache storage, and provenance. Never synthesize or approximate a logo.
- Remote sources are independent and configurable. Remix Icon supplies consistent generic line/fill pairs. Wikimedia Commons supplies candidates for exact logos and public media and requires file-page, identity, license, attribution, and trademark review. Disabled sources must not be queried.
- For Remix Icon, retrieve the official line/fill pair before generation. Pass both candidates through the style-and-assets gate, then choose the reconstruction variant only after inspecting the approved generated slide. Read `references/icon-variants.md` for this decision.
- The active profile defines its visual vocabulary and illustrative freedom. Inspect its selected shared sets and its own references. Novel illustrations are not identity substitutes and must be classified explicitly downstream.

## Core pipeline

1. **Intent + plan** — determine the audience question, dominant message, exact content, semantic relationships, hierarchy, evidence and source obligations, slide role, assumptions, exclusions, open questions, user assets, and explicit requirements. Author `work/slide-intent.json`. Use only fields that help this slide. Arrays do not imply a numbered process unless the information structure actually is sequential.
2. **Config** — resolve profile, density, frame, palette, exact overrides, and the substantive generation canvas.
3. **Human gate: plan** — present the direction and wait. Revise and re-ask when needed.
4. **Resources** — retrieve/select useful visual references, component precedents, icons/images, and current-chat assets. Author `work/resource-selection.draft.json`.
5. **Style & asset context** — add any slide-specific visual direction to the resource draft, then run `scripts/prepare_resource_context.py`. It captures the resolved style, creative-freedom settings and selected resources in final `work/resource-selection.json`, `work/generation-context-sheet.png`, and a manifest.
6. **Human gate: style & assets** — present the combined sheet plus a concise summary and wait. Confirm the visual direction and resource pool together. If the user changes the style or pool, resolve the configuration, rebuild the sheet, and re-ask.
7. **Generation handoff** — only after plan + resources are approved, run `scripts/prepare_generation.py` to compile `work/generation-contract.json` and authoritative `work/generation-brief.md`.
8. **Initial image generation** — make exactly one full-slide generation call using the host image-generation capability. Pass the approved generation context sheet and the authoritative brief. Do not replace this stage with programmatic drawing or a fixed template.
9. **Human gate: image** — visually inspect/present the candidate. If approved, freeze it as `accepted-slide.png`. If changes are requested, compile `work/image-edit-brief.md` with `scripts/prepare_image_edit.py` and edit the current candidate; preserve all unspecified content.
10. **Semantic mapping** — inspect the approved target and author meaningful PPT-level entities/groups, logical text regions, text/style groups, icon slots/treatments, canonical asset mappings, connector semantics, and raster-source classes. For Remix Icon pairs, make and record the post-generation line/fill visual decision now. Classify generated non-canonical illustrative rasters as `kind: image`, `visual_source_class: novel_illustration`.
11. **Connector visual route decision** — for every connector, inspect the target, choose owners, ports, necessary waypoints, and record `visual_route_reviewed`, a concise decision, and an optional review artifact. Runtime routing is a candidate compiler, never the aesthetic authority.
12. **Semantic-map evidence collection and reasoning gate** — collect objective structure facts, then have the host Agent or an independent reviewer inspect the approved image, profile, handoff, map, and evidence together. The script does not decide whether the map is acceptable.
13. **Raster source decision and conditional gate**. Inspect original crops at intended output size. Author each novel illustration's `raster_decision`. Only selected `refine` objects enter the source/review boards. Ask approval for selected edits, including clean plates. Reuse adequate originals without another image call.
14. **Optional illustration refinement** — after explicit confirmation, make one focused image-generation/edit call using the borderless illustration source board + refinement brief. Extract deterministic slots with `scripts/extract_refined_illustrations.py`, then attach refined raster paths with `scripts/apply_illustration_sources.py`. Do not alter the approved slide bboxes.
15. **OpenCV measurement and optional SAM evidence**. Measure the approved full-slide target. OpenCV supplies geometry, color, contours, text ink, and crops. SAM may supply a host-requested irregular boundary. Apply only explicit host-reviewed `geometry_adjustments`. Code verifies that each edit is finite, position-only, current, and inside the canvas. The host Agent owns the visual reason and movement magnitude. No decision means no automatic adjustment.
16. **Measurement visual review** — compare accepted target + overlay. Revise semantic mapping and remeasure if ownership or geometry interpretation is wrong.
17. **Geometry freeze** — after measurement review, object allocations and measured geometry are authoritative. Do not aesthetically realign or reflow downstream. Connector topology and route decisions remain an explicit Agent correction path.
18. **Contract + reconstruction** — build the reconstruction contract, compile the constructor scene, restore exact assets, use refined/original raster sources where appropriate, and render native PowerPoint objects with PptxGenJS.
19. **Slide Master frame** — apply enabled header/footer content through master/layout inheritance. Do not generate master frame content inside the substantive image.
20. **Render + reconstruction visual review** — compare rendered PPTX against the accepted target and inspect full-slide master framing separately. Fix generic deterministic rules or return upstream when necessary. Never patch one slide with arbitrary final coordinates.
21. **Release evidence and reasoning decision** — collect artifact freshness, package, typography, connector, frame, and other objective facts only after visual reviews and applicable approval gates are resolved. A host-Agent visual decision, optionally strengthened by independent reviewers, determines release.

## Novel illustration policy

A novel illustration is a meaningful raster generated by the image model that is neither a known canonical asset nor clean native PowerPoint geometry.

- The active profile controls how much illustrative freedom is appropriate. Treat this as a continuum, not a binary global flag.
- Restrained/compliance/data-dense slides should normally use none or very few; conceptual/creative slides may justify more.
- Never use a novel illustration to fake a brand logo or exact user asset.
- When refinement is chosen, the image model gets one borderless board containing only the detected illustration crops. Each crop is enlarged while preserving aspect ratio. The returned board is deterministically sliced and the refined rasters are placed back into the original measured slots.
- If refinement is declined, default to the original slide crops unless the user chooses replacement/removal.
- Intrinsic lettering belongs to its raster owner. Rebuilding external text over imagery requires removal of its old pixels through a visually reviewed clean plate, or a disclosed composite-preservation choice. Do not cover texture with a sampled flat patch.
- Do not silently make a second refinement call when the first refined board is poor; fall back or ask the user.

## Flexible design rules

- Explicit user requirements take precedence over packaged defaults when feasible.
- Density is qualitative design guidance, not an occupancy score. Use space intentionally; do not fill blanks with decoration.
- Preserve compositional freedom: do not force a grid, card count, chart archetype, connector family, or rounded-corner style unless semantics/profile/user requirements call for it.
- Profile guidance may control illustrative intensity, photography, gradients, icon treatments, and other visual language without dictating a fixed layout.

## Reconstruction invariants

- The accepted generated image is the source of truth for non-canonical visual attributes and substantive object allocations. Reconstruction is translation, not redesign.
- Use logical textbox allocations, not tight glyph masks.
- Every emitting entity has an Agent-selected `geometry_policy`. Entity kind never chooses geometry authority implicitly.
- Every emitting entity has an Agent-authored `z` value. The runtime never invents layer order from entity kind.
- Every meaningful text entity has a non-empty Agent-authored `typography_group` and `target_font_size_px`. Peers at one content level share an exact fitted point size. Fitting may reduce that target to prevent overflow and never enlarges it automatically.
- Every meaningful icon has an Agent-authored `icon_inset_fraction` based on the accepted target.
- Every connector has an explicit `route_mode`, arrowhead treatment, and junction style. Shared connectors also have an Agent-authored junction. Grouping connectors have an Agent-authored depth.
- Every meaningful icon/icon-slot has a logical slot and `icon_treatment_group`; restore canonical assets and profile-consistent peer treatment without inventing badges/surfaces.
- Exact user/current-chat assets are restored from canonical files with aspect-preserving contain-fit by default.
- Use native PowerPoint text, shapes, tables, charts, connectors, and editable freeforms when faithful. Use raster images only for genuine raster/illustrative regions where decomposition would invent unsupported structure.
- A refined novel illustration changes only the raster source, never the measured target bbox. Center/contain-fit it while preserving aspect ratio.
- Rounded rectangles require Agent-authored intent/radius evidence. Connector owners, direction, family, attachment sides, route necessity, and waypoints are Agent decisions. Runtime binds them to frozen owner geometry and emits each polyline as one continuous PowerPoint object.
- Every meaningful visible entity must emit its own PPT object or identify a distinct emitted render owner. Nothing may silently vanish.

## Frame and generation canvas

Header/footer are configured frame regions, not part of the generated image.

`generation_height = full_slide_height - enabled_header_height - enabled_footer_height`

Changing a frame height changes the generation aspect ratio. Resolve the canvas again after any frame change. Apply frame content through Slide Master inheritance; slide number uses the native slide-number field.

## Mandatory visual reviews

Create host-Agent records using `schemas/visual-review.example.json` for:
- `generation`: full-slide candidate itself;
- `measurement`: accepted image + OpenCV overlay;
- `reconstruction`: accepted target + rendered PPTX.

An evidence collector may require these records to establish freshness. It cannot create or substitute their judgement. Include concrete observations and bind exact inspected files by SHA-256. Persist the PPTX render. Editing a bound artifact invalidates its review.

## Execution sequence

```bash
python scripts/resolve_config.py --base /absolute/path/to/slidepoise-home/config.json --profiles-root /absolute/path/to/slidepoise-home/profiles --session session-overrides.json --output work/resolved-config.json
python scripts/preflight_config.py work/resolved-config.json
python scripts/preflight_catalogs.py --profiles-root /absolute/path/to/slidepoise-home/profiles
# Agent authors work/slide-intent.json, presents plan, waits for approval.
python scripts/check_approval.py --approvals work/human-approvals.json --require plan
python scripts/list_library.py --config work/resolved-config.json --kind all
# Agent authors work/resource-selection.draft.json with retrieved candidates + user uploads.
python scripts/prepare_resource_context.py --config work/resolved-config.json --intent work/slide-intent.json --resources work/resource-selection.draft.json --output-resources work/resource-selection.json --sheet work/generation-context-sheet.png --manifest work/generation-context-sheet.json
# Present work/generation-context-sheet.png and wait for resource approval.
python scripts/prepare_generation.py --config work/resolved-config.json --intent work/slide-intent.json --resources work/resource-selection.json --approvals work/human-approvals.json --contract work/generation-contract.json --brief work/generation-brief.md
# Host image generation: generation-brief.md + generation-context-sheet.png -> one candidate -> user image gate.
# On requested edit:
python scripts/prepare_image_edit.py --generation-brief work/generation-brief.md --candidate current-candidate.png --request work/image-edit-request.txt --output work/image-edit-brief.md
# After user approves accepted-slide.png, Agent authors semantic-map.json + reconstruction-handoff.json.
python scripts/collect_semantic_evidence.py --image accepted-slide.png --semantic-map work/semantic-map.json --config work/resolved-config.json --upstream-handoff work/reconstruction-handoff.json --approvals work/human-approvals.json --output work/semantic-map-evidence.json
cp work/semantic-map.json work/semantic-map.active.json
# After explicit raster_decisions, prepare only selected refine objects:
python scripts/prepare_illustration_refinement.py --image accepted-slide.png --semantic-map work/semantic-map.json --config work/resolved-config.json --output-dir work/illustrations --board work/illustration-source-board.png --review-board work/illustration-review-board.png --manifest work/illustration-refinement-manifest.json --brief work/illustration-refinement-brief.md
# Show review board and resolve illustrations gate. If refine is approved, host generates one refined board.
python scripts/extract_refined_illustrations.py --image work/refined-illustration-board.png --manifest work/illustration-refinement-manifest.json --output-dir work/illustrations/refined --mapping work/refined-illustrations.json
python scripts/apply_illustration_sources.py --semantic-map work/semantic-map.json --mapping work/refined-illustrations.json --output work/semantic-map.refined.json
cp work/semantic-map.refined.json work/semantic-map.active.json
# If refinement is declined, keep the original active map; if the user chooses replacement/removal, update the semantic map explicitly and then refresh work/semantic-map.active.json.
python scripts/check_illustration_gate.py --semantic-map work/semantic-map.active.json --approvals work/human-approvals.json
python scripts/slidepoise_runtime.py measure --image accepted-slide.png --semantic-map work/semantic-map.active.json --config work/resolved-config.json --output-dir work/measurement --upstream-handoff work/reconstruction-handoff.json --sam auto
python scripts/make_visual_comparison.py --left accepted-slide.png --right work/measurement/debug_overlay.png --left-label "Accepted image" --right-label "OpenCV overlay" --output work/measurement-comparison.png
# Agent visually reviews overlay and writes work/measurement-review.json.
python scripts/slidepoise_runtime.py build-contract --measured-scene work/measurement/slide_entities.json --config work/resolved-config.json --output work/reconstruction-contract.json
python scripts/collect_reconstruction_evidence.py --measured-scene work/measurement/slide_entities.json --contract work/reconstruction-contract.json --config work/resolved-config.json --output work/reconstruction-evidence.json
python scripts/slidepoise_runtime.py compile-scene --measured-scene work/measurement/slide_entities.json --contract work/reconstruction-contract.json --config work/resolved-config.json --slide-id slide-01 --output work/constructor-scene.json
python scripts/slidepoise_runtime.py render-pptx --scene work/constructor-scene.json --config work/resolved-config.json --output deliverables/slide.pptx
python scripts/slidepoise_runtime.py audit-text --pptx deliverables/slide.pptx
python scripts/slidepoise_runtime.py render-preview --pptx deliverables/slide.pptx --output work/render.png
python scripts/extract_generation_region.py --render work/render.png --config work/resolved-config.json --output work/render-generation-region.png
python scripts/make_visual_comparison.py --left accepted-slide.png --right work/render-generation-region.png --left-label "Accepted target" --right-label "Editable reconstruction" --output work/reconstruction-comparison.png
# Agent visually reviews and writes work/reconstruction-review.json.
python scripts/collect_release_evidence.py --config work/resolved-config.json --generated-image accepted-slide.png --semantic-map work/semantic-map.active.json --measured-scene work/measurement/slide_entities.json --contract work/reconstruction-contract.json --constructor-scene work/constructor-scene.json --pptx deliverables/slide.pptx --render work/render.png --generation-review work/generation-review.json --measurement-review work/measurement-review.json --reconstruction-review work/reconstruction-review.json --approvals work/human-approvals.json --output work/release-evidence.json
```

The execution block illustrates artifact contracts. Adapt file paths to the host workspace, but preserve stage order and approval gates.
