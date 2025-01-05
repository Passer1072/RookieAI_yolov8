import os
import logging
import threading
import datetime
import sys
from pathlib import Path
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL  # noqa: F401
from io import StringIO
from colorama import init, Fore, Style

Root = Path(os.path.realpath(sys.argv[0])).parent


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


class _Logger:
    def __init__(
        self,
        log_file_prefix=Root / "logs",
    ):
        init(autoreset=True)

        console_log_level_int = DEBUG
        self.file_log_level_int = INFO
        os.makedirs(log_file_prefix, exist_ok=True)
        self.log_file_prefix = log_file_prefix
        self.logger = logging.getLogger("Custom Logger")
        self.logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_log_level_int)

        colored_formatter = CustomFormatter(
            f"{Fore.GREEN}{Style.BRIGHT}%(asctime)s{Style.RESET_ALL} "
            f"%(color)s[%(levelname)s]{Style.RESET_ALL} "
            f"{Fore.WHITE}%(message)s{Style.RESET_ALL}",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(colored_formatter)
        self.logger.addHandler(console_handler)

        self.file_handler = None
        self.current_log_date = None
        self.lock = threading.Lock()

        self.log_stream = StringIO()

    def _ensure_log_file_created(self):
        """确保日志文件在首次记录日志时创建，或在新的一天开始时创建新文件。"""
        today = datetime.datetime.now().date()
        if self.file_handler is None or today != self.current_log_date:
            with self.lock:
                if self.file_handler is not None and today != self.current_log_date:
                    self.logger.removeHandler(self.file_handler)
                    self.file_handler.close()

                self.current_log_date = today
                self.log_file = os.path.join(self.log_file_prefix, f"{today}.log")
                self.file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
                self.file_handler.setLevel(self.file_log_level_int)
                self.file_handler.setFormatter(
                    logging.Formatter(
                        "%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S",
                    )
                )
                self.logger.addHandler(self.file_handler)

    def _format_message(self, *args):
        return " ".join(str(arg) for arg in args)

    def debug(self, *args) -> None:
        self._ensure_log_file_created()
        with self.lock:
            self.logger.debug(self._format_message(*args))

    def info(self, *args) -> None:
        self._ensure_log_file_created()
        with self.lock:
            self.logger.info(self._format_message(*args))

    def warning(self, *args) -> None:
        self._ensure_log_file_created()
        with self.lock:
            self.logger.warning(self._format_message(*args))

    def warn(self, *args) -> None:
        self.warning(*args)

    def error(self, *args) -> None:
        self._ensure_log_file_created()
        with self.lock:
            self.logger.error(self._format_message(*args))

    def critical(self, *args) -> None:
        self._ensure_log_file_created()
        with self.lock:
            self.logger.critical(self._format_message(*args))

    def fatal(self, *args) -> None:
        self.critical(*args)

    def _generate_log_output(self):
        """生成器函数，用于生成日志输出。"""
        while True:
            if log_content := self.log_stream.getvalue():
                self.log_stream.seek(0)
                self.log_stream.truncate(0)  # 清空日志缓冲区
                yield log_content
            else:
                yield ""


logger = _Logger()
