# SlidePoise

SlidePoise is a profile-driven presentation framework. The host Agent owns interpretation, design, image generation, semantic mapping, and every visual judgement. The framework supplies isolated guidance profiles, deterministic measurement, optional SAM evidence, editable PowerPoint reconstruction, a CLI installer, and an optional local console.

The stable Agent skill lives in [`slidepoise/`](slidepoise/). Configurable profiles live in [`profiles/`](profiles/). Shared icon and component families live in [`library-sets/`](library-sets/). They are installed separately under `~/.slidepoise`, so evolving a visual system never requires changing the stable skill.

Included profiles are `Consulting`, `Editorial Archive`, and `Monochrome Modern`.

## Install from GitHub

Install directly from GitHub with one command.

```bash
npx --yes github:henryhyw/slidecraft setup
```

## Install from a checkout

```bash
python -m venv .venv
.venv/bin/pip install -e '.[runtime]'
npm install
.venv/bin/slidepoise setup
```

The setup command detects Codex, installs the stable skill, copies profiles into the external framework home, prepares ordinary workspace and cache folders, and verifies Node dependencies. Existing Codex skill content is moved into the framework archive before replacement.

The Node entry point bootstraps an isolated Python runtime under `~/.slidepoise/python`, installs the framework with OpenCV support, installs Node reconstruction dependencies under `~/.slidepoise/node`, then installs the stable Codex skill and external profiles.

```bash
npx . setup
```

After `slidepoise` is published to npm, the shorter command will be `npx slidepoise setup`.

Use `npx . setup --skip-python` only when the active Python environment already contains the SlidePoise runtime dependencies.

You can also install it from a checkout with `pipx install '.[runtime]'` or `uv tool install '.[runtime]'`, followed by `slidepoise setup`. Python 3.10 or newer and Node.js/npm must already be available. Image generation is supplied by the host Agent platform. Setup does not install a local image model or LibreOffice. It attempts to install SAM and its pinned checkpoint inside the isolated SlidePoise Python environment. A failed SAM installation does not block setup or the complete OpenCV route. Use `--skip-sam` when the installation should be omitted.

## CLI

The GitHub installer keeps the working CLI inside SlidePoise's isolated Python environment. On macOS and Linux, use `~/.slidepoise/python/bin/slidepoise`. On Windows, use `%USERPROFILE%\.slidepoise\python\Scripts\slidepoise.exe`. A checkout or `pipx` installation also provides the shorter `slidepoise` command shown below.

```bash
slidepoise doctor
slidepoise profile list
slidepoise profile show personal-website
slidepoise profile select personal-website
slidepoise profile create "My Studio" --based-on personal-website
slidepoise profile add-resource my-studio visual_references reference.png --name "Editorial rhythm" --description "Asymmetric type and image treatment"
slidepoise library list
slidepoise library create icons "Research symbols"
slidepoise library add-resource research-symbols icon.svg --name "Research" --license "CC0"
slidepoise console
```

## Isolated profile structure

```text
profiles/<profile-id>/
  profile.json
  libraries/
    visual_references/catalog.json

library-sets/
  catalog.json
  icons/<set-id>/catalog.json
  components/<set-id>/catalog.json
```

Visual references belong to a profile because they define its point of view. Icons and components belong to coherent Library Sets because multiple profiles can share them without duplication. A profile selects complete sets. A run may temporarily override the captured selection.

Remix Icon and Wikimedia identity assets are remote Library Sets. The Agent inspects identity, visual fit, license terms, and provenance before selecting an asset. Retrieved files remain in the run cache.

Profiles are user-owned and can evolve through ordinary Agent conversation or the Console. The Agent can create a profile from the closest included starting point, translate the user's references and intent into guidance, and add an approved visual reference to the profile's private catalog. A run upload remains session-only until the user indicates that it should influence future work.

Profiles can specify a palette, typography, density, or icon treatment, express those values as guidance, or leave the decision to the Agent. Concrete fallback values remain available for reconstruction even when image generation has visual freedom.

## Installed layout

```text
~/.codex/skills/slidepoise/      stable Agent entrypoint and reconstruction runtime
~/.slidepoise/config.json        framework defaults and global provider switches
~/.slidepoise/profiles/          isolated guidance profiles and their libraries
~/.slidepoise/library-sets/      reusable icon and component families
~/.slidepoise/settings.json      active profile
~/.slidepoise/node/              PptxGenJS and Node runtime dependencies
~/.slidepoise/python/            npx-managed Python environment, when npx setup is used
~/.slidepoise/workspace/         slide runs and Console registry
~/.slidepoise/cache/             remote run assets and reusable runtime cache
~/.slidepoise/archive/           local recovery backups, created only when needed
```

The skill, config, and at least one profile are the working core. `settings.json` remembers the current profile. Python and Node dependencies are needed for measurement and PowerPoint construction, but their location depends on the installation route. A pip or uv installation uses its own Python environment and does not also need `~/.slidepoise/python/`. The workspace and cache hold generated local data.

`archive/` is not an installed component or a dependency. A clean installation does not create it. Updates create a backup only when replacing a changed skill, migrating a config, or retiring bundled profile files. Repeating setup with an identical skill does not create another copy. Backups never participate in generation and are excluded from the distribution. Remove a particular backup only when you no longer need it for recovery. The repository's historical `archive/` is separate and is never copied into a new installation.

### Upgrading from the former name

Default setup moves an existing `~/.slidecraft/` to `~/.slidepoise/` if the new directory does not exist. It leaves a compatibility symlink for historical absolute paths and virtualenv launchers. This is one data directory, not two installations. Historical prompts, run artifacts, reviews, and hashes are not rewritten. An existing `~/.codex/skills/slidecraft/` is archived when the new skill is installed, leaving only `~/.codex/skills/slidepoise/` discoverable. If both data directories already exist, setup stops instead of merging or overwriting them. Custom homes require an explicit `SLIDEPOISE_HOME` value.

### Optional SAM

SAM 2 supplies boundary masks for Agent-designated irregular filled objects, photo subjects, and overlapping filled objects. It receives each object's bounding-box prompt. OpenCV still collects color and geometry evidence. The mask can refine visible bounds and contours, subject to Agent visual review.

SAM does not plan the slide, retrieve assets, recognize text, assign semantic groups, route connectors, generate clean plates, remove covered text, or approve the reconstruction. The current adapter chooses one candidate mask using the model's predicted IoU score. That is a candidate-selection mechanism, not a visual acceptance decision.

The runtime mode is `auto`. Normal setup attempts a best-effort installation of the pinned dependencies and SAM 2.1 Tiny checkpoint. When that succeeds, eligible Agent-authored irregular objects use it automatically. When the machine or environment cannot install it, setup records the failure and the complete OpenCV route continues. `--skip-sam` omits the attempt. `never` disables an installed copy. `required` reports an error if an eligible object needs SAM and the model cannot run.

## Visual authority

Mechanical tools report machine-checkable facts and measurements only. They do not issue a stage verdict. The host Agent combines those facts with direct semantic and visual inspection. When subagents are available, bounded read-only reviewers independently inspect the plan, resources, semantic map, and final reconstruction. Ordinary checkpoints allow one review and one focused correction. Reconstruction receives the stricter review because the released PowerPoint cannot retain a material visual defect.

Every content slide still passes through host image generation and three explicit human approval gates covering the plan, selected resources, and generated image. Separate Agent visual reviews inspect generation, measurement, and reconstruction. Multi-Agent review strengthens reasoning and does not replace human approval.

Connector routes also require an Agent-authored visual route decision. The PowerPoint renderer emits each polyline as one continuous editable object to prevent gaps at bends.

## Session panel

```bash
slidepoise panel --run /absolute/path/to/presentation
slidepoise panel --id <panel_id> --view style
```

The Agent opens this panel beside the conversation. Its four stages are Plan, Style & Assets, Design & Analysis, and PowerPoint. The current activity stage opens by default, followed by the most recent populated stage when no work is active. Images, semantic interpretation, OpenCV overlays, reconstruction renders, and downloads refresh as their files change. A quiet step trail explains what the Agent is doing and why without inventing a percentage.

Style & Assets inherits one captured Profile. Edits made there become session overrides and never modify the shared Profile. User images, logos, source files, and selected references live in the same stage. Applying an edit writes a pending Agent event. For an explicitly bound running Codex task, SlidePoise also attempts immediate delivery through the local control connection. If that connection is unavailable or the task is idle, the event remains pending. The Agent checks for changes at every workflow boundary, after long tool calls, and before downstream writes. A host tool call already in progress cannot be interrupted by the browser, so the change is adopted at the first checkpoint after it returns. Agent edits refresh the Panel and Console automatically while protecting open editors.

Historical stage artifacts appear as versions. Viewing a version is read-only. Choosing it as the continuation point preserves current files, marks downstream work as earlier, and records a rollback event for the Agent.

Run `slidepoise panel` without a presentation to offer an initial selection. The command returns a conversation-local `panel_id`. Read the user's selection with `slidepoise panel --id <panel_id>`. Once selected, creating and switching presentations happens through the Agent. Use `slidepoise panel --id <panel_id> --run /absolute/new/path` after agreeing on a change. The browser follows that binding without a separate switcher. Older run-bound URLs remain supported.

Slide runs are session workspaces, not permanent project mirrors. A new run captures the current global and profile defaults, then keeps its own requirements, materials, settings, approvals, and outputs. Concurrent runs remain isolated. The Agent and Console read and write the same run files. Optimistic revisions prevent one window or Agent from silently overwriting a newer settings change. Missing or hidden runs leave the active list without deleting user files.

The standalone Console is available at `/console/` on the same local service. It manages the run registry, shared Profiles, Profile-owned references, Library Sets, and system capabilities. A Profile opens into its own workspace before any setting is edited. The Agent uses the same revisioned files and can perform the same changes through conversation.

```bash
slidepoise run create "Executive summary"
slidepoise run list
slidepoise run show /absolute/path/to/run
slidepoise run resolve /absolute/path/to/run
slidepoise run sync /absolute/path/to/run
slidepoise run activity /absolute/path/to/run --step generate_design --status running
slidepoise run events /absolute/path/to/run
slidepoise run ack-events /absolute/path/to/run --ids <event-id> --expected <revision>
```

## Validation

```bash
python slidepoise/scripts/preflight_config.py framework/defaults/slidepoise-config.json
python slidepoise/scripts/preflight_catalogs.py --profiles-root profiles
python slidepoise/scripts/audit_skill_boundaries.py
python -m pytest
node --test tests/console_interactions.test.mjs tests/panel_interactions.test.mjs
```
