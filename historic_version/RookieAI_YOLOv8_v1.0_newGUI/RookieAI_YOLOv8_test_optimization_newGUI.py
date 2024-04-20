import gc
import json
import os
import threading
import time
import tkinter as tk
from math import sqrt
from tkinter import filedialog
from PIL import Image

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

# 默0认截图长宽(像素)
screen_width = 640
screen_height = 640

# 初始化帧数计时器（帧数计算）
frame_counter = 0
start_time = time.time()
start_test_time = time.time()

# 新增初始化gc计时器（垃圾清理）
gc_time = time.time()

# 自瞄范围
closest_mouse_dist = 100

# 置信度设置
confidence = 0.65

# 垂直瞄准偏移
aimOffset = 0.5

# 软件页面大小
_win_width = 300
_win_height = 640

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


def display_debug_window(frame):  # 调试窗口
    # 在主循环中显示图像
    cv2.imshow('frame', frame)

    if cv2.waitKey(1) & 0xFF == ord('.'):
        cv2.destroyAllWindows()
        return True
    else:
        return False


def choose_model():  # 选择模型
    global model_file
    model_file = filedialog.askopenfilename()  # 在这里让用户选择文件
    model_file_label.config(text=model_file)  # 更新标签上的文本为选择的文件路径


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
        , closest_mouse_dist_variable, aimOffset_variable, screen_width_scale_variable, screen_height_scale_variable


    # 使用customtkinter创建根窗口
    root = ctk.CTk()
    ctk.set_appearance_mode("system")  # default

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


    # 创建一个Frame来包含aimbot开关和其左边的显示瞄准范围
    aimbot_draw_center_frame = ctk.CTkFrame(root)
    aimbot_draw_center_frame.grid(row=1, column=0, sticky='w', pady=5)  # 使用grid布局并靠左对齐
    # 创建一个名为 'Aimbot' 的复选框
    aimbot_var = ctk.BooleanVar(value=aimbot)
    aimbot_check = ctk.CTkCheckBox(aimbot_draw_center_frame, text='Aimbot', variable=aimbot_var, command=update_values,)
    aimbot_check.grid(row=0, column=0)  # 使用grid布局并靠左对齐
    # 是否显示瞄准范围的开关
    draw_center_var = ctk.BooleanVar(value=False)  # 默认值为False
    draw_center_check = ctk.CTkCheckBox(aimbot_draw_center_frame, text='Draw center(显示瞄准范围)', variable=draw_center_var,
                                        command=update_values)
    draw_center_check.grid(row=0, column=1)



    # 创建一个名为 'Arduino Mode(未启用)' 的复选框
    arduinoMode_var = ctk.BooleanVar(value=arduinoMode)
    arduinoMode_check = ctk.CTkCheckBox(root, text='Arduino Mode(待开发)', variable=arduinoMode_var,
                                        command=update_values, state="DISABLED")
    arduinoMode_check.grid(row=2, column=0, sticky="w")  # 使用grid布局并靠左对齐

    triggerType_var = tk.StringVar(value=triggerType)

    # 创建一个Frame来包含OptionMenu和其左边的Label
    triggerType_frame = ctk.CTkFrame(root)
    triggerType_frame.grid(row=3, column=0, sticky='w', pady=5)  # 使用grid布局并靠左对齐
    # 添加一个Label
    triggerType_label = ctk.CTkLabel(triggerType_frame, text="当前触发方式为:")
    triggerType_label.pack(side='left')  # 在Frame中靠左对齐
    # 添加一个OptionMenu小部件
    options = ["按下", "切换", "shift+按下"]
    triggerType_option = ctk.CTkOptionMenu(triggerType_frame, variable=triggerType_var, values=options, command=update_values)
    triggerType_option.pack(side='left')  # 在Frame中靠左对齐

    # 创建新的Frame部件以容纳标签和OptionMenu
    frame = ctk.CTkLabel(root)
    frame.grid(row=4, column=0, sticky='w', pady=5)  # frame在root窗口中的位置
    # 创建一个标签文本并将其插入frame中
    lbl = ctk.CTkLabel(frame, text="当前热键为:")
    lbl.grid(row=0, column=0)  # 标签在frame部件中的位置
    # 创建一个可变的字符串变量以用于OptionMenu的选项值
    lockKey_var = ctk.StringVar()
    lockKey_var.set('右键')  # 设置选项菜单初始值为'左键'
    options = ['右键', '左键', '右键', '下侧键']  # 定义可用选项的列表
    # 创建OptionMenu并使用lockKey_var和options
    lockKey_menu = ctk.CTkOptionMenu(frame, variable=lockKey_var, values=options, command=update_values)
    # 将OptionMenu插入到frame中，并确保它与标签在同一行
    lockKey_menu.grid(row=0, column=1)  # OptionMenu在frame部件中的位置


    # 创建一个名为 '鼠标侧键瞄准开关' 的复选框
    mouse_Side_Button_Witch_var = ctk.BooleanVar(value=False)
    mouse_Side_Button_Witch_check = ctk.CTkCheckBox(root, text='鼠标侧键瞄准开关', variable=mouse_Side_Button_Witch_var,
                                        command=update_values)
    mouse_Side_Button_Witch_check.grid(row=5, column=0, sticky="w", pady=5)  # 使用grid布局并靠左对齐


    # 瞄准速度
    # 创建一个 StringVar 对象以保存 lockSpeed_scale 的值
    lockSpeed_variable = tk.StringVar()
    lockSpeed_variable.set(str(lockSpeed))
    # 一个名为 'Lock Speed' 的滑动条；瞄准速度模块
    # 创建一个Frame来包含OptionMenu和其左边的Label
    LookSpeed_frame = ctk.CTkFrame(root)
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

    # 置信度调整
    # 创建一个 StringVar 对象以保存 lockSpeed_scale 的值
    confidence_variable = tk.StringVar()
    confidence_variable.set(str(confidence))
    # 置信度调整滑块：创建一个名为 'Confidence' 的滑动条;置信度调整模块
    # 创建一个Frame来包含OptionMenu和其左边的Label
    confidence_frame = ctk.CTkFrame(root)
    confidence_frame.grid(row=7, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
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


    # 自瞄范围调整
    # 创建一个 StringVar 对象以保存 closest_mouse_dist 的值
    closest_mouse_dist_variable = tk.StringVar()
    closest_mouse_dist_variable.set(str(closest_mouse_dist))
    # 2创建一个Frame来包含OptionMenu和其左边的Label
    closest_mouse_dist_frame = ctk.CTkFrame(root)
    closest_mouse_dist_frame.grid(row=8, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
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

    # 瞄准偏移
    # 创建一个 StringVar 对象以保存 closest_mouse_dist 的值
    aimOffset_variable = tk.StringVar()
    aimOffset_variable.set(str(aimOffset))
    # 3创建一个Frame来包含滑块和其左边的Label文字
    aimOffset_frame = ctk.CTkFrame(root)
    aimOffset_frame.grid(row=9, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="瞄准偏移:")
    aimOffset_label.grid(row=0, column=1, sticky='w')
    # 瞄准偏移（数值越大越靠上）
    aimOffset_scale = ctk.CTkSlider(aimOffset_frame, from_=0, to=1, number_of_steps=100, command=update_values, orientation="vertical")
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
    screen_width_scale_frame = ctk.CTkFrame(root)
    screen_width_scale_frame.grid(row=10, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    screen_width_scale_label = ctk.CTkLabel(screen_width_scale_frame, text="截图宽度:")
    screen_width_scale_label.grid(row=0, column=1, sticky='w')
    # 创建一个屏幕宽度滑块
    screen_width_scale = ctk.CTkSlider(screen_width_scale_frame, from_=100, to=2000, number_of_steps=190, command=update_values)
    screen_width_scale.set(screen_width)  # 初始值
    screen_width_scale.grid(row=0, column=2, padx=(12, 0))  # 行号
    # 使用 textvariable 而非 text
    screen_width_scale_text = ctk.CTkLabel(screen_width_scale_frame, textvariable=screen_width_scale_variable)
    screen_width_scale_text.grid(row=0, column=3)


    # 屏幕高度
    # 创建一个 StringVar 对象以保存 screen_height_scale 的值
    screen_height_scale_variable = tk.StringVar()
    screen_height_scale_variable.set(str(screen_height))
    # 5创建一个Frame来包含滑块和其左边的Label文字
    screen_height_scale_frame = ctk.CTkFrame(root)
    screen_height_scale_frame.grid(row=11, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    screen_height_scale_label = ctk.CTkLabel(screen_height_scale_frame, text="截图高度:")
    screen_height_scale_label.grid(row=0, column=1, sticky='w')
    # 创建一个屏幕高度滑块
    screen_height_scale = ctk.CTkSlider(screen_height_scale_frame, from_=100, to=2000, number_of_steps=190, command=update_values)
    screen_height_scale.set(screen_height)  # 初始值
    screen_height_scale.grid(row=0, column=2, padx=(12, 0))  # 行号
    # 使用 textvariable 而非 text
    screen_height_scale_text = ctk.CTkLabel(screen_height_scale_frame, textvariable=screen_height_scale_variable)
    screen_height_scale_text.grid(row=0, column=3)


    # 显示所选文件路径的标签
    model_file_label = tk.Label(root, text="还未选择模型文件", width=40)  # 初始化时显示的文本
    model_file_label.grid(row=12, column=0, sticky="w")  # 使用grid布局并靠左对齐

    # 用户选择模型文件的按钮
    model_file_button = ctk.CTkButton(root, text="选择模型文件", command=choose_model)  # 点击此按钮时，将调用choose_model函数
    model_file_button.grid(row=13, column=0, padx=(0, 245), pady=(5, 0))  # 使用grid布局并靠左对齐


    # 创建 '保存' 按钮
    save_button = ctk.CTkButton(root, text='保存设置', width=20, command=save_settings)
    save_button.grid(row=14, column=0, padx=(0, 320), pady=(10, 0))  # 根据你的需要调整行号

    # 创建 '加载' 按钮
    load_button = ctk.CTkButton(root, text='加载设置(未启用)', width=20, command=load_settings, state="DISABLED")
    load_button.grid(row=14, column=0, padx=(0, 120), pady=(10, 0))

    # 版本号显示
    version_number = ctk.CTkLabel(root, text="V1.0_newGUI", width=40)
    version_number.grid(row=14, column=0, padx=(130, 0), pady=(15, 0))

    # 从文件加载设置
    load_settings()
    # 加载设置后更新变量,也是更新GUI上的显示
    update_values()

    print('自瞄GUI设置：', aimbot_var.get())

    # 主循环运行GUI
    root.mainloop()


def update_values(*args):
    global aimbot, lockSpeed, triggerType, arduinoMode, lockKey, lockKey_var, confidence, closest_mouse_dist \
        , closest_mouse_dist_scale, screen_width, screen_height, model_file, aimOffset, draw_center\
        , mouse_Side_Button_Witch, lockSpeed_text, LookSpeed_label_1
    print("update_values function was called")
    aimbot = aimbot_var.get()
    lockSpeed = lockSpeed_scale.get()
    triggerType = triggerType_var.get()
    arduinoMode = arduinoMode_var.get()
    lockKey = lockKey_var.get()
    mouse_Side_Button_Witch = mouse_Side_Button_Witch_var.get()
    confidence = confidence_scale.get()
    closest_mouse_dist = closest_mouse_dist_scale.get()
    screen_width = int(screen_width_scale.get())
    screen_height = int(screen_height_scale.get())
    aimOffset = aimOffset_scale.get()
    draw_center = draw_center_var.get()

    # 更新 lockSpeed_variable
    lockSpeed = round(lockSpeed_scale.get(), 2)
    lockSpeed_variable.set(str(lockSpeed))
    # 更新 confidence_variable
    confidence = round(confidence_scale.get(), 2)
    confidence_variable.set(str(confidence))
    # 更新 closest_mouse_dist_variable
    closest_mouse_dist = int(closest_mouse_dist_scale.get())
    closest_mouse_dist_variable.set(str(closest_mouse_dist))
    # 更新 aimOffset_variable
    aimOffset = round(aimOffset_scale.get(), 2)  # 取两位小数
    aimOffset_variable.set(str(aimOffset))
    # 更新 screen_width
    screen_width = int(screen_width_scale.get())
    screen_width_scale_variable.set(str(screen_width))
    # 更新 screen_width
    screen_height = int(screen_height_scale.get())
    screen_height_scale_variable.set(str(screen_height))

    # print('状态1：aimbot_var:', aimbot_var.get(), '状态2：aimbot:', aimbot)
    # print('状态1：mouse_Side_Button_Witch:', aimbot_var.get(), '状态2：mouse_Side_Button_Witch_var.get:', mouse_Side_Button_Witch_var.get())

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
    settings = {
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
    }

    with open('settings.json', 'w') as f:
        json.dump(settings, f, sort_keys=True, indent=4)


def load_settings():  # 加载主程序参数设置
    global model_file
    print('Loading settings...')
    try:
        with open('settings.json', 'r') as f:
            settings = json.load(f)

        aimbot_var.set(settings['aimbot'])
        lockSpeed_scale.set(settings['lockSpeed'])
        triggerType_var.set(settings['triggerType'])
        arduinoMode_var.set(settings['arduinoMode'])
        lockKey_var.set(settings['lockKey'])
        mouse_Side_Button_Witch_var.set(settings['mouse_Side_Button_Witch'])
        confidence_scale.set(settings['confidence'])
        closest_mouse_dist_scale.set(settings['closest_mouse_dist'])
        screen_width_scale.set(settings['screen_width'])
        screen_height_scale.set(settings['screen_height'])
        aimOffset_scale.set(settings['aimOffset'])
        model_file = settings.get('model_file', None)  # 从文件中加载model_file
        model_file_label.config(text=model_file or "还未选择模型文件")  # 更新标签上的文本为加载的文件路径或默认文本
        print("设置加载成功！")
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
    global boxes, cWidth, cHeight

    minDist = float('inf')  # 初始最小距离设置为无限大
    minBox = None  # 初始最小框设置为None

    # 计算屏幕的中点
    cWidth = monitor["width"] / 2
    cHeight = monitor["height"] / 2

    # 绘制自瞄范围框
    if draw_center:
        cv2.circle(frame_, (int(cWidth), int(cHeight)), int(closest_mouse_dist), (0, 255, 0), 2)

    for r in results:
        boxes = r.boxes.xyxy.cpu().numpy()  # 获取框坐标
        print("瞄准偏移量倍率为：", aimOffset)  # 打印框坐标

    for box in boxes:
        x1, y1, x2, y2 = box

        # 计算检测到的物体框（BoundingBox）的中心点。
        centerx = (x1 + x2) / 2
        centery = (y1 + y2) / 2

        # 绘制目标中心点
        cv2.circle(frame_, (int(centerx), int(centery)), 5, (0, 255, 255), -1)

        dist = sqrt((cWidth - centerx) ** 2 + (cHeight - centery) ** 2)
        dist = round(dist, 1)

        # 比较当前距离和最小距离
        if dist < minDist and dist < closest_mouse_dist:
            minDist = dist  # 更新最小距离
            minBox = box  # 更新对应最小距离的框

        location = (int(centerx), int(centery))
        cv2.putText(frame_, f'dist: {dist}', location, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # 检查最小距离和最小框是否已更新
    if minBox is not None:
        # print('自瞄状态2：', aimbot)


        cv2.rectangle(frame_, (int(minBox[0]), int(minBox[1])), (int(minBox[2]), int(minBox[3])), (0, 255, 0), 2)
        center_text_x = int((minBox[0] + minBox[2]) / 2)
        center_text_y = int((minBox[1] + minBox[3]) / 2)
        location = (center_text_x, center_text_y)
        cv2.putText(frame_, f'dist: {minDist}', location, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # 瞄准偏移：计算目标中心点到minBox上边框的距离
        distance_to_top_border = center_text_y - minBox[1]
        # print("瞄准偏移——中心点到minBox上边框距离：", distance_to_top_border)

        # 最终偏移距离
        aimOffset_ = distance_to_top_border * aimOffset
        # print("瞄准偏移——最终偏移距离：", aimOffset_)
        # 计算光标应当从当前位置移动多大的距离以便到达目标位置
        centerx = (center_text_x - cWidth) * lockSpeed
        centery = (center_text_y - cHeight - aimOffset_) * lockSpeed

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



def main_program_loop():  # 主程序流程代码
    global start_time, gc_time, closest_mouse_dist, lockSpeed, triggerType, arduinoMode, lockKey, confidence \
        , run_threads, aimbot

    # 加载模型
    model = load_model_file()

    # 初始化帧数计时器（帧数计算）
    frame_counter = 0
    start_time = time.time()

    # 截图区域大小
    monitor = calculate_screen_monitor(screen_width, screen_height)  # 在这里修改截图区域大小

    # 创建窗口并设置 flag 为 cv2.WINDOW_NORMAL
    cv2.namedWindow('frame', cv2.WINDOW_NORMAL)
    # 在主循环中显示图像之前，设置窗口属性
    cv2.setWindowProperty('frame', cv2.WND_PROP_TOPMOST, 1)

    # 循环捕捉屏幕
    while run_threads:
        monitor = calculate_screen_monitor(screen_width, screen_height)
        print("热键为:", lockKey)
        # 截图方式
        frame = capture_screen(monitor, sct)  # mss截图方式
        # ---------------------------------------------------------------------------

        # 检测和跟踪对象（推理部分）
        results = model.predict(frame, save=False, imgsz=320, conf=confidence, half=True, agnostic_nms=True, iou=0.7)

        # ---------------------------------------------------------------------------
        # 绘制结果
        frame_ = results[0].plot()

        # 计算距离 并 将最近的目标绘制为绿色边框
        try:
            frame_ = calculate_distances(monitor, results, frame_, aimbot, lockSpeed, arduinoMode, lockKey, triggerType)
        except TypeError:
            # 当 TypeError 出现时，执行这部分代码
            print('lockKey 值发生错误。但是无关紧要')

        # 获取并显示帧率
        end_time = time.time()
        frame_, frame_counter, start_time = update_and_display_fps(frame_, frame_counter, start_time, end_time)

        # 调试窗口
        should_break = display_debug_window(frame_)
        if should_break:
            break

        # 每120秒进行一次gc
        if time.time() - gc_time >= 60:
            gc.collect()
            gc_time = time.time()
    pass


def stop_program():  # 停止子线程
    global run_threads, Thread_to_join, root
    run_threads = False
    if Thread_to_join:
        Thread_to_join.join()  # 等待子线程结束
    if root is not None:
        root.quit()
        root.destroy()  # 销毁窗口

    os._exit(0)  # 强制结束进程


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
    return model, aimbot, lockSpeed, arduinoMode, triggerType, lockKey, aimOffset, screen_width, screen_height


### ---------------------------------------main--------------------------------------------------------------------------
if __name__ == "__main__":
    model, aimbot, lockSpeed, arduinoMode, triggerType, lockKey, aimOffset, screen_width, screen_height \
        = Initialization_parameters()

    print('当前自瞄开启状态：', aimbot)

    # 创建并启动子线程1用于运行main_program_loop
    thread1 = threading.Thread(target=main_program_loop)
    thread1.start()

    # 启动 GUI(运行主程序)
    create_gui_tkinter()

    # 等待main_program_loop线程结束后再完全退出。
    thread1.join()

