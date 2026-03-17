"""
图片预处理模块
处理图片加载、裁剪、缩放等操作
"""

import numpy as np
from PIL import Image
from typing import Tuple, Optional


class ImageProcessor:
    """图片处理器"""

    # 预设拼豆板尺寸
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
        self._crop_rect: Optional[Tuple[int, int, int, int]] = None

    def load_image(self, filepath: str) -> Image.Image:
        """加载图片"""
        self._original_image = Image.open(filepath).convert("RGB")
        self._cropped_image = None
        self._crop_rect = None
        return self._original_image

    @property
    def original_image(self) -> Optional[Image.Image]:
        return self._original_image

    @property
    def working_image(self) -> Optional[Image.Image]:
        """返回当前工作图片（裁剪后的或原始的）"""
        return self._cropped_image or self._original_image

    def crop(self, left: int, top: int, right: int, bottom: int) -> Image.Image:
        """
        裁剪图片
        Args:
            left, top, right, bottom: 裁剪区域坐标（相对于原图）
        """
        if self._original_image is None:
            raise ValueError("No image loaded")

        self._crop_rect = (left, top, right, bottom)
        self._cropped_image = self._original_image.crop(self._crop_rect)
        return self._cropped_image

    def reset_crop(self):
        """重置裁剪"""
        self._cropped_image = None
        self._crop_rect = None

    def pixelize(
        self,
        target_width: int,
        target_height: int,
        resample_method: str = "lanczos"
    ) -> np.ndarray:
        """
        将图片像素化到目标尺寸

        Args:
            target_width: 目标宽度（拼豆列数）
            target_height: 目标高度（拼豆行数）
            resample_method: 缩放算法

        Returns:
            像素数组 shape=(target_height, target_width, 3)
        """
        if self.working_image is None:
            raise ValueError("No image loaded")

        resample_map = {
            "nearest": Image.Resampling.NEAREST,
            "bilinear": Image.Resampling.BILINEAR,
            "bicubic": Image.Resampling.BICUBIC,
            "lanczos": Image.Resampling.LANCZOS,
        }
        resample = resample_map.get(resample_method, Image.Resampling.LANCZOS)

        resized = self.working_image.resize(
            (target_width, target_height), resample
        )
        return np.array(resized, dtype=np.uint8)

    def get_preview_pixelized(
        self,
        target_width: int,
        target_height: int,
        preview_scale: int = 10
    ) -> Image.Image:
        """
        生成像素化预览图（放大到可预览的尺寸）
        """
        pixel_array = self.pixelize(target_width, target_height)
        img = Image.fromarray(pixel_array)
        preview_size = (target_width * preview_scale, target_height * preview_scale)
        return img.resize(preview_size, Image.Resampling.NEAREST)

    @staticmethod
    def numpy_to_pil(array: np.ndarray) -> Image.Image:
        """numpy数组转PIL图片"""
        return Image.fromarray(array.astype(np.uint8))

    @staticmethod
    def pil_to_numpy(image: Image.Image) -> np.ndarray:
        """PIL图片转numpy数组"""
        return np.array(image.convert("RGB"), dtype=np.uint8)