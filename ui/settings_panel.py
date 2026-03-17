"""
设置面板
拼豆图纸参数配置
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QCheckBox, QPushButton, QGroupBox, QFormLayout,
    QLineEdit, QSlider, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt
from core.palette import PaletteManager
from core.image_processor import ImageProcessor


class SettingsPanel(QWidget):
    """设置面板"""

    settings_changed = pyqtSignal()
    generate_clicked = pyqtSignal()

    def __init__(self, palette_manager: PaletteManager):
        super().__init__()
        self.palette_manager = palette_manager
        self._init_ui()
        self._connect_signals()
        self.set_enabled(False)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 标题
        title = QLabel("⚙️ 参数设置")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        layout.addWidget(title)

        # -- 项目名称 --
        name_group = QGroupBox("项目名称")
        name_layout = QFormLayout(name_group)
        self.project_name_input = QLineEdit("my_beads")
        self.project_name_input.setPlaceholderText("输入项目名称")
        name_layout.addRow("名称:", self.project_name_input)
        layout.addWidget(name_group)

        # -- 尺寸设置 --
        size_group = QGroupBox("图纸尺寸")
        size_layout = QVBoxLayout(size_group)

        # 预设尺寸
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("预设:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("自定义", None)
        for name, size in ImageProcessor.PRESET_SIZES.items():
            self.preset_combo.addItem(name, size)
        self.preset_combo.setCurrentIndex(2)  # 默认选大板52×52
        preset_layout.addWidget(self.preset_combo, 1)
        size_layout.addLayout(preset_layout)

        # 自定义尺寸
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("宽:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 500)
        self.width_spin.setValue(52)
        self.width_spin.setSuffix(" 格")
        custom_layout.addWidget(self.width_spin)

        custom_layout.addWidget(QLabel("高:"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, 500)
        self.height_spin.setValue(52)
        self.height_spin.setSuffix(" 格")
        custom_layout.addWidget(self.height_spin)
        size_layout.addLayout(custom_layout)

        # 锁定比例
        self.lock_ratio_check = QCheckBox("锁定宽高比")
        self.lock_ratio_check.setChecked(True)
        size_layout.addWidget(self.lock_ratio_check)

        layout.addWidget(size_group)

        # -- 色板设置 --
        palette_group = QGroupBox("色板设置")
        palette_layout = QVBoxLayout(palette_group)

        brand_layout = QHBoxLayout()
        brand_layout.addWidget(QLabel("品牌:"))
        self.palette_combo = QComboBox()
        for brand in self.palette_manager.get_available_brands():
            palette_obj = self.palette_manager.get_palette(brand)
            self.palette_combo.addItem(
                f"{brand} ({palette_obj.size} colors)", brand
            )
        brand_layout.addWidget(self.palette_combo, 1)
        palette_layout.addLayout(brand_layout)

        # 颜色数量限制
        color_limit_layout = QHBoxLayout()
        self.limit_colors_check = QCheckBox("限制颜色数量:")
        color_limit_layout.addWidget(self.limit_colors_check)

        self.max_colors_spin = QSpinBox()
        self.max_colors_spin.setRange(2, 100)
        self.max_colors_spin.setValue(20)
        self.max_colors_spin.setEnabled(False)
        self.max_colors_spin.setSuffix(" 种")
        color_limit_layout.addWidget(self.max_colors_spin)
        palette_layout.addLayout(color_limit_layout)

        self.limit_colors_check.toggled.connect(self.max_colors_spin.setEnabled)

        # 抖动算法
        self.dithering_check = QCheckBox("启用 Floyd-Steinberg 抖动（过渡更平滑）")
        palette_layout.addWidget(self.dithering_check)

        layout.addWidget(palette_group)

        # -- 操作按钮 --
        btn_layout = QVBoxLayout()

        self.preview_btn = QPushButton("👁️ 预览效果")
        self.preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #27ae60; }
            QPushButton:disabled { background-color: #bdc3c7; }
        """)
        self.preview_btn.clicked.connect(self.settings_changed.emit)
        btn_layout.addWidget(self.preview_btn)

        self.generate_btn = QPushButton("📄 生成PDF图纸")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #c0392b; }
            QPushButton:disabled { background-color: #bdc3c7; }
        """)
        self.generate_btn.clicked.connect(self.generate_clicked.emit)
        btn_layout.addWidget(self.generate_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def _connect_signals(self):
        """连接内部信号"""
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)

    def _on_preset_changed(self, index):
        """预设尺寸变更"""
        data = self.preset_combo.currentData()
        if data:
            w, h = data
            self.width_spin.blockSignals(True)
            self.height_spin.blockSignals(True)
            self.width_spin.setValue(w)
            self.height_spin.setValue(h)
            self.width_spin.blockSignals(False)
            self.height_spin.blockSignals(False)

    def set_enabled(self, enabled: bool):
        """启用/禁用设置面板"""
        self.preview_btn.setEnabled(enabled)
        self.generate_btn.setEnabled(enabled)

    def get_settings(self) -> dict:
        """获取当前设置"""
        max_colors = 0
        if self.limit_colors_check.isChecked():
            max_colors = self.max_colors_spin.value()

        return {
            "project_name": self.project_name_input.text() or "beads_pattern",
            "grid_width": self.width_spin.value(),
            "grid_height": self.height_spin.value(),
            "palette_brand": self.palette_combo.currentData(),
            "max_colors": max_colors,
            "dithering": self.dithering_check.isChecked(),
        }