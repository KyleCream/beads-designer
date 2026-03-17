"""
PDF图纸生成模块
生成带彩色格子、色号标注、图例和用量统计的PDF拼豆图纸
"""

import os
from typing import Dict, Tuple, List
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color, black, white, HexColor
import numpy as np

from .palette import Palette, BeadColor


class PDFGenerator:
    """PDF图纸生成器"""

    def __init__(self):
        # 页面设置
        self.page_size = A4
        self.margin = 15 * mm
        self.title_height = 12 * mm
        self.legend_area_height = 60 * mm  # 图例和统计区域
        self.min_cell_size = 4 * mm  # 格子最小尺寸
        self.max_cell_size = 12 * mm  # 格子最大尺寸

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
        """
        生成PDF图纸

        Args:
            filepath: 输出PDF路径
            color_id_map: 颜色索引映射 shape=(H, W)
            palette: 使用的色板
            usage_stats: 颜色用量统计
            title: 图纸标题
        """
        h, w = color_id_map.shape
        grid_width = grid_width or w
        grid_height = grid_height or h

        # 计算格子大小和是否需要分页
        cell_size, pages_info = self._calculate_layout(w, h)

        c = canvas.Canvas(filepath, pagesize=self.page_size)

        for page_idx, page_info in enumerate(pages_info):
            if page_idx > 0:
                c.showPage()

            self._draw_page(
                c, color_id_map, palette, usage_stats,
                cell_size, page_info, title, w, h
            )

        c.save()

    def _calculate_layout(
        self, grid_w: int, grid_h: int
    ) -> Tuple[float, List[Dict]]:
        """
        计算布局：格子大小和分页信息
        """
        page_w, page_h = self.page_size
        available_w = page_w - 2 * self.margin
        available_h = page_h - 2 * self.margin - self.title_height - self.legend_area_height

        # 计算单页能容纳的格子大小
        cell_w = available_w / grid_w
        cell_h = available_h / grid_h
        cell_size = min(cell_w, cell_h)

        # 限制格子大小范围
        cell_size = max(self.min_cell_size, min(cell_size, self.max_cell_size))

        # 计算单页能放多少格子
        cols_per_page = max(1, int(available_w / cell_size))
        rows_per_page = max(1, int(available_h / cell_size))

        # 分页
        pages = []
        for row_start in range(0, grid_h, rows_per_page):
            for col_start in range(0, grid_w, cols_per_page):
                row_end = min(row_start + rows_per_page, grid_h)
                col_end = min(col_start + cols_per_page, grid_w)
                pages.append({
                    "row_start": row_start,
                    "row_end": row_end,
                    "col_start": col_start,
                    "col_end": col_end,
                })

        return cell_size, pages

    def _draw_page(
        self,
        c: canvas.Canvas,
        color_id_map: np.ndarray,
        palette: Palette,
        usage_stats: Dict[str, int],
        cell_size: float,
        page_info: Dict,
        title: str,
        total_w: int,
        total_h: int
    ):
        """绘制单页"""
        page_w, page_h = self.page_size

        row_start = page_info["row_start"]
        row_end = page_info["row_end"]
        col_start = page_info["col_start"]
        col_end = page_info["col_end"]
        rows = row_end - row_start
        cols = col_end - col_start

        # 网格区域居中
        grid_total_w = cols * cell_size
        grid_total_h = rows * cell_size
        grid_x = self.margin + (page_w - 2 * self.margin - grid_total_w) / 2
        grid_y = page_h - self.margin - self.title_height - grid_total_h

        # 1. 绘制标题
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(
            page_w / 2,
            page_h - self.margin - 8 * mm,
            f"{title} ({total_w}×{total_h})"
        )
        # 分页标注
        c.setFont("Helvetica", 8)
        c.drawCentredString(
            page_w / 2,
            page_h - self.margin - 12 * mm,
            f"Rows {row_start + 1}-{row_end}, Cols {col_start + 1}-{col_end}"
        )

        # 2. 绘制彩色格子 + 色号
        self._draw_grid(
            c, color_id_map, palette, cell_size,
            grid_x, grid_y, row_start, row_end, col_start, col_end
        )

        # 3. 绘制行列编号
        self._draw_axis_labels(
            c, cell_size, grid_x, grid_y,
            row_start, row_end, col_start, col_end
        )

        # 4. 绘制图例和用量统计（底部）
        legend_y = self.margin + self.legend_area_height
        self._draw_legend_and_stats(
            c, palette, usage_stats, self.margin, self.margin, page_w
        )

    def _draw_grid(
        self,
        c: canvas.Canvas,
        color_id_map: np.ndarray,
        palette: Palette,
        cell_size: float,
        start_x: float,
        start_y: float,
        row_start: int,
        row_end: int,
        col_start: int,
        col_end: int
    ):
        """绘制彩色格子和色号标注"""
        for row in range(row_start, row_end):
            for col in range(col_start, col_end):
                x = start_x + (col - col_start) * cell_size
                y = start_y + (row_end - 1 - row) * cell_size  # PDF坐标从下往上

                color_idx = color_id_map[row, col]
                bead_color = palette.colors[color_idx]
                r, g, b = bead_color.rgb

                # 填充颜色
                fill_color = Color(r / 255.0, g / 255.0, b / 255.0)
                c.setFillColor(fill_color)
                c.setStrokeColor(Color(0.7, 0.7, 0.7))
                c.setLineWidth(0.3)
                c.rect(x, y, cell_size, cell_size, fill=1, stroke=1)

                # 色号标注 - 根据背景色选择文字颜色
                text_color = self._get_contrast_color(r, g, b)
                c.setFillColor(text_color)

                # 动态调整字体大小
                font_size = max(3, min(cell_size * 0.4, 8))
                c.setFont("Helvetica", font_size)

                # 短编号（去掉品牌前缀如果太长）
                label = bead_color.id
                if len(label) > 3 and cell_size < 6 * mm:
                    label = label[-2:]  # 只显示数字部分

                c.drawCentredString(
                    x + cell_size / 2,
                    y + cell_size / 2 - font_size / 3,
                    label
                )

    def _draw_axis_labels(
        self,
        c: canvas.Canvas,
        cell_size: float,
        grid_x: float,
        grid_y: float,
        row_start: int,
        row_end: int,
        col_start: int,
        col_end: int
    ):
        """绘制行列编号"""
        c.setFillColor(black)
        font_size = max(4, min(cell_size * 0.35, 7))
        c.setFont("Helvetica", font_size)

        rows = row_end - row_start
        cols = col_end - col_start

        # 列编号（顶部）
        for col in range(col_start, col_end):
            x = grid_x + (col - col_start) * cell_size + cell_size / 2
            y = grid_y + rows * cell_size + 1 * mm
            c.drawCentredString(x, y, str(col + 1))

        # 行编号（左侧）
        for row in range(row_start, row_end):
            x = grid_x - 2 * mm
            y = grid_y + (row_end - 1 - row) * cell_size + cell_size / 2 - font_size / 3
            c.drawRightString(x, y, str(row + 1))

    def _draw_legend_and_stats(
        self,
        c: canvas.Canvas,
        palette: Palette,
        usage_stats: Dict[str, int],
        x_start: float,
        y_start: float,
        page_width: float
    ):
        """绘制图例和用量统计"""
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(black)
        c.drawString(x_start, y_start + self.legend_area_height - 5 * mm, "Color Legend & Usage Statistics")

        # 排序：按用量降序
        sorted_usage = sorted(usage_stats.items(), key=lambda x: x[1], reverse=True)
        total_beads = sum(usage_stats.values())

        # 计算图例布局
        legend_cols = 4  # 每行显示4个颜色
        item_width = (page_width - 2 * self.margin) / legend_cols
        item_height = 5 * mm
        swatch_size = 3.5 * mm

        y = y_start + self.legend_area_height - 12 * mm
        col_idx = 0

        for color_id, count in sorted_usage:
            bead_color = palette.get_color_by_id(color_id)
            if bead_color is None:
                continue

            x = x_start + col_idx * item_width

            # 颜色色块
            r, g, b = bead_color.rgb
            c.setFillColor(Color(r / 255.0, g / 255.0, b / 255.0))
            c.setStrokeColor(Color(0.5, 0.5, 0.5))
            c.setLineWidth(0.5)
            c.rect(x, y - swatch_size / 2, swatch_size, swatch_size, fill=1, stroke=1)

            # 色号和名称
            c.setFillColor(black)
            c.setFont("Helvetica", 6)
            label = f"{bead_color.id} {bead_color.name}: {count}"
            c.drawString(x + swatch_size + 1 * mm, y - 1 * mm, label)

            col_idx += 1
            if col_idx >= legend_cols:
                col_idx = 0
                y -= item_height
                if y < y_start:
                    break

        # 总计
        c.setFont("Helvetica-Bold", 8)
        total_y = max(y - item_height, y_start)
        c.drawString(
            x_start,
            total_y,
            f"Total: {total_beads} beads | {len(sorted_usage)} colors"
        )

    @staticmethod
    def _get_contrast_color(r: int, g: int, b: int) -> Color:
        """根据背景颜色计算对比文字颜色"""
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        if luminance > 0.5:
            return Color(0, 0, 0)  # 深色文字
        else:
            return Color(1, 1, 1)  # 浅色文字