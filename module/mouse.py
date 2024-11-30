import mouse
import ctypes
import win32api
import win32con
import os
from module.config import Config

dll = ctypes.windll.LoadLibrary("./x64_msdk.dll")
dll.M_Open_VidPid.restype = ctypes.c_uint64  # 声明M_Open函数的返回类型为无符号整数
hdl = dll.M_Open_VidPid(0x1532, 0x98)  # 打开端口代码
dll_path = r".\MouseControl.dll"
if os.path.exists(dll_path):
    LG_driver = ctypes.CDLL(dll_path)


def click():
    match Config["mouse_mode"]:
        case "飞易来USB":
            dll.M_KeyDown2(ctypes.c_uint64(hdl), 1)
            dll.M_KeyDown2(ctypes.c_uint64(hdl), 2)
        case "win32":
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        case "mouse":
            mouse.click("left")
        case "Logitech":
            LG_driver.click_Left_down()
            LG_driver.click_Left_up()


def move(centerx, centery):
    match Config["mouse_mode"]:
        case "飞易来USB":
            dll.M_MoveR2(ctypes.c_uint64(hdl), int(centerx), int(centery))
        case "win32":
            win32api.mouse_event(
                win32con.MOUSEEVENTF_MOVE, int(centerx), int(centery), 0, 0
            )
        case "mouse":
            mouse.move(int(centerx), int(centery), False)
        case "Logitech":
            LG_driver.move_R(int(centerx), int(centery))


def press(key):
    match Config["mouse_mode"]:
        case "飞易来USB":
            dll.M_KeyDown2(ctypes.c_uint64(hdl), key)
        case "win32":
            win32api.keybd_event(key, 0, 0, 0)
        case "mouse":
            mouse.press(key)
        case "Logitech":
            LG_driver.press_key(key)


def release(key):
    match Config["mouse_mode"]:
        case "飞易来USB":
            dll.M_KeyUp2(ctypes.c_uint64(hdl), key)
        case "win32":
            win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)
        case "mouse":
            mouse.release(key)
        case "Logitech":
            LG_driver.release_key(key)
