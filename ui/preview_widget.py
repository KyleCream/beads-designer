"""
预览组件 v2 - 支持缩放
"""

import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QSlider, QPushButton
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter, QPen
from typing import Dict
from core.palette import Palette


class ZoomablePreviewLabel(QLabel):
    """可缩放的预览标签"""

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._matched_rgb = None
        self._base_cell_size = 10
        self._zoom = 1.0

    def set_bead_data(self, matched_rgb: np.ndarray, cell_size: int = 10):
        self._matched_rgb = matched_rgb
        self._base_cell_size = cell_size
        self._render()

    def set_zoom(self, zoom: float):
        self._zoom = max(0.3, min(zoom, 5.0))
        self._render()

    def _render(self):
        if self._matched_rgb is None:
            return

        h, w, _ = self._matched_rgb.shape
        cs = max(2, int(self._base_cell_size * self._zoom))
        img_w = w * cs
        img_h = h * cs

        image = QImage(img_w, img_h, QImage.Format.Format_RGB32)
        painter = QPainter(image)

        for row in range(h):
            for col in range(w):
                r, g, b = self._matched_rgb[row, col]
                painter.fillRect(col * cs, row * cs, cs, cs, QColor(int(r), int(g), int(b)))

        if cs >= 4:
            pen = QPen(QColor(200, 200, 200, 80))
            pen.setWidth(1)
            painter.setPen(pen)
            for row in range(h + 1):
                painter.drawLine(0, row * cs, img_w, row * cs)
            for col in range(w + 1):
                painter.drawLine(col * cs, 0, col * cs, img_h)

        painter.end()

        self.setPixmap(QPixmap.fromImage(image))
        self.setFixedSize(img_w, img_h)


class PreviewWidget(QWidget):
    """预览组件"""

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 缩放工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        toolbar.addWidget(QLabel('🔍 缩放:'))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(30, 500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(150)
        self.zoom_slider.valueChanged.connect(self._on_zoom)
        toolbar.addWidget(self.zoom_slider)

        self.zoom_label = QLabel('100%')
        self.zoom_label.setFixedWidth(45)
        toolbar.addWidget(self.zoom_label)

        fit_btn = QPushButton('适应')
        fit_btn.setStyleSheet("""
            QPushButton {
                background: #74b9ff; color: white; border: none;
                padding: 3px 8px; border-radius: 3px; font-size: 11px;
            }
            QPushButton:hover { background: #0984e3; }
        """)
        fit_btn.clicked.connect(self._on_fit)
        toolbar.addWidget(fit_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 内容分割
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 预览图
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #dcdde1; border-radius: 4px;
                background-color: #f5f6fa;
            }
        """)

        self.preview_label = ZoomablePreviewLabel()
        self.preview_label.setText('预览区域\n\n上传图片并点击「预览效果」')
        self.preview_label.setStyleSheet('color: #95a5a6; font-size: 13px;')
        self.scroll_area.setWidget(self.preview_label)
        splitter.addWidget(self.scroll_area)

        # 统计表
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 5, 0, 0)
        stats_layout.setSpacing(4)

        stats_layout.addWidget(QLabel('📊 颜色统计'))

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(5)
        self.stats_table.setHorizontalHeaderLabels(['颜色', '编号', '名称', '数量', '占比'])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stats_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.setMaximumHeight(200)
        self.stats_table.setStyleSheet("""
            QTableWidget { border: 1px solid #dcdde1; font-size: 10px; }
            QHeaderView::section {
                background: #f5f6fa; border: none;
                border-bottom: 1px solid #dcdde1; padding: 3px; font-size: 10px;
            }
        """)
        stats_layout.addWidget(self.stats_table)

        self.total_label = QLabel('')
        self.total_label.setStyleSheet('font-size: 11px; font-weight: bold; color: #2d3436;')
        stats_layout.addWidget(self.total_label)

        splitter.addWidget(stats_widget)
        splitter.setSizes([450, 180])
        layout.addWidget(splitter, 1)

    def _on_zoom(self, value: int):
        self.zoom_label.setText(f'{value}%')
        self.preview_label.set_zoom(value / 100.0)

    def _on_fit(self):
        if self.preview_label._matched_rgb is None:
            return
        h, w, _ = self.preview_label._matched_rgb.shape
        cs = self.preview_label._base_cell_size
        vp = self.scroll_area.viewport().size()
        zw = vp.width() / (w * cs) if w * cs > 0 else 1
        zh = vp.height() / (h * cs) if h * cs > 0 else 1
        z = int(min(zw, zh) * 95)
        z = max(30, min(z, 500))
        self.zoom_slider.setValue(z)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        cur = self.zoom_slider.value()
        step = 10
        if delta > 0:
            self.zoom_slider.setValue(min(cur + step, 500))
        else:
            self.zoom_slider.setValue(max(cur - step, 30))

    def set_original_image(self, filepath: str):
        pass

    def update_crop(self, rect: tuple):
        pass

    def update_preview(
        self, matched_rgb: np.ndarray, color_id_map: np.ndarray,
        palette: Palette, usage_stats: Dict[str, int]
    ):
        h, w, _ = matched_rgb.shape
        cell_size = max(6, min(14, 700 // max(w, h)))

        self.preview_label.setStyleSheet('')
        self.preview_label.set_bead_data(matched_rgb, cell_size)
        self._on_fit()

        self._update_stats(palette, usage_stats)

    def _update_stats(self, palette: Palette, usage_stats: Dict[str, int]):
        sorted_stats = sorted(usage_stats.items(), key=lambda x: x[1], reverse=True)
        total = sum(usage_stats.values())

        self.stats_table.setRowCount(len(sorted_stats))
        for row, (cid, count) in enumerate(sorted_stats):
            c = palette.get_color_by_id(cid)
            if not c:
                continue

            item = QTableWidgetItem()
            r, g, b = c.rgb
            item.setBackground(QColor(r, g, b))
            self.stats_table.setItem(row, 0, item)
            self.stats_table.setItem(row, 1, QTableWidgetItem(c.id))
            self.stats_table.setItem(row, 2, QTableWidgetItem(c.name))

            ci = QTableWidgetItem(str(count))
            ci.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.stats_table.setItem(row, 3, ci)

            pi = QTableWidgetItem(f'{count / total * 100:.1f}%')
            pi.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.stats_table.setItem(row, 4, pi)

        self.total_label.setText(f'共 {total} 颗 | {len(sorted_stats)} 色')