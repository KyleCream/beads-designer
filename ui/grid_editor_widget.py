"""
图纸编辑器组件
用户可以点击格子修改颜色，最终导出PDF
"""

import numpy as np
from collections import Counter
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QSlider, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QSizePolicy, QDialog,
    QGridLayout, QPushButton, QToolTip
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter, QPen, QCursor

from core.palette import Palette, BeadColor
from core.pixelizer import PixelizeResult


class ColorPickerDialog(QDialog):
    """颜色选择弹窗 - 从色板中选色"""

    def __init__(self, palette: Palette, current_color_id: str = '', parent=None):
        super().__init__(parent)
        self.setWindowTitle('选择颜色')
        self.palette = palette
        self.selected_color: BeadColor = None

        self.setMinimumWidth(400)
        self._init_ui(current_color_id)

    def _init_ui(self, current_id: str):
        layout = QVBoxLayout(self)

        hint = QLabel(f'从 {self.palette.brand} 色板中选择颜色:')
        hint.setStyleSheet('font-size: 12px; margin-bottom: 5px;')
        layout.addWidget(hint)

        # 颜色网格
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(400)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(3)

        cols = 8
        for i, color in enumerate(self.palette.colors):
            btn = QPushButton()
            btn.setFixedSize(42, 42)
            r, g, b = color.rgb
            # 当前选中高亮
            border = '3px solid #e74c3c' if color.id == current_id else '1px solid #ccc'
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgb({r},{g},{b});
                    border: {border}; border-radius: 4px;
                }}
                QPushButton:hover {{
                    border: 2px solid #3498db;
                }}
            """)
            btn.setToolTip(f'{color.id}: {color.name}\nRGB({r},{g},{b})')
            btn.clicked.connect(lambda checked, c=color: self._select(c))
            grid.addWidget(btn, i // cols, i % cols)

        scroll.setWidget(grid_widget)
        layout.addWidget(scroll)

        # 当前选择显示
        self.selection_label = QLabel('点击颜色选择')
        self.selection_label.setStyleSheet(
            'font-size: 12px; padding: 5px; font-weight: bold;'
        )
        layout.addWidget(self.selection_label)

    def _select(self, color: BeadColor):
        self.selected_color = color
        r, g, b = color.rgb
        self.selection_label.setText(f'已选: {color.id} - {color.name}')
        self.selection_label.setStyleSheet(
            f'font-size: 12px; padding: 5px; font-weight: bold;'
            f'background-color: rgb({r},{g},{b});'
            f'color: {"#000" if (0.299*r + 0.587*g + 0.114*b) > 128 else "#fff"};'
            f'border-radius: 4px;'
        )
        self.accept()


class GridCanvas(QWidget):
    """可交互的网格画布"""

    cell_clicked = pyqtSignal(int, int)  # row, col

    def __init__(self):
        super().__init__()
        self._matched_rgb = None
        self._cell_size = 10
        self._zoom = 1.0
        self._show_grid = True
        self._hover_row = -1
        self._hover_col = -1

        self.setMouseTracking(True)

    def set_data(self, matched_rgb: np.ndarray, cell_size: int = 10):
        self._matched_rgb = matched_rgb
        self._cell_size = cell_size
        self._update_size()
        self.update()

    def set_zoom(self, zoom: float):
        self._zoom = max(0.5, min(zoom, 5.0))
        self._update_size()
        self.update()

    def _update_size(self):
        if self._matched_rgb is None:
            return
        h, w, _ = self._matched_rgb.shape
        cs = int(self._cell_size * self._zoom)
        self.setFixedSize(w * cs + 1, h * cs + 1)

    def paintEvent(self, event):
        if self._matched_rgb is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        h, w, _ = self._matched_rgb.shape
        cs = int(self._cell_size * self._zoom)

        # 绘制格子
        for row in range(h):
            for col in range(w):
                r, g, b = self._matched_rgb[row, col]
                painter.fillRect(col * cs, row * cs, cs, cs, QColor(int(r), int(g), int(b)))

        # 网格线
        if self._show_grid and cs >= 4:
            pen = QPen(QColor(180, 180, 180, 80))
            pen.setWidth(1)
            painter.setPen(pen)
            for row in range(h + 1):
                painter.drawLine(0, row * cs, w * cs, row * cs)
            for col in range(w + 1):
                painter.drawLine(col * cs, 0, col * cs, h * cs)

        # 悬停高亮
        if 0 <= self._hover_row < h and 0 <= self._hover_col < w:
            pen = QPen(QColor(255, 255, 0, 200))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(
                self._hover_col * cs, self._hover_row * cs, cs, cs
            )

        painter.end()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        cs = int(self._cell_size * self._zoom)
        if cs <= 0 or self._matched_rgb is None:
            return
        col = pos.x() // cs
        row = pos.y() // cs
        h, w, _ = self._matched_rgb.shape

        if 0 <= row < h and 0 <= col < w:
            if row != self._hover_row or col != self._hover_col:
                self._hover_row = row
                self._hover_col = col
                self.update()
                r, g, b = self._matched_rgb[row, col]
                QToolTip.showText(
                    QCursor.pos(),
                    f'({row + 1}, {col + 1})\nRGB({r},{g},{b})'
                )
        else:
            self._hover_row = -1
            self._hover_col = -1
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._matched_rgb is not None:
            cs = int(self._cell_size * self._zoom)
            if cs <= 0:
                return
            col = event.pos().x() // cs
            row = event.pos().y() // cs
            h, w, _ = self._matched_rgb.shape
            if 0 <= row < h and 0 <= col < w:
                self.cell_clicked.emit(row, col)

    def leaveEvent(self, event):
        self._hover_row = -1
        self._hover_col = -1
        self.update()


class GridEditorWidget(QWidget):
    """图纸编辑器"""

    grid_modified = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._result: PixelizeResult = None
        self._is_modified = False
        self._init_ui()

    @property
    def is_modified(self) -> bool:
        return self._is_modified

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        toolbar.addWidget(QLabel('🔍 缩放:'))

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(50, 500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(150)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        toolbar.addWidget(self.zoom_slider)

        self.zoom_label = QLabel('100%')
        self.zoom_label.setFixedWidth(45)
        toolbar.addWidget(self.zoom_label)

        self.zoom_fit_btn = QPushButton('适应窗口')
        self.zoom_fit_btn.setStyleSheet("""
            QPushButton {
                background: #74b9ff; color: white; border: none;
                padding: 4px 10px; border-radius: 3px; font-size: 11px;
            }
            QPushButton:hover { background: #0984e3; }
        """)
        self.zoom_fit_btn.clicked.connect(self._on_zoom_fit)
        toolbar.addWidget(self.zoom_fit_btn)

        toolbar.addStretch()

        self.edit_info = QLabel('点击格子可修改颜色')
        self.edit_info.setStyleSheet('font-size: 11px; color: #636e72;')
        toolbar.addWidget(self.edit_info)

        layout.addLayout(toolbar)

        # 主内容 - 水平分割：画布 + 统计
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 画布（可滚动）
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #dcdde1;
                border-radius: 4px;
                background-color: #ecf0f1;
            }
        """)

        self.canvas = GridCanvas()
        self.canvas.cell_clicked.connect(self._on_cell_clicked)
        self.scroll_area.setWidget(self.canvas)
        splitter.addWidget(self.scroll_area)

        # 右侧统计
        stats_panel = QWidget()
        stats_panel.setMaximumWidth(250)
        stats_layout = QVBoxLayout(stats_panel)
        stats_layout.setContentsMargins(5, 0, 0, 0)
        stats_layout.setSpacing(4)

        stats_title = QLabel('📊 颜色统计')
        stats_title.setStyleSheet('font-size: 13px; font-weight: bold;')
        stats_layout.addWidget(stats_title)

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(4)
        self.stats_table.setHorizontalHeaderLabels(['色', '编号', '数量', '%'])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stats_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.setStyleSheet("""
            QTableWidget { border: 1px solid #dcdde1; font-size: 10px; }
            QHeaderView::section {
                background: #f5f6fa; border: none;
                border-bottom: 1px solid #dcdde1;
                padding: 3px; font-size: 10px; font-weight: bold;
            }
        """)
        stats_layout.addWidget(self.stats_table, 1)

        self.total_label = QLabel('')
        self.total_label.setStyleSheet('font-size: 11px; font-weight: bold; color: #2d3436;')
        stats_layout.addWidget(self.total_label)

        splitter.addWidget(stats_panel)
        splitter.setSizes([600, 220])

        layout.addWidget(splitter, 1)

    # ==================== 数据操作 ====================

    def load_result(self, result: PixelizeResult):
        """加载像素化结果"""
        self._result = result
        self._is_modified = False

        # 深拷贝可编辑的数据
        self._edit_rgb = result.matched_rgb.copy()
        self._edit_index_map = result.color_index_map.copy()

        cell_size = max(6, min(14, 700 // max(result.grid_width, result.grid_height)))
        self.canvas.set_data(self._edit_rgb, cell_size)

        self._refresh_stats()
        self._on_zoom_fit()

    def get_current_result(self) -> PixelizeResult:
        """获取当前编辑后的结果"""
        if self._result is None:
            return None

        # 重新计算统计
        usage = {}
        h, w = self._edit_index_map.shape
        for row in range(h):
            for col in range(w):
                idx = self._edit_index_map[row, col]
                color = self._result.palette.colors[idx]
                usage[color.id] = usage.get(color.id, 0) + 1

        # 创建新结果
        result = PixelizeResult()
        result.matched_rgb = self._edit_rgb.copy()
        result.color_index_map = self._edit_index_map.copy()
        result.usage_stats = usage
        result.palette = self._result.palette
        result.grid_width = self._result.grid_width
        result.grid_height = self._result.grid_height
        result.raw_pixels = self._result.raw_pixels
        return result

    # ==================== 编辑 ====================

    def _on_cell_clicked(self, row: int, col: int):
        """点击格子，弹出颜色选择"""
        if self._result is None:
            return

        current_idx = self._edit_index_map[row, col]
        current_color = self._result.palette.colors[current_idx]

        dialog = ColorPickerDialog(
            self._result.palette,
            current_color.id,
            self
        )
        if dialog.exec() and dialog.selected_color:
            new_color = dialog.selected_color
            # 找到新颜色在palette中的索引
            for i, c in enumerate(self._result.palette.colors):
                if c.id == new_color.id:
                    self._edit_index_map[row, col] = i
                    self._edit_rgb[row, col] = list(new_color.rgb)
                    break

            self._is_modified = True
            self.canvas.set_data(self._edit_rgb, self.canvas._cell_size)
            self._refresh_stats()
            self.grid_modified.emit()
            self.edit_info.setText(
                f'已修改 ({row + 1},{col + 1}) -> {new_color.id} {new_color.name}'
            )

    # ==================== 缩放 ====================

    def _on_zoom_changed(self, value: int):
        zoom = value / 100.0
        self.zoom_label.setText(f'{value}%')
        self.canvas.set_zoom(zoom)

    def _on_zoom_fit(self):
        """自适应缩放"""
        if self._result is None:
            return

        viewport = self.scroll_area.viewport().size()
        gw = self._result.grid_width
        gh = self._result.grid_height
        cs = self.canvas._cell_size

        zoom_w = viewport.width() / (gw * cs) if gw * cs > 0 else 1
        zoom_h = viewport.height() / (gh * cs) if gh * cs > 0 else 1
        zoom = min(zoom_w, zoom_h) * 0.95

        zoom_pct = int(zoom * 100)
        zoom_pct = max(50, min(zoom_pct, 500))
        self.zoom_slider.setValue(zoom_pct)

    def wheelEvent(self, event):
        """鼠标滚轮缩放"""
        delta = event.angleDelta().y()
        current = self.zoom_slider.value()
        step = 10 if abs(delta) < 200 else 25
        if delta > 0:
            self.zoom_slider.setValue(min(current + step, 500))
        else:
            self.zoom_slider.setValue(max(current - step, 50))

    # ==================== 统计 ====================

    def _refresh_stats(self):
        if self._result is None:
            return

        # 重新统计
        usage = {}
        h, w = self._edit_index_map.shape
        for row in range(h):
            for col in range(w):
                idx = self._edit_index_map[row, col]
                color = self._result.palette.colors[idx]
                usage[color.id] = usage.get(color.id, 0) + 1

        sorted_stats = sorted(usage.items(), key=lambda x: x[1], reverse=True)
        total = sum(usage.values())

        self.stats_table.setRowCount(len(sorted_stats))
        for i, (cid, count) in enumerate(sorted_stats):
            color = self._result.palette.get_color_by_id(cid)
            if not color:
                continue

            # 色块
            item = QTableWidgetItem()
            r, g, b = color.rgb
            item.setBackground(QColor(r, g, b))
            self.stats_table.setItem(i, 0, item)

            # 编号
            self.stats_table.setItem(i, 1, QTableWidgetItem(color.id))

            # 数量
            ci = QTableWidgetItem(str(count))
            ci.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.stats_table.setItem(i, 2, ci)

            # 占比
            pi = QTableWidgetItem(f'{count / total * 100:.1f}')
            pi.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.stats_table.setItem(i, 3, pi)

        self.total_label.setText(f'共 {total} 颗 | {len(sorted_stats)} 色')