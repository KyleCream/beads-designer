"""
图片上传组件 v2
主界面：紧凑缩略图 + 关键按钮
详情弹窗：精细裁剪 + 前进后退
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QRubberBand, QSizePolicy, QDialog,
    QDialogButtonBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen


# ==================== 主界面的紧凑上传区 ====================

class UploadWidget(QWidget):
    """紧凑上传组件 - 缩略图 + 按钮"""

    image_loaded = pyqtSignal(str)
    crop_changed = pyqtSignal(tuple)
    crop_cleared = pyqtSignal()
    detail_requested = pyqtSignal()  # 请求打开详情弹窗

    def __init__(self):
        super().__init__()
        self.current_image_path = None
        self._original_pixmap = None
        self._crop_rect = None  # 当前裁剪区域

        self._history = []
        self._history_index = -1

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 标题
        title = QLabel('📷 图片')
        title.setStyleSheet('font-size: 13px; font-weight: bold;')
        layout.addWidget(title)

        # 缩略图显示
        self.thumb_label = QLabel('点击上传图片')
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setFixedHeight(140)
        self.thumb_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.thumb_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #bdc3c7;
                border-radius: 8px;
                background-color: #f8f9fa;
                color: #95a5a6;
                font-size: 12px;
            }
        """)
        self.thumb_label.mousePressEvent = lambda e: self._on_upload()
        layout.addWidget(self.thumb_label)

        # 裁剪状态
        self.crop_info_label = QLabel('')
        self.crop_info_label.setStyleSheet('font-size: 10px; color: #636e72;')
        self.crop_info_label.setWordWrap(True)
        layout.addWidget(self.crop_info_label)

        # 按钮行1
        btn_row1 = QHBoxLayout()
        btn_row1.setSpacing(4)

        self.upload_btn = QPushButton('📁 上传')
        self.upload_btn.setStyleSheet(self._btn_style('#3498db', '#2980b9'))
        self.upload_btn.clicked.connect(self._on_upload)
        btn_row1.addWidget(self.upload_btn)

        self.detail_btn = QPushButton('🔍 裁剪详情')
        self.detail_btn.setStyleSheet(self._btn_style('#6c5ce7', '#5f3dc4'))
        self.detail_btn.setEnabled(False)
        self.detail_btn.clicked.connect(self.detail_requested.emit)
        btn_row1.addWidget(self.detail_btn)

        layout.addLayout(btn_row1)

        # 按钮行2
        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(4)

        self.undo_btn = QPushButton('↩')
        self.undo_btn.setToolTip('撤回')
        self.undo_btn.setFixedWidth(36)
        self.undo_btn.setStyleSheet(self._btn_style('#636e72', '#2d3436'))
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self._on_undo)
        btn_row2.addWidget(self.undo_btn)

        self.redo_btn = QPushButton('↪')
        self.redo_btn.setToolTip('重做')
        self.redo_btn.setFixedWidth(36)
        self.redo_btn.setStyleSheet(self._btn_style('#636e72', '#2d3436'))
        self.redo_btn.setEnabled(False)
        self.redo_btn.clicked.connect(self._on_redo)
        btn_row2.addWidget(self.redo_btn)

        self.reset_btn = QPushButton('🔄 重置')
        self.reset_btn.setStyleSheet(self._btn_style('#e17055', '#d63031'))
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(self._on_reset)
        btn_row2.addWidget(self.reset_btn)

        btn_row2.addStretch()
        layout.addLayout(btn_row2)

        self.setAcceptDrops(True)

    @staticmethod
    def _btn_style(bg: str, hover: str) -> str:
        return f"""
            QPushButton {{
                background-color: {bg}; color: white; border: none;
                padding: 5px 10px; border-radius: 3px; font-size: 11px;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:disabled {{ background-color: #dfe6e9; color: #b2bec3; }}
        """

    # ==================== 图片加载 ====================

    def _on_upload(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, '选择图片', '',
            'Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*)'
        )
        if filepath:
            self._load_image(filepath)

    def _load_image(self, filepath: str):
        pixmap = QPixmap(filepath)
        if pixmap.isNull():
            return

        self.current_image_path = filepath
        self._original_pixmap = pixmap
        self._crop_rect = None

        self._update_thumbnail()

        self._history.clear()
        self._history_index = -1
        self._push_state({'crop_rect': None, 'desc': '加载原图'})

        self.detail_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)

        w, h = pixmap.width(), pixmap.height()
        self.crop_info_label.setText(f'原图: {w}x{h} px')

        self.image_loaded.emit(filepath)

    def _update_thumbnail(self):
        """更新缩略图显示"""
        if self._original_pixmap is None:
            return

        if self._crop_rect:
            left, top, right, bottom = self._crop_rect
            display = self._original_pixmap.copy(left, top, right - left, bottom - top)
        else:
            display = self._original_pixmap

        scaled = display.scaled(
            self.thumb_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.thumb_label.setPixmap(scaled)
        self.thumb_label.setStyleSheet("""
            QLabel {
                border: 2px solid #3498db;
                border-radius: 8px;
                background-color: #2c3e50;
            }
        """)

    # ==================== 裁剪操作 ====================

    def apply_external_crop(self, rect: tuple):
        """从外部（详情弹窗）应用裁剪"""
        self._crop_rect = rect
        self._push_state({'crop_rect': rect, 'desc': f'裁剪 {rect}'})
        self._update_thumbnail()

        left, top, right, bottom = rect
        self.crop_info_label.setText(
            f'已裁剪: ({left},{top})-({right},{bottom}) | {right - left}x{bottom - top} px'
        )
        self.crop_changed.emit(rect)

    def clear_crop(self):
        """清除裁剪"""
        self._crop_rect = None
        self._push_state({'crop_rect': None, 'desc': '清除裁剪'})
        self._update_thumbnail()
        self.crop_info_label.setText(
            f'原图: {self._original_pixmap.width()}x{self._original_pixmap.height()} px'
        )
        self.crop_cleared.emit()

    def get_crop_rect(self):
        return self._crop_rect

    # ==================== 前进后退 ====================

    def _push_state(self, state: dict):
        if self._history_index < len(self._history) - 1:
            self._history = self._history[:self._history_index + 1]
        self._history.append(state)
        if len(self._history) > 20:
            self._history.pop(0)
        self._history_index = len(self._history) - 1
        self._update_undo_redo()

    def _on_undo(self):
        if self._history_index <= 0:
            return
        self._history_index -= 1
        self._apply_state(self._history[self._history_index])

    def _on_redo(self):
        if self._history_index >= len(self._history) - 1:
            return
        self._history_index += 1
        self._apply_state(self._history[self._history_index])

    def _apply_state(self, state: dict):
        self._crop_rect = state.get('crop_rect')
        self._update_thumbnail()

        if self._crop_rect:
            l, t, r, b = self._crop_rect
            self.crop_info_label.setText(f'裁剪: ({l},{t})-({r},{b}) | {r - l}x{b - t} px')
            self.crop_changed.emit(self._crop_rect)
        else:
            if self._original_pixmap:
                self.crop_info_label.setText(
                    f'原图: {self._original_pixmap.width()}x{self._original_pixmap.height()} px'
                )
            self.crop_cleared.emit()

        self._update_undo_redo()

    def _update_undo_redo(self):
        self.undo_btn.setEnabled(self._history_index > 0)
        self.redo_btn.setEnabled(self._history_index < len(self._history) - 1)

    def _on_reset(self):
        self._crop_rect = None
        self._push_state({'crop_rect': None, 'desc': '重置'})
        self._update_thumbnail()
        if self._original_pixmap:
            self.crop_info_label.setText(
                f'原图: {self._original_pixmap.width()}x{self._original_pixmap.height()} px'
            )
        self.crop_cleared.emit()

    # ==================== 拖拽 ====================

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            fp = urls[0].toLocalFile()
            if fp.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                self._load_image(fp)


# ==================== 精细裁剪详情弹窗 ====================

class CropLabel(QLabel):
    """可裁剪的图片标签"""
    crop_defined = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(400, 400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._pixmap = None
        self._image_rect = QRect()
        self._scale = 1.0
        self._rubber_band = None
        self._origin = QPoint()
        self._dragging = False

    def set_image(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self._refresh()

    def _refresh(self):
        if not self._pixmap:
            return
        scaled = self._pixmap.scaled(
            self.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled)
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        self._image_rect = QRect(x, y, scaled.width(), scaled.height())
        self._scale = self._pixmap.width() / scaled.width() if scaled.width() > 0 else 1.0

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.pos()
            if not self._rubber_band:
                self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
            self._rubber_band.setGeometry(QRect(self._origin, QSize()))
            self._rubber_band.show()
            self._dragging = True

    def mouseMoveEvent(self, event):
        if self._dragging and self._rubber_band:
            self._rubber_band.setGeometry(QRect(self._origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if not self._dragging:
            return
        self._dragging = False
        if self._rubber_band:
            rect = self._rubber_band.geometry()
            result = self._to_original(rect)
            if result:
                self.crop_defined.emit(result)

    def _to_original(self, rect: QRect):
        if not self._pixmap or self._image_rect.isEmpty():
            return None
        inter = rect.intersected(self._image_rect)
        if inter.width() < 5 or inter.height() < 5:
            return None
        l = int((inter.x() - self._image_rect.x()) * self._scale)
        t = int((inter.y() - self._image_rect.y()) * self._scale)
        r = int(l + inter.width() * self._scale)
        b = int(t + inter.height() * self._scale)
        iw, ih = self._pixmap.width(), self._pixmap.height()
        return (max(0, l), max(0, t), min(r, iw), min(b, ih))

    def clear_selection(self):
        if self._rubber_band:
            self._rubber_band.hide()


class ImageDetailDialog(QDialog):
    """图片详情弹窗 - 精细裁剪"""

    def __init__(self, image_path: str, current_crop=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('图片裁剪详情')
        self.setMinimumSize(700, 550)
        self.resize(850, 650)

        self._image_path = image_path
        self._pixmap = QPixmap(image_path)
        self._crop_rect = current_crop
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 提示
        hint = QLabel('在图片上拖拽框选要裁剪的区域：')
        hint.setStyleSheet('font-size: 12px; color: #636e72;')
        layout.addWidget(hint)

        # 裁剪操作区
        self.crop_label = CropLabel()
        self.crop_label.set_image(self._pixmap)
        self.crop_label.setCursor(Qt.CursorShape.CrossCursor)
        self.crop_label.crop_defined.connect(self._on_crop)
        self.crop_label.setStyleSheet(
            'border: 1px solid #dcdde1; border-radius: 4px; background: #2c3e50;'
        )
        layout.addWidget(self.crop_label, 1)

        # 裁剪信息 + 预览
        info_row = QHBoxLayout()

        self.info_label = QLabel('请在图上框选区域')
        self.info_label.setStyleSheet('font-size: 11px;')
        info_row.addWidget(self.info_label)

        info_row.addStretch()

        clear_btn = QPushButton('清除裁剪')
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #e17055; color: white; border: none;
                padding: 5px 12px; border-radius: 3px; font-size: 11px;
            }
            QPushButton:hover { background: #d63031; }
        """)
        clear_btn.clicked.connect(self._on_clear)
        info_row.addWidget(clear_btn)

        layout.addLayout(info_row)

        # 裁剪预览
        self.preview_label = QLabel('裁剪预览')
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setFixedHeight(120)
        self.preview_label.setStyleSheet(
            'border: 1px solid #dcdde1; border-radius: 4px; background: #f5f6fa;'
            'color: #b2bec3; font-size: 11px;'
        )
        layout.addWidget(self.preview_label)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # 如果有已有裁剪，显示
        if self._crop_rect:
            self._show_preview(self._crop_rect)

    def _on_crop(self, rect: tuple):
        self._crop_rect = rect
        self._show_preview(rect)

    def _show_preview(self, rect):
        l, t, r, b = rect
        cropped = self._pixmap.copy(l, t, r - l, b - t)
        scaled = cropped.scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)
        self.preview_label.setStyleSheet(
            'border: 2px solid #00b894; border-radius: 4px; background: #2c3e50;'
        )
        self.info_label.setText(
            f'裁剪: ({l},{t}) -> ({r},{b}) | 尺寸: {r - l} x {b - t} px'
        )

    def _on_clear(self):
        self._crop_rect = None
        self.crop_label.clear_selection()
        self.preview_label.clear()
        self.preview_label.setText('裁剪已清除')
        self.preview_label.setStyleSheet(
            'border: 1px solid #dcdde1; border-radius: 4px; background: #f5f6fa;'
            'color: #b2bec3; font-size: 11px;'
        )
        self.info_label.setText('裁剪已清除，点击确定将使用原图')

    def get_crop_rect(self):
        return self._crop_rect