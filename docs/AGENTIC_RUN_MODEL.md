# Agentic run model

## Control boundary

The host Agent owns conversation, decisions, retries, interruption, and continuation. Slidecraft stores durable project facts and immutable artifact revisions. The MCP server, Python API, CLI, and optional dashboard expose the same local capability layer. None of them owns a separate session state machine.

## Fresh-session behavior

The Agent resolves a human project name with `resolve_project`, then calls `workflow_status`. Existing artifacts, validation, dependencies, and deliverables are read from the project folder. If the user clearly intends new work, the same resolver can create the project and its default deck design.

## Durable dependency graph

Every registered artifact has a logical key, revision, hash, producer, dependency hashes, validation result, and lifecycle. Changing an active input makes affected descendants stale. Unrelated accepted slides remain usable.

Typical deck artifacts include the request, clarification decisions, intake, deck plan, frozen design, slide jobs, semantic prompts, generation packages, generated images, semantic scenes, measured scenes, reconstruction contracts, constructor scenes, and editable PowerPoint.

## Agent operation

The Agent calls `workflow_status` after material changes and selects the highest-priority action that fits the user's intent. A full autonomous run continues until the editable deck is complete. A user may ask to inspect, revise, regenerate, or stop at any point. Continuation begins from another workspace inspection and needs no pause or resume command.

External reasoning, vision, and image results are registered before downstream capabilities consume them. The host's native image tool is preferred when configured. A configured OpenAI or compatible image endpoint is the fallback.

## Quality behavior

Quality gates protect publication. They are not the source of the design logic. Semantic contracts, deterministic workers, and frozen deck rules must produce a valid first pass. A failed gate returns structured evidence and a recoverable next action. Unsupported routes never publish as successful output.

Final assembly requires every planned slide in deck order. It rejects stale or incomplete scenes, canvas mismatch, missing deck chrome, unsupported constructor routes, invalid text fit, and damaged PowerPoint packages.

## User-facing artifacts

The Agent returns the editable PowerPoint when asked for the final deck. It can also return the plan, generated slide, decision record, preview, or reconstruction report on request. Internal masks, OCR fragments, contours, caches, and logs remain hidden during ordinary use.
