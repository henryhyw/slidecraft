# Configuration

Slidecraft resolves settings from five layers.

1. Packaged defaults
2. User configuration
3. Project configuration
4. Documented environment overrides
5. Explicit command arguments

Use these commands to inspect and edit settings.

```bash
slidecraft config path
slidecraft config show
slidecraft config validate
slidecraft config explain
slidecraft config set design.display_font Aptos
slidecraft config set design.density_profile medium --scope project --project /absolute/path/project/.slidecraft/config.toml
```

User settings apply across presentations. Project settings in `.slidecraft/config.toml` refine those defaults for one deck. The web app writes through the same configuration resolver.

## Presentation design

The `design` settings control the communication profile, information density, display and body fonts, palette, text color, surface color, and icon treatment. `.slidecraft/deck_design.json` supplies the fuller construction system, including canvas geometry, title treatment, deck chrome, text roles, icon slots, connector style, and refinement limits.

Each reconstruction writes `resolved_deck_design.json` beside its working artifacts. This snapshot records the effective design used for that slide.

## Resources

Global collections hold visual inspiration, canonical icons, reusable components, and styles. A project records the resources selected for its deck. `slidecraft project context` returns the current materials, visual assets, selections, and library availability.

The project folder uses these locations.

- `materials/` for briefs, documents, data, and notes
- `assets/` for project visuals such as logos, screenshots, photographs, and illustrations
- `deliverables/` for editable slides, assembled decks, previews, and reports
- `.slidecraft/` for shared settings, working artifacts, resource records, and history

## Image generation

The `providers.image_generation` settings select the Agent-hosted image tool or a configured OpenAI-compatible connection. Credentials are stored through the operating system keychain. The web app presents the active connection and model.

## Computer vision and construction

The `segmentation` settings control SAM availability, checkpoint, and device. OpenCV remains the standard measurement path. The `reconstruction` settings select the PowerPoint constructor and package policy.

Run `slidecraft project context /absolute/path/project` before planning and after web-app changes to retrieve the complete effective configuration used by downstream slide work.
