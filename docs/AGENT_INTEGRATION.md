# Agent integration

## Control model

Slidecraft is an Agent-native capability package. The host Agent owns conversation, intent interpretation, orchestration, session progression, and the decision to stop or continue. Slidecraft supplies deterministic tools, typed artifacts, dependency tracking, validation, and reconstruction.

The local project ledger is passive durable memory. It records facts about inputs and completed outputs. It does not choose the next operation. `workflow_status` derives advisory next actions from that ledger for the current Agent call. No workflow session lives in the dashboard process, MCP process, or a background server.

In a fresh session, call `resolve_project` with the human project name, stable ID, or folder. The result provides the canonical workspace location. Set `create_if_missing` only when the user intends new work. Users do not need to remember local paths.

There is no core `pause` or `resume` operation. Every completed capability commits its output atomically. When a conversation resumes, the Agent calls `inspect_workspace`, reads active revisions and freshness, and selects the next useful capability.

## Installation surfaces

Core SDK and CLI installation:

```bash
pip install slidecraft-ai
```

Full local deck generation installs document extraction, OpenCV measurement, and the Agent transport.

```bash
pip install 'slidecraft-ai[cv,documents,agent]'
slidecraft init
slidecraft check-install
```

MCP installation for Codex, Claude, Copilot, and other compatible Agent hosts:

```bash
pip install 'slidecraft-ai[agent]'
```

The MCP server command is:

```bash
slidecraft-mcp
```

The server provides a concise workflow contract in its MCP initialization metadata. Generic MCP
hosts therefore receive the entry logic without requiring a host-specific skill installation.
The bundled skill remains available for hosts that support richer reusable instructions.

The repository also includes an installable Agent skill under `integrations/skills/slidecraft`. It teaches a host how to inspect durable state, ask optional high-value clarification questions, preserve hidden evidence, and compose the capabilities below. MCP is the preferred typed transport. The Python API and JSON CLI remain equivalent fallbacks.

An Agent host should launch it as a local stdio MCP server. The MCP adapter exposes focused entry tools and one generic capability tool.

- `slidecraft_capabilities` discovers the supported operations and their arguments.
- `slidecraft_create_workspace` creates or reopens durable project state.
- `slidecraft_resolve_project` finds or intentionally creates a project from a conversational identifier.
- `slidecraft_project_detail` returns user-facing progress, outputs, sources, and reviewable artifacts.
- `slidecraft_set_deck_brief` records the authoritative conversational brief without direct hidden-file access.
- `slidecraft_inspect_workspace` reports active artifacts, candidates, freshness, and validation.
- `slidecraft_workflow_status` derives exact resumable next actions from current project evidence.
- `slidecraft_call` invokes a discovered capability.

The MCP layer is an optional adapter. The underlying Python capability API remains identical.

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
    "slide_id": "slide_01"
  }
}
```

## Durable continuation

Each artifact records a stable ID, logical key, revision, content hash, file path, producer, slide scope, dependencies, provenance, validation, and lifecycle.

Candidate revisions do not replace accepted work. When the Agent accepts a candidate, Slidecraft updates the active revision. Descendants that cite an older dependency immediately become stale. Their files and audit history remain available.

The constructor refuses to consume stale scene artifacts. This prevents an Agent from accidentally publishing a PPTX built from an older generated image or outdated semantic map.

## Agent behavior contract

An integrating Agent should follow these rules.

1. Call `slidecraft_capabilities` once when tool availability is unknown.
2. Call `workflow_status` before continuing existing work and after each material capability.
3. Translate user intent into the smallest relevant capability calls.
4. Stop calling capabilities when the user asks to inspect or interrupt work.
5. Register external model outputs before using them downstream.
6. Activate a candidate only after the applicable acceptance policy passes.
7. Recompute stale descendants before export.
8. Repair validation failures with their recorded evidence. Report only failures that exhaust the configured recovery policy.

The Agent can revise one slide, regenerate one image, change a plan, or reconstruct again without restarting unrelated work.

## Clarification and native host interaction

The `prepare_clarifications` capability returns a small structured package before deck planning. The host should use its native structured-input component when one exists. Otherwise it can render the same questions in normal chat. Users may answer any subset, skip all questions, or delegate individual choices. `record_clarification_answers` preserves the resulting decisions and assumptions as an authoritative planning input.

The skill avoids questions that merely shift visual taste. It asks only when the answer can materially change communication strategy. The maximum count is configurable and defaults to three.

## Project visibility

The `create_project` capability accepts a user-selected folder. It creates visible `sources/` and `deliverables/` directories plus a hidden `.slidecraft/` workspace. `project_detail` omits internal revision history unless the caller explicitly requests it. This lets the Agent retain full traceability without making users browse OCR fragments, masks, edge evidence, or intermediate prompts.

`project_detail` also returns reviewable intermediate artifacts with human-facing labels. The host Agent selects files from conversational intent. The framework imposes no fixed review screen or delivery sequence.

## Service deployment later

A future background service may add scheduling controls such as pause, resume, cancellation, queues, leases, and retries. Those controls remain outside the core artifact and reconstruction contracts. They can use the same capability API without changing Agent-host behavior.
