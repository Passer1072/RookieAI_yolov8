import aiohttp
import base64
import re
from utils.config import Root


async def get_release_version_with_date() -> tuple[str, str]:
    """
    异步获取最新的发布版本及其发布日期

    该函数通过GitHub API获取指定仓库的最新发布信息，并返回版本号和发布日期

    Returns:
        tuple: 包含版本号（tag_name）和发布日期（published_at）的元组
    """
    url = "https://api.github.com/repos/Passer1072/RookieAI_yolov8/releases/latest"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            return data["tag_name"], data["published_at"]


async def get_dev_version_with_date() -> tuple[str, str | None]:
    """
    异步获取指定GitHub仓库中dev分支的版本号和__version__.py文件的最近修改日期。

    Returns:
        tuple: 包含版本号和发布日期（如果可用）的元组
    """
    owner = "Passer1072"
    repo = "RookieAI_yolov8"
    branch = "dev"
    file_path = "utils/__version__.py"

    async with aiohttp.ClientSession() as session:
        contents_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={branch}"
        async with session.get(contents_url) as response:
            data = await response.json()
            version_content = base64.b64decode(data.get("content", b"")).decode("utf-8")

        version = version_content.split(":")[-1].strip()

        commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits?path={file_path}&sha={branch}"
        async with session.get(commits_url) as response:
            commits_data = await response.json()
            if commits_data:
                last_commit = commits_data[0]
                last_modified_date = last_commit["commit"]["committer"]["date"]
            else:
                last_modified_date = None

    return version, last_modified_date


async def get_dev_version_without_date() -> str:
    """
    异步获取指定仓库的开发版本号（不包含日期）。

    通过GitHub API获取指定文件内容，并解析出版本号。

    Returns:
        str: 仓库的开发版本号（不包含日期）。
    """
    owner = "Passer1072"
    repo = "RookieAI_yolov8"
    branch = "dev"
    file_path = "utils/__version__.py"

    async with aiohttp.ClientSession() as session:
        contents_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={branch}"
        async with session.get(contents_url) as response:
            data = await response.json()
            version_content = base64.b64decode(data.get("content", b"")).decode("utf-8")

        version = version_content.split(":")[-1].strip()

    return version


async def get_online_announcement(
    parse_announcement2json: bool = False,
) -> dict[str, str] | str:
    """
    异步获取在线公告。

    通过GitHub API获取指定仓库中的公告文件内容。
    公告文件是Markdown格式，需要使用base64解码后转换为字符串。

    备注：QT提供支持Markdown语法的WebView组件，建议直接渲染markdown格式的公告内容到WebView。

    Returns:
        str: 公告内容字符串
    """
    owner = "Passer1072"
    repo = "RookieAI_yolov8"
    branch = "dev"
    file_path = "Announcement.md"

    async with aiohttp.ClientSession() as session:
        contents_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={branch}"
        async with session.get(contents_url) as response:
            data = await response.json()
            announcement = base64.b64decode(data.get("content", b"")).decode("utf-8")
    if parse_announcement2json:
        published_at_match = re.search(
            r"\$\[(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\]\$", announcement
        )
        if not published_at_match:
            raise ValueError("无法找到发布时间")

        # 提取发布时间
        published_at = published_at_match[1]

        # 去掉发布时间标记，提取内容
        content = re.sub(
            r"\$\[\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\]\$", "", announcement
        ).strip()

        return {"published_at": published_at, "content": content}
    return announcement


async def get_local_version() -> str:
    """获取当前版本

    返回:
        str: 当前版本号
    """
    _version = "v0.0.0"
    if (Root / "__version__").exists():
        if text := (Root / "__version__").open(encoding="utf8").readline():
            _version = text.split(":")[-1].strip()
    return _version


async def is_dev_version() -> bool:
    """判断当前是否为开发版本
    返回:
        bool: 是否为开发版本
    """
    _version = await get_local_version()
    return bool(re.search(r"-[0-9a-fA-F]{7}$", _version))


async def is_internal_version_dev_version() -> bool:
    """判断当前是否为内部开发版本
    返回:
        bool: 是否为内部开发版本
    """
    _version = await get_local_version()
    return bool(re.search(r"-[0-9a-fA-F]{7}$", _version) and re.search(r"IV", _version))


async def is_official_version() -> bool:
    """判断当前是否为正式版本
    返回:
        bool: 是否为正式版本
    """
    _version = await get_local_version()
    return not bool(re.search(r"-[0-9a-fA-F]{7}$", _version))
