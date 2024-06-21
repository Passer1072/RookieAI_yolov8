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
import numpy as np
import pyautogui
import win32api
import win32con
import customtkinter as ctk
from mss import mss
from ultralytics import YOLO

###------------------------------------------Global Variables---------------------------------------------------------------------

# Choose model
model_file = "yolov8n.pt"

# Create an MSS object (for capturing screenshots)
sct = mss()

# returns a DXCamera instance on primary monitor
camera = bettercam.create(output_idx=0, output_color="BGR", max_buffer_len=2048)  # Primary monitor's BetterCam instance

# Screenshot mode (do not change)
screenshot_mode = False

# Default MSS screenshot dimensions (pixels)
screen_width = 640
screen_height = 640

# DXcam screenshot resolution
DXcam_screenshot = 360

# Initialize frame counter (for frame rate calculation)
frame_counter = 0
start_time = time.time()
start_test_time = time.time()

# Initialize garbage collection timer
gc_time = time.time()

# Initialize DXcam max FPS
dxcam_maxFPS = 30

# Aimbot range
closest_mouse_dist = 100

# Confidence setting
confidence = 0.65

# Vertical aim offset
aimOffset = 0.5

# Horizontal aim offset. Leftmost is 1, rightmost is -1, middle (default) is 0, can be fractional
aimOffset_Magnification_x = 0

# Prediction factor
prediction_factor = 0.1

# Define extra pixel offset
extra_offset_x = 5  # Extra move 5 pixels in x direction
extra_offset_y = 5  # Extra move 10 pixels in y direction

# Software window size
_win_width = 350
_win_height = 700

# Object recognition limit (enemy/friend recognition)
classes = 0

# Segmented aiming
stage1_scope = 55  # Strong lock range
stage1_intensity = 0.8  # Strong lock intensity
stage2_scope = 170  # Soft lock range
stage2_intensity = 0.4  # Soft lock intensity

# Segmented aiming switch
segmented_aiming_switch = False

# Enable external test window (slightly affects performance)
test_window_frame = False

# Enable internal test screen (greatly affects performance)
test_images_GUI = False

# Skip announcement retrieval
crawl_information = False

# Initialization successful flag
loaded_successfully = False

# Target list
target_mapping = {'enemy': 0, 'friend': 1}

# Human body diagram
img = Image.open("body_photo.png")

# Define trigger type and other parameters
# Declare variables for GUI controls globally
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
antirecoil_var = None  # Add a global variable for antirecoil

# Other global variables
Thread_to_join = None
restart_thread = False
run_threads = True
draw_center = True

###------------------------------------------def section---------------------------------------------------------------------

def calculate_screen_monitor(capture_width=640, capture_height=640):  # Screenshot area
    # Get screen width and height
    screen_width, screen_height = pyautogui.size()

    # Calculate center point coordinates
    center_x, center_y = screen_width // 2, screen_height // 2

    # Define the screenshot area, with the center point as the base, capturing an area of capture_width x capture_height
    monitor = {
        "top": center_y - capture_height // 2,
        "left": center_x - capture_width // 2,
        "width": capture_width,
        "height": capture_height,
    }
    return monitor

def calculate_frame_rate(frame_counter, start_time, end_time):  # Frame rate calculation
    # Avoid division by zero
    if end_time - start_time != 0:
        frame_rate = frame_counter / (end_time - start_time)
        # Reset frame_counter and start_time for the next second
        frame_counter = 0
        start_time = time.time()
    else:
        frame_rate = 0  # Or assign something that makes sense in your case
    return frame_rate, frame_counter, start_time

def update_and_display_fps(frame_, frame_counter, start_time, end_time):
    frame_counter += 1
    frame_rate, frame_counter, start_time = calculate_frame_rate(frame_counter, start_time, end_time)

    # Continue displaying the frame rate in the cv2 window
    cv2.putText(frame_, f"FPS: {frame_rate:.0f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Display the frame rate on the graphical user interface
    text_fps = "Real-time FPS: {:.0f}".format(frame_rate)
    image_label_FPSlabel.configure(text=text_fps)
    print(f"FPS: {frame_rate:.0f}")  # Print frame rate in the console (if needed)

    return frame_, frame_counter, start_time

def capture_screen(monitor, sct):  # MSS screenshot method
    # Use MSS to capture the screen
    screenshot = sct.grab(monitor)
    # Convert the PIL/Pillow Image to an OpenCV ndarray object, then convert from BGR to RGB
    frame = np.array(screenshot)[:, :, :3]

    return frame

def DXcam():
    # Get screen width and height
    screen_width, screen_height = pyautogui.size()

    # Calculate screenshot area
    left, top = (screen_width - DXcam_screenshot) // 2, (screen_height - DXcam_screenshot) // 2
    right, bottom = left + DXcam_screenshot, top + DXcam_screenshot
    region = (left, top, right, bottom)

    camera.start(region=region, video_mode=True, target_fps=dxcam_maxFPS)  # Optional parameter for capturing area

def display_debug_window(frame):  # Debug window
    # Display the image in the main loop
    cv2.imshow('frame', frame)

    if cv2.waitKey(1) & 0xFF == ord('.'):
        cv2.destroyAllWindows()
        return True
    else:
        return False

def get_desired_size(screen_width_1, screen_height_1):
    # Determine the adjusted size based on screen size
    if screen_width_1 == 1920 and screen_height_1 == 1080:
        desired_size = (300, 300)
    elif screen_width_1 >= 2560 and screen_height_1 >= 1440:
        desired_size = (370, 370)
    else:
        desired_size = (300, 300)  # Default size

    return desired_size

def fetch_readme():  # Update announcement from GitHub
    print("Fetching announcement...")
    try:
        readme_url = "https://raw.githubusercontent.com/Passer1072/RookieAI_yolov8/master/README.md"
        response = requests.get(readme_url, timeout=10)
        response_text = response.text
        print("Fetch successful")

        # Find the position of "Update log:" in the string
        update_log_start = response_text.find("更新日志：")

        # If "Update log:" is not found, return the entire content
        if update_log_start == -1:
            return response_text

        # Extract the text after "Update log:"
        update_log = response_text[update_log_start:]
        return update_log

    except Exception as e:
        print("Fetch failed:", e)
        return "Unable to load the latest README file. This may be due to network issues or other unknown errors."

def fetch_readme_version_number():  # Get version number from GitHub
    print("Fetching version number...")
    try:
        readme_url = "https://raw.githubusercontent.com/Passer1072/RookieAI_yolov8/master/README.md"
        response = requests.get(readme_url)
        response_text = response.text
        print("Fetch successful")

        # Create search string
        search_str = "Current latest version: "

        # Find the position of "Current latest version: " in the string
        update_log_start = response_text.find(search_str)

        # If "Current latest version: " is not found, return the entire content
        if (update_log_start == -1):
            return response_text

        # Extract the text after "Current latest version: "
        update_log_start += len(search_str)  # Move the index to the end of "Current latest version: "
        update_log = response_text[update_log_start:]

        # Use strip method to remove leading and trailing spaces
        update_log = update_log.strip()

        return update_log

    except Exception as e:
        print("Fetch failed:", e)
        return "Version number fetch failed"

def crawl_information_by_github():
    global readme_content, readme_version
    if crawl_information:
        # Read online announcement
        readme_content = fetch_readme()
        readme_version = fetch_readme_version_number()

def open_web(event):
    webbrowser.open('https://github.com/Passer1072/RookieAI_yolov8')  # The webpage to jump to

def choose_model():  # Choose model
    global model_file
    model_file = filedialog.askopenfilename()  # Let the user choose the file
    model_file_label.config(text=model_file)  # Update the label text to the selected file path

def open_settings_config():
    os.startfile("settings.json")

def load_model_file():  # Load model file
    # Default model file path
    default_model_file = "yolov8n.pt"
    try:
        with open('settings.json', 'r') as f:
            settings = json.load(f)
            model_file = settings.get('model_file', default_model_file)
            # Check if the file exists, if not, use the default model file
            if not os.path.isfile(model_file):
                print("[WARNING] Invalid model file path in settings file; using default model file")
                model_file = default_model_file
    except FileNotFoundError:
        print("[WARNING] Settings file not found; using default model file")
        model_file = default_model_file

    print("Loading model file:", model_file)
    # If model_file is None or empty, we return None, otherwise we return the corresponding YOLO model
    return YOLO(model_file) if model_file else None

def create_gui_tkinter():  # Software theme GUI interface
    global aimbot_var, lockSpeed_scale, triggerType_var, arduinoMode_var, lockKey_var, confidence_scale \
        , closest_mouse_dist_scale, screen_width_scale, screen_height_scale, root, model_file, model_file_label, aimOffset_scale \
        , draw_center_var, mouse_Side_Button_Witch_var, LookSpeed_label_text, lockSpeed_variable, confidence_variable \
        , closest_mouse_dist_variable, aimOffset_variable, screen_width_scale_variable, screen_height_scale_variable \
        , image_label, image_label_switch, image_label_FPSlabel, target_selection_var, target_mapping, prediction_factor_variable \
        , prediction_factor_scale, method_of_prediction_var, extra_offset_x_scale, extra_offset_y_scale, extra_offset_y \
        , extra_offset_x, extra_offset_x_variable, extra_offset_y_variable, readme_content, screenshot_mode_var\
        , screenshot_mode, segmented_aiming_switch_var, stage1_scope, stage1_scope_scale, stage1_scope_variable\
        , stage1_intensity_variable, stage1_intensity, stage1_intensity_scale, stage2_scope_variable\
        , stage2_intensity_variable, stage2_scope_scale, stage2_intensity_scale, antirecoil_var  # Add antirecoil_var

    # Version number
    version_number = "V2.3.3(test)"
    # Create the root window using customtkinter
    root = ctk.CTk()
    # ctk.set_appearance_mode("system")  # default
    ctk.set_appearance_mode("dark")
    # Hide the main window before the splash screen ends
    root.withdraw()
    # Create a splash screen window
    top = tk.Toplevel(root)
    top.title("Starting")
    top.attributes('-topmost', 1)

    logo_file = "logo-bird.png"  # Your logo file path
    photo = tk.PhotoImage(file=logo_file)
    label = tk.Label(top, image=photo)
    label.pack()

    # Close the splash screen window and show the main window after 1 second
    def end_splash():
        top.destroy()  # Destroy the splash screen
        root.deiconify()  # Show the main window

    root.after(2000, end_splash)  # Run after 1 second

    # Main program window stays on top
    root.attributes('-topmost', 1)
    root.update()

    root.title("RookieAI")  # Software name

    root.geometry(f"{_win_width}x{_win_height}")

    # Set the action to take when the user clicks the window's close button
    root.protocol("WM_DELETE_WINDOW", stop_program)  # Set the default action of WM_DELETE_WINDOW to _on_closing function

    # Disable window resizing
    root.resizable(False, True)

    # Instantiate the CTkTabview object
    tab_view = ctk.CTkTabview(root, width=320, height=500)
    # Create tabs
    tab_view.add("Basic")
    tab_view.add("Advanced")
    tab_view.add("AntiRecoil")
    tab_view.add("Other")
    tab_view.add("Test")
    
    # Add the CTkTabview object to the main window
    tab_view.grid(row=0, column=0, padx=(15, 0), pady=(0, 0))

    # Create a frame to contain the aimbot switch and its left display aim range
    aimbot_draw_center_frame = ctk.CTkFrame(tab_view.tab("Basic"))
    aimbot_draw_center_frame.grid(row=0, column=0, sticky='w', pady=5)  # Use grid layout and align left
    # Create a checkbox named 'Aimbot'
    aimbot_var = ctk.BooleanVar(value=aimbot)
    aimbot_check = ctk.CTkCheckBox(aimbot_draw_center_frame, text='Aimbot', variable=aimbot_var,
                                   command=update_values)
    aimbot_check.grid(row=0, column=0)  # Use grid layout and align left
    # Show aim range switch
    draw_center_var = ctk.BooleanVar(value=False)  # Default value is False
    draw_center_check = ctk.CTkCheckBox(aimbot_draw_center_frame, text='Show aim range (for testing)', variable=draw_center_var,
                                        command=update_values)
    draw_center_check.grid(row=0, column=1)

    # Create a frame to contain the arduinoMode switch and its left display aim range
    arduinoMode_frame = ctk.CTkFrame(tab_view.tab("Basic"))
    arduinoMode_frame.grid(row=1, column=0, sticky='w', pady=5)  # Use grid layout and align left
    # Create a checkbox named 'Arduino Mode (Not enabled)'
    arduinoMode_var = ctk.BooleanVar(value=arduinoMode)
    arduinoMode_check = ctk.CTkCheckBox(arduinoMode_frame, text='Arduino Mode (To be developed)', variable=arduinoMode_var,
                                        command=update_values, state="DISABLED")
    arduinoMode_check.grid(row=0, column=0, sticky="w", pady=(0, 0))  # Use grid layout and align left

    triggerType_var = tk.StringVar(value=triggerType)
    # Create a frame to contain the OptionMenu and its left label
    triggerType_frame = ctk.CTkFrame(tab_view.tab("Basic"))
    triggerType_frame.grid(row=2, column=0, sticky='w', pady=5)  # Use grid layout and align left
    # Add a label
    triggerType_label = ctk.CTkLabel(triggerType_frame, text="Current trigger type:")
    triggerType_label.pack(side='left')  # Align left in the frame
    # Add an OptionMenu widget
    options = ["Press", "Toggle", "shift+Press"]
    triggerType_option = ctk.CTkOptionMenu(triggerType_frame, variable=triggerType_var, values=options,
                                           command=update_values)
    triggerType_option.pack(side='left')  # Align left in the frame

    # Create a new frame widget to contain the label and OptionMenu
    frame = ctk.CTkLabel(tab_view.tab("Basic"))
    frame.grid(row=3, column=0, sticky='w', pady=5)  # frame position in the root window
    # Create a label text and insert it into the frame
    lbl = ctk.CTkLabel(frame, text="Current hotkey:")
    lbl.grid(row=0, column=0)  # label position in the frame
    # Create a variable string variable to be used for the OptionMenu options
    lockKey_var = ctk.StringVar()
    lockKey_var.set('Right key')  # Set the initial value of the option menu to 'Left key'
    options = ['Left key', 'Right key', 'Lower side key']  # Define a list of available options
    # Create an OptionMenu and use lockKey_var and options
    lockKey_menu = ctk.CTkOptionMenu(frame, variable=lockKey_var, values=options, command=update_values)
    lockKey_menu.grid(row=0, column=1)  # OptionMenu position in the frame

    # Create a frame to contain the arduinoMode switch and its left display aim range
    mouse_Side_Button_Witch_frame = ctk.CTkFrame(tab_view.tab("Basic"))
    mouse_Side_Button_Witch_frame.grid(row=4, column=0, sticky='w', pady=5)  # Use grid layout and align left
    # Create a checkbox named 'Mouse side key aim switch'
    mouse_Side_Button_Witch_var = ctk.BooleanVar(value=False)
    mouse_Side_Button_Witch_check = ctk.CTkCheckBox(mouse_Side_Button_Witch_frame, text='Mouse side key aim switch',
                                                    variable=mouse_Side_Button_Witch_var,
                                                    command=update_values)
    mouse_Side_Button_Witch_check.grid(row=0, column=0, sticky="w", pady=5)  # Use grid layout and align left

    # Aim speed
    # Create a StringVar object to store the value of lockSpeed_scale
    lockSpeed_variable = tk.StringVar()
    lockSpeed_variable.set(str(lockSpeed))
    # A slider named 'Lock Speed'; aim speed module
    # Create a frame to contain the OptionMenu and its left label
    LookSpeed_frame = ctk.CTkFrame(tab_view.tab("Basic"))
    LookSpeed_frame.grid(row=6, column=0, sticky='w', pady=2)  # Use grid layout and align left
    # A label showing the text "LockSpeed:"
    LookSpeed_label_0 = ctk.CTkLabel(LookSpeed_frame, text="LockSpeed:")
    LookSpeed_label_0.grid(row=0, column=0)  # Align left in the frame
    # A slider named 'Lock Speed'; aim speed module
    lockSpeed_scale = ctk.CTkSlider(LookSpeed_frame, from_=0, to=1, number_of_steps=100, command=update_values)
    lockSpeed_scale.set(lockSpeed)
    lockSpeed_scale.grid(row=0, column=1)
    # Use textvariable instead of text
    LookSpeed_label_text = ctk.CTkLabel(LookSpeed_frame, textvariable=lockSpeed_variable)
    LookSpeed_label_text.grid(row=0, column=2)
    # If segmented aiming is enabled, disable general aim range settings
    if segmented_aiming_switch:
        ban_LookSpeed_label_0 = ctk.CTkLabel(LookSpeed_frame, text="Disable segmented", width=200)
        ban_LookSpeed_label_0.grid(row=0, column=1, padx=(12, 0))  # row number
        ban_LookSpeed_label_text = ctk.CTkLabel(LookSpeed_frame, text="###", width=25)
        ban_LookSpeed_label_text.grid(row=0, column=2)  # row number

    # Adjust aim range
    # Create a StringVar object to store the value of closest_mouse_dist
    closest_mouse_dist_variable = tk.StringVar()
    closest_mouse_dist_variable.set(str(closest_mouse_dist))
    # Create a frame to contain the OptionMenu and its left label
    closest_mouse_dist_frame = ctk.CTkFrame(tab_view.tab("Basic"))
    closest_mouse_dist_frame.grid(row=7, column=0, sticky='w', pady=2)  # Use grid layout and align left
    # Add a label
    closest_mouse_dist_label = ctk.CTkLabel(closest_mouse_dist_frame, text="Aim range:")
    closest_mouse_dist_label.grid(row=0, column=1, sticky='w')
    # Adjust aim range
    closest_mouse_dist_scale = ctk.CTkSlider(closest_mouse_dist_frame, from_=0, to=300, command=update_values)
    closest_mouse_dist_scale.set(closest_mouse_dist)
    closest_mouse_dist_scale.grid(row=0, column=2, padx=(12, 0))
    # Use textvariable instead of text
    closest_mouse_dist_text = ctk.CTkLabel(closest_mouse_dist_frame, textvariable=closest_mouse_dist_variable)
    closest_mouse_dist_text.grid(row=0, column=3)
    # If segmented aiming is enabled, disable general aim range settings
    if segmented_aiming_switch:
        ban_closest_mouse_dist_label = ctk.CTkLabel(closest_mouse_dist_frame, text="Disable segmented ", width=200)
        ban_closest_mouse_dist_label.grid(row=0, column=2, padx=(12, 0))  # row number
        ban_closest_mouse_dist_text = ctk.CTkLabel(closest_mouse_dist_frame, text="####", width=30)
        ban_closest_mouse_dist_text.grid(row=0, column=3)  # row number

    # Create a new frame widget to contain the label and OptionMenu
    frame = ctk.CTkLabel(tab_view.tab("Basic"))
    frame.grid(row=8, column=0, sticky='w', pady=5)  # frame position in the root window
    # Create a label text and insert it into the frame
    lbl = ctk.CTkLabel(frame, text="Prediction method:")
    lbl.grid(row=0, column=0)  # label position in the frame
    # Create a variable string variable to be used for the OptionMenu options
    method_of_prediction_var = ctk.StringVar()
    method_of_prediction_var.set('Disable prediction')  # Set the initial value of the option menu to 'Left key'
    options = ['Disable prediction', 'Multiplier prediction', 'Pixel prediction']  # Define a list of available options
    # Create an OptionMenu and use lockKey_var and options
    method_of_prediction_menu = ctk.CTkOptionMenu(frame, variable=method_of_prediction_var, values=options,
                                                  command=update_values)
    method_of_prediction_menu.grid(row=0, column=1)  # OptionMenu position in the frame

    # Create a frame to contain the OptionMenu and its left label
    message_text_frame = ctk.CTkFrame(tab_view.tab("Basic"))
    message_text_frame.grid(row=9, column=0, sticky='w', pady=2)  # Use grid layout and align left
    # Create a label
    message_text_Label = ctk.CTkLabel(message_text_frame, text="Update announcement")
    message_text_Label.grid(row=0, column=1)
    # Create a text box
    message_text_box = ctk.CTkTextbox(message_text_frame, width=300, height=100, corner_radius=5)
    message_text_box.grid(row=1, column=1, sticky="nsew")
    message_text_box.insert("0.0", readme_content)
    
    # AntiRecoil Tab
    antiRecoil_tab = tab_view.tab("AntiRecoil")
    antiRecoil_layout = ctk.CTkFrame(antiRecoil_tab)
    antiRecoil_layout.pack(fill="both", expand=True, padx=10, pady=10)

    # AntiRecoil Checkbox
    antirecoil_var = ctk.BooleanVar(value=False)  # Default value is False
    antiRecoil_checkbox = ctk.CTkCheckBox(antiRecoil_layout, text="Enable/Disable", variable=antirecoil_var, command=update_values)
    antiRecoil_checkbox.grid(row=0, column=0, sticky="w", pady=5)

    # Instructions Label
    instructions = """
    Recoil Controls:


    - Enter: Save current profile.

    
    - Up Arrow: Increase y_movement.

    
    - Down Arrow: Decrease y_movement.

   
    - Right Arrow: Increase x_movement.

    
    - Left Arrow: Decrease x_movement.

    
    - Page Up: Switch to the next profile.

    
    - Page Down: Switch to the previous profile.
    """
    instructions_label = ctk.CTkLabel(antiRecoil_layout, text=instructions, anchor="w", justify="left")
    instructions_label.grid(row=1, column=0, sticky="w", pady=5)

    # Additional layout adjustments if needed...
    antiRecoil_layout.grid_rowconfigure(2, weight=1)  # Push content to the top
    antiRecoil_layout.grid_columnconfigure(0, weight=1)  # Center content horizontally

    # Target selection box
    # Create a frame to contain the OptionMenu and its left label
    target_selection_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    target_selection_frame.grid(row=1, column=0, sticky='w', pady=5)  # Use grid layout and align left
    # Create a label text and insert it into the frame
    target_selection_label = ctk.CTkLabel(target_selection_frame, text="Current detection target:")
    target_selection_label.grid(row=0, column=0)  # label position in the frame
    # Create a variable string variable to be used for the OptionMenu options
    target_selection_var = ctk.StringVar()
    target_selection_var.set('enemy')  # Set the initial value of the option menu to 'enemy'
    # Define a list of available options
    options = list(target_mapping.keys())
    # Create a selection box
    target_selection_option = ctk.CTkOptionMenu(target_selection_frame, variable=target_selection_var, values=options,
                                                command=update_values)
    target_selection_option.grid(row=0, column=1)

    # Adjust confidence
    # Create a StringVar object to store the value of lockSpeed_scale
    confidence_variable = tk.StringVar()
    confidence_variable.set(str(confidence))
    # Confidence adjustment slider: create a slider named 'Confidence'; confidence adjustment module
    # Create a frame to contain the OptionMenu and its left label
    confidence_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    confidence_frame.grid(row=2, column=0, sticky='w', pady=2)  # Use grid layout and align left
    # Add a label
    confidence_label = ctk.CTkLabel(confidence_frame, text="Confidence:")
    confidence_label.grid(row=0, column=1, sticky='w')
    # Confidence adjustment slider: create a slider named 'Confidence'; confidence adjustment module
    confidence_scale = ctk.CTkSlider(confidence_frame, from_=0, to=1, number_of_steps=100, command=update_values)
    confidence_scale.set(confidence)
    confidence_scale.grid(row=0, column=2, padx=(25, 0))
    # Use textvariable instead of text
    confidence_label_text = ctk.CTkLabel(confidence_frame, textvariable=confidence_variable)
    confidence_label_text.grid(row=0, column=3)

    # Multiplier prediction adjustment
    # Create a StringVar object to store the value of prediction_factor
    prediction_factor_variable = tk.StringVar()
    prediction_factor_variable.set(str(prediction_factor))
    # Create a frame to contain the OptionMenu and its left label
    prediction_factor_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    prediction_factor_frame.grid(row=3, column=0, sticky='w', pady=2)  # Use grid layout and align left
    # Add a label
    prediction_factor_label = ctk.CTkLabel(prediction_factor_frame, text="Prediction:")
    prediction_factor_label.grid(row=0, column=1, sticky='w')
    # Prediction factor adjustment
    prediction_factor_scale = ctk.CTkSlider(prediction_factor_frame, from_=0, to=1, number_of_steps=100,
                                            command=update_values)
    prediction_factor_scale.set(prediction_factor)
    prediction_factor_scale.grid(row=0, column=2, padx=(12, 0))
    # Use textvariable instead of text
    prediction_factor_text = ctk.CTkLabel(prediction_factor_frame, textvariable=prediction_factor_variable)
    prediction_factor_text.grid(row=0, column=3)

    # Pixel prediction adjustment
    # Create a StringVar object to store the value of extra_offset_x
    extra_offset_x_variable = tk.StringVar()
    extra_offset_x_variable.set(str(extra_offset_x))
    # A slider named 'Lock Speed'; aim speed module
    # Create a frame to contain the OptionMenu and its left label
    extra_offset_x_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    extra_offset_x_frame.grid(row=4, column=0, sticky='w', pady=2)  # Use grid layout and align left
    # A label showing the text "LockSpeed:"
    extra_offset_x_label = ctk.CTkLabel(extra_offset_x_frame, text="Prediction X:")
    extra_offset_x_label.grid(row=0, column=0)  # Align left in the frame
    # A slider named 'Lock Speed'; aim speed module
    extra_offset_x_scale = ctk.CTkSlider(extra_offset_x_frame, from_=0, to=20, number_of_steps=20,
                                         command=update_values)
    extra_offset_x_scale.set(extra_offset_x)
    extra_offset_x_scale.grid(row=0, column=1, padx=(4, 0))
    # Use textvariable instead of text
    extra_offset_x_label_text = ctk.CTkLabel(extra_offset_x_frame, textvariable=extra_offset_x_variable)
    extra_offset_x_label_text.grid(row=0, column=2)

    # Pixel prediction adjustment
    # Create a StringVar object to store the value of extra_offset_y
    extra_offset_y_variable = tk.StringVar()
    extra_offset_y_variable.set(str(extra_offset_y))
    # A slider named 'Lock Speed'; aim speed module
    # Create a frame to contain the OptionMenu and its left label
    extra_offset_y_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    extra_offset_y_frame.grid(row=5, column=0, sticky='w', pady=2)  # Use grid layout and align left
    # A label showing the text "LockSpeed:"
    extra_offset_y_label = ctk.CTkLabel(extra_offset_y_frame, text="Prediction Y:")
    extra_offset_y_label.grid(row=0, column=0)  # Align left in the frame
    # A slider named 'Lock Speed'; aim speed module
    extra_offset_y_scale = ctk.CTkSlider(extra_offset_y_frame, from_=0, to=20, number_of_steps=20,
                                         command=update_values)
    extra_offset_y_scale.set(extra_offset_y)
    extra_offset_y_scale.grid(row=0, column=1, padx=(4, 0))
    # Use textvariable instead of text
    extra_offset_y_label_text = ctk.CTkLabel(extra_offset_y_frame, textvariable=extra_offset_y_variable)
    extra_offset_y_label_text.grid(row=0, column=2)

    # Aim offset
    # Create a StringVar object to store the value of closest_mouse_dist
    aimOffset_variable = tk.StringVar()
    aimOffset_variable.set(str(aimOffset))
    # Create a frame to contain the slider and its left label text
    aimOffset_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    aimOffset_frame.grid(row=6, column=0, sticky='w', pady=2)  # Use grid layout and align left
    # Add a label
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="Aim:")
    aimOffset_label.grid(row=0, column=1, sticky='w')
    # Aim offset (the larger the value, the higher the aim)
    aimOffset_scale = ctk.CTkSlider(aimOffset_frame, from_=0, to=1, number_of_steps=100, command=update_values,
                                    orientation="vertical")
    aimOffset_scale.set(aimOffset)
    aimOffset_scale.grid(row=0, column=2, padx=(12, 0))
    # Add a label to show the aim position: waist
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="Waist")
    aimOffset_label.grid(row=0, column=3, pady=(170, 0))
    # Add a label to show the aim position: abdomen
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="Abdomen")
    aimOffset_label.grid(row=0, column=3, pady=(80, 0))
    # Add a label to show the aim position: chest
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="Chest")
    aimOffset_label.grid(row=0, column=3, pady=(0, 5))
    # Add a label to show the aim position: head
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="Head")
    aimOffset_label.grid(row=0, column=3, pady=(0, 170))
    # Add a label to show the human body image
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, image=ctk.CTkImage(img, size=(150, 200)), text="")
    aimOffset_label.grid(row=0, column=4)
    # Use textvariable instead of text
    aimOffset_text = ctk.CTkLabel(aimOffset_frame, textvariable=aimOffset_variable)
    aimOffset_text.grid(row=0, column=5, pady=(0, 0))

    # Screen width
    # Create a StringVar object to store the value of screen_width_scale
    screen_width_scale_variable = tk.StringVar()
    screen_width_scale_variable.set(str(screen_width))
    # Create a frame to contain the slider and its left label text
    screen_width_scale_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    screen_width_scale_frame.grid(row=7, column=0, sticky='w', pady=2)  # Use grid layout and align left
    # Add a label
    screen_width_scale_label = ctk.CTkLabel(screen_width_scale_frame, text="Width:")
    screen_width_scale_label.grid(row=0, column=1, sticky='w')
    # Create a screen width slider
    screen_width_scale = ctk.CTkSlider(screen_width_scale_frame, from_=100, to=2000, number_of_steps=190,
                                       command=update_values)
    screen_width_scale.set(screen_width)  # Initial value
    screen_width_scale.grid(row=0, column=2, padx=(12, 0))  # row number
    # Use textvariable instead of text
    screen_width_scale_text = ctk.CTkLabel(screen_width_scale_frame, textvariable=screen_width_scale_variable)
    screen_width_scale_text.grid(row=0, column=3)
    # If DXcam is enabled, disable screenshot width/height adjustment sliders
    if screenshot_mode:
        ban_screen_width_scale = ctk.CTkLabel(screen_width_scale_frame, text="DXcam enabled", width=200)
        ban_screen_width_scale.grid(row=0, column=2, padx=(12, 0))  # row number
        ban_screen_width_scale_text = ctk.CTkLabel(screen_width_scale_frame, text="####", width=30)
        ban_screen_width_scale_text.grid(row=0, column=3)  # row number

    # Screen height
    # Create a StringVar object to store the value of screen_height_scale
    screen_height_scale_variable = tk.StringVar()
    screen_height_scale_variable.set(str(screen_height))
    # Create a frame to contain the slider and its left label text
    screen_height_scale_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    screen_height_scale_frame.grid(row=8, column=0, sticky='w', pady=2)  # Use grid layout and align left
    # Add a label
    screen_height_scale_label = ctk.CTkLabel(screen_height_scale_frame, text="Height:")
    screen_height_scale_label.grid(row=0, column=1, sticky='w')
    # Create a screen height slider
    screen_height_scale = ctk.CTkSlider(screen_height_scale_frame, from_=100, to=2000, number_of_steps=190,
                                        command=update_values)
    screen_height_scale.set(screen_height)  # Initial value
    screen_height_scale.grid(row=0, column=2, padx=(12, 0))  # row number
    # Use textvariable instead of text
    screen_height_scale_text = ctk.CTkLabel(screen_height_scale_frame, textvariable=screen_height_scale_variable)
    screen_height_scale_text.grid(row=0, column=3)
    if screenshot_mode:
        ban_screen_height_scale = ctk.CTkLabel(screen_height_scale_frame, text=" DXcam  enabled", width=200)
        ban_screen_height_scale.grid(row=0, column=2, padx=(12, 0))  # row number
        ban_screen_height_scale_text = ctk.CTkLabel(screen_height_scale_frame, text="####", width=30)
        ban_screen_height_scale_text.grid(row=0, column=3)  # row number

    # Screenshot mode selection
    # Create a frame to contain the OptionMenu and its left label
    screenshot_mode_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    screenshot_mode_frame.grid(row=9, column=0, sticky='w', pady=5)  # Use grid layout and align left
    # Create a checkbox named 'Enable DXcam mode'
    screenshot_mode_var = ctk.BooleanVar(value=screenshot_mode)
    screenshot_mode_check = ctk.CTkCheckBox(screenshot_mode_frame, text='Enable DXcam ', variable=screenshot_mode_var,
                                   command=update_values)
    screenshot_mode_check.grid(row=0, column=1)  # Use grid layout and align left

    # Aiming mode selection
    # Create a frame to contain the OptionMenu and its left label
    segmented_aiming_switch_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    segmented_aiming_switch_frame.grid(row=10, column=0, sticky='w', pady=5)  # Use grid layout and align left
    # Create a checkbox named 'Enable segmented aiming mode'
    segmented_aiming_switch_var = ctk.BooleanVar(value=segmented_aiming_switch)
    segmented_aiming_switch_check = ctk.CTkCheckBox(segmented_aiming_switch_frame, text='Enable segmented ', variable=segmented_aiming_switch_var,
                                   command=update_values)
    segmented_aiming_switch_check.grid(row=0, column=1)  # Use grid layout and align left

    # Segmented aim range adjustment (strong lock range)
    # Create a StringVar object to store the value of stage1_scope
    stage1_scope_variable = tk.StringVar()
    stage1_scope_variable.set(str(stage1_scope))
    # Create a frame to contain the OptionMenu and its left label
    stage1_scope_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    stage1_scope_frame.grid(row=11, column=0, sticky='w', pady=2)  # Use grid layout and align left
    # Add a label
    stage1_scope_label = ctk.CTkLabel(stage1_scope_frame, text="Strong range:")
    stage1_scope_label.grid(row=0, column=1, sticky='w')
    # Adjust aim range
    stage1_scope_scale = ctk.CTkSlider(stage1_scope_frame, from_=0, to=300, number_of_steps=300, command=update_values)
    stage1_scope_scale.set(stage1_scope)
    stage1_scope_scale.grid(row=0, column=2, padx=(12, 0))
    # Use textvariable instead of text
    stage1_scope_text = ctk.CTkLabel(stage1_scope_frame, textvariable=stage1_scope_variable)
    stage1_scope_text.grid(row=0, column=3)
    # If segmented aiming is not enabled, disable the adjustment
    if not segmented_aiming_switch:
        ban_screen_height_scale = ctk.CTkLabel(stage1_scope_frame, text="Enable segmented", width=200)
        ban_screen_height_scale.grid(row=0, column=2, padx=(12, 0))  # row number
        ban_screen_height_scale_text = ctk.CTkLabel(stage1_scope_frame, text="####", width=30)
        ban_screen_height_scale_text.grid(row=0, column=3)  # row number

    # Segmented aim range adjustment (strong lock speed)
    # Create a StringVar object to store the value of stage1_intensity
    stage1_intensity_variable = tk.StringVar()
    stage1_intensity_variable.set(str(stage1_intensity))
    # Create a frame to contain the OptionMenu and its left label
    stage1_intensity_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    stage1_intensity_frame.grid(row=12, column=0, sticky='w', pady=2)  # Use grid layout and align left
    # Add a label
    stage1_intensity_label = ctk.CTkLabel(stage1_intensity_frame, text="Strong speed:")
    stage1_intensity_label.grid(row=0, column=1, sticky='w')
    # Adjust aim range
    stage1_intensity_scale = ctk.CTkSlider(stage1_intensity_frame, from_=0, to=1, number_of_steps=100, command=update_values)
    stage1_intensity_scale.set(stage1_intensity)
    stage1_intensity_scale.grid(row=0, column=2, padx=(12, 0))
    # Use textvariable instead of text
    stage1_intensity_text = ctk.CTkLabel(stage1_intensity_frame, textvariable=stage1_intensity_variable)
    stage1_intensity_text.grid(row=0, column=3)
    # If segmented aiming is not enabled, disable the adjustment
    if not segmented_aiming_switch:
        ban_stage1_intensity_scale = ctk.CTkLabel(stage1_intensity_frame, text="Enable segmented", width=200)
        ban_stage1_intensity_scale.grid(row=0, column=2, padx=(12, 0))  # row number
        ban_stage1_intensity_scale = ctk.CTkLabel(stage1_intensity_frame, text="####", width=30)
        ban_stage1_intensity_scale.grid(row=0, column=3)  # row number

    # Segmented aim range adjustment (soft lock range)
    # Create a StringVar object to store the value of stage2_intensity
    stage2_scope_variable = tk.StringVar()
    stage2_scope_variable.set(str(stage2_intensity))
    # Create a frame to contain the OptionMenu and its left label
    stage2_scope_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    stage2_scope_frame.grid(row=13, column=0, sticky='w', pady=2)  # Use grid layout and align left
    # Add a label
    stage2_scope_label = ctk.CTkLabel(stage2_scope_frame, text="Soft range:")
    stage2_scope_label.grid(row=0, column=1, sticky='w')
    # Adjust aim range
    stage2_scope_scale = ctk.CTkSlider(stage2_scope_frame, from_=0, to=300, number_of_steps=300, command=update_values)
    stage2_scope_scale.set(stage2_scope)
    stage2_scope_scale.grid(row=0, column=2, padx=(12, 0))
    # Use textvariable instead of text
    stage2_scope_text = ctk.CTkLabel(stage2_scope_frame, textvariable=stage2_scope_variable)
    stage2_scope_text.grid(row=0, column=3)
    # If segmented aiming is not enabled, disable the adjustment
    if not segmented_aiming_switch:
        ban_stage2_scope_scale = ctk.CTkLabel(stage2_scope_frame, text="Enable segmented", width=200)
        ban_stage2_scope_scale.grid(row=0, column=2, padx=(12, 0))  # row number
        ban_stage2_scope_scale = ctk.CTkLabel(stage2_scope_frame, text="####", width=30)
        ban_stage2_scope_scale.grid(row=0, column=3)  # row number

    # Segmented aim range adjustment (soft lock speed)
    # Create a StringVar object to store the value of stage2_intensity
    stage2_intensity_variable = tk.StringVar()
    stage2_intensity_variable.set(str(stage2_intensity))
    # Create a frame to contain the OptionMenu and its left label
    stage2_intensity_frame = ctk.CTkFrame(tab_view.tab("Advanced"))
    stage2_intensity_frame.grid(row=14, column=0, sticky='w', pady=2)  # Use grid layout and align left
    # Add a label
    stage2_intensity_label = ctk.CTkLabel(stage2_intensity_frame, text="Soft speed:")
    stage2_intensity_label.grid(row=0, column=1, sticky='w')
    # Adjust aim range
    stage2_intensity_scale = ctk.CTkSlider(stage2_intensity_frame, from_=0, to=1, number_of_steps=100, command=update_values)
    stage2_intensity_scale.set(stage2_intensity)
    stage2_intensity_scale.grid(row=0, column=2, padx=(12, 0))
    # Use textvariable instead of text
    stage2_intensity_text = ctk.CTkLabel(stage2_intensity_frame, textvariable=stage2_intensity_variable)
    stage2_intensity_text.grid(row=0, column=3)
    # If segmented aiming is not enabled, disable the adjustment
    if not segmented_aiming_switch:
        ban_stage2_intensity_scale = ctk.CTkLabel(stage2_intensity_frame, text="Enable segmented", width=200)
        ban_stage2_intensity_scale.grid(row=0, column=2, padx=(12, 0))  # row number
        ban_stage2_intensity_scale = ctk.CTkLabel(stage2_intensity_frame, text="####", width=30)
        ban_stage2_intensity_scale.grid(row=0, column=3)  # row number

    # Create a frame to contain other settings
    setting_frame = ctk.CTkFrame(tab_view.tab("Other"), width=300, height=300)
    setting_frame.grid(row=9, column=0, sticky='w', pady=2)  # Use grid layout and align left
    setting_frame.grid_propagate(False)  # Prevent the frame from resizing to fit its contents

    # Show the selected file path label
    model_file_label = tk.Label(setting_frame, text="No model ", width=40, anchor='e')  # Initial text displayed
    model_file_label.grid(row=0, column=0, sticky="w")  # Use grid layout and align left

    # User select model file button
    model_file_button = ctk.CTkButton(setting_frame, text="Choose model)",
                                      command=choose_model)  # Call the choose_model function when this button is clicked
    model_file_button.grid(row=1, column=0, padx=(0, 245), pady=(5, 0))  # Use grid layout and align left

    # Create a button to open the configuration file with one click
    config_file_button = ctk.CTkButton(setting_frame, text="Open config",
                                       command=open_settings_config)  # Call the open_config function when this button is clicked
    config_file_button.grid(row=1, column=0, padx=(55, 0), pady=(5, 0))

    # Create a 'Save' button
    save_button = ctk.CTkButton(setting_frame, text='Save Config ', width=20, command=save_settings)
    save_button.grid(row=2, column=0, padx=(0, 320), pady=(10, 0))  # Adjust the row number as needed

    # Create a 'Load' button
    load_button = ctk.CTkButton(setting_frame, text='Load Config', width=20, command=load_settings,
                                state="DISABLED")
    load_button.grid(row=2, column=0, padx=(0, 120), pady=(10, 0))

    # Create a 'Restart Software' button
    restart_button = ctk.CTkButton(setting_frame, text='Restart Software', width=20, command=restart_program)
    restart_button.grid(row=3, column=0, padx=(0, 320), pady=(10, 0))

    # Version number display 1
    version_number_text1 = ctk.CTkLabel(setting_frame, text="Current version:", width=30)
    version_number_text1.bind("<Button-1>", command=open_web)
    version_number_text1.grid(row=3, column=0, padx=(10, 0), pady=(120, 0))
    # Version number display 1
    version_number1 = ctk.CTkLabel(setting_frame, text=version_number, width=30)
    version_number1.bind("<Button-1>", command=open_web)
    version_number1.grid(row=3, column=0, padx=(120, 0), pady=(120, 0))
    # Version number display 2
    version_number_text2 = ctk.CTkLabel(setting_frame, text="Latest version:", width=30)
    version_number_text2.bind("<Button-1>", command=open_web)
    version_number_text2.grid(row=4, column=0, padx=(10, 0), pady=(0, 0))
    # Version number display 2
    version_number2 = ctk.CTkLabel(setting_frame, text=":(", width=30)
    version_number2.bind("<Button-1>", command=open_web)
    version_number2.grid(row=4, column=0, padx=(120, 0), pady=(0, 0))
    # Fetch version number from GitHub
    version = fetch_readme_version_number()
    # Update the text of version_number2 to the version number fetched from GitHub
    version_number2.configure(text=version)
    # Update the text of version_number2 and set the color (compare version numbers)
    if version == version_number1.cget("text"):
        version_number2.configure(text=version, text_color="green")
    else:
        version_number2.configure(text=version, text_color="red")

    # Debug window tab
    image_label_frame = ctk.CTkFrame(tab_view.tab("Test"), height=370, width=305)
    image_label_frame.grid(row=1, column=0, sticky='w')
    image_label_frame.grid_propagate(False)
    # Screen switch
    image_label_switch = ctk.CTkSwitch(image_label_frame, text="Internal test window ", onvalue=True, offvalue=False,
                                       command=update_values)
    image_label_switch.grid(row=0, column=0, padx=(0, 0), sticky='w')
    # Screen display
    image_label = tk.Label(image_label_frame)
    image_label.grid(row=1, column=0, padx=(0, 0))
    # Frame rate display
    image_label_FPSlabel = ctk.CTkLabel(image_label_frame, text="Real-time FPS:", width=40)  # Initial text displayed
    image_label_FPSlabel.grid(row=2, column=0, padx=(0, 0), sticky='w')  # Use grid layout and align left

    # Load settings from file
    load_settings()
    # Update variables after loading settings, also update the display on the GUI
    update_values()

    # Run the GUI main loop
    root.mainloop()

def update_values(*args):
    global aimbot, lockSpeed, triggerType, arduinoMode, lockKey, lockKey_var, confidence, closest_mouse_dist \
        , closest_mouse_dist_scale, screen_width, screen_height, model_file, aimOffset, draw_center \
        , mouse_Side_Button_Witch, lockSpeed_text, LookSpeed_label_1, test_images_GUI, target_selection_str \
        , prediction_factor_scale, prediction_factor, method_of_prediction, extra_offset_x, extra_offset_y\
        , screenshot_mode, segmented_aiming_switch, stage1_scope, stage1_scope_scale, stage1_intensity\
        , stage1_intensity_scale, stage2_scope, stage2_scope_scale, stage2_intensity, stage2_intensity_scale\
        , aimOffset_Magnification_x, antirecoil_var  # Add antirecoil_var

    print("update_values function was called (settings updated)")
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
    antirecoil = antirecoil_var.get()  # Update antirecoil variable

    # Update lockSpeed_variable
    lockSpeed = round(lockSpeed_scale.get(), 2)
    lockSpeed_variable.set(str(lockSpeed))
    # Update confidence_variable
    confidence = round(confidence_scale.get(), 2)
    confidence_variable.set(str(confidence))
    # Update closest_mouse_dist_variable
    closest_mouse_dist = int(closest_mouse_dist_scale.get())
    closest_mouse_dist_variable.set(str(closest_mouse_dist))
    # Update prediction_factor_variable
    prediction_factor = round(prediction_factor_scale.get(), 2)
    prediction_factor_variable.set(str(prediction_factor))
    # Update extra_offset_x_variable
    extra_offset_x = round(extra_offset_x_scale.get())
    extra_offset_x_variable.set(str(extra_offset_x))
    # Update extra_offset_y_variable
    extra_offset_y = round(extra_offset_y_scale.get())
    extra_offset_y_variable.set(str(extra_offset_y))
    # Update aimOffset_variable
    aimOffset = round(aimOffset_scale.get(), 2)  # Round to two decimal places
    aimOffset_variable.set(str(aimOffset))
    # Update screen_width
    screen_width = int(screen_width_scale.get())
    screen_width_scale_variable.set(str(screen_width))
    # Update screen_height
    screen_height = int(screen_height_scale.get())
    screen_height_scale_variable.set(str(screen_height))
    # Update stage1_scope displayed value
    stage1_scope = int(stage1_scope_scale.get())
    stage1_scope_variable.set(str(stage1_scope))
    # Update stage1_intensity displayed value
    stage1_intensity = round(stage1_intensity_scale.get(), 2)
    stage1_intensity_variable.set(str(stage1_intensity))
    # Update stage2_scope displayed value
    stage2_scope = int(stage2_scope_scale.get())
    stage2_scope_variable.set(str(stage2_scope))
    # Update stage2_intensity displayed value
    stage2_intensity = round(stage2_intensity_scale.get(), 2)
    stage2_intensity_variable.set(str(stage2_intensity))

    # Convert trigger key value
    key = lockKey_var.get()
    if key == 'Left key':
        lockKey = 0x01
    elif key == 'Right key':
        lockKey = 0x02
    elif key == 'Lower side key':
        lockKey = 0x05

def save_settings():  # Save settings
    global model_file, antirecoil_var  # Add antirecoil_var
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
        'antirecoil': antirecoil_var.get()  # Save antirecoil variable
    }

    # Load current settings
    try:
        with open('settings.json', 'r') as f:
            current_settings = json.load(f)
    except FileNotFoundError:
        current_settings = {}

    # Merge new settings into current settings
    current_settings.update(new_settings)

    # Save current settings
    with open('settings.json', 'w') as f:
        json.dump(current_settings, f, sort_keys=True, indent=4)

def load_prefix_variables():  # Load prefix parameters
    global model_file, screenshot_mode, segmented_aiming_switch, crawl_information
    print('Loading prefix variables...')
    try:
        with open('settings.json', 'r') as f:
            settings = json.load(f)

        screenshot_mode = settings.get("screenshot_mode", False)  # Load screenshot mode
        segmented_aiming_switch = settings.get("segmented_aiming_switch", False)  # Load segmented aiming switch
        crawl_information = settings.get("crawl_information", False)  # Load announcement fetch switch

        print("Prefix variables loaded successfully!")
    except FileNotFoundError:
        print('[ERROR] Settings file not found; skipping loading settings')

def load_settings():  # Load main program parameter settings
    global model_file, test_window_frame, screenshot_mode, crawl_information, DXcam_screenshot, dxcam_maxFPS, \
        loaded_successfully, stage1_scope, stage1_intensity, stage2_scope, stage2_intensity, segmented_aiming_switch\
        , aimOffset_Magnification_x, antirecoil_var  # Add antirecoil_var
    print('Loading settings...')
    try:
        with open('settings.json', 'r') as f:
            settings = json.load(f)

        aimbot_var.set(settings.get('aimbot', True))
        lockSpeed_scale.set(settings.get('lockSpeed', 0.7))
        triggerType_var.set(settings.get('triggerType', "Press"))
        arduinoMode_var.set(settings.get('arduinoMode', False))
        lockKey_var.set(settings.get('lockKey', "Right key"))
        mouse_Side_Button_Witch_var.set(settings.get('mouse_Side_Button_Witch', True))
        method_of_prediction_var.set(settings.get('method_of_prediction', "Multiplier prediction"))
        confidence_scale.set(settings.get('confidence', 0.5))
        extra_offset_x_scale.set(settings.get('extra_offset_x', 5))
        extra_offset_y_scale.set(settings.get('extra_offset_y', 5))
        prediction_factor_scale.set(settings.get('prediction_factor', 0.5))  # Replace with appropriate default value
        closest_mouse_dist_scale.set(settings.get('closest_mouse_dist', 160))
        screen_width_scale.set(settings.get('screen_width', 360))
        screen_height_scale.set(settings.get('screen_height', 360))
        aimOffset_scale.set(settings.get('aimOffset', 0.4))
        aimOffset_Magnification_x = settings.get('aimOffset_Magnification_x', 0)  # Load horizontal offset (test)
        model_file = settings.get('model_file', None)  # Load model_file from file
        model_file_label.config(text=model_file or "No model file selected yet")  # Update label text to loaded file path or default text
        test_window_frame = settings.get('test_window_frame', False)  # Load the value of test_window_frame from file, if not, default to False
        crawl_information = settings.get("crawl_information", True)  # Whether to load the announcement online
        screenshot_mode = settings.get("screenshot_mode", False)  # Whether to enable DXcam screenshot mode
        DXcam_screenshot = settings.get("DXcam_screenshot", 360)  # Resolution of DXcam screenshot mode
        dxcam_maxFPS = settings.get('dxcam_maxFPS', 30)  # Maximum frame rate limit of DXcam screenshot
        segmented_aiming_switch = settings.get('segmented_aiming_switch', False)  # Whether to enable segmented aiming mode
        stage1_scope_scale.set(settings.get('stage1_scope', 50))  # Strong lock range (segmented aiming)
        stage1_intensity_scale.set(settings.get('stage1_intensity', 0.8))  # Strong lock intensity (segmented aiming)
        stage2_scope_scale.set(settings.get('stage2_scope', 170))  # Soft lock range (segmented aiming)
        stage2_intensity_scale.set(settings.get('stage2_intensity', 0.4))  # Soft lock intensity (segmented aiming)
        antirecoil_var.set(settings.get('antirecoil', False))  # Load antirecoil setting

        print("Settings loaded successfully!")
        loaded_successfully = True  # Load success flag
    except FileNotFoundError:
        print('[ERROR] Settings file not found; skipping loading settings')
        pass

def calculate_distances(
        monitor: dict,  # A dictionary containing width and height of the monitor
        results: list,  # A list of object detection results
        frame_: np.array,  # The current frame to be processed
        aimbot: bool,  # Whether the aimbot is active or not
        lockSpeed: float,  # The speed at which the mouse should move towards the object
        arduinoMode: bool,  # Whether the Arduino mode is active or not
        lockKey: int,  # Lock Key code
        triggerType: str,  # Trigger type
):  # Target selection logic and identification
    global boxes, cWidth, cHeight, extra_offset_x, extra_offset_y

    minDist = float('inf')  # Initial minimum distance set to infinity
    minBox = None  # Initial minimum box set to None

    # Calculate the center of the screen
    cWidth = monitor["width"] / 2
    cHeight = monitor["height"] / 2

    # Draw aim range box
    if draw_center:
        if screenshot_mode:  # If DXcam screenshot mode is used, do not use the screenshot size data of mss
            cWidth = DXcam_screenshot // 2
            cHeight = DXcam_screenshot // 2

        if segmented_aiming_switch:  # If segmented aiming is enabled, draw the segmented aiming range, otherwise draw the default mode range
            cv2.circle(frame_, (int(cWidth), int(cHeight)), int(stage2_scope), (0, 255, 0), 2)
            cv2.circle(frame_, (int(cWidth), int(cHeight)), int(stage1_scope), (0, 255, 255), 2)
            cv2.circle(frame_, (int(cWidth), int(cHeight)), radius=5, color=(0, 0, 255), thickness=-1)
        else:
            cv2.circle(frame_, (int(cWidth), int(cHeight)), int(closest_mouse_dist), (0, 255, 0), 2)
            # Draw a center point in the middle of the aim range box
            cv2.circle(frame_, (int(cWidth), int(cHeight)), radius=5, color=(0, 0, 255), thickness=-1)

    for r in results:
        boxes = r.boxes.xyxy.cpu().numpy()  # Get box coordinates
        print(boxes)  # Print box coordinates

    for box in boxes:
        x1, y1, x2, y2 = box

        # Calculate the center point of the detected object's bounding box.
        centerx = (x1 + x2) / 2
        centery = (y1 + y2) / 2

        # Draw the target center point
        cv2.circle(frame_, (int(centerx), int(centery)), 5, (0, 255, 255), -1)

        dist = sqrt((cWidth - centerx) ** 2 + (cHeight - centery) ** 2)
        dist = round(dist, 1)

        # Range settings
        if segmented_aiming_switch:
            if dist < minDist and dist < stage2_scope:
                minDist = dist  # Update minimum distance
                minBox = box  # Update the box corresponding to the minimum distance
        else:
            # Compare current distance with minimum distance
            if dist < minDist and dist < closest_mouse_dist:
                minDist = dist  # Update minimum distance
                minBox = box  # Update the box corresponding to the minimum distance

        location = (int(centerx), int(centery))
        cv2.putText(frame_, f'dist: {dist}', location, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Check if minimum distance and minimum box have been updated
    if minBox is not None:
        # Get the four coordinates of the minimum box in the current loop
        min_x1, min_y1, min_x2, min_y2 = minBox

        # Mark the closest target as a green box
        cv2.rectangle(frame_, (int(minBox[0]), int(minBox[1])), (int(minBox[2]), int(minBox[3])), (0, 255, 0), 2)
        center_text_x = int((minBox[0] + minBox[2]) / 2)
        center_text_y = int((minBox[1] + minBox[3]) / 2)
        location = (center_text_x, center_text_y)
        cv2.putText(frame_, f'dist: {minDist}', location, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Recalculate the center of the target box
        box_centerx = (min_x1 + min_x2) / 2
        box_centery = (min_y1 + min_y2) / 2
        # Calculate vertical aiming offset
        distance_to_top_border = box_centery - min_y1
        distance_to_left_border = box_centerx - min_x1

        # Final offset distance
        aimOffset_y = distance_to_top_border * aimOffset
        aimOffset_x = distance_to_left_border * aimOffset_Magnification_x

        # Draw offset
        cv2.circle(frame_, (int(box_centerx - aimOffset_x), int(box_centery - aimOffset_y)), 5, (255, 0, 0), -1)

        # Offset target position
        offset_centerx = box_centerx - aimOffset_x
        offset_centery = box_centery - aimOffset_y

        # New position distance to the screen center
        centerx = offset_centerx - cWidth
        centery = offset_centery - cHeight

        # Distance between the screen center and the offset target center
        offset_dist = sqrt((cWidth - offset_centerx) ** 2 + (cHeight - offset_centery) ** 2)
        offset_dist = round(offset_dist, 1)
        # Display offset distance above the offset target center
        offset_location = (int(offset_centerx), int(offset_centery))
        cv2.putText(frame_, f'offset_dist: {offset_dist}', offset_location, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Whether to enable segmented aiming
        if segmented_aiming_switch:
            # Determine if the distance is less than 30 or 100, and then set the value of lockSpeed
            if offset_dist < stage1_scope:  # Strong lock range stage1_scope
                lockSpeed = stage1_intensity  # Strong lock intensity stage1_intensity
            elif offset_dist < stage2_scope:  # Soft lock range stage2_scope
                lockSpeed = stage2_intensity  # Soft lock intensity stage2_intensity

        if method_of_prediction == "Disable prediction":
            print("Prediction disabled")
            # Calculate the distance the cursor should move from its current position to the target position (disable prediction)
            centerx *= lockSpeed
            centery *= lockSpeed

        elif method_of_prediction == "Multiplier prediction":
            print("Multiplier prediction enabled")
            # Add extra offset
            centerx_extra = prediction_factor * centerx
            centery_extra = prediction_factor * centery
            # Calculate mouse movement distance using the updated target position
            centerx = (centerx + centerx_extra) * lockSpeed
            centery = (centery + centery_extra) * lockSpeed

        elif method_of_prediction == "Pixel prediction":
            # If centerx or centery is negative, it means the target is on the left or above the cursor, and the offset needs to be reversed
            extra_offset_x_result = extra_offset_x if centerx >= 0 else -extra_offset_x
            extra_offset_y_result = extra_offset_y if centery >= 0 else -extra_offset_y

            # Calculate mouse movement distance using the updated target position
            centerx = (centerx + extra_offset_x_result) * lockSpeed
            centery = (centery + extra_offset_y_result) * lockSpeed

        # Check if the locker key, Shift key, and mouse lower side key are pressed
        lockKey_pressed = win32api.GetKeyState(lockKey) & 0x8000
        shift_pressed = win32api.GetKeyState(win32con.VK_SHIFT) & 0x8000
        xbutton2_pressed = win32api.GetKeyState(0x05) & 0x8000

        # Move the mouse cursor to the center of the detected box
        # First type: toggle trigger
        if triggerType == "Toggle":
            if aimbot and (win32api.GetKeyState(lockKey) or (mouse_Side_Button_Witch and xbutton2_pressed)):
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(centerx * lockSpeed), int(centery * lockSpeed), 0, 0)

        # Second type: press trigger
        elif triggerType == "Press":
            if aimbot and (lockKey_pressed or (mouse_Side_Button_Witch and xbutton2_pressed)):
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(centerx * lockSpeed), int(centery * lockSpeed), 0, 0)
            elif not (lockKey_pressed or (mouse_Side_Button_Witch and xbutton2_pressed)):
                # Stop code
                pass

        # Third type: shift+press trigger
        elif triggerType == "shift+press":
            if aimbot and ((lockKey_pressed and shift_pressed) or (mouse_Side_Button_Witch and xbutton2_pressed)):
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(centerx * lockSpeed), int(centery * lockSpeed), 0, 0)
            elif not ((lockKey_pressed and shift_pressed) or (mouse_Side_Button_Witch and xbutton2_pressed)):
                # Stop code
                pass

    return frame_

def main_program_loop(model):  # Main program flow code
    global start_time, gc_time, closest_mouse_dist, lockSpeed, triggerType, arduinoMode, lockKey, confidence \
        , run_threads, aimbot, image_label, test_images_GUI, target_selection, target_selection_str, target_mapping \
        , target_selection_var, prediction_factor, should_break, readme_content

    # Load model
    model = load_model_file()

    # Initialize frame counter (frame rate calculation)
    frame_counter = 0
    start_time = time.time()

    # Wait for loading to complete before starting DXcam screenshot to ensure DXcam receives correct parameters
    while True:
        print("Waiting for loading to complete")
        if loaded_successfully:
            # Start DXcam screenshot
            DXcam()
            break

    # If mss screenshot is selected, turn off DXcam
    if not screenshot_mode:
        print("MSS screenshot selected, turning off BetterCam")
        camera.stop()

    if test_window_frame:
        # Create a window and set the flag to cv2.WINDOW_NORMAL (external)
        cv2.namedWindow('frame', cv2.WINDOW_NORMAL)
        # Before displaying the image in the main loop, set the window property to topmost
        cv2.setWindowProperty('frame', cv2.WND_PROP_TOPMOST, 1)

    # Loop to capture the screen
    while run_threads:

        # Screenshot area size
        monitor = calculate_screen_monitor(screen_width, screen_height)

        try:
            target_selection = target_mapping[target_selection_str]
        except KeyError:
            print(f"Key {target_selection_str} not found in target_mapping. (Loading)")
        # print("Current target", target_selection_str)
        # print("Current target", target_mapping)
        # print(segmented_aiming_switch)

        # Screenshot mode selection
        if not screenshot_mode:
            print("Current screenshot mode: mss")
            frame = capture_screen(monitor, sct)  # mss screenshot mode
        elif screenshot_mode:
            print("Current screenshot mode: BetterCam")
            frame = camera.get_latest_frame()  # DXcam screenshot mode
        # ---------------------------------------------------------------------------

        # Detect and track objects (inference part)
        results = model.predict(frame, save=False, conf=confidence, half=True, agnostic_nms=True, iou=0.7,
                                classes=[target_selection], device="cuda:0")
        # ---------------------------------------------------------------------------
        # Draw results
        frame_ = results[0].plot()

        # Calculate distance and draw the closest target as a green box
        try:
            frame_ = calculate_distances(monitor, results, frame_, aimbot, lockSpeed, arduinoMode, lockKey, triggerType)
        except TypeError:
            # Execute this part of the code when a TypeError occurs
            print('lockKey value error. But it doesn’t matter')

        try:
            # Get and display frame rate
            end_time = time.time()
            frame_, frame_counter, start_time = update_and_display_fps(frame_, frame_counter, start_time, end_time)
        except NameError:
            print("ERROR: Failed to display frame rate (Loading)")

        if test_window_frame:
            # Image debug window (external cv2.imshow)
            should_break = display_debug_window(frame_)

        if test_images_GUI:
            # Image debug window (internal GUI)
            # Get screen width and height
            screen_width_1, screen_height_1 = pyautogui.size()
            # Use function to get desired size
            desired_size = get_desired_size(screen_width_1, screen_height_1)
            # Before cv2.imshow, convert frame_ to a PIL.Image object, then convert it to a Tkinter PhotoImage object
            img = cv2.cvtColor(frame_, cv2.COLOR_BGR2RGB)
            im = Image.fromarray(img)
            desired_size = desired_size  # Resize 1
            im_resized = im.resize(desired_size)  # Resize 2
            imgtk = ImageTk.PhotoImage(image=im_resized)
            image_label.config(image=imgtk)
            image_label.image = imgtk

        if test_window_frame:
            if should_break:
                break

        # Perform gc every 120 seconds
        if time.time() - gc_time >= 60:
            gc.collect()
            gc_time = time.time()

    pass

def stop_program():  # Stop sub-threads
    global run_threads, Thread_to_join, root
    camera.stop()
    run_threads = False
    if Thread_to_join:
        Thread_to_join.join()  # Wait for the sub-thread to end
    if root is not None:
        root.quit()
        root.destroy()  # Destroy the window

    os._exit(0)  # Force end the process

def restart_program():  # Restart the software
    python = sys.executable
    os.execl(python, python, *sys.argv)

def Initialization_parameters():  # Initialize parameters

    model = load_model_file()
    aimbot = True
    lockSpeed = 1
    arduinoMode = False
    triggerType = "Press"
    lockKey = 0x02
    aimOffset = 25
    screen_width = 640
    screen_height = 640
    recoil_control.start_control_recoil_thread()
    return (model, aimbot, lockSpeed, arduinoMode, triggerType, lockKey, aimOffset, screen_width,
            screen_height)

if __name__ == "__main__":

    # Priority settings
    p = psutil.Process(os.getpid())
    p.nice(psutil.REALTIME_PRIORITY_CLASS)

    # Load prefix variables
    load_prefix_variables()

    # Crawl version number and announcement
    crawl_information_by_github()

    # Initialize parameters
    (model, aimbot, lockSpeed, arduinoMode, triggerType, lockKey, aimOffset, screen_width, screen_height) \
        = Initialization_parameters()

    freeze_support()

    # Create and start sub-thread 1 to run main_program_loop
    thread1 = threading.Thread(target=main_program_loop, args=(model,))
    thread1.start()

    # Start GUI (run main program)
    create_gui_tkinter()

    # Wait for the main_program_loop thread to end before completely exiting
    thread1.join()
