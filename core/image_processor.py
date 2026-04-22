"""
图片预处理模块 v2
增加超采样、边缘增强、自动对比度等预处理
"""

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from typing import Tuple, Optional


class ImageProcessor:
    """图片处理器"""

    PRESET_SIZES = {
        "小板 (29×29)": (29, 29),
        "大板 (52×52)": (52, 52),
        "大板 (58×58)": (58, 58),
        "双拼 (29×58)": (29, 58),
        "双拼 (58×29)": (58, 29),
        "四拼 (58×58)": (58, 58),
        "大幅 (104×104)": (104, 104),
    }

    def __init__(self):
        self._original_image: Optional[Image.Image] = None
        self._cropped_image: Optional[Image.Image] = None

    def load_image(self, filepath: str) -> Image.Image:
        self._original_image = Image.open(filepath).convert("RGB")
        self._cropped_image = None
        return self._original_image

    @property
    def working_image(self) -> Optional[Image.Image]:
        return self._cropped_image or self._original_image

    def crop(self, left: int, top: int, right: int, bottom: int) -> Image.Image:
        if self._original_image is None:
            raise ValueError("No image loaded")
        self._cropped_image = self._original_image.crop((left, top, right, bottom))
        return self._cropped_image

    def reset_crop(self):
        self._cropped_image = None

    def pixelize(
        self,
        target_width: int,
        target_height: int,
        resample_method: str = "lanczos",
        enhance: bool = True
    ) -> np.ndarray:
        """
        像素化：缩放到目标尺寸

        Args:
            target_width: 目标宽度
            target_height: 目标高度
            resample_method: 缩放算法
            enhance: 是否做增强预处理
        """
        if self.working_image is None:
            raise ValueError("No image loaded")

        img = self.working_image.copy()

        if enhance:
            img = self._enhance_before_resize(img, target_width, target_height)

        resample_map = {
            "nearest": Image.Resampling.NEAREST,
            "bilinear": Image.Resampling.BILINEAR,
            "bicubic": Image.Resampling.BICUBIC,
            "lanczos": Image.Resampling.LANCZOS,
        }
        resample = resample_map.get(resample_method, Image.Resampling.LANCZOS)

        # 超采样：先缩到中间尺寸（target*4），再缩到目标，获得更好的色彩混合
        # 只有在中间尺寸确实比原图小时才做，避免先放大再缩小引入噪点
        src_w, src_h = img.size
        mid_w = target_width * 4
        mid_h = target_height * 4
        if mid_w < src_w and mid_h < src_h:
            img = img.resize((mid_w, mid_h), Image.Resampling.LANCZOS)

        resized = img.resize((target_width, target_height), resample)
        return np.array(resized, dtype=np.uint8)

    def _enhance_before_resize(
        self,
        img: Image.Image,
        target_w: int,
        target_h: int
    ) -> Image.Image:
        """
        缩放前的增强预处理
        自动调整对比度和锐度，让小尺寸像素化效果更好
        """
        src_w, src_h = img.size
        reduction = max(src_w / target_w, src_h / target_h)

        # 大幅缩小时需要更多增强
        if reduction > 10:
            # 轻微提升对比度（让颜色更鲜明）
            img = ImageEnhance.Contrast(img).enhance(1.15)
            # 轻微提升饱和度
            img = ImageEnhance.Color(img).enhance(1.1)
            # 轻微锐化（保留边缘细节）
            img = img.filter(ImageFilter.SHARPEN)
        elif reduction > 4:
            img = ImageEnhance.Contrast(img).enhance(1.08)
            img = ImageEnhance.Color(img).enhance(1.05)

        return img

    @staticmethod
    def auto_contrast(img: Image.Image, cutoff: float = 0.5) -> Image.Image:
        """自动对比度调整"""
        from PIL import ImageOps
        return ImageOps.autocontrast(img, cutoff=cutoff)

    @staticmethod
    def adjust_brightness(img: Image.Image, factor: float) -> Image.Image:
        """调整亮度 factor: 0.5~2.0"""
        return ImageEnhance.Brightness(img).enhance(factor)

    @staticmethod
    def adjust_contrast(img: Image.Image, factor: float) -> Image.Image:
        """调整对比度"""
        return ImageEnhance.Contrast(img).enhance(factor)

    @staticmethod
    def adjust_saturation(img: Image.Image, factor: float) -> Image.Image:
        """调整饱和度"""
        return ImageEnhance.Color(img).enhance(factor)

    @staticmethod
    def numpy_to_pil(array: np.ndarray) -> Image.Image:
        return Image.fromarray(array.astype(np.uint8))

    @staticmethod
    def pil_to_numpy(image: Image.Image) -> np.ndarray:
        return np.array(image.convert("RGB"), dtype=np.uint8)