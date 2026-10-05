<div align="center">

<h1>Comfy Pocket</h1>

<p>手机、电脑都能用的轻量 ComfyUI 应用客户端。</p>

[![npm](https://img.shields.io/npm/v/comfy-pocket?style=flat-square&color=47664b)](https://www.npmjs.com/package/comfy-pocket)
[![CI](https://img.shields.io/github/actions/workflow/status/SquirrelSong5/comfy-pocket/checks.yml?branch=main&style=flat-square&label=CI)](https://github.com/SquirrelSong5/comfy-pocket/actions/workflows/checks.yml)
[![MIT](https://img.shields.io/github/license/SquirrelSong5/comfy-pocket?style=flat-square&color=47664b)](LICENSE)
[![Node.js](https://img.shields.io/badge/Node.js-22.12%2B-47664b?style=flat-square)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-47664b?style=flat-square)](https://www.python.org/)

简体中文 · [English](README.en.md) · [快速开始](#快速开始) · [使用指南](docs/guide.zh-CN.md) · [反馈](https://github.com/SquirrelSong5/comfy-pocket/issues)

</div>

Comfy Pocket 连接你自己的 ComfyUI，把已保存的应用变成适合日常使用的网页。换提示词、上传图片、查看进度和下载结果，都可以在手机上完成。

![Comfy Pocket desktop](docs/screenshots/desktop.png)


## 为什么做这个项目？

ComfyUI 官方已经有应用模式，也支持手机访问。做 Pocket 的起因很简单：通过 Tailscale 在手机上远程打开官方页面时，界面加载需要等很久，而日常使用往往只是换个提示词、传张图片、看一下结果。

因此，Pocket 单独提供一个轻量前端，只保留运行应用需要的操作，减少手机端要加载的页面资源。应用仍在官方 ComfyUI 中构建和保存，任务也交给同一个 ComfyUI 后端执行。它解决的是这类远程使用场景下的界面加载负担，不会让模型推理变快；实际打开速度仍取决于网络和部署环境。

## 同步的是什么？

Pocket 同步的是你在 ComfyUI **应用模式（App Mode）** 中创建并保存的应用。

一个应用基于已有的节点工作流：你通过官方 **App Builder** 选出日常要调整的输入（例如提示词、参考图片、尺寸），以及运行后要展示的输出。ComfyUI 将这些输入和输出组织成简洁的操作界面，底层仍由原来的工作流执行。详见 [官方应用模式指南](https://docs.comfy.org/interface/app-mode)。

例如，一个生图工作流可以包含几十个节点，而使用时只显示「提示词、画面比例、生成结果」。哪些参数出现在界面上，由创建应用的人决定。

点击「同步官方应用」时，Pocket 会读取所连接 ComfyUI 中已保存的 `.app.json` 文件及其输入、输出配置，生成自己的操作面板。普通工作流 `.json` 不会被自动转换成应用；请先在官方界面完成构建并保存，再回到 Pocket 同步。

## 快速开始

已有可用的 **ComfyUI**、**Node.js 22.12+** 和支持 `venv/pip` 的 **Python 3.10+**，就可以运行：

```bash
npx comfy-pocket
```

按提示填写 ComfyUI 的目录或地址，完成后浏览器会自动打开。首次启动会安装独立的 Python 环境，前端已打包好。

1. 在 ComfyUI 中打开工作流，进入 App Mode，通过 App Builder 选择输入和输出，并保存应用（`.app.json`）。
2. 在 Pocket 中点击「同步官方应用」。
3. 选择应用、填写参数，点击「开始生成」。

下次仍然用同一条命令启动。终端保持打开；退出 Pocket 不会自动停止 ComfyUI。

启动成功后，终端会列出本机、局域网和检测到的 Tailscale 地址，并标注是否已开放。没有配置监听的地址会提示如何启用，不会自动改变网络设置。

关闭时在原终端按 `Ctrl+C`，或在另一个终端运行：

```bash
npx comfy-pocket stop
```

默认不会随开机启动，关机后服务就会结束，下次需要重新运行。需要登录 Windows 后自动启动，可按 [开机启动说明](docs/guide.zh-CN.md#开机启动可选) 设置。

<details>
<summary>镜像源找不到包？</summary>

新包同步到镜像源需要时间，可以指定 npm 官方源：

```bash
npx --registry=https://registry.npmjs.org/ comfy-pocket
```

</details>

需要指定 Python、使用整合包或双击启动？见 [安装与启动](docs/guide.zh-CN.md#快速开始)。

## 功能

| | |
| --- | --- |
| **应用同步** | 读取官方保存的应用。新增应用后同步即可，无需修改页面代码。 |
| **参数与图片** | 提示词、数字、选项、开关和图片上传；支持已配置的可选多图组。 |
| **生成进度** | 查看当前节点、执行步骤和排队状态，也可以取消任务。 |
| **结果预览** | 图片先加载较小的 WebP 预览，原图单独下载；支持文本及视频、音频结果。 |
| **运行记录** | 回看通过 Pocket 提交的任务和作品。 |
| **进程控制** | 配置本机运行环境后，在网页中手动启停 ComfyUI，多个应用共用一个后端。 |

提示词增强、多图编辑等能力由工作流提供。Pocket 读取你公开的参数，不附带模型，也不修改节点画布。

## 在手机上使用

<p align="center">
  <img src="docs/screenshots/mobile-create.png" width="280" alt="手机端应用选择与参数输入" />
  &nbsp;&nbsp;
  <img src="docs/screenshots/mobile-result.png" width="280" alt="手机端作品预览与文本结果" />
</p>

电脑端的应用列表在手机上收进下拉框，结果放在参数下方。选好应用、填完参数，向下就能查看作品；右上角的时钟按钮打开运行记录。

手机和电脑连接同一局域网，或者通过 Tailscale 连接。在电脑端「手机访问」中查看地址和访问码，用手机浏览器打开即可。首次需要配置监听地址，步骤见 [手机连接指南](docs/guide.zh-CN.md#手机与局域网访问)。

任务在电脑上执行，切走手机页面不会中断生成。电脑需要保持开机，Pocket 服务也需要运行。默认只允许本机访问，不建议直接把端口开放到公网。

<sub>截图来自实际界面，使用公开演示数据；风景图为 SVG 示意图。演示应用不随项目分发，当前界面以中文为主。</sub>

## 文档

- [电脑端与手机端操作](docs/guide.zh-CN.md#先看看怎么用)
- [配置、命令行参数与升级](docs/guide.zh-CN.md#配置数据与升级)
- [ComfyUI 进程管理](docs/guide.zh-CN.md#进程管理)
- [兼容范围、可选图片与提示词预览](docs/guide.zh-CN.md#兼容范围)
- [常见问题](docs/guide.zh-CN.md#常见问题) · [安全与隐私](docs/guide.zh-CN.md#安全与隐私)

## 开发与反馈

```bash
git clone https://github.com/SquirrelSong5/comfy-pocket.git
cd comfy-pocket
npm install
node cli/index.mjs
```

前端使用 React、TypeScript 和 shadcn/ui，后端使用 Python / aiohttp。构建与测试命令见 [开发指南](docs/guide.zh-CN.md#开发)。

遇到问题可以 [提交 Issue](https://github.com/SquirrelSong5/comfy-pocket/issues)，附上复现步骤和错误信息。应用样例请先去掉私人图片、访问码和机器路径。欢迎 PR。

## 许可证

[MIT](LICENSE)。第三方组件见 [许可证说明](THIRD_PARTY_NOTICES.md)。Comfy Pocket 是独立项目，与 ComfyUI 官方无隶属关系。
