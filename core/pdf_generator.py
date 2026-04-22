"""
PDF图纸生成模块 v2
- 始终单页显示完整网格（自适应格子大小）
- 每29格画粗边线标识拼豆板边界
- 格子太小时省略色号文字，保证可读性
- 图例按需溢出到第二页，不截断
"""

import os
from typing import Dict, Tuple, List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color, black, white
import numpy as np

from .palette import Palette, BeadColor


class PDFGenerator:
    """PDF图纸生成器"""

    BOARD_SIZE = 29       # 拼豆标准板尺寸，每29格画一条粗线

    # 页面布局常量
    MARGIN = 12 * mm
    TITLE_H = 12 * mm     # 标题区高度
    COL_LABEL_H = 5 * mm  # 列编号区高度（网格上方）
    ROW_LABEL_W = 7 * mm  # 行编号区宽度（网格左侧）
    LEGEND_H = 55 * mm    # 图例区高度（底部）
    MAX_CELL = 12 * mm    # 格子最大尺寸

    # 图例布局
    LEGEND_COLS = 5
    LEGEND_ITEM_H = 4.5 * mm
    LEGEND_SWATCH = 3.5 * mm
    LEGEND_HEADER_H = 8 * mm

    def generate(
        self,
        filepath: str,
        color_id_map: np.ndarray,
        palette: Palette,
        usage_stats: Dict[str, int],
        title: str = "Beads Pattern",
        grid_width: int = 0,
        grid_height: int = 0
    ):
        h, w = color_id_map.shape
        grid_w = grid_width or w
        grid_h = grid_height or h

        cell_size = self._calc_cell_size(grid_w, grid_h)

        # 整理图例数据
        sorted_usage = sorted(usage_stats.items(), key=lambda x: x[1], reverse=True)

        c = canvas.Canvas(filepath, pagesize=A4)

        # 第一页：网格 + 尽量多的图例
        overflow = self._draw_grid_page(
            c, color_id_map, palette, sorted_usage,
            cell_size, title, grid_w, grid_h
        )

        # 第二页（如有）：剩余图例
        if overflow:
            c.showPage()
            self._draw_legend_overflow_page(c, palette, overflow, usage_stats, title)

        c.save()

    # ==================== 布局计算 ====================

    def _calc_cell_size(self, grid_w: int, grid_h: int) -> float:
        """计算让网格恰好单页显示的格子尺寸"""
        pw, ph = A4
        avail_w = pw - 2 * self.MARGIN - self.ROW_LABEL_W
        avail_h = ph - 2 * self.MARGIN - self.TITLE_H - self.COL_LABEL_H - self.LEGEND_H
        cell = min(avail_w / grid_w, avail_h / grid_h, self.MAX_CELL)
        return cell

    def _grid_origin(self, grid_w: int, grid_h: int, cell_size: float) -> Tuple[float, float]:
        """返回网格左下角坐标 (x, y)"""
        pw, ph = A4
        grid_x = self.MARGIN + self.ROW_LABEL_W
        grid_top = ph - self.MARGIN - self.TITLE_H - self.COL_LABEL_H
        grid_y = grid_top - grid_h * cell_size   # 底部 y
        return grid_x, grid_y

    # ==================== 第一页绘制 ====================

    def _draw_grid_page(
        self,
        c: canvas.Canvas,
        color_id_map: np.ndarray,
        palette: Palette,
        sorted_usage: List[Tuple[str, int]],
        cell_size: float,
        title: str,
        grid_w: int,
        grid_h: int
    ) -> Optional[List[Tuple[str, int]]]:
        """绘制第一页，返回未显示的图例项（如有）"""
        pw, ph = A4
        grid_x, grid_y = self._grid_origin(grid_w, grid_h, cell_size)

        # 1. 标题
        self._draw_title(c, title, grid_w, grid_h)

        # 2. 轴编号
        self._draw_axis_labels(c, cell_size, grid_x, grid_y, grid_h, grid_w)

        # 3. 彩色格子
        self._draw_grid(c, color_id_map, palette, cell_size, grid_x, grid_y, grid_h, grid_w)

        # 4. 板块边界线（每29格）
        self._draw_board_boundaries(c, cell_size, grid_x, grid_y, grid_h, grid_w)

        # 5. 图例（底部区域）
        legend_x = self.MARGIN
        legend_y = self.MARGIN         # 图例区底边 y
        legend_top = legend_y + self.LEGEND_H
        overflow = self._draw_legend(
            c, palette, sorted_usage, legend_x, legend_y, legend_top, pw
        )
        return overflow

    def _draw_title(self, c: canvas.Canvas, title: str, grid_w: int, grid_h: int):
        pw, ph = A4
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(black)
        c.drawCentredString(
            pw / 2,
            ph - self.MARGIN - 8 * mm,
            f"{title}  ({grid_w} × {grid_h})"
        )

    def _draw_axis_labels(
        self,
        c: canvas.Canvas,
        cell_size: float,
        grid_x: float,
        grid_y: float,
        rows: int,
        cols: int
    ):
        font_size = max(4, min(cell_size * 0.38, 7))
        c.setFont("Helvetica", font_size)
        c.setFillColor(black)

        # 列编号（网格上方）
        label_y = grid_y + rows * cell_size + 1.5 * mm
        for col in range(cols):
            x = grid_x + col * cell_size + cell_size / 2
            c.drawCentredString(x, label_y, str(col + 1))

        # 行编号（网格左侧）
        for row in range(rows):
            x = grid_x - 2 * mm
            y = grid_y + (rows - 1 - row) * cell_size + cell_size / 2 - font_size / 3
            c.drawRightString(x, y, str(row + 1))

    def _draw_grid(
        self,
        c: canvas.Canvas,
        color_id_map: np.ndarray,
        palette: Palette,
        cell_size: float,
        grid_x: float,
        grid_y: float,
        rows: int,
        cols: int
    ):
        """绘制彩色格子，格子足够大时叠加色号"""
        show_label = cell_size >= 3.0 * mm
        font_size = max(3.5, min(cell_size * 0.38, 7.5)) if show_label else 0
        if show_label:
            c.setFont("Helvetica", font_size)

        for row in range(rows):
            for col in range(cols):
                x = grid_x + col * cell_size
                y = grid_y + (rows - 1 - row) * cell_size  # PDF 坐标从下往上

                color_idx = color_id_map[row, col]
                bead = palette.colors[color_idx]
                r, g, b = bead.rgb

                c.setFillColor(Color(r / 255.0, g / 255.0, b / 255.0))
                c.setStrokeColor(Color(0.72, 0.72, 0.72))
                c.setLineWidth(0.25)
                c.rect(x, y, cell_size, cell_size, fill=1, stroke=1)

                if show_label:
                    text_color = self._contrast_color(r, g, b)
                    c.setFillColor(text_color)
                    c.drawCentredString(
                        x + cell_size / 2,
                        y + cell_size / 2 - font_size * 0.35,
                        bead.id
                    )

    def _draw_board_boundaries(
        self,
        c: canvas.Canvas,
        cell_size: float,
        grid_x: float,
        grid_y: float,
        rows: int,
        cols: int
    ):
        """每 BOARD_SIZE 格画一条深色粗线，标识拼豆板边界"""
        c.setStrokeColor(Color(0.12, 0.12, 0.12))
        c.setLineWidth(1.4)

        grid_w_px = cols * cell_size
        grid_h_px = rows * cell_size

        # 垂直线
        for i in range(0, cols + 1, self.BOARD_SIZE):
            x = grid_x + i * cell_size
            c.line(x, grid_y, x, grid_y + grid_h_px)

        # 水平线
        for i in range(0, rows + 1, self.BOARD_SIZE):
            y = grid_y + i * cell_size
            c.line(grid_x, y, grid_x + grid_w_px, y)

        # 外框加粗
        c.setLineWidth(2.0)
        c.rect(grid_x, grid_y, grid_w_px, grid_h_px, fill=0, stroke=1)

    # ==================== 图例 ====================

    def _draw_legend(
        self,
        c: canvas.Canvas,
        palette: Palette,
        sorted_usage: List[Tuple[str, int]],
        x_start: float,
        y_bottom: float,
        y_top: float,
        page_width: float
    ) -> Optional[List[Tuple[str, int]]]:
        """
        在 [y_bottom, y_top] 区域绘制图例，返回未能显示的剩余项
        """
        total_beads = sum(cnt for _, cnt in sorted_usage)

        # 标题行
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(black)
        header_y = y_top - 5 * mm
        c.drawString(x_start, header_y, f"Color Legend  —  {len(sorted_usage)} colors  /  {total_beads:,} beads total")

        item_w = (page_width - 2 * self.MARGIN) / self.LEGEND_COLS
        max_rows = int((y_top - y_bottom - self.LEGEND_HEADER_H) / self.LEGEND_ITEM_H)
        max_items = max_rows * self.LEGEND_COLS

        col_idx = 0
        cur_y = y_top - self.LEGEND_HEADER_H

        for i, (color_id, count) in enumerate(sorted_usage):
            if i >= max_items:
                # 返回剩余的溢出项
                return sorted_usage[i:]

            bead = palette.get_color_by_id(color_id)
            if bead is None:
                continue

            x = x_start + col_idx * item_w

            # 色块
            r, g, b = bead.rgb
            c.setFillColor(Color(r / 255.0, g / 255.0, b / 255.0))
            c.setStrokeColor(Color(0.5, 0.5, 0.5))
            c.setLineWidth(0.4)
            c.rect(x, cur_y - self.LEGEND_SWATCH * 0.7, self.LEGEND_SWATCH, self.LEGEND_SWATCH, fill=1, stroke=1)

            # 文字
            c.setFillColor(black)
            c.setFont("Helvetica", 5.5)
            pct = count / total_beads * 100
            label = f"{bead.id}  {count} ({pct:.1f}%)"
            c.drawString(x + self.LEGEND_SWATCH + 1 * mm, cur_y - 1 * mm, label)

            col_idx += 1
            if col_idx >= self.LEGEND_COLS:
                col_idx = 0
                cur_y -= self.LEGEND_ITEM_H

        return None  # 全部显示完毕

    def _draw_legend_overflow_page(
        self,
        c: canvas.Canvas,
        palette: Palette,
        overflow: List[Tuple[str, int]],
        usage_stats: Dict[str, int],
        title: str
    ):
        """第二页：显示溢出的图例"""
        pw, ph = A4
        total_beads = sum(usage_stats.values())

        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(black)
        c.drawCentredString(pw / 2, ph - self.MARGIN - 7 * mm,
                            f"{title}  —  Color Legend (continued)")

        item_w = (pw - 2 * self.MARGIN) / self.LEGEND_COLS
        max_rows = int((ph - 2 * self.MARGIN - 14 * mm) / self.LEGEND_ITEM_H)

        col_idx = 0
        cur_y = ph - self.MARGIN - 16 * mm

        for color_id, count in overflow:
            bead = palette.get_color_by_id(color_id)
            if bead is None:
                continue

            x = self.MARGIN + col_idx * item_w
            r, g, b = bead.rgb
            c.setFillColor(Color(r / 255.0, g / 255.0, b / 255.0))
            c.setStrokeColor(Color(0.5, 0.5, 0.5))
            c.setLineWidth(0.4)
            c.rect(x, cur_y - self.LEGEND_SWATCH * 0.7, self.LEGEND_SWATCH, self.LEGEND_SWATCH, fill=1, stroke=1)

            c.setFillColor(black)
            c.setFont("Helvetica", 5.5)
            pct = count / total_beads * 100
            label = f"{bead.id}  {count} ({pct:.1f}%)"
            c.drawString(x + self.LEGEND_SWATCH + 1 * mm, cur_y - 1 * mm, label)

            col_idx += 1
            if col_idx >= self.LEGEND_COLS:
                col_idx = 0
                cur_y -= self.LEGEND_ITEM_H
                if cur_y < self.MARGIN:
                    break  # 第二页也满了（颜色极多时）

    # ==================== 工具方法 ====================

    @staticmethod
    def _contrast_color(r: int, g: int, b: int) -> Color:
        """按背景亮度选黑/白文字"""
        lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return black if lum > 0.5 else white
