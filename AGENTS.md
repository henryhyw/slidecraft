# Working with Slidecraft

Slidecraft is a presentation creation framework. Follow its planning method, shared project model, design system, resource workflow, semantic reconstruction logic, and review standards. Local scripts provide deterministic measurement, reconstruction, text fitting, connector routing, and PowerPoint construction.

## Use the skill

Read `integrations/skills/slidecraft/SKILL.md` for every presentation task. Follow its planning and reconstruction references. The skill defines the orchestration method.

Use a local project folder for deck work so the Agent and web app share configuration, design, resources, artifacts, and deliverables. Read `slidecraft project context` before planning and when settings may have changed.

For a new deck, inspect the supplied material and research only what can improve the audience decision or evidence. Discuss the synthesis, key assumptions, proposed slide count, storyline, and one conclusion-led message per slide when the work is collaborative. Continue autonomously when the user delegates those decisions.

Treat required topics as evidence obligations. Create a slide only when it advances the governing argument. Keep research in the background when it only informs the reasoning.

Use image generation for every information-bearing slide. Technical structure, tables, comparisons, process stages, and simple arrangements still require an image-generation composition before reconstruction. Deterministic native layouts are limited to the cover and section-transition roles, including appendix dividers. Never bypass this route by authoring a content slide directly in PowerPoint.

## Build with local commands

Use ordinary project files. Keep planning artifacts, generated images, visual analyses, measurements, constructor scenes, and deliverables in paths that are clear to the Agent and user.

For an accepted slide image, author the semantic visual analysis and run:

```bash
slidecraft reconstruct-slide \
  --project /absolute/path/project \
  --image /absolute/path/generated.png \
  --visual-analysis /absolute/path/visual-analysis.json \
  --slide-id slide-01 \
  --output-dir /absolute/path/working/slide-01 \
  --output /absolute/path/project/deliverables/slides/slide-01.pptx
```

This command composes the established construction logic. It compiles the semantic scene, measures with OpenCV and optional SAM, builds the reconstruction contract, applies bounded refinement and Office-safe text fitting, compiles native objects, and verifies the PowerPoint package.

Assemble constructor scenes in the intended order with `slidecraft render-scenes`. The Agent owns deck order and deck-level coherence.

## Keep judgment with the Agent

The Agent decides whether the story is useful, the evidence is sufficient, the slide messages are relevant, and the visual result is acceptable. Construction code confirms input readability, geometry, asset availability, object-route support, text fit, and PowerPoint package integrity.

Return the editable `.pptx` for final presentation requests. Return the storyboard, generated image, measurement view, constructor scene, or single-slide PowerPoint when the user asks to review intermediate work.
