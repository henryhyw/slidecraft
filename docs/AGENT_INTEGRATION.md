# Agent integration

## Control model

Slidecraft gives an agent app a complete set of presentation tools. The agent interprets the conversation and chooses each action. Slidecraft manages project files, versioned results, validation, and editable PowerPoint construction.

The project folder is the shared memory between sessions. It records inputs, decisions, completed work, and deliverables. `workflow_status` reports that record as facts. The Agent interprets those facts and chooses its own next action. The dashboard and MCP connection show the same project state.

In a fresh session, call `resolve_project` with the project name, stable ID, or folder. The result provides the workspace location. Set `create_if_missing` when the user starts a new presentation.

Every completed action is saved as a consistent project revision. To continue later, the agent calls `inspect_workspace`, checks the current results, and proceeds from the latest valid point.

## Installation surfaces

Install from the public GitHub repository:

```bash
git clone https://github.com/henryhyw/slidecraft.git
cd slidecraft
python3 -m venv .venv
```

Add document extraction, OpenCV measurement, and MCP integration:

```bash
.venv/bin/python -m pip install '.[cv,documents,agent]'
.venv/bin/slidecraft init
.venv/bin/slidecraft check-install
```

Connect Codex, Claude Code, Copilot, or another compatible agent app to this MCP command:

```bash
/absolute/path/to/slidecraft/.venv/bin/slidecraft-mcp
```

The server introduces its compact tool surface when the agent app connects. The guided installer also places the bundled skill into supported Agent hosts so the host owns the presentation reasoning workflow.

The repository also includes an agent skill under `integrations/skills/slidecraft`. It teaches an agent how to inspect project progress, ask useful planning questions, and compose the capabilities below. MCP provides the primary typed connection. Python and JSON CLI integrations expose the same operations.

An agent app launches it as a local stdio MCP server. The connection exposes focused entry tools and one general tool for the full operation catalog.

- `slidecraft_capabilities` discovers the supported operations and their arguments.
- `slidecraft_create_workspace` creates or reopens durable project state.
- `slidecraft_resolve_project` finds or intentionally creates a project from a conversational identifier.
- `slidecraft_project_detail` returns user-facing progress, outputs, sources, and reviewable artifacts.
- `slidecraft_set_deck_brief` records the agreed presentation brief from the conversation.
- `slidecraft_inspect_workspace` reports active artifacts, candidates, freshness, and validation.
- `slidecraft_workflow_status` reports durable progress, artifact availability, validation attention, and deliverables.
- `slidecraft_call` invokes a discovered capability.

Python applications can call the same capabilities directly.

```python
from slidecraft import call_capability

call_capability("create_workspace", {
    "workspace": "/absolute/path/to/my-deck",
    "deck_id": "client_strategy_2026",
})

state = call_capability("inspect_workspace", {
    "workspace": "/absolute/path/to/my-deck",
})
```

Hosts that can execute processes can use the JSON CLI adapter.

```bash
slidecraft agent-capabilities
slidecraft agent-call --request /absolute/path/to/request.json
slidecraft agent-call --capability workflow_status --arguments '{"workspace":"/absolute/path/to/my-deck"}'
```

Example request:

```json
{
  "capability": "prepare_generation",
  "arguments": {
    "workspace": "/absolute/path/to/my-deck",
    "design": "/absolute/path/to/deck-design.json",
    "slide": "/absolute/path/to/slide-request.json",
    "output_dir": "/absolute/path/to/my-deck/slides/slide_01/generation",
    "slide_id": "slide_01",
    "resource_selection": {
      "schema_version": "1.0.0",
      "authored_by": "agent_reasoning",
      "visual_references": [],
      "icons": [],
      "components": []
    }
  }
}
```

## Durable continuation

Each artifact records a stable ID, logical key, revision, content hash, file path, producer, slide scope, dependencies, provenance, validation, and lifecycle.

Candidate revisions do not replace accepted work. When the Agent accepts a candidate, Slidecraft updates the active revision. Descendants that cite an older dependency immediately become stale. Their files and audit history remain available.

The constructor checks that each scene matches the current image, semantic map, and design settings before building the PPTX. Outdated descendants remain available in history and stay out of the published deck.

## Agent behavior contract

An integrating Agent should follow these rules.

1. Call `slidecraft_capabilities` once when tool availability is unknown.
2. Call `workflow_status` when project facts are needed, then choose the next action through host reasoning.
3. Translate user intent into the smallest relevant capability calls.
4. Stop calling capabilities when the user asks to inspect or interrupt work.
5. Register external model outputs before using them downstream.
6. Activate a candidate only after the applicable acceptance policy passes.
7. Recompute stale descendants before export.
8. Repair validation failures with their recorded evidence. Report only failures that exhaust the configured recovery policy.

The Agent can revise one slide, regenerate one image, change a plan, or reconstruct again without restarting unrelated work.

## Clarification and native host interaction

The Agent decides whether any clarification is useful and authors zero to three final questions. `prepare_clarifications` validates and stores that decision. The host can use its native structured-input component or ordinary conversation. Users may answer any subset, skip all questions, or delegate individual choices. `record_clarification_answers` preserves the resulting decisions and assumptions as an authoritative planning input.

The skill avoids questions that merely shift visual taste. It asks only when the answer can materially change communication strategy. The maximum count is configurable and defaults to three.

## Project visibility

The `create_project` capability can use any folder the user chooses. Source files and deliverables stay visible, while detailed reconstruction evidence lives under `.slidecraft/`. `project_detail` presents the materials, progress, and outputs people usually need and can include technical history on request.

`project_detail` also returns reviewable intermediate artifacts with clear labels. The agent selects the files that match the user's request, whether they ask for a plan, preview, decision record, or final deck.

## Service integration

The same capability API can support future queued or hosted services. Local agent use remains the primary workflow for this release.
