# Agent integration

Slidecraft integrates through a local skill, CLI, and shared project workspace.

## Responsibility boundary

The Agent owns interpretation, research, audience reasoning, storyline, slide messages, semantic design, image generation, visual analysis, and editorial review.

The local package owns deterministic operations. These include configuration resolution, resource catalogs, OpenCV measurement, optional SAM segmentation, bounded geometry refinement, text fitting, connector routing, native PowerPoint compilation, and package verification.

## Shared control model

The Agent, CLI, and web app use the same local source of truth.

```text
project/
  materials/
  assets/
  deliverables/
  .slidecraft/
    project.json
    config.toml
    deck_design.json
    artifact_manifest.json
    working/
```

User defaults live in the normal Slidecraft configuration directory. A project can add `.slidecraft/config.toml` as an overlay. The effective order is packaged defaults, user settings, project settings, environment overrides, and explicit runtime overrides.

The web app writes these same files. The Agent should run `slidecraft project context` before planning and after possible web app changes. That command returns effective settings, design, resources, pending events, artifacts, and deliverables.

## Agent-visible commands

Create or inspect shared work.

```bash
slidecraft project create "Presentation name" --location /absolute/path/project
slidecraft project context /absolute/path/project
```

Record an Agent-authored artifact for web display and project continuation.

```bash
slidecraft project record /absolute/path/project \
  --path /absolute/path/project/.slidecraft/working/storyboard.json \
  --logical-key deck/plan \
  --kind deck_plan
```

Reconstruct an accepted image with the configured design and construction logic.

```bash
slidecraft reconstruct-slide \
  --project /absolute/path/project \
  --image /absolute/path/generated.png \
  --visual-analysis /absolute/path/visual-analysis.json \
  --slide-id slide-01 \
  --output-dir /absolute/path/project/.slidecraft/working/slide-01 \
  --output /absolute/path/project/deliverables/slides/slide-01.pptx
```

Assemble constructor scenes in Agent-selected order.

```bash
slidecraft render-scenes \
  --scene /absolute/path/project/.slidecraft/working/slide-01/constructor_scene.json \
  --scene /absolute/path/project/.slidecraft/working/slide-02/constructor_scene.json \
  --output /absolute/path/project/deliverables/presentation.pptx
```

## Quality and construction

The skill guides the Agent through research synthesis, brief discussion, narrative comparison, storyboard quality, semantic completeness, and visual review. These are reasoning tasks.

The construction package confirms JSON readability, valid geometry, referenced asset availability, supported reconstruction routes, bounded transformations, safe text fit, and a healthy PowerPoint ZIP package.
