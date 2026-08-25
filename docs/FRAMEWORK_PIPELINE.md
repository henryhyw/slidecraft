# Presentation workflow

Slidecraft structures the complete presentation process from source material to editable PowerPoint. Its planning method guides research, audience reasoning, storyline development, slide design, and review. Its construction system turns accepted designs into editable PowerPoint objects.

## Shared project context

A project folder holds materials, assets, working artifacts, settings, and deliverables. The Agent and web app use this folder as their shared source of truth.

```bash
slidecraft project context /absolute/path/project
```

The context includes the effective configuration, resolved deck design, selected resources, current artifacts, pending user changes, and presentation outputs.

## Planning

The planning method interprets the source material, incorporates relevant research, defines the audience transformation, and compares plausible storylines. During collaborative work, the user receives a research synthesis and storyboard containing the recommended slide count and one conclusion-led message for every slide.

The accepted storyboard becomes an ordinary project artifact.

```bash
slidecraft project record /absolute/path/project \
  --path /absolute/path/project/.slidecraft/working/storyboard.json \
  --logical-key deck/plan \
  --kind deck_plan
```

## Slide design

Each slide begins with a communication contract that defines its audience question, message, evidence, consequence, visual job, and transition. Relevant project assets and reusable visual resources are selected from the shared context.

Information-bearing slides can use image generation for composition. Structural pages and straightforward arrangements can use native PowerPoint layouts directly. Candidate review covers message fidelity, hierarchy, grouping, relationships, legibility, and deck-style coherence.

## Semantic reconstruction

For an accepted slide image, semantic visual analysis describes complete PowerPoint-level objects and their relationships in normalized coordinates. The reconstruction command then performs this sequence.

1. Compile the semantic scene.
2. Measure geometry, color, text regions, and line structures with OpenCV and OCR.
3. Apply SAM to eligible irregular filled objects when its runtime is available.
4. Resolve text, shape, table, chart, image, icon, connector, and custom-geometry routes.
5. Apply bounded alignment and Office-safe text fitting.
6. Compile native PowerPoint objects.
7. Verify the resulting package.

```bash
slidecraft reconstruct-slide \
  --project /absolute/path/project \
  --image /absolute/path/generated.png \
  --visual-analysis /absolute/path/visual-analysis.json \
  --slide-id slide-01 \
  --output-dir /absolute/path/project/.slidecraft/working/slide-01 \
  --output /absolute/path/project/deliverables/slides/slide-01.pptx
```

Project reconstruction records the resolved design, semantic scene, measurement, reconstruction contract, constructor scene, and editable slide in the shared artifact manifest.

## Review and assembly

Review compares the reconstructed result with the accepted design and checks editability, message fidelity, hierarchy, relationships, legibility, and cross-slide coherence. Revisions target the actual source of the difference, such as the generated image, visual analysis, asset mapping, or refinement plan.

Constructor scenes are assembled in storyboard order.

```bash
slidecraft render-scenes \
  --scene /absolute/path/project/.slidecraft/working/slide-01/constructor_scene.json \
  --scene /absolute/path/project/.slidecraft/working/slide-02/constructor_scene.json \
  --output /absolute/path/project/deliverables/presentation.pptx
```

The final review covers the argument, evidence, visual rhythm, repeated design roles, editable behavior, and PowerPoint package health.
