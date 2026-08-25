"""MCP connection for Slidecraft agent integrations."""

from __future__ import annotations

from typing import Any

from slidecraft import __version__
from slidecraft.agent import list_capabilities, safe_call_capability

SERVER_INSTRUCTIONS = """
Slidecraft creates and revises editable PowerPoint presentations through local project folders.
The agent app interprets the conversation and chooses each action. Slidecraft organizes sources,
decisions, generated work, editable reconstruction, validation, and deliverables.

When a user names a project, call slidecraft_resolve_project and then slidecraft_workflow_status.
Create the project when they are starting new work. Record a new presentation brief with
slidecraft_set_deck_brief. The host agent owns clarifications, planning, retrieval choices, semantic
mapping, reconstruction routes, connector intent, and refinement decisions. Slidecraft supplies
search evidence, typed storage, deterministic processing, validation, and PowerPoint construction.
Use slidecraft_workflow_status to inspect durable facts. Choose the next operation through your own
reasoning over those facts and the user's current request. Register model results before using them
in later operations. Use slidecraft_project_detail to return the final PowerPoint, previews, plans,
or reports requested by the user. Technical reconstruction evidence is available on request.

Call slidecraft_capabilities when an operation or its arguments are unknown. Use slidecraft_call
for capabilities that do not have a dedicated MCP tool.
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
    def slidecraft_capabilities(
        workflow: str | None = None,
        capability: str | None = None,
    ) -> dict[str, Any]:
        """Show compact workflows, expand one workflow, or inspect one capability."""
        return list_capabilities(workflow=workflow, capability=capability)

    @server.tool()
    def slidecraft_resolve_project(
        identifier: str,
        create_if_missing: bool = False,
        location: str | None = None,
    ) -> dict[str, Any]:
        """Find a Slidecraft project by name, ID, or folder. Create it only when the user intends new work."""
        return safe_call_capability(
            "resolve_project",
            {
                "identifier": identifier,
                "create_if_missing": create_if_missing,
                "location": location,
            },
        )

    @server.tool()
    def slidecraft_project_detail(location: str, include_internal: bool = False) -> dict[str, Any]:
        """Return user-facing project progress, sources, deliverables, and reviewable intermediate artifacts."""
        return safe_call_capability(
            "project_detail",
            {"location": location, "include_internal": include_internal},
        )

    @server.tool()
    def slidecraft_set_deck_brief(workspace: str, brief: dict[str, Any]) -> dict[str, Any]:
        """Create or revise the authoritative presentation brief from the Agent conversation."""
        return safe_call_capability("set_deck_brief", {"workspace": workspace, "brief": brief})

    @server.tool()
    def slidecraft_workflow_status(workspace: str, include_history: bool = False) -> dict[str, Any]:
        """Show durable project facts and artifacts for Agent interpretation."""
        return safe_call_capability("workflow_status", {"workspace": workspace, "include_history": include_history})

    @server.tool()
    def slidecraft_call(capability: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call one discovered Slidecraft capability with its typed argument object."""
        return safe_call_capability(capability, arguments)

    return server


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
