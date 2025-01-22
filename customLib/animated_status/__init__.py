from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QPoint, Qt, QTimer
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QVBoxLayout

class AnimatedStatus:
    def __init__(self, window, widget_name: str, label_name: str):
        """
        初始化 AnimatedStatus，并允许用户指定自定义的 Widget 和 Label 名称。

        :param window: 父窗口
        :param widget_name: 自定义的状态提示浮窗 Widget 名称
        :param label_name: 自定义的状态提示文本 Label 名称
        """
        self.window = window
        self.status_widget = getattr(window, widget_name)
        self.status_label = getattr(window, label_name)

        # 初始化布局并将自定义的 Label 居中放置在自定义的 Widget 中
        layout = QVBoxLayout(self.status_widget)
        layout.addWidget(self.status_label)
        layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        layout.setAlignment(self.status_label, Qt.AlignmentFlag.AlignCenter)  # 居中对齐

        # 初始化QTimer，用于自动隐藏
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)  # 只触发一次
        self.hide_timer.timeout.connect(self.hide_status_widget)

    def display_message(self, message, bg_color="lightblue", text_color="black", font_size=14,
                        padding=(5, 10, 5, 10), auto_hide=3000):
        """
        快捷显示带动画的状态提示消息，并在指定时间后自动隐藏。

        :param message: 显示的消息文本
        :param bg_color: 背景颜色，默认浅蓝
        :param text_color: 文本颜色，默认黑色
        :param font_size: 文本字体大小，默认14
        :param padding: 文本内边距（上、右、下、左），默认为(5, 10, 5, 10)
        :param auto_hide: 自动隐藏的倒计时时长（毫秒），默认3000毫秒
        """
        # 调用show_status_widget并自动设置auto_hide
        self.show_status_widget(message, bg_color, text_color, font_size, padding, auto_hide)

    def show_status_widget(self, message, bg_color, text_color, font_size=14, padding=(5, 10, 5, 10), auto_hide=None):
        """
        显示状态提示浮窗的动画效果（位置移动和淡入效果）

        :param message: 显示的消息文本
        :param bg_color: 背景颜色
        :param text_color: 文本颜色
        :param font_size: 文本字体大小，默认14
        :param padding: 文本内边距（上、右、下、左），默认为(5, 10, 5, 10)
        :param auto_hide: 自动隐藏的倒计时时长（毫秒），默认不自动隐藏
        """
        # 设置消息提示浮窗的文本
        self.status_label.setText(message)
        # 设置背景颜色和文本颜色，同时保留圆角效果
        self.status_widget.setStyleSheet(
            f"background-color: {bg_color}; border-radius: 20px;"
        )

        # 设置文本颜色、字体大小、内边距
        top, right, bottom, left = padding
        self.status_label.setStyleSheet(
            f"color: {text_color}; font-size: {font_size}px; "
            f"padding: {top}px {right}px {bottom}px {left}px;"
        )

        # 获取文本的宽度
        font_metrics = self.status_label.fontMetrics()
        text_width = font_metrics.horizontalAdvance(message)

        # 设置 status_label 的固定宽度，确保最小宽度为 130
        label_width = max(text_width + 20, 130)
        self.status_label.setFixedWidth(label_width)

        # 设置 status_widget 的固定宽度，确保最小宽度为 210
        widget_width = max(text_width + 35, 210)
        self.status_widget.setFixedWidth(widget_width)

        # 获取窗口的几何信息
        window_geometry = self.window.geometry()
        widget_width = self.status_widget.width()

        # 创建位置动画，控制 status_widget 的位置
        self.status_display_widget_animation = QPropertyAnimation(self.status_widget, b"pos")

        # 设置起始位置（窗口上边框外部 50 像素）
        start_position = QPoint(
            (window_geometry.width() - widget_width) // 2,  # 水平居中
            -50  # 位于窗口上方 50 像素
        )
        # 设置结束位置（向下移动 80 像素）
        end_position = QPoint(
            (window_geometry.width() - widget_width) // 2,
            start_position.y() + 80
        )

        # 设置位置动画的起始值和结束值
        self.status_display_widget_animation.setStartValue(start_position)
        self.status_display_widget_animation.setEndValue(end_position)
        self.status_display_widget_animation.setDuration(500)  # 动画持续时间为 0.5 秒
        self.status_display_widget_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        # 创建透明度动画，控制淡入效果
        self.status_display_widget_opacity = QGraphicsOpacityEffect(self.status_widget)
        self.status_widget.setGraphicsEffect(self.status_display_widget_opacity)

        self.opacity_animation = QPropertyAnimation(self.status_display_widget_opacity, b"opacity")
        self.opacity_animation.setStartValue(0.0)  # 起始透明度为 0（完全透明）
        self.opacity_animation.setEndValue(1.0)  # 结束透明度为 1（完全不透明）
        self.opacity_animation.setDuration(500)  # 动画持续时间为 0.5 秒

        # 显示组件（初始为不可见状态，确保淡入效果生效）
        self.status_widget.show()

        # 启动动画
        self.status_display_widget_animation.start()
        self.opacity_animation.start()

        # 设置自动隐藏倒计时
        if auto_hide:
            self.hide_timer.start(auto_hide)

    def hide_status_widget(self):
        """用于隐藏 status_widget 的动画效果（位置移动和淡出效果）"""

        # 获取窗口的几何信息
        window_geometry = self.window.geometry()
        widget_width = self.status_widget.width()

        # 创建位置动画，控制 status_widget 的位置
        self.status_display_widget_animation = QPropertyAnimation(self.status_widget, b"pos")

        # 设置起始位置（当前显示位置）
        start_position = QPoint(
            (window_geometry.width() - widget_width) // 2,
            30  # 与 show_status_widget 的结束位置相同
        )

        # 设置结束位置（移动到窗口上方不可见位置）
        end_position = QPoint(
            (window_geometry.width() - widget_width) // 2,
            start_position.y() - 50  # 向上移动 80 像素
        )

        # 设置位置动画的起始值和结束值
        self.status_display_widget_animation.setStartValue(start_position)
        self.status_display_widget_animation.setEndValue(end_position)
        self.status_display_widget_animation.setDuration(500)  # 动画持续时间为 0.5 秒
        self.status_display_widget_animation.setEasingCurve(QEasingCurve.Type.InQuad)

        # 创建透明度动画，控制淡出效果
        self.status_display_widget_opacity = QGraphicsOpacityEffect(self.status_widget)
        self.status_widget.setGraphicsEffect(self.status_display_widget_opacity)

        self.opacity_animation = QPropertyAnimation(self.status_display_widget_opacity, b"opacity")
        self.opacity_animation.setStartValue(1.0)  # 起始透明度为 1（完全不透明）
        self.opacity_animation.setEndValue(0.0)  # 结束透明度为 0（完全透明）
        self.opacity_animation.setDuration(450)  # 动画持续时间为 0.5 秒

        # 启动动画
        self.status_display_widget_animation.start()
        self.opacity_animation.start()

        # 动画结束后隐藏组件并清空文本
        def on_animation_finished():
            self.status_widget.hide()
            self.status_label.setText("")  # 清空 status_label 的文本

        # 将动画结束信号连接到清理函数
        self.status_display_widget_animation.finished.connect(on_animation_finished)
