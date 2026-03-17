"""
拼豆图纸生成器 - 主入口
Beads Designer - Main Entry
"""

import sys
import os

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow


def setup_app_style(app: QApplication):
    """设置全局样式"""
    app.setStyle("Fusion")

    # 全局字体
    font = QFont()
    font.setFamily("Microsoft YaHei" if sys.platform == "win32" else "PingFang SC")
    font.setPointSize(10)
    app.setFont(font)

    # 全局样式表
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f6fa;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #bdc3c7;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 15px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QSpinBox, QComboBox, QLineEdit {
            padding: 5px 8px;
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            background-color: white;
        }
        QSpinBox:focus, QComboBox:focus, QLineEdit:focus {
            border-color: #3498db;
        }
        QStatusBar {
            background-color: #2c3e50;
            color: white;
            font-size: 12px;
        }
        QScrollArea {
            border: none;
        }
    """)


def main():
    # 高DPI支持
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

    app = QApplication(sys.argv)
    setup_app_style(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()