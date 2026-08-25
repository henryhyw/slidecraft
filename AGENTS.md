# Working with Slidecraft

Slidecraft helps agent apps create and revise editable presentations. Use its tools to manage project files and results while the agent app manages the live conversation.

## Begin from a project name

1. Call `slidecraft_open_project` with the name, stable project ID, or local folder supplied by the user.
2. Set `create_if_missing` only when the user clearly intends to start a new project.
3. Reason over the user's request and the returned progress, sources, and deliverables.
4. Use the remaining workflow tools according to the work the user wants.

For new work, inspect every supplied source with the Agent app's native document, data, and visual capabilities. Author the source facts, interpretations, authority, required-use decisions, exclusions, and constraint classifications in the brief. Keep each source path beside the Agent-authored evidence so provenance remains intact. Decide whether the evidence supports credible planning and ask only high-value questions when it does not. Call `slidecraft_prepare_deck` after making those decisions. The first call returns planning guidance. Author the plan, then call the same tool with `deck_plan`.

For a new deck, default to collaborative planning unless the user explicitly delegates uninterrupted execution. Share the source and research synthesis before recording the final brief. Before slide generation, show a combined planning proposal with the audience decision, governing message, recommended slide count, storyline phases, one conclusion-led message per slide, principal evidence allocation, required topics, assumptions, and exclusions. In delegated work, make the same decisions and continue without waiting.

New projects already contain a frozen deck-design baseline. The host Agent authors the storyline, slide routes, structural-layout choices, header and footer content, and content-slide semantic designs. For each content job, use `slidecraft_generate_slide`. It returns semantic-design guidance, resource candidates, or an image-generation brief according to the information supplied in the call.

The user does not need to know project paths, artifact keys, or pipeline stages. Explain decisions in ordinary presentation language.

Lead public-facing explanations with what the user can do and what result they will receive. Describe setup choices through their purpose. Keep implementation boundaries and failure policy in technical contracts, and avoid defensive caveats in user guidance.

## Work conversationally

- Ask only high-value questions that can materially change the message, audience decision, scope, evidence, or required output.
- Own every interpretive decision, including source interpretation, evidence sufficiency, constraint classification, retrieval selections, semantic mapping, reconstruction routes, connector topology, and bounded refinement groups. Slidecraft records, validates, and executes those decisions.
- Respect a request to inspect, revise, regenerate, continue, or deliver one artifact without forcing a full restart.
- Use the host's image-generation capability when available. Use Slidecraft's configured image provider when the host has no image tool or the user selected that provider.
- Register every external model result before another capability consumes it.
- Reopen the project when a fresh factual inventory would help. It reports facts and never chooses the next action.
- Never assemble a partial planned deck. `slidecraft_render_deck` derives deck order from the active plan and rejects missing, extra, stale, or reordered slides.

## Surface useful results

`slidecraft_open_project` returns deliverables, source material, and reviewable intermediate artifacts. Return the editable PowerPoint when the user asks for the deck. Return plans, generated slides, decisions, or reports when they ask to review progress. Keep masks, OCR fragments, contours, caches, and logs hidden unless the user requests technical evidence.

## Interfaces

Prefer the six Slidecraft workflow tools when the MCP server is connected. The optional dashboard reads and edits the same durable files. It does not own workflow progression.
