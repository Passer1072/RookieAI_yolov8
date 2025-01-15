import ctypes
from ctypes import wintypes
import math

# 定义Windows API结构和函数
user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

# 定义需要的Windows API
EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
GetWindowDC = user32.GetWindowDC
ReleaseDC = user32.ReleaseDC
MoveToEx = gdi32.MoveToEx
LineTo = gdi32.LineTo
CreatePen = gdi32.CreatePen
SelectObject = gdi32.SelectObject
DeleteObject = gdi32.DeleteObject
GetWindowRect = user32.GetWindowRect
Ellipse = gdi32.Ellipse
Rectangle = gdi32.Rectangle

# 设置函数参数类型和返回值类型
GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
GetWindowRect.restype = wintypes.BOOL
MoveToEx.argtypes = [
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.POINTER(wintypes.POINT),
]
MoveToEx.restype = wintypes.BOOL
LineTo.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
LineTo.restype = wintypes.BOOL
CreatePen.argtypes = [wintypes.UINT, wintypes.UINT, wintypes.COLORREF]
CreatePen.restype = wintypes.HGDIOBJ
SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
SelectObject.restype = wintypes.HGDIOBJ
DeleteObject.argtypes = [wintypes.HGDIOBJ]
DeleteObject.restype = wintypes.BOOL
Ellipse.argtypes = [
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
]
Ellipse.restype = wintypes.BOOL
Rectangle.argtypes = [
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
]
Rectangle.restype = wintypes.BOOL

# 定义颜色和线条样式
PS_SOLID = 0x00000000
COLOR_BLUE = 0x000000FF
COLOR_RED = 0x00FF0000
COLOR_GREEN = 0x0000FF00
COLOR_YELLOW = 0x00FFFF00
COLOR_WHITE = 0x00FFFFFF


# 枚举窗口的回调函数
def callback(hwnd, lParam):
    rect = wintypes.RECT()
    GetWindowRect(hwnd, ctypes.byref(rect))
    if rect.left == 0 and rect.top == 0:
        ctypes.cast(lParam, ctypes.POINTER(wintypes.HWND)).contents.value = hwnd
        return False
    return True


# 获取桌面窗口句柄
def get_desktop_window():
    hwnd = wintypes.HWND()
    EnumWindows(EnumWindowsProc(callback), ctypes.byref(hwnd))
    return hwnd


# 创建一个笔
def create_pen(color, width):
    return CreatePen(PS_SOLID, width, color)


# 绘制矩形
def draw_rectangle(hdc, x1, y1, x2, y2, color, width):
    pen = create_pen(color, width)
    old_pen = SelectObject(hdc, pen)
    Rectangle(hdc, x1, y1, x2, y2)
    SelectObject(hdc, old_pen)
    DeleteObject(pen)


# 绘制圆形
def draw_circle(hdc, center_x, center_y, radius, color, width):
    pen = create_pen(color, width)
    old_pen = SelectObject(hdc, pen)
    left = center_x - radius
    top = center_y - radius
    right = center_x + radius
    bottom = center_y + radius
    Ellipse(hdc, left, top, right, bottom)
    SelectObject(hdc, old_pen)
    DeleteObject(pen)


# 绘制直线
def draw_line(hdc, x1, y1, x2, y2, color, width):
    pen = create_pen(color, width)
    old_pen = SelectObject(hdc, pen)
    MoveToEx(hdc, x1, y1, None)
    LineTo(hdc, x2, y2)
    SelectObject(hdc, old_pen)
    DeleteObject(pen)


# 绘制文本
# 绘制文本
def draw_text(hdc, text, x, y, color, font_size=16):
    """
    在指定位置和颜色下绘制文本。

    **参数**:
    
    - hdc: 设备上下文句柄。
    - text: 要绘制的文本内容。
    - x: 文本的起始x坐标。
    - y: 文本的起始y坐标。
    - color: 文本颜色(COLORREF)(Windows API颜色值)
    - font_size: 字体大小，默认为16点。
    """
    hfont = gdi32.CreateFontA(
        -font_size, 0, 0, 0, 400, 0, 0, 0, 0, 0, 0, 0, 0, b"Arial"
    )
    old_font = SelectObject(hdc, hfont)

    old_color = gdi32.SetTextColor(hdc, color)

    gdi32.TextOutA(hdc, x, y, text.encode("utf-8"), len(text))

    gdi32.SetTextColor(hdc, old_color)
    SelectObject(hdc, old_font)
    gdi32.DeleteObject(hfont)


# 主函数，用于绘制检测结果
def draw_detections(detections, frame_center, aim_range):
    desktop_hwnd = get_desktop_window()
    desktop_dc = GetWindowDC(desktop_hwnd)

    # 绘制一个淡蓝色的细圆（瞄准范围）
    circle_color = COLOR_WHITE  # 淡蓝色
    draw_circle(
        desktop_dc, frame_center[0], frame_center[1], aim_range, circle_color, 1
    )

    for detection in detections:
        x1, y1, x2, y2 = detection
        box_center = ((x1 + x2) // 2, (y1 + y2) // 2)

        # 默认所有框使用黄色连接线
        box_color = COLOR_YELLOW  # 黄色边框
        line_color = COLOR_YELLOW  # 黄色连接线

        # 绘制矩形框
        draw_rectangle(desktop_dc, x1, y1, x2, y2, box_color, 2)
        # 绘制中心点
        draw_circle(desktop_dc, box_center[0], box_center[1], 5, COLOR_RED, -1)
        # 绘制连接线条
        draw_line(
            desktop_dc,
            box_center[0],
            box_center[1],
            frame_center[0],
            frame_center[1],
            line_color,
            2,
        )

        # 计算距离
        distance = math.sqrt(
            (box_center[0] - frame_center[0]) ** 2
            + (box_center[1] - frame_center[1]) ** 2
        )
        # 绘制距离文本
        distance_text = f"{distance:.1f}px"
        draw_text(desktop_dc, distance_text, x1, y1 - 10, COLOR_BLUE, 16)

    # 如果有最近的 Box，再绘制其绿色框和红色连接线（覆盖上一步绘制）
    if detections:
        closest_box = detections[0]
        x1, y1, x2, y2 = closest_box
        box_center = ((x1 + x2) // 2, (y1 + y2) // 2)
        closest_distance = math.sqrt(
            (box_center[0] - frame_center[0]) ** 2
            + (box_center[1] - frame_center[1]) ** 2
        )

        # 只有当距离小于 aim_range 时，才绘制绿色框和红色连接线
        if closest_distance < aim_range:
            # 绘制最近的框的绿色边框
            draw_rectangle(desktop_dc, x1, y1, x2, y2, COLOR_GREEN, 3)
            # 绘制中心点
            draw_circle(desktop_dc, box_center[0], box_center[1], 5, COLOR_GREEN, -1)
            # 绘制红色连接线
            draw_line(
                desktop_dc,
                box_center[0],
                box_center[1],
                frame_center[0],
                frame_center[1],
                COLOR_RED,
                3,
            )

    # 释放设备上下文句柄
    release_dc(desktop_hwnd, desktop_dc)


def release_dc(desktop_hwnd, desktop_dc):
    """释放设备上下文句柄"""
    ReleaseDC(desktop_hwnd, desktop_dc)
