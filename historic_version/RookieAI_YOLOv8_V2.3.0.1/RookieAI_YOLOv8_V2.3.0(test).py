import gc
import json
import os
import threading
import time
import sys
import requests
import tkinter as tk
import webbrowser
import dxcam
import bettercam
import psutil
from math import sqrt
from tkinter import filedialog
from PIL import Image, ImageTk
from multiprocessing import Process, freeze_support
from tkinter import ttk

import cv2
import numpy as np
import pyautogui
import win32api
import win32con
import customtkinter as ctk
from mss import mss
from ultralytics import YOLO

###------------------------------------------全局变量---------------------------------------------------------------------

# 选择模型
model_file = "yolov8n.pt"

# 新建一个 MSS 对象（获取截图）
sct = mss()

# returns a DXCamera instance on primary monitor
# camera = dxcam.create(output_idx=0, output_color="BGR", max_buffer_len=2048)  # returns a DXCamera instance on primary monitor
camera = bettercam.create(output_idx=0, output_color="BGR", max_buffer_len=2048)  # Primary monitor's BetterCam instance

# 截图模式（请勿更改）
screenshot_mode = None

# MSS默认截图长宽(像素)
screen_width = 640
screen_height = 640

# DXcam截图分辨率
DXcam_screenshot = 360

# 初始化帧数计时器（帧数计算）
frame_counter = 0
start_time = time.time()
start_test_time = time.time()

# 新增初始化gc计时器（垃圾清理）
gc_time = time.time()

# DXcam最大FPS
dxcam_maxFPS = 30

# 自瞄范围
closest_mouse_dist = 100

# 置信度设置
confidence = 0.65

# 垂直瞄准偏移
aimOffset = 0.5

# 预测因子
prediction_factor = 0.1

# 定义额外的像素偏移量
extra_offset_x = 5  # 额外向x方向移动5个像素
extra_offset_y = 5  # 额外向y方向移动10个像素

# 软件页面大小
_win_width = 350
_win_height = 500

# 识别对象限制（敌我识别）
classes = 0

# 分阶段瞄准
stage1_scope = 50  # 强锁范围
stage1_intensity = 0.8  #强锁力度
stage2_scope = 170  # 软锁范围
stage2_intensity = 0.4  #软锁力度

# 分段瞄准开关
segmented_aiming_switch = False

# 是否开启外部测试窗口（小幅影响性能）
test_window_frame = False

# 是否打开内部测试画面（大幅影响性能）
test_images_GUI = False

# 是否跳过公告获取
crawl_information = False

# 初始化加载成功标识
loaded_successfully = False

# 目标列表
target_mapping = {'敌人': 0, '倒地': 1, '队友': 2}

# 人体示意图
img = Image.open("body_photo.png")

# 定义触发器类型和其他参数
# 在全局范围声明 GUI 控件的变量
aimbot_var = None
circle_var = None
lockSpeed_scale = None
triggerType_var = None
arduinoMode_var = None
lockKey_var = None
confidence_scale = None
closest_mouse_dist_scale = None
screen_width_scale = None
screen_height_scale = None
root = None
aimOffset_scale = None
mouse_Side_Button_Witch_var = None
value_label = None
LookSpeed_label_text = None
target_selection = None
target_selection_var = None
target_selection_str = None
method_of_prediction_var = None
readme_content = ""


# 其他全局变量
Thread_to_join = None
restart_thread = False
run_threads = True
draw_center = True


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


def update_and_display_fps(frame_, frame_counter, start_time, end_time):
    frame_counter += 1
    frame_rate, frame_counter, start_time = calculate_frame_rate(frame_counter, start_time, end_time)

    # 在 cv2 窗口中继续显示帧率
    cv2.putText(frame_, f"FPS: {frame_rate:.0f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # 在图形用户界面上显示帧率
    text_fps = "实时FPS：{:.0f}".format(frame_rate)
    image_label_FPSlabel.configure(text=text_fps)
    print(f"FPS: {frame_rate:.0f}")  # 在控制台打印帧率（如果需要的话）

    return frame_, frame_counter, start_time


def capture_screen(monitor, sct):  # mss截图方式
    # 使用 MSS 来抓取屏幕
    screenshot = sct.grab(monitor)
    # 把 PIL/Pillow Image 转为 OpenCV ndarray 对象，然后从 BGR 转换为 RGB
    frame = np.array(screenshot)[:, :, :3]

    return frame


def DXcam():
    # 获取屏幕的宽度和高度
    screen_width, screen_height = pyautogui.size()

    # 计算截图区域
    left, top = (screen_width - DXcam_screenshot) // 2, (screen_height - DXcam_screenshot) // 2
    right, bottom = left + DXcam_screenshot, top + DXcam_screenshot
    region = (left, top, right, bottom)

    camera.start(region=region, video_mode=True, target_fps=dxcam_maxFPS)  # Optional argument to capture a region


def display_debug_window(frame):  # 调试窗口
    # 在主循环中显示图像
    cv2.imshow('frame', frame)

    if cv2.waitKey(1) & 0xFF == ord('.'):
        cv2.destroyAllWindows()
        return True
    else:
        return False


def get_desired_size(screen_width_1, screen_height_1):
    # 根据屏幕尺寸判断调整的大小
    if screen_width_1 == 1920 and screen_height_1 == 1080:
        desired_size = (300, 300)
    elif screen_width_1 >= 2560 and screen_height_1 >= 1440:
        desired_size = (370, 370)
    else:
        desired_size = (300, 300)  # 默认大小

    return desired_size


def fetch_readme():  # 从github更新公告
    print("开始获取公告......")
    try:
        readme_url = "https://raw.githubusercontent.com/Passer1072/RookieAI_yolov8/master/README.md"
        response = requests.get(readme_url, timeout=10)
        response_text = response.text
        print("获取成功")

        # 找到 "更新日志：" 在字符串中的位置
        update_log_start = response_text.find("更新日志：")

        # 若找不到 "更新日志："，则返回全部内容
        if update_log_start == -1:
            return response_text

        # 截取 "更新日志：" 及其后的所有文本
        update_log = response_text[update_log_start:]
        return update_log

    except Exception as e:
        print("获取失败：", e)
        return "无法加载最新的 README 文件，这可能是因为网络问题或其他未知错误。"


def fetch_readme_version_number():  # 从github更新公告
    print("开始获取版本号......")
    try:
        readme_url = "https://raw.githubusercontent.com/Passer1072/RookieAI_yolov8/master/README.md"
        response = requests.get(readme_url)
        response_text = response.text
        print("获取成功")

        # 创建搜索字符串
        search_str = "Current latest version: "

        # 找到 "更新日志：" 在字符串中的位置
        update_log_start = response_text.find(search_str)

        # 若找不到 "Current latest version: "，则返回全部内容
        if update_log_start == -1:
            return response_text

        # 截取 "Current latest version: " 及其后的所有文本
        update_log_start += len(search_str)  # Move the index to the end of "Current latest version: "
        update_log = response_text[update_log_start:]

        # 使用 strip 方法去除两侧空格
        update_log = update_log.strip()

        return update_log

    except Exception as e:
        print("获取失败：", e)
        return "版本号获取失败"


def crawl_information_by_github():
    global readme_content, readme_version
    if crawl_information:
        # 读取在线公告
        readme_content = fetch_readme()
        readme_version = fetch_readme_version_number()

def open_web(event):
    webbrowser.open('https://github.com/Passer1072/RookieAI_yolov8')  # 要跳转的网页


def choose_model():  # 选择模型
    global model_file
    model_file = filedialog.askopenfilename()  # 在这里让用户选择文件
    model_file_label.config(text=model_file)  # 更新标签上的文本为选择的文件路径

def open_settings_config():
    os.startfile("settings.json")

def load_model_file():  # 加载模型文件
    # 默认的模型文件地址
    default_model_file = "yolov8n.pt"
    try:
        with open('settings.json', 'r') as f:
            settings = json.load(f)
            model_file = settings.get('model_file', default_model_file)
            # 检查文件是否存在，如果不存在，使用默认模型文件
            if not os.path.isfile(model_file):
                print("[WARNING] 设置文件中的模型文件路径无效; 使用默认模型文件")
                model_file = default_model_file
    except FileNotFoundError:
        print("[WARNING] 没有找到设置文件; 使用默认模型文件")
        model_file = default_model_file

    print("加载模型文件:", model_file)
    # 如果 model_file 为 None或者空，我们返回None，否则我们返回对应的 YOLO 模型
    return YOLO(model_file) if model_file else None


def create_gui_tkinter():  # 软件主题GUI界面
    global aimbot_var, lockSpeed_scale, triggerType_var, arduinoMode_var, lockKey_var, confidence_scale \
        , closest_mouse_dist_scale, screen_width_scale, screen_height_scale, root, model_file, model_file_label, aimOffset_scale \
        , draw_center_var, mouse_Side_Button_Witch_var, LookSpeed_label_text, lockSpeed_variable, confidence_variable \
        , closest_mouse_dist_variable, aimOffset_variable, screen_width_scale_variable, screen_height_scale_variable \
        , image_label, image_label_switch, image_label_FPSlabel, target_selection_var, target_mapping, prediction_factor_variable \
        , prediction_factor_scale, method_of_prediction_var, extra_offset_x_scale, extra_offset_y_scale, extra_offset_y \
        , extra_offset_x, extra_offset_x_variable, extra_offset_y_variable, readme_content


    # 版本号
    version_number = "V2.3(test)"
    # 使用customtkinter创建根窗口
    root = ctk.CTk()
    # ctk.set_appearance_mode("system")  # default
    ctk.set_appearance_mode("dark")
    # 在启动页面结束前隐藏主窗口
    root.withdraw()
    # 创建一个启动画面窗口
    top = tk.Toplevel(root)
    top.title("启动中")
    logo_file = "logo-bird.png"  # 您的LOGO文件路径
    photo = tk.PhotoImage(file=logo_file)
    label = tk.Label(top, image=photo)
    label.pack()

    # 在1秒后关闭启动画面窗口并显示主窗口
    def end_splash():
        top.destroy()
        root.deiconify()  # 显示主窗口

    root.after(2000, end_splash)  # 1秒后运行

    root.title("RookieAI")  # 软件名称

    root.geometry(f"{_win_width}x{_win_height}")

    # 设置当用户点击窗口的关闭按钮时要做的操作
    root.protocol("WM_DELETE_WINDOW", stop_program)  # 将WM_DELETE_WINDOW的默认操作设置为 _on_closing 函数

    # 禁止窗口大小调整
    root.resizable(False, True)

    # 实例化 CTkTabview 对象
    tab_view = ctk.CTkTabview(root, width=320, height=355)
    # 创建选项卡
    tab_view.add("基础设置")
    tab_view.add("高级设置")
    tab_view.add("其他设置")
    tab_view.add("测试窗口")

    # 将 CTkTabview 对象添加到主窗口
    tab_view.grid(row=0, column=0, padx=(15, 0), pady=(0, 0))

    # 创建一个Frame来包含aimbot开关和其左边的显示瞄准范围
    aimbot_draw_center_frame = ctk.CTkFrame(tab_view.tab("基础设置"))
    aimbot_draw_center_frame.grid(row=0, column=0, sticky='w', pady=5)  # 使用grid布局并靠左对齐
    # 创建一个名为 'Aimbot' 的复选框
    aimbot_var = ctk.BooleanVar(value=aimbot)
    aimbot_check = ctk.CTkCheckBox(aimbot_draw_center_frame, text='Aimbot', variable=aimbot_var,
                                   command=update_values, )
    aimbot_check.grid(row=0, column=0)  # 使用grid布局并靠左对齐
    # 是否显示瞄准范围的开关
    draw_center_var = ctk.BooleanVar(value=False)  # 默认值为False
    draw_center_check = ctk.CTkCheckBox(aimbot_draw_center_frame, text='显示瞄准范围(测试用)', variable=draw_center_var,
                                        command=update_values)
    draw_center_check.grid(row=0, column=1)

    # 创建一个Frame来包含arduinoMode开关和其左边的显示瞄准范围
    arduinoMode_frame = ctk.CTkFrame(tab_view.tab("基础设置"))
    arduinoMode_frame.grid(row=1, column=0, sticky='w', pady=5)  # 使用grid布局并靠左对齐
    # 创建一个名为 'Arduino Mode(未启用)' 的复选框
    arduinoMode_var = ctk.BooleanVar(value=arduinoMode)
    arduinoMode_check = ctk.CTkCheckBox(arduinoMode_frame, text='Arduino Mode(待开发)', variable=arduinoMode_var,
                                        command=update_values, state="DISABLED")
    arduinoMode_check.grid(row=0, column=0, sticky="w", pady=(0, 0))  # 使用grid布局并靠左对齐

    triggerType_var = tk.StringVar(value=triggerType)
    # 创建一个Frame来包含OptionMenu和其左边的Label
    triggerType_frame = ctk.CTkFrame(tab_view.tab("基础设置"))
    triggerType_frame.grid(row=2, column=0, sticky='w', pady=5)  # 使用grid布局并靠左对齐
    # 添加一个Label
    triggerType_label = ctk.CTkLabel(triggerType_frame, text="当前触发方式为:")
    triggerType_label.pack(side='left')  # 在Frame中靠左对齐
    # 添加一个OptionMenu小部件
    options = ["按下", "切换", "shift+按下"]
    triggerType_option = ctk.CTkOptionMenu(triggerType_frame, variable=triggerType_var, values=options,
                                           command=update_values)
    triggerType_option.pack(side='left')  # 在Frame中靠左对齐

    # 创建新的Frame部件以容纳标签和OptionMenu
    frame = ctk.CTkLabel(tab_view.tab("基础设置"))
    frame.grid(row=3, column=0, sticky='w', pady=5)  # frame在root窗口中的位置
    # 创建一个标签文本并将其插入frame中
    lbl = ctk.CTkLabel(frame, text="当前热键为:")
    lbl.grid(row=0, column=0)  # 标签在frame部件中的位置
    # 创建一个可变的字符串变量以用于OptionMenu的选项值
    lockKey_var = ctk.StringVar()
    lockKey_var.set('右键')  # 设置选项菜单初始值为'左键'
    options = ['左键', '右键', '下侧键']  # 定义可用选项的列表
    # 创建OptionMenu并使用lockKey_var和options
    lockKey_menu = ctk.CTkOptionMenu(frame, variable=lockKey_var, values=options, command=update_values)
    lockKey_menu.grid(row=0, column=1)  # OptionMenu在frame部件中的位置

    # 创建一个Frame来包含arduinoMode开关和其左边的显示瞄准范围
    mouse_Side_Button_Witch_frame = ctk.CTkFrame(tab_view.tab("基础设置"))
    mouse_Side_Button_Witch_frame.grid(row=4, column=0, sticky='w', pady=5)  # 使用grid布局并靠左对齐
    # 创建一个名为 '鼠标侧键瞄准开关' 的复选框
    mouse_Side_Button_Witch_var = ctk.BooleanVar(value=False)
    mouse_Side_Button_Witch_check = ctk.CTkCheckBox(mouse_Side_Button_Witch_frame, text='鼠标侧键瞄准开关',
                                                    variable=mouse_Side_Button_Witch_var,
                                                    command=update_values)
    mouse_Side_Button_Witch_check.grid(row=0, column=0, sticky="w", pady=5)  # 使用grid布局并靠左对齐

    # 瞄准速度
    # 创建一个 StringVar 对象以保存 lockSpeed_scale 的值
    lockSpeed_variable = tk.StringVar()
    lockSpeed_variable.set(str(lockSpeed))
    # 一个名为 'Lock Speed' 的滑动条；瞄准速度模块
    # 创建一个Frame来包含OptionMenu和其左边的Label
    LookSpeed_frame = ctk.CTkFrame(tab_view.tab("基础设置"))
    LookSpeed_frame.grid(row=6, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 一个Label，显示文字"LockSpeed:"
    LookSpeed_label_0 = ctk.CTkLabel(LookSpeed_frame, text="LockSpeed:")
    LookSpeed_label_0.grid(row=0, column=0)  # 在Frame中靠左对齐
    # 一个名为 'Lock Speed' 的滑动条；瞄准速度模块
    lockSpeed_scale = ctk.CTkSlider(LookSpeed_frame, from_=0, to=1, number_of_steps=100, command=update_values)
    lockSpeed_scale.set(lockSpeed)
    lockSpeed_scale.grid(row=0, column=1)
    # 使用 textvariable 而非 text
    LookSpeed_label_text = ctk.CTkLabel(LookSpeed_frame, textvariable=lockSpeed_variable)
    LookSpeed_label_text.grid(row=0, column=2)



    # 自瞄范围调整
    # 创建一个 StringVar 对象以保存 closest_mouse_dist 的值
    closest_mouse_dist_variable = tk.StringVar()
    closest_mouse_dist_variable.set(str(closest_mouse_dist))
    # 2创建一个Frame来包含OptionMenu和其左边的Label
    closest_mouse_dist_frame = ctk.CTkFrame(tab_view.tab("基础设置"))
    closest_mouse_dist_frame.grid(row=7, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    closest_mouse_dist_label = ctk.CTkLabel(closest_mouse_dist_frame, text="自瞄范围:")
    closest_mouse_dist_label.grid(row=0, column=1, sticky='w')
    # 自瞄范围调整
    closest_mouse_dist_scale = ctk.CTkSlider(closest_mouse_dist_frame, from_=0, to=300, command=update_values)
    closest_mouse_dist_scale.set(closest_mouse_dist)
    closest_mouse_dist_scale.grid(row=0, column=2, padx=(12, 0))
    # 使用 textvariable 而非 text
    closest_mouse_dist_text = ctk.CTkLabel(closest_mouse_dist_frame, textvariable=closest_mouse_dist_variable)
    closest_mouse_dist_text.grid(row=0, column=3)
    # 如果分段瞄准打开则停用一般瞄准范围设置
    if segmented_aiming_switch:
        ban_closest_mouse_dist_label = ctk.CTkLabel(closest_mouse_dist_frame, text="由于分段瞄准启用，该选项已禁用", width=200)
        ban_closest_mouse_dist_label.grid(row=0, column=2, padx=(12, 0))  # 行号
        ban_closest_mouse_dist_text = ctk.CTkLabel(closest_mouse_dist_frame, text="####", width=30)
        ban_closest_mouse_dist_text.grid(row=0, column=3)  # 行号

    # 创建新的Frame部件以容纳标签和OptionMenu
    frame = ctk.CTkLabel(tab_view.tab("基础设置"))
    frame.grid(row=8, column=0, sticky='w', pady=5)  # frame在root窗口中的位置
    # 创建一个标签文本并将其插入frame中
    lbl = ctk.CTkLabel(frame, text="预测方法:")
    lbl.grid(row=0, column=0)  # 标签在frame部件中的位置
    # 创建一个可变的字符串变量以用于OptionMenu的选项值
    method_of_prediction_var = ctk.StringVar()
    method_of_prediction_var.set('禁用预测')  # 设置选项菜单初始值为'左键'
    options = ['禁用预测', '倍率预测', '像素预测']  # 定义可用选项的列表
    # 创建OptionMenu并使用lockKey_var和options
    method_of_prediction_menu = ctk.CTkOptionMenu(frame, variable=method_of_prediction_var, values=options,
                                                  command=update_values)
    method_of_prediction_menu.grid(row=0, column=1)  # OptionMenu在frame部件中的位置

    # 2创建一个Frame来包含OptionMenu和其左边的Label
    message_text_frame = ctk.CTkFrame(tab_view.tab("基础设置"))
    message_text_frame.grid(row=9, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 创建Label
    message_text_Label = ctk.CTkLabel(message_text_frame, text="更新公告")
    message_text_Label.grid(row=0, column=1)
    # 创建文本框
    message_text_box = ctk.CTkTextbox(message_text_frame, width=300, height=100, corner_radius=5)
    message_text_box.grid(row=1, column=1, sticky="nsew")
    message_text_box.insert("0.0", readme_content)



    # 目标选择框
    # 创建一个Frame来包含OptionMenu和其左边的Label
    target_selection_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    target_selection_frame.grid(row=1, column=0, sticky='w', pady=5)  # 使用grid布局并靠左对齐
    # 创建一个标签文本并将其插入frame中
    target_selection_label = ctk.CTkLabel(target_selection_frame, text="当前检测目标为:")
    target_selection_label.grid(row=0, column=0)  # 标签在frame部件中的位置
    # 创建一个可变的字符串变量以用于OptionMenu的选项值
    target_selection_var = ctk.StringVar()
    target_selection_var.set('敌人')  # 设置选项菜单初始值为'敌人'
    # 定义可用选项的列表
    options = list(target_mapping.keys())
    # 创建选择框
    target_selection_option = ctk.CTkOptionMenu(target_selection_frame, variable=target_selection_var, values=options,
                                                command=update_values)
    target_selection_option.grid(row=0, column=1)

    # 置信度调整
    # 创建一个 StringVar 对象以保存 lockSpeed_scale 的值
    confidence_variable = tk.StringVar()
    confidence_variable.set(str(confidence))
    # 置信度调整滑块：创建一个名为 'Confidence' 的滑动条;置信度调整模块
    # 创建一个Frame来包含OptionMenu和其左边的Label
    confidence_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    confidence_frame.grid(row=2, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    confidence_label = ctk.CTkLabel(confidence_frame, text="置信度:")
    confidence_label.grid(row=0, column=1, sticky='w')
    # 置信度调整滑块：创建一个名为 'Confidence' 的滑动条;置信度调整模块
    confidence_scale = ctk.CTkSlider(confidence_frame, from_=0, to=1, number_of_steps=100, command=update_values)
    confidence_scale.set(confidence)
    confidence_scale.grid(row=0, column=2, padx=(25, 0))
    # 使用 textvariable 而非 text
    confidence_label_text = ctk.CTkLabel(confidence_frame, textvariable=confidence_variable)
    confidence_label_text.grid(row=0, column=3)

    # 倍率预测调整
    # 创建一个 StringVar 对象以保存 prediction_factor 的值
    prediction_factor_variable = tk.StringVar()
    prediction_factor_variable.set(str(prediction_factor))
    # 2创建一个Frame来包含OptionMenu和其左边的Label
    prediction_factor_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    prediction_factor_frame.grid(row=3, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    prediction_factor_label = ctk.CTkLabel(prediction_factor_frame, text="预测倍率:")
    prediction_factor_label.grid(row=0, column=1, sticky='w')
    # 预测因子调整
    prediction_factor_scale = ctk.CTkSlider(prediction_factor_frame, from_=0, to=1, number_of_steps=100,
                                            command=update_values)
    prediction_factor_scale.set(prediction_factor)
    prediction_factor_scale.grid(row=0, column=2, padx=(12, 0))
    # 使用 textvariable 而非 text
    prediction_factor_text = ctk.CTkLabel(prediction_factor_frame, textvariable=prediction_factor_variable)
    prediction_factor_text.grid(row=0, column=3)

    # 像素点预测调整
    # 创建一个 StringVar 对象以保存 extra_offset_x 的值
    extra_offset_x_variable = tk.StringVar()
    extra_offset_x_variable.set(str(extra_offset_x))
    # 一个名为 'Lock Speed' 的滑动条；瞄准速度模块
    # 创建一个Frame来包含OptionMenu和其左边的Label
    extra_offset_x_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    extra_offset_x_frame.grid(row=4, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 一个Label，显示文字"LockSpeed:"
    extra_offset_x_label = ctk.CTkLabel(extra_offset_x_frame, text="预测像素X:")
    extra_offset_x_label.grid(row=0, column=0)  # 在Frame中靠左对齐
    # 一个名为 'Lock Speed' 的滑动条；瞄准速度模块
    extra_offset_x_scale = ctk.CTkSlider(extra_offset_x_frame, from_=0, to=20, number_of_steps=20,
                                         command=update_values)
    extra_offset_x_scale.set(extra_offset_x)
    extra_offset_x_scale.grid(row=0, column=1, padx=(4, 0))
    # 使用 textvariable 而非 text
    extra_offset_x_label_text = ctk.CTkLabel(extra_offset_x_frame, textvariable=extra_offset_x_variable)
    extra_offset_x_label_text.grid(row=0, column=2)

    # 像素点预测调整
    # 创建一个 StringVar 对象以保存 extra_offset_y 的值
    extra_offset_y_variable = tk.StringVar()
    extra_offset_y_variable.set(str(extra_offset_y))
    # 一个名为 'Lock Speed' 的滑动条；瞄准速度模块
    # 创建一个Frame来包含OptionMenu和其左边的Label
    extra_offset_y_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    extra_offset_y_frame.grid(row=5, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 一个Label，显示文字"LockSpeed:"
    extra_offset_y_label = ctk.CTkLabel(extra_offset_y_frame, text="预测像素Y:")
    extra_offset_y_label.grid(row=0, column=0)  # 在Frame中靠左对齐
    # 一个名为 'Lock Speed' 的滑动条；瞄准速度模块
    extra_offset_y_scale = ctk.CTkSlider(extra_offset_y_frame, from_=0, to=20, number_of_steps=20,
                                         command=update_values)
    extra_offset_y_scale.set(extra_offset_y)
    extra_offset_y_scale.grid(row=0, column=1, padx=(4, 0))
    # 使用 textvariable 而非 text
    extra_offset_y_label_text = ctk.CTkLabel(extra_offset_y_frame, textvariable=extra_offset_y_variable)
    extra_offset_y_label_text.grid(row=0, column=2)

    # 瞄准偏移
    # 创建一个 StringVar 对象以保存 closest_mouse_dist 的值
    aimOffset_variable = tk.StringVar()
    aimOffset_variable.set(str(aimOffset))
    # 3创建一个Frame来包含滑块和其左边的Label文字
    aimOffset_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    aimOffset_frame.grid(row=6, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="瞄准偏移:")
    aimOffset_label.grid(row=0, column=1, sticky='w')
    # 瞄准偏移（数值越大越靠上）
    aimOffset_scale = ctk.CTkSlider(aimOffset_frame, from_=0, to=1, number_of_steps=100, command=update_values,
                                    orientation="vertical")
    aimOffset_scale.set(aimOffset)
    aimOffset_scale.grid(row=0, column=2, padx=(12, 0))
    # 添加一个Label显示瞄准位置：腰部
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="胯下")
    aimOffset_label.grid(row=0, column=3, pady=(170, 0))
    # 添加一个Label显示瞄准位置：腹部
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="腹部")
    aimOffset_label.grid(row=0, column=3, pady=(80, 0))
    # 添加一个Label显示瞄准位置：胸口
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="胸口")
    aimOffset_label.grid(row=0, column=3, pady=(0, 5))
    # 添加一个Label显示瞄准位置：头部
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="头部")
    aimOffset_label.grid(row=0, column=3, pady=(0, 170))
    # 添加一个Label显示人体图片
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, image=ctk.CTkImage(img, size=(150, 200)), text="")
    aimOffset_label.grid(row=0, column=4)
    # 使用 textvariable 而非 text
    aimOffset_text = ctk.CTkLabel(aimOffset_frame, textvariable=aimOffset_variable)
    aimOffset_text.grid(row=0, column=5, pady=(0, 0))

    # 屏幕宽度
    # 创建一个 StringVar 对象以保存 screen_width_scale 的值
    screen_width_scale_variable = tk.StringVar()
    screen_width_scale_variable.set(str(screen_width))
    # 4创建一个Frame来包含滑块和其左边的Label文字
    screen_width_scale_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    screen_width_scale_frame.grid(row=7, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    screen_width_scale_label = ctk.CTkLabel(screen_width_scale_frame, text="截图宽度:")
    screen_width_scale_label.grid(row=0, column=1, sticky='w')
    # 创建一个屏幕宽度滑块
    screen_width_scale = ctk.CTkSlider(screen_width_scale_frame, from_=100, to=2000, number_of_steps=190,
                                       command=update_values)
    screen_width_scale.set(screen_width)  # 初始值
    screen_width_scale.grid(row=0, column=2, padx=(12, 0))  # 行号
    # 使用 textvariable 而非 text
    screen_width_scale_text = ctk.CTkLabel(screen_width_scale_frame, textvariable=screen_width_scale_variable)
    screen_width_scale_text.grid(row=0, column=3)
    # 如果启用DXcam则停用截图宽度/高度调整滑块
    if screenshot_mode == 2:
        ban_screen_width_scale = ctk.CTkLabel(screen_width_scale_frame, text="由于DXcam启用，该选项已禁用", width=200)
        ban_screen_width_scale.grid(row=0, column=2, padx=(12, 0))  # 行号
        ban_screen_width_scale_text = ctk.CTkLabel(screen_width_scale_frame, text="####", width=30)
        ban_screen_width_scale_text.grid(row=0, column=3)  # 行号


    # 屏幕高度
    # 创建一个 StringVar 对象以保存 screen_height_scale 的值
    screen_height_scale_variable = tk.StringVar()
    screen_height_scale_variable.set(str(screen_height))
    # 5创建一个Frame来包含滑块和其左边的Label文字
    screen_height_scale_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    screen_height_scale_frame.grid(row=8, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    screen_height_scale_label = ctk.CTkLabel(screen_height_scale_frame, text="截图高度:")
    screen_height_scale_label.grid(row=0, column=1, sticky='w')
    # 创建一个屏幕高度滑块
    screen_height_scale = ctk.CTkSlider(screen_height_scale_frame, from_=100, to=2000, number_of_steps=190,
                                        command=update_values)
    screen_height_scale.set(screen_height)  # 初始值
    screen_height_scale.grid(row=0, column=2, padx=(12, 0))  # 行号
    # 如果启用DXcam则停用截图宽度/高度调整滑块
    # 使用 textvariable 而非 text
    screen_height_scale_text = ctk.CTkLabel(screen_height_scale_frame, textvariable=screen_height_scale_variable)
    screen_height_scale_text.grid(row=0, column=3)
    if screenshot_mode == 2:
        ban_screen_height_scale = ctk.CTkLabel(screen_height_scale_frame, text="由于DXcam启用，该选项已禁用", width=200)
        ban_screen_height_scale.grid(row=0, column=2, padx=(12, 0))  # 行号
        ban_screen_height_scale_text = ctk.CTkLabel(screen_height_scale_frame, text="####", width=30)
        ban_screen_height_scale_text.grid(row=0, column=3)  # 行号


    # 6创建一个Frame来包其他设置
    setting_frame = ctk.CTkFrame(tab_view.tab("其他设置"), width=300, height=300)
    setting_frame.grid(row=9, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    setting_frame.grid_propagate(False)  # 防止框架调整大小以适应其内容

    # 显示所选文件路径的标签
    model_file_label = tk.Label(setting_frame, text="还未选择模型文件", width=40, anchor='e')  # 初始化时显示的文本
    model_file_label.grid(row=0, column=0, sticky="w")  # 使用grid布局并靠左对齐

    # 用户选择模型文件的按钮
    model_file_button = ctk.CTkButton(setting_frame, text="选择模型文件(需重启)",
                                      command=choose_model)  # 点击此按钮时，将调用choose_model函数
    model_file_button.grid(row=1, column=0, padx=(0, 245), pady=(5, 0))  # 使用grid布局并靠左对齐

    # 创建一键打开配置文件的按钮
    config_file_button = ctk.CTkButton(setting_frame, text="打开配置文件(需重启)",
                                       command=open_settings_config)  # 点击此按钮时，将调用open_config函数
    config_file_button.grid(row=1, column=0, padx=(55, 0), pady=(5, 0))

    # 创建 '保存' 按钮
    save_button = ctk.CTkButton(setting_frame, text='保存设置', width=20, command=save_settings)
    save_button.grid(row=2, column=0, padx=(0, 320), pady=(10, 0))  # 根据你的需要调整行号

    # 创建 '加载' 按钮
    load_button = ctk.CTkButton(setting_frame, text='加载设置(未启用)', width=20, command=load_settings,
                                state="DISABLED")
    load_button.grid(row=2, column=0, padx=(0, 120), pady=(10, 0))

    # 创建"重启软件"按钮
    restart_button = ctk.CTkButton(setting_frame, text='重启软件', width=20, command=restart_program)
    restart_button.grid(row=3, column=0, padx=(0, 320), pady=(10, 0))

    # 版本号显示1
    version_number_text1 = ctk.CTkLabel(setting_frame, text="当前版本:", width=30)
    version_number_text1.bind("<Button-1>", command=open_web)
    version_number_text1.grid(row=3, column=0, padx=(10, 0), pady=(120, 0))
    # 版本号显示1
    version_number1 = ctk.CTkLabel(setting_frame, text=version_number, width=30)
    version_number1.bind("<Button-1>", command=open_web)
    version_number1.grid(row=3, column=0, padx=(120, 0), pady=(120, 0))
    # 版本号显示2
    version_number_text2 = ctk.CTkLabel(setting_frame, text="最新版本:", width=30)
    version_number_text2.bind("<Button-1>", command=open_web)
    version_number_text2.grid(row=4, column=0, padx=(10, 0), pady=(0, 0))
    # 版本号显示2
    version_number2 = ctk.CTkLabel(setting_frame, text=":(", width=30)
    version_number2.bind("<Button-1>", command=open_web)
    version_number2.grid(row=4, column=0, padx=(120, 0), pady=(0, 0))
    # # Fetch version number from GitHub
    version = fetch_readme_version_number()
    # # 更新version_number2的文本为从 Github 获取的版本号
    version_number2.configure(text=version)
    # 更新 version_number2 的文本并设置颜色（对比版本号）
    if version == version_number1.cget("text"):
        version_number2.configure(text=version, text_color="green")
    else:
        version_number2.configure(text=version, text_color="red")


    # 调试窗口标签栏
    image_label_frame = ctk.CTkFrame(tab_view.tab("测试窗口"), height=370, width=305)
    image_label_frame.grid(row=1, column=0, sticky='w')
    image_label_frame.grid_propagate(False)
    # 画面开关
    image_label_switch = ctk.CTkSwitch(image_label_frame, text="内部测试窗口(影响性能)", onvalue=True, offvalue=False,
                                       command=update_values)
    image_label_switch.grid(row=0, column=0, padx=(0, 0), sticky='w')
    # 画面显示
    image_label = tk.Label(image_label_frame)
    image_label.grid(row=1, column=0, padx=(0, 0))
    # 帧数显示
    image_label_FPSlabel = ctk.CTkLabel(image_label_frame, text="实时FPS：", width=40)  # 初始化时显示的文本
    image_label_FPSlabel.grid(row=2, column=0, padx=(0, 0), sticky='w')  # 使用grid布局并靠左对齐

    # 从文件加载设置
    load_settings()
    # 加载设置后更新变量,也是更新GUI上的显示
    update_values()

    # 主循环运行GUI
    root.mainloop()


def update_values(*args):
    global aimbot, lockSpeed, triggerType, arduinoMode, lockKey, lockKey_var, confidence, closest_mouse_dist \
        , closest_mouse_dist_scale, screen_width, screen_height, model_file, aimOffset, draw_center \
        , mouse_Side_Button_Witch, lockSpeed_text, LookSpeed_label_1, test_images_GUI, target_selection_str \
        , prediction_factor_scale, prediction_factor, method_of_prediction, extra_offset_x, extra_offset_y

    print("update_values function was called（配置已更新）")
    aimbot = aimbot_var.get()
    lockSpeed = lockSpeed_scale.get()
    triggerType = triggerType_var.get()
    arduinoMode = arduinoMode_var.get()
    lockKey = lockKey_var.get()
    target_selection_str = target_selection_var.get()
    mouse_Side_Button_Witch = mouse_Side_Button_Witch_var.get()
    confidence = confidence_scale.get()
    closest_mouse_dist = closest_mouse_dist_scale.get()
    screen_width = int(screen_width_scale.get())
    screen_height = int(screen_height_scale.get())
    aimOffset = aimOffset_scale.get()
    draw_center = draw_center_var.get()
    test_images_GUI = image_label_switch.get()
    prediction_factor = prediction_factor_scale.get()
    method_of_prediction = method_of_prediction_var.get()
    extra_offset_x = extra_offset_x_scale.get()
    extra_offset_y = extra_offset_y_scale.get()

    # 更新 lockSpeed_variable
    lockSpeed = round(lockSpeed_scale.get(), 2)
    lockSpeed_variable.set(str(lockSpeed))
    # 更新 confidence_variable
    confidence = round(confidence_scale.get(), 2)
    confidence_variable.set(str(confidence))
    # 更新 closest_mouse_dist_variable
    closest_mouse_dist = int(closest_mouse_dist_scale.get())
    closest_mouse_dist_variable.set(str(closest_mouse_dist))
    # 更新prediction_factor_variable
    prediction_factor = round(prediction_factor_scale.get(), 2)
    prediction_factor_variable.set(str(prediction_factor))
    # 更新extra_offset_x_variable
    extra_offset_x = round(extra_offset_x_scale.get())
    extra_offset_x_variable.set(str(extra_offset_x))
    # 更新extra_offset_y_variable
    extra_offset_y = round(extra_offset_y_scale.get())
    extra_offset_y_variable.set(str(extra_offset_y))
    # 更新 aimOffset_variable
    aimOffset = round(aimOffset_scale.get(), 2)  # 取两位小数
    aimOffset_variable.set(str(aimOffset))
    # 更新 screen_width
    screen_width = int(screen_width_scale.get())
    screen_width_scale_variable.set(str(screen_width))
    # 更新 screen_width
    screen_height = int(screen_height_scale.get())
    screen_height_scale_variable.set(str(screen_height))

    # 触发键值转换
    key = lockKey_var.get()
    if key == '左键':
        lockKey = 0x01
    elif key == '右键':
        lockKey = 0x02
    elif key == '下侧键':
        lockKey = 0x05


def save_settings():  # 保存设置
    global model_file
    new_settings = {
        'aimbot': aimbot_var.get(),
        'lockSpeed': lockSpeed_scale.get(),
        'triggerType': triggerType_var.get(),
        'arduinoMode': arduinoMode_var.get(),
        'lockKey': lockKey_var.get(),
        'mouse_Side_Button_Witch': mouse_Side_Button_Witch_var.get(),
        'confidence': confidence_scale.get(),
        'closest_mouse_dist': closest_mouse_dist_scale.get(),
        'screen_width': screen_width_scale.get(),
        'screen_height': screen_height_scale.get(),
        'aimOffset': aimOffset_scale.get(),
        'model_file': model_file,
        'prediction_factor': prediction_factor_scale.get(),
        'method_of_prediction': method_of_prediction_var.get(),
        'extra_offset_x': extra_offset_x_scale.get(),
        'extra_offset_y': extra_offset_y_scale.get(),
    }

    # 加载当前设置
    try:
        with open('settings.json', 'r') as f:
            current_settings = json.load(f)
    except FileNotFoundError:
        current_settings = {}

    # 将新设置合并到当前设置中
    current_settings.update(new_settings)

    # 保存当前设置
    with open('settings.json', 'w') as f:
        json.dump(current_settings, f, sort_keys=True, indent=4)


def load_prefix_variables():  # 加载前置参数
    global model_file, screenshot_mode, segmented_aiming_switch, crawl_information
    print('Loading prefix variables...')
    try:
        with open('settings.json', 'r') as f:
            settings = json.load(f)

        screenshot_mode = settings.get("screenshot_mode", 1)  # 加载截图方式
        segmented_aiming_switch = settings.get("segmented_aiming_switch", False)  # 加载分段瞄准开关
        crawl_information = settings.get("crawl_information", False)  # 加载公告获取开关

        print("前置变量加载成功！")
    except FileNotFoundError:
        print('[ERROR] 没有找到设置文件; 跳过加载设置')


def load_settings():  # 加载主程序参数设置
    global model_file, test_window_frame, screenshot_mode, crawl_information, DXcam_screenshot, dxcam_maxFPS, \
        loaded_successfully, stage1_scope, stage1_intensity, stage2_scope, stage2_intensity
    print('Loading settings...')
    try:
        with open('settings.json', 'r') as f:
            settings = json.load(f)

        aimbot_var.set(settings.get('aimbot', True))
        lockSpeed_scale.set(settings.get('lockSpeed', 0.7))
        triggerType_var.set(settings.get('triggerType', "\u6309\u4e0b"))
        arduinoMode_var.set(settings.get('arduinoMode', False))
        lockKey_var.set(settings.get('lockKey', "\u53f3\u952e"))
        mouse_Side_Button_Witch_var.set(settings.get('mouse_Side_Button_Witch', True))
        method_of_prediction_var.set(settings.get('method_of_prediction', "\u500d\u7387\u9884\u6d4b"))
        confidence_scale.set(settings.get('confidence', 0.5))
        extra_offset_x_scale.set(settings.get('extra_offset_x', 5))
        extra_offset_y_scale.set(settings.get('extra_offset_y', 5))
        prediction_factor_scale.set(settings.get('prediction_factor', 0.5))  # 使用适当的默认值来替换default_value
        closest_mouse_dist_scale.set(settings.get('closest_mouse_dist', 160))
        screen_width_scale.set(settings.get('screen_width', 360))
        screen_height_scale.set(settings.get('screen_height', 360))
        aimOffset_scale.set(settings.get('aimOffset', 0.4))
        model_file = settings.get('model_file', None)  # 从文件中加载model_file
        model_file_label.config(text=model_file or "还未选择模型文件")  # 更新标签上的文本为加载的文件路径或默认文本
        test_window_frame = settings.get('test_window_frame', False)  # 从文件中加载test_window_frame的值，如果没有就默认为False
        crawl_information = settings.get("crawl_information", True)  # 是否联网加载公告
        screenshot_mode = settings.get("screenshot_mode", 1)  # 加载截图方式
        DXcam_screenshot = settings.get("DXcam_screenshot", 360)  # DXcam截图方式的分辨率
        dxcam_maxFPS = settings.get('dxcam_maxFPS', 30)  # DXcam截图最大帧率限制
        stage1_scope = settings.get('stage1_scope', 50)  # 强锁范围(分段瞄准)
        stage1_intensity = settings.get('stage1_intensity', 0.8)  # 强锁力度(分段瞄准)
        stage2_scope = settings.get('stage2_scope', 170)  # 软锁范围(分段瞄准)
        stage2_intensity = settings.get('stage2_intensity', 0.4)  # 软锁力度(分段瞄准)

        print("设置加载成功！")
        loaded_successfully = True  # 加载成功标识符
    except FileNotFoundError:
        print('[ERROR] 没有找到设置文件; 跳过加载设置')
        pass


def calculate_distances(
        monitor: dict,  # A dictionary containing width and height of the monitor
        results: list,  # A list of object detection results
        frame_: np.array,  # The current frame to be processed
        aimbot: bool,  # Whether the aimbot is active or not
        lockSpeed: float,  # The speed at which the mouse should move towards the object
        arduinoMode: bool,  # Whether the Arudino mode is active or not
        lockKey: int,  # Lock Key code
        triggerType: str,  # Trigger type
):  # 目标选择逻辑与标识
    global boxes, cWidth, cHeight, extra_offset_x, extra_offset_y

    minDist = float('inf')  # 初始最小距离设置为无限大
    minBox = None  # 初始最小框设置为None

    # 计算屏幕的中点
    cWidth = monitor["width"] / 2
    cHeight = monitor["height"] / 2

    # 绘制自瞄范围框
    if draw_center:
        if screenshot_mode == 2:  # 如果采用DXcam截图模式则不使用mss的截图大小数据
            cWidth = DXcam_screenshot // 2
            cHeight = DXcam_screenshot // 2

        if segmented_aiming_switch:  # 如果分段瞄准开启，则绘制分段瞄准的范围，否则绘制默认模式范围
            cv2.circle(frame_, (int(cWidth), int(cHeight)), int(stage2_scope), (0, 255, 0), 2)
            cv2.circle(frame_, (int(cWidth), int(cHeight)), int(stage1_scope), (0, 255, 255), 2)
            cv2.circle(frame_, (int(cWidth), int(cHeight)), radius=5, color=(0, 0, 255), thickness=-1)
        else:
            cv2.circle(frame_, (int(cWidth), int(cHeight)), int(closest_mouse_dist), (0, 255, 0), 2)
            # 在自瞄范围框的中心绘制一个中心点
            cv2.circle(frame_, (int(cWidth), int(cHeight)), radius=5, color=(0, 0, 255), thickness=-1)

    for r in results:
        boxes = r.boxes.xyxy.cpu().numpy()  # 获取框坐标
        # print("瞄准偏移量倍率为：", aimOffset)  # 打印框坐标

    for box in boxes:
        x1, y1, x2, y2 = box

        # 计算检测到的物体框（BoundingBox）的中心点。
        centerx = (x1 + x2) / 2
        centery = (y1 + y2) / 2

        # 绘制目标中心点
        cv2.circle(frame_, (int(centerx), int(centery)), 5, (0, 255, 255), -1)


        dist = sqrt((cWidth - centerx) ** 2 + (cHeight - centery) ** 2)
        dist = round(dist, 1)

        # 范围设置
        if segmented_aiming_switch:
            if dist < minDist and dist < stage2_scope:
                minDist = dist  # 更新最小距离
                minBox = box  # 更新对应最小距离的框
        else:
            # 比较当前距离和最小距离
            if dist < minDist and dist < closest_mouse_dist:
                minDist = dist  # 更新最小距离
                minBox = box  # 更新对应最小距离的框

        location = (int(centerx), int(centery))
        cv2.putText(frame_, f'dist: {dist}', location, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # 检查最小距离和最小框是否已更新
    if minBox is not None:
        # print('自瞄状态2：', aimbot)

        # 获取当前循环中的最小框的四个坐标
        min_x1, min_y1, min_x2, min_y2 = minBox



        # 将最近的目标标记为绿色框
        cv2.rectangle(frame_, (int(minBox[0]), int(minBox[1])), (int(minBox[2]), int(minBox[3])), (0, 255, 0), 2)
        center_text_x = int((minBox[0] + minBox[2]) / 2)
        center_text_y = int((minBox[1] + minBox[3]) / 2)
        location = (center_text_x, center_text_y)
        cv2.putText(frame_, f'dist: {minDist}', location, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # 重新计算目标框中点
        box_centerx = (min_x1 + min_x2) / 2
        box_centery = (min_y1 + min_y2) / 2
        # 计算垂直瞄准偏移
        distance_to_top_border = box_centery - min_y1
        # 最终偏移距离
        aimOffset_ = distance_to_top_border * aimOffset

        # 绘制偏移
        cv2.circle(frame_, (int(box_centerx), int(box_centery - aimOffset_)), 5, (255, 0, 0), -1)

        # 偏移后的目标位置
        offset_centerx = box_centerx
        offset_centery = box_centery - aimOffset_

        # 新的位置与屏幕中心的距离
        centerx = offset_centerx - cWidth
        centery = offset_centery - cHeight

        # 屏幕中心点与偏移后的目标中心点之间的距离
        offset_dist = sqrt((cWidth - offset_centerx) ** 2 + (cHeight - offset_centery) ** 2)
        offset_dist = round(offset_dist, 1)
        # 在偏移后的目标中心点上方显示偏移距离
        offset_location = (int(offset_centerx), int(offset_centery))
        cv2.putText(frame_, f'offset_dist: {offset_dist}', offset_location, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # 是否开启分段瞄准
        if segmented_aiming_switch:
            # 判断距离是否小于30或100，然后设置lockSpeed的值
            if offset_dist < stage1_scope:  # 强锁范围 stage1_scope
                lockSpeed = stage1_intensity  # 强锁力度 stage1_intensity
            elif offset_dist < stage2_scope:  # 软锁范围 stage2_scope
                lockSpeed = stage2_intensity  # 软锁力度 stage2_intensity

        if method_of_prediction == "禁用预测":
            print("已禁用预测")
            # 计算光标应当从当前位置移动多大的距离以便到达目标位置(禁用预测)
            centerx *= lockSpeed
            centery *= lockSpeed
            pass

        elif method_of_prediction == "倍率预测":
            print("倍率预测已启用")
            # 添加额外偏移量
            centerx_extra = prediction_factor * centerx
            centery_extra = prediction_factor * centery
            # 使用更新后的目标位置计算鼠标移动距离
            centerx = (centerx + centerx_extra) * lockSpeed
            centery = (centery + centery_extra) * lockSpeed
            pass

        elif method_of_prediction == "像素预测":
            # print("像素预测已启用")
            # print("X轴提前设置：", extra_offset_x)
            # print("Y轴提前设置：", extra_offset_y)
            # 如果centerx或centery为负值，表示目标在光标的左边或上面，偏移量需要反向
            extra_offset_x_result = extra_offset_x if centerx >= 0 else -extra_offset_x
            extra_offset_y_result = extra_offset_y if centery >= 0 else -extra_offset_y

            # print("X轴提前结果：", extra_offset_x_result)
            # print("Y轴提前结果：", extra_offset_y_result)
            # 使用更新后的目标位置计算鼠标移动距离
            centerx = (centerx + extra_offset_x_result) * lockSpeed
            centery = (centery + extra_offset_y_result) * lockSpeed
            pass

        # 检查 locker 键、Shift 键和鼠标下侧键是否按下
        lockKey_pressed = win32api.GetKeyState(lockKey) & 0x8000
        shift_pressed = win32api.GetKeyState(win32con.VK_SHIFT) & 0x8000
        xbutton2_pressed = win32api.GetKeyState(0x05) & 0x8000

        # 将鼠标光标移动到检测到的框的中心
        # 第一种：切换触发
        if triggerType == "切换":
            print(101)
            if aimbot and (win32api.GetKeyState(lockKey) or (mouse_Side_Button_Witch and xbutton2_pressed)):
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(centerx * lockSpeed), int(centery * lockSpeed), 0,
                                     0)


        # 第二种：按下触发
        elif triggerType == "按下":
            print(102)
            if aimbot and (lockKey_pressed or (mouse_Side_Button_Witch and xbutton2_pressed)):
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(centerx * lockSpeed), int(centery * lockSpeed), 0,
                                     0)
            elif not (lockKey_pressed or (mouse_Side_Button_Witch and xbutton2_pressed)):
                # 停止代码
                pass

        # 第三种：shift+按下触发
        elif triggerType == "shift+按下":
            print(104)
            # print('aimbot:', aimbot)
            # print('lockKey_pressed:', lockKey_pressed)
            # print('shift_pressed:', shift_pressed)
            # print('xbutton2_pressed:', xbutton2_pressed)
            # print('mouse_Side_Button_Witch:', mouse_Side_Button_Witch)

            if aimbot and ((lockKey_pressed and shift_pressed) or (mouse_Side_Button_Witch and xbutton2_pressed)):
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(centerx * lockSpeed), int(centery * lockSpeed), 0,
                                     0)
            elif not ((lockKey_pressed and shift_pressed) or (mouse_Side_Button_Witch and xbutton2_pressed)):
                # 停止代码
                pass

    return frame_


def main_program_loop(model):  # 主程序流程代码
    global start_time, gc_time, closest_mouse_dist, lockSpeed, triggerType, arduinoMode, lockKey, confidence \
        , run_threads, aimbot, image_label, test_images_GUI, target_selection, target_selection_str, target_mapping \
        , target_selection_var, prediction_factor, should_break, readme_content





    # # 加载模型
    # model = load_model_file()

    # 初始化帧数计时器（帧数计算）
    frame_counter = 0
    start_time = time.time()

    # 等待加载完成再开启DXcam截图确保DXcam接收的参数正确
    while True:
        print("正在等待加载完成")
        if loaded_successfully:
            # 开启DXcam截图
            DXcam()
            break

    # 如果选择mss截图则关闭DXcam
    if screenshot_mode == 1:
        print("已选择MSS截图，关闭bettercam")
        camera.stop()

    if test_window_frame:
        # 创建窗口并设置 flag 为 cv2.WINDOW_NORMAL（外部）
        cv2.namedWindow('frame', cv2.WINDOW_NORMAL)
        # 在主循环中显示图像之前，设置窗口属性，置顶
        cv2.setWindowProperty('frame', cv2.WND_PROP_TOPMOST, 1)

    # 循环捕捉屏幕
    while run_threads:

        # 截图区域大小
        monitor = calculate_screen_monitor(screen_width, screen_height)

        try:
            target_selection = target_mapping[target_selection_str]
        except KeyError:
            print(f"Key {target_selection_str} not found in target_mapping.（加载中）")
        # print("当前目标为", target_selection_str)
        # print("当前目标为", target_mapping)

        # 截图方式选择
        if screenshot_mode == 1:
            print("当前截图模式：mss")
            frame = capture_screen(monitor, sct)  # mss截图方式
        elif screenshot_mode == 2:
            print("当前截图模式：bettercam")
            frame = camera.get_latest_frame()  # DXcam截图方式
        # ---------------------------------------------------------------------------

        # 检测和跟踪对象（推理部分）
        results = model.predict(frame, save=False, imgsz=320, conf=confidence, half=True, agnostic_nms=True, iou=0.7,
                                classes=[target_selection])

        # ---------------------------------------------------------------------------
        # 绘制结果
        frame_ = results[0].plot()

        # 计算距离 并 将最近的目标绘制为绿色边框
        try:
            frame_ = calculate_distances(monitor, results, frame_, aimbot, lockSpeed, arduinoMode, lockKey, triggerType)
        except TypeError:
            # 当 TypeError 出现时，执行这部分代码
            print('lockKey 值发生错误。但是无关紧要')

        try:
            # 获取并显示帧率
            end_time = time.time()
            frame_, frame_counter, start_time = update_and_display_fps(frame_, frame_counter, start_time, end_time)
        except NameError:
            print("ERROR:帧率显示失败(加载中)")


        if test_window_frame:
            # 图像调试窗口（外部cv2.imshow）
            should_break = display_debug_window(frame_)

        if test_images_GUI:
            # 图像调试窗口（内部GUI）
            # 获取屏幕宽度和高度
            screen_width_1, screen_height_1 = pyautogui.size()
            # 使用函数获取期望的大小
            desired_size = get_desired_size(screen_width_1, screen_height_1)
            # 在cv2.imshow之前，将frame_转换为PIL.Image对象，然后转换成Tkinter可以使用的PhotoImage对象
            img = cv2.cvtColor(frame_, cv2.COLOR_BGR2RGB)
            im = Image.fromarray(img)
            desired_size = desired_size  # 重新调整大小1
            im_resized = im.resize(desired_size)  # 重新调整大小2
            imgtk = ImageTk.PhotoImage(image=im_resized)
            image_label.config(image=imgtk)
            image_label.image = imgtk

        if test_window_frame:
            if should_break:
                break

        # 每120秒进行一次gc
        if time.time() - gc_time >= 60:
            gc.collect()
            gc_time = time.time()

    pass


def stop_program():  # 停止子线程
    global run_threads, Thread_to_join, root
    camera.stop()
    run_threads = False
    if Thread_to_join:
        Thread_to_join.join()  # 等待子线程结束
    if root is not None:
        root.quit()
        root.destroy()  # 销毁窗口

    os._exit(0)  # 强制结束进程


def restart_program():  # 重启软件
    python = sys.executable
    os.execl(python, python, *sys.argv)


def Initialization_parameters():  # 初始化参数

    model = load_model_file()
    aimbot = True
    lockSpeed = 1
    arduinoMode = False
    triggerType = "按下"
    lockKey = 0x02
    aimOffset = 25
    screen_width = 640
    screen_height = 640

    return (model, aimbot, lockSpeed, arduinoMode, triggerType, lockKey, aimOffset, screen_width,
            screen_height)



### ---------------------------------------main-------------------------------------------------------------------------
if __name__ == "__main__":

    # 优先级设置
    p = psutil.Process(os.getpid())
    p.nice(psutil.REALTIME_PRIORITY_CLASS)

    # 加载前置变量
    load_prefix_variables()

    # 爬取版本号与公告
    crawl_information_by_github()

    # 初始化参数
    (model, aimbot, lockSpeed, arduinoMode, triggerType, lockKey, aimOffset, screen_width, screen_height
     ) \
        = Initialization_parameters()

    freeze_support()




    # 创建并启动子线程1用于运行main_program_loop
    thread1 = threading.Thread(target=main_program_loop, args=(model,))
    thread1.start()

    # 启动 GUI(运行主程序)
    create_gui_tkinter()

    # 等待main_program_loop线程结束后再完全退出。
    thread1.join()
