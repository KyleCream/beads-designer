"""
设置面板
拼豆图纸参数配置 - 支持滚动，自适应显示
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QCheckBox, QPushButton, QGroupBox, QFormLayout,
    QLineEdit, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from core.palette import PaletteManager
from core.image_processor import ImageProcessor


class SettingsPanel(QWidget):
    """设置面板 - 带滚动条"""

    settings_changed = pyqtSignal()
    generate_clicked = pyqtSignal()

    def __init__(self, palette_manager: PaletteManager):
        super().__init__()
        self.palette_manager = palette_manager
        self._init_ui()
        self._connect_signals()
        self.set_enabled(False)

    def _init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # 标题（不滚动）
        title = QLabel('⚙️ 参数设置')
        title.setStyleSheet('font-size: 15px; font-weight: bold; padding: 5px;')
        outer_layout.addWidget(title)

        # 用ScrollArea包裹内容，防止显示不全
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QWidget { background: transparent; }
        """)

        # 内容容器
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(5, 0, 5, 5)
        layout.setSpacing(8)

        # ===== 项目名称 =====
        name_group = QGroupBox('项目名称')
        name_group.setStyleSheet(self._group_style())
        name_layout = QFormLayout(name_group)
        name_layout.setContentsMargins(8, 15, 8, 8)
        self.project_name_input = QLineEdit('my_beads')
        self.project_name_input.setPlaceholderText('输入项目名称')
        name_layout.addRow('名称:', self.project_name_input)
        layout.addWidget(name_group)

        # ===== 尺寸设置 =====
        size_group = QGroupBox('图纸尺寸')
        size_group.setStyleSheet(self._group_style())
        size_layout = QVBoxLayout(size_group)
        size_layout.setContentsMargins(8, 15, 8, 8)
        size_layout.setSpacing(6)

        # 预设
        preset_layout = QHBoxLayout()
        preset_label = QLabel('预设:')
        preset_label.setFixedWidth(45)
        preset_layout.addWidget(preset_label)
        self.preset_combo = QComboBox()
        self.preset_combo.addItem('自定义', None)
        for name, size in ImageProcessor.PRESET_SIZES.items():
            self.preset_combo.addItem(name, size)
        self.preset_combo.setCurrentIndex(2)  # 默认大板
        preset_layout.addWidget(self.preset_combo, 1)
        size_layout.addLayout(preset_layout)

        # 自定义尺寸
        custom_layout = QHBoxLayout()
        w_label = QLabel('宽:')
        w_label.setFixedWidth(25)
        custom_layout.addWidget(w_label)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 500)
        self.width_spin.setValue(52)
        self.width_spin.setSuffix(' 格')
        custom_layout.addWidget(self.width_spin)

        h_label = QLabel('高:')
        h_label.setFixedWidth(25)
        custom_layout.addWidget(h_label)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, 500)
        self.height_spin.setValue(52)
        self.height_spin.setSuffix(' 格')
        custom_layout.addWidget(self.height_spin)
        size_layout.addLayout(custom_layout)

        self.lock_ratio_check = QCheckBox('锁定宽高比')
        self.lock_ratio_check.setChecked(True)
        size_layout.addWidget(self.lock_ratio_check)

        layout.addWidget(size_group)

        # ===== 色板设置 =====
        palette_group = QGroupBox('色板设置')
        palette_group.setStyleSheet(self._group_style())
        palette_layout = QVBoxLayout(palette_group)
        palette_layout.setContentsMargins(8, 15, 8, 8)
        palette_layout.setSpacing(6)

        # 品牌选择
        brand_layout = QHBoxLayout()
        brand_label = QLabel('品牌:')
        brand_label.setFixedWidth(45)
        brand_layout.addWidget(brand_label)
        self.palette_combo = QComboBox()
        for brand in self.palette_manager.get_available_brands():
            palette_obj = self.palette_manager.get_palette(brand)
            self.palette_combo.addItem(
                f'{brand} ({palette_obj.size}色)', brand
            )
        brand_layout.addWidget(self.palette_combo, 1)
        palette_layout.addLayout(brand_layout)

        # 颜色限制
        color_limit_layout = QHBoxLayout()
        self.limit_colors_check = QCheckBox('限制颜色:')
        color_limit_layout.addWidget(self.limit_colors_check)
        self.max_colors_spin = QSpinBox()
        self.max_colors_spin.setRange(2, 100)
        self.max_colors_spin.setValue(20)
        self.max_colors_spin.setEnabled(False)
        self.max_colors_spin.setSuffix(' 种')
        color_limit_layout.addWidget(self.max_colors_spin)
        palette_layout.addLayout(color_limit_layout)

        self.limit_colors_check.toggled.connect(self.max_colors_spin.setEnabled)

        # 抖动
        self.dithering_check = QCheckBox('Floyd-Steinberg 抖动')
        self.dithering_check.setToolTip('启用后颜色过渡更平滑，但细节可能模糊')
        palette_layout.addWidget(self.dithering_check)

        layout.addWidget(palette_group)

        # ===== 操作按钮 =====
        btn_group = QGroupBox('操作')
        btn_group.setStyleSheet(self._group_style())
        btn_layout = QVBoxLayout(btn_group)
        btn_layout.setContentsMargins(8, 15, 8, 8)
        btn_layout.setSpacing(8)

        self.preview_btn = QPushButton('👁️  预览效果')
        self.preview_btn.setMinimumHeight(36)
        self.preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #00b894;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #00a381; }
            QPushButton:disabled { background-color: #dfe6e9; color: #b2bec3; }
        """)
        self.preview_btn.clicked.connect(self.settings_changed.emit)
        btn_layout.addWidget(self.preview_btn)

        self.generate_btn = QPushButton('📄  生成PDF图纸')
        self.generate_btn.setMinimumHeight(36)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #c0392b; }
            QPushButton:disabled { background-color: #dfe6e9; color: #b2bec3; }
        """)
        self.generate_btn.clicked.connect(self.generate_clicked.emit)
        btn_layout.addWidget(self.generate_btn)

        layout.addWidget(btn_group)

        layout.addStretch()

        scroll.setWidget(content)
        outer_layout.addWidget(scroll, 1)

    @staticmethod
    def _group_style() -> str:
        return """
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #dcdde1;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 12px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #2d3436;
            }
        """

    def _connect_signals(self):
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)

    def _on_preset_changed(self, index):
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
        self.preview_btn.setEnabled(enabled)
        self.generate_btn.setEnabled(enabled)

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