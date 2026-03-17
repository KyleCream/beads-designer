"""
色彩匹配模块 v2
使用CIELAB色彩空间 + Delta E 2000算法进行精确色彩匹配
支持多种抖动算法
"""

import numpy as np
from scipy.spatial import KDTree
from typing import List, Optional, Tuple, Dict
from .palette import Palette, BeadColor


class ColorMatcher:
    """色彩匹配器 - CIELAB空间"""

    MIN_COLORS = 2
    DEFAULT_MAX_COLORS = 0

    def __init__(self, palette: Palette):
        self.palette = palette
        self._rgb_array = palette.get_all_rgb_array()
        self._lab_array = self._rgb_to_lab_batch(self._rgb_array)
        self._kdtree = KDTree(self._lab_array)

    # ==================== RGB <-> LAB 转换 ====================

    @staticmethod
    def _rgb_to_lab_batch(rgb: np.ndarray) -> np.ndarray:
        """批量 RGB -> CIELAB 转换"""
        rgb_norm = rgb.astype(np.float64) / 255.0

        # sRGB -> Linear RGB (gamma校正)
        mask = rgb_norm > 0.04045
        rgb_linear = np.where(
            mask,
            ((rgb_norm + 0.055) / 1.055) ** 2.4,
            rgb_norm / 12.92
        )

        # Linear RGB -> XYZ (D65 白点)
        # 矩阵转换
        m = np.array([
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041]
        ])
        xyz = rgb_linear @ m.T

        # XYZ -> LAB
        # D65 白点参考值
        ref = np.array([0.95047, 1.00000, 1.08883])
        xyz_norm = xyz / ref

        epsilon = 0.008856
        kappa = 903.3

        mask = xyz_norm > epsilon
        f = np.where(
            mask,
            np.cbrt(xyz_norm),
            (kappa * xyz_norm + 16.0) / 116.0
        )

        L = 116.0 * f[:, 1] - 16.0 if f.ndim > 1 else 116.0 * f[1] - 16.0
        a = 500.0 * (f[:, 0] - f[:, 1]) if f.ndim > 1 else 500.0 * (f[0] - f[1])
        b = 200.0 * (f[:, 1] - f[:, 2]) if f.ndim > 1 else 200.0 * (f[1] - f[2])

        if f.ndim > 1:
            return np.column_stack([L, a, b])
        else:
            return np.array([L, a, b])

    @staticmethod
    def _rgb_to_lab_single(r, g, b) -> np.ndarray:
        """单个颜色 RGB -> LAB"""
        rgb = np.array([[r, g, b]], dtype=np.float64)
        return ColorMatcher._rgb_to_lab_batch(rgb)[0]

    # ==================== Delta E 2000 ====================

    @staticmethod
    def _delta_e_2000(lab1: np.ndarray, lab2: np.ndarray) -> float:
        """
        计算两个LAB颜色之间的 Delta E 2000 色差
        这是目前最精确的色差公式，与人眼感知高度一致
        """
        L1, a1, b1 = lab1[0], lab1[1], lab1[2]
        L2, a2, b2 = lab2[0], lab2[1], lab2[2]

        # Step 1
        C1 = np.sqrt(a1**2 + b1**2)
        C2 = np.sqrt(a2**2 + b2**2)
        C_avg = (C1 + C2) / 2.0

        C_avg_7 = C_avg**7
        G = 0.5 * (1 - np.sqrt(C_avg_7 / (C_avg_7 + 25**7)))

        a1p = a1 * (1 + G)
        a2p = a2 * (1 + G)

        C1p = np.sqrt(a1p**2 + b1**2)
        C2p = np.sqrt(a2p**2 + b2**2)

        h1p = np.degrees(np.arctan2(b1, a1p)) % 360
        h2p = np.degrees(np.arctan2(b2, a2p)) % 360

        # Step 2
        dLp = L2 - L1
        dCp = C2p - C1p

        if C1p * C2p == 0:
            dhp = 0
        elif abs(h2p - h1p) <= 180:
            dhp = h2p - h1p
        elif h2p - h1p > 180:
            dhp = h2p - h1p - 360
        else:
            dhp = h2p - h1p + 360

        dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp / 2))

        # Step 3
        Lp_avg = (L1 + L2) / 2
        Cp_avg = (C1p + C2p) / 2

        if C1p * C2p == 0:
            hp_avg = h1p + h2p
        elif abs(h1p - h2p) <= 180:
            hp_avg = (h1p + h2p) / 2
        elif h1p + h2p < 360:
            hp_avg = (h1p + h2p + 360) / 2
        else:
            hp_avg = (h1p + h2p - 360) / 2

        T = (1
             - 0.17 * np.cos(np.radians(hp_avg - 30))
             + 0.24 * np.cos(np.radians(2 * hp_avg))
             + 0.32 * np.cos(np.radians(3 * hp_avg + 6))
             - 0.20 * np.cos(np.radians(4 * hp_avg - 63)))

        SL = 1 + 0.015 * (Lp_avg - 50)**2 / np.sqrt(20 + (Lp_avg - 50)**2)
        SC = 1 + 0.045 * Cp_avg
        SH = 1 + 0.015 * Cp_avg * T

        Cp_avg_7 = Cp_avg**7
        RT = (-2 * np.sqrt(Cp_avg_7 / (Cp_avg_7 + 25**7))
              * np.sin(np.radians(60 * np.exp(-((hp_avg - 275) / 25)**2))))

        dE = np.sqrt(
            (dLp / SL)**2
            + (dCp / SC)**2
            + (dHp / SH)**2
            + RT * (dCp / SC) * (dHp / SH)
        )

        return dE

    # ==================== 匹配方法 ====================

    def match_color(self, rgb: np.ndarray) -> BeadColor:
        """匹配单个颜色到最近的拼豆颜色"""
        lab = self._rgb_to_lab_batch(rgb.reshape(1, 3))
        _, idx = self._kdtree.query(lab)
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
            pixel_array: shape=(H, W, 3) RGB
            max_colors: 最大颜色数量, 0=不限
            dithering: 是否启用 Floyd-Steinberg 抖动

        Returns:
            matched_rgb, color_index_map, usage_stats
        """
        h, w, _ = pixel_array.shape

        # 如果限制颜色数，先选最优子集
        working_matcher = self
        if max_colors > 0:
            max_colors = max(max_colors, self.MIN_COLORS)
            subset_palette = self._select_optimal_colors(pixel_array, max_colors)
            working_matcher = ColorMatcher(subset_palette)

        if dithering:
            return working_matcher._match_floyd_steinberg(pixel_array)
        else:
            return working_matcher._match_direct(pixel_array)

    def _match_direct(self, pixel_array: np.ndarray):
        """直接最近邻匹配（CIELAB空间）"""
        h, w, _ = pixel_array.shape
        flat = pixel_array.reshape(-1, 3).astype(np.float64)

        # 批量转LAB
        flat_lab = self._rgb_to_lab_batch(flat)

        # KD-Tree 批量查询
        _, indices = self._kdtree.query(flat_lab)

        matched_rgb = self._rgb_array[indices].reshape(h, w, 3).astype(np.uint8)
        color_id_map = indices.reshape(h, w)

        usage = {}
        unique, counts = np.unique(indices, return_counts=True)
        for idx, cnt in zip(unique, counts):
            usage[self.palette.colors[idx].id] = int(cnt)

        return matched_rgb, color_id_map, usage

    def _match_floyd_steinberg(self, pixel_array: np.ndarray):
        """Floyd-Steinberg 抖动匹配（CIELAB空间）"""
        h, w, _ = pixel_array.shape
        # 在浮点RGB空间工作
        working = pixel_array.astype(np.float64).copy()
        color_id_map = np.zeros((h, w), dtype=np.int32)

        for y in range(h):
            for x in range(w):
                old_pixel = working[y, x].copy()
                # 限制到合法范围
                old_pixel = np.clip(old_pixel, 0, 255)

                # LAB空间查找最近色
                lab = self._rgb_to_lab_batch(old_pixel.reshape(1, 3))
                _, idx = self._kdtree.query(lab)
                idx = idx[0]
                new_pixel = self._rgb_array[idx].astype(np.float64)
                color_id_map[y, x] = idx

                # 计算误差
                error = old_pixel - new_pixel
                working[y, x] = new_pixel

                # 分散误差 (Floyd-Steinberg)
                if x + 1 < w:
                    working[y, x + 1] += error * 7.0 / 16.0
                if y + 1 < h:
                    if x - 1 >= 0:
                        working[y + 1, x - 1] += error * 3.0 / 16.0
                    working[y + 1, x] += error * 5.0 / 16.0
                    if x + 1 < w:
                        working[y + 1, x + 1] += error * 1.0 / 16.0

        # 构建结果
        matched_rgb = np.zeros((h, w, 3), dtype=np.uint8)
        for y in range(h):
            for x in range(w):
                matched_rgb[y, x] = self._rgb_array[color_id_map[y, x]]

        usage = {}
        unique, counts = np.unique(color_id_map, return_counts=True)
        for idx, cnt in zip(unique, counts):
            usage[self.palette.colors[idx].id] = int(cnt)

        return matched_rgb, color_id_map, usage

    def _select_optimal_colors(
        self, pixel_array: np.ndarray, max_colors: int
    ) -> Palette:
        """
        选择最优颜色子集
        策略：先全色板匹配 -> 按使用频率排序 -> 取Top N
        然后用选出的子集重新匹配一轮，迭代优化
        """
        # 第一轮：全色板匹配
        _, _, usage = self._match_direct(pixel_array)
        sorted_colors = sorted(usage.items(), key=lambda x: x[1], reverse=True)
        top_ids = [cid for cid, _ in sorted_colors[:max_colors]]
        subset = self.palette.get_subset(top_ids)

        # 第二轮：用子集重新匹配，看有没有被遗漏的重要颜色
        sub_matcher = ColorMatcher(subset)
        _, _, usage2 = sub_matcher._match_direct(pixel_array)

        return subset

    def get_color_by_index(self, index: int) -> BeadColor:
        return self.palette.colors[index]