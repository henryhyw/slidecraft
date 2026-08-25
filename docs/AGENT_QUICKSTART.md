# Agent quickstart

This guide connects Slidecraft to an Agent host. Users then work through ordinary conversation and may ignore the dashboard entirely.

## Install

Install Python 3.10 or newer and the current Node.js LTS release. The guided installer creates an isolated runtime, prepares the constructor, verifies the installation, and connects detected agent apps.

```bash
curl -fsSL https://raw.githubusercontent.com/henryhyw/slidecraft/v0.1.0-alpha.1/install.py | python3 -
```

Windows PowerShell users can run this equivalent command.

```powershell
irm https://raw.githubusercontent.com/henryhyw/slidecraft/v0.1.0-alpha.1/install.py | py -3 -
```

See [Installation](INSTALLATION.md) for selected host setup, a reviewable download flow, and the manual contributor installation.

## Connect an Agent host

Any host that supports stdio MCP can launch this command.

```text
slidecraft-mcp
```

The server introduces its tools and workflow when the agent app connects. Agent apps with reusable
skill support can also install the bundled Slidecraft skill for richer presentation guidance.

The guided installer registers detected Codex and Claude Code installations. The commands below are available when manual registration is useful.

For Codex CLI, register the installed MCP command once.

```bash
codex mcp add slidecraft -- /absolute/path/to/slidecraft-mcp
```

Codex desktop, CLI, and IDE clients share the same MCP configuration. The server can also be
added from the MCP settings interface as a local STDIO server.

For Claude Code, register the same executable.

```bash
claude mcp add slidecraft --scope user -- /absolute/path/to/slidecraft-mcp
```

For GitHub Copilot, add the MCP command to `~/.copilot/mcp-config.json` for the current user or `.mcp.json` in a presentation workspace.

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

When a project includes images or diagrams, the agent describes the information they carry and links that interpretation to the original file. The resulting deck can trace visual claims back to their source.

## Image generation

The Agent calls `resolve_image_generation_route` before generation.

- Agent apps with image generation create the slide image directly and register it with the project.
- An OpenAI or OpenAI-compatible connection gives other agent apps the same generation route.
- The System page lets users choose which route Slidecraft uses for the project.

## Full-deck execution

The Agent normalizes project sources, offers optional high-value clarifications, and creates one deck plan. The plan freezes the storyline, source allocation, density, shared design system, page order, and route for each slide.

Structural slides such as covers and section dividers use packaged deterministic layouts. Content slides become slide jobs. The Agent calls `prepare_slide`, creates the semantic-design result with its host reasoning model, and calls `prepare_generation`. Generated images then pass through semantic mapping, measurement, reconstruction-contract compilation, and constructor-scene compilation.

`workflow_status` only proposes final PowerPoint assembly after every planned slide has a fresh constructor scene. Assembly uses deck-plan order and enforces the frozen design identity, canvas, background, repeated typography roles, canonical asset roles, connector minimums, and deterministic header and footer contract.

## What the Agent returns

`project_detail` exposes user-facing deliverables and a curated list of reviewable intermediate artifacts. The Agent chooses what to return from conversational intent.

- Final deck requests return the editable `.pptx` and any requested report.
- Progress reviews can return the deck plan, generated slides, decisions, or current preview.
- Technical diagnosis can include internal evidence when explicitly requested.

Users can pause, continue, review, or revise the presentation in ordinary conversation. Each completed operation is saved, so another session can pick up from the same point.
