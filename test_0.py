import cv2
import mss
import os

# 屏幕捕获初始化
with mss.mss() as sct:
    # 设置捕获区域，这里是整个屏幕
    monitor = sct.monitors[1]  # 选择第二个显示器，根据你的实际情况调整
    screen_capture = {'top': monitor["top"], 'left': monitor["left"], 'width': monitor["width"], 'height': monitor["height"]}

    # 创建 OpenCV 窗口
    cv2.namedWindow("Screen Capture", cv2.WINDOW_NORMAL)

    while True:
        # 获取屏幕帧
        screenshot_filename = sct.shot(output='numpy')

        # 检查截图文件是否存在
        if os.path.exists(screenshot_filename):
            # 读取截图文件为图像
            screenshot = cv2.imread(screenshot_filename)

            # 检查图像是否有效
            if screenshot is not None and screenshot.any():
                # 显示屏幕帧
                cv2.imshow("Screen Capture", screenshot)

            # 删除截图文件
            os.remove(screenshot_filename)

        # 检测键盘输入，按 'q' 键退出循环
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# 释放资源
cv2.destroyAllWindows()
