# Slidecraft

Slidecraft is a presentation creation framework that turns source material into a planned, visually designed, and fully editable PowerPoint deck.

It gives the creation process a clear structure from research and storyline development through slide design, editable reconstruction, and final assembly. A shared web workspace lets you manage the presentation, review progress, control the design system, and continue revisions across sessions.

## What the framework adds

- A research and briefing method that starts with the audience and intended decision
- A storyboard with a recommended slide count and one conclusion-led message per slide
- A consistent presentation design system covering typography, color, density, icons, connectors, and deck chrome
- Shared materials, visual assets, reusable components, and visual references
- Slide-level visual design with exact content and semantic relationships
- Conversion of designed slides into editable PowerPoint content
- A persistent project record for review, revision, and continuation
- A central web app for presentation settings, resources, progress, and deliverables

## How Slidecraft works

### 1. Build the presentation brief

Slidecraft guides the interpretation of your materials and any supporting research. The brief identifies the audience, the change in understanding the deck should create, the governing answer, the evidence available, and the assumptions that matter.

For collaborative work, you see the research synthesis and proposed brief before slide production begins.

### 2. Plan the argument

The framework compares possible narrative structures and develops a storyboard. The proposal includes the recommended number of slides, storyline phases, and a project-specific message, evidence allocation, visual job, and transition for every slide.

This makes the deck reviewable as an argument before time is spent designing pages.

### 3. Resolve the visual system

Slidecraft applies the selected communication style, information density, typography, colors, icon treatment, connector conventions, and page structure across the deck. Project assets and reusable visual resources remain attached to the presentation and available for later revisions.

### 4. Design each slide

Every slide begins with a communication contract that defines what the audience should understand and what the visual must make clear. Information-rich pages can be composed visually, while structural pages and straightforward arrangements use native layouts.

Each candidate is reviewed for message fidelity, evidence accuracy, hierarchy, grouping, relationships, legibility, and consistency with the deck.

### 5. Reconstruct editable PowerPoint content

Slidecraft identifies the meaningful text, shapes, tables, charts, images, icons, groups, and connectors in an accepted design. It measures their geometry and appearance, maps them to appropriate PowerPoint objects, fits typography, restores canonical assets, and rebuilds semantic connector systems.

OpenCV handles ordinary visual measurement. SAM can support irregular filled boundaries. The resulting slide remains editable in PowerPoint.

### 6. Assemble and review the deck

The framework assembles slides in storyboard order and checks package integrity, text fit, asset resolution, connector behavior, and repeated design roles. The final review covers the argument, evidence, visual rhythm, editability, and cross-slide coherence.

## Shared workspace and web app

Each presentation has one project workspace containing its materials, assets, settings, working artifacts, and deliverables. The conversation and web app use the same project state.

The web app provides a central view for:

- Presentation progress and latest outputs
- Source material and project visuals
- Selected icons, components, and visual inspiration
- Communication style, density, typography, and color
- Image-generation configuration
- Editable slides and assembled decks

Open it with:

```bash
slidecraft console
```

## Working with Slidecraft

You can stay involved throughout the process or delegate the complete presentation.

For collaborative work, ask to review the research synthesis and proposed brief first.

> Create an executive presentation from these materials. Show me the research findings, recommended slide count, storyline, and message for every slide before designing the deck.

At any point, you can request the brief, storyboard, visual design, editable slide, or complete presentation.

## Install

Install Python 3.10 or newer and the current Node.js LTS release. Then run the guided installer.

macOS and Linux

```bash
curl -fsSL https://raw.githubusercontent.com/henryhyw/slidecraft/v0.1.0-alpha.1/install.py | python3 -
```

Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/henryhyw/slidecraft/v0.1.0-alpha.1/install.py | py -3 -
```

See [Installation](docs/INSTALLATION.md) for platform locations and troubleshooting.

## For contributors

```bash
git clone https://github.com/henryhyw/slidecraft.git
cd slidecraft
python3 install.py --source .
```

Implementation details are documented in [Agent integration](docs/AGENT_INTEGRATION.md), [Presentation workflow](docs/FRAMEWORK_PIPELINE.md), and [Full-deck architecture](docs/FULL_DECK_ARCHITECTURE.md).

## License

Slidecraft is released under the [MIT License](LICENSE). Bundled third-party resources retain their own notices.
