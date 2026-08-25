# Slidecraft

Slidecraft helps an AI Agent turn your documents, data, images, and instructions into a polished PowerPoint deck that you can edit normally.

You work through conversation. Tell the Agent what the presentation needs to achieve, share the source material, and review decisions or slides whenever you want. The Agent develops the storyline and visual direction. Slidecraft keeps the work organized, prepares slide images, rebuilds them as native PowerPoint objects, and saves the finished deck with its sources and decisions.

The current alpha works locally with Codex, Claude Code, GitHub Copilot, and other Agent apps that support MCP. Release progress is tracked in [Release readiness](docs/RELEASE_READINESS.md).

## What using Slidecraft looks like

1. Open your Agent in the folder where you want the project to live, then name the presentation and share your material. You can choose another folder whenever you want.
2. Discuss the audience, objective, constraints, and any decisions that matter.
3. Review the proposed storyline when you want control over the deck structure. You can also delegate the choices and let the Agent continue.
4. The Agent creates each slide using the project style, approved visual resources, and exact source content.
5. Slidecraft converts the visual result into editable text, shapes, tables, charts, icons, and connectors.
6. Receive a normal `.pptx` file. You can return later, name the project, and continue from its saved work.

Image generation handles information-rich slide composition. Consistent structural pages such as covers and section dividers use reusable PowerPoint layouts. Header, footer, typography, color, and spacing rules stay coherent across the complete deck.

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

The dashboard is optional. It gives you one place to browse projects, adjust presentation style, manage reusable resources, connect an image service, and check the local installation. Project and collection folders open directly in the operating-system file browser.

## Use it from an Agent app

The installer connects supported Agent apps automatically. Once connected, ask the Agent to create or continue a Slidecraft project in ordinary language. New projects use the Agent's current workspace by default. You do not need to run pipeline commands or manage internal files.

Slidecraft connects through six presentation tools. They open a project, prepare the deck, generate a slide, measure a slide, reconstruct a slide, and render the complete deck. Each tool accepts the Agent's decisions directly and hides the bookkeeping underneath.

```bash
slidecraft-mcp
```

The guided installer registers this local server with detected Agent apps. The Agent app starts it when needed. You do not run it for each project. If you ask to see the dashboard, the Agent can launch `slidecraft console` and open the local webpage for you.

Your Agent app manages the conversation and makes every decision that requires judgment. This includes interpreting source files and deciding whether the material supports a credible deck. Slidecraft records the Agent's evidence and decisions, manages project files, and performs measurement and PowerPoint construction. The dashboard presents the same durable project information.

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

## How the complete workflow works

The Agent guides the work from the first conversation to the finished deck. Slidecraft supplies dependable operations for each part of that work.

1. Understand the brief. The Agent reads every supplied source, identifies grounded facts and exact content, decides relevance and authority, preserves source provenance, and judges whether the evidence supports credible planning. It asks only questions that could materially change the result.
2. Plan the story. The Agent chooses the governing message, sections, slide sequence, information density, and the purpose of every page.
3. Choose reusable resources. The Agent searches local collections of visual inspiration, icons, and editable components, then selects resources that fit each slide.
4. Design content slides. The Agent prepares an image-generation brief with exact content and project style. It uses its own image tool when available or the image service connected in Slidecraft.
5. Understand the result. The Agent identifies meaningful text, groups, icons, diagrams, images, and relationships. OpenCV measures their exact placement and appearance. SAM 2 is available for irregular filled boundaries.
6. Rebuild the slide. Slidecraft creates native PowerPoint text, tables, charts, shapes, connectors, canonical SVG icons, reusable components, and carefully fitted custom geometry.
7. Refine and assemble. The Agent identifies alignments and peer typography that should be normalized. Slidecraft applies bounded corrections, checks every planned page, and exports the editable deck in the approved order.

The generated image provides visual design. Exact source text and data remain authoritative. Icons return to clean library assets. Connectors are rebuilt from their relationship meaning. OCR fragments, masks, and contours remain measurement evidence and never become stray PowerPoint objects.

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
