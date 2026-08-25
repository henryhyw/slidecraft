"""Optional MCP adapter for agent-native Slidecraft installations."""

from __future__ import annotations

from typing import Any

from slidecraft import __version__
from slidecraft.agent import list_capabilities, safe_call_capability

SERVER_INSTRUCTIONS = """
Slidecraft creates and revises editable PowerPoint presentations through durable local projects.
The host Agent owns conversation, judgment, session progression, and use of native reasoning,
vision, and image-generation tools. Slidecraft owns typed artifacts, provenance, reconstruction,
validation, and resumability.

When a user names an existing project, call slidecraft_resolve_project and then
slidecraft_workflow_status. Create a missing project only when the user intends new work. For a
new presentation, record the agreed brief with slidecraft_set_deck_brief. After every material
operation, call slidecraft_workflow_status and continue with its highest-priority valid action
until the requested result is ready or the user asks to stop. Register every external model
result before another capability consumes it. Use slidecraft_project_detail to return final
PowerPoint files or reviewable intermediate work. Keep internal masks, contours, OCR fragments,
caches, and logs hidden unless the user asks for technical evidence.

Call slidecraft_capabilities when an operation or its arguments are unknown. Use slidecraft_call
for capabilities that do not have a dedicated MCP tool.
""".strip()


def build_server() -> Any:
    try:
        from mcp.server import MCPServer
    except ImportError as exc:
        raise RuntimeError("Install Slidecraft with the agent extra: pip install 'slidecraft-ai[agent]'") from exc

    server = MCPServer(
        "Slidecraft",
        title="Slidecraft",
        description="Agent-native editable PowerPoint planning, generation, reconstruction, and validation.",
        instructions=SERVER_INSTRUCTIONS,
        version=__version__,
    )

    @server.tool()
    def slidecraft_capabilities() -> dict[str, Any]:
        """Discover Slidecraft operations before choosing the next pipeline action."""
        return list_capabilities()

    @server.tool()
    def slidecraft_create_workspace(workspace: str, deck_id: str | None = None) -> dict[str, Any]:
        """Create or reopen a durable local deck workspace."""
        return safe_call_capability("create_workspace", {"workspace": workspace, "deck_id": deck_id})

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
    def slidecraft_inspect_workspace(workspace: str, include_history: bool = False) -> dict[str, Any]:
        """Inspect current artifacts, candidates, freshness, validation, and history."""
        return safe_call_capability("inspect_workspace", {"workspace": workspace, "include_history": include_history})

    @server.tool()
    def slidecraft_workflow_status(workspace: str, include_history: bool = False) -> dict[str, Any]:
        """Return exact resumable next actions for the current deck workspace."""
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
