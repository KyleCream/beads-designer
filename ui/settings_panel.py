"""
设置面板 v7 - 修复右侧控件截断
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QCheckBox, QLineEdit, QFrame, QSizePolicy,
    QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt
from core.palette import PaletteManager
from core.image_processor import ImageProcessor


class SettingsCard(QFrame):
    """设置卡片"""

    def __init__(self, icon: str, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName('SettingsCard')
        self.setStyleSheet("""
            #SettingsCard {
                background-color: white;
                border: 1px solid #e8e8e8;
                border-radius: 8px;
            }
            #SettingsCard:hover {
                border-color: #b8d4f0;
                background-color: #fefefe;
            }
        """)

        self._layout = QVBoxLayout(self)
        # 左右边距一致，右侧留够空间
        self._layout.setContentsMargins(14, 12, 14, 12)
        self._layout.setSpacing(8)

        header = QLabel(f'{icon} {title}')
        header.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            color: #2d3436;
            padding-bottom: 6px;
            border-bottom: 1px solid #f0f0f0;
        """)
        header.setMinimumHeight(28)
        self._layout.addWidget(header)

    def add_row(self, label_text: str, widget, label_width: int = 55):
        row = QHBoxLayout()
        row.setSpacing(10)
        row.setContentsMargins(0, 2, 0, 2)

        lbl = QLabel(label_text)
        lbl.setStyleSheet('font-size: 12px; color: #555;')
        lbl.setFixedWidth(label_width)
        lbl.setMinimumHeight(28)
        row.addWidget(lbl)

        widget.setMinimumHeight(30)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row.addWidget(widget, 1)

        self._layout.addLayout(row)

    def add_widget(self, widget):
        widget.setMinimumHeight(26)
        self._layout.addWidget(widget)

    def add_layout(self, lo):
        self._layout.addLayout(lo)

    def add_spacing(self, px: int = 4):
        self._layout.addSpacing(px)


class SettingsPanel(QWidget):
    """设置面板"""

    settings_changed = pyqtSignal()
    generate_clicked = pyqtSignal()

    def __init__(self, palette_manager: PaletteManager):
        super().__init__()
        self.palette_manager = palette_manager
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        title = QLabel('⚙️ 设置')
        title.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #2d3436;
            padding: 4px 0 8px 0;
        """)
        title.setMinimumHeight(30)
        outer.addWidget(title)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 5px;
                margin: 0;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: #d0d0d0;
                border-radius: 2px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background: #aaa; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

        content = QWidget()
        content.setStyleSheet('background: transparent;')
        layout = QVBoxLayout(content)
        # 关键：右边距留 14px，避免滚动条覆盖控件
        layout.setContentsMargins(0, 0, 14, 0)
        layout.setSpacing(10)

        # ====== 卡片1: 项目名称 ======
        card1 = SettingsCard('📝', '项目')
        self.project_name_input = QLineEdit('my_beads')
        self.project_name_input.setPlaceholderText('输入项目名称')
        self.project_name_input.setStyleSheet(self._input_style())
        card1.add_row('名称:', self.project_name_input)
        layout.addWidget(card1)

        # ====== 卡片2: 图纸尺寸 ======
        card2 = SettingsCard('📐', '图纸尺寸')

        self.preset_combo = QComboBox()
        self.preset_combo.addItem('自定义', None)
        for name, size in ImageProcessor.PRESET_SIZES.items():
            self.preset_combo.addItem(name, size)
        self.preset_combo.setCurrentIndex(2)
        self.preset_combo.setStyleSheet(self._combo_style())
        card2.add_row('预设:', self.preset_combo)

        card2.add_spacing(4)

        # 宽 × 高 独立行
        size_container = QWidget()
        size_layout = QHBoxLayout(size_container)
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.setSpacing(6)

        wl = QLabel('宽')
        wl.setStyleSheet('font-size: 12px; color: #555;')
        wl.setFixedWidth(20)
        size_layout.addWidget(wl)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 500)
        self.width_spin.setValue(52)
        self.width_spin.setSuffix(' 格')
        self.width_spin.setMinimumHeight(30)
        self.width_spin.setMinimumWidth(70)
        self.width_spin.setStyleSheet(self._spin_style())
        size_layout.addWidget(self.width_spin, 1)

        xl = QLabel('×')
        xl.setStyleSheet('font-size: 15px; font-weight: bold; color: #b2bec3;')
        xl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        xl.setFixedWidth(16)
        size_layout.addWidget(xl)

        hl = QLabel('高')
        hl.setStyleSheet('font-size: 12px; color: #555;')
        hl.setFixedWidth(20)
        size_layout.addWidget(hl)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, 500)
        self.height_spin.setValue(52)
        self.height_spin.setSuffix(' 格')
        self.height_spin.setMinimumHeight(30)
        self.height_spin.setMinimumWidth(70)
        self.height_spin.setStyleSheet(self._spin_style())
        size_layout.addWidget(self.height_spin, 1)

        card2.add_widget(size_container)

        card2.add_spacing(2)

        self.lock_ratio_check = QCheckBox('🔗 锁定宽高比')
        self.lock_ratio_check.setChecked(True)
        self.lock_ratio_check.setStyleSheet(self._check_style())
        card2.add_widget(self.lock_ratio_check)

        layout.addWidget(card2)

        # ====== 卡片3: 色板与配色 ======
        card3 = SettingsCard('🎨', '色板与配色')

        self.palette_combo = QComboBox()
        for brand in self.palette_manager.get_available_brands():
            p = self.palette_manager.get_palette(brand)
            self.palette_combo.addItem(f'{brand} ({p.size} 色)', brand)
        self.palette_combo.setStyleSheet(self._combo_style())
        card3.add_row('品牌:', self.palette_combo)

        card3.add_spacing(6)

        # 限色 checkbox
        self.limit_colors_check = QCheckBox('限制使用颜色数量')
        self.limit_colors_check.setStyleSheet(self._check_style())
        card3.add_widget(self.limit_colors_check)

        # 限色数量 - 缩进行
        limit_container = QWidget()
        limit_layout = QHBoxLayout(limit_container)
        limit_layout.setContentsMargins(28, 0, 0, 0)
        limit_layout.setSpacing(8)

        max_lbl = QLabel('最多:')
        max_lbl.setStyleSheet('font-size: 12px; color: #888;')
        max_lbl.setFixedWidth(38)
        limit_layout.addWidget(max_lbl)

        self.max_colors_spin = QSpinBox()
        self.max_colors_spin.setRange(2, 100)
        self.max_colors_spin.setValue(20)
        self.max_colors_spin.setEnabled(False)
        self.max_colors_spin.setSuffix(' 种')
        self.max_colors_spin.setMinimumHeight(30)
        self.max_colors_spin.setMinimumWidth(80)
        self.max_colors_spin.setStyleSheet(self._spin_style_disabled())
        limit_layout.addWidget(self.max_colors_spin, 1)

        card3.add_widget(limit_container)

        self.limit_colors_check.toggled.connect(self._on_limit_toggled)

        card3.add_spacing(6)

        # 抖动
        self.dithering_check = QCheckBox('✨ Floyd-Steinberg 抖动')
        self.dithering_check.setToolTip('启用后颜色过渡更自然')
        self.dithering_check.setStyleSheet(self._check_style())
        card3.add_widget(self.dithering_check)

        hint = QLabel('使像素化颜色过渡更平滑')
        hint.setStyleSheet('font-size: 10px; color: #aaa; padding-left: 28px;')
        card3.add_widget(hint)

        layout.addWidget(card3)

        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

    def _on_limit_toggled(self, checked):
        self.max_colors_spin.setEnabled(checked)
        self.max_colors_spin.setStyleSheet(
            self._spin_style() if checked else self._spin_style_disabled()
        )

    # ==================== 统一样式 ====================

    @staticmethod
    def _input_style():
        return """
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px 10px;
                background: #fafafa;
                font-size: 12px;
                min-height: 22px;
            }
            QLineEdit:hover { border-color: #b8d4f0; }
            QLineEdit:focus { border-color: #74b9ff; background: white; }
        """

    @staticmethod
    def _combo_style():
        return """
            QComboBox {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px 10px;
                padding-right: 24px;
                background: #fafafa;
                font-size: 12px;
                min-height: 22px;
            }
            QComboBox:hover { border-color: #b8d4f0; }
            QComboBox:focus { border-color: #74b9ff; background: white; }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border: none;
                border-left: 1px solid #eee;
                margin-right: 2px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #999;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
                selection-background-color: #ebf5fb;
                selection-color: #2d3436;
                padding: 2px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                min-height: 28px;
                padding: 4px 10px;
            }
        """

    @staticmethod
    def _spin_style():
        return """
            QSpinBox {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 4px 8px;
                padding-right: 22px;
                background: #fafafa;
                font-size: 12px;
                min-height: 22px;
            }
            QSpinBox:hover { border-color: #b8d4f0; }
            QSpinBox:focus { border-color: #74b9ff; background: white; }
            QSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px;
                border: none;
                border-left: 1px solid #eee;
                border-bottom: 1px solid #eee;
                background: transparent;
                border-top-right-radius: 4px;
            }
            QSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px;
                border: none;
                border-left: 1px solid #eee;
                background: transparent;
                border-bottom-right-radius: 4px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #e8f0fe;
            }
            QSpinBox::up-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 4px solid #888;
                width: 0; height: 0;
            }
            QSpinBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #888;
                width: 0; height: 0;
            }
        """

    @staticmethod
    def _spin_style_disabled():
        return """
            QSpinBox {
                border: 1px solid #eee;
                border-radius: 5px;
                padding: 4px 8px;
                padding-right: 22px;
                background: #f5f5f5;
                font-size: 12px;
                min-height: 22px;
                color: #bbb;
            }
            QSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px;
                border: none;
                background: transparent;
            }
            QSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px;
                border: none;
                background: transparent;
            }
            QSpinBox::up-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 4px solid #ddd;
                width: 0; height: 0;
            }
            QSpinBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #ddd;
                width: 0; height: 0;
            }
        """

    @staticmethod
    def _check_style():
        return """
            QCheckBox {
                font-size: 12px;
                color: #444;
                spacing: 8px;
                min-height: 24px;
            }
            QCheckBox::indicator {
                width: 17px;
                height: 17px;
                border: 1.5px solid #ccc;
                border-radius: 4px;
                background: #fafafa;
            }
            QCheckBox::indicator:hover {
                border-color: #74b9ff;
                background: #f0f7ff;
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