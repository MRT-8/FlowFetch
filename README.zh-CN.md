# FlowFetch

[English](README.md)

FlowFetch 是一个面向 Linux 的终端下载工具，适合直接处理文件下载链接。它会校验 HTTP 或 HTTPS 链接、以流式方式下载文件、在终端展示清晰的下载进度，并在合适的时候识别和安全解压常见压缩包。

这个项目的设计目标很明确：

- 默认优先走 Python 方案完成下载和解压
- 交互友好，尽量减少用户输入
- 面对大文件或特殊格式时，允许切换到系统工具
- 对解压路径做安全检查，避免路径穿越

## 项目定位

FlowFetch 适合这类常见场景：

- 粘贴一个 `http://` 或 `https://` 文件链接直接下载
- 下载时查看进度、速度、总大小和剩余时间
- 保存到当前目录或自定义目录
- 识别 `zip`、`tar.gz`、`gz` 等压缩格式
- 下载完成后询问是否解压
- 在需要时切换到 `curl`、`wget`、`unzip`、`tar`、`7z` 等系统工具

## 功能

- 支持交互模式和直接命令行模式
- 下载前探测文件元信息
- 自动从响应头或 URL 推断文件名
- 下载过程中先写入 `.part` 临时文件，避免留下“看起来完整但实际损坏”的目标文件
- 文件名冲突时支持自动重命名
- 下载失败支持重试
- 对支持的压缩格式做安全解压检查
- 提供稳定退出码，便于自动化调用

## 支持格式

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

## 从源码安装

目前仓库提供的是源码版本。

运行要求：

- Linux
- Python 3.9+
- 推荐使用 `uv`，也支持使用 `pip`

推荐用 `uv` 初始化：

```bash
uv sync
uv run flowfetch --help
```

`uv` 方式示例：

```bash
uv run flowfetch https://example.com/demo.zip
uv run downloader.py --help
```

如果你更习惯 `pip`：

```bash
pip install -r requirements.txt
python downloader.py --help
```

说明：

- 开发过程中使用的 `.venv` 不会随仓库一起发布，也不应该提交到 GitHub。
- 克隆仓库后的用户应在本地自行安装依赖，而不是依赖一个已打包的虚拟环境。
- 执行 `uv sync` 后，项目会暴露一个可直接使用的 `flowfetch` 命令入口。

## 可选系统工具

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

## 使用方法

交互模式：

```bash
uv run flowfetch
```

直接下载：

```bash
uv run flowfetch https://example.com/demo.zip
```

指定目录并自动解压：

```bash
uv run flowfetch --output-dir ./downloads --extract https://example.com/demo.tar.gz
```

强制使用 Python 下载器：

```bash
uv run flowfetch --downloader httpx https://example.com/file.bin
```

强制使用系统解压器：

```bash
uv run flowfetch --extractor system --extract https://example.com/demo.7z
```

## 常用参数

```bash
uv run flowfetch [options] [url]
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

## 退出码

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

## FlowFetch 的行为方式

- 下载前会尽量获取文件名和文件大小，方便展示和保存。
- 下载过程先写入 `.part` 文件，校验通过后再重命名成最终文件。
- 中小文件默认使用 Python 下载器。
- 大文件在满足条件时可切换到 `curl` 或 `wget`。
- 标准库支持的压缩包默认走 Python 解压，并包含路径安全检查。
- 不支持或体积较大的压缩包会在可用时切换到系统解压工具。

## Linux 单文件发行版

FlowFetch 同时支持通过 GitHub Releases 分发 Linux `x86_64` 单文件版本。

发布资产名称固定为：

- `flowfetch-linux-x86_64.tar.gz`

下载后可这样使用：

```bash
tar -xzf flowfetch-linux-x86_64.tar.gz
cd flowfetch-linux-x86_64
chmod +x flowfetch
./flowfetch --help
./flowfetch https://example.com/demo.zip
```

这个发行版适合希望“下载即运行”的用户，不需要提前安装 Python 依赖，也不需要执行 `pip install`。

首个公开版本的详细发布说明见：

- [`release/v0.1.0.md`](release/v0.1.0.md)

## 仓库结构

- `downloader.py`：当前 CLI 入口和主要实现
- `pyproject.toml`：项目元数据和 `flowfetch` 命令入口
- `uv.lock`：`uv` 工作流使用的锁文件
- `requirements.txt`：面向 `pip` 的简洁依赖列表
- `release/v0.1.0.md`：首个公开 GitHub Release 的说明
- `README.md`：英文主文档
- `README.zh-CN.md`：简体中文文档

## 许可证

本项目采用 Apache License 2.0。详见 [LICENSE](LICENSE)。
