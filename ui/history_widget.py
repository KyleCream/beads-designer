"""
历史记录组件
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon
from core.project import HistoryManager


class HistoryWidget(QWidget):
    """历史记录"""

    project_selected = pyqtSignal(int)

    def __init__(self, history_manager: HistoryManager):
        super().__init__()
        self.history_manager = history_manager
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题栏
        header_layout = QHBoxLayout()
        title = QLabel("📁 历史记录")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_layout.addWidget(title)

        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.refresh_btn.clicked.connect(self.refresh)
        header_layout.addWidget(self.refresh_btn)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # 列表
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(80, 80))
        self.list_widget.setSpacing(5)
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                background-color: white;
            }
            QListWidget::item {
                border-bottom: 1px solid #ecf0f1;
                padding: 10px;
            }
            QListWidget::item:hover {
                background-color: #ebf5fb;
            }
            QListWidget::item:selected {
                background-color: #d4efdf;
            }
        """)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_widget, 1)

        # 底部按钮
        btn_layout = QHBoxLayout()
        self.open_btn = QPushButton("📄 打开PDF")
        self.open_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #27ae60; }
        """)
        self.open_btn.clicked.connect(self._on_open)
        btn_layout.addWidget(self.open_btn)

        self.delete_btn = QPushButton("🗑️ 删除")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        self.delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self.delete_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def refresh(self):
        """刷新历史记录列表"""
        self.list_widget.clear()
        projects = self.history_manager.get_all_projects()

        for project in projects:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, project.id)

            # 文字信息
            text = (
                f"{project.name}\n"
                f"尺寸: {project.grid_width}×{project.grid_height} | "
                f"色板: {project.palette_brand}\n"
                f"创建时间: {project.created_at[:19]}"
            )
            item.setText(text)
            item.setSizeHint(QSize(0, 90))

            # 缩略图
            if project.preview_path and os.path.exists(project.preview_path):
                pixmap = QPixmap(project.preview_path)
                if not pixmap.isNull():
                    item.setIcon(QIcon(pixmap.scaled(
                        80, 80,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )))

            self.list_widget.addItem(item)

    def _get_selected_project_id(self) -> int:
        current = self.list_widget.currentItem()
        if current:
            return current.data(Qt.ItemDataRole.UserRole)
        return -1

    def _on_item_double_clicked(self, item):
        project_id = item.data(Qt.ItemDataRole.UserRole)
        self.project_selected.emit(project_id)

    def _on_open(self):
        project_id = self._get_selected_project_id()
        if project_id > 0:
            self.project_selected.emit(project_id)
        else:
            QMessageBox.information(self, "提示", "请先选择一个项目")

    def _on_delete(self):
        project_id = self._get_selected_project_id()
        if project_id <= 0:
            QMessageBox.information(self, "提示", "请先选择一个项目")
            return

        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除这个项目吗？\n（包括图片和PDF文件）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.history_manager.delete_project(project_id)
            self.refresh()