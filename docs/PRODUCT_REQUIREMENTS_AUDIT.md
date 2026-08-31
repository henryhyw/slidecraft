# SlidePoise product requirements audit

This audit records the product state before new showcase slides are created. The implementation inventory below must be read alongside the integration checks and host limitations. It cannot establish that every future run will be defect-free.

| Requirement | State | Evidence |
|---|---|---|
| SlidePoise is a framework instead of a single prompt file | Complete | `setup.py`, `framework/`, `profiles/`, `library-sets/`, `webapp/`, and the installed skill form one self-contained package. |
| Updates preserve user configuration | Complete | Versioned setup merges new known defaults and preserves configured values. Tests cover migration and preservation. |
| Stable Agent instructions are separate from configurable material | Complete | Product rules live in `slidepoise/`. Global configuration, profiles, Library Sets, run files, runtimes, and migration backups live outside the installed skill. |
| Three supplied design profiles | Complete | Consulting, Editorial Archive, and Monochrome Modern are installed with full guidance and profile-owned visual references. |
| Visual references belong to profiles | Complete | Profile libraries contain only `visual_references`. Legacy profile icon and component copies are retained under the project archive and excluded from installation. |
| Icons and components are shared coherent sets | Complete | `library-sets/` contains shared remote icon sets and local native component sets. Profiles select whole sets. |
| Remix Icon line and fill decision happens after design generation | Complete | Both official variants enter the resource flow. The Agent selects the canonical reconstruction variant after inspecting the approved image. |
| Wikimedia Commons is available for logos and public identity assets | Complete | Search and fetch scripts retain source, identity, license, attribution, trademark, and checksum evidence. |
| SVG Repo is absent | Complete | It is not an allowed provider in config resolution, packaged catalogs, or retrieval instructions. |
| Remix Icon and Wikimedia are selected without duplicate controls | Complete | Both providers appear as shared Icon Sets in Resources. Each Profile chooses its permitted sets. The System page does not repeat these choices. |
| Components remain native and inspectable | Complete | Component Sets retain editable PowerPoint sources. Console opens the native object workspace and can open the source file. |
| SAM remains non-blocking | Complete | Setup attempts to install SAM by default in the isolated runtime. Failure leaves the complete OpenCV route intact. An installed model activates automatically only for eligible Agent-authored irregular objects and never supplies a semantic or visual verdict. |
| Three hard human approval gates | Complete | Plan, resources, and generated image gates remain mandatory in the skill and evidence contracts. |
| Reasoning gates replace heuristic workflow verdicts | Complete | Deterministic scripts collect facts and construct files. The host Agent owns semantic, alignment, connector, raster, and visual decisions. |
| Bounded multi-Agent review | Complete | Plan, resources, semantic mapping, and reconstruction have read-only review contracts with one correction pass. Single-Agent fallback is explicit. |
| Raster composition handles embedded lettering and textured overlap | Complete | Intrinsic lettering remains owned by its raster. External text requires a reviewed clean plate or a disclosed composite-preservation choice. |
| Large usable image regions can be reused without needless regeneration | Complete | The Agent inspects original crops at intended output size and records a reuse, refine, replace, or remove decision. No fixed size heuristic gives the verdict. |
| Connector reconstruction is Agent-directed | Complete | The Agent chooses owners, ports, topology, and necessary waypoints. Runtime binds one continuous connector object to frozen geometry. |
| Session Panel follows the current conversation | Complete | Conversation-local binding, four stage tabs, session assets, style overrides, version viewing, rollback selection, preview refresh, and artifacts are implemented. |
| Standalone Console manages persistent product state | Complete | Profiles, profile references, Library Sets, the run registry, and capabilities remain separate from the session Panel. Runs are created and connected by the Agent. |
| Panel edits reach the Agent | Implemented with transport fallback | Supported session mutations share durable events. Explicitly bound running Codex tasks receive a steering attempt through the local control socket. Checkpoint reads cover unavailable connections and idle tasks. |
| Agent work reaches the Panel | Complete | The Agent publishes structured activity and canonical artifacts. The Panel polls and follows the active stage, current step, versions, previews, and evidence. |
| A browser edit interrupts an already-running image or shell call | Platform boundary | A local browser cannot interrupt an indivisible host tool call. The edit is durable and is applied at the first checkpoint immediately after the call returns. |
| Workflow progress is user-facing and honest | Complete | The Panel shows stage-specific steps, their purpose, a reduced-motion-safe live indicator, waiting and failure states, and no invented percentage. |
| Traceability includes generation, semantics, OpenCV, optional SAM, and reconstruction | Complete | User-facing disclosures explain each evidence group. Raw prompt, semantic map, overlays, measurements, construction contract, and reviews stay one level deeper. |
| Versions preserve history without destructive rollback | Complete | Stage selections mark downstream work as previous. Old files remain intact. The Agent creates the next iteration from the chosen stage. |

## Coordination guarantee

Panel changes are durable immediately. The bridge attempts `turn/steer` only for explicitly bound, already-running Codex tasks. It does not start or resume tasks. The Agent reads pending events and current settings at every required checkpoint even when steering succeeds. Delivery does not acknowledge adoption. Agent edits also update the Panel and Console at their next refresh, with open editors protected.

The local Codex control socket was unavailable during the 2026-08-29 verification. Immediate delivery is therefore unverified on this desktop. The fallback preserves all pending changes. The steering protocol is covered by isolated tests, including idle-task and connection-failure cases.

## Integration repairs verified on 2026-08-29

- Session changes affect both Panel revisions and the Agent event queue. Console observes shared profile and resource edits.
- New candidates remain visible while the accepted image is preserved. Archive and publish operations preserve history and resolve rollback display bindings without granting approval.
- Preview rendering uses a frozen input and discards a stale result if the source changes. Source hashes bind published previews to the PowerPoint.
- Imported native components retain their source and acquire a matching page preview before generation. Changed component sources invalidate cached previews.
- Run retrieval reads resolved session configuration, including selected sets and custom reference paths.
- Profile creation copies effective saved style and references into an independent profile.
- The source distribution builds a self-contained wheel. Tests resolve a new run outside the repository using only that wheel and an isolated product home.
- The npm entry resolves user paths from the caller's working directory.

Executable regression evidence lives in `tests/test_product_handoffs.py`, `tests/test_distribution.py`, `tests/test_host_notifications.py`, and the Panel and Console interaction tests. A full creative slide run was not performed for this repair pass.

The current release evidence is generated by the packaged test suites and release checks. The counts in this document are intentionally omitted because the suites evolve. Configuration and profile catalog checks must report no blocking facts. The installed skill must pass its boundary and metadata checks. Native PowerPoint components must render successfully through LibreOffice and Poppler and receive visual inspection. Panel and Console must pass browser checks. Existing presentation artifacts and user configuration must remain preserved.

## Release rule

This document can show product readiness. It cannot approve a slide. Every slide still requires the three user gates and the mandatory visual reviews defined by the skill.
