"""
图片上传和裁剪组件
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QFrame, QRubberBand
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint, QSize
from PyQt6.QtGui import QPixmap, QPainter, QImage, QDragEnterEvent, QDropEvent


class ImageLabel(QLabel):
    """支持裁剪框选的图片标签"""

    crop_changed = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(300, 300)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #bdc3c7;
                border-radius: 8px;
                background-color: #ecf0f1;
            }
        """)

        self._pixmap = None
        self._crop_enabled = False
        self._rubber_band = None
        self._origin = QPoint()
        self._image_rect = QRect()  # 图片在label中的实际位置
        self._scale_factor = 1.0

    def set_pixmap_scaled(self, pixmap: QPixmap):
        """设置并自适应缩放图片"""
        self._pixmap = pixmap
        self._update_display()

    def _update_display(self):
        if self._pixmap:
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(scaled)

            # 计算图片在label中的实际位置
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            self._image_rect = QRect(x, y, scaled.width(), scaled.height())
            self._scale_factor = self._pixmap.width() / scaled.width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_display()

    def set_crop_enabled(self, enabled: bool):
        self._crop_enabled = enabled
        if enabled:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            if self._rubber_band:
                self._rubber_band.hide()

    def mousePressEvent(self, event):
        if self._crop_enabled and event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.pos()
            if self._rubber_band is None:
                self._rubber_band = QRubberBand(
                    QRubberBand.Shape.Rectangle, self
                )
            self._rubber_band.setGeometry(QRect(self._origin, QSize()))
            self._rubber_band.show()

    def mouseMoveEvent(self, event):
        if self._crop_enabled and self._rubber_band:
            self._rubber_band.setGeometry(
                QRect(self._origin, event.pos()).normalized()
            )

    def mouseReleaseEvent(self, event):
        if self._crop_enabled and self._rubber_band and event.button() == Qt.MouseButton.LeftButton:
            rect = self._rubber_band.geometry()
            # 转换为原图坐标
            crop_rect = self._label_rect_to_image_rect(rect)
            if crop_rect:
                self.crop_changed.emit(crop_rect)

    def _label_rect_to_image_rect(self, rect: QRect):
        """将label坐标转换为原图坐标"""
        if not self._pixmap or self._image_rect.isEmpty():
            return None

        # 裁剪到图片区域
        intersected = rect.intersected(self._image_rect)
        if intersected.isEmpty():
            return None

        # 相对于图片区域的坐标
        x = (intersected.x() - self._image_rect.x()) * self._scale_factor
        y = (intersected.y() - self._image_rect.y()) * self._scale_factor
        w = intersected.width() * self._scale_factor
        h = intersected.height() * self._scale_factor

        return (int(x), int(y), int(x + w), int(y + h))

    def get_crop_rect(self):
        """获取当前裁剪区域（原图坐标）"""
        if self._rubber_band and self._rubber_band.isVisible():
            return self._label_rect_to_image_rect(self._rubber_band.geometry())
        return None


class UploadWidget(QWidget):
    """上传组件"""

    image_loaded = pyqtSignal(str)
    crop_changed = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        self.current_image_path = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 标题
        title = QLabel("📷 图片上传")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        layout.addWidget(title)

        # 图片显示区域
        self.image_label = ImageLabel()
        self.image_label.setText("点击上传或拖拽图片到此处\n\n支持 JPG / PNG / BMP")
        self.image_label.crop_changed.connect(self.crop_changed.emit)
        layout.addWidget(self.image_label, 1)

        # 按钮栏
        btn_layout = QHBoxLayout()

        self.upload_btn = QPushButton("📁 选择图片")
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.upload_btn.clicked.connect(self._on_upload)
        btn_layout.addWidget(self.upload_btn)

        self.crop_btn = QPushButton("✂️ 裁剪模式")
        self.crop_btn.setCheckable(True)
        self.crop_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
            QPushButton:checked {
                background-color: #e67e22;
            }
        """)
        self.crop_btn.setEnabled(False)
        self.crop_btn.clicked.connect(
            lambda checked: self.image_label.set_crop_enabled(checked)
        )
        btn_layout.addWidget(self.crop_btn)

        self.reset_btn = QPushButton("🔄 重置")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(self._on_reset)
        btn_layout.addWidget(self.reset_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 启用拖拽
        self.setAcceptDrops(True)

    def _on_upload(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*)"
        )
        if filepath:
            self._load_image(filepath)

    def _load_image(self, filepath: str):
        pixmap = QPixmap(filepath)
        if pixmap.isNull():
            return

        self.current_image_path = filepath
        self.image_label.set_pixmap_scaled(pixmap)
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px solid #3498db;
                border-radius: 8px;
                background-color: #2c3e50;
            }
        """)
        self.crop_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)
        self.image_loaded.emit(filepath)

    def _on_reset(self):
        self.image_label.set_crop_enabled(False)
        self.crop_btn.setChecked(False)
        if self.current_image_path:
            self._load_image(self.current_image_path)

    def get_crop_rect(self):
        return self.image_label.get_crop_rect()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            filepath = urls[0].toLocalFile()
            if filepath.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                self._load_image(filepath)