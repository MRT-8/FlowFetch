from __future__ import annotations

import argparse
import gzip
import os
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from urllib.parse import unquote, urlparse

try:
    import httpx
except ModuleNotFoundError as exc:  # pragma: no cover
    httpx = None  # type: ignore[assignment]
    HTTPX_IMPORT_ERROR = exc
else:
    HTTPX_IMPORT_ERROR = None

try:
    from rich.console import Console
    from rich.progress import (
        BarColumn,
        DownloadColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeRemainingColumn,
        TransferSpeedColumn,
    )
except ModuleNotFoundError:  # pragma: no cover
    Console = None  # type: ignore[assignment]
    BarColumn = None  # type: ignore[assignment]
    DownloadColumn = None  # type: ignore[assignment]
    Progress = None  # type: ignore[assignment]
    SpinnerColumn = None  # type: ignore[assignment]
    TaskProgressColumn = None  # type: ignore[assignment]
    TextColumn = None  # type: ignore[assignment]
    TimeRemainingColumn = None  # type: ignore[assignment]
    TransferSpeedColumn = None  # type: ignore[assignment]
    RICH_AVAILABLE = False
else:
    RICH_AVAILABLE = True


VERSION = "0.1.0"
DEFAULT_USER_AGENT = f"FlowFetch/{VERSION}"
MULTI_PART_SUFFIXES = (
    ".tar.gz",
    ".tar.bz2",
    ".tar.xz",
    ".tgz",
)
ARCHIVE_SUFFIXES = (
    ".tar.gz",
    ".tar.bz2",
    ".tar.xz",
    ".tgz",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
)
STANDARD_LIBRARY_ARCHIVES = {
    "zip",
    "tar",
    "tar.gz",
    "tgz",
    "tar.bz2",
    "tar.xz",
    "gz",
}
TAR_ARCHIVES = {"tar", "tar.gz", "tgz", "tar.bz2", "tar.xz"}
SYSTEM_TOOL_SUGGESTIONS = {
    "curl/wget": {
        "Debian/Ubuntu": "sudo apt update && sudo apt install -y curl wget",
        "CentOS/RHEL": "sudo yum install -y curl wget",
        "Fedora": "sudo dnf install -y curl wget",
        "Arch Linux": "sudo pacman -S curl wget",
    },
    "curl": {
        "Debian/Ubuntu": "sudo apt update && sudo apt install -y curl",
        "CentOS/RHEL": "sudo yum install -y curl",
        "Fedora": "sudo dnf install -y curl",
        "Arch Linux": "sudo pacman -S curl",
    },
    "wget": {
        "Debian/Ubuntu": "sudo apt update && sudo apt install -y wget",
        "CentOS/RHEL": "sudo yum install -y wget",
        "Fedora": "sudo dnf install -y wget",
        "Arch Linux": "sudo pacman -S wget",
    },
    "unzip": {
        "Debian/Ubuntu": "sudo apt update && sudo apt install -y unzip",
        "CentOS/RHEL": "sudo yum install -y unzip",
        "Fedora": "sudo dnf install -y unzip",
        "Arch Linux": "sudo pacman -S unzip",
    },
    "tar": {
        "Debian/Ubuntu": "sudo apt update && sudo apt install -y tar gzip",
        "CentOS/RHEL": "sudo yum install -y tar gzip",
        "Fedora": "sudo dnf install -y tar gzip",
        "Arch Linux": "sudo pacman -S tar gzip",
    },
    "7z": {
        "Debian/Ubuntu": "sudo apt update && sudo apt install -y p7zip-full",
        "CentOS/RHEL": "sudo yum install -y p7zip p7zip-plugins",
        "Fedora": "sudo dnf install -y p7zip p7zip-plugins",
        "Arch Linux": "sudo pacman -S p7zip",
    },
}

class PlainConsole:
    def print(self, *args: object, **_: object) -> None:
        print(*args)

    def input(self, message: str) -> str:
        return input(message)


console = Console() if RICH_AVAILABLE else PlainConsole()


class ExitCode(IntEnum):
    SUCCESS = 0
    UNKNOWN_ERROR = 1
    INVALID_ARGUMENT = 2
    USER_CANCELLED = 3
    INVALID_URL = 4
    METADATA_FAILED = 5
    DOWNLOAD_FAILED = 6
    FILE_VALIDATION_FAILED = 7
    EXTRACT_FAILED = 8
    MISSING_SYSTEM_DOWNLOADER = 9
    MISSING_SYSTEM_EXTRACTOR = 10
    UNSUPPORTED_FORMAT = 11
    PERMISSION_DENIED = 12


@dataclass
class FileMeta:
    filename: str
    total_size: int | None
    content_type: str | None
    final_url: str


@dataclass
class AppConfig:
    download_switch_threshold_bytes: int = 1024**3
    extract_switch_threshold_bytes: int = 2 * 1024**3
    download_timeout_connect_seconds: int = 10
    download_timeout_read_seconds: int = 60
    download_retry_count: int = 3
    download_chunk_size: int = 64 * 1024
    default_extract_yes: bool = True
    auto_fallback_to_python: bool = True
    auto_retry_with_backup_tool: bool = True
    auto_rename_on_conflict: bool = True
    keep_partial_on_failure: bool = True
    non_interactive_default_extract: bool = False


@dataclass
class RunOptions:
    url: str | None
    output_dir: Path
    filename: str | None
    downloader: str
    extractor: str
    extract_mode: bool | None
    conflict_policy: str
    keep_partial_on_failure: bool
    allow_fallback: bool
    yes: bool
    verbose: bool
    interactive: bool


class AppError(Exception):
    def __init__(
        self,
        code: ExitCode,
        stage: str,
        message: str,
        *,
        suggestion: str | None = None,
        detail: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.stage = stage
        self.message = message
        self.suggestion = suggestion
        self.detail = detail


class FlowFetchArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise AppError(
            ExitCode.INVALID_ARGUMENT,
            "PARSE_ARGS",
            f"参数错误: {message}",
        )


def print_info(message: str) -> None:
    if RICH_AVAILABLE:
        console.print(f"[cyan][INFO][/cyan] {message}")
    else:
        console.print(f"[INFO] {message}")


def print_success(message: str) -> None:
    if RICH_AVAILABLE:
        console.print(f"[green][SUCCESS][/green] {message}")
    else:
        console.print(f"[SUCCESS] {message}")


def print_warn(message: str) -> None:
    if RICH_AVAILABLE:
        console.print(f"[yellow][WARN][/yellow] {message}")
    else:
        console.print(f"[WARN] {message}")


def print_error(message: str) -> None:
    if RICH_AVAILABLE:
        console.print(f"[red][ERROR][/red] {message}")
    else:
        console.print(f"[ERROR] {message}")


def format_bytes(value: int | None) -> str:
    if value is None:
        return "未知"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def display_path(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(Path.cwd().resolve())
        return f"./{relative}" if str(relative) != "." else "."
    except ValueError:
        return str(path.resolve())


def sanitize_filename(filename: str) -> str:
    cleaned = filename.strip().replace("\x00", "")
    cleaned = cleaned.replace("\\", "/").split("/")[-1]
    cleaned = cleaned.strip().strip(".")
    return cleaned or "downloaded_file"


def parse_size_value(raw_value: str) -> int:
    value = raw_value.strip().lower()
    match = re.fullmatch(r"(\d+)([kmgt]?i?b?)?", value)
    if not match:
        raise AppError(
            ExitCode.INVALID_ARGUMENT,
            "PARSE_ARGS",
            f"无法解析大小参数: {raw_value}",
            suggestion="可使用 1048576、512m、1g 这类格式",
        )

    number = int(match.group(1))
    suffix = match.group(2) or ""
    multipliers = {
        "": 1,
        "b": 1,
        "k": 1024,
        "kb": 1024,
        "kib": 1024,
        "m": 1024**2,
        "mb": 1024**2,
        "mib": 1024**2,
        "g": 1024**3,
        "gb": 1024**3,
        "gib": 1024**3,
        "t": 1024**4,
        "tb": 1024**4,
        "tib": 1024**4,
    }
    if suffix not in multipliers:
        raise AppError(
            ExitCode.INVALID_ARGUMENT,
            "PARSE_ARGS",
            f"无法解析大小参数: {raw_value}",
        )
    return number * multipliers[suffix]


def split_name_for_conflict(name: str) -> tuple[str, str]:
    lower_name = name.lower()
    for suffix in MULTI_PART_SUFFIXES:
        if lower_name.endswith(suffix):
            return name[: -len(suffix)], name[-len(suffix) :]
    path = Path(name)
    if path.suffix:
        return path.stem, path.suffix
    return name, ""


def auto_rename_path(path: Path) -> Path:
    if not path.exists():
        return path

    if path.is_dir():
        stem = path.name
        suffix = ""
    else:
        stem, suffix = split_name_for_conflict(path.name)

    index = 1
    while True:
        candidate = path.with_name(f"{stem} ({index}){suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def validate_url(url: str) -> str:
    trimmed = url.strip()
    parsed = urlparse(trimmed)
    if not trimmed:
        raise AppError(
            ExitCode.INVALID_URL,
            "VALIDATE_URL",
            "下载链接不能为空",
        )
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise AppError(
            ExitCode.INVALID_URL,
            "VALIDATE_URL",
            "仅支持 http:// 或 https:// 开头的有效下载链接",
        )
    return trimmed


def prompt_text(message: str) -> str:
    try:
        return console.input(message)
    except EOFError as exc:
        raise AppError(
            ExitCode.USER_CANCELLED,
            "INPUT",
            "输入已结束，任务取消",
        ) from exc


def prompt_url() -> str:
    while True:
        url = prompt_text("请输入下载链接: ").strip()
        try:
            return validate_url(url)
        except AppError as exc:
            print_error(exc.message)


def parse_content_disposition_filename(value: str | None) -> str | None:
    if not value:
        return None

    filename_star = re.search(r"filename\*\s*=\s*[^']*''([^;]+)", value, re.IGNORECASE)
    if filename_star:
        return sanitize_filename(unquote(filename_star.group(1)))

    filename_match = re.search(r'filename\s*=\s*"([^"]+)"', value, re.IGNORECASE)
    if filename_match:
        return sanitize_filename(filename_match.group(1))

    filename_match = re.search(r"filename\s*=\s*([^;]+)", value, re.IGNORECASE)
    if filename_match:
        return sanitize_filename(filename_match.group(1).strip().strip('"'))

    return None


def resolve_program_name() -> str:
    argv0 = Path(sys.argv[0]).name.strip() if sys.argv and sys.argv[0] else ""
    if argv0 in {"", "-c", "__main__.py"}:
        return "flowfetch"
    return argv0


def infer_filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    candidate = Path(unquote(parsed.path)).name
    return sanitize_filename(candidate) if candidate else "downloaded_file"


def build_metadata_from_headers(
    headers: httpx.Headers,
    final_url: str,
    filename_override: str | None,
) -> FileMeta:
    filename = filename_override or parse_content_disposition_filename(
        headers.get("Content-Disposition")
    )
    if not filename:
        filename = infer_filename_from_url(final_url)
    total_size_raw = headers.get("Content-Length")
    total_size = None
    if total_size_raw:
        try:
            parsed_size = int(total_size_raw)
            total_size = parsed_size if parsed_size >= 0 else None
        except ValueError:
            total_size = None
    return FileMeta(
        filename=sanitize_filename(filename),
        total_size=total_size,
        content_type=headers.get("Content-Type"),
        final_url=final_url,
    )


def build_httpx_timeout(config: AppConfig) -> httpx.Timeout:
    return httpx.Timeout(
        connect=config.download_timeout_connect_seconds,
        read=config.download_timeout_read_seconds,
        write=config.download_timeout_read_seconds,
        pool=config.download_timeout_connect_seconds,
    )


def fetch_file_metadata(
    url: str,
    *,
    filename_override: str | None,
    config: AppConfig,
) -> FileMeta:
    timeout = build_httpx_timeout(config)
    headers = {"User-Agent": DEFAULT_USER_AGENT}

    try:
        with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
            try:
                response = client.head(url)
                response.raise_for_status()
                return build_metadata_from_headers(
                    response.headers,
                    str(response.url),
                    filename_override,
                )
            except (httpx.HTTPError, httpx.RequestError):
                pass

            with client.stream("GET", url) as response:
                response.raise_for_status()
                return build_metadata_from_headers(
                    response.headers,
                    str(response.url),
                    filename_override,
                )
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        raise AppError(
            ExitCode.METADATA_FAILED,
            "FETCH_METADATA",
            f"获取文件信息失败: 服务器返回 {status_code}",
            suggestion="请检查下载链接是否正确，或稍后重试",
            detail=str(exc),
        ) from exc
    except httpx.TimeoutException as exc:
        raise AppError(
            ExitCode.METADATA_FAILED,
            "FETCH_METADATA",
            "获取文件信息失败: 请求超时",
            suggestion="请检查网络连接后重试",
            detail=str(exc),
        ) from exc
    except httpx.RequestError as exc:
        raise AppError(
            ExitCode.METADATA_FAILED,
            "FETCH_METADATA",
            f"获取文件信息失败: {exc}",
            suggestion="请检查网络连接和目标服务器状态",
            detail=str(exc),
        ) from exc


def build_parser() -> FlowFetchArgumentParser:
    parser = FlowFetchArgumentParser(
        prog=resolve_program_name(),
        description="FlowFetch: 面向 Linux 的终端下载与按需解压工具",
    )
    parser.add_argument("url", nargs="?", help="下载链接；不提供时进入交互模式")
    parser.add_argument(
        "-o",
        "--output-dir",
        default=".",
        help="下载目录，默认为当前目录",
    )
    parser.add_argument("--filename", help="强制指定保存文件名")
    parser.add_argument(
        "--downloader",
        choices=("auto", "httpx", "curl", "wget"),
        default="auto",
        help="指定下载器",
    )
    parser.add_argument(
        "--extractor",
        choices=("auto", "python", "system"),
        default="auto",
        help="指定解压策略",
    )

    extract_group = parser.add_mutually_exclusive_group()
    extract_group.add_argument("--extract", action="store_true", help="下载后自动解压")
    extract_group.add_argument("--no-extract", action="store_true", help="下载后跳过解压")

    conflict_group = parser.add_mutually_exclusive_group()
    conflict_group.add_argument("--overwrite", action="store_true", help="允许覆盖同名文件")
    conflict_group.add_argument("--rename", action="store_true", help="同名文件自动重命名")

    partial_group = parser.add_mutually_exclusive_group()
    partial_group.add_argument(
        "--keep-partial",
        action="store_true",
        help="下载失败时保留 .part 临时文件",
    )
    partial_group.add_argument(
        "--delete-partial",
        action="store_true",
        help="下载失败时删除 .part 临时文件",
    )

    parser.add_argument(
        "--download-threshold",
        help="下载器切换阈值，支持 1073741824 / 1g / 512m 这类格式",
    )
    parser.add_argument(
        "--extract-threshold",
        help="解压器切换阈值，支持 2147483648 / 2g 这类格式",
    )
    parser.add_argument("--retry", type=int, help="下载失败重试次数")
    parser.add_argument("--timeout", type=int, help="同时设置 connect/read 超时秒数")
    parser.add_argument("--connect-timeout", type=int, help="连接超时秒数")
    parser.add_argument("--read-timeout", type=int, help="读取超时秒数")
    parser.add_argument("--no-fallback", action="store_true", help="禁止自动回退到备选方案")
    parser.add_argument("--yes", action="store_true", help="对确认提示使用默认推荐答案")
    parser.add_argument("--verbose", action="store_true", help="输出更详细的错误信息")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    return parser


def build_config_from_args(args: argparse.Namespace) -> AppConfig:
    config = AppConfig()
    if args.download_threshold:
        config.download_switch_threshold_bytes = parse_size_value(args.download_threshold)
    if args.extract_threshold:
        config.extract_switch_threshold_bytes = parse_size_value(args.extract_threshold)
    if args.retry is not None:
        if args.retry < 1:
            raise AppError(
                ExitCode.INVALID_ARGUMENT,
                "PARSE_ARGS",
                "--retry 必须大于等于 1",
            )
        config.download_retry_count = args.retry
    if args.timeout is not None:
        if args.timeout <= 0:
            raise AppError(
                ExitCode.INVALID_ARGUMENT,
                "PARSE_ARGS",
                "--timeout 必须大于 0",
            )
        config.download_timeout_connect_seconds = args.timeout
        config.download_timeout_read_seconds = args.timeout
    if args.connect_timeout is not None:
        if args.connect_timeout <= 0:
            raise AppError(
                ExitCode.INVALID_ARGUMENT,
                "PARSE_ARGS",
                "--connect-timeout 必须大于 0",
            )
        config.download_timeout_connect_seconds = args.connect_timeout
    if args.read_timeout is not None:
        if args.read_timeout <= 0:
            raise AppError(
                ExitCode.INVALID_ARGUMENT,
                "PARSE_ARGS",
                "--read-timeout 必须大于 0",
            )
        config.download_timeout_read_seconds = args.read_timeout
    if args.no_fallback:
        config.auto_fallback_to_python = False
        config.auto_retry_with_backup_tool = False
    if args.delete_partial:
        config.keep_partial_on_failure = False
    elif args.keep_partial:
        config.keep_partial_on_failure = True
    return config


def build_run_options(args: argparse.Namespace, config: AppConfig) -> RunOptions:
    interactive = sys.stdin.isatty()
    if args.overwrite:
        conflict_policy = "overwrite"
    elif args.rename:
        conflict_policy = "rename"
    else:
        conflict_policy = "ask" if interactive else "rename"

    if args.extract:
        extract_mode = True
    elif args.no_extract:
        extract_mode = False
    else:
        extract_mode = None

    return RunOptions(
        url=args.url,
        output_dir=Path(args.output_dir).expanduser(),
        filename=sanitize_filename(args.filename) if args.filename else None,
        downloader=args.downloader,
        extractor=args.extractor,
        extract_mode=extract_mode,
        conflict_policy=conflict_policy,
        keep_partial_on_failure=config.keep_partial_on_failure,
        allow_fallback=config.auto_fallback_to_python,
        yes=args.yes,
        verbose=args.verbose,
        interactive=interactive,
    )


def ensure_output_dir(path: Path) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        raise AppError(
            ExitCode.PERMISSION_DENIED,
            "RESOLVE_PATH",
            f"无法创建输出目录: {display_path(path)}",
            suggestion="请检查目录权限或改用可写目录",
            detail=str(exc),
        ) from exc
    return path


def prompt_conflict_resolution(path: Path, *, default_choice: str) -> str:
    print_warn(f"目标已存在: {display_path(path)}")
    if default_choice == "rename":
        prompt = "请选择 [o]覆盖 / [r]重命名 / [c]取消 [默认:r]: "
    else:
        prompt = "请选择 [o]覆盖 / [r]重命名 / [c]取消 [默认:o]: "

    answer = prompt_text(prompt).strip().lower()
    if not answer:
        return default_choice
    if answer in {"o", "overwrite"}:
        return "overwrite"
    if answer in {"r", "rename"}:
        return "rename"
    if answer in {"c", "cancel"}:
        return "cancel"
    print_warn("未识别的输入，已按默认选项处理")
    return default_choice


def resolve_conflict_path(path: Path, options: RunOptions) -> Path:
    if not path.exists():
        return path

    if options.conflict_policy == "overwrite":
        return path
    if options.conflict_policy == "rename":
        return auto_rename_path(path)
    if options.yes:
        return auto_rename_path(path)
    if not options.interactive:
        return auto_rename_path(path)

    choice = prompt_conflict_resolution(path, default_choice="rename")
    if choice == "overwrite":
        return path
    if choice == "rename":
        return auto_rename_path(path)
    raise AppError(
        ExitCode.USER_CANCELLED,
        "RESOLVE_PATH",
        "用户取消了当前任务",
    )


def resolve_output_path(
    filename: str,
    output_dir: Path,
    options: RunOptions,
) -> Path:
    ensure_output_dir(output_dir)
    target = output_dir / sanitize_filename(filename)
    return resolve_conflict_path(target, options)


def resolve_temp_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.name}.part")


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def choose_system_downloader() -> str | None:
    if command_exists("curl"):
        return "curl"
    if command_exists("wget"):
        return "wget"
    return None


def choose_7z_command() -> str | None:
    for candidate in ("7z", "7zz"):
        if command_exists(candidate):
            return candidate
    return None


def render_install_help(tool: str) -> str:
    key = "7z" if tool in {"7z", "7zz"} else tool
    suggestions = SYSTEM_TOOL_SUGGESTIONS.get(key)
    if not suggestions:
        return "请安装对应系统工具后重试"
    lines = []
    for distro, command in suggestions.items():
        lines.append(f"{distro}:\n  {command}")
    return "\n".join(lines)


def print_missing_tool_message(
    *,
    tool: str,
    task_type: str,
    fallback_result: str | None,
) -> None:
    print_warn(f"当前任务更适合使用系统工具: {tool}")
    print_warn(f"系统中未找到该命令，任务类型: {task_type}")
    if fallback_result:
        print_info(f"处理结果: 已自动回退到 {fallback_result}")
    else:
        print_error("处理结果: 当前无法继续，请安装对应工具后重试")
    console.print()
    console.print(render_install_help(tool))


def confirm_python_fallback(prompt_message: str, options: RunOptions) -> bool:
    if options.yes:
        return True
    if not options.interactive:
        return False
    answer = prompt_text(f"{prompt_message} [Y/n]: ").strip().lower()
    if answer in {"", "y", "yes"}:
        return True
    if answer in {"n", "no"}:
        return False
    print_warn("未识别的输入，已按默认肯定处理")
    return True


def choose_downloader(meta: FileMeta, config: AppConfig, options: RunOptions) -> str:
    if options.downloader == "httpx":
        return "httpx"

    if options.downloader in {"curl", "wget"}:
        if command_exists(options.downloader):
            return options.downloader
        if options.allow_fallback and confirm_python_fallback(
            f"未检测到 {options.downloader}，是否回退到 httpx 下载？",
            options,
        ):
            print_warn(f"未检测到 {options.downloader}，已回退到 httpx")
            return "httpx"
        raise AppError(
            ExitCode.MISSING_SYSTEM_DOWNLOADER,
            "SELECT_DOWNLOADER",
            f"未检测到系统下载工具: {options.downloader}",
            suggestion=render_install_help(options.downloader),
        )

    if meta.total_size is not None and meta.total_size >= config.download_switch_threshold_bytes:
        system_tool = choose_system_downloader()
        if system_tool:
            print_info(f"检测到文件较大，已切换到系统下载器: {system_tool}")
            return system_tool
        print_missing_tool_message(
            tool="curl/wget",
            task_type="大文件下载",
            fallback_result="httpx 下载",
        )
    return "httpx"


def backup_downloaders(primary: str) -> list[str]:
    ordered = ["httpx", "curl", "wget"]
    return [tool for tool in ordered if tool != primary]


def validate_downloaded_file(path: Path, expected_size: int | None) -> None:
    if not path.exists():
        raise AppError(
            ExitCode.FILE_VALIDATION_FAILED,
            "VERIFY_DOWNLOAD",
            "下载结果校验失败: 文件不存在",
        )
    size = path.stat().st_size
    if size <= 0:
        raise AppError(
            ExitCode.FILE_VALIDATION_FAILED,
            "VERIFY_DOWNLOAD",
            "下载结果校验失败: 文件大小为 0",
        )
    if expected_size is not None and size != expected_size:
        raise AppError(
            ExitCode.FILE_VALIDATION_FAILED,
            "VERIFY_DOWNLOAD",
            f"下载结果校验失败: 期望 {expected_size} 字节，实际 {size} 字节",
        )


def remove_partial_if_needed(part_path: Path, keep_partial_on_failure: bool) -> None:
    if keep_partial_on_failure:
        return
    try:
        if part_path.exists():
            part_path.unlink()
    except OSError:
        pass


def download_with_httpx(
    url: str,
    part_path: Path,
    meta: FileMeta,
    config: AppConfig,
) -> None:
    if httpx is None:
        raise AppError(
            ExitCode.UNKNOWN_ERROR,
            "DOWNLOAD",
            "缺少 Python 依赖: httpx",
            suggestion="请先执行 pip install -r requirements.txt",
            detail=str(HTTPX_IMPORT_ERROR) if HTTPX_IMPORT_ERROR else None,
        )

    timeout = build_httpx_timeout(config)
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    total_size = meta.total_size

    try:
        if part_path.exists():
            part_path.unlink()
        with httpx.stream(
            "GET",
            url,
            follow_redirects=True,
            timeout=timeout,
            headers=headers,
        ) as response:
            response.raise_for_status()
            header_size = response.headers.get("Content-Length")
            if total_size is None and header_size:
                try:
                    total_size = int(header_size)
                except ValueError:
                    total_size = None

            with part_path.open("wb") as file_handle:
                if RICH_AVAILABLE and Progress is not None and sys.stdout.isatty():
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(bar_width=None),
                        TaskProgressColumn(),
                        DownloadColumn(),
                        TransferSpeedColumn(),
                        TimeRemainingColumn(),
                        console=console,
                        expand=True,
                    ) as progress:
                        task_id = progress.add_task(meta.filename, total=total_size)
                        for chunk in response.iter_bytes(config.download_chunk_size):
                            if not chunk:
                                continue
                            file_handle.write(chunk)
                            progress.update(task_id, advance=len(chunk))
                else:
                    for chunk in response.iter_bytes(config.download_chunk_size):
                        if not chunk:
                            continue
                        file_handle.write(chunk)
    except httpx.HTTPStatusError as exc:
        raise AppError(
            ExitCode.DOWNLOAD_FAILED,
            "DOWNLOAD",
            f"下载失败: 服务器返回 {exc.response.status_code}",
            suggestion="请检查链接是否有效或稍后重试",
            detail=str(exc),
        ) from exc
    except httpx.TimeoutException as exc:
        raise AppError(
            ExitCode.DOWNLOAD_FAILED,
            "DOWNLOAD",
            "下载失败: 请求超时",
            suggestion="请检查网络连接后重试",
            detail=str(exc),
        ) from exc
    except httpx.RequestError as exc:
        raise AppError(
            ExitCode.DOWNLOAD_FAILED,
            "DOWNLOAD",
            "下载失败: 网络请求发生错误",
            suggestion="请检查网络连接和目标服务器状态",
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise AppError(
            ExitCode.PERMISSION_DENIED,
            "DOWNLOAD",
            f"下载失败: 无法写入文件 {display_path(part_path)}",
            suggestion="请检查目录权限或更换输出目录",
            detail=str(exc),
        ) from exc
    except OSError as exc:
        raise AppError(
            ExitCode.DOWNLOAD_FAILED,
            "DOWNLOAD",
            "下载失败: 写文件时发生错误",
            suggestion="请检查磁盘空间和目录权限",
            detail=str(exc),
        ) from exc


def build_system_download_command(tool: str, url: str, part_path: Path) -> list[str]:
    if tool == "curl":
        return ["curl", "-L", "--fail", "--output", str(part_path), url]
    if tool == "wget":
        return ["wget", "--output-document", str(part_path), url]
    raise AppError(
        ExitCode.INVALID_ARGUMENT,
        "SELECT_DOWNLOADER",
        f"不支持的系统下载器: {tool}",
    )


def download_with_system_tool(
    url: str,
    part_path: Path,
    downloader: str,
) -> None:
    if part_path.exists():
        part_path.unlink()

    command = build_system_download_command(downloader, url, part_path)
    try:
        result = subprocess.run(command, check=False)
    except FileNotFoundError as exc:
        raise AppError(
            ExitCode.MISSING_SYSTEM_DOWNLOADER,
            "DOWNLOAD",
            f"未检测到系统下载工具: {downloader}",
            suggestion=render_install_help(downloader),
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise AppError(
            ExitCode.PERMISSION_DENIED,
            "DOWNLOAD",
            f"下载失败: 无法执行 {downloader}",
            suggestion="请检查执行权限或系统策略",
            detail=str(exc),
        ) from exc

    if result.returncode != 0:
        raise AppError(
            ExitCode.DOWNLOAD_FAILED,
            "DOWNLOAD",
            f"下载失败: {downloader} 退出码为 {result.returncode}",
            suggestion="请检查链接、网络连接或改用 httpx",
        )


def finalize_download(part_path: Path, output_path: Path, expected_size: int | None) -> Path:
    validate_downloaded_file(part_path, expected_size)
    try:
        part_path.replace(output_path)
    except PermissionError as exc:
        raise AppError(
            ExitCode.PERMISSION_DENIED,
            "VERIFY_DOWNLOAD",
            f"无法移动下载文件到最终位置: {display_path(output_path)}",
            suggestion="请检查目录权限",
            detail=str(exc),
        ) from exc
    except OSError as exc:
        raise AppError(
            ExitCode.FILE_VALIDATION_FAILED,
            "VERIFY_DOWNLOAD",
            "无法完成下载文件重命名",
            suggestion="请检查磁盘空间和目录权限",
            detail=str(exc),
        ) from exc
    return output_path


def download_file(
    url: str,
    output_path: Path,
    meta: FileMeta,
    downloader: str,
    config: AppConfig,
    options: RunOptions,
) -> Path:
    part_path = resolve_temp_path(output_path)
    last_error: AppError | None = None
    attempts_by_tool = config.download_retry_count
    candidate_tools = [downloader]
    if options.downloader == "auto" and config.auto_retry_with_backup_tool:
        candidate_tools.extend(backup_downloaders(downloader))

    for index, tool in enumerate(candidate_tools):
        if index > 0:
            print_warn(f"{candidate_tools[index - 1]} 下载失败，尝试备选下载器: {tool}")
            if tool in {"curl", "wget"} and not command_exists(tool):
                print_warn(f"未检测到备选下载器 {tool}，已跳过")
                continue

        for attempt in range(1, attempts_by_tool + 1):
            if attempts_by_tool > 1:
                print_info(f"下载尝试 {attempt}/{attempts_by_tool}，使用下载器: {tool}")
            try:
                if tool == "httpx":
                    download_with_httpx(url, part_path, meta, config)
                else:
                    download_with_system_tool(url, part_path, tool)
                return finalize_download(part_path, output_path, meta.total_size)
            except AppError as exc:
                last_error = exc
                if attempt < attempts_by_tool:
                    print_warn(f"{tool} 下载失败，准备重试: {exc.message}")
                else:
                    remove_partial_if_needed(part_path, options.keep_partial_on_failure)

    if last_error is not None:
        raise last_error
    raise AppError(
        ExitCode.DOWNLOAD_FAILED,
        "DOWNLOAD",
        "下载失败: 未找到可用的下载器",
    )


def detect_archive_type(file_path: Path) -> str | None:
    lower_name = file_path.name.lower()
    for suffix in ARCHIVE_SUFFIXES:
        if lower_name.endswith(suffix):
            return suffix.lstrip(".")

    if zipfile.is_zipfile(file_path):
        return "zip"
    try:
        if tarfile.is_tarfile(file_path):
            return "tar"
    except OSError:
        pass
    return None


def archive_base_name(file_path: Path, archive_kind: str) -> str:
    lower_name = file_path.name.lower()
    suffix = f".{archive_kind}"
    if archive_kind == "tgz":
        suffix = ".tgz"
    if lower_name.endswith(suffix):
        base = file_path.name[: -len(suffix)]
        return base or file_path.stem
    return file_path.stem


def resolve_extract_target(
    file_path: Path,
    archive_kind: str,
    options: RunOptions,
) -> Path:
    base_name = archive_base_name(file_path, archive_kind)
    if archive_kind == "gz":
        candidate = file_path.parent / sanitize_filename(base_name)
    else:
        candidate = file_path.parent / sanitize_filename(base_name)
    return resolve_conflict_path(candidate, options)


def preview_extract_target(file_path: Path, archive_kind: str) -> Path:
    base_name = archive_base_name(file_path, archive_kind)
    return file_path.parent / sanitize_filename(base_name)


def system_extractor_tool(archive_kind: str) -> str | None:
    if archive_kind == "zip":
        return "unzip"
    if archive_kind in TAR_ARCHIVES:
        return "tar"
    if archive_kind == "7z":
        return choose_7z_command()
    return None


def describe_extractor_choice(extractor: str, archive_kind: str) -> str:
    if extractor == "python":
        return "Python 标准库"
    tool = system_extractor_tool(archive_kind) or "系统工具"
    return f"系统工具 ({tool})"


def choose_extractor(
    file_path: Path,
    archive_kind: str,
    config: AppConfig,
    options: RunOptions,
) -> str:
    standard_supported = archive_kind in STANDARD_LIBRARY_ARCHIVES
    system_tool = system_extractor_tool(archive_kind)
    file_size = file_path.stat().st_size

    if options.extractor == "python":
        if not standard_supported:
            raise AppError(
                ExitCode.UNSUPPORTED_FORMAT,
                "SELECT_EXTRACTOR",
                f"当前格式无法使用 Python 标准库解压: {archive_kind}",
            )
        return "python"

    if options.extractor == "system":
        if system_tool and command_exists(system_tool):
            return "system"
        if standard_supported and options.allow_fallback and confirm_python_fallback(
            "未检测到系统解压工具，是否回退到 Python 解压？",
            options,
        ):
            print_warn("未检测到系统解压工具，已回退到 Python 解压")
            return "python"
        raise AppError(
            ExitCode.MISSING_SYSTEM_EXTRACTOR,
            "SELECT_EXTRACTOR",
            f"未检测到系统解压工具: {system_tool or archive_kind}",
            suggestion=render_install_help(system_tool or archive_kind),
        )

    if archive_kind == "7z":
        if system_tool and command_exists(system_tool):
            return "system"
        raise AppError(
            ExitCode.MISSING_SYSTEM_EXTRACTOR,
            "SELECT_EXTRACTOR",
            "当前格式需要系统解压工具 7z/7zz",
            suggestion=render_install_help("7z"),
        )

    if (
        standard_supported
        and file_size >= config.extract_switch_threshold_bytes
        and system_tool
        and command_exists(system_tool)
    ):
        print_info(f"检测到压缩包较大，已切换到系统解压器: {system_tool}")
        return "system"

    if (
        standard_supported
        and file_size >= config.extract_switch_threshold_bytes
        and system_tool
        and not command_exists(system_tool)
    ):
        print_warn(f"未检测到系统解压工具 {system_tool}，已回退到 Python 解压")

    if standard_supported:
        return "python"

    raise AppError(
        ExitCode.UNSUPPORTED_FORMAT,
        "SELECT_EXTRACTOR",
        f"当前格式不支持自动解压: {archive_kind}",
    )


def recommend_extractor(
    file_path: Path,
    archive_kind: str,
    config: AppConfig,
    options: RunOptions,
) -> str:
    if options.extractor == "python":
        return "python"
    if options.extractor == "system":
        return "system"

    standard_supported = archive_kind in STANDARD_LIBRARY_ARCHIVES
    system_tool = system_extractor_tool(archive_kind)
    file_size = file_path.stat().st_size

    if archive_kind == "7z":
        return "system"
    if (
        standard_supported
        and file_size >= config.extract_switch_threshold_bytes
        and system_tool
        and command_exists(system_tool)
    ):
        return "system"
    if standard_supported:
        return "python"
    return "system"


def should_extract_archive(
    file_path: Path,
    archive_kind: str,
    recommended_extractor: str,
    target_preview: Path,
    options: RunOptions,
    config: AppConfig,
) -> bool:
    print_info(f"检测到压缩包类型: {archive_kind}")
    print_info(f"推荐解压方式: {describe_extractor_choice(recommended_extractor, archive_kind)}")
    print_info(f"目标路径: {display_path(target_preview)}")

    if options.extract_mode is True:
        print_info("已根据参数自动执行解压")
        return True
    if options.extract_mode is False:
        print_info("已根据参数跳过解压")
        return False
    if not options.interactive:
        return config.non_interactive_default_extract
    if options.yes:
        return config.default_extract_yes

    answer = prompt_text("是否解压到当前目录？ [Y/n]: ").strip().lower()
    if answer in {"", "y", "yes"}:
        return True
    if answer in {"n", "no"}:
        return False
    print_warn("未识别的输入，已默认跳过解压")
    return False


def ensure_safe_member_path(target_dir: Path, member_name: str) -> Path:
    normalized = member_name.replace("\\", "/").lstrip("/")
    destination = (target_dir / normalized).resolve()
    target_root = target_dir.resolve()
    if destination != target_root and target_root not in destination.parents:
        raise AppError(
            ExitCode.EXTRACT_FAILED,
            "EXTRACT",
            f"检测到不安全的压缩包成员路径: {member_name}",
            suggestion="该压缩包可能存在路径穿越风险，已停止解压",
        )
    return destination


def validate_zip_members(zip_file: zipfile.ZipFile, target_dir: Path) -> None:
    for info in zip_file.infolist():
        ensure_safe_member_path(target_dir, info.filename)
        mode = info.external_attr >> 16
        if mode and (mode & 0o170000) == 0o120000:
            raise AppError(
                ExitCode.EXTRACT_FAILED,
                "EXTRACT",
                f"为保证安全，当前版本不解压链接类型成员: {info.filename}",
                suggestion="请在确认压缩包可信后手动解压",
            )


def validate_tar_members(tar_file: tarfile.TarFile, target_dir: Path) -> None:
    for member in tar_file.getmembers():
        ensure_safe_member_path(target_dir, member.name)
        if member.issym() or member.islnk():
            raise AppError(
                ExitCode.EXTRACT_FAILED,
                "EXTRACT",
                f"为保证安全，当前版本不解压链接类型成员: {member.name}",
                suggestion="请在确认压缩包可信后手动解压",
            )


def extract_with_python(file_path: Path, archive_kind: str, target_path: Path) -> Path:
    try:
        if archive_kind == "zip":
            target_path.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(file_path) as archive:
                validate_zip_members(archive, target_path)
                archive.extractall(target_path)
            return target_path

        if archive_kind in TAR_ARCHIVES:
            target_path.mkdir(parents=True, exist_ok=True)
            with tarfile.open(file_path) as archive:
                validate_tar_members(archive, target_path)
                archive.extractall(target_path)
            return target_path

        if archive_kind == "gz":
            ensure_safe_member_path(target_path.parent, target_path.name)
            with gzip.open(file_path, "rb") as source, target_path.open("wb") as target:
                shutil.copyfileobj(source, target)
            return target_path
    except AppError:
        raise
    except (tarfile.TarError, zipfile.BadZipFile, gzip.BadGzipFile, OSError) as exc:
        raise AppError(
            ExitCode.EXTRACT_FAILED,
            "EXTRACT",
            "解压失败: 无法读取或写入压缩包内容",
            suggestion="请检查压缩包是否损坏或重试下载",
            detail=str(exc),
        ) from exc

    raise AppError(
        ExitCode.UNSUPPORTED_FORMAT,
        "EXTRACT",
        f"当前格式不支持 Python 解压: {archive_kind}",
    )


def validate_7z_members(command: str, file_path: Path, target_dir: Path) -> None:
    try:
        result = subprocess.run(
            [command, "l", "-slt", str(file_path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise AppError(
            ExitCode.MISSING_SYSTEM_EXTRACTOR,
            "EXTRACT",
            f"未检测到系统解压工具: {command}",
            suggestion=render_install_help("7z"),
            detail=str(exc),
        ) from exc

    if result.returncode != 0:
        raise AppError(
            ExitCode.EXTRACT_FAILED,
            "EXTRACT",
            "无法读取 7z 文件列表",
            detail=result.stderr.strip() or result.stdout.strip() or None,
        )

    in_entries = False
    for line in result.stdout.splitlines():
        if line.strip() == "----------":
            in_entries = True
            continue
        if not in_entries:
            continue
        if line.startswith("Path = "):
            ensure_safe_member_path(target_dir, line.removeprefix("Path = ").strip())


def validate_system_extract_safety(
    file_path: Path,
    archive_kind: str,
    target_path: Path,
) -> None:
    if archive_kind == "zip":
        with zipfile.ZipFile(file_path) as archive:
            validate_zip_members(archive, target_path)
        return
    if archive_kind in TAR_ARCHIVES:
        with tarfile.open(file_path) as archive:
            validate_tar_members(archive, target_path)
        return
    if archive_kind == "7z":
        command = system_extractor_tool("7z")
        if not command:
            raise AppError(
                ExitCode.MISSING_SYSTEM_EXTRACTOR,
                "EXTRACT",
                "未检测到系统解压工具: 7z/7zz",
                suggestion=render_install_help("7z"),
            )
        validate_7z_members(command, file_path, target_path)
        return
    raise AppError(
        ExitCode.UNSUPPORTED_FORMAT,
        "EXTRACT",
        f"当前格式不支持系统解压: {archive_kind}",
    )


def build_system_extract_command(
    file_path: Path,
    archive_kind: str,
    target_path: Path,
) -> list[str]:
    tool = system_extractor_tool(archive_kind)
    if archive_kind == "zip":
        return [tool or "unzip", "-q", str(file_path), "-d", str(target_path)]
    if archive_kind in TAR_ARCHIVES:
        return [tool or "tar", "-xf", str(file_path), "-C", str(target_path)]
    if archive_kind == "7z":
        return [tool or "7z", "x", "-y", f"-o{target_path}", str(file_path)]
    raise AppError(
        ExitCode.UNSUPPORTED_FORMAT,
        "EXTRACT",
        f"当前格式不支持系统解压: {archive_kind}",
    )


def extract_with_system_tool(file_path: Path, archive_kind: str, target_path: Path) -> Path:
    if archive_kind != "gz":
        target_path.mkdir(parents=True, exist_ok=True)

    validate_system_extract_safety(file_path, archive_kind, target_path)
    command = build_system_extract_command(file_path, archive_kind, target_path)

    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        tool = system_extractor_tool(archive_kind) or archive_kind
        raise AppError(
            ExitCode.MISSING_SYSTEM_EXTRACTOR,
            "EXTRACT",
            f"未检测到系统解压工具: {tool}",
            suggestion=render_install_help(tool),
            detail=str(exc),
        ) from exc

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "未知错误"
        raise AppError(
            ExitCode.EXTRACT_FAILED,
            "EXTRACT",
            "系统解压失败",
            suggestion="请检查压缩包是否损坏，或尝试改用 Python 解压",
            detail=message,
        )
    return target_path


def extract_archive(
    file_path: Path,
    archive_kind: str,
    target_path: Path,
    extractor: str,
) -> Path:
    if extractor == "python":
        return extract_with_python(file_path, archive_kind, target_path)
    return extract_with_system_tool(file_path, archive_kind, target_path)


def print_summary(meta: FileMeta, output_path: Path, downloader: str) -> None:
    print_info(f"文件名: {meta.filename}")
    print_info(f"文件大小: {format_bytes(meta.total_size)}")
    print_info(f"保存位置: {display_path(output_path)}")
    print_info(f"已选择下载器: {downloader}")


def run() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = build_config_from_args(args)
    options = build_run_options(args, config)

    if RICH_AVAILABLE:
        console.print("[bold green]FlowFetch[/bold green]")
    else:
        console.print("FlowFetch")

    if httpx is None:
        raise AppError(
            ExitCode.UNKNOWN_ERROR,
            "INIT",
            "缺少 Python 依赖: httpx",
            suggestion="请先执行 pip install -r requirements.txt",
            detail=str(HTTPX_IMPORT_ERROR) if HTTPX_IMPORT_ERROR else None,
        )

    if options.url:
        url = validate_url(options.url)
    else:
        if not options.interactive:
            raise AppError(
                ExitCode.INVALID_ARGUMENT,
                "INPUT_URL",
                "当前为非交互模式，且未提供下载链接",
            )
        url = prompt_url()

    print_info("正在获取文件信息...")
    meta = fetch_file_metadata(
        url,
        filename_override=options.filename,
        config=config,
    )

    output_dir = ensure_output_dir(options.output_dir)
    output_path = resolve_output_path(meta.filename, output_dir, options)
    downloader = choose_downloader(meta, config, options)
    print_summary(meta, output_path, downloader)

    print_info("开始下载...")
    downloaded_file = download_file(url, output_path, meta, downloader, config, options)
    print_success(f"下载完成: {display_path(downloaded_file)}")

    archive_kind = detect_archive_type(downloaded_file)
    if not archive_kind:
        print_info("该文件不是压缩包，任务结束")
        return ExitCode.SUCCESS

    recommended_extractor = recommend_extractor(
        downloaded_file,
        archive_kind,
        config,
        options,
    )
    target_preview = preview_extract_target(downloaded_file, archive_kind)
    if not should_extract_archive(
        downloaded_file,
        archive_kind,
        recommended_extractor,
        target_preview,
        options,
        config,
    ):
        return ExitCode.SUCCESS

    selected_extractor = choose_extractor(downloaded_file, archive_kind, config, options)
    target_path = resolve_extract_target(downloaded_file, archive_kind, options)
    print_info(f"已选择解压器: {describe_extractor_choice(selected_extractor, archive_kind)}")
    print_info("正在解压...")
    extracted_path = extract_archive(
        downloaded_file,
        archive_kind,
        target_path,
        selected_extractor,
    )
    print_success(f"解压完成: {display_path(extracted_path)}")
    return ExitCode.SUCCESS


def main() -> int:
    try:
        return int(run())
    except KeyboardInterrupt:
        print_error("用户中断了当前任务")
        return int(ExitCode.USER_CANCELLED)
    except AppError as exc:
        print_error(exc.message)
        print_info(f"当前阶段: {exc.stage}")
        if exc.suggestion:
            print_info(f"建议: {exc.suggestion}")
        if exc.detail and ("--verbose" in sys.argv or "-v" in sys.argv):
            print_info(f"详细信息: {exc.detail}")
        return int(exc.code)
    except Exception as exc:  # pragma: no cover
        print_error("发生未预期错误，请使用 --verbose 查看详细信息")
        print_info("当前阶段: UNKNOWN")
        if "--verbose" in sys.argv or "-v" in sys.argv:
            print_info(f"详细信息: {exc}")
        return int(ExitCode.UNKNOWN_ERROR)


if __name__ == "__main__":
    sys.exit(main())
