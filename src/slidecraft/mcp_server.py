"""MCP connection for Slidecraft agent integrations."""

from __future__ import annotations

from typing import Any

from slidecraft import __version__
from slidecraft.agent_workflows import (
    generate_slide,
    measure_slide,
    open_project,
    prepare_deck,
    reconstruct_slide,
    render_deck,
)

SERVER_INSTRUCTIONS = """
Slidecraft turns source material into editable PowerPoint presentations. Work through ordinary
conversation and use these tools as complete presentation tasks. Open the project first. Prepare
the agreed brief and Agent-authored deck plan. Generate each information-bearing slide, measure its
accepted image with Agent-authored visual analysis, reconstruct it, then render the complete deck.

The Agent reads every source and owns grounded fact extraction, relevance, authority, required use,
exclusions, evidence sufficiency, questions, storyline, resource choices, visual analysis, connector
meaning, reconstruction routes, and refinement decisions. Include those source decisions in the
brief with stable locators and provenance. Slidecraft never parses sources or decides whether the
material is sufficient. It stores Agent-authored decisions, performs deterministic measurement and
construction, and validates mechanical consistency. Tools may
return a brief or candidate set for the Agent to complete, then accept that authored result on the
next call. Return the editable PowerPoint or requested review artifact to the user. Keep internal
masks, contours, caches, and logs hidden unless technical evidence is requested.

For new work, place the project in the Agent's current workspace unless the user chose another
folder. Pass that workspace as `location` when calling `slidecraft_open_project`. Existing projects
can be reopened by name, stable ID, or folder.
""".strip()


def build_server() -> Any:
    try:
        from mcp.server import MCPServer
    except ImportError as exc:
        raise RuntimeError("MCP support is not installed. From the Slidecraft folder, run `python -m pip install '.[agent]'`.") from exc

    server = MCPServer(
        "Slidecraft",
        title="Slidecraft",
        description="Plan, generate, reconstruct, and validate editable PowerPoint presentations.",
        instructions=SERVER_INSTRUCTIONS,
        version=__version__,
    )

    @server.tool()
    def slidecraft_open_project(
        identifier: str,
        create_if_missing: bool = False,
        location: str | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Open or create a presentation project. New projects default to the current workspace."""
        return open_project(
            identifier=identifier,
            create_if_missing=create_if_missing,
            location=location,
            description=description,
        )

    @server.tool()
    def slidecraft_prepare_deck(
        project: str,
        brief: dict[str, Any] | None = None,
        deck_plan: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Store Agent-authored source evidence and the brief, return planning guidance, or validate the authored plan."""
        return prepare_deck(project=project, brief=brief, deck_plan=deck_plan)

    @server.tool()
    def slidecraft_generate_slide(
        project: str,
        slide_id: str,
        semantic_design: dict[str, Any] | None = None,
        resource_selection: dict[str, Any] | None = None,
        generated_image: str | None = None,
        host_supports_image_generation: bool = True,
    ) -> dict[str, Any]:
        """Prepare, generate, or register one planned content-slide image."""
        return generate_slide(
            project=project,
            slide_id=slide_id,
            semantic_design=semantic_design,
            resource_selection=resource_selection,
            generated_image=generated_image,
            host_supports_image_generation=host_supports_image_generation,
        )

    @server.tool()
    def slidecraft_measure_slide(
        project: str,
        slide_id: str,
        visual_analysis: dict[str, Any] | None = None,
        segmentation: str = "auto",
        checkpoint: str | None = None,
        device: str = "auto",
    ) -> dict[str, Any]:
        """Prepare visual-analysis guidance or measure an Agent-understood slide image."""
        return measure_slide(
            project=project,
            slide_id=slide_id,
            visual_analysis=visual_analysis,
            segmentation=segmentation,
            checkpoint=checkpoint,
            device=device,
        )

    @server.tool()
    def slidecraft_reconstruct_slide(
        project: str,
        slide_id: str,
        refinement_plan: dict[str, Any],
    ) -> dict[str, Any]:
        """Build one editable slide from measured evidence and Agent-authored refinement intent."""
        return reconstruct_slide(project=project, slide_id=slide_id, refinement_plan=refinement_plan)

    @server.tool()
    def slidecraft_render_deck(
        project: str,
        output: str | None = None,
        title: str = "Slidecraft presentation",
        company: str = "",
        language: str = "en-US",
    ) -> dict[str, Any]:
        """Validate every planned slide and export the complete editable PowerPoint deck."""
        return render_deck(project=project, output=output, title=title, company=company, language=language)

    return server


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
