# SlidePoise project instructions

Read `slidepoise/SKILL.md` for every presentation task and follow the references it routes to. The skill directory is the product source of truth. Its packaged configuration, resources, scripts, schemas, and runtime must remain self-contained.

The host Agent owns visual and semantic judgement. Deterministic code may measure, validate, transform files, fit text, and construct PowerPoint objects. It must not replace visual review with a heuristic score or workflow state machine.

The browser console in `webapp/` is an optional management surface over the same skill and run folders. It may edit explicit session overrides, manage resources and uploads, show artifacts, and record a user's approval action. It does not plan a slide, select resources, generate images, create semantic maps, or decide whether a visual result is acceptable.

SAM is an optional measurement enhancement. Keep OpenCV as the complete default measurement route. Load SAM only for host-authored eligible irregular objects, only when the configured checkpoint and optional dependencies are available, and record whether its mask contributed. SAM never decides semantic ownership or visual acceptance.

For changes to the skill itself, also read `slidepoise/references/maintenance.md`. Preserve the three hard approval gates and run the packaged validators before release.
