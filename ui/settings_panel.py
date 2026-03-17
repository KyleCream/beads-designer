"""
设置面板 v3 - 卡片式设计
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QCheckBox, QLineEdit, QFrame, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from core.palette import PaletteManager
from core.image_processor import ImageProcessor


class SettingsCard(QFrame):
    """设置卡片容器"""

    def __init__(self, icon: str, title: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            SettingsCard {
                background-color: white;
                border: 1px solid #e8e8e8;
                border-radius: 8px;
            }
            SettingsCard:hover {
                border-color: #b8d4f0;
            }
        """)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 10, 12, 10)
        self._layout.setSpacing(6)

        # 标题
        header = QLabel(f'{icon} {title}')
        header.setStyleSheet("""
            font-size: 12px;
            font-weight: bold;
            color: #2d3436;
            padding-bottom: 4px;
            border-bottom: 1px solid #f0f0f0;
        """)
        self._layout.addWidget(header)

    def add_row(self, label_text: str, widget):
        """添加一行：标签 + 控件"""
        row = QHBoxLayout()
        row.setSpacing(8)
        lbl = QLabel(label_text)
        lbl.setStyleSheet('font-size: 11px; color: #555; min-width: 40px;')
        lbl.setFixedWidth(50)
        row.addWidget(lbl)
        row.addWidget(widget, 1)
        self._layout.addLayout(row)

    def add_widget(self, widget):
        self._layout.addWidget(widget)

    def add_layout(self, layout_item):
        self._layout.addLayout(layout_item)


class SettingsPanel(QWidget):
    """设置面板 - 卡片式"""

    settings_changed = pyqtSignal()
    generate_clicked = pyqtSignal()

    def __init__(self, palette_manager: PaletteManager):
        super().__init__()
        self.palette_manager = palette_manager
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 标题
        title = QLabel('⚙️ 设置')
        title.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #2d3436;
            padding: 2px 0;
        """)
        layout.addWidget(title)

        # ====== 卡片1: 项目 ======
        card1 = SettingsCard('📝', '项目')
        self.project_name_input = QLineEdit('my_beads')
        self.project_name_input.setPlaceholderText('输入项目名称')
        self.project_name_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px 8px;
                background: #fafafa;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #74b9ff;
                background: white;
            }
        """)
        card1.add_row('名称:', self.project_name_input)
        layout.addWidget(card1)

        # ====== 卡片2: 尺寸 ======
        card2 = SettingsCard('📐', '图纸尺寸')

        self.preset_combo = QComboBox()
        self.preset_combo.addItem('自定义', None)
        for name, size in ImageProcessor.PRESET_SIZES.items():
            self.preset_combo.addItem(name, size)
        self.preset_combo.setCurrentIndex(2)
        self.preset_combo.setStyleSheet(self._combo_style())
        card2.add_row('预设:', self.preset_combo)

        # 宽高行
        size_row = QHBoxLayout()
        size_row.setSpacing(6)

        lw = QLabel('宽')
        lw.setStyleSheet('font-size: 11px; color: #555;')
        size_row.addWidget(lw)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 500)
        self.width_spin.setValue(52)
        self.width_spin.setSuffix(' 格')
        self.width_spin.setStyleSheet(self._spin_style())
        size_row.addWidget(self.width_spin)

        x_label = QLabel('×')
        x_label.setStyleSheet('font-size: 13px; font-weight: bold; color: #636e72;')
        x_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        x_label.setFixedWidth(16)
        size_row.addWidget(x_label)

        lh = QLabel('高')
        lh.setStyleSheet('font-size: 11px; color: #555;')
        size_row.addWidget(lh)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, 500)
        self.height_spin.setValue(52)
        self.height_spin.setSuffix(' 格')
        self.height_spin.setStyleSheet(self._spin_style())
        size_row.addWidget(self.height_spin)

        card2.add_layout(size_row)

        self.lock_ratio_check = QCheckBox('🔗 锁定宽高比')
        self.lock_ratio_check.setChecked(True)
        self.lock_ratio_check.setStyleSheet(self._check_style())
        card2.add_widget(self.lock_ratio_check)

        layout.addWidget(card2)

        # ====== 卡片3: 色板 ======
        card3 = SettingsCard('🎨', '色板')

        self.palette_combo = QComboBox()
        for brand in self.palette_manager.get_available_brands():
            p = self.palette_manager.get_palette(brand)
            self.palette_combo.addItem(f'{brand} ({p.size} 色)', brand)
        self.palette_combo.setStyleSheet(self._combo_style())
        card3.add_row('品牌:', self.palette_combo)

        # 颜色限制
        limit_row = QHBoxLayout()
        limit_row.setSpacing(6)
        self.limit_colors_check = QCheckBox('限制颜色')
        self.limit_colors_check.setStyleSheet(self._check_style())
        limit_row.addWidget(self.limit_colors_check)

        self.max_colors_spin = QSpinBox()
        self.max_colors_spin.setRange(2, 100)
        self.max_colors_spin.setValue(20)
        self.max_colors_spin.setEnabled(False)
        self.max_colors_spin.setSuffix(' 种')
        self.max_colors_spin.setStyleSheet(self._spin_style())
        limit_row.addWidget(self.max_colors_spin)
        card3.add_layout(limit_row)

        self.limit_colors_check.toggled.connect(self.max_colors_spin.setEnabled)

        self.dithering_check = QCheckBox('✨ Floyd-Steinberg 抖动')
        self.dithering_check.setToolTip('启用后颜色过渡更自然')
        self.dithering_check.setStyleSheet(self._check_style())
        card3.add_widget(self.dithering_check)

        layout.addWidget(card3)

        layout.addStretch()

    # ==================== 样式 ====================

    @staticmethod
    def _combo_style():
        return """
            QComboBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px 8px;
                background: #fafafa;
                font-size: 11px;
                min-height: 22px;
            }
            QComboBox:hover { border-color: #74b9ff; }
            QComboBox:focus { border-color: #0984e3; background: white; }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #636e72;
                margin-right: 6px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
                selection-background-color: #dfe6e9;
                selection-color: #2d3436;
            }
        """

    @staticmethod
    def _spin_style():
        return """
            QSpinBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 3px 6px;
                background: #fafafa;
                font-size: 11px;
                min-height: 22px;
            }
            QSpinBox:hover { border-color: #74b9ff; }
            QSpinBox:focus { border-color: #0984e3; background: white; }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 16px;
                border: none;
                background: #f0f0f0;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #dfe6e9;
            }
        """

    @staticmethod
    def _check_style():
        return """
            QCheckBox {
                font-size: 11px;
                color: #555;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background: #fafafa;
            }
            QCheckBox::indicator:hover {
                border-color: #74b9ff;
            }
            QCheckBox::indicator:checked {
                background: #0984e3;
                border-color: #0984e3;
            }
        """

    # ==================== 逻辑 ====================

    def _connect_signals(self):
        self.preset_combo.currentIndexChanged.connect(self._on_preset)

    def _on_preset(self, index):
        data = self.preset_combo.currentData()
        if data:
            self.width_spin.blockSignals(True)
            self.height_spin.blockSignals(True)
            self.width_spin.setValue(data[0])
            self.height_spin.setValue(data[1])
            self.width_spin.blockSignals(False)
            self.height_spin.blockSignals(False)

    def set_enabled(self, enabled: bool):
        pass

    def get_settings(self) -> dict:
        mc = 0
        if self.limit_colors_check.isChecked():
            mc = self.max_colors_spin.value()
        return {
            'project_name': self.project_name_input.text() or 'beads_pattern',
            'grid_width': self.width_spin.value(),
            'grid_height': self.height_spin.value(),
            'palette_brand': self.palette_combo.currentData(),
            'max_colors': mc,
            'dithering': self.dithering_check.isChecked(),
        }