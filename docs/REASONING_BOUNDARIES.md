# Reasoning boundaries

People work with Slidecraft through an AI Agent. The Agent interprets the request, materials, images, and design context. Slidecraft supplies reliable operations that turn those decisions into traceable editable presentations.

## Agent-owned decisions

- Whether clarification is useful and which questions to ask
- How user statements become constraints, preferences, objectives, and source facts
- How a deck storyline and its slide jobs should be organized
- Which slide roles, routes, and configured structural layouts serve the storyline
- What each slide should communicate
- Which reusable visual references, icons, and components fit the task
- What the generated slide contains and how entities relate
- Which canonical asset an icon slot maps to
- Which reconstruction route preserves each authored object
- Connector source, target, topology, direction, and clean route
- Which peer objects should align or share typography
- Whether a generated candidate is strong enough to accept

These decisions are stored as typed artifacts with provenance. Slidecraft validates their structure and references. It does not recreate them from keywords, filenames, proximity, lexical rank, or first-result fallbacks.

## Framework-owned operations

- Project folders, source copying, hashes, locators, and artifact history
- Reusable-resource indexing and candidate search
- Configuration resolution and canvas derivation
- Schema validation and stable ID resolution
- OpenCV measurements and eligible SAM boundary evidence
- Coordinate transforms, mask and contour evidence, and color sampling
- Proportional SVG fitting into authoritative icon slots
- Bounded application of Agent-authored alignment plans
- Joint Office-safe text fitting from Agent-authored semantic roles
- Native connector construction from Agent-authored relationship graphs
- Editable PowerPoint construction and package integrity checks
- Artifact freshness, dependency tracking, and cross-slide conformance

## Why this preserves quality

The agent sees the whole communication problem and can make coherent decisions across slides and resources. Deterministic code then executes those decisions without introducing semantic guesses. Quality gates verify source coverage, containment, legibility, topology, style consistency, package integrity, and other observable requirements. They catch execution failures. They do not design the deck after the fact.

## Retrieval contract

Search functions return candidates and evidence. The agent selects the final set and records why each resource fits. Exact known identities resolve directly. Candidate scores support recall and ordering only. They never authorize final use.

## Refinement contract

The agent identifies the semantic peers and intended relationship. Slidecraft computes the smallest feasible correction and rejects unsafe movement. This keeps normalization intelligent and bounded without encoding slide-specific designs in the constructor.
