import pyautogui
import numpy as np
from ultralytics import YOLO
import cv2
import time
from mss import mss
import pygetwindow as gw
import gc
from math import sqrt

###------------------------------------------全局变量---------------------------------------------------------------------

# 加载模型
model = YOLO('yolov8n.pt')

# 新建一个 MSS 对象（获取截图）
sct = mss()

# 初始化帧数计时器（帧数计算）
frame_counter = 0
start_time = time.time()

# 新增初始化gc计时器（垃圾清理）
gc_time = time.time()


###------------------------------------------def部分---------------------------------------------------------------------

def calculate_screen_monitor(capture_width=640, capture_height=640):  # 截图区域
    # 获取屏幕的宽度和高度
    screen_width, screen_height = pyautogui.size()

    # 计算中心点坐标
    center_x, center_y = screen_width // 2, screen_height // 2

    # 定义截图区域，以中心点为基准，截取一个 capture_width x capture_height 的区域
    monitor = {
        "top": center_y - capture_height // 2,
        "left": center_x - capture_width // 2,
        "width": capture_width,
        "height": capture_height,
    }
    return monitor

def calculate_frame_rate(frame_counter, start_time, end_time):  # 帧率计算
    # 避免被零除
    if end_time - start_time != 0:
        frame_rate = frame_counter / (end_time - start_time)
        # 重置下一秒的frame_counter和start_time
        frame_counter = 0
        start_time = time.time()
    else:
        frame_rate = 0  # Or assign something that makes sense in your case
    return frame_rate, frame_counter, start_time

def update_and_display_fps(frame_, frame_counter, start_time, end_time):  # 更新和显示帧率
    frame_counter += 1
    frame_rate, frame_counter, start_time = calculate_frame_rate(frame_counter, start_time, end_time)
    cv2.putText(frame_, f"FPS: {frame_rate:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    return frame_, frame_counter, start_time

def capture_screen(monitor, sct):  # mss截图方式
    # 使用 MSS 来抓取屏幕
    screenshot = sct.grab(monitor)
    # 把 PIL/Pillow Image 转为 OpenCV ndarray 对象，然后从 BGR 转换为 RGB
    frame = np.array(screenshot)[:, :, :3]
    return frame

def capture_screenshot(region):  # pyautogui截图方式
    img = pyautogui.screenshot(region=region)
    frame = np.array(img)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    return frame

def get_window_position(title):  # 通过窗口名称获取窗口
    try:
        window = gw.getWindowsWithTitle(title)[0]
        return window.left, window.top, window.width, window.height
    except IndexError:
        print(f"No window with title '{title}' found")
        return None

def display_debug_window(frame):  # 调试窗口
    # 在主循环中显示图像
    cv2.imshow('frame', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        cv2.destroyAllWindows()
        return True
    else:
        return False


def calculate_distances(monitor, results, frame_):  # 目标选择逻辑与标识
    minDist = float('inf')  # 初始最小距离设置为无限大
    minBox = None  # 初始最小框设置为None

    for r in results:
        boxes = r.boxes.xyxy.cpu().numpy()

    for box in boxes:
        x1, y1, x2, y2 = box

        centerx = (x1 + x2) / 2
        centery = (y1 + y2) / 2

        cWidth = monitor["width"] / 2
        cHeight = monitor["height"] / 2

        dist = sqrt((cWidth - centerx) ** 2 + (cHeight - centery) ** 2)
        dist = round(dist, 1)

        # 比较当前距离和最小距离
        if dist < minDist:
            minDist = dist  # 更新最小距离
            minBox = box  # 更新对应最小距离的框

        location = (int(centerx), int(centery))
        cv2.putText(frame_, f'dist: {dist}', location, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # 检查最小距离和最小框是否已更新
    if minBox is not None:
        cv2.rectangle(frame_, (int(minBox[0]), int(minBox[1])), (int(minBox[2]), int(minBox[3])), (0, 255, 0), 2)
        center_text_x = int((minBox[0] + minBox[2]) / 2)
        center_text_y = int((minBox[1] + minBox[3]) / 2)
        location = (center_text_x, center_text_y)
        cv2.putText(frame_, f'dist: {minDist}', location, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    return frame_
### ---------------------------------------main--------------------------------------------------------------------------

# 截图区域大小
monitor = calculate_screen_monitor(640, 640)  # 在这里修改截图区域大小

# 创建窗口并设置 flag 为 cv2.WINDOW_NORMAL
cv2.namedWindow('frame', cv2.WINDOW_NORMAL)
# 在主循环中显示图像之前，设置窗口属性
cv2.setWindowProperty('frame', cv2.WND_PROP_TOPMOST, 1)

# 循环捕捉屏幕
while True:
    # 截图方式
    frame = capture_screen(monitor, sct)  # mss截图方式
    # # 通过窗口名称获取窗口
    # region = get_window_position("任务管理器")
    # monitor = {"top": region[1], "left": region[0], "width": region[2], "height": region[3]}
    # frame = capture_screen(monitor, sct)

    # 检测和跟踪对象（推理部分）
    results = model.predict(frame, save=False, imgsz=320, conf=0.65)

    # 绘制结果
    frame_ = results[0].plot()
    # 计算距离 并 将最近的目标绘制为绿色边框
    frame_ = calculate_distances(monitor, results, frame_)



    # 获取并显示帧率
    end_time = time.time()
    frame_, frame_counter, start_time = update_and_display_fps(frame_, frame_counter, start_time, end_time)

    # 调试窗口
    should_break = display_debug_window(frame_)
    if should_break:
        break

    # 每秒进行一次gc
    if time.time() - gc_time >= 1:
        gc.collect()
        gc_time = time.time()