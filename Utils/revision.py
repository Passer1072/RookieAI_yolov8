import base64
import re
import requests
from Module.config import Root

session = requests.Session()


def get_release_version_with_date() -> tuple[str, str]:
    """
    异步获取最新的发布版本及其发布日期

    该函数通过GitHub API获取指定仓库的最新发布信息，并返回版本号和发布日期

    Returns:
        tuple: 包含版本号（tag_name）和发布日期（published_at）的元组
    """
    url = "https://api.github.com/repos/Passer1072/RookieAI_yolov8/releases/latest"
    data = session.get(url).json()
    return data["tag_name"], data["published_at"]


def get_dev_version_with_date() -> tuple[str, str | None]:
    """
    异步获取指定GitHub仓库中dev分支的版本号和最近修改日期。

    Returns:
        tuple: 包含版本号和发布日期（如果可用）的元组
    """
    owner = "Passer1072"
    repo = "RookieAI_yolov8"
    branch = "dev"
    file_path = "__version__"
    _version = "v0.0.0"
    _date = "1970-01-01 00:00:00"
    contents_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={branch}"
    data = session.get(contents_url).json()
    content = base64.b64decode(
        data.get("content", b"")).decode("utf-8").split("\n")
    Line1 = content[0].strip() if len(content) > 0 else ""
    if Line1.startswith("__version__:"):
        _version = Line1.split(":", 1)[1].strip()
    Line2 = content[1].strip() if len(content) > 1 else ""
    if Line2.startswith("__version_date__:"):
        _date = Line2.split(":", 1)[1].strip()

    return _version, _date


def get_online_announcement(
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

    contents_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={branch}"
    data = session.get(contents_url).json()
    announcement = base64.b64decode(
        data.get("content", b"")).decode("utf-8")
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


def get_local_version() -> str:
    """获取当前版本

    返回:
        str: 当前版本号
    """
    _version = "v0.0.0"
    version_file_path = Root / "__version__"
    with version_file_path.open(encoding="utf8") as version_file:
        first_line = version_file.readline().strip()
        if first_line.startswith("__version__:"):
            _version = first_line.split(":", 1)[1].strip()
    return _version


def get_local_version_with_date() -> str:
    """获取当前版本日期

    返回:
        str: 当前版本号日期
    """
    _date = "1970-01-01 00:00:00"
    version_file_path = Root / "__version__"
    with version_file_path.open(encoding="utf8") as version_file:
        first_line = version_file.readline().strip()
        if first_line.startswith("__version_date__:"):
            _date = first_line.split(":", 1)[1].strip()
    return _date


def is_dev_version() -> bool:
    """判断当前是否为开发版本
    返回:
        bool: 是否为开发版本
    """
    _version = get_local_version()
    return bool(re.search(r"-[0-9a-fA-F]{7}$", _version))


def is_internal_version() -> bool:
    """判断当前是否为内部开发版本
    返回:
        bool: 是否为内部版本
    """
    _version = get_local_version()
    return bool(re.search(r"-[0-9a-fA-F]{7}$", _version) and re.search(r"IV", _version))


def is_official_version() -> bool:
    """判断当前是否为正式版本
    返回:
        bool: 是否为正式版本
    """
    _version = get_local_version()
    return not bool(re.search(r"-[0-9a-fA-F]{7}$", _version))


def get_channel() -> str:
    """获取当前渠道
    返回:
        str: 当前渠道
    """
    if is_dev_version():
        return "预览版"
    elif is_internal_version():
        return "内部预览版"
    else:
        return "正式版"
