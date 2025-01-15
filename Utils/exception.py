import traceback
import sys


def handle_exception(e):
    error_type = type(e).__name__
    error_message = str(e)[:3000]  # 限制错误消息的最大长度
    if trace_info := traceback.extract_tb(sys.exc_info()[2]):
        error_traceback = trace_info[-1]
        return f"ERROR:\nType: {error_type}\nMessage: {error_message}\nLine: {error_traceback.lineno}\nFile: {error_traceback.filename}\nFunction: {error_traceback.name}"
    else:
        return f"ERROR:\nType: {error_type}\nMessage: {error_message}\nTraceback: Not available"
