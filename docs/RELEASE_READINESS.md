# Release Readiness

## Current status

The repository is an installable alpha framework. The portable path supports planning, generation-package assembly, host or OpenAI provider boundaries, semantic mapping, deterministic measurement, reconstruction-contract generation, editable text, tables, charts, shapes, fitted freeforms, canonical SVG assets, native connector graphs, source notes, package validation, and optional Microsoft PowerPoint rendering on macOS.

The functional Agent-host path is complete. A stable 1.0 tag still needs broader release certification across clean machines.

- Native Office render parity fixtures on supported macOS versions
- Windows and Linux construction and package-validation coverage
- A larger gold-deck quality suite covering dense tables, charts, screenshots, and irregular visuals

The framework intentionally has no monolithic `slidecraft run` state machine. Host Agents own session progression. `workflow_status` derives exact next actions from the passive artifact ledger. MCP, CLI, and Python transports expose the same capabilities.

## Acceptance policy

A run may publish a PPTX only when every reconstruction route in its scene is supported by the selected backend, semantic and connector conformance checks pass, required canonical assets resolve, text fitting reports no overflow, and package validation succeeds. When configured, native Microsoft PowerPoint rendering is an additional publish gate.

The framework does not silently fall back to an unsupported constructor route. It returns a machine-readable failure before accepting partial output.
