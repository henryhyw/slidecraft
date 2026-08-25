# Framework naming conventions

The framework separates visual evidence, governing configuration, deterministic construction, and real PowerPoint file formats.

| Canonical term | Meaning | Excluded meaning |
| --- | --- | --- |
| Visual reference page | A whole-slide image or preview used as a visual precedent for typography, density, whitespace, hierarchy, color, diagram language, and polish | An editable layout source or PowerPoint master |
| Visual Reference Library | The indexed collection from which up to three visual reference pages are retrieved | A PowerPoint template gallery |
| Deck design configuration | Authoritative dimensions, excluded regions, chrome, title rules, typography, color roles, density, icon treatment, connector style, and visual conventions | A retrieved reference image |
| Guidance profile | Communication and reasoning guidance for a deck type, such as consulting, academic, or investor communication | Brand geometry or slide styling |
| System layout | A deterministic editable construction used for low-information structural slides such as covers and section dividers | A visual reference page |
| Known Component Library | Reusable editable constructions such as maps, structured diagrams, and stable compound visuals | Generated raster evidence |
| PowerPoint template | Reserved for a real `.potx`, theme, slide master, or layout-master integration | Any of the visual references above |

## Canonical machine names

- `visual_references`
- `visual_reference_retrieval`
- `visual_reference_retriever_v1`
- `visual_reference_manifest`
- `deck_design_configuration`
- `system_layout`
- `system_layout_id`

External provider identifiers remain unchanged. For example, a Tabler icon file may retain an upstream glyph name containing the word `template`. That identifier describes the external icon asset and is never used as framework terminology.

Existing saved runs created before this change may contain former numbered field names. Temporary input adapters migrate those legacy names when loading old deck settings, slide requests, orchestration states, and reconstruction handoffs. Migration notices are recorded. New outputs use only the canonical terms above.
