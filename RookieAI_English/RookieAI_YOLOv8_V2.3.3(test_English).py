import gc
import json
import os
import threading
import time
import sys
import requests
import tkinter as tk
import webbrowser
import bettercam
import psutil
from math import sqrt
from tkinter import filedialog
from PIL import Image, ImageTk
from multiprocessing import Process, freeze_support
import recoil_control
import cv2
from skimage.color import rgb2lab, deltaE_cie76

import cv2
import numpy as np
import pyautogui
import win32api
import win32con
import customtkinter as ctk
from mss import mss
from ultralytics import YOLO
import ast

model_file = "yolov8n.pt"
sct = mss()
camera = bettercam.create(output_idx=0, output_color="BGR", max_buffer_len=2048)  
screenshot_mode = False
screen_width = 640
screen_height = 640
DXcam_screenshot = 360
frame_counter = 0
start_time = time.time()
start_test_time = time.time()
gc_time = time.time()
dxcam_maxFPS = 30
closest_mouse_dist = 100
confidence = 0.65
aimOffset = 0.5
aimOffset_Magnification_x = 0
prediction_factor = 0.1
extra_offset_x = 5 
extra_offset_y = 5 
_win_width = 350
_win_height = 750
classes = 0
stage1_scope = 55  
stage1_intensity = 0.8 
stage2_scope = 170  
stage2_intensity = 0.4 
segmented_aiming_switch = False
test_window_frame = False
test_images_GUI = False
crawl_information = False
loaded_successfully = False
target_mapping = {'enemy': 0, 'friend': 1, 'head': 2}
img = Image.open("body_photo.png")
tolerance = 80  # Default value
ignore_colors = [(62,203,236)]  # Default value, list of BGR tuples


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

kp_scale = None
ki_scale = None
kd_scale = None
kp_variable = None
ki_variable = None
kd_variable = None

Thread_to_join = None
restart_thread = False
run_threads = True
draw_center = True

# PID controller values
kp = 1.0
ki = 0.1
kd = 0.05


def calculate_screen_monitor(capture_width=640, capture_height=640):     
    screen_width, screen_height = pyautogui.size() 
    center_x, center_y = screen_width // 2, screen_height // 2

    monitor = {
        "top": center_y - capture_height // 2,
        "left": center_x - capture_width // 2,
        "width": capture_width,
        "height": capture_height,
    }
    return monitor


def calculate_frame_rate(frame_counter, start_time, end_time): 
    if end_time - start_time != 0:
        frame_rate = frame_counter / (end_time - start_time)
        frame_counter = 0
        start_time = time.time()
    else:
        frame_rate = 0 
    return frame_rate, frame_counter, start_time


def update_and_display_fps(frame_, frame_counter, start_time, end_time):
    frame_counter += 1
    frame_rate, frame_counter, start_time = calculate_frame_rate(frame_counter, start_time, end_time)

    cv2.putText(frame_, f"FPS: {frame_rate:.0f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 1)

    text_fps = "FPS：{:.0f}".format(frame_rate)
    image_label_FPSlabel.configure(text=text_fps)
    print(f"FPS: {frame_rate:.0f}") 

    return frame_, frame_counter, start_time


def capture_screen(monitor, sct):
    screenshot = sct.grab(monitor)
    frame = np.array(screenshot)[:, :, :3]

    return frame


def DXcam():
    screen_width, screen_height = pyautogui.size()
    left, top = (screen_width - DXcam_screenshot) // 2, (screen_height - DXcam_screenshot) // 2
    right, bottom = left + DXcam_screenshot, top + DXcam_screenshot
    region = (left, top, right, bottom)

    camera.start(region=region, video_mode=True, target_fps=dxcam_maxFPS)  


def display_debug_window(frame): 
    cv2.imshow('frame', frame)
    if cv2.waitKey(1) & 0xFF == ord('.'):
        cv2.destroyAllWindows()
        return True
    else:
        return False


def get_desired_size(screen_width_1, screen_height_1):
    if screen_width_1 == 1920 and screen_height_1 == 1080:
        desired_size = (300, 300)
    elif screen_width_1 >= 2560 and screen_height_1 >= 1440:
        desired_size = (370, 370)
    else:
        desired_size = (300, 300)  
    return desired_size


def fetch_readme():  
    print("Start getting announcements......")
    try:
        readme_url = "https://raw.githubusercontent.com/Passer1072/RookieAI_yolov8/master/README.md"
        response = requests.get(readme_url, timeout=10)
        response_text = response.text
        print("get success")
        update_log_start = response_text.find("Change log：")
        if update_log_start == -1:
            return response_text
        update_log = response_text[update_log_start:]
        return update_log

    except Exception as e:
        print("Failed to obtain：", e)
        return "Unable to load latest README file，This may be due to network issues or other unknown errors。"

def fetch_readme_version_number(): 
    print("Start getting version number......")
    try:
        readme_url = "https://raw.githubusercontent.com/Passer1072/RookieAI_yolov8/master/README.md"
        response = requests.get(readme_url)
        response_text = response.text
        print("get success")

        search_str = "Current latest version: "

        update_log_start = response_text.find(search_str)

        if update_log_start == -1:
            return response_text

        update_log_start += len(search_str)  
        update_log = response_text[update_log_start:]

        update_log = update_log.strip()

        return update_log

    except Exception as e:
        print("Failed to obtain：", e)
        return "Failed to obtain version number"


def crawl_information_by_github():
    global readme_content, readme_version
    if crawl_information:
        readme_content = fetch_readme()
        readme_version = fetch_readme_version_number()

def open_web(event):
    webbrowser.open('https://github.com/Passer1072/RookieAI_yolov8') 


def choose_model(): 
    global model_file
    model_file = filedialog.askopenfilename()  
    model_file_label.config(text=model_file) 

def open_settings_config():
    os.startfile("settings.json")

def load_model_file(): 
    default_model_file = "yolov8n.pt"
    try:
        with open('settings.json', 'r') as f:
            settings = json.load(f)
            model_file = settings.get('model_file', default_model_file)
            if not os.path.isfile(model_file):
                print("[WARNING] Invalid model file path in settings file; use default model file")
                model_file = default_model_file
    except FileNotFoundError:
        print("[WARNING] Settings file not found; using default model file")
        model_file = default_model_file

    print("Load model file:", model_file)
    return YOLO(model_file) if model_file else None


def create_gui_tkinter():
    global aimbot_var, lockSpeed_scale, triggerType_var, arduinoMode_var, lockKey_var, confidence_scale \
        , closest_mouse_dist_scale, screen_width_scale, screen_height_scale, root, model_file, model_file_label, aimOffset_scale \
        , draw_center_var, mouse_Side_Button_Witch_var, LookSpeed_label_text, lockSpeed_variable, confidence_variable \
        , closest_mouse_dist_variable, aimOffset_variable, screen_width_scale_variable, screen_height_scale_variable \
        , image_label, image_label_switch, image_label_FPSlabel, target_selection_var, target_mapping, prediction_factor_variable \
        , prediction_factor_scale, method_of_prediction_var, extra_offset_x_scale, extra_offset_y_scale, extra_offset_y \
        , extra_offset_x, extra_offset_x_variable, extra_offset_y_variable, readme_content, screenshot_mode_var\
        , screenshot_mode, segmented_aiming_switch_var, stage1_scope, stage1_scope_scale, stage1_scope_variable\
        , stage1_intensity_variable, stage1_intensity, stage1_intensity_scale, stage2_scope_variable\
        , stage2_intensity_variable, stage2_scope_scale, stage2_intensity_scale, tolerance_variable, tolerance_scale\
        , ignore_colors_variable, ignore_colors, kp_scale, ki_scale, kd_scale, kp_variable, ki_variable, kd_variable

    version_number = "V2.3.3(test)"
    root = ctk.CTk()
    ctk.set_appearance_mode("dark")
    root.withdraw()
    top = tk.Toplevel(root)
    top.title("starting")
    top.attributes('-topmost', 1)

    logo_file = "logo-bird.png"
    photo = tk.PhotoImage(file=logo_file)
    label = tk.Label(top, image=photo)
    label.pack()

    def end_splash():
        top.destroy()
        root.deiconify()

    root.after(2000, end_splash)

    root.attributes('-topmost', 1)
    root.update()

    root.title("RookieAI")

    root.geometry(f"{_win_width}x{_win_height}")

    root.protocol("WM_DELETE_WINDOW", stop_program)

    root.resizable(False, True)

    tab_view = ctk.CTkTabview(root, width=320, height=500)
    tab_view.add("Basic")
    tab_view.add("Advanced")
    tab_view.add("AntiRecoil")  # Add Anti Recoil tab here
    tab_view.add("Other")
    tab_view.add("Test")

    tab_view.grid(row=0, column=0, padx=(15, 0), pady=(0, 0))

    aimbot_draw_center_frame = ctk.CTkFrame(tab_view.tab("Basic"))
    aimbot_draw_center_frame.grid(row=0, column=0, sticky='w', pady=5)
    aimbot_var = ctk.BooleanVar(value=aimbot)
    aimbot_check = ctk.CTkCheckBox(aimbot_draw_center_frame, text='Aimbot', variable=aimbot_var,
                                   command=update_values, )
    aimbot_check.grid(row=0, column=0)

    draw_center_var = ctk.BooleanVar(value=False)
    draw_center_check = ctk.CTkCheckBox(aimbot_draw_center_frame, text='Display aiming range', variable=draw_center_var,
                                        command=update_values)
    draw_center_check.grid(row=0, column=1)

    arduinoMode_frame = ctk.CTkFrame(tab_view.tab("Basic"))
    arduinoMode_frame.grid(row=1, column=0, sticky='w', pady=5)
    arduinoMode_var = ctk.BooleanVar(value=arduinoMode)
    arduinoMode_check = ctk.CTkCheckBox(arduinoMode_frame, text='Arduino Mode', variable=arduinoMode_var,
                                        command=update_values, state="DISABLED")
    arduinoMode_check.grid(row=0, column=0, sticky="w", pady=(0, 0))

    triggerType_var = tk.StringVar(value=triggerType)
    triggerType_frame = ctk.CTkFrame(tab_view.tab("Basic"))
    triggerType_frame.grid(row=2, column=0, sticky='w', pady=5)
    triggerType_label = ctk.CTkLabel(triggerType_frame, text="Trigger method :")
    triggerType_label.pack(side='left')
    options = ["press", "switch", "shift+press"]
    triggerType_option = ctk.CTkOptionMenu(triggerType_frame, variable=triggerType_var, values=options,
                                           command=update_values)
    triggerType_option.pack(side='left')
    frame = ctk.CTkLabel(tab_view.tab("Basic"))
    frame.grid(row=3, column=0, sticky='w', pady=5)
    lbl = ctk.CTkLabel(frame, text="The hotkey is :")
    lbl.grid(row=0, column=0)
    lockKey_var = ctk.StringVar()
    lockKey_var.set('Right click')
    options = ['left click', 'Right click', 'lower key']
    lockKey_menu = ctk.CTkOptionMenu(frame, variable=lockKey_var, values=options, command=update_values)
    lockKey_menu.grid(row=0, column=1)

    mouse_Side_Button_Witch_frame = ctk.CTkFrame(tab_view.tab("Basic"))
    mouse_Side_Button_Witch_frame.grid(row=4, column=0, sticky='w', pady=5)
    mouse_Side_Button_Witch_var = ctk.BooleanVar(value=False)
    mouse_Side_Button_Witch_check = ctk.CTkCheckBox(mouse_Side_Button_Witch_frame, text='Mouse side button aiming switch',
                                                    variable=mouse_Side_Button_Witch_var,
                                                    command=update_values)
    mouse_Side_Button_Witch_check.grid(row=0, column=0, sticky="w", pady=5)

    lockSpeed_variable = tk.StringVar()
    lockSpeed_variable.set(str(lockSpeed))
    LookSpeed_frame = ctk.CTkFrame(tab_view.tab("Basic"))
    LookSpeed_frame.grid(row=5, column=0, sticky='w', pady=2)
    LookSpeed_label_0 = ctk.CTkLabel(LookSpeed_frame, text="LockSpeed:")
    LookSpeed_label_0.grid(row=0, column=0)
    lockSpeed_scale = ctk.CTkSlider(LookSpeed_frame, from_=0, to=1, number_of_steps=100, command=update_values)
    lockSpeed_scale.set(lockSpeed)
    lockSpeed_scale.grid(row=0, column=1)
    LookSpeed_label_text = ctk.CTkLabel(LookSpeed_frame, textvariable=lockSpeed_variable)
    LookSpeed_label_text.grid(row=0, column=2)
    if segmented_aiming_switch:
        ban_LookSpeed_label_0 = ctk.CTkLabel(LookSpeed_frame, text="Disabled", width=200)
        ban_LookSpeed_label_0.grid(row=0, column=1, padx=(12, 0))
        ban_LookSpeed_label_text = ctk.CTkLabel(LookSpeed_frame, text="", width=25)
        ban_LookSpeed_label_text.grid(row=0, column=2)

    closest_mouse_dist_variable = tk.StringVar()
    closest_mouse_dist_variable.set(str(closest_mouse_dist))
    closest_mouse_dist_frame = ctk.CTkFrame(tab_view.tab("Basic"))
    closest_mouse_dist_frame.grid(row=6, column=0, sticky='w', pady=2)
    closest_mouse_dist_label = ctk.CTkLabel(closest_mouse_dist_frame, text="Aim range:")
    closest_mouse_dist_label.grid(row=0, column=1, sticky='w')
    closest_mouse_dist_scale = ctk.CTkSlider(closest_mouse_dist_frame, from_=0, to=300, command=update_values)
    closest_mouse_dist_scale.set(closest_mouse_dist)
    closest_mouse_dist_scale.grid(row=0, column=2, padx=(12, 0))
    closest_mouse_dist_text = ctk.CTkLabel(closest_mouse_dist_frame, textvariable=closest_mouse_dist_variable)
    closest_mouse_dist_text.grid(row=0, column=3)
    if segmented_aiming_switch:
        ban_closest_mouse_dist_label = ctk.CTkLabel(closest_mouse_dist_frame, text="Disabled", width=200)
        ban_closest_mouse_dist_label.grid(row=0, column=2, padx=(12, 0))
        ban_closest_mouse_dist_text = ctk.CTkLabel(closest_mouse_dist_frame, text="", width=30)
        ban_closest_mouse_dist_text.grid(row=0, column=3)

    kp_variable = tk.StringVar()
    kp_variable.set(f"{kp:.2f}")
    kp_frame = ctk.CTkFrame(tab_view.tab("Basic"))
    kp_frame.grid(row=8, column=0, sticky='w', pady=2)
    kp_label = ctk.CTkLabel(kp_frame, text="KP:")
    kp_label.grid(row=0, column=0, sticky='w')
    kp_scale = ctk.CTkSlider(kp_frame, from_=0, to=1, number_of_steps=100, command=update_values)
    kp_scale.set(kp)
    kp_scale.grid(row=0, column=1, padx=(12, 0))
    kp_text = ctk.CTkLabel(kp_frame, textvariable=kp_variable)
    kp_text.grid(row=0, column=2)

    ki_variable = tk.StringVar()
    ki_variable.set(f"{ki:.5f}")
    ki_frame = ctk.CTkFrame(tab_view.tab("Basic"))
    ki_frame.grid(row=9, column=0, sticky='w', pady=2)
    ki_label = ctk.CTkLabel(ki_frame, text="KI:")
    ki_label.grid(row=0, column=0, sticky='w')
    ki_scale = ctk.CTkSlider(ki_frame, from_=0, to=1, number_of_steps=1000, command=update_values)
    ki_scale.set(ki)
    ki_scale.grid(row=0, column=1, padx=(12, 0))
    ki_text = ctk.CTkLabel(ki_frame, textvariable=ki_variable)
    ki_text.grid(row=0, column=2)

    kd_variable = tk.StringVar()
    kd_variable.set(f"{kd:.5f}")
    kd_frame = ctk.CTkFrame(tab_view.tab("Basic"))
    kd_frame.grid(row=10, column=0, sticky='w', pady=2)
    kd_label = ctk.CTkLabel(kd_frame, text="KD:")
    kd_label.grid(row=0, column=0, sticky='w')
    kd_scale = ctk.CTkSlider(kd_frame, from_=0, to=1, number_of_steps=1000, command=update_values)
    kd_scale.set(kd)
    kd_scale.grid(row=0, column=1, padx=(12, 0))
    kd_text = ctk.CTkLabel(kd_frame, textvariable=kd_variable)
    kd_text.grid(row=0, column=2)

    frame = ctk.CTkLabel(tab_view.tab("Basic"))
    frame.grid(row=11, column=0, sticky='w', pady=5) 
    lbl = ctk.CTkLabel(frame, text="method of prediction:")
    lbl.grid(row=0, column=0) 
    method_of_prediction_var = ctk.StringVar()
    method_of_prediction_var.set('Disable prediction')  
    options = ['Disable prediction', 'Rate prediction', 'Pixel prediction']  
    method_of_prediction_menu = ctk.CTkOptionMenu(frame, variable=method_of_prediction_var, values=options,
                                                command=update_values)
    method_of_prediction_menu.grid(row=0, column=1)

    message_text_frame = ctk.CTkFrame(tab_view.tab("Basic"))
    message_text_frame.grid(row=12, column=0, sticky='w', pady=2)
    message_text_Label = ctk.CTkLabel(message_text_frame, text="Update announcement")
    message_text_Label.grid(row=0, column=1)
    message_text_box = ctk.CTkTextbox(message_text_frame, width=300, height=100, corner_radius=5)
    message_text_box.grid(row=1, column=1, sticky="nsew")
    message_text_box.insert("0.0", readme_content)

    target_selection_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    target_selection_frame.grid(row=1, column=0, sticky='w', pady=5)

    target_selection_label = ctk.CTkLabel(target_selection_frame, text="The current detection target is:")
    target_selection_label.grid(row=0, column=0)
    target_selection_var = ctk.StringVar()
    target_selection_var.set('enemy')
    options = list(target_mapping.keys())
    target_selection_option = ctk.CTkOptionMenu(target_selection_frame, variable=target_selection_var, values=options,
                                                command=update_values)
    target_selection_option.grid(row=0, column=1)

    confidence_variable = tk.StringVar()
    confidence_variable.set(str(confidence))
    confidence_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    confidence_frame.grid(row=2, column=0, sticky='w', pady=2)
    confidence_label = ctk.CTkLabel(confidence_frame, text="Confidence:")
    confidence_label.grid(row=0, column=1, sticky='w')
    confidence_scale = ctk.CTkSlider(confidence_frame, from_=0, to=1, number_of_steps=100, command=update_values)
    confidence_scale.set(confidence)
    confidence_scale.grid(row=0, column=2, padx=(25, 0))
    confidence_label_text = ctk.CTkLabel(confidence_frame, textvariable=confidence_variable)
    confidence_label_text.grid(row=0, column=3)

    prediction_factor_variable = tk.StringVar()
    prediction_factor_variable.set(str(prediction_factor))
    prediction_factor_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    prediction_factor_frame.grid(row=3, column=0, sticky='w', pady=2)
    prediction_factor_label = ctk.CTkLabel(prediction_factor_frame, text="Predict rate:")
    prediction_factor_label.grid(row=0, column=1, sticky='w')
    prediction_factor_scale = ctk.CTkSlider(prediction_factor_frame, from_=0, to=1, number_of_steps=100,
                                            command=update_values)
    prediction_factor_scale.set(prediction_factor)
    prediction_factor_scale.grid(row=0, column=2, padx=(12, 0))
    prediction_factor_text = ctk.CTkLabel(prediction_factor_frame, textvariable=prediction_factor_variable)
    prediction_factor_text.grid(row=0, column=3)

    extra_offset_x_variable = tk.StringVar()
    extra_offset_x_variable.set(str(extra_offset_x))
    extra_offset_x_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    extra_offset_x_frame.grid(row=4, column=0, sticky='w', pady=2)
    extra_offset_x_label = ctk.CTkLabel(extra_offset_x_frame, text="Predict X:")
    extra_offset_x_label.grid(row=0, column=0)
    extra_offset_x_scale = ctk.CTkSlider(extra_offset_x_frame, from_=0, to=20, number_of_steps=20,
                                         command=update_values)
    extra_offset_x_scale.set(extra_offset_x)
    extra_offset_x_scale.grid(row=0, column=1, padx=(4, 0))
    extra_offset_x_label_text = ctk.CTkLabel(extra_offset_x_frame, textvariable=extra_offset_x_variable)
    extra_offset_x_label_text.grid(row=0, column=2)

    extra_offset_y_variable = tk.StringVar()
    extra_offset_y_variable.set(str(extra_offset_y))
    extra_offset_y_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    extra_offset_y_frame.grid(row=5, column=0, sticky='w', pady=2)
    extra_offset_y_label = ctk.CTkLabel(extra_offset_y_frame, text="Predict Y:")
    extra_offset_y_label.grid(row=0, column=0)
    extra_offset_y_scale = ctk.CTkSlider(extra_offset_y_frame, from_=0, to=20, number_of_steps=20,
                                         command=update_values)
    extra_offset_y_scale.set(extra_offset_y)
    extra_offset_y_scale.grid(row=0, column=1, padx=(4, 0))
    extra_offset_y_label_text = ctk.CTkLabel(extra_offset_y_frame, textvariable=extra_offset_y_variable)
    extra_offset_y_label_text.grid(row=0, column=2)

    aimOffset_variable = tk.StringVar()
    aimOffset_variable.set(str(aimOffset))
    aimOffset_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    aimOffset_frame.grid(row=6, column=0, sticky='w', pady=2)
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="Aim:")
    aimOffset_label.grid(row=0, column=1, sticky='w')
    aimOffset_scale = ctk.CTkSlider(aimOffset_frame, from_=0, to=1, number_of_steps=100, command=update_values,
                                    orientation="vertical")
    aimOffset_scale.set(aimOffset)
    aimOffset_scale.grid(row=0, column=2, padx=(12, 0))
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="Crotch")
    aimOffset_label.grid(row=0, column=3, pady=(170, 0))
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="Abdomen")
    aimOffset_label.grid(row=0, column=3, pady=(80, 0))
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="Chest")
    aimOffset_label.grid(row=0, column=3, pady=(0, 5))
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="Head")
    aimOffset_label.grid(row=0, column=3, pady=(0, 170))
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, image=ctk.CTkImage(img, size=(150, 200)), text="")
    aimOffset_label.grid(row=0, column=4)
    aimOffset_text = ctk.CTkLabel(aimOffset_frame, textvariable=aimOffset_variable)
    aimOffset_text.grid(row=0, column=5, pady=(0, 0))

    screen_width_scale_variable = tk.StringVar()
    screen_width_scale_variable.set(str(screen_width))
    screen_width_scale_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    screen_width_scale_frame.grid(row=7, column=0, sticky='w', pady=2)
    screen_width_scale_label = ctk.CTkLabel(screen_width_scale_frame, text="Width:")
    screen_width_scale_label.grid(row=0, column=1, sticky='w')
    screen_width_scale = ctk.CTkSlider(screen_width_scale_frame, from_=100, to=2000, number_of_steps=190,
                                       command=update_values)
    screen_width_scale.set(screen_width)
    screen_width_scale.grid(row=0, column=2, padx=(12, 0))
    screen_width_scale_text = ctk.CTkLabel(screen_width_scale_frame, textvariable=screen_width_scale_variable)
    screen_width_scale_text.grid(row=0, column=3)
    if screenshot_mode:
        ban_screen_width_scale = ctk.CTkLabel(screen_width_scale_frame, text="Disabled DXcam enabled", width=200)
        ban_screen_width_scale.grid(row=0, column=2, padx=(12, 0))
        ban_screen_width_scale_text = ctk.CTkLabel(screen_width_scale_frame, text="", width=30)
        ban_screen_width_scale_text.grid(row=0, column=3)

    screen_height_scale_variable = tk.StringVar()
    screen_height_scale_variable.set(str(screen_height))
    screen_height_scale_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    screen_height_scale_frame.grid(row=8, column=0, sticky='w', pady=2)
    screen_height_scale_label = ctk.CTkLabel(screen_height_scale_frame, text="Height:")
    screen_height_scale_label.grid(row=0, column=1, sticky='w')
    screen_height_scale = ctk.CTkSlider(screen_height_scale_frame, from_=100, to=2000, number_of_steps=190,
                                        command=update_values)
    screen_height_scale.set(screen_height)
    screen_height_scale.grid(row=0, column=2, padx=(12, 0))
    screen_height_scale_text = ctk.CTkLabel(screen_height_scale_frame, textvariable=screen_height_scale_variable)
    screen_height_scale_text.grid(row=0, column=3)
    if screenshot_mode:
        ban_screen_height_scale = ctk.CTkLabel(screen_height_scale_frame, text="Disabled DXcam enabled", width=200)
        ban_screen_height_scale.grid(row=0, column=2, padx=(12, 0))
        ban_screen_height_scale_text = ctk.CTkLabel(screen_height_scale_frame, text="", width=30)
        ban_screen_height_scale_text.grid(row=0, column=3)

    screenshot_mode_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    screenshot_mode_frame.grid(row=9, column=0, sticky='w', pady=5)
    screenshot_mode_var = ctk.BooleanVar(value=screenshot_mode)
    screenshot_mode_check = ctk.CTkCheckBox(screenshot_mode_frame, text='Enable DXcam ', variable=screenshot_mode_var,
                                   command=update_values)
    screenshot_mode_check.grid(row=0, column=1)

    segmented_aiming_switch_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    segmented_aiming_switch_frame.grid(row=10, column=0, sticky='w', pady=5)
    segmented_aiming_switch_var = ctk.BooleanVar(value=segmented_aiming_switch)
    segmented_aiming_switch_check = ctk.CTkCheckBox(segmented_aiming_switch_frame, text='Enable segmented ', variable=segmented_aiming_switch_var,
                                   command=update_values)
    segmented_aiming_switch_check.grid(row=0, column=1)

    stage1_scope_variable = tk.StringVar()
    stage1_scope_variable.set(str(stage1_scope))
    stage1_scope_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    stage1_scope_frame.grid(row=11, column=0, sticky='w', pady=2)
    stage1_scope_label = ctk.CTkLabel(stage1_scope_frame, text="Strong range:")
    stage1_scope_label.grid(row=0, column=1, sticky='w')
    stage1_scope_scale = ctk.CTkSlider(stage1_scope_frame, from_=0, to=300, number_of_steps=300, command=update_values)
    stage1_scope_scale.set(stage1_scope)
    stage1_scope_scale.grid(row=0, column=2, padx=(12, 0))
    stage1_scope_text = ctk.CTkLabel(stage1_scope_frame, textvariable=stage1_scope_variable)
    stage1_scope_text.grid(row=0, column=3)
    if not segmented_aiming_switch:
        ban_screen_height_scale = ctk.CTkLabel(stage1_scope_frame, text="Segmented disabled", width=200)
        ban_screen_height_scale.grid(row=0, column=2, padx=(12, 0))
        ban_screen_height_scale_text = ctk.CTkLabel(stage1_scope_frame, text="", width=30)
        ban_screen_height_scale_text.grid(row=0, column=3)

    stage1_intensity_variable = tk.StringVar()
    stage1_intensity_variable.set(str(stage1_intensity))
    stage1_intensity_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    stage1_intensity_frame.grid(row=12, column=0, sticky='w', pady=2)
    stage1_intensity_label = ctk.CTkLabel(stage1_intensity_frame, text="Strong speed:")
    stage1_intensity_label.grid(row=0, column=1, sticky='w')
    stage1_intensity_scale = ctk.CTkSlider(stage1_intensity_frame, from_=0, to=1, number_of_steps=100, command=update_values)
    stage1_intensity_scale.set(stage1_intensity)
    stage1_intensity_scale.grid(row=0, column=2, padx=(12, 0))
    stage1_intensity_text = ctk.CTkLabel(stage1_intensity_frame, textvariable=stage1_intensity_variable)
    stage1_intensity_text.grid(row=0, column=3)
    if not segmented_aiming_switch:
        ban_stage1_intensity_scale = ctk.CTkLabel(stage1_intensity_frame, text="Segmented disabled", width=200)
        ban_stage1_intensity_scale.grid(row=0, column=2, padx=(12, 0))
        ban_stage1_intensity_scale = ctk.CTkLabel(stage1_intensity_frame, text="", width=30)
        ban_stage1_intensity_scale.grid(row=0, column=3)

    stage2_scope_variable = tk.StringVar()
    stage2_scope_variable.set(str(stage2_intensity))
    stage2_scope_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    stage2_scope_frame.grid(row=13, column=0, sticky='w', pady=2)
    stage2_scope_label = ctk.CTkLabel(stage2_scope_frame, text="Soft range:")
    stage2_scope_label.grid(row=0, column=1, sticky='w')
    stage2_scope_scale = ctk.CTkSlider(stage2_scope_frame, from_=0, to=300, number_of_steps=300, command=update_values)
    stage2_scope_scale.set(stage2_scope)
    stage2_scope_scale.grid(row=0, column=2, padx=(12, 0))
    stage2_scope_text = ctk.CTkLabel(stage2_scope_frame, textvariable=stage2_scope_variable)
    stage2_scope_text.grid(row=0, column=3)
    if not segmented_aiming_switch:
        ban_stage2_scope_scale = ctk.CTkLabel(stage2_scope_frame, text="Segmented disabled", width=200)
        ban_stage2_scope_scale.grid(row=0, column=2, padx=(12, 0))
        ban_stage2_scope_scale = ctk.CTkLabel(stage2_scope_frame, text="", width=30)
        ban_stage2_scope_scale.grid(row=0, column=3)

    stage2_intensity_variable = tk.StringVar()
    stage2_intensity_variable.set(str(stage2_intensity))
    stage2_intensity_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    stage2_intensity_frame.grid(row=14, column=0, sticky='w', pady=2)
    stage2_intensity_label = ctk.CTkLabel(stage2_intensity_frame, text="Soft speed:")
    stage2_intensity_label.grid(row=0, column=1, sticky='w')
    stage2_intensity_scale = ctk.CTkSlider(stage2_intensity_frame, from_=0, to=1, number_of_steps=100, command=update_values)
    stage2_intensity_scale.set(stage2_intensity)
    stage2_intensity_scale.grid(row=0, column=2, padx=(12, 0))
    stage2_intensity_text = ctk.CTkLabel(stage2_intensity_frame, textvariable=stage2_intensity_variable)
    stage2_intensity_text.grid(row=0, column=3)
    if not segmented_aiming_switch:
        ban_stage2_intensity_scale = ctk.CTkLabel(stage2_intensity_frame, text="Segmented disabled", width=200)
        ban_stage2_intensity_scale.grid(row=0, column=2, padx=(12, 0))
        ban_stage2_intensity_scale = ctk.CTkLabel(stage2_intensity_frame, text="", width=30)
        ban_stage2_intensity_scale.grid(row=0, column=3)

    tolerance_variable = tk.StringVar()
    tolerance_variable.set(str(tolerance))
    tolerance_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    tolerance_frame.grid(row=15, column=0, sticky='w', pady=2)
    tolerance_label = ctk.CTkLabel(tolerance_frame, text="Tolerance:")
    tolerance_label.grid(row=0, column=1, sticky='w')
    tolerance_scale = ctk.CTkSlider(tolerance_frame, from_=0, to=100, number_of_steps=100, command=update_values)
    tolerance_scale.set(tolerance)
    tolerance_scale.grid(row=0, column=2, padx=(12, 0))
    tolerance_label_text = ctk.CTkLabel(tolerance_frame, textvariable=tolerance_variable)
    tolerance_label_text.grid(row=0, column=3)

    ignore_colors_variable = tk.StringVar()
    ignore_colors_variable.set(str(ignore_colors))
    ignore_colors_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    ignore_colors_frame.grid(row=16, column=0, sticky='w', pady=2)
    ignore_colors_label = ctk.CTkLabel(ignore_colors_frame, text="Ignore Colors:")
    ignore_colors_label.grid(row=0, column=1, sticky='w')
    ignore_colors_entry = ctk.CTkEntry(ignore_colors_frame, textvariable=ignore_colors_variable)
    ignore_colors_entry.grid(row=0, column=2, padx=(12, 0))

    setting_frame = ctk.CTkFrame(tab_view.tab("Other"), width=300, height=300)
    setting_frame.grid(row=9, column=0, sticky='w', pady=2)
    setting_frame.grid_propagate(False)

    model_file_label = tk.Label(setting_frame, text="No model ", width=40, anchor='e')
    model_file_label.grid(row=0, column=0, sticky="w")

    model_file_button = ctk.CTkButton(setting_frame, text="Select model file ",
                                      command=choose_model)
    model_file_button.grid(row=1, column=0, padx=(0, 245), pady=(5, 0))

    config_file_button = ctk.CTkButton(setting_frame, text="Open the config ",
                                       command=open_settings_config)
    config_file_button.grid(row=1, column=0, padx=(55, 0), pady=(5, 0))

    save_button = ctk.CTkButton(setting_frame, text='Save settings', width=20, command=save_settings)
    save_button.grid(row=2, column=0, padx=(0, 320), pady=(10, 0))

    load_button = ctk.CTkButton(setting_frame, text='Load settings', width=20, command=load_settings,
                                state="DISABLED")
    load_button.grid(row=2, column=0, padx=(0, 120), pady=(10, 0))

    restart_button = ctk.CTkButton(setting_frame, text='Restart software', width=20, command=restart_program)
    restart_button.grid(row=3, column=0, padx=(0, 320), pady=(10, 0))

    version_number_text1 = ctk.CTkLabel(setting_frame, text="current version:", width=30)
    version_number_text1.bind("<Button-1>", command=open_web)
    version_number_text1.grid(row=3, column=0, padx=(10, 0), pady=(120, 0))
    version_number1 = ctk.CTkLabel(setting_frame, text=version_number, width=30)
    version_number1.bind("<Button-1>", command=open_web)
    version_number1.grid(row=3, column=0, padx=(120, 0), pady=(120, 0))
    version_number_text2 = ctk.CTkLabel(setting_frame, text="The latest version:", width=30)
    version_number_text2.bind("<Button-1>", command=open_web)
    version_number_text2.grid(row=4, column=0, padx=(10, 0), pady=(0, 0))
    version_number2 = ctk.CTkLabel(setting_frame, text=":(", width=30)
    version_number2.bind("<Button-1>", command=open_web)
    version_number2.grid(row=4, column=0, padx=(120, 0), pady=(0, 0))
    version = fetch_readme_version_number()
    version_number2.configure(text=version)
    if version == version_number1.cget("text"):
        version_number2.configure(text=version, text_color="green")
    else:
        version_number2.configure(text=version, text_color="red")
    image_label_frame = ctk.CTkFrame(tab_view.tab("Test"), height=370, width=305)
    image_label_frame.grid(row=1, column=0, sticky='w')
    image_label_frame.grid_propagate(False)
    image_label_switch = ctk.CTkSwitch(image_label_frame, text="Internal Test (affects performance)", onvalue=True, offvalue=False,
                                       command=update_values)
    image_label_switch.grid(row=0, column=0, padx=(0, 0), sticky='w')
    image_label = tk.Label(image_label_frame)
    image_label.grid(row=1, column=0, padx=(0, 0))
    image_label_FPSlabel = ctk.CTkLabel(image_label_frame, text="FPS：", width=40)
    image_label_FPSlabel.grid(row=2, column=0, padx=(0, 0), sticky='w')

    load_settings()
    update_values()

    # AntiRecoil Tab
    antiRecoil_tab = tab_view.tab("AntiRecoil")
    antiRecoil_layout = ctk.CTkFrame(antiRecoil_tab)
    antiRecoil_layout.pack(fill="both", expand=True, padx=10, pady=10)

    # Instructions Label
    instructions = """
    Recoil Controls: 
    
    - Home: On  Off

    - Enter: Save current profile.

    - Up Arrow: Increase y_movement.

    - Down Arrow: Decrease y_movement.

    - Right Arrow: Increase x_movement.

    - Left Arrow: Decrease x_movement.

    - Page Up: Switch to the next profile.

    - Page Down: Switch to the previous profile.
    """
    instructions_label = ctk.CTkLabel(antiRecoil_layout, text=instructions, anchor="w", justify="left")
    instructions_label.grid(row=0, column=0, sticky="w", pady=5)

    root.mainloop()

def update_values(*args):
    global aimbot, lockSpeed, triggerType, arduinoMode, lockKey, lockKey_var, confidence, closest_mouse_dist, \
        closest_mouse_dist_scale, screen_width, screen_height, model_file, aimOffset, draw_center, \
        mouse_Side_Button_Witch, lockSpeed_text, LookSpeed_label_1, test_images_GUI, target_selection_str, \
        prediction_factor_scale, prediction_factor, method_of_prediction, extra_offset_x, extra_offset_y, \
        screenshot_mode, segmented_aiming_switch, stage1_scope, stage1_intensity, \
        stage1_intensity_scale, stage2_scope, stage2_intensity, stage2_intensity_scale, \
        aimOffset_Magnification_x, tolerance, ignore_colors, tolerance_variable, ignore_colors_variable, \
        kp, ki, kd

    print("update_values function was called (Configuration has been updated)")
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
    stage1_scope = stage1_scope_scale.get()
    stage1_intensity = stage1_intensity_scale.get()
    stage2_scope = stage2_scope_scale.get()
    stage2_intensity = stage2_intensity_scale.get()
    tolerance = int(tolerance_scale.get())
    try:
        ignore_colors = [list(map(int, color.strip('()').split(','))) for color in ignore_colors_variable.get().strip('[]').split('), (')]
    except ValueError:
        print("Invalid color input")
        ignore_colors = [[62, 203, 236]]  # valor padrão

    lockSpeed = round(lockSpeed_scale.get(), 2)
    lockSpeed_variable.set(str(lockSpeed))
    confidence = round(confidence_scale.get(), 2)
    confidence_variable.set(str(confidence))
    closest_mouse_dist = int(closest_mouse_dist_scale.get())
    closest_mouse_dist_variable.set(str(closest_mouse_dist))
    prediction_factor = round(prediction_factor_scale.get(), 2)
    prediction_factor_variable.set(str(prediction_factor))
    extra_offset_x = round(extra_offset_x_scale.get())
    extra_offset_x_variable.set(str(extra_offset_x))
    extra_offset_y = round(extra_offset_y_scale.get())
    extra_offset_y_variable.set(str(extra_offset_y))
    aimOffset = round(aimOffset_scale.get(), 2)
    aimOffset_variable.set(str(aimOffset))
    screen_width = int(screen_width_scale.get())
    screen_width_scale_variable.set(str(screen_width))
    screen_height = int(screen_height_scale.get())
    screen_height_scale_variable.set(str(screen_height))
    stage1_scope = int(stage1_scope_scale.get())
    stage1_scope_variable.set(str(stage1_scope))
    stage1_intensity = round(stage1_intensity_scale.get(), 2)
    stage1_intensity_variable.set(str(stage1_intensity))
    stage2_scope = int(stage2_scope_scale.get())
    stage2_scope_variable.set(str(stage2_scope))
    stage2_intensity = round(stage2_intensity_scale.get(), 2)
    stage2_intensity_variable.set(str(stage2_intensity))
    tolerance_variable.set(str(tolerance))

    kp = round(kp_scale.get(), 2)
    kp_variable.set(f"{kp:.2f}")
    ki = round(ki_scale.get(), 5)
    ki_variable.set(f"{ki:.5f}")
    kd = round(kd_scale.get(), 5)
    kd_variable.set(f"{kd:.5f}")

    if 'pid' in globals():
        pid.update_parameters(kp, ki, kd)

    key = lockKey_var.get()
    if key == 'left click':
        lockKey = 0x01
    elif key == 'Right click':
        lockKey = 0x02
    elif key == 'lower key':
        lockKey = 0x05


def save_settings():
    global model_file, ignore_colors, kp, ki, kd

    try:
        ignore_colors = [list(map(int, color.strip('()').split(','))) for color in ignore_colors_variable.get().strip('[]').split('), (')]
    except ValueError:
        print("Invalid color input")
        ignore_colors = [[62, 203, 236]]  # valor padrão

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
        'screenshot_mode': screenshot_mode_var.get(),
        'segmented_aiming_switch': segmented_aiming_switch_var.get(),
        'aimOffset': aimOffset_scale.get(),
        'model_file': model_file,
        'prediction_factor': prediction_factor_scale.get(),
        'method_of_prediction': method_of_prediction_var.get(),
        'extra_offset_x': extra_offset_x_scale.get(),
        'extra_offset_y': extra_offset_y_scale.get(),
        'stage1_intensity': stage1_intensity_scale.get(),
        'stage1_scope': stage1_scope_scale.get(),
        'stage2_intensity': stage2_intensity_scale.get(),
        'stage2_scope': stage2_scope_scale.get(),
        'tolerance': tolerance,  
        'ignore_colors': ignore_colors,
        'kp': kp_scale.get(),
        'ki': ki_scale.get(),
        'kd': kd_scale.get()
    }

    try:
        with open('settings.json', 'r') as f:
            current_settings = json.load(f)
    except FileNotFoundError:
        current_settings = {}
    current_settings.update(new_settings)
    with open('settings.json', 'w') as f:
        json.dump(current_settings, f, sort_keys=True, indent=4)
    print("Settings saved successfully!")

def load_prefix_variables():  
    global model_file, screenshot_mode, segmented_aiming_switch, crawl_information
    print('Loading prefix variables...')
    try:
        with open('settings.json', 'r') as f:
            settings = json.load(f)
        screenshot_mode = settings.get("screenshot_mode", False)  
        segmented_aiming_switch = settings.get("segmented_aiming_switch", False)  
        crawl_information = settings.get("crawl_information", False)  
        print("Prefix variables loaded successfully!")
    except FileNotFoundError:
        print('[ERROR] Settings file not found; skipping loading settings')

def load_settings():
    global model_file, test_window_frame, screenshot_mode, crawl_information, DXcam_screenshot, dxcam_maxFPS, \
        loaded_successfully, stage1_scope, stage1_intensity, stage2_scope, stage2_intensity, segmented_aiming_switch, \
        aimOffset_Magnification_x, tolerance, ignore_colors, kp, ki, kd
    print('Loading settings...')
    try:
        with open('settings.json', 'r') as f:
            settings = json.load(f)

        aimbot_var.set(settings.get('aimbot', True))
        lockSpeed_scale.set(settings.get('lockSpeed', 0.7))
        triggerType_var.set(settings.get('triggerType', "press"))
        arduinoMode_var.set(settings.get('arduinoMode', False))
        lockKey_var.set(settings.get('lockKey', "left click"))
        mouse_Side_Button_Witch_var.set(settings.get('mouse_Side_Button_Witch', True))
        method_of_prediction_var.set(settings.get('method_of_prediction', "Disable prediction"))
        confidence_scale.set(settings.get('confidence', 0.5))
        extra_offset_x_scale.set(settings.get('extra_offset_x', 5))
        extra_offset_y_scale.set(settings.get('extra_offset_y', 5))
        prediction_factor_scale.set(settings.get('prediction_factor', 0.5))
        closest_mouse_dist_scale.set(settings.get('closest_mouse_dist', 160))
        screen_width_scale.set(settings.get('screen_width', 360))
        screen_height_scale.set(settings.get('screen_height', 360))
        aimOffset_scale.set(settings.get('aimOffset', 0.4))
        aimOffset_Magnification_x = settings.get('aimOffset_Magnification_x', 0)
        model_file = settings.get('model_file', None)
        model_file_label.config(text=model_file or "No model file selected yet")
        test_window_frame = settings.get('test_window_frame', False)
        crawl_information = settings.get("crawl_information", True)
        screenshot_mode = settings.get("screenshot_mode", False)
        DXcam_screenshot = settings.get("DXcam_screenshot", 360)
        dxcam_maxFPS = settings.get('dxcam_maxFPS', 30)
        segmented_aiming_switch = settings.get('segmented_aiming_switch', False)
        stage1_scope_scale.set(settings.get('stage1_scope', 50))
        stage1_intensity_scale.set(settings.get('stage1_intensity', 0.8))
        stage2_scope_scale.set(settings.get('stage2_scope', 170))
        stage2_intensity_scale.set(settings.get('stage2_intensity', 0.4))
        tolerance = settings.get('tolerance', 80)
        ignore_colors = settings.get('ignore_colors', [[62, 203, 236]])
        kp_scale.set(settings.get('kp', 1.0))
        ki_scale.set(settings.get('ki', 0.1))
        kd_scale.set(settings.get('kd', 0.05))

        # Atualizar os valores das variáveis da interface
        tolerance_scale.set(tolerance)
        tolerance_variable.set(str(tolerance))
        ignore_colors_variable.set(str(ignore_colors))
        kp_variable.set(str(kp_scale.get()))
        ki_variable.set(str(ki_scale.get()))
        kd_variable.set(str(kd_scale.get()))

        print("Settings loaded successfully!")
        loaded_successfully = True
    except FileNotFoundError:
        print('[ERROR] Settings file not found; skipping loading settings')
        pass

class PIDController:
    def __init__(self, kp, ki, kd, prediction_time=5, integral_limit=500, deadband=1.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral_x = 0
        self.integral_y = 0
        self.last_error_x = 0
        self.last_error_y = 0
        self.last_time = time.time()
        self.prediction_time = prediction_time
        self.integral_limit = integral_limit
        self.deadband = deadband

    def update_parameters(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd

    def predict_target_position(self, target_x, target_y, prev_x, prev_y):
        velocity_x = target_x - prev_x
        velocity_y = target_y - prev_y
        
        predicted_x = target_x + velocity_x
        predicted_y = target_y + velocity_y

        return predicted_x, predicted_y

    def calculate_movement(self, target_x, target_y, center_x, center_y):
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time

        if dt == 0:
            dt = 1e-6  
        error_x = target_x - center_x
        error_y = target_y - center_y

        
        if abs(error_x) < self.deadband:
            error_x = 0
        if abs(error_y) < self.deadband:
            error_y = 0

        prop_x = self.kp * error_x
        prop_y = self.kp * error_y

        self.integral_x += error_x * dt
        self.integral_y += error_y * dt

        self.integral_x = max(min(self.integral_x, self.integral_limit), -self.integral_limit)
        self.integral_y = max(min(self.integral_y, self.integral_limit), -self.integral_limit)
        integral_x = self.ki * self.integral_x
        integral_y = self.ki * self.integral_y

        deriv_x = self.kd * (error_x - self.last_error_x) / dt
        deriv_y = self.kd * (error_y - self.last_error_y) / dt
        self.last_error_x = error_x
        self.last_error_y = error_y

        move_x = prop_x + integral_x + deriv_x
        move_y = prop_y + integral_y + deriv_y

        move_x = np.clip(move_x, -1e6, 1e6)
        move_y = np.clip(move_y, -1e6, 1e6)

        return move_x, move_y

def rgb_to_lab(rgb_color):
    rgb_normalized = np.array(rgb_color, dtype=np.float32) / 255.0
    return rgb2lab([[rgb_normalized]])[0][0]

def is_color_similar(color1, color2, tolerance):
    lab1 = rgb_to_lab(color1)
    lab2 = rgb_to_lab(color2)
    distance = deltaE_cie76(lab1, lab2)
    print(f"Color distance: {distance}, Tolerance: {tolerance}")
    return distance <= tolerance

def count_pixels_of_color(image, target_color, tolerance=30):
    target_color_bgr = target_color[::-1] 
    lower_bound = np.array([max(0, c - tolerance) for c in target_color_bgr], dtype=np.uint8)
    upper_bound = np.array([min(255, c + tolerance) for c in target_color_bgr], dtype=np.uint8)
    mask = cv2.inRange(image, lower_bound, upper_bound)
    return cv2.countNonZero(mask)

def filter_color_above_box(frame_, box, ignore_colors, height=33, width_ratio=1, tolerance=80):
    x1, y1, x2, y2 = map(int, box)
    box_width = x2 - x1
    region_width = int(box_width * width_ratio)
    center_x = x1 + box_width // 2
    region_x1 = max(0, center_x - region_width // 2)
    region_x2 = min(frame_.shape[1], center_x + region_width // 2)
    region_above = frame_[max(0, y1-height):y1, region_x1:region_x2]

    if region_above.size == 0:
        return False

    for ignore_color in ignore_colors:
        ignore_color_count = count_pixels_of_color(region_above, ignore_color, tolerance)
        print(f"Ignore color ({ignore_color}) pixel count: {ignore_color_count}")

        if ignore_color_count >= 5:
            ignore_color_bgr = ignore_color[::-1]  
            #cv2.rectangle(frame_, (region_x1, max(0, y1-height)), (region_x2, y1), ignore_color_bgr, -1)  
            print(f"Filled region above box with color: {ignore_color}")
            return True

    print("Box passed the color filter")
    return False

def calculate_distances(
        monitor: dict,
        results: list,
        frame_: np.array,
        aimbot: bool,
        lockSpeed: float,
        arduinoMode: bool,
        lockKey: int,
        triggerType: str,
):
    global boxes, cWidth, cHeight, extra_offset_x, extra_offset_y, tolerance, kp, ki, kd, pid

    minDist = float('inf')
    minBox = None
    cWidth = monitor["width"] / 2
    cHeight = monitor["height"] / 2
    if draw_center:
        if screenshot_mode:
            cWidth = DXcam_screenshot // 2
            cHeight = DXcam_screenshot // 2

        if segmented_aiming_switch: 
            cv2.circle(frame_, (int(cWidth), int(cHeight)), int(stage2_scope), (255, 255, 255), 1)
            cv2.circle(frame_, (int(cWidth), int(cHeight)), int(stage1_scope), (255, 255, 255), 1)
            cv2.circle(frame_, (int(cWidth), int(cHeight)), radius=3, color=(255, 255, 255), thickness=-1)
        else:
            cv2.circle(frame_, (int(cWidth), int(cHeight)), int(closest_mouse_dist), (255, 255, 255), 1)
            cv2.circle(frame_, (int(cWidth), int(cHeight)), radius=3, color=(255, 255, 255), thickness=-1)

    for r in results:
        boxes = r.boxes.xyxy.cpu().numpy()

    current_target = None
    for box in boxes:
        if filter_color_above_box(frame_, box, ignore_colors, tolerance=tolerance):
            print("Box ignored due to ignored color filter")
            continue

        x1, y1, x2, y2 = box
        centerx = (x1 + x2) / 2
        centery = (y1 + y2) / 2
        cv2.circle(frame_, (int(centerx), int(centery)), 3, (0, 255, 255), -1)
        dist = np.sqrt((cWidth - centerx) ** 2 + (cHeight - centery) ** 2)
        dist = round(dist, 1)
        print(f"Distance: {dist}, Closest mouse dist: {closest_mouse_dist}")    

        if dist < minDist and dist <= closest_mouse_dist:   
            minDist = dist
            minBox = box

        location = (int(centerx), int(centery))
        cv2.putText(frame_, f'dist: {dist}', location, cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 1)

    if minBox is not None:
        min_x1, min_y1, min_x2, min_y2 = minBox

        cv2.rectangle(frame_, (int(minBox[0]), int(minBox[1])), (int(minBox[2]), int(minBox[3])), (0, 0, 255), 2)
        center_text_x = int((minBox[0] + minBox[2]) / 2)
        center_text_y = int((minBox[1] + minBox[3]) / 2)
        location = (center_text_x, center_text_y)
        cv2.putText(frame_, f'dist: {minDist}', location, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 1)

        box_centerx = (min_x1 + min_x2) / 2
        box_centery = (min_y1 + min_y2) / 2
        distance_to_top_border = box_centery - min_y1
        distance_to_left_border = box_centerx - min_x1

        aimOffset_y = distance_to_top_border * aimOffset
        aimOffset_x = distance_to_left_border * aimOffset_Magnification_x

        cv2.circle(frame_, (int(box_centerx - aimOffset_x), int(box_centery - aimOffset_y)), 3, (255, 0, 0), -1)

        offset_centerx = box_centerx - aimOffset_x
        offset_centery = box_centery - aimOffset_y

        centerx = offset_centerx - cWidth
        centery = offset_centery - cHeight

        offset_dist = np.sqrt((cWidth - offset_centerx) ** 2 + (cHeight - offset_centery) ** 2)
        offset_dist = round(offset_dist, 1)
        offset_location = (int(offset_centerx), int(offset_centery))
        cv2.putText(frame_, f'offset_dist: {offset_dist}', offset_location, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 1)

        if segmented_aiming_switch:
            if offset_dist < stage1_scope:
                lockSpeed = stage1_intensity
            elif offset_dist < stage2_scope:
                lockSpeed = stage2_intensity

        if 'pid' not in globals():
            pid = PIDController(kp=kp, ki=ki, kd=kd)
        pid.update_parameters(kp, ki, kd)

        move_x, move_y = pid.calculate_movement(offset_centerx, offset_centery, cWidth, cHeight)

        lockKey_pressed = win32api.GetKeyState(lockKey) & 0x8000
        shift_pressed = win32api.GetKeyState(win32con.VK_SHIFT) & 0x8000
        xbutton2_pressed = win32api.GetKeyState(0x05) & 0x8000

        if triggerType == "switch":
            if aimbot and (win32api.GetKeyState(lockKey) or (mouse_Side_Button_Witch and xbutton2_pressed)):
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(move_x), int(move_y), 0, 0)

        elif triggerType == "press":
            if aimbot and (lockKey_pressed or (mouse_Side_Button_Witch and xbutton2_pressed)):
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(move_x), int(move_y), 0, 0)
            elif not (lockKey_pressed or (mouse_Side_Button_Witch and xbutton2_pressed)):
                pass

        elif triggerType == "shift+press":
            if aimbot and ((lockKey_pressed and shift_pressed) or (mouse_Side_Button_Witch and xbutton2_pressed)):
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(move_x), int(move_y), 0, 0)
            elif not ((lockKey_pressed and shift_pressed) or (mouse_Side_Button_Witch and xbutton2_pressed)):
                pass

    return frame_


def main_program_loop(model):  
    global start_time, gc_time, closest_mouse_dist, lockSpeed, triggerType, arduinoMode, lockKey, confidence \
        , run_threads, aimbot, image_label, test_images_GUI, target_selection, target_selection_str, target_mapping \
        , target_selection_var, prediction_factor, should_break, readme_content

    frame_counter = 0
    start_time = time.time()
    while True:
        print("Waiting for loading to complete")
        if loaded_successfully:
            DXcam()
            break

    if not screenshot_mode:
        print("MSS screenshot selected, close bettercam")
        camera.stop()

    if test_window_frame:
        cv2.namedWindow('frame', cv2.WINDOW_NORMAL)
        cv2.setWindowProperty('frame', cv2.WND_PROP_TOPMOST, 1)

    while run_threads:
        monitor = calculate_screen_monitor(screen_width, screen_height)
        try:
            target_selection = target_mapping[target_selection_str]
        except KeyError:
            print(f"Key {target_selection_str} not found in target_mapping.（加载中）")

        if not screenshot_mode:
            print("Current screenshot mode: mss")
            frame = capture_screen(monitor, sct)  
        elif screenshot_mode:
            print("Current screenshot mode: bettercam")
            frame = camera.get_latest_frame()  
        # ---------------------------------------------------------------------------
        results = model.predict(frame, save=False,  conf=confidence, half=True, agnostic_nms=True, iou=0.7
                                , classes=[target_selection], device="cuda:0")
        # ---------------------------------------------------------------------------

        boxes = results[0].boxes.xyxy.cpu().numpy()  
        frame_ = frame.copy()
        for box in boxes:
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(frame_, (x1, y1), (x2, y2), (0, 255, 0), 2)

        try:
            frame_ = calculate_distances(monitor, results, frame_, aimbot, lockSpeed, arduinoMode, lockKey, triggerType)
        except TypeError:
            print('lockKey An error occurred in the value. But it doesnt matter')
        try:
            end_time = time.time()
            frame_, frame_counter, start_time = update_and_display_fps(frame_, frame_counter, start_time, end_time)
        except NameError:
            print("ERROR: Frame rate display failed (loading)")

        if test_window_frame:
            should_break = display_debug_window(frame_)
        if test_images_GUI:
            screen_width_1, screen_height_1 = pyautogui.size()
            desired_size = get_desired_size(screen_width_1, screen_height_1)
            img = cv2.cvtColor(frame_, cv2.COLOR_BGR2RGB)
            im = Image.fromarray(img)
            desired_size = desired_size  
            im_resized = im.resize(desired_size)  
            imgtk = ImageTk.PhotoImage(image=im_resized)
            image_label.config(image=imgtk)
            image_label.image = imgtk
        if test_window_frame:
            if should_break:
                break

        if time.time() - gc_time >= 60:
            gc.collect()
            gc_time = time.time()
    pass

def stop_program():  
    global run_threads, Thread_to_join, root
    camera.stop()
    run_threads = False
    if Thread_to_join:
        Thread_to_join.join()  
    if root is not None:
        root.quit()
        root.destroy()  

    os._exit(0)  

def restart_program(): 
    python = sys.executable
    os.execl(python, python, *sys.argv)

def Initialization_parameters(): 
    model = load_model_file()
    aimbot = True
    lockSpeed = 1
    arduinoMode = False
    triggerType = "press"
    lockKey = 0x02
    aimOffset = 25
    screen_width = 640
    screen_height = 640

    return (model, aimbot, lockSpeed, arduinoMode, triggerType, lockKey, aimOffset, screen_width,
            screen_height)

### ---------------------------------------main-------------------------------------------------------------------------
if __name__ == "__main__":
    p = psutil.Process(os.getpid())
    p.nice(psutil.REALTIME_PRIORITY_CLASS)

    load_prefix_variables()
    crawl_information_by_github()

    (model, aimbot, lockSpeed, arduinoMode, triggerType, lockKey, aimOffset, screen_width, screen_height) \
        = Initialization_parameters()

    freeze_support()

    recoil_thread = threading.Thread(target=recoil_control.control_recoil)
    recoil_thread.daemon = True
    recoil_thread.start()
    
    thread1 = threading.Thread(target=main_program_loop, args=(model,))
    thread1.start()

    create_gui_tkinter()
    thread1.join()
