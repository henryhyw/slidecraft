# Installation

The guided installer prepares Slidecraft in its own local runtime and connects supported agent apps found on the computer. It leaves the system Python environment unchanged.

## Before you start

Install these two supported runtimes once.

- Python 3.10 or newer from [python.org](https://www.python.org/downloads/)
- The current Node.js LTS release from [nodejs.org](https://nodejs.org/)

Node.js powers editable PowerPoint construction. Slidecraft installs and manages the JavaScript presentation packages inside its own application data folder.

## Guided installation

On macOS or Linux, run this command.

```bash
curl -fsSL https://raw.githubusercontent.com/henryhyw/slidecraft/v0.1.0-alpha.1/install.py | python3 -
```

On Windows PowerShell, run this command.

```powershell
irm https://raw.githubusercontent.com/henryhyw/slidecraft/v0.1.0-alpha.1/install.py | py -3 -
```

The installer completes five steps.

1. Check Python, Node.js, and npm.
2. Create an isolated Slidecraft runtime in the standard application data folder.
3. Install Slidecraft with document, computer vision, agent, and image API support.
4. Prepare the editable PowerPoint constructor and run the readiness gate.
5. Connect detected Codex and Claude Code installations. A Copilot workspace can be supplied explicitly.

It is safe to run the same command again. A repeated run refreshes the installed release, shared starter resources, and constructor packages while preserving healthy agent connections.

The installer never asks for an API key. Add an image-generation connection later from the dashboard if your agent app has no suitable image tool.

## Review the installer first

Download the installer when you want to inspect it before execution.

```bash
curl -fLO https://raw.githubusercontent.com/henryhyw/slidecraft/v0.1.0-alpha.1/install.py
python3 install.py --dry-run
python3 install.py
```

On Windows, download `install.py` from the same address, then run these commands.

```powershell
py -3 install.py --dry-run
py -3 install.py
```

## Choose agent apps

Auto-detection is the default. You can select hosts explicitly.

```bash
python3 install.py --agent codex --agent claude
```

To configure GitHub Copilot for the current user, select it explicitly.

```bash
python3 install.py --agent copilot
```

To keep the connection inside one workspace, supply that workspace folder.

```bash
python3 install.py --agent copilot --copilot-workspace /path/to/workspace
```

To install the runtime without changing any agent configuration, use this option.

```bash
python3 install.py --agent none
```

An existing healthy agent connection is preserved. If Slidecraft was moved to a different installation folder, refresh its registered command explicitly.

```bash
python3 install.py --refresh-agent-connections
```

Codex desktop, Codex CLI, and the Codex IDE extension share the same local MCP configuration. The installer uses the [official Codex MCP registration flow](https://learn.chatgpt.com/docs/extend/mcp#configure-with-the-cli).

## Open Slidecraft

The installer prints the exact dashboard and MCP commands for the new runtime. Their stable launchers live in the installation folder under `bin`.

Typical application locations are listed below.

| Platform | Managed installation |
|---|---|
| macOS | `~/Library/Application Support/Slidecraft/app` |
| Linux | `~/.local/share/slidecraft/app` |
| Windows | `%LOCALAPPDATA%\Slidecraft\app` |

Open the dashboard through the launcher printed at the end of installation. The agent connection uses the managed `slidecraft-mcp` executable directly, so the installation folder does not need to be added to `PATH`.

## Install from a cloned repository

Contributors and local source testers can point the same installer at the checkout.

```bash
git clone https://github.com/henryhyw/slidecraft.git
cd slidecraft
python3 install.py --source .
```

The manual virtual-environment workflow remains available in [Agent quickstart](AGENT_QUICKSTART.md).

## Optional SAM 2 support

The default installation uses OpenCV for ordinary deterministic measurements. SAM 2 is useful for selected irregular filled boundaries and adds a large PyTorch-based dependency. Install it into the managed runtime only when a project needs that capability.

```bash
"/path/to/Slidecraft/app/runtime/bin/python" -m pip install 'slidecraft-ai[segmentation]'
```

Use `Scripts\python.exe` in the managed runtime on Windows.

## Troubleshooting

Run the readiness gate at any time.

```bash
"/path/to/Slidecraft/app/bin/slidecraft" check-install
```

If the installer reports that Node.js is missing, install the current LTS release and run the installer again. If an agent app was installed after Slidecraft, run the installer again to connect it or register the printed MCP command in that app's local STDIO server settings.
