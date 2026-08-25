# Installation

The guided installer prepares Slidecraft in an isolated local runtime and installs the presentation skill for supported Agent hosts.

## Requirements

- Python 3.10 or newer
- The current Node.js LTS release

Node.js powers editable PowerPoint construction. The installer manages the required JavaScript presentation packages inside the application data folder.

## Guided installation

macOS and Linux

```bash
curl -fsSL https://raw.githubusercontent.com/henryhyw/slidecraft/v0.1.0-alpha.1/install.py | python3 -
```

Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/henryhyw/slidecraft/v0.1.0-alpha.1/install.py | py -3 -
```

The installer performs five operations.

1. Check Python, Node.js, and npm.
2. Create an isolated Slidecraft runtime.
3. Install document, computer vision, and image API support.
4. Prepare and verify the editable PowerPoint constructor.
5. Install the Slidecraft skill for detected Codex and Claude hosts.

The installed skill contains a generated `references/runtime.md` file with the exact local `slidecraft` command for reliable invocation.

The optional web app remains available through `slidecraft console`. It reads and edits the same local configuration and project files used by the Agent and CLI.

## Select an Agent host

Auto-detection is the default. You can choose hosts explicitly.

```bash
python3 install.py --agent codex --agent claude
```

Install only the runtime with this option.

```bash
python3 install.py --agent none
```

## Managed locations

| Platform | Managed installation |
| --- | --- |
| macOS | `~/Library/Application Support/Slidecraft/app` |
| Linux | `~/.local/share/slidecraft/app` |
| Windows | `%LOCALAPPDATA%\Slidecraft\app` |

The stable launchers are stored under the managed installation in `bin`.

## Install from a checkout

```bash
git clone https://github.com/henryhyw/slidecraft.git
cd slidecraft
python3 install.py --source .
```

Use `--dry-run` to inspect the installation plan first.

## Optional SAM support

OpenCV covers ordinary deterministic measurement. SAM is useful for selected irregular filled boundaries and adds a large PyTorch dependency.

```bash
"/path/to/Slidecraft/app/runtime/bin/python" -m pip install 'slidecraft-ai[segmentation]'
```

Use `Scripts\python.exe` inside the managed runtime on Windows.

## Troubleshooting

Run the readiness check at any time.

```bash
"/path/to/Slidecraft/app/bin/slidecraft" check-install
```

If Node.js is missing, install the current LTS release and rerun the installer. If an Agent host was installed later, rerun the installer so it can copy the skill and runtime reference.
