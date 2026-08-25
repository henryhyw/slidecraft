# User interaction and generation preflight

## Configuration layers

The framework separates long-term configuration from run-resolved decisions.

| Layer | Typical contents | Confirmation frequency |
| --- | --- | --- |
| Guidance profile | Communication principles, reasoning patterns, writing discipline, anti-patterns | When the user selects or changes the deck type |
| Density profile | Semantic units, evidence range, relationship range, word-range guidance, sparse-slide policy | Selected from predefined profiles, usually once per deck |
| Deck design configuration | Slide dimensions, header and footer heights, title system, typography, color roles, icon treatment, connector system, and visual conventions | Once per deck design system or when changed |
| Run-resolved deck plan | Objective, audience, desired outcome, storyline, sections, source allocation, and slide routes | Before generating the deck |
| Run-resolved slide plan | Slide objective, governing message, title, subtitle, chrome content, exact content, hard constraints, assets, and references | Before generating the slide, usually approved through a deck matrix |

Header and footer heights belong to the deck design configuration. Header and footer text belongs to the run-resolved slide plan. The framework can propose text from deck, section, slide role, title, confidentiality, date, and slide-number context. The user can replace any proposed field before approval.

## Default interaction

1. The user supplies documents, data, images, logos, notes, and constraints through chat or a request file.
2. The intake layer registers every source with provenance, authority, and a stable locator.
3. The framework prepares up to three optional, high-value questions before planning. It asks only when an answer can materially change the storyline, governing message, scope, evidence standard, or decision framing.
4. The planner resolves the guidance profile, predefined density profile, deck storyline, slide objectives, source allocation, and generation routes.
5. The framework proposes run-specific titles, subtitles, chrome content, asset usage, and slide metadata where the user did not specify them.
6. The preflight builder creates a concise approval summary and a complete generation package.
7. The user approves the fingerprint or requests changes.
8. External image generation is released only for the approved fingerprint.
9. A material change invalidates approval and creates a new fingerprint.

If the user says “take this over,” the framework may resolve all proposal-eligible fields. The default approval boundary still applies before paid or external image generation. A workspace policy may explicitly enable automatic approval.

## High-value clarification policy

Clarification is a planning aid and never a mandatory questionnaire. The selector considers audience and decision, desired action, governing answer, situation and complication, scope, time horizon, proof requirement, stakeholder sensitivity, and success criteria. It excludes questions already answered by the request or sources. It also excludes questions whose answer changes only cosmetic styling.

Each question explains why the answer matters and offers a short set of mutually exclusive choices. Every question includes an explicit option that delegates the choice to the Agent. The user may skip the complete set. In that case, the framework records the assumptions it makes and continues planning.

The host Agent owns presentation of the questions. A host with structured elicitation support can render choices through its native interface. Other hosts ask the same package conversationally. Both routes call `record_clarification_answers`, so the downstream planner receives one normalized artifact with source provenance.

## Human approval summary

The concise summary should expose decisions and risks without repeating the full prompt. It includes:

- Deck objective, audience, desired outcome, guidance profile, and density profile
- Storyline and section structure for a multi-slide deck
- A slide matrix showing slide number, role, objective, governing message, title, route, and source allocation
- Header and footer content proposed by the Agent or supplied by the user, with provenance clearly distinguished
- Mandatory and optional assets, semantic roles, status, and intended slide usage
- Selected visual reference pages and their purpose
- Hard constraints and explicit prohibitions
- Unresolved assumptions, conflicts, missing inputs, and blocked slides
- Source coverage, including required material that was excluded or moved to an appendix
- Generation count, selected model route, and any known cost or privacy implications when available
- The approval fingerprint and the classes of change that invalidate it

## Detailed generation package

The detailed package is machine-oriented and remains available for inspection. It contains exact source content, source atoms, semantic design, configuration snapshots, resolved chrome, normalized assets, visual references, route decisions, and the draft image-generation prompt. Slide understanding receives the same approved package with the generated image.

## Uploaded assets

Chat and agent hosts usually expose uploaded files through an accessible temporary path. The attachment adapter passes that path to the project asset ingestor. The ingestor copies the file into a project-scoped store, computes a SHA-256 identity, records the original attachment name and source locator, deduplicates identical files, and writes a manifest entry.

Every upload requires a usage class:

- `mandatory` means the asset must appear in its assigned semantic role
- `optional` means the framework may use it when beneficial
- `reference_only` means it can inform visual understanding but cannot become slide content
- `do_not_use` means it is retained for context or audit and excluded from generation

The user can express this naturally. For example, “These are the OpenAI and OpenCV logos. Both are mandatory.” The interaction agent maps that statement to semantic roles and usage classes, then shows the result in preflight.

For a multi-slide project, direct-use visual assets live inside the broader project resource catalog. Chat uploads, console uploads, and files placed in `sources/assets/` converge on its Visual assets category. The default policy is `available`. `preferred` asks the planner to use an asset when it strengthens a relevant slide. `required_somewhere` requires at least one semantically suitable placement. Deck-level requirements never imply placement on every slide.

Adding a catalog entry makes the asset available to the project. The next planning or revision request can assign it to specific slides. Once accepted, that assignment becomes part of the slide's tracked inputs.

## Multi-slide approval

Large decks should not require opening every detailed generation package. The preferred interaction is one deck-level approval plus a compact slide matrix. Slides with unresolved questions, unusual assets, route exceptions, or unique chrome receive explicit exception cards. Users can approve the whole run, approve selected slides, or request changes for specific slides.

## Safety and consistency

Approval is tied to a fingerprint of the complete generation package. Changes to authoritative content, hard constraints, mandatory assets, title text, chrome content, route, or deck design configuration invalidate the fingerprint. Diagnostic wording and other nonmaterial report changes do not.
