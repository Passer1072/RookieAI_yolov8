import contextlib
import math
import multiprocessing
import os
import queue
import subprocess
import sys
import time
import cv2
import mss
import numpy as np
import pyautogui
import win32api
import win32con
from math import sqrt
from ultralytics import YOLO
from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import QTimer, Qt, QPropertyAnimation, QPoint, QEasingCurve, QParallelAnimationGroup, QRect, QSize
from PyQt6.QtGui import QIcon, QImage, QPixmap, QBitmap, QPainter
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QFileDialog, QMessageBox, QSizePolicy
from multiprocessing import Pipe, Process, Queue, shared_memory, Event
from customLib.animated_status import AnimatedStatus  # 导入 带动画的状态提示浮窗 库
#from automatic_trigger_set_dialog import AutomaticTriggerSetDialog  # 导入自定义设置窗口类
# TODO: Line 1050
from Module.const import method_mode
from Module.config import Config, Root
from Module.control import kmNet
from Module.logger import logger
import Module.control as control
import Module.keyboard as keyboard
import Module.jump_detection as jump_detection
import Module.announcement


def communication_Process(pipe, videoSignal_queue, videoSignal_stop_queue, floating_information_signal_queue,
                          information_output_queue):
    """
    总通信进程
    pipe_parent
    """
    global video_running

    logger.debug("启动 communication_Process 监听信号...")
    while True:
        if pipe.poll():
            try:
                message = pipe.recv()
                if isinstance(message, tuple):  # 处理消息类型
                    cmd, cmd_01 = message
                    logger.debug(f"收到信号: {cmd}")
                    logger.debug(f"信号内容: {cmd_01}")

                    information_output_queue.put(
                        ("log_output_main", message))  # 显示调试信息

                    # 手动触发异常测试
                    if cmd == "trigger_error":
                        logger.info("手动触发异常测试")
                        raise ValueError("[INFO]手动触发的错误")

                    if cmd == "start_video":
                        logger.info("启动视频命令")
                        video_running = True
                        videoSignal_queue.put(("start_video", cmd_01))

                    elif cmd == "stop_video":
                        logger.info("停止视频命令")
                        video_running = False
                        videoSignal_stop_queue.put(("stop_video", cmd_01))

                    elif cmd == "loading_complete":
                        logger.info("软件初始化完毕")
                        floating_information_signal_queue.put(
                            ("loading_complete", cmd_01))

                    elif cmd == "loading_error":
                        logger.error("一般错误，软件初始化失败")
                        floating_information_signal_queue.put(
                            ("error_log", cmd_01))

                    elif cmd == "red_error":
                        logger.fatal("致命错误，无法加载模型")
                        floating_information_signal_queue.put(
                            ("red_error_log", cmd_01))

            except (BrokenPipeError, EOFError) as e:
                logger.error(f"管道通信错误: {e}")
                information_output_queue.put(
                    ("error_log", f"管道通信错误: {e}"))  # 捕获并记录错误信息
            except Exception as e:
                logger.error(f"发生错误: {e}")
                information_output_queue.put(("error_log", f"未知错误: {e}"))


def start_capture_process_multie(shm_name, frame_shape, frame_dtype, frame_available_event,
                                 videoSignal_queue, videoSignal_stop_queue, pipe, information_output_queue,
                                 ProcessMode):
    """
    （多进程）
    子进程视频信号获取逻辑 \n
    接收内容:\n
    1.start_video \n
    2.stop_video
    """

    # 连接到共享内存
    existing_shm = shared_memory.SharedMemory(name=shm_name)
    shared_frame = np.ndarray(
        frame_shape, dtype=frame_dtype, buffer=existing_shm.buf)

    logger.debug("视频信号获取进程已启动。")
    while True:
        try:
            message = videoSignal_queue.get(timeout=1)
            command, information = message
            logger.debug(f"接收到命令: {command}, 内容: {information}")
            information_output_queue.put(
                ("video_signal_acquisition_log", message))  # 调试信息输出

            if command == "start_video":
                logger.debug("进程模式选择")
                logger.info("进程模式：", ProcessMode)
                open_screen_video(
                    shared_frame, frame_available_event, videoSignal_stop_queue)
            if command == "change_model":
                logger.info("正在重新加载模型")
                model_file = information
                model = YOLO(model_file)
                logger.info(f"模型 {model_file} 加载完毕")
        except queue.Empty:
            pass
        except Exception as e:
            logger.error(f"获取视频信号时发生错误: {e}")
            information_output_queue.put(("error_log", f"获取视频信号时发生错误: {e}"))


def start_capture_process_single(videoSignal_queue, videoSignal_stop_queue, information_output_queue,
                                 processedVideo_queue, YoloSignal_queue, pipe_parent, model_file,
                                 box_shm_name, box_data_event, box_lock, accessibilityProcessSignal_queue):
    """
    （单进程）子进程视频信号获取逻辑
    接收内容:
    1.start_video
    2.stop_video
    """
    logger.debug("视频信号获取进程已启动。")

    def initialization_Yolo(model_file, information_output_queue):
        """初始化 YOLO 并进行一次模拟推理"""
        try:
            # 检查模型文件是否存在
            if not os.path.exists(model_file):
                logger.warn(f"模型文件 '{model_file}' 未找到，尝试使用默认模型 'yolov8n.pt'。")
                information_output_queue.put(
                    ("log_output_main", f"模型文件 '{model_file}' 未找到，使用默认模型 yolov8n.pt'。"))
                model_file = "yolov8n.pt"
                log_message = f"[ERROR]一般错误，模型文件 '{model_file}' 未找到，使用默认模型 'yolov8n.pt'。"
                # 选定文件未能找到，黄色报错
                pipe_parent.send(("loading_error", log_message))
                if not os.path.exists(model_file):
                    logger.fatal(f"致命错误，默认模型文件 '{model_file}' 也未找到。请确保模型文件存在。")
                    log_message = f"[ERROR]致命错误，默认模型文件 '{model_file}' 也未找到。请确保模型文件存在。"
                    # 默认文件也未找到，红色报错
                    pipe_parent.send(("red_error", log_message))
                    raise FileNotFoundError(
                        f"默认模型文件 '{model_file}' 也未找到。请确保模型文件存在。")

            model = YOLO(model_file)  # 加载 YOLO 模型
            logger.info(f"YOLO 模型 '{model_file}' 已加载。")
            # 创建一张临时图像（纯色或随机噪声）用于预热
            temp_img = np.zeros((320, 320, 3), dtype=np.uint8)  # 修改为640x640
            temp_img_path = "temp_init_image.jpg"
            cv2.imwrite(temp_img_path, temp_img)
            # 执行一次模拟推理
            model.predict(temp_img_path, conf=0.5)
            logger.debug("YOLO 模型已预热完成。")
            os.remove(temp_img_path)  # 删除临时图像
            return model
        except Exception as e:
            logger.error(f"YOLO 初始化失败: {e}")
            information_output_queue.put(("error_log", f"YOLO 初始化失败: {e}"))
            return None

    model = initialization_Yolo(
        model_file, information_output_queue)  # 初始化YOLO
    pipe_parent.send(("loading_complete", True))  # 初始化加载完成标志

    with contextlib.suppress(KeyboardInterrupt):
        while True:
            """开始监听视频开关信号"""
            try:
                message = videoSignal_queue.get(timeout=1)
                command, information = message
                logger.debug(f"接收到命令: {command}, 内容: {information}")
                information_output_queue.put(
                    ("video_signal_acquisition_log", message))  # 调试信息输出
                if command == 'start_video':
                    logger.debug("启动视频捕获和YOLO处理")
                    # 调用集成了共享内存写入的屏幕捕获和YOLO处理函数
                    screen_capture_and_yolo_processing(
                        processedVideo_queue, videoSignal_stop_queue, YoloSignal_queue,
                        pipe_parent, information_output_queue, model,
                        box_shm_name, box_data_event, box_lock, accessibilityProcessSignal_queue
                    )
                if command == 'change_model':  # 重新加载模型
                    logger.info("正在重新加载模型")
                    model_file = information
                    model = YOLO(model_file)
                    logger.info(f"模型 {model_file} 加载完毕")
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"获取视频信号时发生错误: {e}")
                information_output_queue.put(
                    ("error_log", f"获取视频信号时发生错误: {e}"))


def open_screen_video(shared_frame, frame_available_event, videoSignal_stop_queue):
    """（多进程）打开屏幕捕获并显示视频帧，限制截图速率为100 FPS"""
    # 清空 videoSignal_stop_queue 队列
    while not videoSignal_stop_queue.empty():
        try:
            videoSignal_stop_queue.get_nowait()
        except Exception:
            break
    with mss.mss() as sct:
        _extracted_from_open_screen_video_11(
            videoSignal_stop_queue, sct, shared_frame, frame_available_event
        )


# TODO Rename this here and in `open_screen_video`
def _extracted_from_open_screen_video_11(videoSignal_stop_queue, sct, shared_frame, frame_available_event):
    # 获取屏幕分辨率
    screen_width, screen_height = pyautogui.size()
    logger.info("屏幕分辨率:", screen_width, screen_height)

    # 计算中心区域 320x320 的截取范围
    capture_width, capture_height = 320, 320
    left = (screen_width - capture_width) // 2
    top = (screen_height - capture_height) // 2
    capture_area = {
        "top": top,
        "left": left,
        "width": capture_width,
        "height": capture_height
    }

    # 初始化 'frame' 以避免引用前未赋值
    frame = np.zeros((capture_height, capture_width, 3), dtype=np.uint8)

    frame_interval = 0.05

    while True:
        frame_start_time = time.time()  # 记录帧开始时间

        # 检查是否收到停止信号
        if not videoSignal_stop_queue.empty():
            command, _ = videoSignal_stop_queue.get()
            logger.debug(f"videoSignal_stop_queue（多进程） 队列接收信息 {command}")
            if command == 'stop_video':
                logger.debug("停止屏幕捕获")
                break  # 退出循环

        # 获取指定区域的截图
        img = sct.grab(capture_area)

        # 使用 numpy.frombuffer 直接转换为数组，避免数据拷贝
        frame = np.frombuffer(img.rgb, dtype=np.uint8)
        frame = frame.reshape((img.height, img.width, 3))

        # 转换颜色空间，从 BGRA 到 RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)

        # 将视频帧放入共享内存
        np.copyto(shared_frame, frame)
        frame_available_event.set()

        # 计算已用时间
        frame_end_time = time.time()
        elapsed_time = frame_end_time - frame_start_time

        # 计算剩余时间
        remaining_time = frame_interval - elapsed_time
        if remaining_time > 0:
            time.sleep(remaining_time)
        else:
            # 如果处理时间超过了帧间隔，可能需要记录或优化
            logger.warn(
                f"视频帧处理时间 {elapsed_time:.4f} 秒超过目标间隔 {frame_interval:.4f} 秒")


def screen_capture_and_yolo_processing(processedVideo_queue, videoSignal_stop_queue, YoloSignal_queue, pipe_parent,
                                       information_output_queue, model,
                                       box_shm_name, box_data_event, box_lock, accessibilityProcessSignal_queue):
    """
    （单进程）整合屏幕捕获和 YOLO 推理。

    参数:
    - processedVideo_queue: 处理后的视频队列
    - videoSignal_stop_queue: 视频停止信号队列
    - YoloSignal_queue: YOLO 控制队列
    - pipe_parent: 管道父端
    - information_output_queue: 调试信息输出队列
    - model: YOLO 模型实例
    - box_shm_name: Box 坐标共享内存名称
    - box_data_event: 用于通知 Box 数据可用的 Event
    - box_lock: 用于同步访问共享内存的 Lock
    """
    global unique_id_counter

    yolo_enabled = False
    yolo_confidence = 0.5  # 初始化 YOLO 置信度
    unique_id_counter = 0

    # 清空 videoSignal_stop_queue 队列
    while not videoSignal_stop_queue.empty():
        try:
            videoSignal_stop_queue.get_nowait()
        except Exception:
            break

    with mss.mss(backend='directx') as sct:
        # 获取屏幕分辨率
        screen_width, screen_height = pyautogui.size()
        logger.info("屏幕分辨率:", screen_width, screen_height)
        # 计算中心区域 320x320 的截取范围
        capture_width, capture_height = 320, 320
        left = (screen_width - capture_width) // 2
        top = (screen_height - capture_height) // 2
        capture_area = {
            "top": top,
            "left": left,
            "width": capture_width,
            "height": capture_height
        }
        while True:
            try:
                # 检查是否收到停止信号
                if not videoSignal_stop_queue.empty():
                    command, _ = videoSignal_stop_queue.get()
                    logger.debug(f"videoSignal_stop_queue（单进程） 队列接收信息 {command}")
                    if command == 'stop_video':
                        logger.debug("停止屏幕捕获")
                        break
                    if command == 'change_model':
                        logger.debug("重新加载模型")
                        break
                # 检查 YOLO 的开启或停止信号
                if not YoloSignal_queue.empty():
                    command_data = YoloSignal_queue.get()
                    if isinstance(command_data, tuple):
                        cmd, cmd_01 = command_data
                        information_output_queue.put(
                            ("video_processing_log", command_data))
                        if cmd == 'YOLO_start':
                            yolo_enabled = True
                        elif cmd == 'YOLO_stop':
                            yolo_enabled = False
                        elif cmd == "change_conf":  # 更改置信度
                            logger.debug("更改置信度")
                            yolo_confidence = cmd_01
                        elif cmd == "change_class":
                            logger.debug(f"更改检测类别为: {cmd_01}")
                            target_class = cmd_01  # 更新目标类别
                        elif cmd == "aim_range_change":
                            aim_range = cmd_01
                            logger.debug(f"瞄准范围更改_02: {aim_range}")
                # 获取屏幕帧
                img = sct.grab(capture_area)
                # 转换为 numpy 数组
                frame = np.frombuffer(img.rgb, dtype=np.uint8).reshape(
                    (img.height, img.width, 3))
                # 转换颜色空间从 BGRA 到 RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
                # 如果启用了 YOLO，执行推理并写入共享内存
                if yolo_enabled and model is not None:
                    processed_frame = YOLO_process_frame(
                        model, frame, accessibilityProcessSignal_queue, yolo_confidence,
                        target_class=target_class,  # 使用更新后的目标类别
                        box_shm_name=box_shm_name,
                        box_data_event=box_data_event,
                        box_lock=box_lock,
                        aim_range=aim_range,
                    )
                else:
                    processed_frame = frame
                # 将处理后的帧放入队列中
                processedVideo_queue.put(processed_frame)
            except Exception as e:
                logger.warn(f"捕获或处理时出错: {e}")
                information_output_queue.put(("error_log", f"捕获或处理时出错: {e}"))
                break


def video_processing(shm_name, frame_shape, frame_dtype, frame_available_event,
                     processedVideo_queue, YoloSignal_queue, pipe_parent, information_output_queue, model_file,
                     box_shm_name, box_data_event, box_lock, accessibilityProcessSignal_queue):
    """
    （多进程）对视频进行处理，支持 YOLO 推理。

    参数:
    - shm_name: 视频帧共享内存名称
    - frame_shape: 视频帧形状
    - frame_dtype: 视频帧数据类型
    - frame_available_event: 用于通知新帧可用的 Event
    - processedVideo_queue: 处理后的视频队列
    - YoloSignal_queue: YOLO 控制队列
    - pipe_parent: 管道父端
    - information_output_queue: 调试信息输出队列
    - model_file: YOLO 模型文件路径
    - box_shm_name: Box 坐标共享内存名称
    - box_data_event: 用于通知 Box 数据可用的 Event
    - box_lock: 用于同步访问共享内存的 Lock
    """
    global unique_id_counter

    yolo_enabled = False
    model = None
    frame = None
    yolo_confidence = 0.5
    target_class = "ALL"  # 初始化目标类别
    unique_id_counter = 0
    aim_range = 20  # 瞄准范围默认值

    # 连接到共享内存
    existing_shm = shared_memory.SharedMemory(name=shm_name)
    shared_frame = np.ndarray(
        frame_shape, dtype=frame_dtype, buffer=existing_shm.buf)

    try:
        # 初始化 YOLO
        # 检查模型文件是否存在，如果不存在则使用默认模型
        if not os.path.exists(model_file):
            logger.warn(f"模型文件 '{model_file}' 未找到，尝试使用默认模型 'yolov8n.pt'")
            information_output_queue.put(
                ("log_output_main", f"模型文件 '{model_file}' 未找到，使用默认模型 'yolov8n.pt'。"))
            log_message = f"[ERROR]一般错误，模型文件 '{model_file}' 未找到，使用默认模型 'yolov8n.pt'。"
            pipe_parent.send(("loading_error", log_message))  # 选定文件未能找到，黄色报错
            model_file = "yolov8n.pt"
            if not os.path.exists(model_file):
                logger.fatal(f"致命错误，默认模型文件 '{model_file}' 也未找到。请确保模型文件存在。")
                log_message = f"[ERROR]致命错误，默认模型文件 '{model_file}' 也未找到。请确保模型文件存在。"
                pipe_parent.send(("red_error", log_message))  # 默认文件也未找到，红色报错
                raise FileNotFoundError(
                    f"默认模型文件 '{model_file}' 也未找到。请确保模型文件存在。")
        model = YOLO(model_file)
        logger.debug("YOLO 模型已加载。")

        # 进行一次模拟推理以预热模型
        temp_img = np.zeros((320, 320, 3), dtype=np.uint8)
        model.predict(temp_img, conf=0.5)
        logger.debug("YOLO 模型已预热完成。")

        pipe_parent.send(("loading_complete", True))  # 软件初始化加载完毕标志

        while True:
            # 检查 YoloSignal_queue 中的信号
            if not YoloSignal_queue.empty():
                command_data = YoloSignal_queue.get()
                if isinstance(command_data, tuple):
                    cmd, cmd_01 = command_data
                    logger.debug(
                        f"video_processing(YoloSignal_queue) 收到命令: {cmd}, 信息: {cmd_01}")
                    information_output_queue.put(
                        ("video_processing_log", command_data))  # 显示调试信息
                    if cmd == 'YOLO_start':
                        yolo_enabled = True
                    elif cmd == 'YOLO_stop':
                        yolo_enabled = False
                    elif cmd == 'change_model':
                        logger.debug("video_processing进程 模型已重新加载")
                        model = YOLO(cmd_01)
                    elif cmd == "change_conf":
                        logger.debug("更改置信度")
                        yolo_confidence = cmd_01
                    elif cmd == "change_class":
                        logger.debug(f"更改检测类别为: {cmd_01}")
                        target_class = cmd_01  # 更新目标类别
                    elif cmd == "aim_range_change":
                        aim_range = cmd_01
                        logger.debug(f"瞄准范围更改_01: {aim_range}")

            # 等待新帧
            frame_available_event.wait()
            frame = shared_frame.copy()
            frame_available_event.clear()

            if yolo_enabled and model is not None:
                # 执行 YOLO 推理并写入共享内存
                processed_frame = YOLO_process_frame(
                    model, frame, yolo_confidence,
                    target_class=target_class,  # 使用更新后的目标类别
                    box_shm_name=box_shm_name,
                    box_data_event=box_data_event,
                    box_lock=box_lock,
                    aim_range=aim_range,
                )
            else:
                processed_frame = frame

            # 将处理后的帧放入队列
            processedVideo_queue.put(processed_frame)
    except Exception as e:
        logger.error(f"视频处理发生错误: {e}")
        information_output_queue.put(("error_log", f"视频处理发生错误: {e}"))
    finally:
        existing_shm.close()


def YOLO_process_frame(
    model,
    frame,
    accessibilityProcessSignal_queue,
    yolo_confidence=0.1,
    target_class="ALL",
    box_shm_name=None,
    box_data_event=None,
    box_lock=None,
    aim_range=100
):
    """
    对帧进行 YOLO 推理，返回带有标注的图像，并将最近的 Box 坐标、距离和唯一ID写入共享内存。
    """
    global unique_id_counter  # 声明使用全局变量
    try:
        # 确定 YOLO 推理中要使用的类别
        if target_class == "ALL":
            classes = None  # 允许检测所有类别
        else:
            try:
                classes = [int(target_class)]  # 只检测指定的类别
            except ValueError:
                classes = None  # 如果转换失败，则检测所有类别

        # 执行 YOLO 推理
        results = model.predict(
            frame,
            save=False,
            device="cuda:0",
            verbose=False,
            save_txt=False,
            half=True,
            conf=yolo_confidence,
            classes=classes  # 指定类别
        )

        # 获取检测结果
        boxes = results[0].boxes.xyxy  # 获取所有 Box 的 xyxy 坐标
        distances = []  # 用于存储每个 Box 到帧中心的距离
        frame = results[0].plot()  # 绘制检测框信息

        # 计算帧中心点
        frame_height, frame_width = frame.shape[:2]
        frame_center = (frame_width / 2, frame_height / 2)

        # 计算每个 Box 的距离
        for box in boxes:
            x1, y1, x2, y2 = box.cpu().numpy()  # 获取每个 Box 的坐标
            box_center = ((x1 + x2) / 2, (y1 + y2) / 2)  # 计算每个 Box 的中心点
            distance = sqrt((box_center[0] - frame_center[0]) ** 2 + (box_center[1] - frame_center[1]) ** 2)  # 计算距离
            distances.append(distance)  # 将距离加入到 distances 列表中

        # 找到距离最近的 Box
        if distances:
            min_distance_idx = np.argmin(distances)  # 找到最小距离的索引
            closest_box = boxes[min_distance_idx].cpu().numpy()
            closest_distance = distances[min_distance_idx]
            new_trigger_conditions = True
        else:
            closest_box = None
            closest_distance = None
            new_trigger_conditions = False

        # 初始化 last_put_data
        if not hasattr(YOLO_process_frame, "last_put_data"):
            YOLO_process_frame.last_put_data = None

        # 发送 Trigger_conditions 到队列，避免重复数据
        if new_trigger_conditions != YOLO_process_frame.last_put_data:
            try:
                accessibilityProcessSignal_queue.put(
                    ("Trigger_conditions", False), timeout=0.1
                )
                YOLO_process_frame.last_put_data = new_trigger_conditions
                logger.debug(f"放入队列的数据: ('Trigger_conditions', {new_trigger_conditions})")
            except multiprocessing.queues.Full:
                logger.warning("accessibilityProcessSignal_queue 已满，无法放入数据")

        # 将最近的 Box 坐标、距离和唯一ID写入共享内存
        if box_shm_name and box_data_event and box_lock:
            # 连接到共享内存
            box_shm = shared_memory.SharedMemory(name=box_shm_name)
            # 修改共享内存结构，加入unique_id
            box_array = np.ndarray(
                (1, 6), dtype=np.float32, buffer=box_shm.buf
            )
            with box_lock:
                box_array.fill(0)  # 清空之前的数据
                if closest_box is not None:
                    x1, y1, x2, y2 = closest_box
                    unique_id_counter += 1  # 递增唯一ID
                    unique_id = unique_id_counter
                    box_array[0, :4] = [x1, y1, x2, y2]  # 存储最近的 Box 坐标
                    box_array[0, 4] = closest_distance  # 存储距离
                    box_array[0, 5] = unique_id  # 存储唯一ID
            # 发送 Box 数据可用信号
            box_data_event.set()
            box_shm.close()

        # 绘制一个淡蓝色的细圆（瞄准范围）
        circle_color = (173, 216, 230)  # 淡蓝色
        cv2.circle(frame, (int(frame_center[0]), int(frame_center[1])), aim_range, circle_color, 1)

        # 绘制所有 Box
        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = box.cpu().numpy()
            box_center = (int((x1 + x2) / 2), int((y1 + y2) / 2))
            # 默认所有框使用黄色连接线
            box_color = (255, 255, 0)  # 黄色边框
            line_color = (255, 255, 0)  # 黄色连接线
            # 绘制矩形框
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), box_color, 2)
            # 绘制中心点
            cv2.circle(frame, box_center, 5, (0, 0, 255), -1)
            # 绘制连接线条
            cv2.line(frame, box_center, (int(frame_center[0]), int(frame_center[1])), line_color, 2)
            # 计算距离
            distance = sqrt((box_center[0] - frame_center[0]) ** 2 + (box_center[1] - frame_center[1]) ** 2)
            # 绘制距离文本
            distance_text = f"{distance:.1f}px"
            cv2.putText(frame, distance_text, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        # 如果有最近的 Box，再绘制其绿色框和红色连接线（覆盖上一步绘制）
        if closest_box is not None:
            # 获取最近的 Box 的坐标和中心
            x1, y1, x2, y2 = closest_box
            box_center = (int((x1 + x2) / 2), int((y1 + y2) / 2))
            # 只有当距离小于 aim_range 时，才绘制绿色框和红色连接线
            if closest_distance < aim_range:
                # 绘制最近的框的绿色边框
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 3)
                # 绘制中心点
                cv2.circle(frame, box_center, 5, (0, 255, 0), -1)
                # 绘制红色连接线
                cv2.line(frame, box_center, (int(frame_center[0]), int(frame_center[1])), (255, 0, 0), 3)

        # 返回带有检测结果的图像
        return frame  # 返回绘制后的图像是 BGR 格式

    except Exception as e:
        logger.error(f"YOLO 推理失败: {e}")
        return frame  # 如果 YOLO 推理失败，返回原始帧


def mouse_move_prosses(box_shm_name, box_lock, mouseMoveProssesSignal_queue, accessibilityProcessSignal_queue,
                       aim_speed_x=0.2, aim_speed_y=0.0, aim_range=100, offset_centerx=0, offset_centery=0.3,
                       lockKey=0x02, aimbot_switch=True, mouse_Side_Button_Witch=True,
                       screen_pixels_for_360_degrees=1800,
                       screen_height_pixels=900, near_speed_multiplier=2, slow_zone_radius=10, mouseMoveMode='win32'):
    """
    鼠标移动进程，读取最近的 Box 数据并执行鼠标移动。

    参数:
    - box_shm_name: Box 坐标共享内存的名称
    - box_lock: 用于同步访问共享内存的 Lock
    - aim_speed_x: X轴基础瞄准速度
    - aim_speed_y: Y轴基础瞄准速度
    - aim_range: 瞄准范围
    - threshold: 距离阈值
    - fast_decay_rate: 当 distance < threshold 时的衰减率
    - slow_decay_rate: 当 distance >= threshold 时的衰减率
    - offset_centerx: X 轴瞄准偏移量
    - offset_centery: Y 轴瞄准偏移量
    - lockKey: 锁定键代码
    - aimbot_switch: 自瞄开关
    - mouse_Side_Button_Witch: 是否开启鼠标侧键瞄准
    """

    IP = "192.168.2.188"
    PORT = "1244"
    MAC = "84FF7019"
    connectKmBox = False

    logger.debug("测试KmBoxNet连通性...")
    response = subprocess.run(
        ["ping", IP], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = response.stdout.decode('gbk', errors='ignore')
    logger.debug(output)

    # 根据 returncode 判断是否连通
    if response.returncode == 0:
        logger.info("KmBoxNet IP连通成功")
    else:
        logger.error("KmBoxNet IP连通测试失败")

    # 连接到 Box 共享内存
    box_shm = shared_memory.SharedMemory(name=box_shm_name)
    box_array = np.ndarray((1, 6), dtype=np.float32, buffer=box_shm.buf)

    # 获取截图中心坐标
    screenshot_center_x = 320 // 2
    screenshot_center_y = 320 // 2

    # 初始化变量
    last_unique_id = 0    # 上次读取的数据的唯一ID

    # 触发方式 按下/切换 press/toggle
    trigger_mode = 'press'
    trigger_toggle_state = False  # 切换触发模式下的运行状态
    prev_lockKey_pressed = False  # 上一次循环时触发键的状态

    # 初始化目标切换状态
    target_switching = False
    last_offset_distance = None  # 上次的偏移后目标距离
    fluctuation_range = 10  # 波动范围，单位：像素
    jump_detection_switch = True  # 跳变检测开关

    # 初始化自动扳机
    automatic_trigger_range_scale_factor = 0.1

    # 初始化 last_put_data 变量
    last_put_data = None

    try:
        while True:
            '''信号检查部分'''
            if not mouseMoveProssesSignal_queue.empty():
                command_data = mouseMoveProssesSignal_queue.get()
                logger.debug(f"mouseMoveProssesSignal_queue 队列收到信号: {command_data}")
                if isinstance(command_data, tuple):
                    cmd, cmd_01 = command_data
                    if cmd == "aimbot_switch_change":
                        aimbot_switch = cmd_01
                        logger.debug(f"自瞄状态更改: {aimbot_switch}")
                    elif cmd == "aim_speed_x_change":
                        aim_speed_x = cmd_01
                        logger.debug(f"X轴瞄准速度更改: {aim_speed_x}")
                    elif cmd == "aim_speed_y_change":
                        aim_speed_y = cmd_01
                        logger.debug(f"Y轴瞄准速度更改: {aim_speed_y}")
                    elif cmd == "aim_range_change":
                        aim_range = cmd_01
                        logger.debug(f"瞄准范围更改: {aim_range}")
                    elif cmd == "offset_centerx_change":
                        offset_centerx = cmd_01
                        logger.debug(f"瞄准偏移X更改: {offset_centerx}")
                    elif cmd == "offset_centery_change":
                        offset_centery = cmd_01
                        logger.debug(f"瞄准偏移Y更改: {offset_centery}")
                    elif cmd == "triggerMethod_change":
                        triggerMethod = cmd_01
                        logger.debug(f"瞄准热键触发方式更改: {triggerMethod}")
                    elif cmd == "lock_key_change":
                        lockKey = cmd_01
                        logger.debug(f"瞄准热键更改: {lockKey}")
                    elif cmd == "mouse_Side_Button_Witch_change":
                        mouse_Side_Button_Witch = cmd_01
                        logger.debug(f"侧键瞄准开关更改: {mouse_Side_Button_Witch}")
                    elif cmd == "trigger_mode_change":
                        trigger_mode = cmd_01  # 'press' 或 'toggle'
                        logger.debug(f"触发模式已更改为: {trigger_mode}")
                    elif cmd == "screen_pixels_for_360_degrees":
                        screen_pixels_for_360_degrees = cmd_01
                        logger.debug(f"游戏内X像素设置为: {screen_pixels_for_360_degrees}")
                    elif cmd == "screen_height_pixels":
                        screen_height_pixels = cmd_01
                        logger.debug(f"游戏内Y像素设置为: {screen_height_pixels}")
                    elif cmd == "near_speed_multiplier":
                        near_speed_multiplier = cmd_01
                        logger.debug(f"近点瞄准速度倍率设置为: {near_speed_multiplier}")
                    elif cmd == "slow_zone_radius":
                        slow_zone_radius = cmd_01
                        logger.debug(f"减速区域设置为: {slow_zone_radius}")
                    elif cmd == "mouseMoveMode":
                        mouseMoveMode = cmd_01
                        logger.debug(f"设置鼠标移动模式为: {mouseMoveMode}")
                    elif cmd == "automatic_trigger_range_switching":
                        automatic_trigger_range_scale_factor = cmd_01
                        print(f"自动扳机范围比例设置为: {automatic_trigger_range_scale_factor}")
                    elif cmd == "jump_detection_switch":
                        jump_detection_switch = cmd_01
                        logger.debug(f"跳变检测设置为: {jump_detection_switch}")
                    elif cmd == "jump_suppression_fluctuation_range":
                        fluctuation_range = cmd_01
                        logger.debug(f"跳变误差设置为: {fluctuation_range}")

            if mouseMoveMode == "KmBoxNet" and not connectKmBox:
                '''连接KmBox'''
                logger.info("尝试连接KmBox")
                kmNet.init(IP, PORT, MAC)  # 连接盒子
                kmNet.enc_move(100, 100)  # 测试移动
                connectKmBox = True
                logger.info("KmBox连接成功")

            pixels_per_degree_x = screen_pixels_for_360_degrees / 360  # 每度需要的像素数度
            pixels_per_degree_y = screen_height_pixels / 180  # 每度像素数

            '''鼠标移动处理部分'''
            # 获取最新的 Box 数据
            with box_lock:
                boxes = box_array.copy()

            # 获取最近的 Box（第一项）
            closest_box = boxes[0]
            x1, y1, x2, y2, distance, unique_id = closest_box

            # 检查是否有新数据
            if unique_id != last_unique_id:
                # 有新数据
                last_unique_id = int(unique_id)
                if not np.all(closest_box[:5] == 0):
                    # 计算Box的中心点
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2

                    # 将 Box 中心点坐标从左上角坐标系转为以截图中心为原点的坐标系
                    center_x_relative_to_center = center_x - screenshot_center_x
                    center_y_relative_to_center = center_y - screenshot_center_y

                    # 计算中心点到上边框的垂直距离
                    vertical_distance = center_y - y1
                    # logger.debug(f"中心点到上边框的垂直距离: {vertical_distance}")

                    # 计算左边框到右边框的距离
                    horizontal_distance = x2 - x1
                    # logger.debug(f"左边框到右边框的水平距离: {horizontal_distance}")

                    # 计算目标相对于截图中心的偏移
                    delta_x = horizontal_distance * offset_centerx
                    delta_y = -vertical_distance * offset_centery
                    offset_target_x = center_x_relative_to_center + delta_x  # 偏移后目标点X
                    offset_target_y = center_y_relative_to_center + delta_y  # 偏移后目标点Y

                    # 计算偏移后的距离
                    offset_distance = math.sqrt(
                        offset_target_x ** 2 + offset_target_y ** 2)

                    # 自动扳机范围计算
                    box_horizontal_length = x2 - x1  # Box 的横向长度
                    automatic_trigger_range = (box_horizontal_length * automatic_trigger_range_scale_factor) / 2  # 半径为横向长度 * 缩放因子的一半

                    # 将像素偏移转换为角度偏移
                    angle_offset_x = offset_target_x / pixels_per_degree_x  # 度
                    angle_offset_y = offset_target_y / pixels_per_degree_y  # 度

                    # 基础 aim_speed 和最大 aim_speed
                    base_aim_speed_x = aim_speed_x  # x轴的基础速度
                    base_aim_speed_y = aim_speed_y  # y轴的基础速度
                    max_aim_speed_x = near_speed_multiplier * base_aim_speed_x  # 最大X速度
                    max_aim_speed_y = near_speed_multiplier * base_aim_speed_y  # 最大Y速度

                    # 动态调整 aim_speed
                    if offset_distance < slow_zone_radius:
                        # 偏移距离越小，aim_speed 越接近 base_aim_speed
                        last_aim_speed_x = base_aim_speed_x + (max_aim_speed_x - base_aim_speed_x) * (
                                    offset_distance / slow_zone_radius)
                        last_aim_speed_y = base_aim_speed_y + (max_aim_speed_y - base_aim_speed_y) * (
                                    offset_distance / slow_zone_radius)
                    elif offset_distance < aim_range:
                        # 使用偏移后的距离动态调整 aim_speed
                        last_aim_speed_x = base_aim_speed_x + (max_aim_speed_x - base_aim_speed_x) * (
                                    1 - offset_distance / aim_range)
                        last_aim_speed_y = base_aim_speed_y + (max_aim_speed_y - base_aim_speed_y) * (
                                    1 - offset_distance / aim_range)
                    else:
                        # 超过瞄准范围时，保持基础 aim_speed
                        last_aim_speed_x = base_aim_speed_x
                        last_aim_speed_y = base_aim_speed_y

                    # 保留小数点后两位
                    last_aim_speed_x = round(last_aim_speed_x, 2)
                    last_aim_speed_y = round(last_aim_speed_y, 2)

                    move_x = angle_offset_x * last_aim_speed_x * 2
                    move_y = angle_offset_y * last_aim_speed_y * 2

                    # 判断目标是否在瞄准范围内
                    target_is_within_range = distance < aim_range

                    if isinstance(lockKey, str) and lockKey.startswith("0x"):
                        lockKey = int(lockKey, 16)  # 转换为十六进制整数

                    # 检查锁定键、鼠标侧键和 Shift 键是否按下
                    lockKey_pressed = bool(win32api.GetKeyState(lockKey) & 0x8000)
                    xbutton2_pressed = bool(win32api.GetKeyState(0x05) & 0x8000)  # 鼠标侧键
                    shift_pressed = bool(win32api.GetKeyState(win32con.VK_SHIFT) & 0x8000)  # Shift 键

                    if trigger_mode == 'press':
                        # 按下模式：只需检测按键是否被按下
                        should_move = aimbot_switch and target_is_within_range and (
                            lockKey_pressed or (
                                mouse_Side_Button_Witch and xbutton2_pressed)
                        )
                    elif trigger_mode == 'shift+press':
                        # Shift + 按下模式：需要同时按下 Shift 和锁定键
                        should_move = aimbot_switch and target_is_within_range and (
                            shift_pressed and lockKey_pressed
                        )

                    elif trigger_mode == 'toggle':
                        # 检测按键从未按下变为按下的瞬间
                        if lockKey_pressed and not prev_lockKey_pressed:
                            trigger_toggle_state = not trigger_toggle_state  # 切换运行状态
                            # logger.debug(f"切换触发状态已更改为: {trigger_toggle_state}")
                        # 更新上一次的按键状态
                        prev_lockKey_pressed = lockKey_pressed
                        # 切换模式：运行状态由 `trigger_toggle_state` 控制
                        should_move = aimbot_switch and target_is_within_range and trigger_toggle_state

                    # 独立的触发逻辑：当仅按下 xbutton2_pressed，mouse_Side_Button_Witch 为 True，同时目标在瞄准范围内
                    if mouse_Side_Button_Witch and xbutton2_pressed and target_is_within_range:
                        should_move = True

                    # 自动扳机：如果目标进入自动扳机范围，则满足触发条件
                    Trigger_conditions = offset_distance <= int(automatic_trigger_range)
                    new_data = ("Trigger_conditions", Trigger_conditions)
                    if new_data != last_put_data:
                        try:
                            accessibilityProcessSignal_queue.put(new_data, timeout=0.1)
                            last_put_data = new_data
                            logger.debug(f"放入队列的数据: {new_data}")
                        except multiprocessing.queues.Full:
                            logger.warning("accessibilityProcessSignal_queue 已满，无法放入数据")

                    # 判断是否发生目标切换：通过move_x_int和move_y_int的数值变化规律
                    if should_move:
                        move_x_int = round(move_x / 2)
                        move_y_int = round(move_y / 2)

                        if last_offset_distance is not None:
                            # 调用跳变检测函数
                            target_switching = jump_detection.check_target_switching(offset_distance, last_offset_distance,
                                                                                     jump_detection_switch, fluctuation_range, target_switching)

                        # 保存当前的 offset_distance 用于下一次比较
                        last_offset_distance = int(offset_distance)

                        # 目标切换时，拒绝执行移动
                        if not target_switching and (move_x_int != 0 or move_y_int != 0):
                            control.move(mouseMoveMode, move_x_int, move_y_int)
                    else:
                        # 当 should_move 为 False 时，重置last_offset_distance为 None,重置规律移动状态
                        # logger.debug("重置规律移动状态")
                        last_offset_distance = None
                        target_switching = False
    except KeyboardInterrupt:
        pass
    finally:
        box_shm.close()


def accessibility_process(accessibilityProcessSignal_queue, mouseMoveMode='win32', click_mode="连点",
                          automatic_trigger_switch=False, Trigger_conditions=False, Effective_mode="按下自瞄生效",
                          mouse_isdown=False, BoxConnect=False, emergenc_stop_switch=False, stop=False):  # 辅助功能进程
    # 按键状态记录
    last_state_w = False
    last_state_a = False
    last_state_s = False
    last_state_d = False


    while True:
        '''信号检查部分'''
        if not accessibilityProcessSignal_queue.empty():
            command_data = accessibilityProcessSignal_queue.get()
            logger.debug(f"accessibilityProcessSignal_queue 队列收到信号: {command_data}")
            if isinstance(command_data, tuple):
                cmd, cmd_01 = command_data
                if cmd == "click_mode":  # 点击模式：“连点” “单点” “长按”
                    click_mode = cmd_01
                    print(f"点击模式切换为: {click_mode}")
                elif cmd == "automatic_trigger_switch":
                    automatic_trigger_switch = cmd_01
                    print(f"自动扳机开关切换为: {automatic_trigger_switch}")
                elif cmd == "Trigger_conditions":
                    Trigger_conditions = cmd_01
                    print(f"扳机条件是否满足: {Trigger_conditions}")
                elif cmd == "mouseMoveMode":
                    mouseMoveMode = cmd_01
                    print(f"鼠标点击模块为: {mouseMoveMode}")
                elif cmd == "Effective_mode":
                    Effective_mode = cmd_01
                    print(f"生效模式为: {Effective_mode}")
                elif cmd == "emergenc_stop_switch":
                    emergenc_stop_switch = cmd_01

        if mouseMoveMode == "KmBoxNet" and not BoxConnect:
            IP = "192.168.2.188"
            PORT = "1244"
            MAC = "84FF7019"
            kmNet.init(IP, PORT, MAC)  # 连接盒子
            kmNet.enc_move(100, 100)  # 测试移动
            kmNet.monitor(8888)  # 开启物理键鼠监控功能。使用端口号8888接收物理键鼠数据
            BoxConnect = True

        if Effective_mode == "持续生效":
            mouse_isdown = True
        elif Effective_mode == "按下自瞄生效":
            mouse_isdown = control.monitor(mouseMoveMode)

        if automatic_trigger_switch and Trigger_conditions and mouse_isdown:  # 自动扳机
            if click_mode == "连点":
                control.click(mouseMoveMode)
                # print(mouseMoveMode)
            elif click_mode == "单击":
                pass
            elif click_mode == "长按":
                pass
        else:
            pass

        if emergenc_stop_switch:  # 急停
            # 调用 monitor_release，接收返回的状态
            last_state_w, last_state_a, last_state_s, last_state_d = control.emergencStop_valorant(
                last_state_w, last_state_a, last_state_s, last_state_d
            )


class RookieAiAPP:  # 主进程 (UI进程)
    """
    RookieAiAPP
    主进程中 初始化UI 进程。
    """

    def __init__(self):
        """初始化 UI"""
        self.information_output_queue = None
        self.floating_information_signal_queue = None
        self.video_queue = None
        self.processedVideo_queue = None
        self.YoloSignal_queue = None
        self.videoSignal_queue = None
        self.videoSignal_stop_queue = None
        self.pipe_child = None
        self.pipe_parent = None

        # 创建 QApplication 实例
        self.app = QtWidgets.QApplication(sys.argv)

        # 加载主窗口 UI 文件
        self.window = uic.loadUi(Root / "UI" / 'RookieAiWindow.ui')  # 请确保 Root 已正确定义
        self.window.setWindowTitle("YOLO识别系统")  # 设置窗口标题
        self.window.setWindowIcon(QIcon(str(Root / "ico" / "ultralytics-botAvatarSrcUrl-1729379860806.png")))  # 设置窗口图标
        self.window.setFixedSize(1290, 585)  # 固定窗口大小（可选）

        # TODO: 实例化设置窗口
        #self.automaticTriggerSetDialog = AutomaticTriggerSetDialog(self.window)
        #self.automaticTriggerSetDialog.setModal(True)  # 设置为模态窗口

        # 连接控制组件
        self.window.OpVideoButton.clicked.connect(
            self.toggle_video_button)  # 连接按钮点击信号到打开视频信号的槽

        # 连接 OpYoloButton 的点击信号到 toggle_YOLO_button 方法
        self.window.OpYoloButton.clicked.connect(self.toggle_YOLO_button)

        # 连接settingsButton按钮，显示设置按钮
        self.window.settingsYoloButton.clicked.connect(self.show_settings)
        self.window.closeYoloSettingsButton.clicked.connect(self.hide_settings)

        # 连接保存按钮
        self.window.saveButton.clicked.connect(self.save_settings)

        # 连接窗口置顶复选框状态改变信号
        self.window.topWindowCheckBox.stateChanged.connect(
            self.update_window_on_top_state)

        # 连接 解锁窗口大小 复选框状态改变信号
        self.window.unlockWindowSizeCheckBox.stateChanged.connect(
            self.update_unlock_window_size)

        # 连接 跳变抑制 复选框改变信号
        self.window.jumpSuppressionCheckBox.stateChanged.connect(self.update_jum_suppression_state)

        # 连接 自动扳机 复选框改变信号
        self.window.automatic_trigger_switchCheckBox.stateChanged.connect(self.update_automatic_trigger_state)

        # 连接 resetSizeButton 的点击信号到槽函数
        self.window.resetSizeButton.clicked.connect(self.reset_window_size)

        # 连接模型选择按钮
        self.window.chooseModelButton.clicked.connect(self.choose_model)

        # 连接重启按钮
        self.window.RestartButton.clicked.connect(self.restart_application)

        # 连接 重新加载模型 按钮 change_yolo_model
        self.window.reloadModelButton.clicked.connect(self.change_yolo_model)

        # 连接 automatic_trigger_switchToolButton 的点击信号到显示设置窗口的槽函数
        self.window.automatic_trigger_switchToolButton.clicked.connect(self.show_automatic_trigger_set_dialog)

        # 连接 自动扳机配置buttonClicked 信号
        self.automaticTriggerSetDialog.buttonGroup.buttonClicked.connect(self.on_button_clicked)

        # 连接 detectionTargetComboBox 的信号到槽函数
        self.window.detectionTargetComboBox.currentTextChanged.connect(
            self.on_detection_target_changed)

        # 连接 aimBotCheckBox 的状态变化信号
        self.window.aimBotCheckBox.stateChanged.connect(
            self.on_aimBotCheckBox_state_changed)

        # 连接 sideButtonCheckBox 的状态变化信号
        self.window.sideButtonCheckBox.stateChanged.connect(
            self.on_sideButtonCheckBox_state_changed)

        # 连接 mobileModeQComboBox 的信号槽函数(鼠标移动模式)
        self.window.mobileModeQComboBox.currentIndexChanged.connect(
            self.on_mobileMode_changed)

        # 连接 触发方式选择 conboBox
        self.window.triggerMethodComboBox.currentTextChanged.connect(
            self.on_trigger_method_changed)

        # 连接 热键选择 HotkeyPushButton
        self.window.HotkeyPushButton.clicked.connect(
            lambda: self.on_trigger_hotkey_changed(self.window.HotkeyPushButton.text()))

        self.window.announcement.setReadOnly(True)
        # 设置公告内容
        logger.debug("正在获取公告信息...")
        Module.announcement.get_announcement(self)

        '''参数框架切换 代码'''
        # 初始化动画列表和当前框架索引
        self.animations = []
        self.animation_group = QParallelAnimationGroup()
        self.current_frame_index = 1  # 初始显示中间的框架（索引为1）
        # 定义框架列表和索引映射
        self.frames = [
            self.window.advancedSettingsFrame,  # 索引0
            self.window.basicSettingsFrame,  # 索引1
            self.window.softwareInformationFrame  # 索引2
        ]
        # 设置每个框架的初始位置
        for i, frame in enumerate(self.frames):
            frame.move((i - self.current_frame_index)
                       * frame.width(), frame.y())
        # 连接按钮点击事件，并传递对应的目标框架索引
        self.window.advancedSettingsPushButton.clicked.connect(
            lambda: self.move_to_frame(0))
        self.window.basicSettingsPushButton.clicked.connect(
            lambda: self.move_to_frame(1))
        self.window.softwareInformationPushButton.clicked.connect(
            lambda: self.move_to_frame(2))
        # 连接动画组的 finished 信号
        self.animation_group.finished.connect(self.on_animation_finished)

        '''参数选项文字 动画'''
        # 连接按钮点击事件
        self.window.basicSettingsPushButton.clicked.connect(
            lambda: self.on_item_button_clicked("basic"))
        self.window.advancedSettingsPushButton.clicked.connect(
            lambda: self.on_item_button_clicked("advanced"))
        self.window.softwareInformationPushButton.clicked.connect(
            lambda: self.on_item_button_clicked("software"))
        # 保存按钮的默认 y 坐标
        self.button_default_y = 20  # 按钮的默认 y 坐标
        self.button_selected_y = 15  # 被选中按钮的 y 坐标（上移 5 像素）
        # 保存当前选中的按钮类型
        self.current_selected = None
        # 初始化动画列表
        self.item_animations = []
        # 初始化红线位置（假设初始选中 basicSettingsPushButton）
        self.on_item_button_clicked("basic")

        # 设置 YOLO置信度 滑动条
        self.window.confSlider.setMinimum(0)
        self.window.confSlider.setMaximum(100)

        # 连接滑动条信号
        self.window.confSlider.sliderPressed.connect(self.on_slider_pressed)
        self.window.confSlider.sliderMoved.connect(self.on_slider_moved)
        self.window.confSlider.sliderReleased.connect(self.on_slider_released)
        self.window.confSlider.valueChanged.connect(
            self.on_slider_value_changed)

        # 初始化滑动条发送定时器
        self.slider_update_timer = QTimer()
        self.slider_update_timer.setInterval(200)  # 设置200ms的间隔
        self.slider_update_timer.timeout.connect(self.send_update)

        # 初始化滑动条状态变量
        self.is_slider_pressed = False

        # 设置 lockspeedX 滑动条
        self.window.lockSpeedXHorizontalSlider.setMaximum(100)
        self.window.lockSpeedXHorizontalSlider.setMinimum(0)

        # 连接滑动条信号(lockspeedX)
        self.window.lockSpeedXHorizontalSlider.sliderPressed.connect(
            self.on_lockSpeedX_slider_pressed)
        self.window.lockSpeedXHorizontalSlider.sliderMoved.connect(
            self.on_lockSpeedX_slider_moved)
        self.window.lockSpeedXHorizontalSlider.sliderReleased.connect(
            self.on_lockSpeedX_slider_released)
        self.window.lockSpeedXHorizontalSlider.valueChanged.connect(
            self.on_lockSpeedX_slider_value_changed)

        # 初始化滑动条发送定时器(lockspeedX)
        self.slider_update_timer_lockSpeedX = QTimer()
        self.slider_update_timer_lockSpeedX.setInterval(200)  # 设置200ms的间隔
        self.slider_update_timer_lockSpeedX.timeout.connect(
            self.send_lockSpeedX_update)

        # 初始化滑动条状态变量(lockspeedX)
        self.is_slider_pressed_lockSpeedX = False

        # 设置 lockspeedY 滑动条
        self.window.lockSpeedYHorizontalSlider.setMaximum(100)
        self.window.lockSpeedYHorizontalSlider.setMinimum(0)

        # 连接滑动条信号(lockspeedY)
        self.window.lockSpeedYHorizontalSlider.sliderPressed.connect(
            self.on_lockSpeedY_slider_pressed)
        self.window.lockSpeedYHorizontalSlider.sliderMoved.connect(
            self.on_lockSpeedY_slider_moved)
        self.window.lockSpeedYHorizontalSlider.sliderReleased.connect(
            self.on_lockSpeedY_slider_released)
        self.window.lockSpeedYHorizontalSlider.valueChanged.connect(
            self.on_lockSpeedY_slider_value_changed)

        # 初始化滑动条发送定时器(lockspeedY)
        self.slider_update_timer_lockSpeedY = QTimer()
        self.slider_update_timer_lockSpeedY.setInterval(200)  # 设置200ms的间隔
        self.slider_update_timer_lockSpeedY.timeout.connect(
            self.send_lockSpeedY_update)

        # 初始化滑动条状态变量(lockspeedY)
        self.is_slider_pressed_lockSpeedY = False

        # 设置 jumpSuppression 滑动条
        self.window.jumpSuppressionVerticalSlider.setMaximum(50)
        self.window.jumpSuppressionVerticalSlider.setMinimum(0)

        # 连接滑动条信号(jumpSuppression)
        self.window.jumpSuppressionVerticalSlider.sliderPressed.connect(
            self.on_jumpSuppression_slider_pressed)
        self.window.jumpSuppressionVerticalSlider.sliderMoved.connect(
            self.on_jumpSuppression_slider_moved)
        self.window.jumpSuppressionVerticalSlider.sliderReleased.connect(
            self.on_jumpSuppression_slider_released)
        self.window.jumpSuppressionVerticalSlider.valueChanged.connect(
            self.on_jumpSuppression_slider_value_changed)

        # 初始化滑动条发送定时器(jumpSuppression)
        self.slider_update_timer_jumpSuppression = QTimer()
        self.slider_update_timer_jumpSuppression.setInterval(200)  # 设置200ms的间隔
        self.slider_update_timer_jumpSuppression.timeout.connect(
            self.send_jumpSuppression_update)

        # 初始化滑动条状态变量(jumpSuppression)
        self.is_slider_pressed_jumpSuppression = False

        # 初始化 aimRange 滑动条(aim_range)
        self.window.aimRangeHorizontalSlider.setMinimum(0)  # 滑块的实际范围是 0 到 280
        self.window.aimRangeHorizontalSlider.setMaximum(280)

        # 连接滑动条信号(aim_range)
        self.window.aimRangeHorizontalSlider.sliderPressed.connect(
            self.on_aimRange_slider_pressed)
        self.window.aimRangeHorizontalSlider.sliderMoved.connect(
            self.on_aimRange_slider_moved)
        self.window.aimRangeHorizontalSlider.sliderReleased.connect(
            self.on_aimRange_slider_released)
        self.window.aimRangeHorizontalSlider.valueChanged.connect(
            self.on_aimRange_slider_value_changed)

        # 初始化滑动条发送定时器(aim_range)
        self.aimRange_slider_update_timer = QTimer()
        self.aimRange_slider_update_timer.setInterval(200)  # 设置 200ms 的间隔
        self.aimRange_slider_update_timer.timeout.connect(
            self.send_aimRange_update)

        # 初始化滑动条状态变量(aim_range)
        self.is_aimRange_slider_pressed = False

        # 初始化 offset_centery 的定时器和标志位（offset_centery）
        self.offset_centery_slider_update_timer = QTimer()
        self.offset_centery_slider_update_timer.setInterval(200)  # 设置定时器间隔为200ms
        self.offset_centery_slider_update_timer.timeout.connect(self.send_offset_centery_update)
        self.is_offset_centery_slider_pressed = False  # 标志位，表示滑动条是否被按下
        # 初始化 offset_centery 值
        self.offset_centery = 0.0  # 根据需要设置初始值

        # 设置 offset_centeryVerticalSlider 滑动条（offset_centery）
        self.window.offset_centeryVerticalSlider.setMinimum(0)
        self.window.offset_centeryVerticalSlider.setMaximum(100)
        self.window.offset_centeryVerticalSlider.setSingleStep(1)
        self.window.offset_centeryVerticalSlider.setValue(
            int(self.offset_centery * 100))  # 初始化滑动条位置

        # 连接滑动条信号（offset_centery）
        self.window.offset_centeryVerticalSlider.sliderPressed.connect(
            self.on_offset_centery_slider_pressed)
        self.window.offset_centeryVerticalSlider.sliderMoved.connect(
            self.on_offset_centery_slider_moved)
        self.window.offset_centeryVerticalSlider.sliderReleased.connect(
            self.on_offset_centery_slider_released)
        self.window.offset_centeryVerticalSlider.valueChanged.connect(
            self.on_offset_centery_slider_value_changed)

        # 初始化 offset_centerx 的定时器和标志位（offset_centerx）
        self.offset_centerx_slider_update_timer = QTimer()
        self.offset_centerx_slider_update_timer.setInterval(200)  # 设置定时器间隔为200ms
        self.offset_centerx_slider_update_timer.timeout.connect(self.send_offset_centerx_update)
        self.is_offset_centerx_slider_pressed = False  # 标志位，表示滑动条是否被按下
        # 初始化 offset_centerx 值
        self.offset_centerx = 0.0  # 根据需要设置初始值

        # 设置 offset_centerxVerticalSlider 滑动条（offset_centerx）
        self.window.offset_centerxVerticalSlider.setMinimum(0)
        self.window.offset_centerxVerticalSlider.setMaximum(100)
        self.window.offset_centerxVerticalSlider.setSingleStep(1)
        self.window.offset_centerxVerticalSlider.setValue(
            int(self.offset_centerx * 100))  # 初始化滑动条位置

        # 连接滑动条信号（offset_centerx）
        self.window.offset_centerxVerticalSlider.sliderPressed.connect(
            self.on_offset_centerx_slider_pressed)
        self.window.offset_centerxVerticalSlider.sliderMoved.connect(
            self.on_offset_centerx_slider_moved)
        self.window.offset_centerxVerticalSlider.sliderReleased.connect(
            self.on_offset_centerx_slider_released)
        self.window.offset_centerxVerticalSlider.valueChanged.connect(
            self.on_offset_centerx_slider_value_changed)

        # 初始化 aimRange 滑动条(autoTiggerRangeSlider)
        self.automaticTriggerSetDialog.autoTiggerRangeSlider.setMinimum(0)  # 滑块的实际范围是 0 到 280
        self.automaticTriggerSetDialog.autoTiggerRangeSlider.setMaximum(1)

        # 连接滑动条信号(autoTiggerRangeSlider)
        self.automaticTriggerSetDialog.autoTiggerRangeSlider.sliderPressed.connect(
            self.on_autoTiggerRangeSlider_pressed)
        self.automaticTriggerSetDialog.autoTiggerRangeSlider.sliderMoved.connect(
            self.on_autoTiggerRangeSlider_moved)
        self.automaticTriggerSetDialog.autoTiggerRangeSlider.sliderReleased.connect(
            self.on_autoTiggerRangeSlider_released)
        self.automaticTriggerSetDialog.autoTiggerRangeSlider.valueChanged.connect(
            self.on_autoTiggerRangeSlider_value_changed)

        # 初始化滑动条发送定时器(autoTiggerRangeSlider)
        self.autoTiggerRangeSlider_update_timer = QTimer()
        self.autoTiggerRangeSlider_update_timer.setInterval(200)  # 设置定时器间隔为200ms
        self.autoTiggerRangeSlider_update_timer.timeout.connect(self.send_autoTiggerRangeSlider_update)

        # 初始化滑动条状态变量(autoTiggerRangeSlider)
        self.is_autoTiggerRangeSlider_slider_pressed = False  # 标志位，表示滑动条是否被按下
        # 初始化 autoTiggerRangeSlider 值
        self.autoTiggerRange = 0.5  # 根据需要设置初始值

        # 设置 autoTiggerRangeSlider 滑动条（autoTiggerRangeSlider）
        self.automaticTriggerSetDialog.autoTiggerRangeSlider.setMinimum(0)
        self.automaticTriggerSetDialog.autoTiggerRangeSlider.setMaximum(100)
        self.automaticTriggerSetDialog.autoTiggerRangeSlider.setSingleStep(1)
        self.automaticTriggerSetDialog.autoTiggerRangeSlider.setValue(
            int(self.autoTiggerRange * 100))  # 初始化滑动条位置


        # 初始化遮罩透明度效果
        self.window.overlay_opacity = QGraphicsOpacityEffect(
            self.window.overlay)
        self.window.overlay.setGraphicsEffect(self.window.overlay_opacity)
        self.window.overlay_animation = QPropertyAnimation(
            self.window.overlay_opacity, b"opacity")

        # 初始隐藏设置面板，并将其移动到屏幕左侧外
        self.window.settingsPanel.hide()
        self.window.settingsPanel.move(-self.window.settingsPanel.width(),
                                       self.window.settingsPanel.y())
        self.window.overlay.hide()
        self.window.overlay.setGeometry(
            0, 0, self.window.width(), self.window.height())

        # 初始化 AnimatedStatus，将 TestUI 实例作为窗口参数传递，指定Widget和Label名称
        self.window.status_widget = AnimatedStatus(window=self.window,
                                                   widget_name="statusDisplayWidget",
                                                   label_name="statusDisplayLabel")

        # 初始化视频状态
        self.is_video_running = False
        self.update_button_text()

        # 初始化 视频显示画面更新 定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_video_frame)  # 每次超时调用更新函数
        self.timer.start(5)  # 约每30毫秒更新一次

        # 初始化 帧 计数
        self.fps = 0
        self.frame_count = 0
        self.start_time = time.time()
        self.fps_update_interval = 0.5  # 设置FPS更新间隔（秒）

        # 初始化 YOLO 处理状态
        self.is_yolo_running = False

        # 初始化视频状态
        self.video_running = False

        # 创建并应用遮罩到 show_video
        self.apply_rounded_mask_to_show_video()

    def show_automatic_trigger_set_dialog(self):
        """显示自动扳机设置窗口（模态）"""
        self.automaticTriggerSetDialog.exec()

    def hide_automatic_trigger_set_window(self):
        """隐藏自动扳机设置窗口"""
        self.automaticTriggerSetDialog.hide()

    def on_button_clicked(self, button):
        # 获取被点击的按钮文本并打印
        Effective_mode = button.text()
        print(f"选中的按钮文本是: {Effective_mode}")
        self.accessibilityProcessSignal_queue.put(("Effective_mode", Effective_mode))

    def on_mobileMode_changed(self, selected_mobileMode):
        """
        鼠标移动方式库选择
        当 mobileModeQComboBox 改变时调用。
        :param selected_mobileMode: 鼠标移动模式(0 = win32, 1 = 飞易来, 2 = KmBoxNet)
        """
        # 对照字典
        mobile_mode_dict = {
            0: "win32",
            1: "飞易来",
            2: "KmBoxNet"
        }

        # 根据 selected_mobileMode 获取对应的鼠标移动方式
        selected_mode_name = mobile_mode_dict.get(selected_mobileMode, "未知模式")
        logger.debug(f"选择的鼠标移动方式: {selected_mode_name}")

        # 发送鼠标移动方式切换的信号
        self.mouseMoveProssesSignal_queue.put(("mouseMoveMode", selected_mode_name))
        self.accessibilityProcessSignal_queue.put(("mouseMoveMode", selected_mode_name))

    def on_trigger_method_changed(self, selected_method):
        """
        当 triggerMethodComboBox 的选中值发生变化时调用
        """
        # 选项到触发模式的映射
        method_to_mode = method_mode

        # 获取对应的触发模式
        trigger_mode = method_to_mode.get(
            selected_method, "press")  # 默认值为 "press"

        # 向队列发送触发模式更新信号
        self.mouseMoveProssesSignal_queue.put(
            ("trigger_mode_change", trigger_mode))
        logger.debug(f"触发模式切换为: {trigger_mode}")

    def on_trigger_hotkey_changed(self, text):
        """当 LableButton 被点击时调用"""

        # 获取键代码
        lockKey = keyboard.get_keyboard_event(text)
        lockKey_name = keyboard.get_key_name_vk(lockKey)
        if lockKey != "UNKNOWN":
            # 更新鼠标相关的按键
            self.lockKey = lockKey
            self.window.HotkeyPushButton.setText(lockKey_name)
            # 发送信息到 mouseMoveProssesSignal_queue
            self.mouseMoveProssesSignal_queue.put(("lock_key_change", lockKey))
            logger.debug(f"触发按键已更改为: {lockKey_name} (代码: {lockKey})")

    def on_sideButtonCheckBox_state_changed(self, state):
        # 判断复选框是否被选中
        is_checked = (state == 2)  # 检查是否是 PartiallyChecked 或 Checked
        if state == 0:
            is_checked = False  # 如果是 Unchecked，则为 False
        elif state == 1:
            is_checked = True  # 如果是 Checked，则为 True

        # 发送信号到 mouseMoveProssesSignal_queue
        self.mouseMoveProssesSignal_queue.put(
            ("mouse_Side_Button_Witch_change", is_checked))
        logger.debug(f"sideButtonCheckBox 状态变化: {is_checked}")

    def on_aimBotCheckBox_state_changed(self, state):
        """处理 aimBotCheckBox 状态变化的槽函数。"""
        # 判断复选框是否被选中
        is_checked = (state == 2)  # 检查是否是 PartiallyChecked 或 Checked
        if state == 0:
            is_checked = False  # 如果是 Unchecked，则为 False
        elif state == 1:
            is_checked = True  # 如果是 Checked，则为 True

        # 发送信号到 mouseMoveProssesSignal_queue
        self.mouseMoveProssesSignal_queue.put(
            ("aimbot_switch_change", is_checked))
        logger.debug(f"aimBotCheckBox 状态变化: {is_checked}")

    def on_detection_target_changed(self, selected_class):
        """
        当 detectionTargetComboBox 的选项改变时调用。

        参数:
        - selected_class: 选中的类别 (0, 1, 2, 或 "ALL")
        """
        logger.debug(f"选择的检测类别: {selected_class}")
        self.information_output_queue.put(
            ("UI_process_log", f"选择的检测类别: {selected_class}"))

        # 发送类别更改信号到 YOLO 处理进程
        self.YoloSignal_queue.put(("change_class", selected_class))

    """瞄准偏移X滑动条"""

    def on_offset_centerx_slider_value_changed(self, value):
        """当滑动条的值改变时调用"""
        value = 1 - (value / 50.0)  # 将滑动条值从 0-100 映射到 1 到 -1
        self.window.offset_centerxNumber.display(f"{value:.2f}")  # 更新显示，保留两位小数
        self.offset_centerx = value  # 更新 offset_centerx 值
        # 如果定时器未启动，启动定时器
        if not self.offset_centerx_slider_update_timer.isActive():
            self.offset_centerx_slider_update_timer.start()

    def on_offset_centerx_slider_pressed(self):
        """当用户开始拖动滑动条时调用"""
        self.is_offset_centerx_slider_pressed = True
        self.offset_centerx_slider_update_timer.start()  # 开始定时器

    def on_offset_centerx_slider_moved(self, value):
        """当滑动条被拖动时调用"""
        value = 1 - (value / 50.0)  # 将滑动条值从 0-100 映射到 1 到 -1
        self.window.offset_centerxNumber.display(f"{value:.2f}")  # 实时更新显示
        self.offset_centerx = value  # 更新 offset_centerx 值

    def on_offset_centerx_slider_released(self):
        """当用户释放滑动条时调用"""
        self.is_offset_centerx_slider_pressed = False
        # 定时器将在发送最后一次值后停止

    def send_offset_centerx_update(self):
        """每200ms发送一次最新的 offset_centerx 值"""
        self.mouseMoveProssesSignal_queue.put(
            ("offset_centerx_change", self.offset_centerx))
        logger.debug(f"定时发送 offset_centerx 更新信号: {self.offset_centerx}")
        if not self.is_offset_centerx_slider_pressed:
            # 用户已停止拖动滑动条，停止定时器
            self.offset_centerx_slider_update_timer.stop()

    """瞄准偏移Y滑动条"""

    def on_offset_centery_slider_value_changed(self, value):
        """当滑动条的值改变时调用"""
        value = value / 100.0  # 将值转换为 0 到 1 的浮点数
        self.window.offset_centeryNumber.display(f"{value:.2f}")  # 更新显示，保留两位小数
        self.offset_centery = value  # 更新 offset_centery 值

        # 如果定时器未启动，启动定时器
        if not self.offset_centery_slider_update_timer.isActive():
            self.offset_centery_slider_update_timer.start()

    def on_offset_centery_slider_pressed(self):
        """当用户开始拖动滑动条时调用"""
        self.is_offset_centery_slider_pressed = True
        self.offset_centery_slider_update_timer.start()  # 开始定时器

    def on_offset_centery_slider_moved(self, value):
        """当滑动条被拖动时调用"""
        value = value / 100.0
        self.window.offset_centeryNumber.display(f"{value:.2f}")  # 实时更新显示
        self.offset_centery = value  # 更新 offset_centery 值

    def on_offset_centery_slider_released(self):
        """当用户释放滑动条时调用"""
        self.is_offset_centery_slider_pressed = False
        # 定时器将在发送最后一次值后停止

    def send_offset_centery_update(self):
        """每200ms发送一次最新的 offset_centery 值"""
        self.mouseMoveProssesSignal_queue.put(
            ("offset_centery_change", self.offset_centery))
        logger.debug(f"定时发送 offset_centery 更新信号: {self.offset_centery}")
        if not self.is_offset_centery_slider_pressed:
            # 用户已停止拖动滑动条，停止定时器
            self.offset_centery_slider_update_timer.stop()

    """自动扳机范围比例"""
    def on_autoTiggerRangeSlider_value_changed(self, value):
        """当 autoTiggerRang 滑动条的值改变时调用"""
        value = value / 100
        self.automaticTriggerSetDialog.autoTiggerRangeNumber.display(f"{value:.2f}")
        self.autoTiggerRange = value  # 更新 aimRange 值
        # 如果定时器未启动，启动定时器
        if not self.autoTiggerRangeSlider_update_timer.isActive():
            self.autoTiggerRangeSlider_update_timer.start()

    def on_autoTiggerRangeSlider_pressed(self):
        """当用户开始拖动 autoTiggerRang 滑动条时调用"""
        self.is_autoTiggerRangeSlider_slider_pressed = True
        self.autoTiggerRangeSlider_update_timer.start()  # 开始定时器

    def on_autoTiggerRangeSlider_moved(self, value):
        """当 autoTiggerRang 滑动条被拖动时调用"""
        value = value / 100.0
        self.automaticTriggerSetDialog.autoTiggerRangeNumber.display(f"{value:.2f}")  # 实时更新显示
        self.autoTiggerRange = value  # 更新 offset_centery 值

    def on_autoTiggerRangeSlider_released(self):
        """当用户释放 autoTiggerRang 滑动条时调用"""
        self.is_autoTiggerRangeSlider_slider_pressed = False
        # 定时器将在发送最后一次值后停止

    def send_autoTiggerRangeSlider_update(self):
        """每 200ms 发送一次最新的 autoTiggerRang 值"""
        self.mouseMoveProssesSignal_queue.put(
            ("automatic_trigger_range_switching", self.autoTiggerRange))
        self.YoloSignal_queue.put(("autoTiggerRange_change", self.autoTiggerRange))
        logger.debug(f"定时发送 autoTiggerRange 更新信号: {self.autoTiggerRange}")
        if not self.is_autoTiggerRangeSlider_slider_pressed:
            # 用户已停止拖动滑动条，停止定时器
            self.autoTiggerRangeSlider_update_timer.stop()

    '''瞄准范围 滑动条'''

    def on_aimRange_slider_value_changed(self, value):
        """当 aimRange 滑动条的值改变时调用"""
        # 将滑块的值映射到 20-300 范围
        mapped_value = value
        self.window.aimRangeLcdNumber.display(mapped_value)
        self.aim_range = mapped_value  # 更新 aimRange 值
        # 如果定时器未启动，启动定时器
        if not self.aimRange_slider_update_timer.isActive():
            self.aimRange_slider_update_timer.start()

    def on_aimRange_slider_pressed(self):
        """当用户开始拖动 aimRange 滑动条时调用"""
        self.is_aimRange_slider_pressed = True
        self.aimRange_slider_update_timer.start()  # 开始定时器

    def on_aimRange_slider_moved(self, value):
        """当 aimRange 滑动条被拖动时调用"""
        # 将滑块的值映射到 20-300 范围
        mapped_value = 20 + value
        self.window.aimRangeLcdNumber.display(mapped_value)
        self.aim_range = mapped_value  # 更新 aimRange 值

    def on_aimRange_slider_released(self):
        """当用户释放 aimRange 滑动条时调用"""
        self.is_aimRange_slider_pressed = False
        # 定时器将在发送最后一次值后停止

    def send_aimRange_update(self):
        """每 200ms 发送一次最新的 aimRange 值"""
        self.mouseMoveProssesSignal_queue.put(
            ("aim_range_change", self.aim_range))
        self.YoloSignal_queue.put(("aim_range_change", self.aim_range))
        logger.debug(f"定时发送 aimRange 更新信号: {self.aim_range}")
        if not self.is_aimRange_slider_pressed:
            # 用户已停止拖动滑动条，停止定时器
            self.aimRange_slider_update_timer.stop()

    '''lockSpeed_x 滑动条'''

    def on_lockSpeedX_slider_value_changed(self, value):
        """当 lockSpeed_x 滑动条的值改变时调用"""
        value = value / 10  # 将值缩放到 [0, 10] 范围
        self.window.lockSpeedXLcdNumber.display(
            f"{value:.1f}")  # 在 LCD 上显示一位小数的值
        self.lock_speed_x = value  # 更新锁定速度
        # 如果定时器未启动，启动定时器
        if not self.slider_update_timer_lockSpeedX.isActive():
            self.slider_update_timer_lockSpeedX.start()

    def on_lockSpeedX_slider_pressed(self):
        """当用户开始拖动 lockSpeed_x 滑动条时调用"""
        self.is_slider_pressed_lockSpeedX = True
        self.slider_update_timer_lockSpeedX.start()  # 开始定时器

    def on_lockSpeedX_slider_moved(self, value):
        """当 lockSpeed 滑动条被拖动时调用"""
        value = value / 10  # 将值缩放到 [0, 10] 范围
        self.window.lockSpeedXLcdNumber.display(
            f"滑动条的值: {value:.1f}")  # 在 LCD 上显示实时的值
        self.lock_speed_x = value  # 更新锁定速度

    def on_lockSpeedX_slider_released(self):
        """当用户释放 lockSpeed 滑动条时调用"""
        self.is_slider_pressed_lockSpeedX = False
        # 定时器将在发送最后一次值后停止
        self.send_lockSpeedX_update()

    def send_lockSpeedX_update(self):
        """每200ms发送一次最新的 lockSpeed 值"""
        self.mouseMoveProssesSignal_queue.put(
            ("aim_speed_x_change", self.lock_speed_x))  # 发送锁定速度到队列
        logger.debug(f"定时发送锁定速度更新信号: {self.lock_speed_x}")
        if not self.is_slider_pressed_lockSpeedX:
            # 用户已停止拖动滑动条，停止定时器
            self.slider_update_timer_lockSpeedX.stop()

    '''lockSpeed_y 滑动条'''

    def on_lockSpeedY_slider_value_changed(self, value):
        """当 lockSpeed_y 滑动条的值改变时调用"""
        value = value / 10  # 将值缩放到 [0, 10] 范围
        self.window.lockSpeedYLcdNumber.display(
            f"{value:.1f}")  # 在 LCD 上显示一位小数的值
        self.lock_speed_y = value  # 更新锁定速度
        # 如果定时器未启动，启动定时器
        if not self.slider_update_timer_lockSpeedY.isActive():
            self.slider_update_timer_lockSpeedY.start()

    def on_lockSpeedY_slider_pressed(self):
        """当用户开始拖动 lockSpeed_y 滑动条时调用"""
        self.is_slider_pressed_lockSpeedY = True
        self.slider_update_timer_lockSpeedY.start()  # 开始定时器

    def on_lockSpeedY_slider_moved(self, value):
        """当 lockSpeed 滑动条被拖动时调用"""
        value = value / 10  # 将值缩放到 [0, 10] 范围
        self.window.lockSpeedYLcdNumber.display(
            f"滑动条的值: {value:.1f}")  # 在 LCD 上显示实时的值
        self.lock_speed_y = value  # 更新锁定速度

    def on_lockSpeedY_slider_released(self):
        """当用户释放 lockSpeed 滑动条时调用"""
        self.is_slider_pressed_lockSpeedY = False
        # 定时器将在发送最后一次值后停止
        self.send_lockSpeedY_update()

    def send_lockSpeedY_update(self):
        """每200ms发送一次最新的 lockSpeed 值"""
        self.mouseMoveProssesSignal_queue.put(
            ("aim_speed_y_change", self.lock_speed_y))  # 发送锁定速度到队列
        logger.debug(f"定时发送锁定速度更新信号: {self.lock_speed_y}")
        if not self.is_slider_pressed_lockSpeedY:
            # 用户已停止拖动滑动条，停止定时器
            self.slider_update_timer_lockSpeedY.stop()

    '''jumpSuppression 滑动条'''

    def on_jumpSuppression_slider_value_changed(self, value):
        """当 jumpSuppression 滑动条的值改变时调用"""
        self.window.jumpSuppressionNumber.display(
            f"{value}")  # 在 LCD 上显示一位小数的值
        self.jump_suppression_fluctuation_range = value  # 更新锁定速度
        # 如果定时器未启动，启动定时器
        if not self.slider_update_timer_jumpSuppression.isActive():
            self.slider_update_timer_jumpSuppression.start()

    def on_jumpSuppression_slider_pressed(self):
        """当用户开始拖动 jumpSuppression 滑动条时调用"""
        self.is_slider_pressed_jumpSuppression = True
        self.slider_update_timer_jumpSuppression.start()  # 开始定时器

    def on_jumpSuppression_slider_moved(self, value):
        """当 jumpSuppression 滑动条被拖动时调用"""
        self.window.jumpSuppressionNumber.display(
            f"滑动条的值: {value}")  # 在 LCD 上显示实时的值
        self.jump_suppression_fluctuation_range = value  # 更新锁定速度

    def on_jumpSuppression_slider_released(self):
        """当用户释放 jumpSuppression 滑动条时调用"""
        self.is_slider_pressed_jumpSuppression = False
        # 定时器将在发送最后一次值后停止
        self.send_jumpSuppression_update()

    def send_jumpSuppression_update(self):
        """每200ms发送一次最新的 jumpSuppression 值"""
        self.mouseMoveProssesSignal_queue.put(
            ("jump_suppression_fluctuation_range", self.jump_suppression_fluctuation_range))  # 发送锁定速度到队列
        logger.debug(f"定时发送跳变误差更新信号: {self.jump_suppression_fluctuation_range}")
        if not self.is_slider_pressed_jumpSuppression:
            # 用户已停止拖动滑动条，停止定时器
            self.slider_update_timer_jumpSuppression.stop()

    '''置信度滑动条'''

    def on_slider_value_changed(self, value):
        """当滑动条的值改变时调用"""
        value = value / 100
        self.window.confNumber.display(f"{value:.2f}")
        self.yolo_confidence = value  # 更新置信度值

        # 如果定时器未启动，启动定时器
        if not self.slider_update_timer.isActive():
            self.slider_update_timer.start()

    def on_slider_pressed(self):
        """当用户开始拖动滑动条时调用"""
        self.is_slider_pressed = True
        self.slider_update_timer.start()  # 开始定时器

    def on_slider_moved(self, value):
        """当滑动条被拖动时调用"""
        value = value / 100
        self.window.confNumber.display(f"滑动条的值: {value:.2f}")
        self.yolo_confidence = value  # 更新置信度值

    def on_slider_released(self):
        """当用户释放滑动条时调用"""
        self.is_slider_pressed = False
        # 定时器将在发送最后一次值后停止

    def send_update(self):
        """每200ms发送一次最新的置信度值"""
        self.YoloSignal_queue.put(("change_conf", self.yolo_confidence))
        logger.debug(f"定时发送 YOLO 置信度更新信号: {self.yolo_confidence}")

        if not self.is_slider_pressed:
            # 用户已停止拖动滑动条，停止定时器
            self.slider_update_timer.stop()

    def restart_application(self):
        """重启当前应用程序。"""
        # 显示警告对话框
        reply = QMessageBox.warning(
            self.window,
            "确认重启",
            "软件即将重启，未保存的参数将丢失，是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # 用户选择了“是”，执行重启
            # 首先，清理资源并停止子进程
            self.clean_up()
            # 使用 os.execl 重启应用程序
            python = sys.executable
            os.execl(python, python, *sys.argv)

    def clean_up(self):
        """终止子进程并清理资源。"""
        # 终止进程
        if hasattr(self, 'process_signal_processing'):
            self.process_signal_processing.terminate()
            self.process_signal_processing.join()
        if hasattr(self, 'process_video_signal'):
            self.process_video_signal.terminate()
            self.process_video_signal.join()
        if hasattr(self, 'process_videoprocessing'):
            self.process_videoprocessing.terminate()
            self.process_videoprocessing.join()
        # 关闭共享内存
        if hasattr(self, 'shm_video'):
            self.shm_video.close()
            self.shm_video.unlink()
        # 关闭应用程序
        self.app.quit()

    def req_config(self):
        """单进程推理模式 手动请求推理参数(补丁)"""
        # 获取当前 detectionTargetComboBox 的选项
        current_target_class = self.window.detectionTargetComboBox.currentText()
        self.YoloSignal_queue.put(
            ("change_class", current_target_class))  # 检测目标
        self.YoloSignal_queue.put(("change_conf", self.yolo_confidence))  # 置信度
        self.YoloSignal_queue.put(("aim_range_change", self.aim_range))  # 瞄准范围

    def load_settings(self):
        """加载配置文件 settings.json"""
        try:
            self._extracted_from_load_settings_4()
        except Exception as e:
            logger.warn("配置文件读取失败:", e)
            self.information_output_queue.put(
                ("UI_process_log", f"配置文件读取失败: {e}"))
            self.settings = Config
            self.ProcessMode = "single_process"  # 设置默认值

    # TODO Rename this here and in `load_settings`
    def _extracted_from_load_settings_4(self):
        self.settings = Config
        logger.info("配置文件读取成功")
        self.information_output_queue.put(("UI_process_log", "配置文件读取成功"))

        '''读取参数'''
        # 获取 "ProcessMode" 的状态
        self.ProcessMode = self.settings.get("ProcessMode", "single_process")
        logger.debug("ProcessMode状态:", self.ProcessMode)
        self.allow_network = self.settings.get("allow_network", False)
        logger.debug("是否允许联网:", self.allow_network)
        self.information_output_queue.put(
            ("UI_process_log", f"ProcessMode状态: {self.ProcessMode}"))
        # 获取 "window_always_on_top" 的状态
        self.window_always_on_top = self.settings.get(
            "window_always_on_top", False)
        logger.debug("窗口置顶状态:", self.window_always_on_top)
        # 获取 "model_file" 模型文件的路径
        self.model_file = self.settings.get("model_file", "yolov8n.pt")
        logger.debug(f"读取模型文件路径: {self.model_file}")
        # 获取 YOLO 置信度设置
        yolo_confidence = self.settings.get('confidence', 0.5)  # 默认值为0.5
        self.yolo_confidence = yolo_confidence
        self.window.confSlider.setValue(
            int(yolo_confidence * 100))  # 将置信度转换为滑动条值
        logger.debug(f"读取保存的YOLO置信度: {yolo_confidence}")
        # 获取 瞄准速度x
        aim_speed_x = self.settings.get('aim_speed_x', 0.5)
        self.aim_speed_x = aim_speed_x
        self.window.lockSpeedXHorizontalSlider.setValue(int(aim_speed_x * 10))
        logger.debug(f"读取保存的瞄准速度X: {aim_speed_x}")
        # 获取 瞄准速度y
        aim_speed_y = self.settings.get('aim_speed_y', 0.5)
        self.aim_speed_y = aim_speed_y
        self.window.lockSpeedYHorizontalSlider.setValue(int(aim_speed_y * 10))
        logger.debug(f"读取保存的瞄准速度Y: {aim_speed_y}")
        # 获取 瞄准范围
        aim_range = self.settings.get('aim_range', 100)
        self.aim_range = aim_range
        self.window.aimRangeHorizontalSlider.setValue(int(aim_range))
        logger.debug(f"读取保存的瞄准范围: {aim_range}")
        # 获取 Aimbot 开启状态
        aimbot_switch = self.settings.get("aimBot", False)
        self.window.aimBotCheckBox.setChecked(aimbot_switch)
        self.mouseMoveProssesSignal_queue.put(
            ("aimbot_switch_change", aimbot_switch))
        logger.debug(f"读取自瞄状态: {aimbot_switch}")
        # 获取 侧键瞄准 开启状态
        mouse_Side_Button_Witch = self.settings.get(
            "mouse_Side_Button_Witch", False)
        self.window.sideButtonCheckBox.setChecked(mouse_Side_Button_Witch)
        self.mouseMoveProssesSignal_queue.put(
            ("mouse_Side_Button_Witch_change", mouse_Side_Button_Witch))
        logger.debug(f"读取侧键瞄准开启状态: {mouse_Side_Button_Witch}")
        # 获取 detectionTargetComboBox 的值
        target_class = self.settings.get('target_class', "ALL")
        logger.debug(f"读取保存的检测类别: {target_class}")
        self.window.detectionTargetComboBox.setCurrentText(target_class)
        self.YoloSignal_queue.put(("change_class", target_class))
        # 获取 Y轴偏移 值
        offset_centery = self.settings.get('offset_centery', 0.3)
        logger.debug(f"读取保存的Y轴偏移: {offset_centery}")
        self.offset_centery = offset_centery
        self.window.offset_centeryVerticalSlider.setValue(
            int(offset_centery * 100))
        # 获取 Y轴偏移 值
        offset_centerx = self.settings.get('offset_centerx', 0)
        logger.debug(f"读取保存的X轴偏移: {offset_centerx}")
        self.offset_centerx = offset_centerx
        # 映射公式：slider_value = (1 - offset_centerx) * 50
        slider_value = int((1 - offset_centerx) * 50)
        self.window.offset_centerxVerticalSlider.setValue(slider_value)
        # 获取 触发热键代码 值
        lockKey = self.settings.get('lockKey', "VK_LBUTTON")
        logger.debug(f"读取保存的触发热键: {lockKey}")
        self.window.HotkeyPushButton.setText(lockKey)
        key_code = keyboard.get_key_code_vk(lockKey)
        logger.debug(f"加载触发热键代码: {key_code}")
        self.mouseMoveProssesSignal_queue.put(("lock_key_change", key_code))
        # 获取 触发方式
        triggerType = (self.settings.get('triggerType', "press"))
        logger.debug(f"读取保存的触发方式: {triggerType}")
        self.window.triggerMethodComboBox.setCurrentText(triggerType)
        # 获取 游戏内X轴360度视角像素
        screen_pixels_for_360_degrees = self.settings.get(
            'screen_pixels_for_360_degrees', 1800)
        logger.debug(f"读取游戏内一周像素: {screen_pixels_for_360_degrees}")
        self.mouseMoveProssesSignal_queue.put(
            ("screen_pixels_for_360_degrees", screen_pixels_for_360_degrees))
        # 获取 游戏内Y轴180度视角像素
        screen_height_pixels = self.settings.get('screen_height_pixels', 900)
        logger.debug(f"读取游戏内一周像素: {screen_height_pixels}")
        self.mouseMoveProssesSignal_queue.put(
            ("screen_height_pixels", screen_height_pixels))
        # 获取 近点瞄准速率倍率
        near_speed_multiplier = self.settings.get('near_speed_multiplier', 2)
        logger.debug(f"读取近点瞄准速率倍率: {near_speed_multiplier}")
        self.mouseMoveProssesSignal_queue.put(
            ("near_speed_multiplier", near_speed_multiplier))
        # 获取 瞄准减速区域
        slow_zone_radius = self.settings.get("slow_zone_radius", 10)
        logger.debug(f"读取瞄准减速区域: {slow_zone_radius}")
        self.mouseMoveProssesSignal_queue.put(
            ("slow_zone_radius", slow_zone_radius))
        # 获取 跳变抑制开关
        jump_suppression_switch = self.settings.get("jump_suppression_switch", False)
        logger.debug(f"跳变抑制开关: {jump_suppression_switch}")
        self.window.jumpSuppressionCheckBox.setChecked(jump_suppression_switch)
        self.mouseMoveProssesSignal_queue.put(("jump_detection_switch", jump_suppression_switch))
        # 获取 跳变抑制误差
        jump_suppression_fluctuation_range = self.settings.get("jump_suppression_fluctuation_range", 10)
        logger.debug(f"跳变抑制误差: {jump_suppression_fluctuation_range}")
        self.window.jumpSuppressionVerticalSlider.setValue(jump_suppression_fluctuation_range)
        self.mouseMoveProssesSignal_queue.put(
            ("jump_suppression_fluctuation_range", jump_suppression_fluctuation_range))

    def save_settings(self):
        """保存当前设置到 settings.json 文件"""
        '''获取值'''
        # 获取当前 ProcessModeComboBox 的选项
        current_process_mode = self.choose_process_model_comboBox()
        # 获取当前 topWindowCheckBox 的状态
        current_window_on_top = self.window.topWindowCheckBox.isChecked()
        # 获取当前 jumpSuppressionCheckBox 的状态
        jump_suppression_switch = self.window.jumpSuppressionCheckBox.isChecked()
        # 获取当前 detectionTargetComboBox 的选项
        current_target_class = self.window.detectionTargetComboBox.currentText()
        # 获取当前 aimBotCheckBox 的选项
        aimbot_switch = self.window.aimBotCheckBox.isChecked()
        # 获取当前 sideButtonCheckBox 的选项
        mouse_Side_Button_Witch = self.window.sideButtonCheckBox.isChecked()
        # 获取当前 HotkeyName PushButton 的文字
        lockKey = self.window.HotkeyPushButton.text()
        # 获取当前 triggerMethodComboBox 的选项
        triggerType = self.window.triggerMethodComboBox.currentText()

        '''保存参数'''
        # 更新 settings 字典
        # 推理模式
        self.settings['ProcessMode'] = current_process_mode
        # 窗口置顶状态
        self.settings['window_always_on_top'] = current_window_on_top
        # 自瞄开启状态
        self.settings['aimBot'] = aimbot_switch
        # 侧键瞄准开启状态
        self.settings['mouse_Side_Button_Witch'] = mouse_Side_Button_Witch
        # 模型文件路径
        self.settings['model_file'] = self.model_file
        # 置信度
        self.settings['confidence'] = self.yolo_confidence
        # 锁定速度x
        self.settings['aim_speed_x'] = self.lock_speed_x
        # 锁定速度y
        self.settings['aim_speed_y'] = self.lock_speed_y
        # 瞄准范围
        self.settings['aim_range'] = self.aim_range
        # 目标代码
        self.settings['target_class'] = current_target_class
        # Y轴瞄准偏移
        self.settings['offset_centery'] = self.offset_centery
        # X轴瞄准偏移
        self.settings['offset_centerx'] = self.offset_centerx
        # 触发热键
        self.settings['lockKey'] = lockKey
        # 触发方式
        self.settings['triggerType'] = triggerType
        # 跳变抑制开关
        self.settings['jump_suppression_switch'] = jump_suppression_switch
        # 跳变抑制误差
        self.settings['jump_suppression_fluctuation_range'] = self.jump_suppression_fluctuation_range

        # 将 settings 保存到文件
        try:
            Config.save()
            logger.info("配置文件保存成功")
            self.information_output_queue.put(("UI_process_log", "配置文件保存成功"))
            self.window.status_widget.display_message("配置已保存", bg_color="#55ff00", text_color="black",
                                                      auto_hide=3000)
        except Exception as e:
            logger.error("配置文件保存失败:", e)
            self.information_output_queue.put(
                ("UI_process_log", f"配置文件保存失败: {e}"))
            self.window.status_widget.display_message("配置保存失败", bg_color="Red", text_color="white",
                                                      auto_hide=3000)

    def init_ui_from_settings(self):
        """根据配置文件初始化界面"""
        # 设置 ProcessModeComboBox 的当前选项
        if (
                self.ProcessMode == "single_process"
                or self.ProcessMode != "multi_process"
        ):
            self.window.ProcessModeComboBox.setCurrentText("单进程模式")
        else:
            self.window.ProcessModeComboBox.setCurrentText("多进程模式")
        # 设置 topWindowCheckBox 的状态
        self.window.topWindowCheckBox.setChecked(self.window_always_on_top)
        # 根据设置，更新窗口置顶状态
        self.update_window_on_top_state()

    def update_window_on_top_state(self):
        """根据复选框状态更新窗口的置顶状态"""
        if self.window.topWindowCheckBox.isChecked():
            self.window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        else:
            self.window.setWindowFlag(
                Qt.WindowType.WindowStaysOnTopHint, False)
        self.window.show()  # 需要调用 show() 以应用窗口标志的更改

    def update_unlock_window_size(self):
        """根据复选框状态更新窗口大小锁定的状态"""
        if self.window.unlockWindowSizeCheckBox.isChecked():
            # 解锁窗口大小：允许调整
            self.window.setFixedSize(QSize())  # 移除固定大小限制
            self.window.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            self.window.setMinimumSize(300, 400)  # 设置合理的最小尺寸，视具体需求调整
            self.window.setMaximumSize(QSize(16777215, 16777215))  # 设置最大的尺寸限制
        else:
            # 锁定窗口大小：设置固定大小为当前尺寸
            self.window.setFixedSize(self.window.size())
            self.window.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def update_jum_suppression_state(self):
        """跳变抑制开关"""
        if self.window.jumpSuppressionCheckBox.isChecked():
            self.mouseMoveProssesSignal_queue.put(("jump_detection_switch", True))
        else:
            self.mouseMoveProssesSignal_queue.put(("jump_detection_switch", False))

    def update_automatic_trigger_state(self):
        """自动扳机开关"""
        if self.window.automatic_trigger_switchCheckBox.isChecked():
            self.accessibilityProcessSignal_queue.put(("automatic_trigger_switch", True))
        else:
            self.accessibilityProcessSignal_queue.put(("automatic_trigger_switch", False))

    def reset_window_size(self):
        """重置窗口大小为 (1290, 585)"""
        target_size = QSize(1290, 585)

        if self.window.unlockWindowSizeCheckBox.isChecked():
            # 如果窗口大小已解锁，直接调整窗口大小
            self.window.resize(target_size)
        else:
            # 如果窗口大小已锁定，设置固定大小为目标大小
            self.window.setFixedSize(target_size)

        # 如果需要在重置大小后更新大小策略，可以在这里进行
        if self.window.unlockWindowSizeCheckBox.isChecked():
            self.window.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        else:
            self.window.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def choose_process_model_comboBox(self):
        """选择进程模式"""
        ProcessMode = self.window.ProcessModeComboBox.currentText()  # 获取当前选项文本
        return "multi_process" if ProcessMode == "多进程模式" else "single_process"

    def apply_rounded_mask_to_show_video(self):
        """对 show_video 应用带圆角的遮罩"""
        radius = 20  # 设置圆角半径
        width = self.window.show_video.width()
        height = self.window.show_video.height()

        # 创建带圆角的遮罩
        mask = QBitmap(width, height)
        mask.fill(Qt.GlobalColor.color0)  # 使用 GlobalColor 中的 color0
        painter = QPainter(mask)
        # 使用 RenderHint.Antialiasing
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.GlobalColor.color1)  # 使用 GlobalColor 中的 color1
        painter.drawRoundedRect(0, 0, width, height, radius, radius)
        painter.end()

        # 将遮罩应用到 show_video
        self.window.show_video.setMask(mask)

    def update_button_text(self):
        """更新按钮文本"""
        if self.is_video_running:
            self.window.OpVideoButton.setText("关闭视频预览")
        else:
            self.window.OpVideoButton.setText("打开视频预览")

    def update_video_frame(self):
        """更新视频帧到QLabel"""
        frame = None  # 初始化 frame 为 None
        if not self.processedVideo_queue.empty():
            # 清空队列，只保留最新的帧
            while not self.processedVideo_queue.empty():
                frame = self.processedVideo_queue.get()

        # 如果 frame 为空，直接返回以跳过更新
        if frame is None:
            # logger.debug("未接收到视频帧，跳过更新")
            return

        # 更新 FPS 计数
        self.frame_count += 1
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        # 每 fps_update_interval 秒更新一次 FPS
        if elapsed_time >= self.fps_update_interval:
            self.fps = self.frame_count / elapsed_time  # 计算当前 FPS
            self.frame_count = 0
            self.start_time = current_time

        # 将 BGR 转换为 RGB 格式
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # 将帧转换为 QImage
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_img = QImage(frame.data, width, height,
                       bytes_per_line, QImage.Format.Format_RGB888)
        # 绘制 FPS
        cv2.putText(frame, f'FPS: {self.fps:.1f}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
        # 更新 QLabel，保持等比填充
        pixmap = QPixmap.fromImage(q_img)
        pixmap = pixmap.scaled(self.window.show_video.size(), aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio,
                               transformMode=Qt.TransformationMode.SmoothTransformation)

        self.window.show_video.setPixmap(pixmap)

    def toggle_YOLO_button(self):
        """切换 YOLO 处理状态并更新按钮文本"""
        if self.is_yolo_running:
            self._extracted_from_toggle_YOLO_button_5(
                'YOLO_stop', "开启 YOLO", False, "YOLO 处理已停止。"
            )
        else:
            # 开启 YOLO 处理
            self.req_config()  # 手动请求数据
            self._extracted_from_toggle_YOLO_button_5(
                'YOLO_start', "关闭 YOLO", True, "YOLO 处理已启动。"
            )

    # TODO Rename this here and in `toggle_YOLO_button`
    def _extracted_from_toggle_YOLO_button_5(self, arg0, arg1, arg2, arg3):
        # 停止 YOLO 处理
        self.YoloSignal_queue.put((arg0, None))
        self.window.OpYoloButton.setText(arg1)
        self.is_yolo_running = arg2
        logger.debug(arg3)

    def toggle_video_button(self):
        """切换视频状态并更新按钮文本"""
        # video_source = self.choose_process_model_comboBox()  # 通过选择器获取进程模式
        video_source = "screen"  # 视频源

        if self.is_video_running:
            logger.debug("关闭视频源:", video_source)
            self.window.OpVideoButton.setText("关闭视频显示中...")  # 更新按钮文本
            self.pipe_parent.send(('stop_video', video_source))  # 发送停止视频信号
            self.window.status_widget.display_message("预览已关闭", bg_color="Yellow", text_color="black",
                                                      auto_hide=1500)
            # 启动清理定时器
            if not hasattr(self, 'clear_timer'):
                self.clear_timer = QTimer()
                self.clear_timer.timeout.connect(self.clear_video_display)
            self.clear_timer.start(100)  # 每100毫秒清理一次
            self.is_video_running = False  # 更新状态
        else:
            logger.debug("启动视频源:", video_source)
            self.window.OpVideoButton.setText("打开视频显示中...")  # 更新按钮文本
            self.pipe_parent.send(("start_video", video_source))  # 发送启动视频信号
            self.window.status_widget.display_message("预览已开启", bg_color="#55ff00", text_color="black",
                                                      auto_hide=1500)
            # 停止清理定时器
            if hasattr(self, 'clear_timer'):
                self.clear_timer.stop()
                del self.clear_timer  # 删除定时器
            self.is_video_running = True  # 更新状态

        self.update_button_text()  # 更新按钮文本

    def hide_settings(self):
        """隐藏设置面板"""

        # 获取当前设置面板的位置
        start_pos = self.window.settingsPanel.pos()
        # 计算结束位置，使面板移出屏幕（左侧）
        end_pos = QPoint(-self.window.settingsPanel.width(), start_pos.y())

        # 创建一个属性动画，控制设置面板的位置
        self.window.animation = QPropertyAnimation(
            self.window.settingsPanel, b"pos")
        self.window.animation.setDuration(500)  # 动画持续时间为 500 毫秒
        self.window.animation.setStartValue(start_pos)  # 动画开始位置
        self.window.animation.setEndValue(end_pos)  # 动画结束位置
        self.window.animation.setEasingCurve(
            QEasingCurve.Type.InQuad)  # 设置动画效果为缓入

        # 启动面板位置动画
        self.window.animation.start()

        # 设置遮罩动画属性
        self.window.overlay_animation.setDuration(500)  # 遮罩动画持续时间为 500 毫秒
        self.window.overlay_animation.setStartValue(1)  # 遮罩的初始透明度
        self.window.overlay_animation.setEndValue(0)  # 遮罩的结束透明度（完全透明）
        self.window.overlay_animation.setEasingCurve(
            QEasingCurve.Type.InQuad)  # 设置动画效果为缓入

        # 启动遮罩透明度动画
        self.window.overlay_animation.start()

        # 在面板隐藏动画完成后，隐藏面板并使主窗口可用
        self.window.animation.finished.connect(self.window.settingsPanel.hide)
        self.window.animation.finished.connect(lambda: (
            self.window.settingsPanel.hide(),
            self.window.overlay.hide(),  # 隐藏遮罩
            self.window.setEnabled(True)  # 使主窗口重新可用
        ))

    def show_settings(self):
        """显示设置面板和半透明遮罩"""

        # 显示遮罩组件
        self.window.overlay.show()

        # 设置遮罩动画属性
        self.window.overlay_animation.setDuration(500)  # 遮罩动画持续时间为 500 毫秒
        self.window.overlay_animation.setStartValue(0)  # 遮罩的初始透明度（完全透明）
        self.window.overlay_animation.setEndValue(1)  # 遮罩的结束透明度（完全不透明）
        self.window.overlay_animation.setEasingCurve(
            QEasingCurve.Type.OutQuad)  # 设置动画效果为缓出

        # 启动遮罩透明度动画
        self.window.overlay_animation.start()

        # 设置允许鼠标事件通过遮罩
        self.window.overlay.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.window.settingsPanel.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        # 显示设置面板
        self.window.settingsPanel.show()

        # 获取当前设置面板的位置
        start_pos = self.window.settingsPanel.pos()
        # 计算结束位置，使面板从左侧进入屏幕
        end_pos = QPoint(0, start_pos.y())

        # 创建一个属性动画，控制设置面板的位置
        self.window.animation = QPropertyAnimation(
            self.window.settingsPanel, b"pos")
        self.window.animation.setDuration(500)  # 动画持续时间为 500 毫秒
        self.window.animation.setStartValue(start_pos)  # 动画开始位置
        self.window.animation.setEndValue(end_pos)  # 动画结束位置
        self.window.animation.setEasingCurve(
            QEasingCurve.Type.OutQuad)  # 设置动画效果为缓出

        # 启动面板位置动画
        self.window.animation.start()

    def disable_buttons(self):
        """禁用按钮，防止在动画进行时重复点击"""
        self.window.advancedSettingsPushButton.setEnabled(False)
        self.window.basicSettingsPushButton.setEnabled(False)
        self.window.softwareInformationPushButton.setEnabled(False)

    def enable_buttons(self):
        """启用按钮"""
        self.window.advancedSettingsPushButton.setEnabled(True)
        self.window.basicSettingsPushButton.setEnabled(True)
        self.window.softwareInformationPushButton.setEnabled(True)

    def on_animation_finished(self):
        """动画结束后的处理"""
        # 启用按钮
        self.enable_buttons()

    def move_to_frame(self, target_index):
        """根据目标框架索引移动框架，实现页面切换动画。"""
        if self.current_frame_index == target_index:
            return  # 如果点击的是当前显示的框架，则不执行

        duration = 500  # 动画持续时间，单位为毫秒
        frame_width = self.frames[0].width()  # 假设所有框架宽度相同

        # 禁用按钮，防止在动画过程中重复点击
        self.disable_buttons()

        # 如果有正在进行的动画，先停止并清理
        if hasattr(self, 'animation_group') and self.animation_group.state() == QParallelAnimationGroup.State.Running:
            self.animation_group.stop()

        # 创建新的动画组
        self.animation_group = QParallelAnimationGroup()

        # 计算偏移量（当前索引 - 目标索引） * 框架宽度
        offset = (self.current_frame_index - target_index) * frame_width

        # 为每个框架创建动画
        for frame in self.frames:
            start_pos = frame.pos()
            end_pos = QPoint(start_pos.x() + offset, start_pos.y())

            # 创建动画
            animation = QPropertyAnimation(frame, b"pos")
            animation.setDuration(duration)
            animation.setStartValue(start_pos)
            animation.setEndValue(end_pos)
            animation.setEasingCurve(QEasingCurve.Type.OutQuad)

            # 将动画添加到动画组
            self.animation_group.addAnimation(animation)

        # 连接动画组的 finished 信号
        self.animation_group.finished.connect(self.on_animation_finished)

        # 启动动画组
        self.animation_group.start()

        # 更新当前框架索引
        self.current_frame_index = target_index

    def on_item_button_clicked(self, button_type):
        """当 itemFrame 中的按钮被点击时调用"""

        # 清除之前的动画引用
        self.item_animations.clear()

        # 获取按钮和红线控件
        basic_button = self.window.basicSettingsPushButton
        advanced_button = self.window.advancedSettingsPushButton
        software_button = self.window.softwareInformationPushButton
        red_line = self.window.redLine

        # 创建一个字典，方便根据类型获取按钮
        buttons = {
            "basic": basic_button,
            "advanced": advanced_button,
            "software": software_button
        }

        # 获取目标按钮
        target_button = buttons.get(button_type)

        # 如果目标按钮与当前选中的按钮相同，则不执行任何操作
        if self.current_selected == button_type:
            return

        # 更新当前选中的按钮类型
        self.current_selected = button_type

        # 按钮列表
        all_buttons = [basic_button, advanced_button, software_button]

        # 动画持续时间
        duration = 200  # 可以根据需要调整

        # 移动红线到目标按钮下方
        red_line_animation = QPropertyAnimation(red_line, b"geometry")
        red_line_animation.setDuration(duration)
        red_line_animation.setStartValue(red_line.geometry())
        target_red_line_geometry = QRect(
            target_button.x(), red_line.y(), target_button.width(), red_line.height())
        self._extracted_from_on_item_button_clicked_59(
            red_line_animation, target_red_line_geometry
        )
        # 移动按钮位置
        for button in all_buttons:
            button_animation = QPropertyAnimation(button, b"geometry")
            button_animation.setDuration(duration)
            button_animation.setStartValue(button.geometry())

            if button == target_button:
                # 被选中的按钮上移 5 像素
                target_geometry = QRect(
                    button.x(), self.button_selected_y, button.width(), button.height())
            else:
                # 其他按钮回到默认 y 位置
                target_geometry = QRect(
                    button.x(), self.button_default_y, button.width(), button.height())

            self._extracted_from_on_item_button_clicked_59(
                button_animation, target_geometry
            )

    # TODO Rename this here and in `on_item_button_clicked`
    def _extracted_from_on_item_button_clicked_59(self, arg0, arg1):
        arg0.setEndValue(arg1)
        arg0.setEasingCurve(QEasingCurve.Type.OutQuad)
        arg0.start()
        self.item_animations.append(arg0)

    def clear_video_display(self):
        """清空视频显示窗口直到清空干净"""
        if self.window.show_video.pixmap():
            self.window.show_video.setPixmap(QPixmap())  # 清空显示窗口
        else:
            self.clear_timer.stop()  # 停止定时器

    def change_yolo_model(self):
        """重新加载模型"""
        logger.debug("重新加载模型")
        # 检查模型文件路径是否为空
        if not getattr(self, 'model_file', None):  # 如果 model_file 属性不存在或为空
            log_msg = "未选择模型文件，无法重新加载模型。"
            self.window.status_widget.display_message(
                log_msg, bg_color="Red", text_color="black", auto_hide=6000)
            return  # 退出方法，不执行后续操作

        # 如果此时 视频预览 在开启状态，则进行关闭。
        if self.is_video_running:
            self.toggle_video_button()
        # 如果此时 YOLO推理 在开启状态，则进行关闭。
        if self.is_yolo_running:
            self.toggle_YOLO_button()

        if self.ProcessMode == "multi_process":
            # 发送更改模型信号 与 模型路径(多进程)
            self.YoloSignal_queue.put(("change_model", self.model_file))
            self.information_output_queue.put(
                ("UI_process_log", "向 YoloSignal_queue 发送 change_model"))
        else:
            # 发送更改模型信号 与 模型路径(单进程)
            self.videoSignal_queue.put(("change_model", self.model_file))
            self.information_output_queue.put(
                ("UI_process_log", "向 videoSignal_queue 发送 change_model"))

        # 显示模型已重新加载的消息
        self.window.status_widget.display_message("模型已重新加载", bg_color="#55ff00", text_color="black",
                                                  auto_hide=1500)

    def choose_model(self):
        """弹出文件选择窗口，让用户选择模型文件"""
        model_file, _ = QFileDialog.getOpenFileName(
            self.window,  # 父窗口
            "选择模型文件",  # 对话框标题
            "",  # 默认打开的路径
            "模型文件 (*.pt *.engine *.onnx);;所有文件 (*.*)"  # 文件过滤器
        )
        if model_file:  # 如果用户选择了文件
            self.file_name = os.path.basename(model_file)  # 只提取文件名和后缀
            self.window.modelFileLabel.setText(self.file_name)  # 更新UI中的标签文本
            self.model_file = model_file  # 保存模型文件路径到类属性
            logger.debug(f"选择的模型文件: {self.file_name}")

    def show(self):
        """显示窗口"""
        self.window.show()

        self.show_loading_animation()  # 显示加载信息悬浮窗

        self.show_log_output()  # 开启 调试信息 输出监听

        # 更新 modelFileLabel 显示的模型名称
        file_name = os.path.basename(self.model_file)  # 只提取文件名和后缀
        self.window.modelFileLabel.setText(file_name)  # 更新UI中的标签文本

        # 发送最新 置信度
        self.YoloSignal_queue.put(("change_conf", self.yolo_confidence))

        self.information_output_queue.put(("UI_process_log", "UI主进程 初始化完毕"))

        sys.exit(self.app.exec())

    def show_loading_animation(self):
        # 提示加载信息框
        self.window.status_widget.show_status_widget(
            "加载中...", bg_color="Yellow", text_color="black")

        # 创建定时器，用来周期性地检查队列
        # 将 self.window 作为 QTimer 的父对象
        self.timer_check_queue = QTimer(self.window)
        self.timer_check_queue.timeout.connect(
            self.check_floating_information_signal_queue)
        self.timer_check_queue.start(500)  # 每100毫秒检查一次队列

    def check_floating_information_signal_queue(self):
        """检查 floating_information_signal_queue 是否有加载完毕的信号"""
        if not self.floating_information_signal_queue.empty():
            message = self.floating_information_signal_queue.get_nowait()  # 非阻塞地获取消息
            if message[0] == "loading_complete" and message[1] is True:
                logger.info("软件初始化完毕，停止检查队列")
                # 停止定时器检查队列
                # self.timer_check_queue.stop()
                # 更新UI或执行其他操作
                self.window.status_widget.display_message("加载完毕", bg_color="#55ff00", text_color="black",
                                                          auto_hide=3000)
            elif message[0] == "error_log":
                self.window.status_widget.display_message(message[1], bg_color="Yellow", text_color="black",
                                                          auto_hide=3000)
            elif message[0] == "red_error_log":
                self.window.status_widget.show_status_widget(
                    message[1], bg_color="Red", text_color="black")

    def show_log_output(self):
        """调试信息输出 计时循环"""
        logger.debug("调试信息输出 监听信号...")
        self.timer_check_information_output_queue = QTimer(self.window)
        self.timer_check_information_output_queue.timeout.connect(
            self.log_output)
        self.timer_check_information_output_queue.start(100)

    def log_output(self):
        """调试信息输出"""
        if self.information_output_queue.empty():
            return
        message = self.information_output_queue.get_nowait()
        logger.debug("information_output_queue 队列接收信息:", message)

        if message[0] == "UI_process_log":  # UI主进程 调试信息输出
            log_msg = message[1]

            if not isinstance(log_msg, str):
                log_msg = str(log_msg)

            self.window.log_output_00.append(f"[INFO]UI主进程 日志: {log_msg}")
            self.window.log_output_00.ensureCursorVisible()

        if message[0] == "log_output_main":  # 主通信进程 调试信息输出
            log_msg = message[1]  # 提取信息段

            # 确保 log_msg 是字符串类型
            if not isinstance(log_msg, str):
                log_msg = str(log_msg)  # 如果不是字符串类型，则转换为字符串

            self.window.log_output_01.append(
                f"[INFO]通信进程 收到信号: {log_msg}")  # 添加新的日志信息
            self.window.log_output_01.ensureCursorVisible()  # 确保光标可见

        if message[0] == "video_processing_log":  # 视频处理进程 调试信息输出
            log_msg = message[1]

            if not isinstance(log_msg, str):
                log_msg = str(log_msg)

            self.window.log_output_02.append(
                f"[INFO]视频处理进程 收到信号: {log_msg}")
            self.window.log_output_02.ensureCursorVisible()

        if message[0] == "video_signal_acquisition_log":  # 视频信号接收进程 调试信息输出
            log_msg = message[1]
            operate, signal_source = log_msg

            if not isinstance(log_msg, str):
                log_msg = str(log_msg)

            self.window.log_output_03.append(
                f"[INFO]动作: {operate}  信号源: {signal_source}")
            self.window.log_output_03.ensureCursorVisible()

        if message[0] == "error_log":  # 报错信息提示
            log_msg = message[1]

            if not isinstance(log_msg, str):
                log_msg = str(log_msg)

            self.window.status_widget.display_message(
                log_msg, bg_color="Red", text_color="black", auto_hide=6000)

    def main(self):
        """程序启动初始化"""
        '''创建管道与队列'''
        # 创建总管道，总信号传输，
        parent_conn, child_conn = Pipe()  # 总传输管道
        VideoSignal_queue = Queue()  # 视频状态信号队列
        videoSignal_stop_queue = Queue()  # 视频状态信号队列（停止）
        video_queue = Queue(maxsize=1)  # 源视频画面传输队列
        processedVideo_queue = Queue(maxsize=1)  # 处理后的视频画面传输队列
        YoloSignal_queue = Queue()  # YOLO控制管道
        floating_information_signal_queue = Queue()  # 悬浮信息窗通信队列
        information_output_queue = Queue()  # 调试信息输出独立额
        mouseMoveProssesSignal_queue = Queue()  # 鼠标移动进程通信队列
        accessibilityProcessSignal_queue = Queue(maxsize=1)  # 辅助功能进程通信队列

        # 保存父进程中的管道与队列引用
        self.pipe_parent = parent_conn  # 控制信号的管道(父)
        self.pipe_child = child_conn  # 控制信号的管道(子)
        self.videoSignal_queue = VideoSignal_queue  # 视频信号队列
        self.videoSignal_stop_queue = videoSignal_stop_queue  # 视频状态信号队列（停止）
        self.video_queue = video_queue  # 视频传输队列
        self.processedVideo_queue = processedVideo_queue  # 处理后的视频画面传输队列
        self.YoloSignal_queue = YoloSignal_queue  # YOLO控制队列
        self.floating_information_signal_queue = floating_information_signal_queue  # 悬浮信息窗通信队列
        self.information_output_queue = information_output_queue  # 调试信息输出队列
        self.mouseMoveProssesSignal_queue = mouseMoveProssesSignal_queue  # 鼠标移动进程通信队列
        self.accessibilityProcessSignal_queue = accessibilityProcessSignal_queue  # 辅助功能进程通信队列

        self.information_output_queue.put(("UI_process_log", "管道创建完毕"))

        self.load_settings()  # 加载配置文件
        self.init_ui_from_settings()  # 根据加载的配置文件设置界面初始状态

        '''创建共享内存，用于 Box 坐标传输'''
        box_shape = (1, 6)  # 修改为1行，每行6字段 (x1, y1, x2, y2, distance, unique_id)
        box_dtype = np.float32
        box_size = int(np.prod(box_shape) * np.dtype(box_dtype).itemsize)
        box_shm = shared_memory.SharedMemory(create=True, size=box_size)
        box_array = np.ndarray(box_shape, dtype=box_dtype, buffer=box_shm.buf)
        box_array.fill(0)  # 初始化为0

        '''创建共享内存，用于 video_queue'''
        frame_shape = (320, 320, 3)  # 根据您的实际帧尺寸
        frame_dtype = np.uint8  # 假设帧的数据类型为 uint8
        frame_size = int(np.prod(frame_shape) * np.dtype(frame_dtype).itemsize)
        shm_video = shared_memory.SharedMemory(create=True, size=frame_size)
        shm_video_name = shm_video.name  # 共享内存名称，用于在子进程中访问

        '''创建同步原语'''
        # 用于 Box 坐标同步
        box_data_event = Event()  # 用于通知Box数据可用
        box_lock = multiprocessing.Lock()  # 用于同步访问Box共享内存

        # 用于视频帧同步
        frame_available_event = Event()

        # 保存共享内存和事件的引用
        information_output_queue.put(
            ("UI_process_log", f"共享内存已创建，名称为 {shm_video_name}"))
        information_output_queue.put(
            ("UI_process_log", f"Box共享内存已创建，名称为 {box_shm.name}"))

        '''创建进程'''
        # 1.进程通信进程
        process_signal_processing = Process(target=communication_Process,
                                            args=(self.pipe_child, self.videoSignal_queue, self.videoSignal_stop_queue,
                                                  self.floating_information_signal_queue,
                                                  self.information_output_queue,))
        self._extracted_from_main_65(
            process_signal_processing, "process_signal_processing 进程创建完毕"
        )
        # 2.视频信号获取进程
        if self.ProcessMode == "multi_process":  # 多进程模式
            target_function = start_capture_process_multie
            args = (
                shm_video_name, frame_shape, frame_dtype,
                frame_available_event, self.videoSignal_queue,
                self.videoSignal_stop_queue, self.pipe_parent,
                self.information_output_queue, self.ProcessMode
            )
        elif self.ProcessMode == "single_process":  # 单进程模式
            target_function = start_capture_process_single
            args = (
                self.videoSignal_queue, self.videoSignal_stop_queue,
                self.information_output_queue,
                self.processedVideo_queue, self.YoloSignal_queue, self.pipe_parent, self.model_file,
                box_shm.name, box_data_event, box_lock, self.accessibilityProcessSignal_queue
            )
        else:
            raise ValueError(f"未知的 ProcessMode: {self.ProcessMode}")
        # 创建并启动进程
        process_video_signal = Process(target=target_function, args=args)
        self._extracted_from_main_65(process_video_signal, "process_video_signal 进程创建完毕")

        # 3.视频处理进程(仅在多进程时启动)
        if self.ProcessMode == "multi_process":
            process_videoprocessing = Process(target=video_processing,
                                              args=(shm_video_name, frame_shape, frame_dtype,
                                                    frame_available_event, processedVideo_queue,
                                                    YoloSignal_queue, parent_conn,
                                                    information_output_queue, self.model_file,
                                                    box_shm.name, box_data_event, box_lock,
                                                    accessibilityProcessSignal_queue))
            process_videoprocessing.daemon = True
            process_videoprocessing.start()
            information_output_queue.put(
                ("UI_process_log", "process_videoprocessing 进程创建完毕"))

        # 4.鼠标移动进程
        process_mouse_move = Process(target=mouse_move_prosses,
                                     args=(box_shm.name, box_lock, self.mouseMoveProssesSignal_queue,
                                           self.accessibilityProcessSignal_queue))
        self._extracted_from_main_65(process_mouse_move, "process_mouse_move 进程创建完毕")

        # 5.辅助功能进程
        process_accessibility = Process(target=accessibility_process, args=(self.accessibilityProcessSignal_queue,))
        self._extracted_from_main_65(process_accessibility, "process_accessibility 进程创建完毕")

        # 启动进程后，保存引用
        self.process_signal_processing = process_signal_processing
        self.process_video_signal = process_video_signal
        self.process_mouse_move = process_mouse_move

        '''显示软件页面'''
        self.show()  # 初始化完毕 显示 UI窗口

    # TODO Rename this here and in `main`
    def _extracted_from_main_65(self, arg0, arg1):
        arg0.daemon = True
        arg0.start()
        self.information_output_queue.put(("UI_process_log", arg1))


if __name__ == '__main__':
    multiprocessing.freeze_support()
    app = RookieAiAPP()
    app.main()
