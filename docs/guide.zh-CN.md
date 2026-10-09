# Comfy Pocket 使用指南

**工作流在电脑上跑，手机上也能随手用。**

[English](guide.en.md) · [安装与启动](#快速开始) · [手机访问](#手机与局域网访问) · [兼容范围](#兼容范围)

工作流调好之后，平时往往只需要换一句提示词、传几张图片、改一下尺寸，然后等结果。Comfy Pocket 把这些操作放进一个轻量网页，电脑和手机都能打开，生成任务仍然交给你自己的 ComfyUI。

你在 ComfyUI 官方界面里保存应用、选好要公开的参数，Pocket 就会读取它们。以后新增应用，点击同步就能看到，不需要为每个模型重新写页面。搭节点、装模型还是在 ComfyUI 里完成。



## 先看看怎么用

下面是当前界面的浏览器截图。为方便公开展示，应用、参数和结果均使用演示数据；风景图是手绘 SVG 示意图，不代表某个模型的生成效果。项目不附带截图中的演示应用或模型。当前界面以中文为主。

### 电脑端：一边调参数，一边看结果

![电脑端：左侧应用列表，中间参数表单，右侧图片结果](screenshots/desktop.png)

左边是你已经保存的应用。选中一个后，中间显示它公开的参数，右边显示这次任务的结果。不必每次回到节点画布里寻找提示词和图片输入。

1. **先看顶部的 ComfyUI 状态。** 配置了本机进程管理后，可以在这里手动启动、停止或重启。切换应用会复用同一个后端，不会再开一个进程。
2. **填写这次要用的参数。** 改提示词、选比例，或者上传参考图。设为高级项的参数收在「更多参数」里；具体有哪些控件，取决于你保存的应用。
3. **点击「开始生成」。** 右侧会显示当前执行的节点和步骤。加载模型时可能只有状态文字；这里的百分比是当前节点的进度，不是整次任务的剩余时间。
4. **看图，再决定要不要下载。** 页面先加载较小的预览图，点击「查看原图」或下载按钮取得原始文件。工作流输出了文本时，图片下方也能查看、复制，例如增强后的提示词。

侧边栏的「运行记录」可以回看从 Pocket 提交的任务；「同步官方应用」用来刷新新增或修改过的应用。它不会导入你在其他 ComfyUI 页面里提交的全部历史。

参数修改后会自动保存到 Pocket 电脑端的 `state/preferences.json`，看到「已保存到电脑」即可离开页面。每个应用分别记住提示词、模型、尺寸、步数、种子和开关，并恢复上次打开的应用；连接同一台电脑的手机和不同浏览器共用这些设置。图片需要重新上传。点击「恢复默认参数」只重置当前应用。工作流更新后，失效的参数和选项会回退到新默认值。

### 手机端：选应用，填参数，往下看作品

<p>
  <img src="screenshots/mobile-create.png" width="320" alt="手机端：应用选择、提示词、比例和开始生成按钮" />
  <img src="screenshots/mobile-result.png" width="320" alt="手机端：图片预览、原图下载和提示词文本结果" />
</p>

手机上用浏览器打开即可，不需要额外安装客户端。应用列表收进顶部下拉框，参数和作品按上下顺序排列，避免把电脑上的三栏硬塞进小屏幕。

第一次连接，先在电脑端点击「手机访问」，再用手机打开对应地址、输入访问码。手机和电脑可以在同一个局域网，也可以通过 Tailscale 连接；[具体配置在这里](#手机与局域网访问)。

连接好以后，日常操作就是：**选应用 → 填提示词或添加图片 → 开始生成 → 向下查看结果**。右上角的时钟按钮可以打开运行记录。任务提交后在电脑上执行，暂时切走手机页面不会中断生成；回来后可继续查看状态。

图片编辑应用可以从手机选择 PNG、JPEG、WebP 图片。应用若配置了可选多图组，就可以按需只传一张或添加多张；数量上限和是否允许不传图由工作流决定。iPhone 的 HEIC 图片需要先转换格式。

查看结果时先传输 WebP 预览，最长边不超过 1280 px，原图仍保留在电脑里。这样浏览作品时不用每次等完整大图下载；需要原始质量时再打开原图。视频、音频输出也可以在页面播放，但实际支持情况取决于工作流和浏览器。

**电脑需要保持开机，Pocket 也要保持运行。** 手机只负责操作和显示，推理仍使用电脑上的模型与显卡。提示词增强、多图编辑等能力来自你自己的工作流，Pocket 不会自动为工作流补上这些能力。

## 快速开始

### 准备条件

1. Node.js **22.12+**（包含 npm / npx）。
2. Python **3.10+**，支持 `venv` 和 `pip`。可指定现有 ComfyUI 虚拟环境中的 Python。
3. 已安装的 ComfyUI，以及你自己的模型、自定义节点和已保存应用。

已在 Windows 11 + Python 3.13 上实测。CI 覆盖 Windows/Linux；macOS、各类整合包及旧版 ComfyUI 没有完整实机验收。

### 方式一：一条命令启动

```bash
npx comfy-pocket
```

首次运行按提示填写 ComfyUI 目录或地址，安装完成后会打开浏览器。npm 包已经带好前端，不需要安装 Git 或自己构建页面。以后执行同一条命令，会继续使用已保存的配置和 Python 环境。

- **ComfyUI 已经在运行？** 目录留空，填写它的地址即可。
- **希望在页面里启停 ComfyUI？** 选择包含 `main.py` 的目录，并使用具备 ComfyUI 依赖的 Python。
- **首次安装需要联网。** 启动器会从 PyPI 安装 Pocket 的依赖，放进独立环境，不会安装模型、CUDA 或修改 ComfyUI 环境。

如果你的 npm 使用镜像源，新包可能尚未同步。遇到找不到包时，指定官方源：

```bash
npx --registry=https://registry.npmjs.org/ comfy-pocket
```

### 方式二：预构建发行包（跳过前端构建）

```bash
npx --yes --package=https://github.com/SquirrelSong5/comfy-pocket/releases/download/v0.1.0/comfy-pocket-0.1.0.tgz comfy-pocket
```

此包自带编译后的前端；首次仍需准备独立 Python 环境。也可从 [Releases](https://github.com/SquirrelSong5/comfy-pocket/releases) 下载 `.tgz`，解压后执行 `node cli/index.mjs`。

### 无交互配置示例

```powershell
npx comfy-pocket --comfy-dir "D:\AI\ComfyUI" --python "D:\AI\ComfyUI\.venv\Scripts\python.exe"
```

只连接已经运行的后端：

```bash
npx comfy-pocket --comfy-url http://127.0.0.1:8188
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

启动成功后，终端会列出本机、局域网和检测到的 Tailscale IPv4 地址。只有配置允许且本机探测成功的地址才会标为可访问；「未开放」需要编辑配置的 `bind`、`hosts`、`networks` 并重启，「未就绪」通常表示网卡尚未连接或监听失败。本机探测不能证明手机侧网络和防火墙已通。其他 VPN 使用的 `100.64.0.0/10` 地址不会直接标为 Tailscale。

1. 在官方 ComfyUI 中加载并测试工作流。
2. 使用官方应用构建功能，选择日常运行需要公开的输入与输出，保存为 `.app.json`。
3. 打开 Pocket，点击「同步官方应用」。普通工作流 `.json` 不会自动变成应用。
4. 选择应用、填写参数、上传图片并开始生成。
5. 查看当前节点进度、文本结果和预览图；需要原始质量时点击原图/下载。

应用名推荐 `模型名称 · 用途.app.json`，例如 `My Model · Image editing.app.json`。本仓库不附送个人工作流或任何模型。

## 关闭 Pocket

在启动终端按 `Ctrl+C`，或在另一个终端执行：

```bash
npx comfy-pocket stop
```

如果启动时指定了数据目录，关闭时使用同一个目录：

```bash
npx comfy-pocket stop --home "D:\PocketData"
```

此命令只停止该数据目录对应的 Pocket 服务，不停止 ComfyUI，也不取消已经交给 ComfyUI 的任务。`stop` 从 0.1.1 起支持；旧版服务请先在原终端按 `Ctrl+C`，升级并启动后再使用。安装包不会创建开机启动项，关机或重启后 Pocket 会结束。

## 开机启动（可选）

Windows 下可以按需设置为**登录后启动**：

1. 先手动运行 Pocket，完成首次安装和配置。
2. 按 `Win+R`，输入 `shell:startup`，打开当前用户的启动文件夹。
3. 在里面新建 `Start Comfy Pocket.cmd`，内容如下：

```bat
@echo off
call npx --yes comfy-pocket --no-open
```

使用自定义数据目录时，在末尾加上 `--home "D:\PocketData"`。下次登录 Windows 会打开终端并运行 Pocket，不自动打开浏览器，也不自动启动 ComfyUI。保持此终端打开；关闭方式同上。删除启动文件夹里的这个文件即可取消自动启动。

这是当前用户登录后的启动方式，不是在登录前运行的系统服务。首次安装仍应手动完成，避免开机时卡在配置提问或依赖安装。

## 手机与局域网访问

默认只监听 `127.0.0.1:8189`，只有电脑自身可以打开。

第一次配置时，使用明确的电脑网卡 IPv4 地址增加监听：

```bash
npx comfy-pocket --host 100.80.20.10 --host 192.168.1.20
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

配置示例见 [config.example.json](../config.example.json)。源码直接运行 `python -m backend.server` 默认使用仓库中的私有 `config.json`；设置 `COMFY_POCKET_HOME` 可指定外部数据目录。CLI 不把用户数据放在临时 npx 缓存中。

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

升级时运行 `npx comfy-pocket@latest`；需要固定版本时使用 `npx comfy-pocket@0.1.0`。数据目录不变。卸载时先停止 Pocket，再删除其数据目录；这不会卸载 ComfyUI 或删除 ComfyUI 原始结果。请先备份需要的运行记录。

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

MIT，见 [LICENSE](../LICENSE)。第三方组件说明见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。ComfyUI、模型和自定义节点各自遵循其许可证；本项目不代表或隶属于 ComfyUI 官方。

参考：[ComfyUI 服务端接口](https://docs.comfy.org/development/comfyui-server/comms_routes)、[实时事件](https://docs.comfy.org/development/comfyui-server/comms_messages)、[npm npx](https://docs.npmjs.com/cli/v11/commands/npx)。
