# Slidecraft

Slidecraft is a local-first, Agent-native framework that turns source material into editable PowerPoint presentations. A host Agent plans the deck and controls the workflow. Slidecraft supplies durable project artifacts, reusable visual resources, image-generation orchestration, slide understanding, and deterministic PowerPoint construction.

The package is an alpha. Its reusable runtime, dashboard, Agent capability surface, and tested reconstruction path are installable today. Release criteria are tracked in [Release readiness](docs/RELEASE_READINESS.md).

## Install

Python 3.10 or newer is required. Node.js is used by the current portable PowerPoint constructor.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[cv,documents,agent]'
.venv/bin/slidecraft init
.venv/bin/slidecraft check-install
```

`slidecraft init` installs the managed PowerPoint constructor packages under the platform-specific Slidecraft data directory. Users need Node.js on the machine and do not need to manage repository-level JavaScript dependencies.

Open the local dashboard with the following command.

```bash
.venv/bin/slidecraft console
```

The dashboard shows projects, style settings, shared resource collections, provider configuration, and runtime health. Project and library folders can be opened directly in the operating-system file browser.

## Agent integration

Slidecraft exposes the same capabilities in process, through its CLI, and over MCP.

```bash
.venv/bin/slidecraft agent-capabilities
.venv/bin/slidecraft-mcp
```

The host Agent owns conversational and session state. Slidecraft persists only durable project facts and artifacts. The dashboard is a second interface over those same files and resources. It does not run a competing workflow state machine.

The bundled Agent skill is available at [integrations/skills/slidecraft/SKILL.md](integrations/skills/slidecraft/SKILL.md). The complete host contract is documented in [Agent integration](docs/AGENT_INTEGRATION.md).

The MCP server is self-describing and works as a local STDIO tool server in Codex, Claude Code,
GitHub Copilot Chat, and other MCP-capable hosts. Host-specific setup examples are available in
[Agent quickstart](docs/AGENT_QUICKSTART.md).

For a fresh Agent session, the user only needs to name the project. The Agent resolves the name, inspects durable progress, and either continues or returns the requested artifact. New work begins through the typed `set_deck_brief` capability, so MCP-only hosts do not need to write hidden files. See [Agent quickstart](docs/AGENT_QUICKSTART.md).

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

Visual inspiration, canonical icons, and reusable editable components live in shared local collections. Agent retrieval and dashboard choices are written to one project resource ledger. A restored project can therefore recover its selected resources without relying on an active server session or historical UI state.

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
6. Measure geometry with OpenCV and optional SAM 2 segmentation.
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

SAM 2 is optional. Install it with the `segmentation` extra when irregular filled-object boundaries materially benefit from segmentation. Ordinary text, connector, and line-art measurements use deterministic local logic.

## License

Slidecraft is released under the [MIT License](LICENSE). Bundled third-party resources retain their own notices.
