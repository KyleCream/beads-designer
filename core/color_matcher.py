"""
色彩匹配模块
将图片像素颜色匹配到最接近的拼豆颜色
支持多种匹配算法和颜色数量限制
"""

import numpy as np
from scipy.spatial import KDTree
from typing import List, Optional, Tuple, Dict
from collections import Counter
from .palette import Palette, BeadColor


class ColorMatcher:
    """色彩匹配器"""

    # 用户选择颜色数量时的最小阈值
    MIN_COLORS = 2
    DEFAULT_MAX_COLORS = 0  # 0表示不限制

    def __init__(self, palette: Palette):
        self.palette = palette
        self._build_index()

    def _build_index(self):
        """构建KD树索引用于快速最近邻搜索"""
        self._rgb_array = self.palette.get_all_rgb_array()
        # 使用LAB空间权重的加权RGB进行匹配，效果更好
        self._weighted_array = self._apply_perceptual_weight(self._rgb_array)
        self._kdtree = KDTree(self._weighted_array)

    @staticmethod
    def _apply_perceptual_weight(rgb_array: np.ndarray) -> np.ndarray:
        """
        应用人眼感知权重
        人眼对绿色最敏感，红色次之，蓝色最不敏感
        使用加权欧几里德距离进行匹配
        """
        weights = np.array([0.299, 0.587, 0.114])  # ITU-R BT.601 亮度权重
        return rgb_array * np.sqrt(weights)

    def match_color(self, rgb: np.ndarray) -> BeadColor:
        """匹配单个颜色到最近的拼豆颜色"""
        weighted = self._apply_perceptual_weight(rgb.reshape(1, 3))
        _, idx = self._kdtree.query(weighted)
        return self.palette.colors[idx[0]]

    def match_image(
        self,
        pixel_array: np.ndarray,
        max_colors: int = 0,
        dithering: bool = False
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
        """
        匹配整个图片

        Args:
            pixel_array: 像素数组, shape=(H, W, 3), RGB格式
            max_colors: 最大颜色数量, 0表示不限制
            dithering: 是否启用Floyd-Steinberg抖动

        Returns:
            matched_rgb: 匹配后的RGB数组, shape=(H, W, 3)
            color_id_map: 颜色ID映射, shape=(H, W), 存储颜色在palette中的索引
            usage_stats: 颜色使用统计 {color_id: count}
        """
        h, w, _ = pixel_array.shape
        working_palette = self.palette

        # 如果限制了颜色数量，先进行颜色量化选出最优子集
        if max_colors > 0:
            max_colors = max(max_colors, self.MIN_COLORS)
            working_palette = self._select_optimal_colors(
                pixel_array, max_colors
            )
            # 重建索引
            matcher = ColorMatcher(working_palette)
        else:
            matcher = self

        if dithering:
            return matcher._match_with_dithering(pixel_array)
        else:
            return matcher._match_direct(pixel_array)

    def _match_direct(
        self, pixel_array: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
        """直接匹配（无抖动）"""
        h, w, _ = pixel_array.shape
        flat_pixels = pixel_array.reshape(-1, 3).astype(np.float64)
        weighted_pixels = self._apply_perceptual_weight(flat_pixels)

        _, indices = self._kdtree.query(weighted_pixels)

        matched_rgb = self._rgb_array[indices].reshape(h, w, 3).astype(np.uint8)
        color_id_map = indices.reshape(h, w)

        # 统计用量
        usage_stats = {}
        unique, counts = np.unique(indices, return_counts=True)
        for idx, count in zip(unique, counts):
            color = self.palette.colors[idx]
            usage_stats[color.id] = int(count)

        return matched_rgb, color_id_map, usage_stats

    def _match_with_dithering(
        self, pixel_array: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
        """Floyd-Steinberg 抖动匹配"""
        h, w, _ = pixel_array.shape
        # 使用浮点数工作
        working = pixel_array.astype(np.float64).copy()
        color_id_map = np.zeros((h, w), dtype=np.int32)

        for y in range(h):
            for x in range(w):
                old_pixel = working[y, x].copy()
                # 找最近颜色
                weighted = self._apply_perceptual_weight(
                    old_pixel.reshape(1, 3)
                )
                _, idx = self._kdtree.query(weighted)
                idx = idx[0]
                new_pixel = self._rgb_array[idx]
                color_id_map[y, x] = idx

                # 计算误差
                error = old_pixel - new_pixel
                working[y, x] = new_pixel

                # 分散误差到相邻像素
                if x + 1 < w:
                    working[y, x + 1] += error * 7.0 / 16.0
                if y + 1 < h:
                    if x - 1 >= 0:
                        working[y + 1, x - 1] += error * 3.0 / 16.0
                    working[y + 1, x] += error * 5.0 / 16.0
                    if x + 1 < w:
                        working[y + 1, x + 1] += error * 1.0 / 16.0

        matched_rgb = np.zeros((h, w, 3), dtype=np.uint8)
        for y in range(h):
            for x in range(w):
                matched_rgb[y, x] = self._rgb_array[color_id_map[y, x]]

        # 统计用量
        usage_stats = {}
        unique, counts = np.unique(color_id_map, return_counts=True)
        for idx, count in zip(unique, counts):
            color = self.palette.colors[idx]
            usage_stats[color.id] = int(count)

        return matched_rgb, color_id_map, usage_stats

    def _select_optimal_colors(
        self, pixel_array: np.ndarray, max_colors: int
    ) -> Palette:
        """
        从色板中选择最优的N种颜色
        策略：先做全色板匹配，然后选出使用频率最高的N种颜色
        """
        _, _, usage = self._match_direct(pixel_array)

        # 按使用量排序，取前N个
        sorted_colors = sorted(usage.items(), key=lambda x: x[1], reverse=True)
        top_color_ids = [cid for cid, _ in sorted_colors[:max_colors]]

        return self.palette.get_subset(top_color_ids)

    def get_color_by_index(self, index: int) -> BeadColor:
        """通过索引获取颜色"""
        return self.palette.colors[index]