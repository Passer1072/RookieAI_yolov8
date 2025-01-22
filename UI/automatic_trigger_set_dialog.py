# automatic_trigger_set_dialog.py

import sys
from PyQt6 import QtWidgets, uic
from PyQt6.QtWidgets import QDialog
from PyQt6.QtGui import QIcon
from pathlib import Path

Root = Path(__file__).parent


class AutomaticTriggerSetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.autoTiggerRangeNumber = None
        self.autoTiggerRangeSlider = None
        self.buttonGroup = None
        uic.loadUi(Root / 'automaticTrigger_set.ui', self)
        self.setWindowTitle("自动扳机设置")
        self.setWindowIcon(QIcon(str(Root / "ico" / "ultralytics-botAvatarSrcUrl-1729379860806.png")))
        self.setFixedSize(400, 300)  # 根据需要设置窗口大小

    def closeEvent(self, event):
        """重写关闭事件，只隐藏窗口而不关闭"""
        event.ignore()
        self.hide()
