import traceback
import sys


def handle_exception(e):
    error_type = type(e).__name__
    error_message = str(e)[:3000]  # 限制错误消息的最大长度
    if trace_info := traceback.extract_tb(sys.exc_info()[2]):
        error_traceback = trace_info[-1]
        return (
            "ERROR:\n"
            f"Type: {error_type}\n"
            f"Message: {error_message}\n"
            f"Line: {error_traceback.lineno}\n"
            f"File: {error_traceback.filename}\n"
            f"Function: {error_traceback.name}"
        )
    else:
        return "ERROR:\n" f"Type: {error_type}\n" f"Message: {error_message}"
