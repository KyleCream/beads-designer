"""
拼豆图纸生成器 - 主入口
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt


def setup_app_style(app: QApplication):
    app.setStyle('Fusion')

    font = QFont()
    if sys.platform == 'win32':
        font.setFamily('Microsoft YaHei')
    elif sys.platform == 'darwin':
        font.setFamily('PingFang SC')
    else:
        font.setFamily('Noto Sans CJK SC')
    font.setPointSize(9)
    app.setFont(font)

    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f6fa;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #dcdde1;
            border-radius: 6px;
            margin-top: 8px;
            padding-top: 12px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QSpinBox, QComboBox, QLineEdit {
            padding: 4px 6px;
            border: 1px solid #dcdde1;
            border-radius: 4px;
            background-color: white;
            min-height: 22px;
        }
        QSpinBox:focus, QComboBox:focus, QLineEdit:focus {
            border-color: #3498db;
        }
        QStatusBar {
            background-color: #2c3e50;
            color: white;
            font-size: 11px;
            min-height: 22px;
        }
        QSplitter::handle {
            background-color: #dcdde1;
        }
        QSplitter::handle:horizontal {
            width: 3px;
        }
        QSplitter::handle:vertical {
            height: 3px;
        }
    """)


def main():
    # 高DPI
    os.environ.setdefault('QT_ENABLE_HIGHDPI_SCALING', '1')

    app = QApplication(sys.argv)
    setup_app_style(app)

    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()