<div align="center">
  <h1>FlowFetch</h1>
  <p><strong>面向 Linux 的直链下载与安全解压命令行工具。</strong></p>
  <p>校验链接、展示下载进度，并在需要时安全解压常见压缩包。</p>
  <p>
    <a href="README.md">English</a> •
    <a href="https://github.com/MRT-8/FlowFetch/releases">Releases</a> •
    <a href="https://github.com/MRT-8/FlowFetch/releases/latest">最新二进制</a>
  </p>
  <p>
    <a href="https://github.com/MRT-8/FlowFetch/releases">
      <img alt="GitHub Release" src="https://img.shields.io/github/v/release/MRT-8/FlowFetch?display_name=tag&label=release">
    </a>
    <a href="https://github.com/MRT-8/FlowFetch/actions/workflows/release.yml">
      <img alt="Release Workflow" src="https://github.com/MRT-8/FlowFetch/actions/workflows/release.yml/badge.svg">
    </a>
    <a href="LICENSE">
      <img alt="License" src="https://img.shields.io/github/license/MRT-8/FlowFetch">
    </a>
    <img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-3776AB">
    <img alt="Platform" src="https://img.shields.io/badge/platform-Linux-111827">
  </p>
</div>

[快速开始](#快速开始) • [使用安装包](#使用-linux-安装包) • [源码运行](#从源码运行) • [命令示例](#常见示例) • [发布说明](#发布说明)

> [!TIP]
> 如果你只是想直接使用 FlowFetch，优先下载 GitHub Releases 里的 `flowfetch-linux-x86_64.tar.gz`。解压后运行 `./flowfetch` 即可，不需要安装 Python，也不需要执行 `pip install`。

## 为什么用 FlowFetch

FlowFetch 面向的是很常见的这类需求：给一个文件直链，尽量少折腾环境，尽快把文件安全地下载到本地。

| 需求 | FlowFetch 的处理方式 |
| --- | --- |
| 直接下载文件 | 接受 `http://` 和 `https://` 链接，并在下载前先做校验 |
| 清晰的终端反馈 | 展示文件名、大小、进度、速度和剩余时间 |
| 更稳妥的文件落地 | 先写入 `.part`，校验通过后再原子重命名 |
| 压缩包友好 | 自动识别常见压缩格式，并在需要时安全解压 |
| 便于脚本调用 | 提供稳定退出码和明确的 CLI 参数 |
| 需要时可借助系统工具 | 可切换到 `curl`、`wget`、`tar`、`unzip`、`gzip`、`7z` |

## 快速开始

| 方式 | 适合谁 | 是否需要 Python | 第一步 |
| --- | --- | --- | --- |
| Release 安装包 | 想直接使用成品二进制的用户 | 否 | 从 Releases 下载最新的 `flowfetch-linux-x86_64.tar.gz` |
| `uv` 源码工作流 | 开发者或想从源码运行的用户 | 是 | `uv sync` |
| `pip` 源码工作流 | 只有普通 Python 环境的用户 | 是 | `pip install -r requirements.txt` |

## 使用 Linux 安装包

如果你想使用已经打包好的单文件版本，这就是最推荐的方式。

1. 从 [GitHub Releases](https://github.com/MRT-8/FlowFetch/releases/latest) 下载最新的 `flowfetch-linux-x86_64.tar.gz`。
2. 解压压缩包并进入目录。
3. 直接运行 `flowfetch`，或者把它安装到系统路径里。

直接运行：

```bash
tar -xzf flowfetch-linux-x86_64.tar.gz
cd flowfetch-linux-x86_64
chmod +x flowfetch
./flowfetch --help
./flowfetch https://example.com/demo.zip
```

可选：安装到系统中，后续直接输入 `flowfetch`：

```bash
sudo install -m 0755 flowfetch /usr/local/bin/flowfetch
flowfetch --help
flowfetch https://example.com/demo.zip
```

> [!NOTE]
> 这个安装包里包含一个 Linux `x86_64` 单文件可执行程序，以及 `LICENSE` 和简短的 `README.txt`。它不依赖 Python、`uv` 或 `pip install`。

## 从源码运行

推荐使用 `uv`：

```bash
uv sync
uv run flowfetch --help
uv run flowfetch https://example.com/demo.zip
```

也可以直接跑脚本入口：

```bash
uv run downloader.py --help
python downloader.py https://example.com/demo.zip
```

如果你更习惯 `pip`：

```bash
pip install -r requirements.txt
python downloader.py --help
```

## 常见示例

下载一个文件：

```bash
flowfetch https://example.com/demo.zip
```

下载到指定目录并自动解压：

```bash
flowfetch --output-dir ./downloads --extract https://example.com/demo.tar.gz
```

强制使用 Python 下载器：

```bash
flowfetch --downloader httpx https://example.com/file.bin
```

强制使用系统解压器：

```bash
flowfetch --extractor system --extract https://example.com/demo.7z
```

交互模式：

```bash
flowfetch
```

## 常用参数

```bash
flowfetch [options] [url]
```

- `-o, --output-dir`：指定下载目录
- `--filename`：强制指定保存文件名
- `--downloader auto|httpx|curl|wget`：选择下载器
- `--extractor auto|python|system`：选择解压策略
- `--extract`：下载完成后总是解压
- `--no-extract`：下载完成后不解压
- `--overwrite`：允许覆盖已有文件
- `--rename`：同名文件自动重命名
- `--download-threshold`：下载器切换阈值，例如 `1g`
- `--extract-threshold`：解压器切换阈值
- `--retry`：下载失败重试次数
- `--timeout`：统一设置 connect/read 超时
- `--keep-partial`：失败时保留 `.part`
- `--delete-partial`：失败时删除 `.part`
- `--no-fallback`：关闭自动回退
- `--yes`：自动采用推荐确认项
- `--verbose`：输出更详细的错误信息

## FlowFetch 的工作方式

- 在条件允许时，下载前会先探测元信息，方便展示文件名和预期大小。
- 下载过程先写入 `.part` 文件，校验通过后再重命名为最终文件。
- 中小文件默认使用 Python 下载器。
- 大文件在满足条件时可切换到 `curl` 或 `wget`。
- 标准库支持的压缩包默认使用 Python 解压，并带有路径穿越防护。
- 对于不支持或较大的压缩包，可在可用时切换到系统解压工具。

<details>
<summary><strong>支持的格式</strong></summary>

当前 Python 标准库支持自动解压：

- `zip`
- `tar`
- `tar.gz`
- `tgz`
- `tar.bz2`
- `tar.xz`
- `gz`

通过系统工具增强支持：

- `7z`，依赖 `7z` 或 `7zz`

</details>

<details>
<summary><strong>可选系统工具</strong></summary>

FlowFetch 默认路径不依赖系统工具，但在以下情况下会把它们当作增强能力使用：

- 文件较大，需要切换下载器
- 某些格式更适合由系统工具解压
- Python 路径失败且允许自动回退

常用工具包括：

- `curl`
- `wget`
- `unzip`
- `tar`
- `gzip`
- `7z` 或 `7zz`

常见 Linux 安装示例：

```bash
# Debian / Ubuntu
sudo apt update && sudo apt install -y curl wget unzip tar gzip p7zip-full

# CentOS / RHEL
sudo yum install -y curl wget unzip tar gzip p7zip p7zip-plugins

# Fedora
sudo dnf install -y curl wget unzip tar gzip p7zip p7zip-plugins

# Arch Linux
sudo pacman -S curl wget unzip tar gzip p7zip
```

</details>

<details>
<summary><strong>退出码</strong></summary>

- `0`：成功
- `2`：参数错误
- `3`：用户取消
- `4`：URL 非法
- `5`：获取元信息失败
- `6`：下载失败
- `7`：下载结果校验失败
- `8`：解压失败
- `9`：缺少系统下载工具
- `10`：缺少系统解压工具
- `11`：当前格式不支持
- `12`：权限不足

</details>

## 发布说明

- [`release/v0.1.0.md`](release/v0.1.0.md)
- [GitHub Release v0.1.0](https://github.com/MRT-8/FlowFetch/releases/tag/v0.1.0)

## 仓库结构

- `downloader.py`：当前 CLI 入口和主要实现
- `pyproject.toml`：项目元数据和 `flowfetch` 命令入口
- `uv.lock`：`uv` 工作流使用的锁文件
- `requirements.txt`：面向 `pip` 的简洁依赖列表
- `flowfetch.spec`：Linux 单文件构建的 PyInstaller 配置
- `release/README.txt`：打包后二进制附带的简短使用说明
- `release/v0.1.0.md`：首个公开 GitHub Release 的说明
- `README.md`：英文主文档
- `README.zh-CN.md`：简体中文文档

## 许可证

本项目采用 Apache License 2.0。详见 [LICENSE](LICENSE)。
