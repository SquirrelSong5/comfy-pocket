# 手机浏览电脑 input / output

## input / output 文件

点击侧栏或手机顶栏的「电脑文件」，选择 `output · 生成作品` 或 `input · 输入素材`。支持子文件夹、当前目录搜索、文件类型筛选、最新排序、分页、图片预览、视频/音频播放和原文件下载。浏览器不能播放的编码需要下载后打开。

文件列表直接读取电脑文件夹，包括在 ComfyUI 官方界面运行生成的作品。它与 Pocket 的运行记录相互独立，ComfyUI 暂停时也能浏览已有文件。该入口只读，不提供删除、移动或覆盖。

在 Pocket 的 `config.json` 中明确配置本机目录并重启 Pocket，例如：

```json
{
  "input_directory": "D:/ComfyUI/input",
  "output_directory": "D:/ComfyUI/output"
}
```

配置的是 Pocket 所在电脑可读取的目录；连接远程 ComfyUI 时不会自动扫描远程磁盘。使用自定义 `--input-directory` / `--output-directory` 时填实际路径。没有配置的入口会显示提示。

手机继续使用现有局域网或 Tailscale 地址和访问码。新文件接口沿用 Pocket 的地址限制、网络限制和登录验证，只能读取所选根目录，拒绝路径越界、符号链接及 Windows 目录联接。HTML 等非媒体文件强制下载。
