"""
色板管理模块
负责加载、管理拼豆色板数据，支持内置品牌色板和自定义色板
"""

import sys
import json
import os
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class BeadColor:
    """单个拼豆颜色"""
    id: str
    name: str
    rgb: Tuple[int, int, int]

    @property
    def hex_color(self) -> str:
        return "#{:02x}{:02x}{:02x}".format(*self.rgb)

    @property
    def rgb_array(self) -> np.ndarray:
        return np.array(self.rgb, dtype=np.float64)


class Palette:
    """色板类"""

    def __init__(self, brand: str, colors: List[BeadColor], version: str = "1.0"):
        self.brand = brand
        self.version = version
        self.colors: List[BeadColor] = colors
        self._color_map: Dict[str, BeadColor] = {c.id: c for c in colors}

    def get_color_by_id(self, color_id: str) -> Optional[BeadColor]:
        return self._color_map.get(color_id)

    def get_all_rgb_array(self) -> np.ndarray:
        """返回所有颜色的RGB矩阵, shape=(N, 3)"""
        return np.array([c.rgb for c in self.colors], dtype=np.float64)

    def get_subset(self, color_ids: List[str]) -> 'Palette':
        """获取子集色板"""
        subset_colors = [c for c in self.colors if c.id in color_ids]
        return Palette(
            brand=f"{self.brand} (Custom)",
            colors=subset_colors,
            version=self.version
        )

    @property
    def size(self) -> int:
        return len(self.colors)

    def to_dict(self) -> dict:
        return {
            "brand": self.brand,
            "version": self.version,
            "colors": [
                {"id": c.id, "name": c.name, "rgb": list(c.rgb)}
                for c in self.colors
            ]
        }


class PaletteManager:
    """色板管理器"""

    def __init__(self):
        self._palettes = {}

        # 兼容 PyInstaller 打包后的路径
        if getattr(sys, 'frozen', False):
            # 打包后运行
            base_dir = sys._MEIPASS
        else:
            # 开发环境
            base_dir = os.path.dirname(os.path.dirname(__file__))

        self._palettes_dir = os.path.join(base_dir, "palettes")
        self._custom_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "palettes", "custom"
        )
        os.makedirs(self._custom_dir, exist_ok=True)

    def load_builtin_palettes(self):
        """加载所有内置色板"""
        for filename in os.listdir(self._palettes_dir):
            if filename.endswith(".json") and os.path.isfile(
                os.path.join(self._palettes_dir, filename)
            ):
                self._load_palette_file(
                    os.path.join(self._palettes_dir, filename)
                )

    def _load_palette_file(self, filepath: str) -> Optional[Palette]:
        """从JSON文件加载色板"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            colors = []
            for c in data["colors"]:
                colors.append(BeadColor(
                    id=c["id"],
                    name=c["name"],
                    rgb=tuple(c["rgb"])
                ))

            palette = Palette(
                brand=data["brand"],
                colors=colors,
                version=data.get("version", "1.0")
            )
            self._palettes[data["brand"]] = palette
            return palette

        except Exception as e:
            print(f"Error loading palette {filepath}: {e}")
            return None

    def get_palette(self, brand: str) -> Optional[Palette]:
        return self._palettes.get(brand)

    def get_available_brands(self) -> List[str]:
        return list(self._palettes.keys())

    def save_custom_palette(self, palette: Palette, filename: str):
        """保存自定义色板"""
        filepath = os.path.join(self._custom_dir, f"{filename}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(palette.to_dict(), f, indent=2, ensure_ascii=False)

    def load_custom_palette(self, filename: str) -> Optional[Palette]:
        """加载自定义色板"""
        filepath = os.path.join(self._custom_dir, f"{filename}.json")
        if os.path.exists(filepath):
            return self._load_palette_file(filepath)
        return None

    def create_custom_palette(
        self, name: str, color_data: List[Dict]
    ) -> Palette:
        """
        创建自定义色板 (预留接口)
        color_data: [{"id": "C01", "name": "My Red", "rgb": [255, 0, 0]}, ...]
        """
        colors = [
            BeadColor(id=c["id"], name=c["name"], rgb=tuple(c["rgb"]))
            for c in color_data
        ]
        return Palette(brand=name, colors=colors)