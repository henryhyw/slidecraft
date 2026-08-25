# Configuration

Slidecraft resolves configuration once at the start of a run. Every resolved value has recorded provenance.

## Precedence

Values are applied in this order.

1. Packaged defaults
2. User configuration
3. Project configuration
4. Documented environment overrides
5. Explicit command arguments for the current operation

The default user configuration path is platform-specific. Run these commands to inspect it.

```bash
slidecraft config path
slidecraft config show
slidecraft config validate
slidecraft config explain
slidecraft config set providers.image_generation.selection_policy force_configured
slidecraft config set reconstruction.backend pptxgenjs --scope project --project ./slidecraft.toml
slidecraft config unset reconstruction.backend --scope project --project ./slidecraft.toml
```

`slidecraft config explain` prints the resolved value and source for every setting. Set `SLIDECRAFT_CONFIG` to choose another user configuration file. Set `SLIDECRAFT_DATA_DIR` to relocate local libraries, models, cache, projects, and logs.

`config set` changes a persistent overlay. User scope applies across projects. Project scope applies only when that project configuration is supplied. `config unset` removes the overlay and reveals the next value in the precedence chain. These commands use dotted keys and JSON-typed values.

## Long-lived configuration

The user or organization configuration owns these values.

- Image-generation connection, model, and selection policy
- Model IDs and credential environment-variable names
- Local visual-reference, icon, component, and style libraries
- Icon search scope, with local-only or local plus official Tabler retrieval
- Segmentation policy, checkpoint, and device selection
- Constructor backend and quality policy
- Validation policy
- Non-interactive runtime behavior

Deck design files own slide dimensions, title treatment, typography, colors, density, deck chrome geometry, icon slots, connector style, and normalization thresholds.

## Per-project and per-slide input

Project requests own the objective, audience, source materials, constraints, assets, desired deck length, and guidance profile. Per-slide jobs own exact content, slide objective, semantic relationships, mandatory assets, and proposed header or footer content.

Deck length is run-specific. It has no packaged default. When the user supplies a preferred slide count, the planner is required to stay inside the requested range. `slidecraft plan-deck --slide-count 12` converts the value to an exact minimum, target, and maximum for that run. Without a supplied count, the planner proposes the smallest credible length from evidence volume, density, storyline needs, and structural pages.

Commands that prepare or plan a run accept repeatable `--set KEY=VALUE` overrides. They are recorded in run artifacts and never modify persistent files. For example:

```bash
slidecraft plan-deck --request request.json --design design.json --run-dir runs/demo --slide-count 12 --set density_profile=high_consulting
slidecraft prepare-generation --design design.json --slide slide.json --output-dir runs/demo/slide_01 --resource-candidates candidates.json --resource-selection selection.json --set style.density=high
```

An agent in chat uses the same interface. Phrases such as "use 12 slides this time" become runtime overrides. Phrases such as "make medium density my default" require an explicit persistent intent and become `slidecraft config set` operations. The agent should report the scope and file it changed.

## Manual configuration locations

Run `slidecraft config path` to obtain the exact user file and data-library root for the current operating system. A project can keep a small `slidecraft.toml` overlay beside its request files and pass it through `--project`. Deck design JSON files remain explicit design-system snapshots so each run stays reproducible. Run artifacts store the resolved snapshot and runtime overrides.

Secrets are never stored in deck or slide artifacts. Provider records name an environment variable such as `OPENAI_API_KEY`.

## Local control console

Run `slidecraft console` to open the local dashboard. It shows project history and deliverables, presentation design defaults, reusable resource collections, image connections, and runtime health. The dashboard opens locally at `127.0.0.1`.

The console is a user control surface. Its primary views are Overview, Projects, Design, and System. Overview summarizes active work and completed editable presentations. A project shows its current milestone, source materials, visual assets, retrieved resources, and user-facing outputs. Design exposes one combined communication design control for communication approach and information density, plus typography, color and icon treatment, and three reusable resource collections. System exposes automatic runtime health and the image-generation connection a user can change. Internal capability catalogs and raw engineering configuration stay out of the interface. A change made in chat and a change made in the console both flow through the same validated operations.

## Project folders

`create_project` accepts a user-selected absolute location. When no location is supplied, Slidecraft creates a managed folder under the configured data root. Project resources are grouped inside the project workspace.

- Materials include documents, data, images, user statements, constraints, clarification answers, and extracted source atoms.
- Visual assets include logos, photographs, and other canonical files that can appear directly in the PowerPoint.
- Visual inspiration includes retrieved whole-slide precedents used only as guidance.
- Icons include retrieved canonical pictograms.
- Components include retrieved reusable editable constructions.

The resource catalog is a derived project view. It preserves provenance and reports the slide IDs that cite each source atom or canonical resource. Long-lived visual, icon, component, and style libraries remain global. Items retrieved from those libraries become project-specific selected resources.

### Icon search scope

`resources.icons.allow_online_retrieval` is enabled by default. When enabled, an Agent request for icon candidates searches the configured local collection and the official Tabler Icons outline collection. Matching SVG candidates are downloaded into the local collection with their release and source provenance. The Agent evaluates those candidates in slide context and records the final choice.

When the option is disabled, icon discovery remains inside the local collection. The Resources screen exposes this setting as **Find icons online**. The same value can be changed in the user configuration file or through a runtime configuration override.

A project has three filesystem visibility layers.

- `assets/` contains project-specific visuals that may appear directly in slides.
- `materials/` contains briefs, documents, data, notes, and other working sources with provenance.
- `deliverables/` contains editable slide files, combined PPTX files, previews, reports, and other user-facing outputs.
- `.slidecraft/` contains prompts, semantic plans, measurements, masks, revision history, logs, and the artifact graph. It is hidden by default and remains available to the Agent.

The local project registry keeps the project path and recent status. If a user deletes or moves the folder, the registry reports it as unavailable and does not recreate or overwrite it.

## Provider modes

Reasoning and visual understanding come from Codex or another Agent host. Image generation has two selection policies. `prefer_host` uses the Agent image tool when it is available, then falls back to the configured API connection. `force_configured` always uses that connection. `openai` uses the configured OpenAI endpoint. `custom-openai-compatible` uses a compatible base URL. The Agent can resolve this policy through `resolve_image_generation_route` before generating a slide.

Setup stores credentials in the operating system keychain and reports any required installation or permission in the System page. Each run records which local capabilities it used.
