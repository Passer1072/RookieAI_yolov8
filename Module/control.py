import mouse
import os
import importlib.machinery
import importlib.util
import sys
import ctypes
import win32api
import win32con
import platform
import random
import time
from Module.config import Root
from Module.logger import logger

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
    logger.debug("******************* 开始动态加载模块 *************************")
    
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
    logger.debug("FileFinder: ", tools_finder)
    
    toolbox_specs = tools_finder.find_spec(module_name)
    logger.debug("find_spec: ", toolbox_specs)

    if toolbox_specs is None or toolbox_specs.loader is None:
        raise ImportError(f"无法找到或加载模块: {module_name} ({file_name})")

    toolbox = importlib.util.module_from_spec(toolbox_specs)
    logger.debug("module: ", toolbox)
    toolbox_specs.loader.exec_module(toolbox)
    logger.success("导入成功 path_import(): ", toolbox)
    logger.debug("检查sys中是否包含了此模块: ", toolbox in sys.modules)
    logger.debug("******************* 动态加载模块完成 *************************\n")
    return toolbox

msdk_dll = ctypes.windll.LoadLibrary(f"{Root}/DLLs/x64_msdk.dll")
msdk_dll.M_Open_VidPid.restype = ctypes.c_uint64  # 声明M_Open函数的返回类型为无符号整数
msdk_hdl = msdk_dll.M_Open_VidPid(0x1532, 0x98)  # 打开端口代码

LG_driver = ctypes.CDLL(f"{Root}/DLLs/LGmouseControl/MouseControl.dll")

kmNet = path_import("kmNet")

def emergencStop_valorant(last_state_w, last_state_a, last_state_s, last_state_d):
    # 获取当前按键状态
    state_w = bool(win32api.GetAsyncKeyState(0x57) & 0x8000)  # W键
    state_a = bool(win32api.GetAsyncKeyState(0x41) & 0x8000)  # A键
    state_s = bool(win32api.GetAsyncKeyState(0x53) & 0x8000)  # S键
    state_d = bool(win32api.GetAsyncKeyState(0x44) & 0x8000)  # D键

    stop = False


    # 检测按键是否从按下变为松开
    if not state_w and last_state_w:  # 如果按键W被松开
        logger.debug("W键弹起")
        kmNet.keydown(22)  #保持键盘s键按下
        time.sleep(0.03)
        kmNet.keyup(22)  # 键盘s键松开
        logger.debug("S键点击")
        stop = True
    if not state_a and last_state_a:  # 如果按键A被松开
        logger.debug("A键弹起")
        kmNet.keydown(7)   #保持键盘d键按下
        time.sleep(0.03)
        kmNet.keyup(7)   # 键盘d键松开
        logger.debug("D键点击")
        stop = True
    if not state_s and last_state_s:  # 如果按键S被松开
        logger.debug("S键弹起")
        kmNet.keydown(26)  #保持键盘w键按下
        time.sleep(0.03)
        kmNet.keyup(26)  # 键盘w键松开
        logger.debug("W键点击")
        stop = True
    if not state_d and last_state_d:  # 如果按键D被松开
        logger.debug("D键弹起")
        kmNet.keydown(4)  #保持键盘a键按下
        time.sleep(0.03)
        kmNet.keyup(4)  # 键盘a键松开
        logger.debug("A键点击")
        stop = True

    if stop:
        time.sleep(0.003)  # 添加一个小的延时，避免CPU占用过高

    # 返回更新后的按键状态
    return state_w, state_a, state_s, state_d


def monitor(mode):
    state = None
    match mode:
        case 'KmBoxNet':
            state = bool(kmNet.isdown_right())
        case "win32":
            state = bool(win32api.GetAsyncKeyState(0x02) & 0x8000)
    return state


def click(mode):
    match mode:
        case "飞易来USB":
            msdk_dll.M_KeyDown2(ctypes.c_uint64(msdk_hdl), 1)
            time.sleep(random.uniform(0.12, 0.17))
            msdk_dll.M_KeyDown2(ctypes.c_uint64(msdk_hdl), 2)
            time.sleep(random.uniform(0.12, 0.17))
        case "win32":
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(random.uniform(0.12, 0.17))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(random.uniform(0.12, 0.17))
        case "mouse":
            mouse.click("left")
            time.sleep(random.uniform(0.12, 0.17))
        case "Logitech":
            LG_driver.click_Left_down()
            time.sleep(random.uniform(0.12, 0.17))
            LG_driver.click_Left_up()
            time.sleep(random.uniform(0.12, 0.17))
        case 'KmBoxNet':
            kmNet.left(1)
            time.sleep(random.uniform(0.12, 0.17))
            kmNet.left(0)
            time.sleep(random.uniform(0.12, 0.17))


def move(mode, centerx, centery):
    match mode:
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
def press(mode, key):
    match mode:
        case "飞易来USB":
            msdk_dll.M_KeyDown2(ctypes.c_uint64(msdk_hdl), key)
        case "win32":
            win32api.keybd_event(key, 0, 0, 0)
        case "mouse":
            mouse.press(key)
        case "Logitech":
            LG_driver.press_key(key)


def release(mode, key):
    match mode:
        case "飞易来USB":
            msdk_hdl.M_KeyUp2(ctypes.c_uint64(msdk_hdl), key)
        case "win32":
            win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)
        case "mouse":
            mouse.release(key)
        case "Logitech":
            LG_driver.release_key(key)
