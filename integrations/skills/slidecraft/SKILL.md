---
name: slidecraft
description: Turn source materials and instructions into polished, editable PowerPoint presentations through collaborative planning, visual design, revision, and delivery.
---

# Slidecraft

Slidecraft is a presentation creation framework for planning, designing, reconstructing, revising, and delivering editable decks. Follow its planning method, shared project model, design system, resource workflow, semantic reconstruction logic, and review standards. Packaged commands provide OpenCV measurement, optional SAM segmentation, editable reconstruction, text fitting, connector routing, and PowerPoint construction.

Work through ordinary project files with the `slidecraft` CLI and packaged scripts.

If [references/runtime.md](references/runtime.md) exists, use the installed command path recorded there for every `slidecraft` example. Otherwise resolve the command with `command -v slidecraft`. In a source checkout, use the repository virtual environment or `python -m slidecraft.cli`.

## Share state with the local console

Create a local Slidecraft project folder so the Agent and web app share the same files and controls.

```bash
slidecraft project create "Presentation name" --location /absolute/path/project
slidecraft project context /absolute/path/project
```

Read `project context` before planning and again when the user may have changed settings or resources in the web app. It returns the effective global and project configuration, resolved deck design, materials, visual assets, selected library resources, pending console events, deliverables, and current artifact records.

Store user-visible inputs under `materials/` and `assets/`. Store working files under `.slidecraft/working/`. Store editable outputs under `deliverables/`. Record Agent-authored planning and review files so the web app can display them.

```bash
slidecraft project record /absolute/path/project \
  --path /absolute/path/project/.slidecraft/working/storyboard.json \
  --logical-key deck/plan \
  --kind deck_plan
```

The web app and CLI edit the same user configuration, optional `.slidecraft/config.toml` project overlay, `.slidecraft/deck_design.json`, resource ledgers, artifact manifest, and deliverables. Treat these shared files as authoritative throughout planning and construction. A project-level reconstruction automatically records its construction outputs.

## Develop the presentation

Read the supplied sources with the host Agent's document, data, and visual capabilities. Decide what matters, what is authoritative, what the audience needs, and what the deck should accomplish. Use research as visible evidence when it advances the argument and as background context when it sharpens the reasoning.

For a new or substantially replanned deck, read [references/planning.md](references/planning.md). It defines the positive editorial workflow and the Agent-owned planning artifacts.

Default to collaborative planning unless the user explicitly delegates uninterrupted execution. Share the source and research synthesis, material assumptions, and proposed storyboard before generation when the work is collaborative.

## Create slide images

Author each slide's communication contract and semantic visual design. Use image generation for every information-bearing slide. This includes agendas, executive summaries, comparisons, tables, charts, process diagrams, technical architecture, statements, closing pages, appendix content, and visually straightforward arrangements.

Use deterministic native layouts only for covers and section transitions, including appendix dividers. Do not directly author any other slide in PowerPoint. Structured technical content is a reason to preserve exact semantics and reconstruct clean native objects after generation. It is never a reason to skip image generation.

Review every generated candidate visually. Select the candidate with the strongest message fidelity, hierarchy, grouping, relationships, legibility, and deck-style coherence.

## Reconstruct an accepted image

Read [references/reconstruction.md](references/reconstruction.md) before reconstructing the first slide in a deck. It defines the Agent-authored visual-analysis and handoff structures.

The ordinary direct command is:

```bash
slidecraft reconstruct-slide \
  --project /absolute/path/project \
  --image /absolute/path/generated.png \
  --visual-analysis /absolute/path/visual-analysis.json \
  --slide-id slide-01 \
  --output-dir /absolute/path/working/slide-01 \
  --output /absolute/path/project/deliverables/slides/slide-01.pptx
```

Add `--handoff` when exact source text, selected canonical assets, a generation region, deck chrome, or other upstream reconstruction context matters. Add `--design` for a deck-specific design snapshot. Add `--refinement-plan` when the Agent has identified peer groups that should move together.

The command performs the established construction logic in this order.

1. Compile the Agent-authored semantic scene.
2. Measure the accepted image with OpenCV and OCR.
3. Use SAM for eligible irregular filled regions when its optional dependencies are available.
4. Build the reconstruction contract.
5. Apply bounded refinement and Office-safe text fitting.
6. Compile native PowerPoint objects.
7. Construct and verify a one-slide `.pptx` package.

Use `--sam never` for the lightweight OpenCV path. Auto mode uses SAM for eligible objects when its checkpoint and optional dependencies are available.

## Review and iterate

Render the reconstructed PowerPoint when a compatible local renderer is available. Compare it with the accepted image and inspect editable object behavior. Let the Agent decide whether differences are material. Revise the visual analysis, handoff, refinement plan, or generated image according to the actual cause.

Confirm that construction inputs are readable, geometry is valid, referenced assets are available, object routes are supported, text fits safely, and the PowerPoint package is healthy. The Agent evaluates editorial quality, source coverage, and semantic confidence during review.

## Assemble the deck

Pass constructor scenes to `slidecraft render-scenes` in the intended order.

```bash
slidecraft render-scenes \
  --scene /absolute/path/working/slide-01/constructor_scene.json \
  --scene /absolute/path/working/slide-02/constructor_scene.json \
  --output /absolute/path/project/deliverables/presentation.pptx
```

The order of `--scene` arguments is the deck order. The Agent owns that order and the deck-level coherence review.

## Continue existing work

Inspect the project files and current deliverables. Reuse accepted images, measurements, semantic scenes, and constructor scenes when their inputs still match. Rerun reconstruction after an accepted image changes. Rerun assembly after a deck-order change.

Return the editable PowerPoint for final-deck requests. Return the storyboard, generated image, measurement debug view, constructor scene, or single-slide PowerPoint when the user asks to review progress.
