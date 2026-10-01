# Comfy Pocket

**把已有的 ComfyUI 应用带到手机上：轻量加载、运行任务、查看结果。**

[English](README.en.md) · [安装与启动](#快速开始) · [手机访问](#手机与局域网访问) · [兼容范围](#兼容范围)

Comfy Pocket 是独立的轻量 Web 客户端，通过官方 HTTP / WebSocket 接口连接你自己的 ComfyUI。它适合已经搭好工作流、希望在手机或另一台电脑上日常使用的人。

它不包含模型，不替代 ComfyUI 推理后端，也不是节点编辑器。无需把完整的官方编辑器加载到手机上。



## 能做什么

- **动态应用列表**：读取 ComfyUI 已保存的 `.app.json`，根据官方应用公开的参数生成表单。新增应用后同步即可，不维护模型白名单。
- **移动端运行**：文本、数字、枚举、开关、图片输入，上传、队列、取消、历史与结果下载。
- **可选多图**：已有工作流支持可选分支时，通过通用图片组描述自动管理图片数量和空槽位。
- **真实执行进度**：显示官方上报的节点和步骤；没有步骤的阶段不伪造百分比。
- **文本结果**：显示节点返回的 `ui.text`，可用于实际提示词、增强提示词等预览。
- **更小的图片传输**：先显示最大边 1280 px 的 WebP 预览，原图单独查看或下载，原文件不改动。
- **可选进程管理**：配置本机 ComfyUI 后，在页面启动、停止和重启同一个后端进程。
- **私有访问**：远程访问码、Host 和来源网段检查、跨站请求限制；兼容 Tailscale。

## 快速开始

### 准备条件

1. Node.js **22.12+**（包含 npm / npx）。
2. Python **3.10+**，支持 `venv` 和 `pip`。可指定现有 ComfyUI 虚拟环境中的 Python。
3. 已安装的 ComfyUI，以及你自己的模型、自定义节点和已保存应用。

已在 Windows 11 + Python 3.13 上实测。CI 覆盖 Windows/Linux；macOS、各类整合包及旧版 ComfyUI 没有完整实机验收。

### 方式一：一条命令启动

```bash
npx --yes github:SquirrelSong5/comfy-pocket#v0.1.0
```

首次会下载项目、自动构建前端、询问 ComfyUI 目录/地址，创建独立 Python 环境并安装轻量服务依赖。随后打开浏览器。以后再次执行会复用用户配置和 Python 环境。

- 留空 ComfyUI 目录：仅连接已有后端，不提供本机进程管理。
- 指定目录：选择包含 `main.py` 的目录；自动尝试其中的 `.venv`、`venv`、`env` 等 Python。
- 前端构建属于首次 GitHub 安装流程；不需要手动运行 npm install/build。
- 需要联网访问 GitHub、npm 和 PyPI。不会安装模型、CUDA 或修改 ComfyUI 环境。
- GitHub 安装可能需要 Git。无 Git 或希望跳过构建，使用下面的预构建包。

> 目前发布在 GitHub，**尚未发布 npm 注册表**。`npx comfy-pocket` 不是本项目已验证的安装命令，请使用带 GitHub 地址的命令。

### 方式二：预构建发行包（跳过前端构建）

```bash
npx --yes --package=https://github.com/SquirrelSong5/comfy-pocket/releases/download/v0.1.0/comfy-pocket-0.1.0.tgz comfy-pocket
```

此包自带编译后的前端；首次仍需准备独立 Python 环境。也可从 [Releases](https://github.com/SquirrelSong5/comfy-pocket/releases) 下载 `.tgz`，解压后执行 `node cli/index.mjs`。

### 无交互配置示例

```powershell
npx --yes github:SquirrelSong5/comfy-pocket#v0.1.0 --comfy-dir "D:\AI\ComfyUI" --python "D:\AI\ComfyUI\.venv\Scripts\python.exe"
```

只连接已经运行的后端：

```bash
npx --yes github:SquirrelSong5/comfy-pocket#v0.1.0 --comfy-url http://127.0.0.1:8188
```

`--python` 必须是 Python 可执行文件，不能填写启动 BAT。Windows 便携版的嵌入式 Python 可能缺少 `venv`；这种情况下请安装标准 Python，或使用支持 venv 的环境。若要进程管理，配置里的 `runtime.executable` 应指向具备 ComfyUI 模型依赖的 Python。

### 本地源码 / 双击启动

```bash
git clone https://github.com/SquirrelSong5/comfy-pocket.git
cd comfy-pocket
npm install
node cli/index.mjs
```

Windows 完成首次安装后，也可双击 **`Start Comfy Pocket.cmd`**。已有本地 `config.json` 的开发环境会使用 `start.ps1` 后台启动；普通新安装通过 CLI 引导启动。

CLI 默认前台运行：保持终端打开；`Ctrl+C` 只停止 Pocket，不自动停止 ComfyUI。自动开机/登录启动需自行配置系统启动项，本发行包不会悄悄创建系统服务。

## 第一次使用

1. 在官方 ComfyUI 中加载并测试工作流。
2. 使用官方应用构建功能，选择日常运行需要公开的输入与输出，保存为 `.app.json`。
3. 打开 Pocket，点击「同步官方应用」。普通工作流 `.json` 不会自动变成应用。
4. 选择应用、填写参数、上传图片并开始生成。
5. 查看当前节点进度、文本结果和预览图；需要原始质量时点击原图/下载。

应用名推荐 `模型名称 · 用途.app.json`，例如 `My Model · Image editing.app.json`。本仓库不附送个人工作流或任何模型。

## 手机与局域网访问

默认只监听 `127.0.0.1:8189`，只有电脑自身可以打开。

第一次配置时，使用明确的电脑网卡 IPv4 地址增加监听：

```bash
npx --yes github:SquirrelSong5/comfy-pocket#v0.1.0 --host 100.80.20.10 --host 192.168.1.20
```

以上是示例地址，必须替换为你电脑实际的 Tailscale / 局域网地址。手机与电脑需要在同一 tailnet 或同一局域网。浏览器访问 `http://电脑地址:8189`。

首次手机访问需要访问码。在电脑用 `http://127.0.0.1:8189` 打开页面，点击侧边栏「手机访问」获取。请勿公开分享访问码。

已有配置时，命令行不会覆盖它；修改 `~/.comfy-pocket/config.json` 的 `bind`、`hosts` 和 `networks` 后重启 Pocket。`--host` 生成的配置允许对应 LAN /24 或 Tailscale `100.64.0.0/10` 来源。需要更窄范围时自行修改。

软件不自动安装 Tailscale、不创建公网隧道、不修改防火墙。若防火墙阻止访问，需要允许该端口来自所需私有网段。电脑必须开机且未睡眠。

## 配置、数据与升级

默认数据目录：**`~/.comfy-pocket/`**，Windows 通常为 `%USERPROFILE%\.comfy-pocket`。

```text
~/.comfy-pocket/
├── config.json       # 私有机器配置
├── .venv/            # Pocket 专用 Python 环境
└── state/
    ├── access.json   # 访问码和会话签名密钥，不要分享
    ├── jobs.json     # Pocket 提交的任务记录
    ├── uploads.json  # 上传标识映射
    ├── previews/     # 可重新生成的图片预览
    └── comfyui.log   # 经 Pocket 启动的 ComfyUI 日志
```

配置示例见 [config.example.json](config.example.json)。源码直接运行 `python -m backend.server` 默认使用仓库中的私有 `config.json`；设置 `COMFY_POCKET_HOME` 可指定外部数据目录。CLI 不把用户数据放在临时 npx 缓存中。

| 参数 | 作用 |
| --- | --- |
| `--home DIR` | 独立配置与数据目录，适合多套安装 |
| `--python FILE` | 创建环境所用 Python；启用本机管理时也是 ComfyUI Python |
| `--comfy-dir DIR` | ComfyUI 源码目录，启用进程管理 |
| `--comfy-url URL` | 后端 HTTP(S) origin，默认本机 8188 |
| `--port PORT` | Pocket 端口，默认 8189 |
| `--host IPv4` | 额外监听地址，可重复；拒绝通配地址 |
| `--no-open` | 不自动打开浏览器 |
| `--setup-only` | 完成配置和依赖安装后退出 |
| `--help` | 显示帮助 |

升级时改用新版本 tag 或 release URL，数据目录不变。卸载时先停止 Pocket，再删除其数据目录；这不会卸载 ComfyUI 或删除 ComfyUI 原始结果。请先备份需要的运行记录。

## 进程管理

一台电脑复用一个 ComfyUI 后端，切换应用不需要启动新进程。模型换入/换出由 ComfyUI 处理，和进程启动不同。

可选 `runtime` 包含 `cwd`、`executable`、`args`。进程管理只识别完整命令匹配的本机实例，网页不能提交任意命令。已有外部实例的启动参数不同，会显示不可接管；按原启动参数修改配置后再试。远端 `--comfy-url` 不支持控制那台机器的进程。

有运行或排队任务时拒绝停止/重启。当前页面状态会在启动中、运行中、停止或失败之间更新；启动失败查看日志。

## 兼容范围

| 内容 | 支持情况 |
| --- | --- |
| 官方应用 `.app.json` + `extra.linearData` | 动态读取输入与输出 |
| STRING / INT / FLOAT / BOOLEAN / 枚举 | 按 `/object_info` 生成控件 |
| 普通后端节点、Reroute、部分绕过节点 | 支持当前适配器转换范围 |
| 图片上传、图片/视频/音频结果 | 支持；视频按 Range 分段读取 |
| 文本 `ui.text` | 支持运行时及历史预览 |
| 前端 JS 虚拟节点、嵌套子图、特殊控件 | 不保证兼容；无法解析时显示原因 |
| 动态组合控件分支切换 | 建议在官方界面固定分支，不保证运行时切换兼容 |
| 官方全部历史任务 | 不导入，仅显示 Pocket 提交的任务 |
| 用户隔离、账号体系、多人权限 | 不支持；共享访问码代表同一个工作室 |

应用结构属于当前官方前端保存格式，上游升级可能需要调整适配器。真实运行测试包含图片生成、0/1/2/8 张可选图、增强开关及短视频，但不代表任意模型、分辨率、时长都已经验证。

### 可选图片与提示词文本

表单不能把必填 LoadImage 自动变成可选。工作流本身要有不会执行空槽位的惰性选择分支，再用 `extra.comfyLite` 描述图片组：

```json
{
  "description": "应用说明",
  "fields": {"42.steps": {"advanced": true, "max": 60}},
  "imageGroups": [{
    "label": "参考图片",
    "fields": ["10.image", "11.image"],
    "min": 0,
    "count": "12.value"
  }]
}
```

字段引用必须是已公开参数。`count` 写入实际张数；也可以用 `toggle` 控制第二张图片是否存在。`min: 1` 表示至少一张。未使用的槽位清空。

增强提示词预览需要工作流输出文本。可在提示词切换之后、编码之前连接官方 `PreviewAny`，并把它设为应用输出；关闭增强时仍走原文分支。Pocket 不会凭空推断模型内部的提示词。

## 常见问题

**没有应用？** 检查是否保存 `.app.json`、公开了输出、ComfyUI 是否在线、是否显示兼容性错误。官方普通工作流文件不是应用文件。

**第一次启动很慢？** 首次安装要下载 npm/Python 依赖；ComfyUI 还要导入自定义节点。第一次生成还可能把模型从磁盘载入。这三个阶段不同。

**进度从 100% 又变为 0%？** 百分比是当前节点的步骤，不是全任务耗时；下一节点会重新计数。模型加载等阶段可能只有节点名。

**端口被占用？** 确认是否已经启动一个 Pocket；使用不同的 `--home` 和 `--port` 创建第二套配置，或修改已有配置端口。不要同时管理同一个 ComfyUI。

**便携 Python 无法创建环境？** 安装支持 `venv/pip` 的标准 Python。先用它安装 Pocket，再在配置中单独填写 ComfyUI 的嵌入式 Python 路径。

**手机慢或打不开？** 先确认电脑本机可用、Tailscale 在线、监听地址/防火墙正确。预览能减少图片传输量，但不能解决中继网络延迟或提升模型推理速度。

**图片上传格式？** PNG / JPEG / WebP，单张最多 20 MB、4000 万像素；HEIC 需先转换。图片传给你配置的 ComfyUI，不上传到本项目托管的云服务。

## 安全与隐私

默认仅本机监听。远程 API 需要访问码，Cookie 有效期 30 天；校验 Host、Origin 和来源网段。媒体仅提供此客户端任务产生的结果，没有任意 URL 代理接口。

这不是面向公网的多用户服务。任何拥有访问码的人都可以运行应用和管理已配置的 ComfyUI；不提供按用户隔离。局域网 HTTP 不加密，推荐使用受信任的私有网络/Tailscale，不要直接公网转发端口。Pocket 的访问控制不保护原始 ComfyUI 8188 或电脑其他端口。

本仓库排除真实配置、访问码、运行记录、上传映射、私有工作流、模型、开发截图与审计资料。问题报告请先去除令牌、私人图片、机器路径和模型下载凭据。安全问题请勿在公开 issue 附带可利用凭据。

## 开发

```bash
npm install                          # 安装并构建前端
npm test                             # Node CLI 单元测试
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
npm run build                        # 构建并生成 gzip 资源
npm pack                             # 生成可供 npx 使用的发行包
```

使用复制后的 `config.example.json` 配置本地私有 `config.json`，或通过 CLI 生成外部配置。开发前端在 `web/`，生产后端在 `backend/`。公开测试全部使用合成数据，不依赖个人工作流、模型或 GPU。

```text
cli/           # npx 入口、环境准备和配置引导
backend/       # 官方 API 适配、鉴权、进度、预览和进程管理
web/           # React + TypeScript + shadcn/ui
scripts/       # 构建/压缩工具
tests/         # 无 GPU 的单元测试
.dev/          # 忽略的本地辅助资料，不参与发行
```

欢迎提交复现步骤、最小且无隐私的应用样例和 PR。不要提交模型、访问码或个人生成结果。

## 致谢与许可证

MIT，见 [LICENSE](LICENSE)。第三方组件说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。ComfyUI、模型和自定义节点各自遵循其许可证；本项目不代表或隶属于 ComfyUI 官方。

参考：[ComfyUI 服务端接口](https://docs.comfy.org/development/comfyui-server/comms_routes)、[实时事件](https://docs.comfy.org/development/comfyui-server/comms_messages)、[npm npx](https://docs.npmjs.com/cli/v11/commands/npx)。
