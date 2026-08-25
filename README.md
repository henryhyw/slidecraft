# Slidecraft

Slidecraft turns source material into polished, editable PowerPoint presentations inside the agent app you already use. The agent plans and guides the work while Slidecraft organizes project files, visual resources, image generation, slide understanding, and PowerPoint construction.

The current alpha is ready for local projects through Codex, Claude Code, GitHub Copilot, and other MCP-compatible agent apps. Release progress is tracked in [Release readiness](docs/RELEASE_READINESS.md).

## Install

Install Python 3.10 or newer and the current Node.js LTS release, then run the guided installer.

macOS and Linux

```bash
curl -fsSL https://raw.githubusercontent.com/henryhyw/slidecraft/v0.1.0-alpha.1/install.py | python3 -
```

Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/henryhyw/slidecraft/v0.1.0-alpha.1/install.py | py -3 -
```

The installer creates an isolated runtime, installs everyday presentation features, prepares the editable PowerPoint constructor, verifies the installation, and connects detected agent apps. It can be run again safely when Slidecraft is updated.

See [Installation](docs/INSTALLATION.md) for an inspect-before-running option, selected agent setup, GitHub Copilot workspace setup, installation locations, and troubleshooting.

Contributors can install from a cloned checkout with the same guided flow.

```bash
git clone https://github.com/henryhyw/slidecraft.git
cd slidecraft
python3 install.py --source .
```

The installer prints the exact dashboard command when it finishes. It follows this form.

```bash
/path/to/Slidecraft/app/bin/slidecraft console
```

The dashboard shows projects, style settings, shared resource collections, provider configuration, and runtime health. Project and library folders can be opened directly in the operating-system file browser.

## Agent integration

Slidecraft exposes the same capabilities in process, through its CLI, and over MCP.

```bash
slidecraft agent-capabilities
slidecraft-mcp
```

Your agent app manages the conversation. Slidecraft records project decisions, sources, progress, and deliverables so any new session can continue from the same project. The dashboard presents those files and settings in one place.

The bundled Agent skill is available at [integrations/skills/slidecraft/SKILL.md](integrations/skills/slidecraft/SKILL.md). The complete host contract is documented in [Agent integration](docs/AGENT_INTEGRATION.md).

The MCP server is self-describing and works as a local STDIO tool server in Codex, Claude Code,
GitHub Copilot Chat, and other MCP-capable hosts. Host-specific setup examples are available in
[Agent quickstart](docs/AGENT_QUICKSTART.md).

In a fresh session, name the project and describe what you want. The agent finds its saved progress, continues the work, or returns the requested presentation artifact. See [Agent quickstart](docs/AGENT_QUICKSTART.md).

Shell-based Agent hosts can use the same name-first entry point directly.

```bash
slidecraft project resolve "Market Growth"
slidecraft project show "Market Growth"
```

## Projects and resources

A project can live in a user-selected directory or in Slidecraft's managed data directory.

```text
project/
  slidecraft.project.json
  sources/           user material and direct-use visual assets
  deliverables/      editable presentations, previews, and reports
  .slidecraft/       durable Agent evidence and resource assignments
```

Visual inspiration, canonical icons, and reusable editable components live in shared local collections. Selections made in chat or in the dashboard stay attached to the project and are ready when the project is opened again.

Configuration follows packaged defaults, user configuration, an optional project overlay, environment variables, and explicit runtime arguments. Use these commands to inspect every resolved value and its source.

```bash
slidecraft config path
slidecraft config show
slidecraft config validate
slidecraft config explain
```

See [Configuration](docs/CONFIGURATION.md), [Guidance profiles](docs/GUIDANCE_PROFILES.md), and the [documentation map](docs/README.md).

## Pipeline

The Agent composes these reusable capabilities.

1. Normalize multimodal source material and hard constraints.
2. Plan the deck storyline and slide-specific semantic intent.
3. Retrieve visual inspiration, canonical icons, and reusable components.
4. Assemble and execute image-generation briefs for information-bearing slides.
5. Map meaningful rendered entities and relationships to authoritative source content.
6. Measure text, shapes, and layout with OpenCV, using SAM 2 for irregular filled regions when it adds useful boundary detail.
7. Build a reconstruction contract and compile editable PowerPoint scenes.
8. Normalize typography, alignment, icon slots, and connector topology within bounded constraints.
9. Render the editable deck and retain a reconstruction report.

The system contract is documented in [Framework pipeline](docs/FRAMEWORK_PIPELINE.md). Connector reasoning is documented in [Connector contract](docs/CONNECTOR_CONTRACT.md). Refinement constraints are documented in [Normalization contract](docs/NORMALIZATION_CONTRACT.md).

## Repository layout

```text
src/slidecraft/       installable Python package and dashboard
js/                   portable PowerPoint constructor
scripts/              installed worker and platform integration scripts
config/               versioned framework and design-policy examples
src/slidecraft/guidance_profiles/ reusable communication profiles
schemas/              interchange contracts
integrations/         Agent integration packages
tests/                automated tests
tools/historical_regression/  architecture-slide regression utilities excluded from the runtime
vendor/               upstream development sources for bundled resources
workspace/            ignored local projects, caches, and generated evidence
```

The top-level [AGENTS.md](AGENTS.md) gives repository-aware Agents a concise entry contract. Shared framework code never depends on a project under `workspace/` or on test fixtures.

Live presentation projects and generated output stay under `workspace/` during repository development and are excluded from Git. Packaged starter resources live under `src/slidecraft/starter_resources/`.

Every new project receives a packaged deck-design baseline under its hidden `.slidecraft/` directory. Covers, agendas, section dividers, statements, closings, and appendix dividers use shared deterministic layouts. Information-bearing slides use the image-generation route. Final assembly requires all planned slides in deck order and checks the frozen design, repeated typography roles, connector policy, canonical assets, canvas, and deck chrome before export.

## Development

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests tools
.venv/bin/python -m build
```

OpenCV handles ordinary text, connector, and line-art measurement. Install the `segmentation` extra to add SAM 2 boundary detection for irregular filled objects.

## License

Slidecraft is released under the [MIT License](LICENSE). Bundled third-party resources retain their own notices.
