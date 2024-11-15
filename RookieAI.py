import contextlib
import multiprocessing
import os
import queue
import sys
import time
from multiprocessing import Pipe, Process, Queue, shared_memory, Event
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
from utils.AnimatedStatusUtils.animated_status import AnimatedStatus  # 导入 带动画的状态提示浮窗 库
from utils.config import Config, Root


def communication_Process(pipe, videoSignal_queue, videoSignal_stop_queue, floating_information_signal_queue,
                          information_output_queue):
    """
    总通信进程
    pipe_parent
    """
    global video_running

    print("启动 communication_Process 监听信号...")
    while True:
        if pipe.poll():
            try:
                message = pipe.recv()
                if isinstance(message, tuple):  # 处理消息类型
                    cmd, cmd_01 = message
                    print(f"收到信号: {cmd}")
                    print(f"信号内容: {cmd_01}")

                    information_output_queue.put(("log_output_main", message))  # 显示调试信息

                    # 手动触发异常测试
                    if cmd == "trigger_error":
                        raise ValueError("[INFO]手动触发的错误")

                    if cmd == "start_video":
                        print("[INFO]启动视频命令")
                        video_running = True
                        videoSignal_queue.put(("start_video", cmd_01))

                    elif cmd == "stop_video":
                        print("[INFO]停止视频命令")
                        video_running = False
                        videoSignal_stop_queue.put(("stop_video", cmd_01))

                    elif cmd == "loading_complete":
                        print("[INFO]软件初始化完毕")
                        floating_information_signal_queue.put(("loading_complete", cmd_01))

                    elif cmd == "loading_error":
                        print("[ERROR]，一般错误，软件初始化失败")
                        floating_information_signal_queue.put(("error_log", cmd_01))

                    elif cmd == "red_error":
                        print("[ERROR]致命错误，无法加载模型")
                        floating_information_signal_queue.put(("red_error_log", cmd_01))

            except (BrokenPipeError, EOFError) as e:
                print(f"管道通信错误: {e}")
                information_output_queue.put(("error_log", f"管道通信错误: {e}"))  # 捕获并记录错误信息
            except Exception as e:
                print(f"发生错误: {e}")
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
    shared_frame = np.ndarray(frame_shape, dtype=frame_dtype, buffer=existing_shm.buf)

    print("视频信号获取进程已启动。")
    while True:
        try:
            message = videoSignal_queue.get(timeout=1)
            command, information = message
            print(f"接收到命令: {command}, 内容: {information}")
            information_output_queue.put(("video_signal_acquisition_log", message))  # 调试信息输出

            if command == "start_video":
                print("进程模式选择")
                print("进程模式：", ProcessMode)
                open_screen_video(shared_frame, frame_available_event, videoSignal_stop_queue)
            if command == "change_model":
                print("正在重新加载模型")
                model_file = information
                model = YOLO(model_file)
                print(f"模型 {model_file} 加载完毕")
                pass
        except queue.Empty:
            pass
        except Exception as e:
            print(f"获取视频信号时发生错误: {e}")
            information_output_queue.put(("error_log", f"获取视频信号时发生错误: {e}"))


def start_capture_process_single(videoSignal_queue, videoSignal_stop_queue, information_output_queue,
                                 processedVideo_queue, YoloSignal_queue, pipe_parent, model_file,
                                 box_shm_name, box_data_event, box_lock):
    """
    （单进程）子进程视频信号获取逻辑
    接收内容:
    1.start_video
    2.stop_video
    """
    print("视频信号获取进程已启动。")

    def initialization_Yolo(model_file, information_output_queue):
        """初始化 YOLO 并进行一次模拟推理"""
        try:
            # 检查模型文件是否存在
            if not os.path.exists(model_file):
                print(f"模型文件 '{model_file}' 未找到，尝试使用默认模型 'yolo11n.pt'。")
                information_output_queue.put(
                    ("log_output_main", f"模型文件 '{model_file}' 未找到，使用默认模型 'yolo11n.pt'。"))
                model_file = "yolo11n.pt"
                log_message = f"[ERROR]一般错误，模型文件 '{model_file}' 未找到，使用默认模型 'yolo11n.pt'。"
                pipe_parent.send(("loading_error", log_message))  # 选定文件未能找到，黄色报错
                if not os.path.exists(model_file):
                    log_message = f"[ERROR]致命错误，默认模型文件 '{model_file}' 也未找到。请确保模型文件存在。"
                    pipe_parent.send(("red_error", log_message))  # 默认文件也未找到，红色报错
                    raise FileNotFoundError(f"默认模型文件 '{model_file}' 也未找到。请确保模型文件存在。")

            model = YOLO(model_file)  # 加载 YOLO 模型
            print(f"YOLO 模型 '{model_file}' 已加载。")
            # 创建一张临时图像（纯色或随机噪声）用于预热
            temp_img = np.zeros((320, 320, 3), dtype=np.uint8)  # 修改为640x640
            temp_img_path = "temp_init_image.jpg"
            cv2.imwrite(temp_img_path, temp_img)
            # 执行一次模拟推理
            model.predict(temp_img_path, conf=0.5)
            print("YOLO 模型已预热完成。")
            os.remove(temp_img_path)  # 删除临时图像
            return model
        except Exception as e:
            print(f"YOLO 初始化失败: {e}")
            information_output_queue.put(("error_log", f"YOLO 初始化失败: {e}"))
            return None

    model = initialization_Yolo(model_file, information_output_queue)  # 初始化YOLO
    pipe_parent.send(("loading_complete", True))  # 初始化加载完成标志

    with contextlib.suppress(KeyboardInterrupt):
        while True:
            """开始监听视频开关信号"""
            try:
                message = videoSignal_queue.get(timeout=1)
                command, information = message
                print(f"接收到命令: {command}, 内容: {information}")
                information_output_queue.put(("video_signal_acquisition_log", message))  # 调试信息输出
                if command == 'start_video':
                    print("启动视频捕获和YOLO处理")
                    # 调用集成了共享内存写入的屏幕捕获和YOLO处理函数
                    screen_capture_and_yolo_processing(
                        processedVideo_queue, videoSignal_stop_queue, YoloSignal_queue,
                        pipe_parent, information_output_queue, model,
                        box_shm_name, box_data_event, box_lock
                    )
                if command == 'change_model':  # 重新加载模型
                    print("正在重新加载模型")
                    model_file = information
                    model = YOLO(model_file)
                    print(f"模型 {model_file} 加载完毕")
            except queue.Empty:
                pass
            except Exception as e:
                print(f"获取视频信号时发生错误: {e}")
                information_output_queue.put(("error_log", f"获取视频信号时发生错误: {e}"))


def open_screen_video(shared_frame, frame_available_event, videoSignal_stop_queue):
    """（多进程）打开屏幕捕获并显示视频帧"""
    # 清空 videoSignal_stop_queue 队列
    while not videoSignal_stop_queue.empty():
        try:
            videoSignal_stop_queue.get_nowait()
        except Exception:
            break
    with mss.mss() as sct:
        # 获取屏幕分辨率
        screen_width, screen_height = pyautogui.size()
        print("屏幕分辨率:", screen_width, screen_height)

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
            if not videoSignal_stop_queue.empty():  # 检查信号队列
                command, _ = videoSignal_stop_queue.get()
                print(f"videoSignal_stop_queue（多进程） 队列接收信息 {command}")
                if command == 'stop_video':
                    print("停止屏幕捕获")
                    break  # 退出循环

            # 获取指定区域的截图
            img = sct.grab(capture_area)

            # 使用 numpy.frombuffer 直接转换为数组，避免数据拷贝
            frame = np.frombuffer(img.rgb, dtype=np.uint8)
            frame = frame.reshape((img.height, img.width, 3))

            # 如果需要，可以跳过颜色空间转换
            # frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)

            # 将视频帧放入队列
            np.copyto(shared_frame, frame)
            frame_available_event.set()


def screen_capture_and_yolo_processing(processedVideo_queue, videoSignal_stop_queue, YoloSignal_queue, pipe_parent,
                                       information_output_queue, model,
                                       box_shm_name, box_data_event, box_lock):
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
    yolo_enabled = False
    yolo_confidence = 0.5  # 初始化 YOLO 置信度
    unique_id_counter = 0

    # 清空 videoSignal_stop_queue 队列
    while not videoSignal_stop_queue.empty():
        try:
            videoSignal_stop_queue.get_nowait()
        except Exception:
            break

    with mss.mss() as sct:
        # 获取屏幕分辨率
        screen_width, screen_height = pyautogui.size()
        print("屏幕分辨率:", screen_width, screen_height)
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
                    print(f"videoSignal_stop_queue（单进程） 队列接收信息 {command}")
                    if command == 'stop_video':
                        print("停止屏幕捕获")
                        break
                    if command == 'change_model':
                        print("重新加载模型")
                        break
                # 检查 YOLO 的开启或停止信号
                if not YoloSignal_queue.empty():
                    command_data = YoloSignal_queue.get()
                    if isinstance(command_data, tuple):
                        cmd, cmd_01 = command_data
                        information_output_queue.put(("video_processing_log", command_data))
                        if cmd == 'YOLO_start':
                            yolo_enabled = True
                        elif cmd == 'YOLO_stop':
                            yolo_enabled = False
                        elif cmd == "change_conf":  # 更改置信度
                            print("更改置信度")
                            yolo_confidence = cmd_01
                        elif cmd == "change_class":
                            print(f"更改检测类别为: {cmd_01}")
                            target_class = cmd_01  # 更新目标类别
                # 获取屏幕帧
                img = sct.grab(capture_area)
                frame = np.frombuffer(img.rgb, dtype=np.uint8).reshape((img.height, img.width, 3)).copy()  # 确保frame是可写的
                # 如果启用了 YOLO，执行推理并写入共享内存
                if yolo_enabled and model is not None:
                    processed_frame = YOLO_process_frame(
                        model, frame, yolo_confidence,
                        target_class=target_class,
                        box_shm_name=box_shm_name,
                        box_data_event=box_data_event,
                        box_lock=box_lock
                    )
                else:
                    processed_frame = frame
                # 将处理后的帧放入队列中
                processedVideo_queue.put(processed_frame)
            except Exception as e:
                print(f"捕获或处理时出错: {e}")
                information_output_queue.put(("error_log", f"捕获或处理时出错: {e}"))
                break


def video_processing(shm_name, frame_shape, frame_dtype, frame_available_event,
                     processedVideo_queue, YoloSignal_queue, pipe_parent, information_output_queue, model_file,
                     box_shm_name, box_data_event, box_lock):
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
    shared_frame = np.ndarray(frame_shape, dtype=frame_dtype, buffer=existing_shm.buf)

    try:
        # 初始化 YOLO
        # 检查模型文件是否存在，如果不存在则使用默认模型
        if not os.path.exists(model_file):
            print(f"模型文件 '{model_file}' 未找到，尝试使用默认模型 'yolo11n.pt'")
            information_output_queue.put(
                ("log_output_main", f"模型文件 '{model_file}' 未找到，使用默认模型 'yolo11n.pt'。"))
            log_message = f"[ERROR]一般错误，模型文件 '{model_file}' 未找到，使用默认模型 'yolo11n.pt'。"
            pipe_parent.send(("loading_error", log_message))  # 选定文件未能找到，黄色报错
            model_file = "yolo11n.pt"
            if not os.path.exists(model_file):
                log_message = f"[ERROR]致命错误，默认模型文件 '{model_file}' 也未找到。请确保模型文件存在。"
                pipe_parent.send(("red_error", log_message))  # 默认文件也未找到，红色报错
                raise FileNotFoundError(f"默认模型文件 '{model_file}' 也未找到。请确保模型文件存在。")
        model = YOLO(model_file)
        print("YOLO 模型已加载。")

        # 进行一次模拟推理以预热模型
        temp_img = np.zeros((320, 320, 3), dtype=np.uint8)
        model.predict(temp_img, conf=0.5)
        print("YOLO 模型已预热完成。")

        pipe_parent.send(("loading_complete", True))  # 软件初始化加载完毕标志

        while True:
            # 检查 YoloSignal_queue 中的信号
            if not YoloSignal_queue.empty():
                command_data = YoloSignal_queue.get()
                if isinstance(command_data, tuple):
                    cmd, cmd_01 = command_data
                    print(f"video_processing(YoloSignal_queue) 收到命令: {cmd}, 信息: {cmd_01}")
                    information_output_queue.put(("video_processing_log", command_data))  # 显示调试信息
                    if cmd == 'YOLO_start':
                        yolo_enabled = True
                    elif cmd == 'YOLO_stop':
                        yolo_enabled = False
                    elif cmd == 'change_model':
                        print("video_processing进程 模型已重新加载")
                        model = YOLO(cmd_01)
                    elif cmd == "change_conf":
                        print("更改置信度")
                        yolo_confidence = cmd_01
                    elif cmd == "change_class":
                        print(f"更改检测类别为: {cmd_01}")
                        target_class = cmd_01  # 更新目标类别
                    if cmd == "aim_range_change":
                        aim_range = cmd_01
                        print(f"瞄准范围更改_01: {aim_range}")

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
        print(f"视频处理发生错误: {e}")
        information_output_queue.put(("error_log", f"视频处理发生错误: {e}"))
    finally:
        existing_shm.close()


def YOLO_process_frame(model, frame, yolo_confidence=0.1, target_class="ALL",
                       box_shm_name=None, box_data_event=None, box_lock=None, aim_range=100):
    """对帧进行 YOLO 推理，返回带有标注的图像，并将最近的 Box 坐标、距离和唯一ID写入共享内存。"""
    global unique_id_counter  # 声明使用全局变量

    try:
        # print("收到的检测类别", target_class)
        # 确定 YOLO 推理中要使用的类别
        if target_class == "ALL":
            classes = None  # 允许检测所有类别
        else:
            try:
                classes = [int(target_class)]  # 只检测指定的类别
            except ValueError:
                classes = None  # 如果转换失败，则检测所有类别

        # print("实际检测类别：", classes)

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
        else:
            closest_box = None
            closest_distance = None

        # 将最近的 Box 坐标、距离和唯一ID写入共享内存
        if box_shm_name and box_data_event and box_lock:
            # 连接到共享内存
            box_shm = shared_memory.SharedMemory(name=box_shm_name)
            box_array = np.ndarray((1, 6), dtype=np.float32, buffer=box_shm.buf)  # 修改共享内存结构，加入unique_id

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
            cv2.putText(frame, distance_text, (int(x1), int(y1) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        # 如果有最近的 Box，再绘制其绿色框和红色连接线（覆盖上一步绘制）
        if closest_box is not None:
            # 获取最近的 Box 的坐标和中心
            x1, y1, x2, y2 = closest_box
            box_center = (int((x1 + x2) / 2), int((y1 + y2) / 2))

            # 只有当距离小于 aim_range 时，才绘制绿色框和红色连接线
            if closest_distance is not None and closest_distance < aim_range:
                # 绘制最近的框的绿色边框
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 3)
                # 绘制中心点
                cv2.circle(frame, box_center, 5, (0, 255, 0), -1)
                # 绘制红色连接线
                cv2.line(frame, box_center, (int(frame_center[0]), int(frame_center[1])), (255, 0, 0), 3)

        # 返回带有检测结果的图像
        return frame  # 返回绘制后的图像是 BGR 格式

    except Exception as e:
        print(f"YOLO 推理失败: {e}")
        return frame  # 如果 YOLO 推理失败，返回原始帧


def mouse_move_prosses(box_shm_name, box_lock, mouseMoveProssesSignal_queue, aim_speed=0.2, aim_range=100, offset_centerx=0, offset_centery=0,
                      lockKey=0x02, aimbot_switch=True, mouse_Side_Button_Witch=True, max_move_rate=800, min_move_rate=300):
    """
    鼠标移动进程，读取最近的 Box 数据并执行鼠标移动，保持平滑和精准。

    参数:
    - box_shm_name: Box 坐标共享内存的名称
    - box_lock: 用于同步访问共享内存的 Lock
    - aim_speed: 瞄准速度
    - aim_range: 瞄准范围
    - offset_centerx: X 横向瞄准偏移量
    - offset_centery: Y 纵向瞄准偏移量
    - lockKey: 锁定键代码
    - mouse_Side_Button_Witch: 是否开启鼠标侧键瞄准
    - max_move_rate: 每秒最多移动的次数，最大值
    - min_move_rate: 每秒最多移动的次数，最小值
    """
    # 连接到 Box 共享内存
    box_shm = shared_memory.SharedMemory(name=box_shm_name)
    box_array = np.ndarray((1, 6), dtype=np.float32, buffer=box_shm.buf)  # 修改为1行，每行6字段

    # 获取截图中心坐标
    screenshot_center_x = 320 // 2
    screenshot_center_y = 320 // 2

    # 初始化时间变量
    last_move_time = time.time()    # 上次移动时间
    last_data_time = 0.0            # 上次数据更新时间
    last_unique_id = 0              # 上次读取的数据的唯一ID

    # 衰减参数
    decay_duration = 0.05  # 衰减持续时间 (秒)，即50毫秒
    decaying = False
    decay_start_time = None

    # 记录上次移动的距离
    last_move_x = 0
    last_move_y = 0

    # 记录上次有效的距离
    last_distance = aim_range + 1  # 初始化为超出范围

    # 累积移动量
    accumulated_x = 0.0
    accumulated_y = 0.0

    try:
        while True:
            '''信号检查部分'''
            if not mouseMoveProssesSignal_queue.empty():
                command_data = mouseMoveProssesSignal_queue.get()
                print(f"mouseMoveProssesSignal_queue 队列收到信号: {command_data}")
                if isinstance(command_data, tuple):
                    cmd, cmd_01 = command_data
                    if cmd == "aimbot_switch_change":
                        aimbot_switch = cmd_01
                        print(f"自瞄状态更改: {aimbot_switch}")

                    if cmd == "aim_speed_change":
                        aim_speed = cmd_01
                        print(f"瞄准速度更改: {aim_speed}")

                    if cmd == "aim_range_change":
                        aim_range = cmd_01
                        print(f"瞄准范围更改_02: {aim_range}")

                    if cmd == "offset_centerx_change":
                        offset_centerx = cmd_01
                        print(f"瞄准偏移X更改: {offset_centerx}")

                    if cmd == "offset_centery_change":
                        offset_centery = cmd_01
                        print(f"瞄准偏移Y更改: {offset_centery}")

                    if cmd == "lock_key_change":
                        lockKey = cmd_01
                        print(f"瞄准热键更改: {lockKey}")

                    if cmd == "mouse_Side_Button_Witch_change":
                        mouse_Side_Button_Witch = cmd_01
                        print(f"侧键瞄准开关更改: {mouse_Side_Button_Witch}")

                    if cmd == "max_move_rate_change":
                        max_move_rate = cmd_01
                        print(f"最大鼠标移动频率更改: {max_move_rate}")

                    if cmd == "min_move_rate_change":
                        min_move_rate = cmd_01
                        print(f"最小鼠标移动频率更改: {min_move_rate}")

            '''鼠标移动处理部分'''
            current_time = time.time()
            # 获取最新的 Box 数据
            with box_lock:
                boxes = box_array.copy()  # 获取最新的 Box 数据
            # 获取最近的 Box（第一项）
            closest_box = boxes[0]  # 目前只存储最近的 Box（第一项）
            x1, y1, x2, y2, distance, unique_id = closest_box  # 解包 Box 数据和唯一ID

            # 检查是否有新数据
            if unique_id != last_unique_id:  # 数据是新的
                # print("检测到新数据")
                last_unique_id = int(unique_id)
                if not np.all(closest_box[:5] == 0):
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    # 更新最后数据更新时间
                    last_data_time = current_time
                    # 更新上次有效距离
                    last_distance = distance

                    # 动态调整 move_rate，距离越近 move_rate 越小，最小 min_move_rate, move_rate 应该随着 distance 增大而增大
                    adjusted_move_rate = min(
                        max_move_rate,
                        max(
                            min_move_rate,
                            int(min_move_rate + (distance / aim_range) * (max_move_rate - min_move_rate))
                        )
                    )
                    move_interval = 1.0 / adjusted_move_rate

                    # 计算目标相对于截图中心的偏移
                    delta_x = center_x + offset_centerx - screenshot_center_x
                    delta_y = center_y + offset_centery - screenshot_center_y

                    # 根据 aim_speed 控制每次鼠标移动的距离
                    move_x = delta_x * aim_speed
                    move_y = delta_y * aim_speed

                    # 累积移动量
                    accumulated_x += move_x
                    accumulated_y += move_y

                    # 分离整数部分用于实际移动
                    int_move_x = int(accumulated_x)
                    int_move_y = int(accumulated_y)

                    # 保留小数部分
                    accumulated_x -= int_move_x
                    accumulated_y -= int_move_y

                    # 更新上次移动的距离
                    last_move_x = int_move_x
                    last_move_y = int_move_y

                    # 判断目标是否在瞄准范围内
                    target_is_within_range = distance < aim_range

                    # 检查锁定键、Shift 键和鼠标侧键是否按下
                    lockKey_pressed = win32api.GetKeyState(lockKey) & 0x8000
                    shift_pressed = win32api.GetKeyState(win32con.VK_SHIFT) & 0x8000
                    xbutton2_pressed = win32api.GetKeyState(0x05) & 0x8000  # 鼠标侧键

                    # 判断是否应该移动鼠标
                    should_move = aimbot_switch and target_is_within_range and (
                            (lockKey_pressed) or
                            (mouse_Side_Button_Witch and xbutton2_pressed)
                    )

                    # 如果满足移动条件，执行鼠标移动
                    if should_move:
                        # 只在间隔时间足够时移动鼠标
                        time_since_last_move = current_time - last_move_time
                        if time_since_last_move >= move_interval and (abs(int_move_x) > 0 or abs(int_move_y) > 0):
                            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int_move_x, int_move_y, 0, 0)
                            # 更新上次移动的时间
                            last_move_time = current_time

                    # 重置衰减状态，因为有新数据
                    decaying = False
                    decay_start_time = None

            else:
                # 没有新数据，检查是否超过数据超时
                time_since_last_data = current_time - last_data_time
                # print(f"时间自上次数据更新时间: {time_since_last_data:.4f} 秒")
                if time_since_last_data > 0.01:
                    if not decaying:
                        # 开始衰减
                        # print("进入衰减")
                        decay_start_time = current_time
                        decaying = True

                    if decaying and decay_start_time is not None:
                        elapsed = current_time - decay_start_time
                        if elapsed < decay_duration:
                            # 计算衰减因子
                            decay_factor = 1.0 - (elapsed / decay_duration)
                            scaled_move_x = int(last_move_x * decay_factor)
                            scaled_move_y = int(last_move_y * decay_factor)

                            # 判断是否有足够的移动量
                            if abs(scaled_move_x) > 0 or abs(scaled_move_y) > 0:
                                # 动态调整 move_rate based on last_distance
                                adjusted_move_rate = min(
                                    max_move_rate,
                                    max(
                                        min_move_rate,
                                        int(min_move_rate + (distance / aim_range) * (max_move_rate - min_move_rate))
                                    )
                                )
                                move_interval = 1.0 / adjusted_move_rate

                                # 判断是否应该移动鼠标
                                target_is_within_range = last_distance < aim_range

                                lockKey_pressed = win32api.GetKeyState(lockKey) & 0x8000
                                shift_pressed = win32api.GetKeyState(win32con.VK_SHIFT) & 0x8000
                                xbutton2_pressed = win32api.GetKeyState(0x05) & 0x8000  # 鼠标侧键

                                # 判断是否应该移动鼠标
                                should_move = aimbot_switch and target_is_within_range and (
                                        (lockKey_pressed) or
                                        (mouse_Side_Button_Witch and xbutton2_pressed)
                                )
                                if should_move:
                                    # 只在间隔时间足够时移动鼠标
                                    time_since_last_move = current_time - last_move_time
                                    if time_since_last_move >= move_interval:
                                        # 移动鼠标
                                        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, scaled_move_x, scaled_move_y, 0,
                                                             0)
                                        # 更新上次移动的时间
                                        last_move_time = current_time
                                        # print(f"衰减阶段鼠标移动: X={scaled_move_x}, Y={scaled_move_y}")
                        else:
                            # 衰减完成，停止移动
                            decaying = False
                            last_move_x = 0
                            last_move_y = 0
                            # print("衰减完成，停止移动")

            # 防止 CPU 占用过高，添加短暂的睡眠
            # time.sleep(0.001)
    except KeyboardInterrupt:
        pass
    finally:
        box_shm.close()


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
        self.app = QtWidgets.QApplication(sys.argv)
        self.window = uic.loadUi(Root / "data" / "RookieAiWindow.ui") # type: ignore # 加载UI文件
        assert self.window is not None
        self.window.setWindowTitle("YOLO识别系统")  # 设置窗口名称
        self.window.setWindowIcon(QIcon(str(Root / "data" / "ico" / "ultralytics-botAvatarSrcUrl-1729379860806.png")))  # type: ignore  # 替换为图标文件路径
        # self.window.resize(1290, 585)  # 设置窗口的大小
        self.window.setFixedSize(1290, 585)  # 如果需要固定窗口大小，可以使用 setFixedSize

        # 连接控制组件
        self.window.OpVideoButton.clicked.connect(self.toggle_video_button)  # 连接按钮点击信号到打开视频信号的槽

        # 连接 OpYoloButton 的点击信号到 toggle_YOLO_button 方法
        self.window.OpYoloButton.clicked.connect(self.toggle_YOLO_button)

        # 连接settingsButton按钮，显示设置按钮
        self.window.settingsYoloButton.clicked.connect(self.show_settings)
        self.window.closeYoloSettingsButton.clicked.connect(self.hide_settings)

        # 连接保存按钮
        self.window.saveButton.clicked.connect(self.save_settings)

        # 连接窗口置顶复选框状态改变信号
        self.window.topWindowCheckBox.stateChanged.connect(self.update_window_on_top_state)

        # 连接 解锁窗口大小 复选框状态改变信号
        self.window.unlockWindowSizeCheckBox.stateChanged.connect(self.update_unlock_window_size)

        # 连接 resetSizeButton 的点击信号到槽函数
        self.window.resetSizeButton.clicked.connect(self.reset_window_size)

        # 连接模型选择按钮
        self.window.chooseModelButton.clicked.connect(self.choose_model)

        # 连接重启按钮
        self.window.RestartButton.clicked.connect(self.restart_application)

        # 连接 重新加载模型 按钮 change_yolo_model
        self.window.reloadModelButton.clicked.connect(self.change_yolo_model)

        # 连接 detectionTargetComboBox 的信号到槽函数
        self.window.detectionTargetComboBox.currentTextChanged.connect(self.on_detection_target_changed)

        # 连接 aimBotCheckBox 的状态变化信号
        self.window.aimBotCheckBox.stateChanged.connect(self.on_aimBotCheckBox_state_changed)

        # 连接 sideButtonCheckBox 的状态变化信号
        self.window.sideButtonCheckBox.stateChanged.connect(self.on_sideButtonCheckBox_state_changed)

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
            frame.move((i - self.current_frame_index) * frame.width(), frame.y())
        # 连接按钮点击事件，并传递对应的目标框架索引
        self.window.advancedSettingsPushButton.clicked.connect(lambda: self.move_to_frame(0))
        self.window.basicSettingsPushButton.clicked.connect(lambda: self.move_to_frame(1))
        self.window.softwareInformationPushButton.clicked.connect(lambda: self.move_to_frame(2))
        # 连接动画组的 finished 信号
        self.animation_group.finished.connect(self.on_animation_finished)

        '''参数选项文字 动画'''
        # 连接按钮点击事件
        self.window.basicSettingsPushButton.clicked.connect(lambda: self.on_item_button_clicked("basic"))
        self.window.advancedSettingsPushButton.clicked.connect(lambda: self.on_item_button_clicked("advanced"))
        self.window.softwareInformationPushButton.clicked.connect(lambda: self.on_item_button_clicked("software"))
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
        self.window.confSlider.valueChanged.connect(self.on_slider_value_changed)

        # 初始化滑动条发送定时器
        self.slider_update_timer = QTimer()
        self.slider_update_timer.setInterval(200)  # 设置200ms的间隔
        self.slider_update_timer.timeout.connect(self.send_update)

        # 初始化滑动条状态变量
        self.is_slider_pressed = False

        # 设置 瞄准速度 滑动条
        self.window.lockSpeedHorizontalSlider.setMaximum(100)
        self.window.lockSpeedHorizontalSlider.setMinimum(0)

        # 连接滑动条信号(lockspeed)
        self.window.lockSpeedHorizontalSlider.sliderPressed.connect(self.on_lockSpeed_slider_pressed)
        self.window.lockSpeedHorizontalSlider.sliderMoved.connect(self.on_lockSpeed_slider_moved)
        self.window.lockSpeedHorizontalSlider.sliderReleased.connect(self.on_lockSpeed_slider_released)
        self.window.lockSpeedHorizontalSlider.valueChanged.connect(self.on_lockSpeed_slider_value_changed)

        # 初始化滑动条发送定时器(lockspeed)
        self.slider_update_timer_lockSpeed = QTimer()
        self.slider_update_timer_lockSpeed.setInterval(200)  # 设置200ms的间隔
        self.slider_update_timer_lockSpeed.timeout.connect(self.send_lockSpeed_update)

        # 初始化滑动条状态变量(lockspeed)
        self.is_slider_pressed_lockSpeed = False

        # 初始化 aimRange 滑动条(aim_range)
        self.window.aimRangeHorizontalSlider.setMinimum(0)  # 滑块的实际范围是 0 到 280
        self.window.aimRangeHorizontalSlider.setMaximum(280)

        # 连接滑动条信号(aim_range)
        self.window.aimRangeHorizontalSlider.sliderPressed.connect(self.on_aimRange_slider_pressed)
        self.window.aimRangeHorizontalSlider.sliderMoved.connect(self.on_aimRange_slider_moved)
        self.window.aimRangeHorizontalSlider.sliderReleased.connect(self.on_aimRange_slider_released)
        self.window.aimRangeHorizontalSlider.valueChanged.connect(self.on_aimRange_slider_value_changed)

        # 初始化滑动条发送定时器(aim_range)
        self.aimRange_slider_update_timer = QTimer()
        self.aimRange_slider_update_timer.setInterval(200)  # 设置 200ms 的间隔
        self.aimRange_slider_update_timer.timeout.connect(self.send_aimRange_update)

        # 初始化滑动条状态变量(aim_range)
        self.is_aimRange_slider_pressed = False

        # 初始化遮罩透明度效果
        self.window.overlay_opacity = QGraphicsOpacityEffect(self.window.overlay)
        self.window.overlay.setGraphicsEffect(self.window.overlay_opacity)
        self.window.overlay_animation = QPropertyAnimation(self.window.overlay_opacity, b"opacity") # type: ignore

        # 初始隐藏设置面板，并将其移动到屏幕左侧外
        self.window.settingsPanel.hide()
        self.window.settingsPanel.move(-self.window.settingsPanel.width(), self.window.settingsPanel.y())
        self.window.overlay.hide()
        self.window.overlay.setGeometry(0, 0, self.window.width(), self.window.height())

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

    def on_sideButtonCheckBox_state_changed(self, state):
        # 判断复选框是否被选中
        is_checked = (state == 2)  # 检查是否是 PartiallyChecked 或 Checked
        if state == 0:
            is_checked = False  # 如果是 Unchecked，则为 False
        elif state == 1:
            is_checked = True  # 如果是 Checked，则为 True

        # 发送信号到 mouseMoveProssesSignal_queue
        self.mouseMoveProssesSignal_queue.put(("mouse_Side_Button_Witch_change", is_checked))
        print(f"sideButtonCheckBox 状态变化: {is_checked}")

    def on_aimBotCheckBox_state_changed(self, state):
        """处理 aimBotCheckBox 状态变化的槽函数。"""
        # 判断复选框是否被选中
        is_checked = (state == 2)  # 检查是否是 PartiallyChecked 或 Checked
        if state == 0:
            is_checked = False  # 如果是 Unchecked，则为 False
        elif state == 1:
            is_checked = True  # 如果是 Checked，则为 True

        # 发送信号到 mouseMoveProssesSignal_queue
        self.mouseMoveProssesSignal_queue.put(("aimbot_switch_change", is_checked))
        print(f"aimBotCheckBox 状态变化: {is_checked}")

    def on_detection_target_changed(self, selected_class):
        """
        当 detectionTargetComboBox 的选项改变时调用。

        参数:
        - selected_class: 选中的类别 (0, 1, 2, 或 "ALL")
        """
        print(f"选择的检测类别: {selected_class}")
        self.information_output_queue.put(("UI_process_log", f"选择的检测类别: {selected_class}")) # type: ignore

        # 发送类别更改信号到 YOLO 处理进程
        self.YoloSignal_queue.put(("change_class", selected_class)) # type: ignore

    '''瞄准范围 滑动条'''
    def on_aimRange_slider_value_changed(self, value):
        """当 aimRange 滑动条的值改变时调用"""
        # 将滑块的值映射到 20-300 范围
        mapped_value = 20 + value
        self.window.aimRangeLcdNumber.display(mapped_value) # type: ignore
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
        self.window.aimRangeLcdNumber.display(mapped_value) # type: ignore
        self.aim_range = mapped_value  # 更新 aimRange 值

    def on_aimRange_slider_released(self):
        """当用户释放 aimRange 滑动条时调用"""
        self.is_aimRange_slider_pressed = False
        # 定时器将在发送最后一次值后停止

    def send_aimRange_update(self):
        """每 200ms 发送一次最新的 aimRange 值"""
        self.mouseMoveProssesSignal_queue.put(("aim_range_change", self.aim_range))
        self.YoloSignal_queue.put(("aim_range_change", self.aim_range)) # type: ignore
        print(f"定时发送 aimRange 更新信号: {self.aim_range}")
        if not self.is_aimRange_slider_pressed:
            # 用户已停止拖动滑动条，停止定时器
            self.aimRange_slider_update_timer.stop()

    '''lockSpeed 滑动条'''
    def on_lockSpeed_slider_value_changed(self, value):
        """当 lockSpeed 滑动条的值改变时调用"""
        value = value / 100  # 将值缩放到 [0, 1] 范围
        self.window.lockSpeedLcdNumber.display(f"{value:.2f}") # type: ignore  # 在 LCD 上显示两位小数的值
        self.lock_speed = value  # 更新锁定速度
        # 如果定时器未启动，启动定时器
        if not self.slider_update_timer_lockSpeed.isActive():
            self.slider_update_timer_lockSpeed.start()

    def on_lockSpeed_slider_pressed(self):
        """当用户开始拖动 lockSpeed 滑动条时调用"""
        self.is_slider_pressed_lockSpeed = True
        self.slider_update_timer_lockSpeed.start()  # 开始定时器

    def on_lockSpeed_slider_moved(self, value):
        """当 lockSpeed 滑动条被拖动时调用"""
        value = value / 100  # 将值缩放到 [0, 1] 范围
        self.window.lockSpeedLcdNumber.display(f"滑动条的值: {value:.2f}") # type: ignore  # 在 LCD 上显示实时的值
        self.lock_speed = value  # 更新锁定速度

    def on_lockSpeed_slider_released(self):
        """当用户释放 lockSpeed 滑动条时调用"""
        self.is_slider_pressed_lockSpeed = False
        # 定时器将在发送最后一次值后停止
        self.send_lockSpeed_update()

    def send_lockSpeed_update(self):
        """每200ms发送一次最新的 lockSpeed 值"""
        self.mouseMoveProssesSignal_queue.put(("aim_speed_change", self.lock_speed))  # 发送锁定速度到队列
        print(f"定时发送锁定速度更新信号: {self.lock_speed}")
        if not self.is_slider_pressed_lockSpeed:
            # 用户已停止拖动滑动条，停止定时器
            self.slider_update_timer_lockSpeed.stop()

    '''置信度滑动条'''
    def on_slider_value_changed(self, value):
        """当滑动条的值改变时调用"""
        value = value / 100
        self.window.confNumber.display(f"{value:.2f}") # type: ignore
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
        self.window.confNumber.display(f"滑动条的值: {value:.2f}") # type: ignore
        self.yolo_confidence = value  # 更新置信度值

    def on_slider_released(self):
        """当用户释放滑动条时调用"""
        self.is_slider_pressed = False
        # 定时器将在发送最后一次值后停止

    def send_update(self):
        """每200ms发送一次最新的置信度值"""
        self.YoloSignal_queue.put(("change_conf", self.yolo_confidence)) # type: ignore
        print(f"定时发送 YOLO 置信度更新信号: {self.yolo_confidence}")

        if not self.is_slider_pressed:
            # 用户已停止拖动滑动条，停止定时器
            self.slider_update_timer.stop()

    def restart_application(self):
        """重启当前应用程序。"""
        # 显示警告对话框
        reply = QMessageBox.warning(
            self.window, # type: ignore
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
        else:
            # 用户选择了“否”，取消重启操作
            pass

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
            self.process_videoprocessing.terminate() # type: ignore
            self.process_videoprocessing.join() # type: ignore
        # 关闭共享内存
        if hasattr(self, 'shm_video'):
            self.shm_video.close() # type: ignore
            self.shm_video.unlink() # type: ignore
        # 关闭应用程序
        self.app.quit()

    def load_settings(self):
        """加载配置文件 settings.json"""
        try:
            '''读取参数'''
            # 获取 "ProcessMode" 的状态
            self.ProcessMode = Config.get("ProcessMode", "single_process")
            print("ProcessMode状态:", self.ProcessMode)
            self.information_output_queue.put(("UI_process_log", f"ProcessMode状态: {self.ProcessMode}")) # type: ignore
            # 获取 "window_always_on_top" 的状态
            self.window_always_on_top =Config.get("window_always_on_top", False)
            print("窗口置顶状态:", self.window_always_on_top)
            # 获取 "model_file" 模型文件的路径
            self.model_file = Config.get("model_file", "yolo11n")
            print(f"读取模型文件路径: {self.model_file}")
            # 获取 YOLO 置信度设置
            yolo_confidence = Config.get('confidence', 0.5)  # 默认值为0.5
            self.yolo_confidence = yolo_confidence
            self.window.confSlider.setValue(int(yolo_confidence * 100)) # type: ignore  # 将置信度转换为滑动条值
            print(f"读取保存的YOLO置信度: {yolo_confidence}")
            # 获取 瞄准速度
            aim_speed = Config.get('lockSpeed', 0.5)
            self.aim_speed = aim_speed
            self.window.lockSpeedHorizontalSlider.setValue(int(aim_speed * 100)) # type: ignore
            print(f"读取保存的瞄准速度: {aim_speed}")
            # 获取 瞄准范围
            aim_range = Config.get('aim_range', 100)
            self.aim_range = aim_range
            self.window.aimRangeHorizontalSlider.setValue(int(aim_range)) # type: ignore
            print(f"读取保存的瞄准范围: {aim_range}")
            # 获取 Aimbot 开启状态
            aimbot_switch = Config.get("aimbot", False)
            self.window.aimBotCheckBox.setChecked(aimbot_switch) # type: ignore
            self.mouseMoveProssesSignal_queue.put(("aimbot_switch_change", aimbot_switch))
            print(f"读取自瞄状态: {aimbot_switch}")
            # 获取 侧键瞄准 开启状态
            mouse_Side_Button_Witch = Config.get("mouse_Side_Button_Witch", False)
            self.window.sideButtonCheckBox.setChecked(mouse_Side_Button_Witch) # type: ignore
            self.mouseMoveProssesSignal_queue.put(("mouse_Side_Button_Witch_change", mouse_Side_Button_Witch))
            print(f"读取侧键瞄准开启状态: {mouse_Side_Button_Witch}")
            # 获取 detectionTargetComboBox 的值
            target_class = Config.get('target_class', "ALL")
            print(f"读取保存的检测类别: {target_class}")
            self.window.detectionTargetComboBox.setCurrentText(target_class) # type: ignore
            self.YoloSignal_queue.put(("change_class", target_class)) # type: ignore

        except Exception as e:
            print("配置文件读取失败:", e)
            self.information_output_queue.put(("UI_process_log", f"配置文件读取失败: {e}")) # type: ignore
            self.settings = {}
            self.ProcessMode = "single_process"  # 设置默认值

    def save_settings(self):
        """保存当前设置到 settings.json 文件"""
        '''获取值'''
        # 获取当前 ProcessModeComboBox 的选项
        current_process_mode = self.choose_process_model_comboBox()
        # 获取当前 topWindowCheckBox 的状态
        current_window_on_top = self.window.topWindowCheckBox.isChecked() # type: ignore
        # 获取当前 detectionTargetComboBox 的选项
        current_target_class = self.window.detectionTargetComboBox.currentText() # type: ignore
        # 获取当前 aimBotCheckBox 的选项
        aimbot_switch = self.window.aimBotCheckBox.isChecked() # type: ignore
        # 获取当前 sideButtonCheckBox 的选项
        mouse_Side_Button_Witch = self.window.sideButtonCheckBox.isChecked() # type: ignore

        '''保存参数'''
        # 更新 settings 字典
        Config.update('ProcessMode', current_process_mode)                 # 推理模式
        Config.update('window_always_on_top', current_window_on_top)       # 窗口置顶状态
        Config.update('aimBot', aimbot_switch)                             # 自瞄开启状态
        Config.update('mouse_Side_Button_Witch', mouse_Side_Button_Witch)  # 侧键瞄准开启状态
        Config.update('model_file', self.model_file)                       # 模型文件路径
        Config.update('confidence', self.yolo_confidence)                  # 置信度
        Config.update('lockSpeed', self.lock_speed)                        # 锁定速度
        Config.update('aim_range', self.aim_range)                         # 瞄准范围
        Config.update('target_class', current_target_class)                # 目标代码

        # 将 settings 保存到文件
        #########################################
        #                                       #
        #   这些代码没用，因为update方法会自动保存   #
        #                                       #
        #########################################
        #try:
        #    with open('settings.json', 'w', encoding='utf-8') as f:
        #        json.dump(self.settings, f, ensure_ascii=False, indent=4)
        #    print("配置文件保存成功")
        #    self.information_output_queue.put(("UI_process_log", "配置文件保存成功"))
        #    self.window.status_widget.display_message("配置已保存", bg_color="#55ff00", text_color="black",
        #                                              auto_hide=3000)
        #except Exception as e:
        #    print("配置文件保存失败:", e)
        #    self.information_output_queue.put(("UI_process_log", f"配置文件保存失败: {e}"))
        #    self.window.status_widget.display_message("配置保存失败", bg_color="Red", text_color="white",
        #                                              auto_hide=3000)

    def init_ui_from_settings(self):
        """根据配置文件初始化界面"""
        # 设置 ProcessModeComboBox 的当前选项
        if self.ProcessMode == "single_process":
            self.window.ProcessModeComboBox.setCurrentText("单进程模式") # type: ignore
        elif self.ProcessMode == "multi_process":
            self.window.ProcessModeComboBox.setCurrentText("多进程模式") # type: ignore
        else:
            self.window.ProcessModeComboBox.setCurrentText("单进程模式") # type: ignore  # 默认值

        # 设置 topWindowCheckBox 的状态
        self.window.topWindowCheckBox.setChecked(self.window_always_on_top) # type: ignore
        # 根据设置，更新窗口置顶状态
        self.update_window_on_top_state()

    def update_window_on_top_state(self):
        """根据复选框状态更新窗口的置顶状态"""
        if self.window.topWindowCheckBox.isChecked(): # type: ignore
            self.window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True) # type: ignore
        else:
            self.window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False) # type: ignore
        self.window.show() # type: ignore  # 需要调用 show() 以应用窗口标志的更改

    def update_unlock_window_size(self):
        """根据复选框状态更新窗口大小锁定的状态"""
        if self.window.unlockWindowSizeCheckBox.isChecked(): # type: ignore
            # 解锁窗口大小：允许调整
            self.window.setFixedSize(QSize()) # type: ignore  # 移除固定大小限制
            self.window.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred) # type: ignore
            self.window.setMinimumSize(300, 400) # type: ignore  # 设置合理的最小尺寸，视具体需求调整
            self.window.setMaximumSize(QSize(16777215, 16777215)) # type: ignore  # 设置最大的尺寸限制
        else:
            # 锁定窗口大小：设置固定大小为当前尺寸
            self.window.setFixedSize(self.window.size()) # type: ignore
            self.window.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed) # type: ignore

    def reset_window_size(self):
        """重置窗口大小为 (1290, 585)"""
        target_size = QSize(1290, 585)

        if self.window.unlockWindowSizeCheckBox.isChecked(): # type: ignore
            # 如果窗口大小已解锁，直接调整窗口大小
            self.window.resize(target_size) # type: ignore
        else:
            # 如果窗口大小已锁定，设置固定大小为目标大小
            self.window.setFixedSize(target_size) # type: ignore

        # 如果需要在重置大小后更新大小策略，可以在这里进行
        if self.window.unlockWindowSizeCheckBox.isChecked(): # type: ignore
            self.window.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred) # type: ignore
        else:
            self.window.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed) # type: ignore

    def choose_process_model_comboBox(self):
        """选择进程模式"""
        ProcessMode = self.window.ProcessModeComboBox.currentText() # type: ignore  # 获取当前选项文本
        if ProcessMode == "单进程模式":
            return "single_process"
        elif ProcessMode == "多进程模式":
            return "multi_process"
        else:
            return "single_process"  # 默认返回单进程

    def apply_rounded_mask_to_show_video(self):
        """对 show_video 应用带圆角的遮罩"""
        radius = 20  # 设置圆角半径
        width = self.window.show_video.width() # type: ignore
        height = self.window.show_video.height() # type: ignore

        # 创建带圆角的遮罩
        mask = QBitmap(width, height)
        mask.fill(Qt.GlobalColor.color0)  # 使用 GlobalColor 中的 color0
        painter = QPainter(mask)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)  # 使用 RenderHint.Antialiasing
        painter.setBrush(Qt.GlobalColor.color1)  # 使用 GlobalColor 中的 color1
        painter.drawRoundedRect(0, 0, width, height, radius, radius)
        painter.end()

        # 将遮罩应用到 show_video
        self.window.show_video.setMask(mask) # type: ignore

    def update_button_text(self):
        """更新按钮文本"""
        if self.is_video_running:
            self.window.OpVideoButton.setText("关闭视频预览") # type: ignore
        else:
            self.window.OpVideoButton.setText("打开视频预览") # type: ignore

    def update_video_frame(self):
        """更新视频帧到QLabel"""
        frame = None  # 初始化 frame 为 None
        if not self.processedVideo_queue.empty(): # type: ignore
            # 清空队列，只保留最新的帧
            while not self.processedVideo_queue.empty(): # type: ignore
                frame = self.processedVideo_queue.get() # type: ignore

        # 如果 frame 为空，直接返回以跳过更新
        if frame is None:
            # print("未接收到视频帧，跳过更新")
            pass
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

        # 将帧转换为 QImage
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        # 绘制 FPS
        cv2.putText(frame, f'FPS: {self.fps:.1f}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
        # 更新 QLabel，保持等比填充
        pixmap = QPixmap.fromImage(q_img)
        pixmap = pixmap.scaled(self.window.show_video.size(), aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio, # type: ignore
                               transformMode=Qt.TransformationMode.SmoothTransformation)

        self.window.show_video.setPixmap(pixmap) # type: ignore

    def toggle_YOLO_button(self):
        """切换 YOLO 处理状态并更新按钮文本"""
        if self.is_yolo_running:
            # 停止 YOLO 处理
            self.YoloSignal_queue.put(('YOLO_stop', None)) # type: ignore
            self.window.OpYoloButton.setText("开启 YOLO") # type: ignore
            self.is_yolo_running = False
            print("YOLO 处理已停止。")
        else:
            # 开启 YOLO 处理
            self.YoloSignal_queue.put(('YOLO_start', None)) # type: ignore
            self.window.OpYoloButton.setText("关闭 YOLO") # type: ignore
            self.is_yolo_running = True
            print("YOLO 处理已启动。")

    def toggle_video_button(self):
        """切换视频状态并更新按钮文本"""
        # video_source = self.choose_process_model_comboBox()  # 通过选择器获取进程模式
        video_source = "screen"  # 视频源

        if self.is_video_running:
            print("关闭视频源:", video_source)
            self.window.OpVideoButton.setText("关闭视频显示中...") # type: ignore  # 更新按钮文本
            self.pipe_parent.send(('stop_video', video_source)) # type: ignore  # 发送停止视频信号
            self.window.status_widget.display_message("预览已关闭", bg_color="Yellow", text_color="black", # type: ignore
                                                      auto_hide=1500)
            # 启动清理定时器
            if not hasattr(self, 'clear_timer'):
                self.clear_timer = QTimer()
                self.clear_timer.timeout.connect(self.clear_video_display)
            self.clear_timer.start(100)  # 每100毫秒清理一次
            self.is_video_running = False  # 更新状态
        else:
            print("启动视频源:", video_source)
            self.window.OpVideoButton.setText("打开视频显示中...") # type: ignore  # 更新按钮文本
            self.pipe_parent.send(("start_video", video_source)) # type: ignore  # 发送启动视频信号
            self.window.status_widget.display_message("预览已开启", bg_color="#55ff00", text_color="black", # type: ignore
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
        start_pos = self.window.settingsPanel.pos() # type: ignore
        # 计算结束位置，使面板移出屏幕（左侧）
        end_pos = QPoint(-self.window.settingsPanel.width(), start_pos.y()) # type: ignore

        # 创建一个属性动画，控制设置面板的位置
        self.window.animation = QPropertyAnimation(self.window.settingsPanel, b"pos") # type: ignore
        self.window.animation.setDuration(500) # type: ignore  # 动画持续时间为 500 毫秒
        self.window.animation.setStartValue(start_pos) # type: ignore  # 动画开始位置
        self.window.animation.setEndValue(end_pos)  # type: ignore # 动画结束位置
        self.window.animation.setEasingCurve(QEasingCurve.Type.InQuad) # type: ignore  # 设置动画效果为缓入

        # 启动面板位置动画
        self.window.animation.start() # type: ignore

        # 设置遮罩动画属性
        self.window.overlay_animation.setDuration(500)  # type: ignore # 遮罩动画持续时间为 500 毫秒
        self.window.overlay_animation.setStartValue(1)  # type: ignore # 遮罩的初始透明度
        self.window.overlay_animation.setEndValue(0)  # type: ignore # 遮罩的结束透明度（完全透明）
        self.window.overlay_animation.setEasingCurve(QEasingCurve.Type.InQuad)  # type: ignore # 设置动画效果为缓入

        # 启动遮罩透明度动画
        self.window.overlay_animation.start() # type: ignore

        # 在面板隐藏动画完成后，隐藏面板并使主窗口可用
        self.window.animation.finished.connect(self.window.settingsPanel.hide) # type: ignore
        self.window.animation.finished.connect(lambda: ( # type: ignore
            self.window.settingsPanel.hide(), # type: ignore
            self.window.overlay.hide(),  # 隐藏遮罩 # type: ignore
            self.window.setEnabled(True) # type: ignore  # 使主窗口重新可用
        ))

    def show_settings(self):
        """显示设置面板和半透明遮罩"""

        # 显示遮罩组件
        self.window.overlay.show() # type: ignore

        # 设置遮罩动画属性
        self.window.overlay_animation.setDuration(500) # type: ignore  # 遮罩动画持续时间为 500 毫秒
        self.window.overlay_animation.setStartValue(0) # type: ignore  # 遮罩的初始透明度（完全透明）
        self.window.overlay_animation.setEndValue(1) # type: ignore  # 遮罩的结束透明度（完全不透明）
        self.window.overlay_animation.setEasingCurve(QEasingCurve.Type.OutQuad) # type: ignore  # 设置动画效果为缓出

        # 启动遮罩透明度动画
        self.window.overlay_animation.start() # type: ignore

        # 设置允许鼠标事件通过遮罩
        self.window.overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False) # type: ignore
        self.window.settingsPanel.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False) # type: ignore

        # 显示设置面板
        self.window.settingsPanel.show() # type: ignore

        # 获取当前设置面板的位置
        start_pos = self.window.settingsPanel.pos() # type: ignore
        # 计算结束位置，使面板从左侧进入屏幕
        end_pos = QPoint(0, start_pos.y())

        # 创建一个属性动画，控制设置面板的位置
        self.window.animation = QPropertyAnimation(self.window.settingsPanel, b"pos") # type: ignore
        self.window.animation.setDuration(500) # type: ignore  # 动画持续时间为 500 毫秒
        self.window.animation.setStartValue(start_pos) # type: ignore  # 动画开始位置
        self.window.animation.setEndValue(end_pos) # type: ignore  # 动画结束位置
        self.window.animation.setEasingCurve(QEasingCurve.Type.OutQuad) # type: ignore  # 设置动画效果为缓出

        # 启动面板位置动画
        self.window.animation.start() # type: ignore

    def disable_buttons(self):
        """禁用按钮，防止在动画进行时重复点击"""
        self.window.advancedSettingsPushButton.setEnabled(False) # type: ignore
        self.window.basicSettingsPushButton.setEnabled(False) # type: ignore
        self.window.softwareInformationPushButton.setEnabled(False) # type: ignore

    def enable_buttons(self):
        """启用按钮"""
        self.window.advancedSettingsPushButton.setEnabled(True) # type: ignore
        self.window.basicSettingsPushButton.setEnabled(True) # type: ignore
        self.window.softwareInformationPushButton.setEnabled(True) # type: ignore

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
            animation = QPropertyAnimation(frame, b"pos") # type: ignore
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
        basic_button = self.window.basicSettingsPushButton # type: ignore
        advanced_button = self.window.advancedSettingsPushButton # type: ignore
        software_button = self.window.softwareInformationPushButton # type: ignore
        red_line = self.window.redLine # type: ignore

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
        red_line_animation = QPropertyAnimation(red_line, b"geometry") # type: ignore
        red_line_animation.setDuration(duration)
        red_line_animation.setStartValue(red_line.geometry())
        target_red_line_geometry = QRect(target_button.x(), red_line.y(), target_button.width(), red_line.height()) # type: ignore
        red_line_animation.setEndValue(target_red_line_geometry)
        red_line_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        red_line_animation.start()
        self.item_animations.append(red_line_animation)

        # 移动按钮位置
        for button in all_buttons:
            button_animation = QPropertyAnimation(button, b"geometry") # type: ignore
            button_animation.setDuration(duration)
            button_animation.setStartValue(button.geometry())

            if button == target_button:
                # 被选中的按钮上移 5 像素
                target_geometry = QRect(button.x(), self.button_selected_y, button.width(), button.height())
            else:
                # 其他按钮回到默认 y 位置
                target_geometry = QRect(button.x(), self.button_default_y, button.width(), button.height())

            button_animation.setEndValue(target_geometry)
            button_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
            button_animation.start()
            self.item_animations.append(button_animation)

    def clear_video_display(self):
        """清空视频显示窗口直到清空干净"""
        if self.window.show_video.pixmap(): # type: ignore
            self.window.show_video.setPixmap(QPixmap()) # type: ignore  # 清空显示窗口
        else:
            self.clear_timer.stop()  # 停止定时器

    def change_yolo_model(self):
        """重新加载模型"""
        print("重新加载模型")
        # 检查模型文件路径是否为空
        if not getattr(self, 'model_file', None):  # 如果 model_file 属性不存在或为空
            log_msg = "未选择模型文件，无法重新加载模型。"
            self.window.status_widget.display_message(log_msg, bg_color="Red", text_color="black", auto_hide=6000) # type: ignore
            return  # 退出方法，不执行后续操作

        # 如果此时 视频预览 在开启状态，则进行关闭。
        if self.is_video_running:
            self.toggle_video_button()
        # 如果此时 YOLO推理 在开启状态，则进行关闭。
        if self.is_yolo_running:
            self.toggle_YOLO_button()

        if self.ProcessMode == "multi_process":
            # 发送更改模型信号 与 模型路径(多进程)
            self.YoloSignal_queue.put(("change_model", self.model_file)) # type: ignore
            self.information_output_queue.put(("UI_process_log", "向 YoloSignal_queue 发送 change_model")) # type: ignore
        else:
            # 发送更改模型信号 与 模型路径(单进程)
            self.videoSignal_queue.put(("change_model", self.model_file)) # type: ignore
            self.information_output_queue.put(("UI_process_log", "向 videoSignal_queue 发送 change_model")) # type: ignore

        # 显示模型已重新加载的消息
        self.window.status_widget.display_message("模型已重新加载", bg_color="#55ff00", text_color="black", # type: ignore
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
            self.window.modelFileLabel.setText(self.file_name)  # 更新UI中的标签文本 # type: ignore
            self.model_file = model_file  # 保存模型文件路径到类属性
            print(f"选择的模型文件: {self.file_name}")

    def show(self):
        """显示窗口"""
        self.window.show() # type: ignore

        self.show_loading_animation()  # 显示加载信息悬浮窗

        self.show_log_output()  # 开启 调试信息 输出监听

        # 更新 modelFileLabel 显示的模型名称
        file_name = os.path.basename(self.model_file)  # 只提取文件名和后缀 # type: ignore
        self.window.modelFileLabel.setText(file_name)  # 更新UI中的标签文本 # type: ignore

        # 发送最新 置信度
        self.YoloSignal_queue.put(("change_conf", self.yolo_confidence)) # type: ignore

        self.information_output_queue.put(("UI_process_log", "UI主进程 初始化完毕")) # type: ignore

        sys.exit(self.app.exec())

    def show_loading_animation(self):
        # 提示加载信息框
        self.window.status_widget.show_status_widget("加载中...", bg_color="Yellow", text_color="black") # type: ignore

        # 创建定时器，用来周期性地检查队列
        self.timer_check_queue = QTimer(self.window)  # 将 self.window 作为 QTimer 的父对象
        self.timer_check_queue.timeout.connect(self.check_floating_information_signal_queue)
        self.timer_check_queue.start(500)  # 每100毫秒检查一次队列

    def check_floating_information_signal_queue(self):
        """检查 floating_information_signal_queue 是否有加载完毕的信号"""
        if not self.floating_information_signal_queue.empty(): # type: ignore
            message = self.floating_information_signal_queue.get_nowait()  # 非阻塞地获取消息 # type: ignore
            if message[0] == "loading_complete" and message[1] is True:
                print("软件初始化完毕，停止检查队列")
                # 停止定时器检查队列
                # self.timer_check_queue.stop()
                # 更新UI或执行其他操作
                self.window.status_widget.display_message("加载完毕", bg_color="#55ff00", text_color="black", # type: ignore
                                                          auto_hide=3000)
            elif message[0] == "error_log":
                self.window.status_widget.display_message(message[1], bg_color="Yellow", text_color="black", # type: ignore
                                                          auto_hide=3000)
            elif message[0] == "red_error_log":
                self.window.status_widget.show_status_widget(message[1], bg_color="Red", text_color="black") # type: ignore

    def show_log_output(self):
        """调试信息输出 计时循环"""
        print("调试信息输出 监听信号...")
        self.timer_check_information_output_queue = QTimer(self.window)
        self.timer_check_information_output_queue.timeout.connect(self.log_output)
        self.timer_check_information_output_queue.start(100)

    def log_output(self):
        """调试信息输出"""
        if not self.information_output_queue.empty(): # type: ignore
            message = self.information_output_queue.get_nowait() # type: ignore
            print("information_output_queue 队列接收信息:", message)

            if message[0] == "UI_process_log":  # UI主进程 调试信息输出
                log_msg = message[1]

                if not isinstance(log_msg, str):
                    log_msg = str(log_msg)

                self.window.log_output_00.append(f"[INFO]UI主进程 日志: {log_msg}") # type: ignore
                self.window.log_output_00.ensureCursorVisible() # type: ignore

            if message[0] == "log_output_main":  # 主通信进程 调试信息输出
                log_msg = message[1]  # 提取信息段

                # 确保 log_msg 是字符串类型
                if not isinstance(log_msg, str):
                    log_msg = str(log_msg)  # 如果不是字符串类型，则转换为字符串

                self.window.log_output_01.append(f"[INFO]通信进程 收到信号: {log_msg}")  # 添加新的日志信息 # type: ignore
                self.window.log_output_01.ensureCursorVisible()  # 确保光标可见 # type: ignore

            if message[0] == "video_processing_log":  # 视频处理进程 调试信息输出
                log_msg = message[1]

                if not isinstance(log_msg, str):
                    log_msg = str(log_msg)

                self.window.log_output_02.append(f"[INFO]视频处理进程 收到信号: {log_msg}") # type: ignore
                self.window.log_output_02.ensureCursorVisible() # type: ignore

            if message[0] == "video_signal_acquisition_log":  # 视频信号接收进程 调试信息输出
                log_msg = message[1]
                operate, signal_source = log_msg

                if not isinstance(log_msg, str):
                    log_msg = str(log_msg)

                self.window.log_output_03.append(f"[INFO]动作: {operate}  信号源: {signal_source}") # type: ignore
                self.window.log_output_03.ensureCursorVisible() # type: ignore

            if message[0] == "error_log":  # 报错信息提示
                log_msg = message[1]

                if not isinstance(log_msg, str):
                    log_msg = str(log_msg)

                self.window.status_widget.display_message(log_msg, bg_color="Red", text_color="black", auto_hide=6000) # type: ignore

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
        information_output_queue.put(("UI_process_log", f"共享内存已创建，名称为 {shm_video_name}"))
        information_output_queue.put(("UI_process_log", f"Box共享内存已创建，名称为 {box_shm.name}"))

        '''创建进程'''
        # 1.进程通信进程
        process_signal_processing = Process(target=communication_Process,
                                            args=(self.pipe_child, self.videoSignal_queue, self.videoSignal_stop_queue,
                                                  self.floating_information_signal_queue,
                                                  self.information_output_queue,))
        process_signal_processing.daemon = True
        process_signal_processing.start()
        self.information_output_queue.put(("UI_process_log", "process_signal_processing 进程创建完毕"))

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
                box_shm.name, box_data_event, box_lock
            )
        else:
            raise ValueError(f"未知的 ProcessMode: {self.ProcessMode}")
        # 创建并启动进程
        process_video_signal = Process(target=target_function, args=args)
        process_video_signal.daemon = True  # 设置为守护进程
        process_video_signal.start()
        self.information_output_queue.put(("UI_process_log", "process_video_signal 进程创建完毕"))

        # 3.视频处理进程(仅在多进程时启动)
        if self.ProcessMode == "multi_process":
            process_videoprocessing = Process(target=video_processing,
                                              args=(shm_video_name, frame_shape, frame_dtype,
                                                    frame_available_event, processedVideo_queue,
                                                    YoloSignal_queue, parent_conn,
                                                    information_output_queue, self.model_file,
                                                    box_shm.name, box_data_event, box_lock))
            process_videoprocessing.daemon = True
            process_videoprocessing.start()
            information_output_queue.put(("UI_process_log", "process_videoprocessing 进程创建完毕"))

        # 4.鼠标移动进程
        process_mouse_move = Process(target=mouse_move_prosses,
                                     args=(box_shm.name, box_lock, self.mouseMoveProssesSignal_queue))
        process_mouse_move.daemon = True
        process_mouse_move.start()
        self.information_output_queue.put(("UI_process_log", "process_mouse_move 进程创建完毕"))

        # 启动进程后，保存引用
        self.process_signal_processing = process_signal_processing
        self.process_video_signal = process_video_signal

        '''显示软件页面'''
        self.show()  # 初始化完毕 显示 UI窗口


if __name__ == '__main__':
    multiprocessing.freeze_support()
    app = RookieAiAPP()
    app.main()
