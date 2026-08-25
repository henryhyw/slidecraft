# Working with Slidecraft

Slidecraft helps agent apps create and revise editable presentations. Use its tools to manage project files and results while the agent app manages the live conversation.

## Begin from a project name

1. Call `resolve_project` with the name, stable project ID, or local folder supplied by the user.
2. Set `create_if_missing` only when the user clearly intends to start a new project.
3. Call `workflow_status` with the resolved project location.
4. Continue with the highest-priority valid action that serves the user's request.

For new work, turn the conversation into an authoritative brief and call `set_deck_brief`. Include source-grounded interpretations for uploaded images and diagrams. Keep the source path alongside the interpretation so provenance remains intact.

New projects already contain a frozen deck-design baseline. Deck planning creates deterministic constructor scenes for structural slides and content-slide jobs for image generation. For each content job, call `prepare_slide`, use the returned prompt with the host reasoning model, then call `prepare_generation` with that semantic result. Continue from `workflow_status` after every registered artifact.

The user does not need to know project paths, artifact keys, or pipeline stages. Explain decisions in ordinary presentation language.

Lead public-facing explanations with what the user can do and what result they will receive. Describe setup choices through their purpose. Keep implementation boundaries and failure policy in technical contracts, and avoid defensive caveats in user guidance.

## Work conversationally

- Ask only high-value questions that can materially change the message, audience decision, scope, evidence, or required output.
- Respect a request to inspect, revise, regenerate, continue, or deliver one artifact without forcing a full restart.
- Use the host's image-generation capability when available. Use Slidecraft's configured image provider when the host has no image tool or the user selected that provider.
- Register every external model result before another capability consumes it.
- Call `workflow_status` after material changes so work resumes from durable evidence instead of chat memory.
- Never assemble a partial planned deck. `render_pptx` derives deck order from the active plan and rejects missing, extra, stale, or reordered scenes.

## Surface useful results

Use `project_detail` to find deliverables, source material, and reviewable intermediate artifacts. Return the editable PowerPoint when the user asks for the deck. Return plans, generated slides, decisions, or reports when they ask to review progress. Keep masks, OCR fragments, contours, caches, and logs hidden unless the user requests technical evidence.

## Interfaces

Prefer the Slidecraft MCP tools when they are connected. The Python capability API and `slidecraft agent-call` provide the same behavior. The optional dashboard reads and edits the same durable files. It does not own workflow progression.
