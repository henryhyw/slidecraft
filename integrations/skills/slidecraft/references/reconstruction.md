# Image reconstruction

Use this reference when converting an accepted generated slide image into editable PowerPoint.

## Agent-authored visual analysis

The visual analysis describes authored objects and relationships in normalized coordinates from 0 to 1000. Use the packaged schema at `slidecraft/schemas/semantic_scene_draft.schema.json` as structural guidance.

Identify semantic PowerPoint-level objects such as complete text blocks, shapes, tables, charts, icons, images, groups, and connector systems. Treat OCR words, raster contours, individual letters, edge fragments, and decorative pixels as measurement evidence.

For every meaningful entity, choose a reconstruction route such as native text, native shape, native table, native chart, canonical asset, native connector system, fitted custom geometry, or raster image region. Preserve meaningful grouping, containment, reading order, stacking, and connector ownership.

Use the `quality` object to record the Agent's assessment for review and iteration.

## Optional reconstruction handoff

The direct reconstruction command can infer a full-slide canvas and visible-text fallback from the image. Supply a handoff when upstream knowledge should control reconstruction.

```json
{
  "full_slide_dimensions_px": [2048, 1152],
  "generation_region": {
    "offset_y_px": 41,
    "dimensions_px": [2048, 1070]
  },
  "exact_title_text": "Exact slide title",
  "exact_source_content": {
    "title": "Exact slide title",
    "content": ["Exact authored text or structured values"]
  },
  "semantic_design": {
    "message": "What the slide communicates",
    "visual_job": "What relationships the composition shows"
  },
  "selected_assets": [],
  "deck_chrome_configuration": {
    "enabled": false
  }
}
```

Include fields that materially guide reconstruction. The direct workflow supplies operational defaults for the remaining context.

Selected assets should retain an exact local file path, stable asset ID, semantic role, and placement role. Map a detected icon or supplied image to an asset when the visible image and upstream intent support its identity.

## Optional refinement plan

Reconstruction preserves measured positions by default. Supply a refinement plan when peer groups should align or normalize.

```json
{
  "schema_version": "1.0.0",
  "authored_by": "agent_reasoning",
  "coordinate_space": "generation_region_px",
  "decision_rationale": "Why these peers should move together",
  "alignment_groups": []
}
```

Alignment groups describe a semantic relationship among peers. Deterministic construction preserves containment, clearance, text fit, and connector attachment while applying the requested adjustment.

## Direct reconstruction

```bash
slidecraft reconstruct-slide \
  --image /absolute/path/generated.png \
  --visual-analysis /absolute/path/visual-analysis.json \
  --handoff /absolute/path/handoff.json \
  --design /absolute/path/design.json \
  --refinement-plan /absolute/path/refinement.json \
  --slide-id slide-01 \
  --output-dir /absolute/path/working/slide-01 \
  --output /absolute/path/working/slide-01/slide.pptx
```

Use `--sam never` when the OpenCV path is sufficient. Auto mode uses SAM for eligible irregular filled objects when its optional runtime is available.

The command returns paths to the normalized handoff, semantic scene, measured scene, measurement overlay, reconstruction contract, constructor scene, and editable PowerPoint.
