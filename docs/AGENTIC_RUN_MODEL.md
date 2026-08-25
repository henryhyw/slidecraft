# Agentic run model

## Conversation and project memory

The Agent manages the conversation and decides what to do next. Slidecraft stores ordinary project files and an optional artifact ledger. The CLI and web app read and edit the same local state.

## Shared project context

`slidecraft project context` returns the effective global and project configuration, resolved design, materials, assets, selected resources, pending web app events, current artifacts, and deliverables. The Agent reads this context before planning and whenever the user may have changed controls in the web app.

The project registry helps the web app discover local folders. Construction commands operate directly on the shared project files selected by the Agent.

## Durable artifact graph

An Agent can record useful milestones such as a storyboard, generated image, visual analysis, constructor scene, or editable presentation. Each record includes a logical key, revision, file hash, producer, and lifecycle. The web app uses these records to present current progress.

Direct project reconstruction automatically records its design snapshot and construction outputs.

## Agent operation

The Agent follows the bundled skill, discusses planning when the work is collaborative, creates and reviews slides, then invokes local construction commands. A user can inspect, revise, regenerate, or stop at any point. Continuation begins by reading the current project context.

## Quality behavior

The Agent owns editorial quality, evidence sufficiency, message relevance, storyline coherence, semantic mapping, and visual review. Local code checks the mechanical conditions needed for reliable construction. These include readable inputs, valid geometry, available assets, supported object routes, safe text fit, bounded movement, and PowerPoint package integrity.

## User-facing artifacts

The Agent returns the editable PowerPoint for final deck requests. It can also return the storyboard, generated slide, decision record, preview, or reconstruction evidence when requested. Masks, OCR fragments, contours, caches, and logs remain internal during ordinary use.
