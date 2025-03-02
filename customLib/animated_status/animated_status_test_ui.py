"""
带动画的 状态提示浮窗 库使用示例
"""

import sys
from PyQt6 import QtWidgets, uic
from customLib.animated_status import AnimatedStatus  # 导入 带动画的状态提示浮窗 库


class TestUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('animated_status_test_ui.ui', self)  # 加载 UI 文件

        # 初始化 AnimatedStatus，将 TestUI 实例作为窗口参数传递，指定Widget和Label名称
        self.status_widget = AnimatedStatus(window=self,
                                            widget_name="statusDisplayWidget",
                                            label_name="statusDisplayLabel")

        # 设置按钮事件
        self.showButton.clicked.connect(self.show_status_message)
        self.hideButton.clicked.connect(self.hide_status_message)
        self.quickCall.clicked.connect(self.quick_call_display_message)  # 连接quickCall按钮

    def show_status_message(self):
        """显示带动画效果的状态提示"""
        self.status_widget.show_status_widget("显示中的提示信息", bg_color="Yellow", text_color="black")

    def hide_status_message(self):
        """隐藏带动画效果的状态提示"""
        self.status_widget.hide_status_widget()

    def quick_call_display_message(self):
        """使用 display_message 快捷方法显示提示信息并自动隐藏"""
        self.status_widget.display_message("快捷调用成功！", bg_color="green", text_color="white", auto_hide=2000)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = TestUI()
    window.show()
    sys.exit(app.exec())
