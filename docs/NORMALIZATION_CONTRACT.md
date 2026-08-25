# Constrained normalization contract

The image model supplies the composition and approximate geometry. Slide understanding supplies measured objects, semantic ownership, parent containers, and candidate peer relationships. The refinement reasoning pass supplies explainable alignment intents. A deterministic solver decides whether each intent is safe to apply.

## Processing sequence

1. Build semantic groups before proposing movement. A badge containing a background, logo, and label is one movable object.
2. Identify peer groups from semantic role, repeated parent structure, reading order, and near-alignment evidence.
3. Select an anchor that expresses the design relationship. Parent-relative anchors are preferred across separate containers.
4. Compute the robust target from the peer median or an explicit configured grid.
5. Translate each peer within its configured movement bound.
6. Validate parent containment, object clearance, text fit, z-order, semantic order, and connector topology.
7. Apply the transaction only when the alignment error improves enough. Otherwise retain the measured geometry.
8. Reroute attached native connectors and run native PowerPoint text validation after accepted movement.

Clear component rows can also be inferred automatically. Two or more icon slots that share a semantic parent, have similar dimensions, overlap vertically, and fall within the configured center-line tolerance form a candidate peer row. Nearby technology labels join that row. The solver moves each slot surface and canonical glyph as one rigid unit to the shared center line, subject to the same movement and containment limits.

## Current slide example

The two technology badges are semantically equivalent attribution components. Their stage containers are peers. The intended relationship is a shared bottom inset. Based on the current image measurements, the robust target is approximately 13.5 px. The GPT Image 2 badge moves down about 5.5 px and the OpenCV + SAM 2 badge moves up about 5.5 px. Their dimensions and internal content remain unchanged.

The executable regression fixture is in `tests/fixtures/architecture/normalization_plan.json`. The solver configuration is in `config/normalization_config.json`. The reusable implementation is in `src/slidecraft/refinement/constrained_normalization.py`.

The constructor also applies a final native-text gate. It revalidates supplied text-fit contracts, includes literal bullet prefixes in width measurement, applies configured line spacing and margins, rounds font sizes downward to the configured point grid, and rejects any textbox that still cannot fit. The current design profile uses a 0.5 pt grid and emits explicit `noAutofit` OOXML.

## Guardrails

- No correction may cross a parent boundary.
- No correction may create a new overlap or violate minimum clearance.
- Width and height remain fixed unless a separate, explicitly authorized size-normalization intent exists.
- Child fragments never move independently when they belong to one semantic object.
- Textbox content, margins, and wrapping policy stay intact during geometric translation.
- Low-confidence relationships remain unchanged.
- Aesthetic preference alone is insufficient. Every move needs a declared semantic relationship.
