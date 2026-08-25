# Agent integration

Slidecraft gives an AI Agent six tools for creating editable PowerPoint presentations. The person continues to work through ordinary conversation. The Agent handles interpretation and design decisions while Slidecraft manages files, measurements, construction, and validation.

## The six tools

| Tool | Purpose |
| --- | --- |
| `slidecraft_open_project` | Find or create a project and return its progress, sources, previews, and deliverables |
| `slidecraft_prepare_deck` | Record the agreed brief, provide planning guidance, and validate the Agent-authored deck plan |
| `slidecraft_generate_slide` | Prepare semantic design, present reusable-resource candidates, assemble the image brief, and register the generated image |
| `slidecraft_measure_slide` | Accept the Agent's visual analysis and measure exact slide geometry with OpenCV and optional SAM 2 |
| `slidecraft_reconstruct_slide` | Build editable PowerPoint objects from measured evidence and the Agent's refinement decisions |
| `slidecraft_render_deck` | Validate every planned slide and export the complete editable `.pptx` file |

Several tools support a short exchange. For example, `slidecraft_generate_slide` first returns semantic-design guidance. A later call with `semantic_design` returns resource candidates. A call with the selected resources returns the final image brief or uses the connected image service. This keeps reasoning with the Agent and keeps internal file operations out of the conversation.

## Automatic connection

The guided installer registers Slidecraft with detected Agent apps. Those apps start the local STDIO MCP server when its tools are needed. Users do not start a server for each project.

```bash
slidecraft-mcp
```

The command above is the registered server command. It is useful for manual MCP configuration and is normally invisible during everyday use.

If an Agent has shell access and the MCP connection is unavailable, it can import and call the matching functions in `slidecraft.agent_workflows`. The bundled skill teaches both routes. A user can therefore ask for a presentation in chat without knowing which route is active.

When the user asks to see the dashboard, the Agent can launch `slidecraft console`. The command starts the local webpage and opens it in the default browser. The dashboard is optional and reads the same projects and settings.

See [Agent quickstart](AGENT_QUICKSTART.md) for host-specific setup examples.

## A complete run

```text
slidecraft_open_project
        ↓
slidecraft_prepare_deck
        ↓
slidecraft_generate_slide × each information-bearing slide
        ↓
slidecraft_measure_slide × each generated slide
        ↓
slidecraft_reconstruct_slide × each generated slide
        ↓
slidecraft_render_deck
```

Cover pages, section dividers, and other low-information structural pages use the reusable layouts selected in the deck plan. They enter final assembly without image generation.

The Agent can stop after any completed operation. Reopening the project returns the saved progress and current deliverables. A new Agent session only needs the project name.

## What the Agent owns

The Agent owns every decision that requires judgment. This includes useful clarification questions, source interpretation, storyline, slide allocation, headers and footers, semantic design, reusable-resource choices, visual analysis, connector meaning, reconstruction routes, and refinement groups.

Slidecraft validates and executes those decisions. It manages provenance, candidate search, exact pixel measurement, bounded alignment, Office-safe text fitting, editable PowerPoint construction, and final deck checks.

## Image generation

When the Agent app has an image tool, `slidecraft_generate_slide` returns the assembled prompt, references, and canvas dimensions. The Agent generates the image and calls the same tool with `generated_image`.

When the Agent app has no image tool, Slidecraft uses the OpenAI or OpenAI-compatible image service configured in the dashboard. A user can also select that service as the required route.

## Python fallback

Agent runtimes that embed Python can call the same six workflows directly.

```python
from slidecraft import open_project, prepare_deck

project = open_project(identifier="Market Review", create_if_missing=True)
planning = prepare_deck(
    project=project["project"]["workspace_path"],
    brief={
        "objective": "Recommend a market entry strategy",
        "materials": [],
    },
)
```

For new work, `open_project` uses the current working folder when `location` is omitted. Pass an
explicit location when the user selected a different folder. Agent apps using MCP should pass their
current workspace as `location`, since the MCP process can have a different working directory.

The lower-level Python capabilities remain available to Slidecraft itself and to advanced integrations. They are intentionally absent from the MCP surface so an Agent sees a small and coherent tool set.

## Project visibility

People normally see `sources/` and `deliverables/`. Slidecraft stores prompts, measurements, revision records, and construction evidence under `.slidecraft/`. The dashboard presents the same project and resource information without controlling workflow progression.

The Agent should return the editable PowerPoint for final-deck requests. It can return plans, generated slides, previews, or decisions when the user asks to review progress. Masks, OCR fragments, contours, caches, and logs stay hidden unless technical evidence is requested.
