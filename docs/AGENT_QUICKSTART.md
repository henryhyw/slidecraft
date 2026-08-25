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

The server introduces six presentation tools when the Agent app connects. Agent apps with reusable
skill support also receive the bundled Slidecraft skill for richer presentation guidance.

The guided installer registers detected Codex and Claude Code installations. It also installs the bundled Slidecraft workflow skill for those hosts. The commands below are available when manual registration is useful.

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
The client starts that process automatically when it needs Slidecraft. If the client has no MCP
support but can run Python, it can import the six functions in `slidecraft.agent_workflows`.

The bundled skill at `integrations/skills/slidecraft/SKILL.md` teaches compatible hosts the conversational workflow. The repository-level `AGENTS.md` gives the same entry guidance to Agents working from this source tree.

When a user asks to see the optional dashboard, the Agent can run `slidecraft console`. Slidecraft
starts the local webpage and opens it in the default browser.

## Start a fresh session

A user can say any natural equivalent of the following request.

> Continue the Market Growth project and show me what is ready.

The Agent calls `slidecraft_open_project` and returns the most relevant result. If the user clearly asks to begin a new project, it sets `create_if_missing`. A path is optional.

For a new presentation, the Agent first reads every source with its native document, data, and visual capabilities. It authors grounded source atoms with locators, authority, required-use decisions, exclusions, and provenance. It decides whether the evidence supports credible planning and asks only questions that could materially change the result. The Agent then calls `slidecraft_prepare_deck` with the agreed brief. The tool returns planning guidance. The Agent authors the deck plan and sends it through the same tool.

When a project includes images or diagrams, the agent describes the information they carry and links that interpretation to the original file. The resulting deck can trace visual claims back to their source.

## Image generation

`slidecraft_generate_slide` resolves image generation automatically.

- Agent apps with image generation receive the prompt and references, create the slide image directly, and send its path through the same tool.
- An OpenAI or OpenAI-compatible connection gives other agent apps the same generation route.
- The System page lets users choose which route Slidecraft uses for the project.

## Full-deck execution

The Agent interprets project sources, decides whether any high-value clarification is useful, and creates one deck plan. The plan freezes the storyline, source allocation, density, shared design system, page order, and route for each slide.

Structural slides such as covers and section dividers use packaged deterministic layouts selected by the Agent. For each content slide, `slidecraft_generate_slide` guides semantic design and resource selection before image generation. `slidecraft_measure_slide` accepts the Agent's visual analysis and records exact geometry. `slidecraft_reconstruct_slide` builds editable objects from the measured evidence and refinement plan.

`slidecraft_open_project` reports which planned slides are complete. The Agent calls `slidecraft_render_deck` when every planned slide is ready and the user's request calls for the deck. Assembly uses deck-plan order and enforces the frozen design identity, canvas, background, repeated typography roles, canonical asset roles, connector minimums, and deterministic header and footer contract.

## What the Agent returns

`slidecraft_open_project` exposes user-facing deliverables and a curated list of reviewable intermediate artifacts. The Agent chooses what to return from conversational intent.

- Final deck requests return the editable `.pptx` and any requested report.
- Progress reviews can return the deck plan, generated slides, decisions, or current preview.
- Technical diagnosis can include internal evidence when explicitly requested.

Users can pause, continue, review, or revise the presentation in ordinary conversation. Each completed operation is saved, so another session can pick up from the same point.
