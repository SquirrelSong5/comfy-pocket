# Comfy Pocket

**Run your existing ComfyUI apps from a lightweight, mobile-friendly interface.**

[简体中文](README.md) · [Quick start](#quick-start) · [Phone access](#phone-and-lan-access) · [Compatibility](#compatibility)

Comfy Pocket is an independent Web client for your own ComfyUI backend. It targets people who already build workflows and want to run them comfortably from a phone or another computer, without loading the full node editor.

It does not include models, replace the inference backend, or edit node graphs.



## Features

- **Dynamic apps:** discovers saved official `.app.json` files and generates forms from exposed inputs and backend node schemas. New apps do not require frontend code changes.
- **Mobile execution:** text, numbers, enums, switches, image uploads, queue status, cancellation, history, and downloads.
- **Optional image groups:** data-driven counts and empty slots when the underlying workflow supports lazy optional branches.
- **Live progress:** official node/step events; no fabricated whole-job percentage.
- **Text results:** displays `ui.text`, including actual/enhanced prompts when the workflow exposes them.
- **Smaller previews:** cached WebP images, at most 1280 px on the longest edge. Original results remain available separately and are never rewritten.
- **Optional local process controls:** manually start, stop, or restart one shared ComfyUI process from the page.
- **Private access:** remote access codes, Host/network/Origin checks, and Tailscale-compatible networking.

## Quick start

### Prerequisites

1. Node.js **22.12+**, including npm/npx.
2. Python **3.10+** with `venv` and `pip`. You can point to a suitable existing ComfyUI virtual environment.
3. Your own ComfyUI installation, models, custom nodes, and saved apps.

Tested locally on Windows 11 / Python 3.13. CI targets Windows and Linux. macOS, all portable bundles, and older ComfyUI releases have not received complete device testing.

### Option 1: one command

```bash
npx --yes github:SquirrelSong5/comfy-pocket#v0.1.0
```

On first run, npm downloads the project and builds the frontend automatically. The launcher asks for a ComfyUI directory/URL, creates an isolated Python environment for Pocket, installs its small backend dependencies, and opens the browser. Subsequent runs reuse your configuration and Python environment.

Leave the ComfyUI directory blank to connect to an already running backend without local process controls. To enable controls, select the directory containing `main.py`; the launcher searches common `.venv`, `venv`, and `env` environments.

Initial setup needs GitHub, npm, and PyPI access. It does not install models/CUDA or change ComfyUI's environment. GitHub-based npm installs may require Git; use the release package below to skip source checkout and frontend compilation.

> This project is distributed through GitHub and is **not currently published to the npm registry**. Plain `npx comfy-pocket` is not a verified command for this project. Use the GitHub-qualified command.

### Option 2: prebuilt package

```bash
npx --yes --package=https://github.com/SquirrelSong5/comfy-pocket/releases/download/v0.1.0/comfy-pocket-0.1.0.tgz comfy-pocket
```

The archive includes the compiled frontend. It still needs to create the Python environment on first use. Alternatively, download the `.tgz` from [Releases](https://github.com/SquirrelSong5/comfy-pocket/releases), extract it, and run `node cli/index.mjs` in the package directory.

### Non-interactive setup

```powershell
npx --yes github:SquirrelSong5/comfy-pocket#v0.1.0 --comfy-dir "D:\AI\ComfyUI" --python "D:\AI\ComfyUI\.venv\Scripts\python.exe"
```

Connect-only mode:

```bash
npx --yes github:SquirrelSong5/comfy-pocket#v0.1.0 --comfy-url http://127.0.0.1:8188
```

`--python` takes an executable, not a BAT launcher. Embedded Python bundles may lack `venv`; use standard Python to install Pocket, then separately set `runtime.executable` to the Python environment that contains ComfyUI's inference dependencies.

### Source checkout / Windows double-click

```bash
git clone https://github.com/SquirrelSong5/comfy-pocket.git
cd comfy-pocket
npm install
node cli/index.mjs
```

After initial setup, Windows users can double-click **`Start Comfy Pocket.cmd`**. A development checkout with a private root `config.json` uses the background PowerShell launcher; otherwise the command starts the CLI wizard.

The CLI runs in the foreground. Keep its terminal open; `Ctrl+C` stops Pocket, not ComfyUI. This release does not silently install a system service or login task. Configure OS startup yourself if desired.

## First run

1. Build and test a workflow in official ComfyUI.
2. Use its app builder to expose the daily inputs and outputs, then save an `.app.json`.
3. Open Pocket and synchronize official apps. A regular workflow `.json` is not automatically treated as an app.
4. Select an app, enter parameters, upload images, and generate.
5. View live node progress, text results, and image previews; open/download the original when needed.

A suggested filename is `Model name · Purpose.app.json`. Personal workflows and models are not bundled in this repository.

## Phone and LAN access

Default binding is **127.0.0.1:8189 only**. To enable another interface during initial setup:

```bash
npx --yes github:SquirrelSong5/comfy-pocket#v0.1.0 --host 100.80.20.10 --host 192.168.1.20
```

Replace these example addresses with actual Tailscale/LAN IPv4 addresses assigned to the computer. The phone must share the tailnet or LAN. Visit `http://COMPUTER_ADDRESS:8189`.

Remote access requires a code. On the computer, visit `http://127.0.0.1:8189` and open **Phone access / 手机访问** in the sidebar. Do not publish the code.

Existing configurations are never silently overwritten by CLI flags. Edit `bind`, `hosts`, and `networks` in `~/.comfy-pocket/config.json`, then restart Pocket. Generated LAN rules allow the corresponding /24; Tailscale uses `100.64.0.0/10`. You may narrow those ranges manually.

Pocket does not install Tailscale, create public tunnels, or modify the firewall. If needed, allow the configured port from the intended private networks. The computer must be on and awake.

## Configuration, data, upgrades

Default data directory: **`~/.comfy-pocket/`**, typically `%USERPROFILE%\.comfy-pocket` on Windows.

```text
~/.comfy-pocket/
├── config.json       # Private machine configuration
├── .venv/            # Pocket's isolated Python environment
└── state/
    ├── access.json   # Access code/session signing secret: do not share
    ├── jobs.json     # Jobs submitted through Pocket
    ├── uploads.json  # Upload identifiers
    ├── previews/     # Regenerable image preview cache
    └── comfyui.log   # ComfyUI process output
```

See [config.example.json](config.example.json). Running `python -m backend.server` directly uses the checkout's private config unless `COMFY_POCKET_HOME` points elsewhere. CLI data lives outside temporary npx caches.

| Option | Purpose |
| --- | --- |
| `--home DIR` | Independent persistent data/config directory |
| `--python FILE` | Bootstrap Python; also ComfyUI Python for local controls |
| `--comfy-dir DIR` | Local directory containing main.py |
| `--comfy-url URL` | Backend HTTP(S) origin; defaults to localhost:8188 |
| `--port PORT` | Pocket port, default 8189 |
| `--host IPv4` | Additional concrete address; repeatable; no wildcard |
| `--no-open` | Do not open a browser |
| `--setup-only` | Install/configure and exit |
| `--help` | Show help |

To upgrade, use a newer tag or release URL with the same data directory. To uninstall, stop Pocket and remove its data directory after backing up anything you need. This does not remove ComfyUI or its original generated files.

## Process management

One ComfyUI process serves all apps. Selecting another workflow does not start another process. Model loading/unloading is handled by ComfyUI and is separate from process startup.

Controls remain **manual**, with visible startup/running/stopped/error state. The optional `runtime` section defines `cwd`, `executable`, and `args`. The browser cannot supply arbitrary commands. Only a local process whose full command matches that configuration can be controlled; externally started instances with different arguments are not adopted. Remote backend URLs cannot be used to control processes on another machine.

Running or queued jobs block stop/restart. Inspect the local log when startup fails. Starting Pocket does not automatically start ComfyUI.

## Compatibility

| Feature | Scope |
| --- | --- |
| Official `.app.json` with `extra.linearData` | Dynamic input/output discovery |
| STRING / INT / FLOAT / BOOLEAN / enums | Schema-generated controls |
| Ordinary backend nodes, Reroute, some bypass nodes | Within current adapter support |
| Image uploads; image/video/audio results | Supported; video uses Range requests |
| `ui.text` | Live and persisted text output |
| Frontend-only JS nodes, nested subgraphs, special widgets | Not universally supported; conversion errors are displayed |
| Dynamic-combo branch selection | Prefer fixing branches in the official UI |
| Complete official job history | Not imported; Pocket jobs only |
| User accounts, per-user isolation, roles | Not supported; shared studio/access code |

The official app serialization can change upstream. Functional smoke tests cover generation, optional 0/1/2/8-image inputs, enhancement switches, and short video; they are not exhaustive model/resolution/duration certification.

### Optional images and text previews

A form cannot make a mandatory LoadImage optional. The graph must first implement lazy optional branches. Then describe the grouping in `extra.comfyLite`:

```json
{
  "description": "App description",
  "fields": {"42.steps": {"advanced": true, "max": 60}},
  "imageGroups": [{
    "label": "Reference images",
    "fields": ["10.image", "11.image"],
    "min": 0,
    "count": "12.value"
  }]
}
```

All references must be exposed official inputs. `count` receives the actual number; `toggle` may control whether a second image exists. `min: 1` requires at least one image. Unused slots are cleared.

Enhanced-prompt preview requires text output from the graph. Connect official `PreviewAny` after the prompt switch and before encoding, and select it as an app output. With enhancement disabled, the original text branch remains unchanged. Pocket cannot infer a model's internal prompt.

## Troubleshooting

**No apps:** verify the `.app.json` extension, exposed outputs, backend availability, and compatibility messages. Ordinary workflow JSON is not an app.

**Slow first launch:** package/dependency installation, custom-node imports, and first model loading are different stages. Subsequent launches reuse installed dependencies.

**Progress resets after 100%:** it describes the current node, not a whole-job time estimate. The next node starts a new counter. Some nodes report no numeric progress.

**Port occupied:** check for another Pocket instance. Use a separate `--home` and `--port`, or update saved configuration. Avoid two controllers managing the same ComfyUI.

**Embedded Python cannot create a venv:** bootstrap Pocket with standard Python, then point the separate runtime executable to ComfyUI's embedded interpreter.

**Phone is slow/unreachable:** verify local access, Tailscale, interface addresses, and firewall. Smaller previews reduce payloads, not relay latency or inference time.

**Upload formats:** PNG/JPEG/WebP, up to 20 MB and 40 million pixels each. Convert HEIC first. Images go to the backend you configured, not a hosted Pocket cloud.

## Security and privacy

Loopback-only by default. Remote APIs require an access code; sessions last 30 days. Host, Origin, and source networks are checked. Media is restricted to known job results; there is no arbitrary URL proxy.

This is not a public multi-tenant service. Everyone holding the access code can run apps and manage a configured local ComfyUI process. LAN HTTP is not encrypted; use trusted private networks/Tailscale, not public port forwarding. Pocket does not protect the original ComfyUI port or other computer services.

Real configurations, secrets, jobs, upload maps, private workflows/models, and development audit materials are excluded from publication. Remove tokens, private images, machine paths, and download credentials before reporting issues.

## Development

```bash
npm install
npm test
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
npm run build
npm pack
```

Create a private config from `config.example.json`, or use the CLI. Public tests use synthetic fixtures and require no private workflows, models, or GPU.

```text
cli/           # npx launcher and setup
backend/       # API adapter, auth, progress, previews, process controls
web/           # React + TypeScript + shadcn/ui
scripts/       # Build/compression tools
tests/         # GPU-free unit tests
.dev/          # Ignored local-only helper material
```

Contributions should include reproduction steps and minimal non-private app examples. Never commit model files, access codes, or personal output media.

## License and acknowledgements

MIT: [LICENSE](LICENSE). See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). ComfyUI, models, and custom nodes retain their own licenses. This project is independent and not endorsed by ComfyUI.

References: [ComfyUI routes](https://docs.comfy.org/development/comfyui-server/comms_routes), [execution messages](https://docs.comfy.org/development/comfyui-server/comms_messages), [npm npx](https://docs.npmjs.com/cli/v11/commands/npx).
