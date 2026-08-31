# Session panel

The browser surface accompanies the current Agent conversation. Its four top tabs are Plan, Style & Assets, Design & Analysis, and PowerPoint. They present the current run and its evolving artifacts. Shared Profile, Library Set, and project management belong to the standalone Console.

## Open the correct session

1. When the user has chosen a presentation, create or attach its run using `slidepoise run`. For a new presentation, use a dedicated folder in the current working directory unless the user specifies another location. Preserve its absolute path throughout this conversation.
2. Run `slidepoise panel --run /absolute/run/path`. It starts or reuses a local server and returns a panel URL and `panel_id`. Preserve both. If the user has not chosen a presentation yet, run `slidepoise panel` without a run. That initial panel lists available presentations. Discuss whether to continue one or start a new presentation in the conversation.
3. Open the returned URL beside the conversation using the host browser-panel capability. In Codex desktop, discover `open_in_codex` and use a browser target with right placement when available.
4. Read `slidepoise panel --id <panel_id>` after the user's initial selection and before acting on a run. Its `run` field is the shared selection. An omitted `--run` preserves that selection. Once selected, the browser offers no create, switch or folder-location control. Create and switch presentations through conversation only. After the user requests a change, run `slidepoise panel --id <panel_id> --run /absolute/new/run`. The open panel follows that binding automatically. Never guess the active run or store a global current run. Separate conversations have separate panel IDs.
5. At each resumed slide-work turn and before presenting a review gate, check whether the matching panel remains available. Reopen it if closed. The Agent cannot reopen a host tab while it is not running. Do not promise a background host-window watcher.

Use `--view plan`, `--view style`, `--view design`, or `--view powerpoint` to open the relevant stage directly. The URL hash preserves the stage when the user browses, and normal workflow updates do not pull them away from a stage they chose manually.

If the host has no embedded panel capability, provide the same URL and continue in conversation. Never make panel availability a prerequisite for slide creation.

## Present actual artifacts

The panel reads the canonical plan, session style, user assets, selected resource pool, generated design, semantic and measurement artifacts, reconstruction render, and deliverables from the run. Save artifacts as each handoff is prepared. The display refreshes automatically and selects the current or latest populated stage on first open. It does not infer completion or acceptance from file presence.

Plan displays the complete information contract using the structure authored for that slide. Show semantic relationships, hierarchy, required content, evidence obligations, exclusions and open questions when present. Do not reduce the plan to a generic sequence or assign numbers unless the intent explicitly defines a sequence.

Style & Assets shows the captured Profile and session controls first. After retrieval, it also shows the combined style and asset context sheet used at the second approval gate. The user confirms the visual direction, creative-freedom boundaries and material pool together before generation.

Publish `work/activity.json` through `slidepoise run activity` whenever a meaningful step starts, completes, pauses, fails, or waits for the user. The Panel shows the current step, its user-facing purpose, and a restrained stage trail. It never shows a fabricated percentage. While work is running, use a three-dot vertical bob with staggered timing. Waiting and failed states remain still. Respect reduced-motion preferences.

At the start of every turn, every core-pipeline boundary, after a long tool call returns, and before writing downstream artifacts, run `slidepoise run sync <run>`. This returns pending changes, current overrides and requirements, activity, version selections and revisions. Acknowledge a change after adopting it. Browser displays poll shared files without overwriting open editors.

When opened from Codex with `CODEX_THREAD_ID`, the panel binding records that explicit task identity. Applied changes attempt delivery through `codex app-server proxy` and `turn/steer` to an already-running turn. The bridge never starts a daemon, resumes a task or creates a turn. If the control socket is unavailable or the task is idle, the event remains pending for the next checkpoint. Delivery is separate from acknowledgement. Do not claim immediate delivery without a delivered record, or interruption of an indivisible tool call. These host operations follow the [Codex App Server protocol](https://learn.chatgpt.com/docs/app-server).

Use the conversation to explain the important decision and point to the corresponding panel section. Images can be enlarged. Keep essential summaries and approval questions in the conversation so the user can still work without the panel.

## Conversation and Panel handoff

The Panel is a shared working surface. Use it to make a concrete result visible while the conversation carries intent, judgement, and approval.

Apply `user-language.md` to every Agent-authored field that the Panel can display, including intent summaries, resource reasons, activity messages, semantic display labels, review purposes, and short status copy. Panel files may retain complete technical evidence, while the default surface shows reader-facing labels and explanations. Never treat raw Agent prose as ready for display without reviewing it in context.

When a user requests a change, first infer its scope from the conversation and active run.

- Use Plan for the message, audience, required ideas, evidence, relationships, and hierarchy.
- Use Style & Assets for current-presentation color, typography, density, treatment, selected libraries, uploads, references, and other session overrides.
- Use Design & Analysis for the candidate composition and the user-facing evidence behind its interpretation and measurement.
- Use PowerPoint for the editable file, current render, visual comparison, and final review evidence.
- Use the Console Profile workspace for reusable guidance and Profile-owned visual references.
- Use the Console Resources workspace for reusable icon and component sets.

If the request is clear, carry it out first, synchronize the run, and then open the affected stage so the user can inspect the result. If a choice is ambiguous or materially changes the direction, open the relevant stage and ask one focused question. Do not require the user to hunt through controls, repeat a value already visible in the active run, or operate the Panel before the Agent can proceed.

When the user changes a Panel control, treat its pending event as user input. Adopt it at the next checkpoint, explain its impact only when useful, refresh any affected downstream artifact, and acknowledge the event after adoption. When the Agent changes a value or artifact, write it through the canonical session APIs or files so the Panel refreshes from the same state. Never maintain a second private copy of Panel settings.

Guide users with the result and location together. For example, say that the session palette has been updated and that Style & Assets now shows the exact colors. Avoid empty directions such as asking them to go to the Panel without saying what changed or what to inspect.

Keep this handoff adaptive. Choose whether to act, show, or ask based on ambiguity, consequence, and the applicable human gate. Derive copy and destinations from the active run. Do not encode a fixed Profile, palette, layout, asset count, filename, or project-specific sequence into the Panel or the Agent's instructions.

The panel can render an updated local PPTX through the installed renderer. If no renderer is available, show that limitation and retain the downloadable PPTX. This rendering action supplies an image for inspection and does not approve it.

For a short user-facing status, optionally maintain `work/panel.json` with the structure in `schemas/panel.example.json`. This is an Agent-authored presentation record. It is not an execution state machine or a replacement for approval records. Keep prose factual and concise. Avoid ceremonial status messages or invented progress metrics.

The default surface uses one row of tabs and the presentation's actual title and content. Avoid a branding row, companion taglines, repeated explanations of conversation isolation, technical folder controls, raw review notes, and internal handoff language. A short instruction is appropriate for an empty state, a real error, or a choice with consequences. Keep detailed technical evidence behind Developer details.

Design & Analysis keeps the generated image primary and places generation context, semantic groups, relationships, prompts, OpenCV measurement overlays, optional SAM contribution, and reasoning reviews in user-facing disclosure sections. Each section explains why it matters. Raw evidence stays one level deeper. PowerPoint refreshes its render while reconstruction changes and shows construction and final-review evidence in the same way. Use meaningful group names and relationship descriptions. Do not fill the default view with raw IDs, debug labels or JSON.

## Session editing and versions

Style & Assets shows the captured Profile as the parent system. Every control below it writes only a session override. Applying a change or adding an asset records a pending item in `work/panel-events.json`. Read these events before continuing Agent work and acknowledge them only after they have influenced the plan or downstream strategy.

The panel may show current and historical versions for a stage. Selecting an older version is read-only. Choosing Use this version records a pending rollback event and marks downstream stages as earlier work. It never changes approval status.

Before replacing existing work, run `slidepoise run archive <run>`. This preserves current work, deliverables, uploads and the accepted image under a new history version. Read the requested version, adapt the work and reset affected human gates as described in `human-approval.md`. New primary artifacts become visible as the current stage while unchanged downstream work remains marked earlier. Use `slidepoise run publish <run> --stage <plan|style|design|powerpoint> --expected <selection_revision>` after writing a new stage, including when the resulting files are unchanged. Obtain the revision from `run sync`. Publishing changes display selection only and cannot approve a stage. Preserve `accepted-slide.png` while showing a newer candidate for review.

The standalone Console maintains shared Profiles, Profile-owned visual references, Library Sets, system capabilities, and the run registry. Opening a Profile enters its own workspace before any setting is edited. Agent and Console use the same revisioned files.

The Console is a display and editing surface. The host Agent still owns planning, retrieval, resource selection, generation, interpretation and visual review. All three human approval gates remain unchanged.
