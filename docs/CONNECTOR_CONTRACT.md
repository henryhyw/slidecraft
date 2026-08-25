# Connector system

Slidecraft treats connectors as semantic relationship graphs.

## Generation

The image-generation brief asks the image model to decide conceptual endpoints and topology before drawing. It requests clear standard routes, visible arrowheads, axis-aligned peer flows, minimal bends, and meaningful attachment. Generated connector pixels remain a visual proposal.

## Focused semantic audit

Semantic mapping first identifies objects, groups, containment, and candidate relationships. A focused second visual-reasoning pass then audits every connector against the full semantic scene and upstream content.

The audit resolves:

- conceptual source owners
- conceptual target owners
- relationship type and direction
- one-to-one, branch, merge, or many-to-many topology
- route feasibility within the existing layout
- routing orientation
- logical junctions and visible junction semantics
- approximate routing corridors and visual style

The audit preserves the composition. It does not redesign the slide.

## Deterministic compilation

The compiler snaps endpoints to the boundary of the audited semantic owner. Raster endpoints remain soft evidence. Horizontal peer flows share a centerline. Ordinary logical junctions remain invisible. A visible junction requires an independent semantic role.

Topology and route family are separate decisions. The active design profile may normalize an ambiguous curve into a clean orthogonal bus. The renderer emits native PowerPoint connectors only.

Route optimization follows a fixed priority order:

1. semantic ownership and direction
2. containment and collision safety
3. zero-bend feasibility
4. minimum bend count
5. horizontal or vertical alignment
6. terminal clearance and arrowhead visibility
7. peer-route consistency and symmetry
8. raster resemblance

For a branch or merge terminal, the compiler projects the logical junction onto the selected owner boundary. It uses a centered attachment only when projection is infeasible. This prevents an avoidable slope or final bend.

## Segment joints and near-axis normalization

One-to-one connectors are simplified before serialization. If source and target anchors are horizontally or vertically aligned within the configured tolerance, raster-derived intermediate junctions are discarded and one straight native connector is emitted. This prevents tiny image-generation offsets from becoming visible doglegs or disconnected multi-segment joins.

When a routed connector genuinely needs multiple segments, every adjacent segment receives the same shared endpoint coordinate. Near-axis segments are snapped, duplicate points are removed, collinear points are collapsed, and round line caps close subpixel seams. Only the final segment receives an arrowhead.

The relevant design configuration values are `collapse_aligned_one_to_one`, `snap_near_axis_segments`, `axis_alignment_tolerance_px`, `segment_join_policy`, and `segment_line_cap` under `connectors.routing`.

## Conformance

Compilation checks endpoint cardinality, required shared junctions, route support, terminal clearance, owner attachment, axis alignment, junction semantics, arrowhead size, and object coverage. The constructor never traces raster connector fragments or emits separate arrowhead shapes.

Synthetic routing tests use arbitrary component IDs and geometry. They provide a clean-room check that routing behavior comes from repository policies instead of slide-specific patches or conversational context.

## Automatic recovery boundary

When a model endpoint is available, the focused audit is a second schema-constrained model call. Host-agent mode supports the same two-pass contract through an operation-result bundle. Intermediate audit artifacts remain inspectable and resumable.
