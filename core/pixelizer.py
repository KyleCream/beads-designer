# core/pixelizer.py

"""
像素化引擎模块
负责完整的像素化流水线：
图片预处理 → 缩放像素化 → 色板匹配 → 输出结果

这是核心协调器，串联 ImageProcessor 和 ColorMatcher
"""

import numpy as np
from PIL import Image
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass, field

from .image_processor import ImageProcessor
from .color_matcher import ColorMatcher
from .palette import Palette, BeadColor, PaletteManager


@dataclass
class PixelizeResult:
    """像素化结果数据类"""
    # 原始像素化数组 (未匹配色板) shape=(H, W, 3)
    raw_pixels: np.ndarray = None

    # 匹配色板后的RGB数组 shape=(H, W, 3)
    matched_rgb: np.ndarray = None

    # 颜色索引映射 shape=(H, W)，存储每个位置对应palette中的颜色索引
    color_index_map: np.ndarray = None

    # 颜色ID映射 shape=(H, W)，存储每个位置对应的颜色ID字符串
    color_id_grid: List[List[str]] = None

    # 颜色用量统计 {color_id: count}
    usage_stats: Dict[str, int] = field(default_factory=dict)

    # 使用的色板
    palette: Palette = None

    # 网格尺寸
    grid_width: int = 0
    grid_height: int = 0

    # 总豆子数
    @property
    def total_beads(self) -> int:
        return sum(self.usage_stats.values())

    # 使用的颜色种数
    @property
    def color_count(self) -> int:
        return len(self.usage_stats)

    def get_color_at(self, row: int, col: int) -> Optional[BeadColor]:
        """获取指定位置的拼豆颜色"""
        if self.color_index_map is None or self.palette is None:
            return None
        if 0 <= row < self.grid_height and 0 <= col < self.grid_width:
            idx = self.color_index_map[row, col]
            return self.palette.colors[idx]
        return None

    def get_sorted_usage(self, reverse: bool = True) -> List[Tuple[BeadColor, int]]:
        """获取排序后的用量统计列表"""
        if not self.palette:
            return []
        result = []
        for color_id, count in self.usage_stats.items():
            color = self.palette.get_color_by_id(color_id)
            if color:
                result.append((color, count))
        result.sort(key=lambda x: x[1], reverse=reverse)
        return result


@dataclass
class PixelizeConfig:
    """像素化配置"""
    # 目标网格尺寸
    grid_width: int = 52
    grid_height: int = 52

    # 色板品牌
    palette_brand: str = "Perler"

    # 最大颜色数量，0=不限制
    max_colors: int = 0

    # 是否启用抖动
    dithering: bool = False

    # 缩放算法: nearest, bilinear, bicubic, lanczos
    resample_method: str = "lanczos"

    # 裁剪区域 (left, top, right, bottom)，None=不裁剪
    crop_rect: Optional[Tuple[int, int, int, int]] = None

    # 亮度调整 (-100 到 100)
    brightness: int = 0

    # 对比度调整 (-100 到 100)
    contrast: int = 0

    # 饱和度调整 (-100 到 100)
    saturation: int = 0


class Pixelizer:
    """
    像素化引擎
    
    使用方式:
        palette_mgr = PaletteManager()
        palette_mgr.load_builtin_palettes()
        
        pixelizer = Pixelizer(palette_mgr)
        
        config = PixelizeConfig(grid_width=52, grid_height=52)
        result = pixelizer.process("image.jpg", config)
        
        # 使用结果
        print(result.total_beads)
        print(result.color_count)
    """

    def __init__(self, palette_manager: PaletteManager):
        self.palette_manager = palette_manager
        self._processor = ImageProcessor()

    def process(
        self,
        image_input,
        config: PixelizeConfig
    ) -> PixelizeResult:
        """
        完整像素化流水线
        
        Args:
            image_input: 图片路径(str) 或 PIL.Image 或 numpy数组
            config: 像素化配置
            
        Returns:
            PixelizeResult 包含所有结果数据
        """
        result = PixelizeResult()
        result.grid_width = config.grid_width
        result.grid_height = config.grid_height

        # Step 1: 加载图片
        pil_image = self._load_image(image_input)

        # Step 2: 预处理（裁剪、色彩调整）
        pil_image = self._preprocess(pil_image, config)

        # Step 3: 缩放像素化
        raw_pixels = self._resize_pixelize(pil_image, config)
        result.raw_pixels = raw_pixels

        # Step 4: 色板匹配
        palette = self.palette_manager.get_palette(config.palette_brand)
        if palette is None:
            available = self.palette_manager.get_available_brands()
            raise ValueError(
                f"Unknown palette brand: {config.palette_brand}. "
                f"Available: {available}"
            )

        matched_rgb, color_index_map, usage_stats, used_palette = (
            self._match_colors(raw_pixels, palette, config)
        )

        result.matched_rgb = matched_rgb
        result.color_index_map = color_index_map
        result.usage_stats = usage_stats
        result.palette = used_palette

        # Step 5: 生成颜色ID网格
        result.color_id_grid = self._build_color_id_grid(
            color_index_map, used_palette
        )

        return result

    def process_from_array(
        self,
        pixel_array: np.ndarray,
        palette: Palette,
        max_colors: int = 0,
        dithering: bool = False
    ) -> PixelizeResult:
        """
        直接从像素数组进行色板匹配（跳过加载和缩放步骤）
        适用于已经预处理好的数据
        """
        h, w, _ = pixel_array.shape
        result = PixelizeResult()
        result.grid_width = w
        result.grid_height = h
        result.raw_pixels = pixel_array

        config = PixelizeConfig(max_colors=max_colors, dithering=dithering)
        matched_rgb, color_index_map, usage_stats, used_palette = (
            self._match_colors(pixel_array, palette, config)
        )

        result.matched_rgb = matched_rgb
        result.color_index_map = color_index_map
        result.usage_stats = usage_stats
        result.palette = used_palette
        result.color_id_grid = self._build_color_id_grid(
            color_index_map, used_palette
        )

        return result

    def preview(
        self,
        image_input,
        config: PixelizeConfig,
        preview_scale: int = 10
    ) -> Image.Image:
        """
        快速生成预览图
        
        Returns:
            放大的PIL.Image用于预览显示
        """
        result = self.process(image_input, config)
        preview_img = Image.fromarray(result.matched_rgb)
        preview_size = (
            config.grid_width * preview_scale,
            config.grid_height * preview_scale
        )
        return preview_img.resize(preview_size, Image.Resampling.NEAREST)

    # ==================== 内部步骤方法 ====================

    def _load_image(self, image_input) -> Image.Image:
        """Step 1: 加载图片，统一转为PIL.Image"""
        if isinstance(image_input, str):
            # 文件路径
            return Image.open(image_input).convert("RGB")
        elif isinstance(image_input, Image.Image):
            return image_input.convert("RGB")
        elif isinstance(image_input, np.ndarray):
            return Image.fromarray(image_input).convert("RGB")
        else:
            raise TypeError(
                f"Unsupported image input type: {type(image_input)}"
            )

    def _preprocess(
        self,
        image: Image.Image,
        config: PixelizeConfig
    ) -> Image.Image:
        """Step 2: 预处理"""
        # 裁剪
        if config.crop_rect:
            left, top, right, bottom = config.crop_rect
            # 确保裁剪区域合法
            w, h = image.size
            left = max(0, min(left, w))
            top = max(0, min(top, h))
            right = max(left + 1, min(right, w))
            bottom = max(top + 1, min(bottom, h))
            image = image.crop((left, top, right, bottom))

        # 亮度调整
        if config.brightness != 0:
            from PIL import ImageEnhance
            factor = 1.0 + config.brightness / 100.0
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(factor)

        # 对比度调整
        if config.contrast != 0:
            from PIL import ImageEnhance
            factor = 1.0 + config.contrast / 100.0
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(factor)

        # 饱和度调整
        if config.saturation != 0:
            from PIL import ImageEnhance
            factor = 1.0 + config.saturation / 100.0
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(factor)

        return image

    def _resize_pixelize(
        self,
        image: Image.Image,
        config: PixelizeConfig
    ) -> np.ndarray:
        """Step 3: 缩放到目标网格尺寸"""
        resample_map = {
            "nearest": Image.Resampling.NEAREST,
            "bilinear": Image.Resampling.BILINEAR,
            "bicubic": Image.Resampling.BICUBIC,
            "lanczos": Image.Resampling.LANCZOS,
        }
        resample = resample_map.get(
            config.resample_method, Image.Resampling.LANCZOS
        )

        resized = image.resize(
            (config.grid_width, config.grid_height),
            resample
        )
        return np.array(resized, dtype=np.uint8)

    def _match_colors(
        self,
        pixel_array: np.ndarray,
        palette: Palette,
        config: PixelizeConfig
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, int], Palette]:
        """
        Step 4: 色板匹配
        
        Returns:
            matched_rgb, color_index_map, usage_stats, used_palette
        """
        matcher = ColorMatcher(palette)

        matched_rgb, color_index_map, usage_stats = matcher.match_image(
            pixel_array,
            max_colors=config.max_colors,
            dithering=config.dithering
        )

        # 如果限制了颜色数量，matcher内部会用子集色板
        # 我们需要拿到实际使用的色板
        if config.max_colors > 0:
            used_color_ids = list(usage_stats.keys())
            used_palette = palette.get_subset(used_color_ids)

            # 重新匹配以确保index对应used_palette
            rematcher = ColorMatcher(used_palette)
            matched_rgb, color_index_map, usage_stats = rematcher.match_image(
                pixel_array,
                max_colors=0,  # 已经是子集了，不再限制
                dithering=config.dithering
            )
            return matched_rgb, color_index_map, usage_stats, used_palette
        else:
            return matched_rgb, color_index_map, usage_stats, palette

    def _build_color_id_grid(
        self,
        color_index_map: np.ndarray,
        palette: Palette
    ) -> List[List[str]]:
        """
        Step 5: 构建颜色ID网格
        将索引映射转为颜色ID字符串网格，方便PDF生成使用
        """
        h, w = color_index_map.shape
        grid = []
        for row in range(h):
            row_ids = []
            for col in range(w):
                idx = color_index_map[row, col]
                color = palette.colors[idx]
                row_ids.append(color.id)
            grid.append(row_ids)
        return grid


class PixelizerFactory:
    """
    像素化器工厂
    提供便捷的创建方法
    """

    @staticmethod
    def create_default() -> Pixelizer:
        """创建默认配置的像素化器"""
        palette_mgr = PaletteManager()
        palette_mgr.load_builtin_palettes()
        return Pixelizer(palette_mgr)

    @staticmethod
    def create_with_palette(palette: Palette) -> Pixelizer:
        """使用指定色板创建像素化器"""
        palette_mgr = PaletteManager()
        palette_mgr._palettes[palette.brand] = palette
        return Pixelizer(palette_mgr)