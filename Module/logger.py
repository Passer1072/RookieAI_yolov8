import os
import logging
import threading
import datetime
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL  # noqa: F401
from io import StringIO
from colorama import init, Fore, Style
from Module.config import Root, Config

def get_log_level() -> int:
    """根据日志名称获取日志级别"""
    maps = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return maps.get(Config.get("log_level", "INFO").upper(), logging.INFO)

class CustomFormatter(logging.Formatter):
    def format(self, record):
        color = self._get_color(record.levelname)
        record.color = color
        return super().format(record)
    def _get_color(self, level_name):
        """根据日志级别返回相应的颜色"""
        colors = {
            "DEBUG": Fore.CYAN,
            "INFO": Fore.BLUE,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "CRITICAL": Fore.RED + Style.BRIGHT,
        }
        return colors.get(level_name, Fore.WHITE)

class logger:
    
    init(autoreset=True)

    console_log_level_int = DEBUG
    file_log_level_int = INFO
    log_file_prefix = Root / "logs"
    os.makedirs(log_file_prefix, exist_ok=True)
    logger = logging.getLogger("Custom Logger")
    logger.setLevel(get_log_level())

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_log_level_int)

    colored_formatter = CustomFormatter(
        f"{Fore.GREEN}{Style.BRIGHT}%(asctime)s{Style.RESET_ALL} "
        f"%(color)s[%(levelname)s]{Style.RESET_ALL} "
        f"{Fore.WHITE}%(message)s{Style.RESET_ALL}",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(colored_formatter)
    logger.addHandler(console_handler)

    file_handler = None
    current_log_date = None
    lock = threading.Lock()

    log_stream = StringIO()

    @classmethod
    def _ensure_log_file_created(cls):
        """确保日志文件在首次记录日志时创建，或在新的一天开始时创建新文件。"""
        today = datetime.datetime.now().date()
        if cls.file_handler is None or today != cls.current_log_date:
            with cls.lock:
                if cls.file_handler is not None and today != cls.current_log_date:
                    cls.logger.removeHandler(cls.file_handler)
                    cls.file_handler.close()

                cls.current_log_date = today
                cls.log_file = os.path.join(cls.log_file_prefix, f"{today}.log")
                cls.file_handler = logging.FileHandler(cls.log_file, encoding="utf-8")
                cls.file_handler.setLevel(cls.file_log_level_int)
                cls.file_handler.setFormatter(
                    logging.Formatter(
                        "%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S",
                    )
                )
                cls.logger.addHandler(cls.file_handler)

    @classmethod
    def _format_message(cls, *args):
        return " ".join(str(arg) for arg in args)

    @classmethod
    def debug(cls, *args) -> None:
        cls._ensure_log_file_created()
        with cls.lock:
            cls.logger.debug(cls._format_message(*args))

    @classmethod
    def info(cls, *args) -> None:
        cls._ensure_log_file_created()
        with cls.lock:
            cls.logger.info(cls._format_message(*args))

    @classmethod
    def warning(cls, *args) -> None:
        cls._ensure_log_file_created()
        with cls.lock:
            cls.logger.warning(cls._format_message(*args))


    @classmethod
    def warn(cls, *args) -> None:
        cls.warning(*args)

    @classmethod
    def error(cls, *args) -> None:
        cls._ensure_log_file_created()
        with cls.lock:
            cls.logger.error(cls._format_message(*args))

    @classmethod
    def critical(cls, *args) -> None:
        cls._ensure_log_file_created()
        with cls.lock:
            cls.logger.critical(cls._format_message(*args))
    @classmethod
    def fatal(cls, *args) -> None:
        cls.critical(*args)
    @classmethod
    def _generate_log_output(cls):
        """生成器函数，用于生成日志输出。"""
        while True:
            if log_content := cls.log_stream.getvalue():
                cls.log_stream.seek(0)
                cls.log_stream.truncate(0)  # 清空日志缓冲区
                yield log_content
            else:
                yield ""
