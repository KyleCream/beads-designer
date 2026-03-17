"""
设置面板 v2 - 直接平铺，不用滚动条
左侧固定宽度280px足够放下所有控件
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QCheckBox, QPushButton, QGroupBox, QFormLayout,
    QLineEdit, QSizePolicy
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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title = QLabel('⚙️ 参数设置')
        title.setStyleSheet('font-size: 13px; font-weight: bold;')
        layout.addWidget(title)

        # === 项目名称 ===
        layout.addWidget(self._section_label('项目名称'))
        self.project_name_input = QLineEdit('my_beads')
        self.project_name_input.setPlaceholderText('输入名称')
        layout.addWidget(self.project_name_input)

        # === 图纸尺寸 ===
        layout.addWidget(self._section_label('图纸尺寸'))

        # 预设
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel('预设:'))
        self.preset_combo = QComboBox()
        self.preset_combo.addItem('自定义', None)
        for name, size in ImageProcessor.PRESET_SIZES.items():
            self.preset_combo.addItem(name, size)
        self.preset_combo.setCurrentIndex(2)
        preset_row.addWidget(self.preset_combo, 1)
        layout.addLayout(preset_row)

        # 宽高
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel('宽:'))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 500)
        self.width_spin.setValue(52)
        self.width_spin.setSuffix(' 格')
        size_row.addWidget(self.width_spin)
        size_row.addWidget(QLabel('高:'))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, 500)
        self.height_spin.setValue(52)
        self.height_spin.setSuffix(' 格')
        size_row.addWidget(self.height_spin)
        layout.addLayout(size_row)

        self.lock_ratio_check = QCheckBox('锁定宽高比')
        self.lock_ratio_check.setChecked(True)
        layout.addWidget(self.lock_ratio_check)

        # === 色板 ===
        layout.addWidget(self._section_label('色板设置'))

        brand_row = QHBoxLayout()
        brand_row.addWidget(QLabel('品牌:'))
        self.palette_combo = QComboBox()
        for brand in self.palette_manager.get_available_brands():
            p = self.palette_manager.get_palette(brand)
            self.palette_combo.addItem(f'{brand} ({p.size}色)', brand)
        brand_row.addWidget(self.palette_combo, 1)
        layout.addLayout(brand_row)

        # 颜色限制
        limit_row = QHBoxLayout()
        self.limit_colors_check = QCheckBox('限色:')
        limit_row.addWidget(self.limit_colors_check)
        self.max_colors_spin = QSpinBox()
        self.max_colors_spin.setRange(2, 100)
        self.max_colors_spin.setValue(20)
        self.max_colors_spin.setEnabled(False)
        self.max_colors_spin.setSuffix(' 种')
        limit_row.addWidget(self.max_colors_spin)
        layout.addLayout(limit_row)

        self.limit_colors_check.toggled.connect(self.max_colors_spin.setEnabled)

        self.dithering_check = QCheckBox('Floyd-Steinberg 抖动')
        self.dithering_check.setToolTip('颜色过渡更平滑')
        layout.addWidget(self.dithering_check)

        # 弹性空间
        layout.addStretch()

    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            'font-size: 11px; font-weight: bold; color: #636e72;'
            'border-bottom: 1px solid #dcdde1; padding-bottom: 2px; margin-top: 4px;'
        )
        return lbl

    def _connect_signals(self):
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)

    def _on_preset_changed(self, index):
        data = self.preset_combo.currentData()
        if data:
            self.width_spin.blockSignals(True)
            self.height_spin.blockSignals(True)
            self.width_spin.setValue(data[0])
            self.height_spin.setValue(data[1])
            self.width_spin.blockSignals(False)
            self.height_spin.blockSignals(False)

    def set_enabled(self, enabled: bool):
        pass  # 按钮已移到顶部step_bar

    def get_settings(self) -> dict:
        max_colors = 0
        if self.limit_colors_check.isChecked():
            max_colors = self.max_colors_spin.value()
        return {
            'project_name': self.project_name_input.text() or 'beads_pattern',
            'grid_width': self.width_spin.value(),
            'grid_height': self.height_spin.value(),
            'palette_brand': self.palette_combo.currentData(),
            'max_colors': max_colors,
            'dithering': self.dithering_check.isChecked(),
        }