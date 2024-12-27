import mouse
import os
import importlib.machinery
import importlib.util
import sys
import ctypes
import win32api
import win32con
import platform
from Module.config import Config, Root

#############################################################
# Pyd files list in                                               #
# https://github.com/kvmaibox/kmboxnet/tree/main/python_pyd #
#############################################################
def path_import(module_name):
    """
        导入模块
    :param file:
    :return:
    """
    print("\n******************* 开始动态加载模块 *************************")
    
    # 获取当前Python版本和平台
    py_version = f"cp{sys.version_info.major}{sys.version_info.minor}"
    platform_tag = f"{platform.system().lower()}_{platform.architecture()[0]}"
    file_name = f"{module_name}.{py_version}-{platform_tag}.pyd"
    file_path = Root / "DLLs"/ "python_pyd" / file_name
        
    loader_details = (
        importlib.machinery.ExtensionFileLoader,
        importlib.machinery.EXTENSION_SUFFIXES
    )
    tools_finder = importlib.machinery.FileFinder(
        os.path.dirname(file_path), loader_details)
    print("FileFinder: ", tools_finder)
    
    toolbox_specs = tools_finder.find_spec(module_name)
    print("find_spec: ", toolbox_specs)

    if toolbox_specs is None or toolbox_specs.loader is None:
        raise ImportError(f"无法找到或加载模块: {module_name} ({file_name})")

    toolbox = importlib.util.module_from_spec(toolbox_specs)
    print("module: ", toolbox)
    toolbox_specs.loader.exec_module(toolbox)
    print("导入成功 path_import(): ", toolbox)
    print("检查sys中是否包含了此模块: ", toolbox in sys.modules)
    print("******************* 动态加载模块完成 *************************\n")
    return toolbox

msdk_dll = ctypes.windll.LoadLibrary(f"{Root}/DLLs/x64_msdk.dll")
msdk_dll.M_Open_VidPid.restype = ctypes.c_uint64  # 声明M_Open函数的返回类型为无符号整数
msdk_hdl = msdk_dll.M_Open_VidPid(0x1532, 0x98)  # 打开端口代码

LG_driver = ctypes.CDLL(f"{Root}/DLLs/LGmouseControl/MouseControl.dll")

kmNet = path_import("kmNet")

def click():
    match Config["mouse_mode"]:
        case "飞易来USB":
            msdk_dll.M_KeyDown2(ctypes.c_uint64(msdk_hdl), 1)
            msdk_dll.M_KeyDown2(ctypes.c_uint64(msdk_hdl), 2)
        case "win32":
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        case "mouse":
            mouse.click("left")
        case "Logitech":
            LG_driver.click_Left_down()
            LG_driver.click_Left_up()
        case 'KmBoxNet':
            kmNet.enc_left(1)
            kmNet.enc_left(0)


def move(centerx, centery):
    match Config["mouse_mode"]:
        case "飞易来USB":
            msdk_dll.M_MoveR2(ctypes.c_uint64(msdk_hdl), int(centerx), int(centery))
        case "win32":
            win32api.mouse_event(
                win32con.MOUSEEVENTF_MOVE, int(centerx), int(centery), 0, 0
            )
        case "mouse":
            mouse.move(int(centerx), int(centery), False)
        case "Logitech":
            LG_driver.move_R(int(centerx), int(centery))
        case 'KmBoxNet':
            kmNet.enc_move(int(centerx), int(centery))




##############################################################
# Why is there no press and release method for kmNet?
# Please see:
# https://github.com/kvmaibox/kmboxnet/issues/14
##############################################################
def press(key):
    match Config["mouse_mode"]:
        case "飞易来USB":
            msdk_dll.M_KeyDown2(ctypes.c_uint64(msdk_hdl), key)
        case "win32":
            win32api.keybd_event(key, 0, 0, 0)
        case "mouse":
            mouse.press(key)
        case "Logitech":
            LG_driver.press_key(key)


def release(key):
    match Config["mouse_mode"]:
        case "飞易来USB":
            msdk_hdl.M_KeyUp2(ctypes.c_uint64(msdk_hdl), key)
        case "win32":
            win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)
        case "mouse":
            mouse.release(key)
        case "Logitech":
            LG_driver.release_key(key)
