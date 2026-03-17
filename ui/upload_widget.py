"""
图片上传组件 v3
主界面：紧凑缩略图 + 关键按钮
详情弹窗：支持缩放的精细裁剪 + 前进后退
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QRubberBand, QSizePolicy, QDialog,
    QDialogButtonBox, QScrollArea, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen


# ==================== 主界面的紧凑上传区 ====================

class UploadWidget(QWidget):
    """紧凑上传组件"""

    image_loaded = pyqtSignal(str)
    crop_changed = pyqtSignal(tuple)
    crop_cleared = pyqtSignal()
    detail_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_image_path = None
        self._original_pixmap = None
        self._crop_rect = None

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

        # 缩略图
        self.thumb_label = QLabel('点击上传图片')
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setFixedHeight(130)
        self.thumb_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
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
        self.crop_info = QLabel('')
        self.crop_info.setStyleSheet('font-size: 10px; color: #636e72;')
        self.crop_info.setWordWrap(True)
        layout.addWidget(self.crop_info)

        # 按钮行1
        row1 = QHBoxLayout()
        row1.setSpacing(4)

        self.upload_btn = QPushButton('📁 上传')
        self.upload_btn.setStyleSheet(self._bs('#3498db', '#2980b9'))
        self.upload_btn.clicked.connect(self._on_upload)
        row1.addWidget(self.upload_btn)

        self.detail_btn = QPushButton('🔍 裁剪详情')
        self.detail_btn.setStyleSheet(self._bs('#6c5ce7', '#5f3dc4'))
        self.detail_btn.setEnabled(False)
        self.detail_btn.clicked.connect(self.detail_requested.emit)
        row1.addWidget(self.detail_btn)

        layout.addLayout(row1)

        # 按钮行2
        row2 = QHBoxLayout()
        row2.setSpacing(4)

        self.undo_btn = QPushButton('↩')
        self.undo_btn.setToolTip('撤回')
        self.undo_btn.setFixedWidth(36)
        self.undo_btn.setStyleSheet(self._bs('#636e72', '#2d3436'))
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self._on_undo)
        row2.addWidget(self.undo_btn)

        self.redo_btn = QPushButton('↪')
        self.redo_btn.setToolTip('重做')
        self.redo_btn.setFixedWidth(36)
        self.redo_btn.setStyleSheet(self._bs('#636e72', '#2d3436'))
        self.redo_btn.setEnabled(False)
        self.redo_btn.clicked.connect(self._on_redo)
        row2.addWidget(self.redo_btn)

        self.reset_btn = QPushButton('🔄 重置')
        self.reset_btn.setStyleSheet(self._bs('#e17055', '#d63031'))
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(self._on_reset)
        row2.addWidget(self.reset_btn)

        row2.addStretch()
        layout.addLayout(row2)

        self.setAcceptDrops(True)

    @staticmethod
    def _bs(bg, hover):
        return f"""
            QPushButton {{
                background-color: {bg}; color: white; border: none;
                padding: 5px 10px; border-radius: 3px; font-size: 11px;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:disabled {{ background-color: #dfe6e9; color: #b2bec3; }}
        """

    # ==================== 加载 ====================

    def _on_upload(self):
        fp, _ = QFileDialog.getOpenFileName(
            self, '选择图片', '',
            'Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All (*)'
        )
        if fp:
            self._load_image(fp)

    def _load_image(self, filepath):
        px = QPixmap(filepath)
        if px.isNull():
            return

        self.current_image_path = filepath
        self._original_pixmap = px
        self._crop_rect = None

        self._update_thumb()
        self._history.clear()
        self._history_index = -1
        self._push({'crop_rect': None, 'desc': '加载原图'})

        self.detail_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)
        self.crop_info.setText(f'原图: {px.width()}×{px.height()} px')
        self.image_loaded.emit(filepath)

    def _update_thumb(self):
        if not self._original_pixmap:
            return
        src = self._original_pixmap
        if self._crop_rect:
            l, t, r, b = self._crop_rect
            src = self._original_pixmap.copy(l, t, r - l, b - t)

        scaled = src.scaled(
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

    # ==================== 裁剪 ====================

    def apply_external_crop(self, rect):
        self._crop_rect = rect
        self._push({'crop_rect': rect, 'desc': f'裁剪 {rect}'})
        self._update_thumb()
        l, t, r, b = rect
        self.crop_info.setText(f'已裁剪: {r-l}×{b-t} px')
        self.crop_changed.emit(rect)

    def clear_crop(self):
        self._crop_rect = None
        self._push({'crop_rect': None, 'desc': '清除裁剪'})
        self._update_thumb()
        if self._original_pixmap:
            self.crop_info.setText(
                f'原图: {self._original_pixmap.width()}×{self._original_pixmap.height()} px'
            )
        self.crop_cleared.emit()

    def get_crop_rect(self):
        return self._crop_rect

    # ==================== 历史 ====================

    def _push(self, state):
        if self._history_index < len(self._history) - 1:
            self._history = self._history[:self._history_index + 1]
        self._history.append(state)
        if len(self._history) > 20:
            self._history.pop(0)
        self._history_index = len(self._history) - 1
        self._update_btns()

    def _on_undo(self):
        if self._history_index <= 0:
            return
        self._history_index -= 1
        self._apply(self._history[self._history_index])

    def _on_redo(self):
        if self._history_index >= len(self._history) - 1:
            return
        self._history_index += 1
        self._apply(self._history[self._history_index])

    def _apply(self, state):
        self._crop_rect = state.get('crop_rect')
        self._update_thumb()
        if self._crop_rect:
            l, t, r, b = self._crop_rect
            self.crop_info.setText(f'裁剪: {r-l}×{b-t} px')
            self.crop_changed.emit(self._crop_rect)
        else:
            if self._original_pixmap:
                self.crop_info.setText(
                    f'原图: {self._original_pixmap.width()}×{self._original_pixmap.height()} px'
                )
            self.crop_cleared.emit()
        self._update_btns()

    def _update_btns(self):
        self.undo_btn.setEnabled(self._history_index > 0)
        self.redo_btn.setEnabled(self._history_index < len(self._history) - 1)

    def _on_reset(self):
        self._crop_rect = None
        self._push({'crop_rect': None, 'desc': '重置'})
        self._update_thumb()
        if self._original_pixmap:
            self.crop_info.setText(
                f'原图: {self._original_pixmap.width()}×{self._original_pixmap.height()} px'
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


# ==================== 可缩放裁剪画布 ====================

class ZoomCropCanvas(QWidget):
    """支持缩放的裁剪画布"""

    crop_defined = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        self._pixmap = None
        self._zoom = 1.0
        self._offset = QPoint(0, 0)  # 图片绘制偏移

        # 裁剪状态
        self._crop_start = None
        self._crop_end = None
        self._crop_rect_display = None  # 屏幕坐标的裁剪框
        self._is_cropping = False

        # 拖拽平移
        self._is_panning = False
        self._pan_start = QPoint()
        self._pan_offset_start = QPoint()

        self.setMinimumSize(300, 300)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_image(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self._zoom = 1.0
        self._offset = QPoint(0, 0)
        self._crop_rect_display = None
        self._fit_to_view()
        self.update()

    def set_zoom(self, zoom: float):
        old_zoom = self._zoom
        self._zoom = max(0.1, min(zoom, 10.0))

        # 保持中心点不变
        center = QPoint(self.width() // 2, self.height() // 2)
        self._offset = QPoint(
            int(center.x() - (center.x() - self._offset.x()) * self._zoom / old_zoom),
            int(center.y() - (center.y() - self._offset.y()) * self._zoom / old_zoom)
        )
        self.update()

    def get_zoom(self) -> float:
        return self._zoom

    def _fit_to_view(self):
        """自适应视图"""
        if not self._pixmap:
            return
        pw, ph = self._pixmap.width(), self._pixmap.height()
        vw, vh = self.width(), self.height()
        if pw <= 0 or ph <= 0:
            return
        scale_w = vw / pw
        scale_h = vh / ph
        self._zoom = min(scale_w, scale_h) * 0.92
        # 居中
        disp_w = pw * self._zoom
        disp_h = ph * self._zoom
        self._offset = QPoint(int((vw - disp_w) / 2), int((vh - disp_h) / 2))

    def clear_crop(self):
        self._crop_rect_display = None
        self.update()

    # ==================== 坐标转换 ====================

    def _screen_to_image(self, screen_pt: QPoint) -> QPoint:
        """屏幕坐标 → 原图坐标"""
        ix = (screen_pt.x() - self._offset.x()) / self._zoom
        iy = (screen_pt.y() - self._offset.y()) / self._zoom
        return QPoint(int(ix), int(iy))

    def _image_to_screen(self, img_pt: QPoint) -> QPoint:
        """原图坐标 → 屏幕坐标"""
        sx = img_pt.x() * self._zoom + self._offset.x()
        sy = img_pt.y() * self._zoom + self._offset.y()
        return QPoint(int(sx), int(sy))

    # ==================== 绘制 ====================

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 背景
        painter.fillRect(self.rect(), QColor(40, 44, 52))

        if self._pixmap:
            # 绘制图片
            disp_w = int(self._pixmap.width() * self._zoom)
            disp_h = int(self._pixmap.height() * self._zoom)
            target = QRect(self._offset.x(), self._offset.y(), disp_w, disp_h)
            painter.drawPixmap(target, self._pixmap)

            # 绘制裁剪框
            if self._crop_rect_display:
                # 半透明遮罩
                overlay = QColor(0, 0, 0, 120)
                img_rect = QRect(self._offset.x(), self._offset.y(), disp_w, disp_h)

                # 裁剪框外的区域加遮罩
                crop = self._crop_rect_display

                # 上
                painter.fillRect(
                    QRect(img_rect.left(), img_rect.top(),
                          img_rect.width(), crop.top() - img_rect.top()),
                    overlay
                )
                # 下
                painter.fillRect(
                    QRect(img_rect.left(), crop.bottom(),
                          img_rect.width(), img_rect.bottom() - crop.bottom()),
                    overlay
                )
                # 左
                painter.fillRect(
                    QRect(img_rect.left(), crop.top(),
                          crop.left() - img_rect.left(), crop.height()),
                    overlay
                )
                # 右
                painter.fillRect(
                    QRect(crop.right(), crop.top(),
                          img_rect.right() - crop.right(), crop.height()),
                    overlay
                )

                # 裁剪框边框
                pen = QPen(QColor(0, 184, 148), 2, Qt.PenStyle.SolidLine)
                painter.setPen(pen)
                painter.drawRect(crop)

                # 三分线
                pen2 = QPen(QColor(255, 255, 255, 80), 1, Qt.PenStyle.DashLine)
                painter.setPen(pen2)
                w3 = crop.width() / 3
                h3 = crop.height() / 3
                for i in range(1, 3):
                    painter.drawLine(
                        int(crop.left() + w3 * i), crop.top(),
                        int(crop.left() + w3 * i), crop.bottom()
                    )
                    painter.drawLine(
                        crop.left(), int(crop.top() + h3 * i),
                        crop.right(), int(crop.top() + h3 * i)
                    )

        # 缩放提示
        painter.setPen(QColor(255, 255, 255, 150))
        painter.drawText(10, self.height() - 10, f'缩放: {self._zoom:.0%} | 左键裁剪 | 右键拖拽 | 滚轮缩放')

        painter.end()

    # ==================== 鼠标交互 ====================

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 开始裁剪
            self._is_cropping = True
            self._crop_start = event.pos()
            self._crop_end = event.pos()
            self._crop_rect_display = None
            self.setCursor(Qt.CursorShape.CrossCursor)

        elif event.button() == Qt.MouseButton.RightButton:
            # 开始拖拽平移
            self._is_panning = True
            self._pan_start = event.pos()
            self._pan_offset_start = QPoint(self._offset)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self._is_cropping:
            self._crop_end = event.pos()
            # 实时更新裁剪框
            x1 = min(self._crop_start.x(), self._crop_end.x())
            y1 = min(self._crop_start.y(), self._crop_end.y())
            x2 = max(self._crop_start.x(), self._crop_end.x())
            y2 = max(self._crop_start.y(), self._crop_end.y())
            self._crop_rect_display = QRect(x1, y1, x2 - x1, y2 - y1)
            self.update()

        elif self._is_panning:
            delta = event.pos() - self._pan_start
            self._offset = self._pan_offset_start + delta
            self.update()

        else:
            # 根据位置切换光标
            if self._pixmap:
                self.setCursor(Qt.CursorShape.CrossCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_cropping:
            self._is_cropping = False
            self.setCursor(Qt.CursorShape.CrossCursor)

            if self._crop_rect_display and self._crop_rect_display.width() > 5 and self._crop_rect_display.height() > 5:
                # 转换为原图坐标
                top_left = self._screen_to_image(self._crop_rect_display.topLeft())
                bottom_right = self._screen_to_image(self._crop_rect_display.bottomRight())

                if self._pixmap:
                    iw, ih = self._pixmap.width(), self._pixmap.height()
                    l = max(0, min(top_left.x(), iw - 1))
                    t = max(0, min(top_left.y(), ih - 1))
                    r = max(l + 1, min(bottom_right.x(), iw))
                    b = max(t + 1, min(bottom_right.y(), ih))

                    if (r - l) > 3 and (b - t) > 3:
                        self.crop_defined.emit((l, t, r, b))

        elif event.button() == Qt.MouseButton.RightButton and self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.CrossCursor)

    def wheelEvent(self, event):
        """滚轮缩放"""
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1 / 1.15

        # 以鼠标位置为中心缩放
        mouse_pos = event.position().toPoint()
        old_img_pos = self._screen_to_image(mouse_pos)

        self._zoom = max(0.1, min(self._zoom * factor, 10.0))

        # 调整偏移使鼠标下的图片位置不变
        new_screen = self._image_to_screen(old_img_pos)
        self._offset += mouse_pos - new_screen

        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap and self._crop_rect_display is None:
            self._fit_to_view()
            self.update()


# ==================== 裁剪详情弹窗 ====================

class ImageDetailDialog(QDialog):
    """图片详情弹窗 - 可缩放的精细裁剪"""

    def __init__(self, image_path: str, current_crop=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('图片裁剪 - 左键框选裁剪 | 右键拖拽 | 滚轮缩放')
        self.setMinimumSize(750, 580)
        self.resize(950, 700)

        self._pixmap = QPixmap(image_path)
        self._crop_rect = current_crop
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ---- 工具栏 ----
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        toolbar.addWidget(QLabel('🔍 缩放:'))

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 1000)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(180)
        self.zoom_slider.valueChanged.connect(self._on_zoom_slider)
        toolbar.addWidget(self.zoom_slider)

        self.zoom_label = QLabel('100%')
        self.zoom_label.setFixedWidth(50)
        self.zoom_label.setStyleSheet('font-weight: bold;')
        toolbar.addWidget(self.zoom_label)

        fit_btn = QPushButton('📐 适应窗口')
        fit_btn.setStyleSheet(self._tb_style('#74b9ff', '#0984e3'))
        fit_btn.clicked.connect(self._on_fit)
        toolbar.addWidget(fit_btn)

        zoom_100_btn = QPushButton('1:1 原始大小')
        zoom_100_btn.setStyleSheet(self._tb_style('#a29bfe', '#6c5ce7'))
        zoom_100_btn.clicked.connect(lambda: self._set_zoom(1.0))
        toolbar.addWidget(zoom_100_btn)

        toolbar.addStretch()

        clear_btn = QPushButton('✖ 清除裁剪')
        clear_btn.setStyleSheet(self._tb_style('#e17055', '#d63031'))
        clear_btn.clicked.connect(self._on_clear)
        toolbar.addWidget(clear_btn)

        layout.addLayout(toolbar)

        # ---- 裁剪画布 ----
        self.canvas = ZoomCropCanvas()
        self.canvas.set_image(self._pixmap)
        self.canvas.crop_defined.connect(self._on_crop)
        layout.addWidget(self.canvas, 1)

        # ---- 底部信息+按钮 ----
        bottom = QHBoxLayout()

        self.info_label = QLabel(
            f'原图: {self._pixmap.width()}×{self._pixmap.height()} px | 左键框选裁剪区域'
        )
        self.info_label.setStyleSheet('font-size: 11px; color: #636e72;')
        bottom.addWidget(self.info_label)

        bottom.addStretch()

        # 裁剪预览缩略图
        self.preview_thumb = QLabel()
        self.preview_thumb.setFixedSize(80, 60)
        self.preview_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_thumb.setStyleSheet(
            'border: 1px solid #dcdde1; border-radius: 4px; background: #f5f6fa;'
        )
        bottom.addWidget(self.preview_thumb)

        layout.addLayout(bottom)

        # 确定/取消
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('确定裁剪')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('取消')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # 如果有已有裁剪
        if self._crop_rect:
            self._show_crop_info(self._crop_rect)

    @staticmethod
    def _tb_style(bg, hover):
        return f"""
            QPushButton {{
                background: {bg}; color: white; border: none;
                padding: 5px 12px; border-radius: 3px; font-size: 11px;
            }}
            QPushButton:hover {{ background: {hover}; }}
        """

    def _on_crop(self, rect):
        self._crop_rect = rect
        self._show_crop_info(rect)

    def _show_crop_info(self, rect):
        l, t, r, b = rect
        w, h = r - l, b - t
        self.info_label.setText(f'裁剪区域: ({l},{t})→({r},{b}) | 尺寸: {w}×{h} px')
        self.info_label.setStyleSheet('font-size: 11px; color: #00b894; font-weight: bold;')

        # 裁剪预览缩略图
        cropped = self._pixmap.copy(l, t, w, h)
        scaled = cropped.scaled(
            self.preview_thumb.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.preview_thumb.setPixmap(scaled)
        self.preview_thumb.setStyleSheet(
            'border: 2px solid #00b894; border-radius: 4px; background: #2c3e50;'
        )

    def _on_clear(self):
        self._crop_rect = None
        self.canvas.clear_crop()
        self.info_label.setText(
            f'原图: {self._pixmap.width()}×{self._pixmap.height()} px | 裁剪已清除'
        )
        self.info_label.setStyleSheet('font-size: 11px; color: #636e72;')
        self.preview_thumb.clear()
        self.preview_thumb.setStyleSheet(
            'border: 1px solid #dcdde1; border-radius: 4px; background: #f5f6fa;'
        )

    def _on_zoom_slider(self, value):
        zoom = value / 100.0
        self.zoom_label.setText(f'{value}%')
        self.canvas.set_zoom(zoom)

    def _set_zoom(self, zoom):
        self.zoom_slider.setValue(int(zoom * 100))

    def _on_fit(self):
        self.canvas._fit_to_view()
        self.canvas.update()
        self.zoom_slider.setValue(int(self.canvas.get_zoom() * 100))

    def get_crop_rect(self):
        return self._crop_rect