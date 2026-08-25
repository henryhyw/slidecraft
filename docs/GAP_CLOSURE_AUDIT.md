# Gap Closure Audit

## Closed in the supported Agent-host release

| Area | Current state |
| --- | --- |
| Exact-content authority | Exact source fields become 27 traceable source atoms for the architecture slide |
| Constraint register | Explicit instructions are classified as hard, soft, or preference with category, source, confidence, and status |
| User assets | Canonical files, semantic roles, hashes, provenance, and mandatory status are retained |
| Semantic planning | Multiple structures are proposed, scored, selected, and audited for exact-source traceability |
| Visual-reference retrieval | Local metadata-first ranking with a maximum of three results and structural-family diversity |
| Icon retrieval | Local semantic metadata ranking, exact upstream asset priority, coherent set selection, and alternative candidates |
| Known-component retrieval | Local manifest search with confidence thresholds, implementation availability checks, and a Slide understanding entity-level requery policy |
| Generation handoff | Intake, constraints, source atoms, retrieved candidates, exact content, style, assets, and policy reach Slide understanding |
| Evidence separation | OCR, contours, masks, edge fragments, and generated glyphs remain reconstruction evidence |
| Reconstruction policies | Authored text, canonical icon slots, semantic connector graphs, known components, images, and fitted geometry have explicit routes |
| Automatic semantic mapping | Provider-neutral structured VLM mapping compiles meaningful entities, source mappings, canonical assets, connector graphs, groups, z-order, and SAM eligibility into Semantic mapping |
| General constructor scene | Slide understanding and Editable reconstruction contracts compile into a reusable scene IR with Office-scaled native text, canonical assets, shapes, and native connector graphs |
| Agent-native workflow | Typed deck plans, deterministic structural-slide routing, passive artifact persistence, derived next actions, and cross-slide coherence checks are implemented |
| Portable constructor routes | Native text, tables, editable charts, SVG assets, semantic connector graphs, standard shapes, fitted freeforms, raster images, z-order, and source notes are implemented |
| Distribution | Wheel build, starter collections, MCP adapter, explicit constructor dependency setup, and isolated-install rendering are verified |
| Capability safety | Normal runs never invoke permission dialogs. PowerPoint automation is explicit setup-only and time bounded |

## Partially closed

### Extended multimodal extraction

The intake manifest and source-atom contract are implemented. The current runtime handles text, JSON, CSV, PDF, DOCX, XLSX, XLSM, PPTX text, source-grounded host interpretations of images and diagrams, exact content, notes, and canonical assets. Path-only visuals remain explicitly pending until the host Agent interprets them. Audio transcription, URL capture, scanned-document vision, and PPTX shape-level extraction remain optional adapter extensions. They are outside the currently advertised supported-material set.

Each adapter must produce source atoms with stable locators such as page, paragraph, table cell, slide shape, worksheet cell, image region, timestamp, or URL fragment. Tables and charts must retain structured data instead of becoming plain text.

### Constraint reasoning

Explicit constraint classification has a deterministic baseline. A managed reasoning adapter still needs to detect implied hard constraints, conflicts across materials, superseded instructions, conditional requirements, and missing decisions.

The gate policy is settled. An unresolved hard constraint pauses the run and asks the user. Soft constraints can be balanced by semantic planning. Preferences can yield when they conflict with hard requirements or legibility.

### Managed semantic planner

The schema, prompt, candidate comparison, traceability audit, host execution, and OpenAI-compatible structured reasoning provider work. Additional provider families can implement the same interface.

### Visual-reference indexing

The three current pages have complete metadata and retrieve correctly. A scalable indexer still needs to extract previews and propose metadata from PPTX files, allow human correction, validate licenses, compute embeddings when enabled, and update the local index.

### Icon indexing

The current Tabler subset has semantic metadata and retrieves correctly. A production local index should cover the full installed library, aliases, style families, stroke policies, license metadata, and optional embeddings.

### Known components

The manifest schema, example map, semantic retrieval, confidence threshold, and reconstruction policy exist. The editable PPTX-fragment importer, primitive-recipe interpreter, parameter binder, preview generator, and trusted Python factory loader remain to be built.

### Source-to-output traceability

The handoff preserves source atoms and semantic traceability. Constructor scenes attach source references to content-bearing objects and the PPTX stores a slide-level source ledger in speaker notes. A richer human-facing lineage report remains a product enhancement.

## Deferred coverage extensions

| Priority | Gap | Required completion |
| --- | --- | --- |
| P1 | Known-component runtime | Editable fragment import, recipes, factories, parameter binding, and ports |
| P1 | Local library indexers | Visual-reference, icon, component, and style indexing commands |
| P1 | Native rendering evaluation | Gold-deck Office fidelity suite and bounded automatic compare-and-refit loop |
| P2 | Evaluation suite | Gold slides, semantic coverage, retrieval relevance, editability, and Office-render fidelity benchmarks |
| P2 | Library governance | Versions, provenance, licenses, deprecation, compatibility, and migration |

These items expand coverage and reusable resources. They do not block the supported Agent-host flow. Unavailable or uncertified known components stay as retrieval evidence and automatically use a supported reconstruction route.

## Retrieval contracts

### Visual-reference query

The visual-reference query combines slide objective, selected communication archetype, relationship types, density, visual conventions, diagram conventions, and deck style.

Ranking uses semantic metadata. A diversity correction penalizes repeated structural families. The final result contains at most three pages. Only selected files are attached to generation or opened for VLM verification.

### Icon query

Each asset need contains semantic role, purpose, concepts, requirement status, and semantic size role. Retrieval ranks local icon metadata. Exact user or upstream assets bypass substitution. Remaining roles are selected jointly to maintain distinction and one coherent style family.

### Known-component query

Before generation, the query uses semantic units, concepts, relationships, and required parts. After Slide understanding, the framework requeries using the identified entity's role, internal parts, topology, text or data bindings, measured aspect ratio, and visual family.

The component route activates only when confidence exceeds the component's declared threshold and required parameters can be resolved.

## Multimodal source model

Every material receives a stable material ID and provenance record. Extracted information becomes source atoms.

```json
{
  "atom_id": "SOURCE_042",
  "material_id": "UPLOAD_FINANCIAL_MODEL",
  "modality": "spreadsheet",
  "locator": "Revenue!B12:E12",
  "value": [120, 145, 171, 205],
  "authority": "authoritative",
  "extraction_confidence": 1.0
}
```

Semantic units cite one or more atoms. Generated supporting visuals cite a semantic role and generation decision. Editable reconstruction object records cite their semantic units. This creates an auditable chain from user material to editable object.

## Constraint precedence

Use this default precedence order.

1. Safety, legal, and file-integrity policies
2. Explicit current user hard constraints
3. Authoritative exact content and data
4. Mandatory asset and brand requirements
5. Deck-level hard configuration
6. Project and workspace hard configuration
7. Soft constraints
8. Preferences
9. Model design choices

Conflicts at the same level require explicit resolution. A newer user instruction can supersede an older one when the source order is known and the change is unambiguous.

## Acceptance condition

The framework is gap-closed when an arbitrary supported material set can be ingested, cited, constrained, structured, retrieved against local libraries, generated, understood, reconstructed, and validated without slide-specific code or undocumented human intervention.
