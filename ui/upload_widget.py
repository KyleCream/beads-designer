"""
图片上传和裁剪组件
支持裁剪预览、前进后退操作
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QFrame, QRubberBand, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint, QSize
from PyQt6.QtGui import QPixmap, QPainter, QImage, QColor, QPen


class CropImageLabel(QLabel):
    """支持裁剪框选的图片标签"""

    crop_defined = pyqtSignal(tuple)  # 裁剪区域确定时发射 (left, top, right, bottom)

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._original_pixmap = None  # 原始完整图片
        self._display_pixmap = None   # 当前显示的缩放图片
        self._crop_enabled = False
        self._rubber_band = None
        self._origin = QPoint()
        self._image_rect = QRect()    # 图片在label中的实际显示区域
        self._scale_factor = 1.0
        self._is_dragging = False

    def set_image(self, pixmap: QPixmap):
        """设置图片并自适应显示"""
        self._original_pixmap = pixmap
        self._update_display()

    def _update_display(self):
        """根据当前label大小重新缩放显示"""
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return

        available = self.size()
        scaled = self._original_pixmap.scaled(
            available,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self._display_pixmap = scaled
        self.setPixmap(scaled)

        # 计算图片在label中的实际位置（居中）
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        self._image_rect = QRect(x, y, scaled.width(), scaled.height())

        # 缩放比例：原图 / 显示图
        if scaled.width() > 0:
            self._scale_factor = self._original_pixmap.width() / scaled.width()
        else:
            self._scale_factor = 1.0

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_display()

    def set_crop_enabled(self, enabled: bool):
        """开启/关闭裁剪模式"""
        self._crop_enabled = enabled
        if enabled:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            if self._rubber_band:
                self._rubber_band.hide()
                self._rubber_band = None

    def mousePressEvent(self, event):
        if not self._crop_enabled or event.button() != Qt.MouseButton.LeftButton:
            return
        self._origin = event.pos()
        if self._rubber_band is None:
            self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self._rubber_band.setGeometry(QRect(self._origin, QSize()))
        self._rubber_band.show()
        self._is_dragging = True

    def mouseMoveEvent(self, event):
        if self._is_dragging and self._rubber_band:
            self._rubber_band.setGeometry(
                QRect(self._origin, event.pos()).normalized()
            )

    def mouseReleaseEvent(self, event):
        if not self._is_dragging or event.button() != Qt.MouseButton.LeftButton:
            return
        self._is_dragging = False

        if self._rubber_band:
            rect = self._rubber_band.geometry()
            crop_rect = self._display_rect_to_original(rect)
            if crop_rect:
                self.crop_defined.emit(crop_rect)

    def _display_rect_to_original(self, rect: QRect):
        """将显示区域的矩形坐标转换为原图坐标"""
        if self._original_pixmap is None or self._image_rect.isEmpty():
            return None

        intersected = rect.intersected(self._image_rect)
        if intersected.width() < 5 or intersected.height() < 5:
            return None

        left = (intersected.x() - self._image_rect.x()) * self._scale_factor
        top = (intersected.y() - self._image_rect.y()) * self._scale_factor
        right = left + intersected.width() * self._scale_factor
        bottom = top + intersected.height() * self._scale_factor

        # 限制在原图范围内
        img_w = self._original_pixmap.width()
        img_h = self._original_pixmap.height()
        left = max(0, min(int(left), img_w - 1))
        top = max(0, min(int(top), img_h - 1))
        right = max(left + 1, min(int(right), img_w))
        bottom = max(top + 1, min(int(bottom), img_h))

        return (left, top, right, bottom)

    def clear_rubber_band(self):
        """清除裁剪框"""
        if self._rubber_band:
            self._rubber_band.hide()
            self._rubber_band = None


class UploadWidget(QWidget):
    """上传组件 - 带裁剪预览和前进后退"""

    image_loaded = pyqtSignal(str)       # 原始图片加载完成
    crop_changed = pyqtSignal(tuple)     # 裁剪区域变化
    crop_cleared = pyqtSignal()          # 裁剪重置

    def __init__(self):
        super().__init__()
        self.current_image_path = None
        self._original_pixmap = None

        # 操作历史栈（用于前进后退）
        self._history = []        # 所有状态列表
        self._history_index = -1  # 当前状态指针
        self._max_history = 20

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 标题
        title = QLabel('📷 图片上传与裁剪')
        title.setStyleSheet('font-size: 15px; font-weight: bold; padding: 3px;')
        layout.addWidget(title)

        # === 图片显示区 - 上下排列：原图 + 裁剪结果 ===
        image_area = QWidget()
        image_layout = QVBoxLayout(image_area)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(4)

        # 原图/裁剪操作区
        orig_label = QLabel('原图（裁剪模式下可框选区域）:')
        orig_label.setStyleSheet('font-size: 11px; color: #7f8c8d;')
        image_layout.addWidget(orig_label)

        self.image_label = CropImageLabel()
        self.image_label.setText('点击下方按钮上传图片\n或拖拽图片到此处\n\n支持 JPG / PNG / BMP')
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #bdc3c7;
                border-radius: 8px;
                background-color: #f8f9fa;
                color: #95a5a6;
                font-size: 12px;
            }
        """)
        self.image_label.crop_defined.connect(self._on_crop_defined)
        image_layout.addWidget(self.image_label, 3)

        # 裁剪结果预览区
        crop_header = QLabel('裁剪结果预览:')
        crop_header.setStyleSheet('font-size: 11px; color: #7f8c8d;')
        image_layout.addWidget(crop_header)

        self.crop_preview_label = QLabel('暂无裁剪')
        self.crop_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.crop_preview_label.setMinimumHeight(100)
        self.crop_preview_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.crop_preview_label.setStyleSheet("""
            QLabel {
                border: 1px solid #dcdde1;
                border-radius: 6px;
                background-color: #f5f6fa;
                color: #b2bec3;
                font-size: 11px;
            }
        """)
        image_layout.addWidget(self.crop_preview_label, 2)

        layout.addWidget(image_area, 1)

        # === 按钮栏 ===
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self.upload_btn = QPushButton('📁 选择图片')
        self.upload_btn.setStyleSheet(self._btn_style('#3498db', '#2980b9'))
        self.upload_btn.clicked.connect(self._on_upload)
        btn_layout.addWidget(self.upload_btn)

        self.crop_btn = QPushButton('✂️ 裁剪')
        self.crop_btn.setCheckable(True)
        self.crop_btn.setStyleSheet(self._btn_toggle_style())
        self.crop_btn.setEnabled(False)
        self.crop_btn.toggled.connect(self._on_crop_toggled)
        btn_layout.addWidget(self.crop_btn)

        # 前进后退按钮
        self.undo_btn = QPushButton('↩ 撤回')
        self.undo_btn.setStyleSheet(self._btn_style('#636e72', '#2d3436'))
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self._on_undo)
        btn_layout.addWidget(self.undo_btn)

        self.redo_btn = QPushButton('↪ 重做')
        self.redo_btn.setStyleSheet(self._btn_style('#636e72', '#2d3436'))
        self.redo_btn.setEnabled(False)
        self.redo_btn.clicked.connect(self._on_redo)
        btn_layout.addWidget(self.redo_btn)

        self.reset_btn = QPushButton('🔄 重置')
        self.reset_btn.setStyleSheet(self._btn_style('#e17055', '#d63031'))
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(self._on_reset)
        btn_layout.addWidget(self.reset_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 状态信息
        self.info_label = QLabel('')
        self.info_label.setStyleSheet('font-size: 11px; color: #636e72; padding: 2px;')
        layout.addWidget(self.info_label)

        # 拖拽支持
        self.setAcceptDrops(True)

    # ==================== 按钮样式 ====================

    @staticmethod
    def _btn_style(color: str, hover: str) -> str:
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 6px 14px;
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:disabled {{ background-color: #dfe6e9; color: #b2bec3; }}
        """

    @staticmethod
    def _btn_toggle_style() -> str:
        return """
            QPushButton {
                background-color: #636e72;
                color: white;
                border: none;
                padding: 6px 14px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #2d3436; }
            QPushButton:checked { background-color: #e17055; }
            QPushButton:disabled { background-color: #dfe6e9; color: #b2bec3; }
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

        # 显示原图
        self.image_label.set_image(pixmap)
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px solid #3498db;
                border-radius: 8px;
                background-color: #2c3e50;
            }
        """)

        # 清空裁剪预览
        self.crop_preview_label.setPixmap(QPixmap())
        self.crop_preview_label.setText('暂无裁剪 - 点击「裁剪」按钮后在原图上框选区域')

        # 重置历史
        self._history.clear()
        self._history_index = -1
        self._push_state({
            'type': 'load',
            'crop_rect': None,
            'description': '加载原图'
        })

        # 启用按钮
        self.crop_btn.setEnabled(True)
        self.crop_btn.setChecked(False)
        self.reset_btn.setEnabled(True)
        self._update_undo_redo_state()

        # 状态信息
        w, h = pixmap.width(), pixmap.height()
        self.info_label.setText(f'图片尺寸: {w} × {h} px | 文件: {os.path.basename(filepath)}')

        self.image_loaded.emit(filepath)

    # ==================== 裁剪 ====================

    def _on_crop_toggled(self, checked: bool):
        self.image_label.set_crop_enabled(checked)
        if checked:
            self.info_label.setText('✂️ 裁剪模式：在原图上拖拽框选需要的区域')
        else:
            self.info_label.setText('')

    def _on_crop_defined(self, rect: tuple):
        """用户完成一次裁剪框选"""
        left, top, right, bottom = rect
        w = right - left
        h = bottom - top

        if w < 5 or h < 5:
            return

        # 生成裁剪结果预览
        if self._original_pixmap:
            cropped = self._original_pixmap.copy(left, top, w, h)
            # 缩放到预览区域
            scaled = cropped.scaled(
                self.crop_preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.crop_preview_label.setPixmap(scaled)
            self.crop_preview_label.setStyleSheet("""
                QLabel {
                    border: 2px solid #00b894;
                    border-radius: 6px;
                    background-color: #2c3e50;
                }
            """)

        # 保存到历史
        self._push_state({
            'type': 'crop',
            'crop_rect': rect,
            'description': f'裁剪 ({left},{top})-({right},{bottom})'
        })

        self.info_label.setText(
            f'✅ 裁剪区域: ({left}, {top}) → ({right}, {bottom}) | 尺寸: {w} × {h} px'
        )

        # 通知外部
        self.crop_changed.emit(rect)

    # ==================== 前进/后退 ====================

    def _push_state(self, state: dict):
        """压入新状态"""
        # 如果当前不在历史末尾，丢弃后面的状态
        if self._history_index < len(self._history) - 1:
            self._history = self._history[:self._history_index + 1]

        self._history.append(state)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        self._history_index = len(self._history) - 1
        self._update_undo_redo_state()

    def _on_undo(self):
        """撤回"""
        if self._history_index <= 0:
            return

        self._history_index -= 1
        self._apply_state(self._history[self._history_index])
        self._update_undo_redo_state()

    def _on_redo(self):
        """重做"""
        if self._history_index >= len(self._history) - 1:
            return

        self._history_index += 1
        self._apply_state(self._history[self._history_index])
        self._update_undo_redo_state()

    def _apply_state(self, state: dict):
        """应用某个历史状态"""
        crop_rect = state.get('crop_rect')

        if crop_rect is None:
            # 无裁剪 - 显示原图
            self.crop_preview_label.setPixmap(QPixmap())
            self.crop_preview_label.setText('暂无裁剪')
            self.crop_preview_label.setStyleSheet("""
                QLabel {
                    border: 1px solid #dcdde1;
                    border-radius: 6px;
                    background-color: #f5f6fa;
                    color: #b2bec3;
                    font-size: 11px;
                }
            """)
            self.image_label.clear_rubber_band()
            self.info_label.setText(f'↩ {state.get("description", "")}')
            self.crop_cleared.emit()
        else:
            # 有裁剪 - 显示裁剪结果
            left, top, right, bottom = crop_rect
            w = right - left
            h = bottom - top
            if self._original_pixmap:
                cropped = self._original_pixmap.copy(left, top, w, h)
                scaled = cropped.scaled(
                    self.crop_preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.crop_preview_label.setPixmap(scaled)
                self.crop_preview_label.setStyleSheet("""
                    QLabel {
                        border: 2px solid #00b894;
                        border-radius: 6px;
                        background-color: #2c3e50;
                    }
                """)

            self.info_label.setText(f'↩ {state.get("description", "")} | 尺寸: {w}×{h}')
            self.crop_changed.emit(crop_rect)

    def _update_undo_redo_state(self):
        """更新前进后退按钮状态"""
        self.undo_btn.setEnabled(self._history_index > 0)
        self.redo_btn.setEnabled(self._history_index < len(self._history) - 1)

        # 显示历史信息
        if self._history:
            current = self._history[self._history_index]
            pos_text = f'[{self._history_index + 1}/{len(self._history)}]'
            desc = current.get('description', '')
            # 追加到info
            current_info = self.info_label.text()
            if pos_text not in current_info:
                self.info_label.setText(f'{current_info}  {pos_text}'.strip())

    # ==================== 重置 ====================

    def _on_reset(self):
        """重置到原图"""
        self.crop_btn.setChecked(False)
        self.image_label.set_crop_enabled(False)
        self.image_label.clear_rubber_band()

        if self._original_pixmap:
            self.image_label.set_image(self._original_pixmap)

        self.crop_preview_label.setPixmap(QPixmap())
        self.crop_preview_label.setText('暂无裁剪')
        self.crop_preview_label.setStyleSheet("""
            QLabel {
                border: 1px solid #dcdde1;
                border-radius: 6px;
                background-color: #f5f6fa;
                color: #b2bec3;
                font-size: 11px;
            }
        """)

        self._push_state({
            'type': 'reset',
            'crop_rect': None,
            'description': '重置为原图'
        })

        self.info_label.setText('🔄 已重置为原图')
        self.crop_cleared.emit()

    # ==================== 获取当前裁剪 ====================

    def get_crop_rect(self):
        """获取当前生效的裁剪区域"""
        if self._history_index >= 0:
            state = self._history[self._history_index]
            return state.get('crop_rect')
        return None

    # ==================== 拖拽上传 ====================

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            filepath = urls[0].toLocalFile()
            exts = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')
            if filepath.lower().endswith(exts):
                self._load_image(filepath)