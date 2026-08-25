# Agentic run model

## Conversation and project memory

The agent app manages the conversation and decides what to do next. Slidecraft saves project facts and versioned results. MCP, Python, CLI, and the dashboard all work with the same project record.

## Fresh-session behavior

The Agent resolves a human project name with `resolve_project`, then calls `workflow_status`. Existing artifacts, validation, dependencies, and deliverables are read from the project folder. If the user clearly intends new work, the same resolver can create the project and its default deck design.

## Durable dependency graph

Every registered artifact has a logical key, revision, hash, producer, dependency hashes, validation result, and lifecycle. Changing an active input makes affected descendants stale. Unrelated accepted slides remain usable.

Typical deck artifacts include the request, clarification decisions, intake, deck plan, frozen design, slide jobs, semantic prompts, generation packages, generated images, semantic scenes, measured scenes, reconstruction contracts, constructor scenes, and editable PowerPoint.

## Agent operation

The Agent calls `workflow_status` when it needs a current artifact inventory. It reasons over the user's request, the workflow skill, and those durable facts to choose its next action. A full autonomous run continues until the editable deck is complete. A user may ask to inspect, revise, regenerate, or stop at any point. Continuation begins from another workspace inspection and needs no pause or resume command.

The agent registers reasoning, visual interpretations, and generated images with the project before construction begins. Image generation can come from the agent app or from the image service selected in Slidecraft settings.

## Quality behavior

The semantic plan, deck rules, and construction workers produce the first editable result. Publication checks then verify text fit, connector logic, assets, package integrity, and cross-slide consistency. When a check finds a problem, it names the affected object and recommends the next repair.

Final assembly requires every planned slide in deck order. It rejects stale or incomplete scenes, canvas mismatch, missing deck chrome, unsupported constructor routes, invalid text fit, and damaged PowerPoint packages.

## User-facing artifacts

The Agent returns the editable PowerPoint when asked for the final deck. It can also return the plan, generated slide, decision record, preview, or reconstruction report on request. Internal masks, OCR fragments, contours, caches, and logs remain hidden during ordinary use.
