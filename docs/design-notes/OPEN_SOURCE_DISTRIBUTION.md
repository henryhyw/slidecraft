# Open-Source Distribution Design

## Product goal

The framework should install as one Python command and work locally with sensible defaults.

```text
pipx install slidecraft
slidecraft init
slidecraft doctor
slidecraft run slide.toml
```

Python owns the public runtime and orchestration surface. Node.js remains an allowed internal constructor dependency when it produces the highest-quality PowerPoint output. Users should not need to understand model orchestration, device selection, checkpoint placement, library indexing, PowerPoint package internals, or workflow state.

## Python-first runtime

Use Python 3.11 or newer. Package the project through `pyproject.toml` and publish wheels to PyPI.

The core runtime should contain these capabilities.

- Typed configuration and contracts
- CLI
- Local artifact history and dependency management
- Local visual-reference, icon, component, and upload libraries
- Prompt orchestration
- Native PowerPoint construction
- Provider and worker plugin discovery

PptxGenJS is the certified portable constructor for the currently supported scene routes. New routes require conformance tests before they can be published.

### Constructor

The framework supports `auto` and `pptxgenjs` constructor modes. `auto` selects the managed PptxGenJS runtime installed by `slidecraft init`. Missing route support stops publication with a structured failure.

PptxGenJS remains available when Node.js is installed. Packaged desktop or container distributions can include a pinned Node runtime and dependencies so the user does not configure them manually.

The Python backend uses the following implementation.

Use `python-pptx` for native textboxes, shapes, tables, charts, pictures, and standard package operations. Add a focused internal OOXML layer based on `lxml` for capabilities that need lower-level control.

- SVG insertion with fallback preview
- Native connector XML and arrowhead settings
- Freeform and Bezier geometry
- Grouped shapes
- Copying editable component fragments between PPTX packages
- Relationship and media remapping
- Explicit text body properties missing from high-level APIs

Keep the OOXML layer private behind a stable constructor interface. Users and component authors should not manipulate raw XML.

## Installation profiles

One package can expose optional dependency groups.

| Installation | Intended user | Contents |
| --- | --- | --- |
| `slidecraft` | Host-agent or API user | Core orchestration, libraries, constructor interface, CLI |
| `slidecraft[cv]` | Local reconstruction | Core plus OpenCV and OCR support |
| `slidecraft[local-ai]` | Local segmentation | CV plus PyTorch and segmentation adapter |
| `slidecraft[server]` | Shared service | REST API and server runtime |
| `slidecraft[all]` | Full workstation | All supported Python capabilities with constructor auto-detection |

`slidecraft doctor` detects missing optional capabilities and explains the smallest installation command that enables each one.

Constructor selection follows a quality policy. The framework does not switch from PptxGenJS to the Python backend until parity tests pass for the routes used by the slide. A run report records the chosen backend and its capabilities.

Segmentation checkpoints should download through `slidecraft models install sam2-tiny` or on first approved use. Downloads are hashed, versioned, resumable, and stored in the platform-specific user data directory.

## Local-first data layout

Use `platformdirs` to select the correct operating-system locations. Avoid hard-coded home-directory paths.

```text
slidecraft-data/
  config/
    config.toml
    providers.toml
  libraries/
    visual_references/
    icons/
    components/
    styles/
  projects/
  models/
  cache/
  logs/
```

Users can override the data root through one documented environment variable or CLI option.

## Local configuration

Use TOML for human-authored configuration. Python includes a TOML reader, and the CLI can write validated files.

```toml
schema_version = "1.0.0"

[runtime]
mode = "local"
compute = "auto"

[libraries]
visual_references = "local:visual-references"
icons = "local:icons"
components = "local:components"
styles = "local:styles"

[providers.image_generation]
adapter = "host"
selection_policy = "prefer_host"
configured_adapter = "openai"
api_key_env = "OPENAI_API_KEY"

[segmentation]
enabled = "auto"
model = "sam2.1-hiera-tiny"
device = "auto"
remote_fallback = false

[reconstruction]
backend = "auto"
quality_policy = "highest_fidelity"
```

The CLI should provide `config show`, `config edit`, `config validate`, `config path`, and `config explain` commands. `config explain` shows the source and precedence of every resolved value.

## Local library commands

```text
slidecraft library visual-reference add reference.pptx
slidecraft library visual-reference index
slidecraft library icon add icon.svg --concept measurement
slidecraft library component create world-map
slidecraft library component validate world-map
slidecraft library component preview world-map
slidecraft library component test world-map
slidecraft library list
```

The local provider stores manifests and files in ordinary directories. A future remote provider implements the same Python protocol.

## Known component packages

A component is a versioned directory with a validated manifest and an editable implementation.

```text
world-map/
  component.json
  preview.png
  source.pptx
  examples/
    basic.json
  tests/
    expected.png
```

### Declarative PowerPoint fragment

This is the default format for user-defined components. `source.pptx` contains one editable component on one slide. Shapes use stable names such as `region_france`, `label_title`, and `legend_item_pattern`.

The manifest declares semantic recognition information, configurable parameters, bindings from parameters to named shapes, connection ports, resizing policy, and editable object types.

During reconstruction, the component importer performs these actions.

1. Copy the component's editable shapes and required media into the target package.
2. Remap relationship IDs and shape IDs.
3. Apply one proportional transform into the measured component region.
4. Bind parameters to named parts.
5. Apply deck typography and colors where the manifest permits it.
6. Restore z-order and connector ports.
7. Return created object IDs for the reconstruction report.

This format allows a user to create a component in PowerPoint without writing code.

### Primitive recipe

Simple reusable constructions can use a declarative recipe containing rectangles, circles, lines, textboxes, connectors, and groups. The recipe uses normalized coordinates from 0 to 1 and parameter bindings.

This format works well for KPI blocks, maturity scales, process chevrons, simple matrices, and callout patterns.

### Python factory plugin

Data-driven components can use an installed Python factory. Examples include maps with arbitrary highlighted regions, charts with special labelling logic, and components that generate a variable number of children.

Factories are discovered through Python package entry points. A local component directory cannot execute arbitrary Python by default. The user must explicitly install and trust a factory package.

```python
class ComponentFactory(Protocol):
    component_type: str

    def validate_parameters(self, values: dict) -> dict: ...
    def build(self, context: BuildContext, values: dict) -> BuiltComponent: ...
```

## Component recognition

Slide understanding does not search the component library using pixels alone. It forms a typed query from several signals.

- Semantic role
- Inferred purpose
- Required internal parts
- Relationship topology
- Text or data bindings
- Visual family
- Approximate aspect ratio
- Upstream component candidates

The local library first filters by roles and required parts. It then ranks candidates using keywords, optional embeddings, aspect compatibility, and VLM comparison of previews.

The result contains the selected candidate, alternatives, confidence, supporting evidence, and unresolved parameters.

Editable reconstruction uses the known-component route only when confidence exceeds policy and required parameters can be resolved. Otherwise it uses native primitives, fitted geometry, or raster fallback.

## Component manifest

The canonical machine schema is [`known_component.schema.json`](../../schemas/known_component.schema.json). The example component is [`world_map.component.json`](../../examples/local_library/components/world_map/world_map.component.json).

Important manifest sections include these fields.

- Stable ID, name, version, description, license, and provenance
- Semantic roles, concepts, aliases, and required parts
- Recognition signatures and confidence policy
- Implementation type and source
- Parameter definitions
- Bindings to named editable parts
- Connection ports
- Aspect, scaling, recoloring, and typography policies
- Preview and example inputs

## Plugin system

Use standard Python entry points.

```text
slidecraft.reasoning_providers
slidecraft.vision_providers
slidecraft.image_providers
slidecraft.segmentation_providers
slidecraft.library_providers
slidecraft.component_factories
slidecraft.renderers
```

Plugins install through pip and register themselves through package metadata. The core framework discovers them without importing unknown local files.

## Host-agent installation

The package can expose a local MCP server.

```text
slidecraft mcp serve
```

Codex or another agent host can call the slide pipeline through MCP tools while the Python process owns local files, libraries, OpenCV, segmentation, reconstruction, and the durable artifact ledger. The Agent owns workflow state.

The host Agent owns reasoning and visual understanding. Image generation remains the only configured model capability and can use the host or a configured external adapter.

## Automatic local compute

`slidecraft doctor` creates a capability record containing CPU, memory, MPS, CUDA, installed checkpoints, PowerPoint availability, and optional remote providers.

The runtime selects the lowest-complexity valid execution path.

```text
OpenCV measurement
  → local CPU

Selective segmentation
  → local MPS
  → local CUDA
  → local CPU when policy permits
  → configured remote provider
  → skip and record reduced capability

PowerPoint validation
  → explicitly authorized local Microsoft PowerPoint renderer
  → package-level validation when PowerPoint is unavailable
```

Permission-gated capabilities are setup-only. The framework never attempts to grant itself macOS Automation access and never launches a consent dialog during an ordinary run. `slidecraft authorize-powerpoint` performs the one explicit probe and records success. Later native renders require that record and have a hard timeout.

The user sees the selected path and any reduced-capability warning. Device details remain automatic unless advanced configuration overrides them.

## Open-source repository shape

```text
slidecraft/
  pyproject.toml
  src/slidecraft/
    cli/
    api/
    mcp/
    domain/
    workflows/
    agents/
    providers/
    libraries/
    cv/
    reconstruction/
    validation/
    storage/
  schemas/
  examples/
  tests/
  docs/
```

The package should include a small example library and test deck. Large checkpoints and substantial reference libraries remain external downloads.

## Migration from the current prototype

1. Add `pyproject.toml`, a `src/slidecraft` package, and a CLI entry point.
2. Move the current orchestration contracts into typed Pydantic models.
3. Wrap existing Python scripts as workflow activities.
4. Implement local-folder library providers.
5. Implement the component manifest loader and validator.
6. Implement declarative primitive recipes.
7. Implement editable PPTX fragment import.
8. Place JavaScript builders behind the constructor interface and build the Python backend under route-level parity tests.
9. Add capability discovery and `slidecraft doctor`.
10. Add the MCP server and optional REST API.

The first publishable release can support local CLI use, host-agent MCP use, local libraries, OpenCV, optional SAM 2, and direct PPTX reconstruction through the best available constructor backend. Distributed orchestration and remote libraries can follow without changing user-facing contracts.
