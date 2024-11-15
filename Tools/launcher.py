import sys
import asyncio
from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, QSize, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QWidget,
)


class LauncherAPP(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName("MainWindow")
        MainWindow.resize(382, 283)
        MainWindow.setMaximumSize(QSize(382, 283))
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.checkBox = QCheckBox(self.centralwidget)
        self.checkBox.setObjectName("checkBox")
        self.checkBox.setGeometry(QRect(296, 10, 86, 19))
        self.checkBox.setChecked(True)
        self.textBrowser = QTextBrowser(self.centralwidget)
        self.textBrowser.setObjectName("textBrowser")
        self.textBrowser.setGeometry(QRect(0, 74, 382, 208))
        self.textBrowser.setMinimumSize(QSize(0, 200))
        self.progressBar = QProgressBar(self.centralwidget)
        self.progressBar.setObjectName("progressBar")
        self.progressBar.setGeometry(QRect(0, 46, 382, 22))
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)
        self.progressBar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pushButton = QPushButton(self.centralwidget)
        self.pushButton.setObjectName("pushButton")
        self.pushButton.setGeometry(QRect(0, 0, 100, 40))
        self.pushButton.setMinimumSize(QSize(100, 40))
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(
            QCoreApplication.translate("MainWindow", "MainWindow", None)
        )
        self.checkBox.setText(
            QCoreApplication.translate(
                "MainWindow", "\u4f7f\u7528\u955c\u50cf\u6e90", None
            )
        )
        self.pushButton.setText(
            QCoreApplication.translate("MainWindow", "\u4e00\u952e\u5b89\u88c5", None)
        )


class InstallationError(Exception):
    pass


async def install_requirements(launcher_app):
    import asyncio

    if launcher_app.checkBox.isChecked():
        process = await asyncio.create_subprocess_exec(
            "pip",
            "install",
            "-r",
            "requirements.txt",
            "-i",
            "https://pypi.doubanio.com/simple/",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    else:
        process = await asyncio.create_subprocess_exec(
            "pip",
            "install",
            "-r",
            "requirements.txt",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_message = stderr.decode().strip() if stderr else "未知错误"
        raise InstallationError(f"(code: {process.returncode})\n\t{error_message}")


async def start_app(launcher_app):
    import subprocess

    subprocess.Popen(["python", "RookieAI.py"])


async def install_torch(launcher_app):
    import asyncio

    if launcher_app.checkBox.isChecked():
        process = await asyncio.create_subprocess_exec(
            "pip",
            "install",
            "torch",
            "torchvision",
            "torchaudio",
            "-f",
            "https://mirror.sjtu.edu.cn/pytorch-wheels/torch_stable.html",
            "--no-index",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    else:
        process = await asyncio.create_subprocess_exec(
            "pip",
            "install",
            "torch",
            "torchvision",
            "torchaudio",
            "-f",
            "https://download.pytorch.org/whl/torch_stable.html",
            "--no-index",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_message = stderr.decode().strip() if stderr else "未知错误"
        raise InstallationError(f"(code: {process.returncode})\n\t{error_message}")


def update_progress(launcher_app, step_increment):
    launcher_app.progressBar.setValue(
        min(launcher_app.progressBar.value() + step_increment, 100)
    )


async def exec_install_async(launcher_app):
    launcher_app.textBrowser.clear()
    launcher_app.textBrowser.append(f"RookieAI v{VERSION} 安装程序\n")
    launcher_app.progressBar.setValue(0)
    launcher_app.pushButton.setEnabled(False)
    launcher_app.textBrowser.append("开始执行安装操作...\n")

    total_steps = 100
    increment_fast = 40  # 快速增加的步长
    increment_slow = 40  # 慢速增加的步长

    try:
        launcher_app.textBrowser.append("正在安装requirements.txt\n")
        await install_requirements(launcher_app)
        update_progress(launcher_app, increment_fast)
        launcher_app.textBrowser.append("安装requirements.txt完成\n")

        launcher_app.textBrowser.append("正在安装torch torchvision torchaudio\n")
        await install_torch(launcher_app)
        update_progress(launcher_app, increment_slow)
        launcher_app.textBrowser.append("安装torch torchvision torchaudio完成。\n")

        launcher_app.textBrowser.append("依赖已全部安装，准备启动主程序\n")
        launcher_app.progressBar.setValue(total_steps)
        await start_app(launcher_app)

    except Exception as e:
        launcher_app.textBrowser.append(f"安装过程中发生错误: {e}\n")
    finally:
        launcher_app.progressBar.setValue(0)
        launcher_app.pushButton.setEnabled(True)


def exec_install(launcher_app):
    asyncio.run(exec_install_async(launcher_app))


VERSION = "0.1.0"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = QMainWindow()
    launcher_app = LauncherAPP()
    launcher_app.setupUi(main_window)
    launcher_app.pushButton.clicked.connect(lambda: exec_install(launcher_app))
    main_window.show()
    sys.exit(app.exec())
