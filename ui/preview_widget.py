"""
预览组件
显示像素化后的拼豆效果预览
"""

import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter, QPen
from typing import Dict
from core.palette import Palette


class BeadsPreviewLabel(QLabel):
    """拼豆预览标签 - 带网格线的像素预览"""

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._matched_rgb = None
        self._cell_size = 10
        self._show_grid = True

    def set_bead_data(self, matched_rgb: np.ndarray, cell_size: int = 10):
        """设置拼豆数据并渲染"""
        self._matched_rgb = matched_rgb
        self._cell_size = cell_size
        self._render()

    def _render(self):
        if self._matched_rgb is None:
            return

        h, w, _ = self._matched_rgb.shape
        cs = self._cell_size
        img_w = w * cs
        img_h = h * cs

        image = QImage(img_w, img_h, QImage.Format.Format_RGB32)
        painter = QPainter(image)

        # 绘制格子
        for row in range(h):
            for col in range(w):
                r, g, b = self._matched_rgb[row, col]
                color = QColor(int(r), int(g), int(b))
                painter.fillRect(col * cs, row * cs, cs, cs, color)

        # 绘制网格线
        if self._show_grid and cs >= 4:
            pen = QPen(QColor(200, 200, 200, 100))
            pen.setWidth(1)
            painter.setPen(pen)

            for row in range(h + 1):
                painter.drawLine(0, row * cs, img_w, row * cs)
            for col in range(w + 1):
                painter.drawLine(col * cs, 0, col * cs, img_h)

        painter.end()

        pixmap = QPixmap.fromImage(image)
        self.setPixmap(pixmap)
        self.setFixedSize(img_w, img_h)


class PreviewWidget(QWidget):
    """预览组件"""

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 标题
        title = QLabel("👀 效果预览")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        layout.addWidget(title)

        # 上下分割
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 上：图片预览（可滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: #ecf0f1;
            }
        """)

        self.preview_label = BeadsPreviewLabel()
        self.preview_label.setText('预览区域\n\n上传图片并点击「预览效果」')
        self.preview_label.setStyleSheet("color: #95a5a6; font-size: 14px;")
        scroll.setWidget(self.preview_label)
        splitter.addWidget(scroll)

        # 下：用量统计表格
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 5, 0, 0)

        stats_title = QLabel("📊 颜色用量统计")
        stats_title.setStyleSheet("font-size: 13px; font-weight: bold;")
        stats_layout.addWidget(stats_title)

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(5)
        self.stats_table.setHorizontalHeaderLabels(
            ["颜色", "编号", "名称", "数量", "占比"]
        )
        self.stats_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.stats_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.stats_table.setMaximumHeight(250)
        stats_layout.addWidget(self.stats_table)

        # 总计标签
        self.total_label = QLabel("")
        self.total_label.setStyleSheet(
            "font-size: 12px; font-weight: bold; padding: 5px; color: #2c3e50;"
        )
        stats_layout.addWidget(self.total_label)

        splitter.addWidget(stats_widget)
        splitter.setSizes([500, 250])

        layout.addWidget(splitter, 1)

    def set_original_image(self, filepath: str):
        """显示原图预览"""
        pass  # 可选：在某处显示原图对比

    def update_crop(self, rect: tuple):
        """更新裁剪区域"""
        pass

    def update_preview(
        self,
        matched_rgb: np.ndarray,
        color_id_map: np.ndarray,
        palette: Palette,
        usage_stats: Dict[str, int]
    ):
        """更新预览"""
        h, w, _ = matched_rgb.shape

        # 动态计算cell_size使预览合适
        cell_size = max(4, min(12, 600 // max(w, h)))
        self.preview_label.setStyleSheet("")
        self.preview_label.set_bead_data(matched_rgb, cell_size)

        # 更新统计表格
        self._update_stats_table(palette, usage_stats)

    def _update_stats_table(
        self, palette: Palette, usage_stats: Dict[str, int]
    ):
        """更新用量统计表格"""
        sorted_stats = sorted(
            usage_stats.items(), key=lambda x: x[1], reverse=True
        )
        total = sum(usage_stats.values())

        self.stats_table.setRowCount(len(sorted_stats))

        for row, (color_id, count) in enumerate(sorted_stats):
            bead_color = palette.get_color_by_id(color_id)
            if not bead_color:
                continue

            # 颜色色块
            color_item = QTableWidgetItem()
            r, g, b = bead_color.rgb
            color_item.setBackground(QColor(r, g, b))
            self.stats_table.setItem(row, 0, color_item)

            # 编号
            self.stats_table.setItem(row, 1, QTableWidgetItem(bead_color.id))

            # 名称
            self.stats_table.setItem(row, 2, QTableWidgetItem(bead_color.name))

            # 数量
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.stats_table.setItem(row, 3, count_item)

            # 占比
            pct = f"{count / total * 100:.1f}%"
            pct_item = QTableWidgetItem(pct)
            pct_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.stats_table.setItem(row, 4, pct_item)

        self.total_label.setText(
            f"总计: {total} 颗豆子 | {len(sorted_stats)} 种颜色"
        )