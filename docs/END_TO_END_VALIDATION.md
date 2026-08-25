# End-to-end validation

Validation date is 25 August 2026 on Apple silicon macOS.

## How projects continue across sessions

The agent app manages the live conversation. Slidecraft saves accepted inputs, active revisions, source links, validation results, and deliverables in the project folder. A new session reads this record and continues from the latest valid result.

## Verified capability path

The installed package completed this sequence.

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
- An agent can create a project by name, record the presentation brief, and receive the next useful planning action through the installed tools.
- `slidecraft init` installs the constructor runtime into the configured user data directory.
- `slidecraft check-install` passes in the isolated installation.
- The installed CLI renders an editable PPTX without repository-local JavaScript packages.
- Presentation package validation passes.
- Text-overflow validation passes.
- The local dashboard responds successfully on port 8765.

## Local capabilities and integrations

- Agent apps with vision and image generation can supply both capabilities directly.
- The System page connects an OpenAI or compatible image service for agent apps that need image generation.
- OpenCV provides local measurement. SAM 2 adds boundary detection for irregular filled regions.
- Microsoft PowerPoint for Mac can render reconstructed slides and verify Office typography against the target image.
- The current alpha is tested on Windows, Linux, and macOS. The 1.0 quality program will add more Office versions and a larger gold-deck suite.
