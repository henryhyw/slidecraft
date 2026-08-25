# End-to-end validation

Validation date is 25 August 2026 on Apple silicon macOS.

## Agent-native control boundary

The host Agent owns the session, workflow decisions, retries, and stopping behavior. Slidecraft stores immutable artifacts, active revisions, provenance, validation, and dependency hashes in a passive local ledger. `workflow_status` derives advisory next actions from that ledger. The dashboard and MCP adapter hold no workflow session.

## Verified capability path

The public capability surface completed this sequence.

1. Prepare generation inputs and register the generation handoff.
2. Register a generated image.
3. Compile a structured semantic scene through the host-result provider boundary.
4. Measure the scene locally with OpenCV.
5. Build a reconstruction contract with semantic routes and canonical icon resolution.
6. Compile the constructor scene with text fitting, containment, z-order, and conformance gates.
7. Render an editable PPTX through the portable PptxGenJS backend.
8. Validate ZIP package integrity, required Office parts, slide count, constructor conformance, and text overflow.
9. Derive a final workflow status of `complete` with no pending action.

The validated output was written to `/tmp/slidecraft_e2e_deliverables.WC9xy5/editable_deck_validated.pptx`.

## Automated evidence

- Python test suite has 77 passing tests.
- The wheel builds successfully in an isolated build environment.
- A fresh virtual environment installs the wheel outside the repository.
- The installed Agent capability surface creates a project by name, records a conversational deck brief, and derives the next clarification action without direct hidden-file access.
- `slidecraft init` installs the constructor runtime into the configured user data directory.
- `slidecraft check-install` passes in the isolated installation.
- The installed CLI renders an editable PPTX without repository-local JavaScript packages.
- Presentation package validation passes.
- Text-overflow validation passes.
- The local dashboard responds successfully on port 8765.

## External capabilities

These are environment capabilities instead of framework state.

- An Agent with native vision and image generation needs no model API configuration.
- A host without native image generation needs a configured image-generation API and credential.
- OpenCV runs locally. SAM 2 is optional and selected lazily for eligible irregular regions.
- Microsoft PowerPoint automation is optional canonical-render validation. It remains disabled until the user explicitly authorizes it.
- Stable 1.0 certification still needs broader Windows, Linux, macOS, and gold-deck coverage. This does not block the supported Agent-host workflow.
