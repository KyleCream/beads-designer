"""
像素化引擎 v2
配合CIELAB色彩匹配和增强预处理
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
    """像素化结果"""
    raw_pixels: np.ndarray = None
    matched_rgb: np.ndarray = None
    color_index_map: np.ndarray = None
    color_id_grid: List[List[str]] = None
    usage_stats: Dict[str, int] = field(default_factory=dict)
    palette: Palette = None
    grid_width: int = 0
    grid_height: int = 0

    @property
    def total_beads(self) -> int:
        return sum(self.usage_stats.values())

    @property
    def color_count(self) -> int:
        return len(self.usage_stats)

    def get_color_at(self, row: int, col: int) -> Optional[BeadColor]:
        if self.color_index_map is None or self.palette is None:
            return None
        if 0 <= row < self.grid_height and 0 <= col < self.grid_width:
            idx = self.color_index_map[row, col]
            return self.palette.colors[idx]
        return None

    def get_sorted_usage(self, reverse=True) -> List[Tuple[BeadColor, int]]:
        if not self.palette:
            return []
        result = []
        for cid, cnt in self.usage_stats.items():
            c = self.palette.get_color_by_id(cid)
            if c:
                result.append((c, cnt))
        result.sort(key=lambda x: x[1], reverse=reverse)
        return result


@dataclass
class PixelizeConfig:
    """像素化配置"""
    grid_width: int = 52
    grid_height: int = 52
    palette_brand: str = "Perler"
    max_colors: int = 0
    dithering: bool = False
    resample_method: str = "lanczos"
    crop_rect: Optional[Tuple[int, int, int, int]] = None
    brightness: int = 0
    contrast: int = 0
    saturation: int = 0
    enhance: bool = True  # 自动增强


class Pixelizer:
    """像素化引擎"""

    def __init__(self, palette_manager: PaletteManager):
        self.palette_manager = palette_manager
        self._processor = ImageProcessor()

    def process(self, image_input, config: PixelizeConfig) -> PixelizeResult:
        """完整像素化流水线"""
        result = PixelizeResult()
        result.grid_width = config.grid_width
        result.grid_height = config.grid_height

        # Step 1: 加载
        pil_image = self._load_image(image_input)

        # Step 2: 预处理
        pil_image = self._preprocess(pil_image, config)

        # Step 3: 像素化缩放
        self._processor._original_image = pil_image
        self._processor._cropped_image = None
        raw_pixels = self._processor.pixelize(
            config.grid_width,
            config.grid_height,
            config.resample_method,
            enhance=config.enhance
        )
        result.raw_pixels = raw_pixels

        # Step 4: CIELAB色板匹配
        palette = self.palette_manager.get_palette(config.palette_brand)
        if palette is None:
            available = self.palette_manager.get_available_brands()
            raise ValueError(f"Unknown palette: {config.palette_brand}. Available: {available}")

        matched_rgb, color_index_map, usage_stats, used_palette = (
            self._match_colors(raw_pixels, palette, config)
        )

        result.matched_rgb = matched_rgb
        result.color_index_map = color_index_map
        result.usage_stats = usage_stats
        result.palette = used_palette

        # Step 5: 颜色ID网格
        result.color_id_grid = self._build_id_grid(color_index_map, used_palette)

        return result

    def process_from_array(
        self, pixel_array: np.ndarray, palette: Palette,
        max_colors: int = 0, dithering: bool = False
    ) -> PixelizeResult:
        """从像素数组直接匹配"""
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
        result.color_id_grid = self._build_id_grid(color_index_map, used_palette)
        return result

    def preview(self, image_input, config: PixelizeConfig, scale=10) -> Image.Image:
        result = self.process(image_input, config)
        img = Image.fromarray(result.matched_rgb)
        return img.resize(
            (config.grid_width * scale, config.grid_height * scale),
            Image.Resampling.NEAREST
        )

    # ==================== 内部方法 ====================

    def _load_image(self, image_input) -> Image.Image:
        if isinstance(image_input, str):
            return Image.open(image_input).convert("RGB")
        elif isinstance(image_input, Image.Image):
            return image_input.convert("RGB")
        elif isinstance(image_input, np.ndarray):
            return Image.fromarray(image_input).convert("RGB")
        raise TypeError(f"Unsupported: {type(image_input)}")

    def _preprocess(self, image: Image.Image, config: PixelizeConfig) -> Image.Image:
        if config.crop_rect:
            l, t, r, b = config.crop_rect
            w, h = image.size
            l, t = max(0, l), max(0, t)
            r, b = min(w, r), min(h, b)
            if r > l and b > t:
                image = image.crop((l, t, r, b))

        if config.brightness != 0:
            from PIL import ImageEnhance
            image = ImageEnhance.Brightness(image).enhance(1.0 + config.brightness / 100.0)
        if config.contrast != 0:
            from PIL import ImageEnhance
            image = ImageEnhance.Contrast(image).enhance(1.0 + config.contrast / 100.0)
        if config.saturation != 0:
            from PIL import ImageEnhance
            image = ImageEnhance.Color(image).enhance(1.0 + config.saturation / 100.0)

        return image

    def _match_colors(self, pixel_array, palette, config):
        matcher = ColorMatcher(palette)
        matched_rgb, color_index_map, usage_stats = matcher.match_image(
            pixel_array,
            max_colors=config.max_colors,
            dithering=config.dithering
        )

        if config.max_colors > 0:
            used_ids = list(usage_stats.keys())
            used_palette = palette.get_subset(used_ids)
            rematcher = ColorMatcher(used_palette)
            matched_rgb, color_index_map, usage_stats = rematcher.match_image(
                pixel_array, max_colors=0, dithering=config.dithering
            )
            return matched_rgb, color_index_map, usage_stats, used_palette
        return matched_rgb, color_index_map, usage_stats, palette

    def _build_id_grid(self, color_index_map, palette):
        h, w = color_index_map.shape
        grid = []
        for row in range(h):
            row_ids = []
            for col in range(w):
                idx = color_index_map[row, col]
                row_ids.append(palette.colors[idx].id)
            grid.append(row_ids)
        return grid


class PixelizerFactory:
    @staticmethod
    def create_default() -> Pixelizer:
        pm = PaletteManager()
        pm.load_builtin_palettes()
        return Pixelizer(pm)