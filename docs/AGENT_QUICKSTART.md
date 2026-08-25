# Agent quickstart

This guide connects Slidecraft to an Agent host. Users then work through ordinary conversation and may ignore the dashboard entirely.

## Install

Install Python 3.10 or newer and Node.js. From a cloned repository, run the following commands.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[cv,documents,agent]'
.venv/bin/slidecraft init
.venv/bin/slidecraft check-install
```

`slidecraft init` creates the local data directories, installs the managed PowerPoint constructor dependencies, and seeds the reusable collections. It is non-interactive.

## Connect an Agent host

Any host that supports stdio MCP can launch this command.

```text
slidecraft-mcp
```

The server publishes its operating instructions during MCP initialization. The optional bundled
skill adds richer guidance for hosts that support skills, while the MCP connection remains
self-describing on its own.

For Codex CLI, register the installed command once.

```bash
codex mcp add slidecraft -- /absolute/path/to/slidecraft-mcp
```

Codex desktop, CLI, and IDE clients share the same MCP configuration. The server can also be
added from the MCP settings interface as a local STDIO server.

For Claude Code, register the same executable.

```bash
claude mcp add slidecraft -- /absolute/path/to/slidecraft-mcp
```

For GitHub Copilot Chat in VS Code, add `.vscode/mcp.json` to the presentation workspace.

```json
{
  "servers": {
    "slidecraft": {
      "command": "/absolute/path/to/slidecraft-mcp",
      "args": []
    }
  }
}
```

For another MCP client, create a local STDIO server entry with `slidecraft-mcp` as the command.
If the client has no MCP support but can run local commands, use `slidecraft agent-call` with JSON
arguments. Python hosts can import `slidecraft.call_capability` directly.

The bundled skill at `integrations/skills/slidecraft/SKILL.md` teaches compatible hosts the conversational workflow. The repository-level `AGENTS.md` gives the same entry guidance to Agents working from this source tree.

Hosts with shell access and no MCP client can use `slidecraft project resolve`, `slidecraft project show`, and the generic `slidecraft agent-call` transport.

```bash
slidecraft agent-call --capability workflow_status --arguments '{"workspace":"/path/to/project"}'
```

## Start a fresh session

A user can say any natural equivalent of the following request.

> Continue the Market Growth project and show me what is ready.

The Agent should resolve the project name, inspect its durable status, and return the most relevant result. If the user clearly asks to begin a new project, the Agent may create it through the same resolver. A path is optional.

For a new presentation, the Agent calls `set_deck_brief` with the audience, objective, source materials, explicit constraints, desired result, optional density override, and optional slide-count range agreed in conversation. This typed entry point works over MCP and does not require the host to author hidden project files.

Uploaded images and diagrams need a source-grounded interpretation from the host's visual understanding. The Agent stores that interpretation as material content and preserves the original file path. Slidecraft refuses to plan from dimensions and filenames alone.

## Image generation

The Agent calls `resolve_image_generation_route` before generation.

- If the host has image generation and the configured policy permits it, the Agent uses its native image tool and registers the generated image.
- If the host has no image tool, Slidecraft uses the configured OpenAI or OpenAI-compatible image endpoint.
- A user can force the configured provider through the normal Slidecraft settings.

## Full-deck execution

The Agent normalizes project sources, offers optional high-value clarifications, and creates one deck plan. The plan freezes the storyline, source allocation, density, shared design system, page order, and route for each slide.

Structural slides such as covers and section dividers use packaged deterministic layouts. Content slides become slide jobs. The Agent calls `prepare_slide`, creates the semantic-design result with its host reasoning model, and calls `prepare_generation`. Generated images then pass through semantic mapping, measurement, reconstruction-contract compilation, and constructor-scene compilation.

`workflow_status` only proposes final PowerPoint assembly after every planned slide has a fresh constructor scene. Assembly uses deck-plan order and enforces the frozen design identity, canvas, background, repeated typography roles, canonical asset roles, connector minimums, and deterministic header and footer contract.

## What the Agent returns

`project_detail` exposes user-facing deliverables and a curated list of reviewable intermediate artifacts. The Agent chooses what to return from conversational intent.

- Final deck requests return the editable `.pptx` and any requested report.
- Progress reviews can return the deck plan, generated slides, decisions, or current preview.
- Technical diagnosis can include internal evidence when explicitly requested.

The framework contains no chat-specific pause, resume, or review command. Durable artifacts make every operation resumable, while the host Agent interprets normal conversation.
