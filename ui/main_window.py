"""
主窗口模块
自适应屏幕大小，管理整体布局和页面流转
"""

import sys
import os
import json

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QMessageBox,
    QSplitter, QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QScreen

from .upload_widget import UploadWidget
from .settings_panel import SettingsPanel
from .preview_widget import PreviewWidget
from .history_widget import HistoryWidget

from core.palette import PaletteManager
from core.project import HistoryManager, ProjectRecord
from core.pixelizer import Pixelizer, PixelizeConfig
from core.pdf_generator import PDFGenerator


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle('拼豆图纸生成器 - Beads Designer')

        # 自适应屏幕大小
        self._adapt_to_screen()

        # 缓存
        self._current_result = None

        # 初始化核心组件
        self._init_managers()
        self._init_ui()
        self._connect_signals()

    def _adapt_to_screen(self):
        """自适应屏幕大小"""
        screen = QApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            # 窗口为屏幕可用区域的80%
            w = int(available.width() * 0.8)
            h = int(available.height() * 0.8)
            # 设置合理的最小和最大值
            w = max(900, min(w, 1600))
            h = max(600, min(h, 1000))
            self.resize(w, h)

            # 居中显示
            x = available.x() + (available.width() - w) // 2
            y = available.y() + (available.height() - h) // 2
            self.move(x, y)
        else:
            self.resize(1100, 750)

        self.setMinimumSize(800, 550)

    def _init_managers(self):
        self.palette_manager = PaletteManager()
        self.palette_manager.load_builtin_palettes()
        self.history_manager = HistoryManager()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧导航栏
        nav_widget = self._create_nav_bar()
        main_layout.addWidget(nav_widget)

        # 右侧内容
        self.content_stack = QStackedWidget()

        # 页面1: 工作区
        self.workspace_page = self._create_workspace()
        self.content_stack.addWidget(self.workspace_page)

        # 页面2: 历史记录
        self.history_widget = HistoryWidget(self.history_manager)
        self.content_stack.addWidget(self.history_widget)

        main_layout.addWidget(self.content_stack, 1)

        # 状态栏
        self.statusBar().showMessage('Ready - 请上传图片开始制作')

    def _create_nav_bar(self) -> QWidget:
        nav = QWidget()
        nav.setFixedWidth(160)
        nav.setStyleSheet("""
            QWidget {
                background-color: #2c3e50;
            }
            QPushButton {
                color: white;
                background-color: transparent;
                border: none;
                padding: 12px 16px;
                text-align: left;
                font-size: 13px;
                border-left: 3px solid transparent;
            }
            QPushButton:hover {
                background-color: #34495e;
                border-left: 3px solid #3498db;
            }
            QPushButton:checked {
                background-color: #34495e;
                border-left: 3px solid #3498db;
            }
        """)

        layout = QVBoxLayout(nav)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title_label = QLabel('🎨 拼豆设计器')
        title_label.setStyleSheet("""
            color: white;
            font-size: 16px;
            font-weight: bold;
            padding: 16px 12px;
            border-bottom: 1px solid #34495e;
        """)
        layout.addWidget(title_label)

        self.nav_workspace_btn = QPushButton('📋 新建图纸')
        self.nav_workspace_btn.setCheckable(True)
        self.nav_workspace_btn.setChecked(True)
        layout.addWidget(self.nav_workspace_btn)

        self.nav_history_btn = QPushButton('📁 历史记录')
        self.nav_history_btn.setCheckable(True)
        layout.addWidget(self.nav_history_btn)

        layout.addStretch()

        version_label = QLabel('v1.0.0')
        version_label.setStyleSheet('color: #7f8c8d; padding: 8px 12px; font-size: 11px;')
        layout.addWidget(version_label)

        return nav

    def _create_workspace(self) -> QWidget:
        workspace = QWidget()
        layout = QHBoxLayout(workspace)
        layout.setContentsMargins(6, 6, 6, 6)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧: 上传 + 设置（用垂直splitter）
        left_splitter = QSplitter(Qt.Orientation.Vertical)

        self.upload_widget = UploadWidget()
        left_splitter.addWidget(self.upload_widget)

        self.settings_panel = SettingsPanel(self.palette_manager)
        left_splitter.addWidget(self.settings_panel)

        # 上传区占60%，设置区占40%
        left_splitter.setSizes([350, 250])

        splitter.addWidget(left_splitter)

        # 右侧: 预览
        self.preview_widget = PreviewWidget()
        splitter.addWidget(self.preview_widget)

        # 左侧占40%，右侧占60%
        splitter.setSizes([380, 550])

        # 设置splitter的最小尺寸
        splitter.setChildrenCollapsible(False)

        layout.addWidget(splitter)
        return workspace

    def _connect_signals(self):
        # 导航
        self.nav_workspace_btn.clicked.connect(lambda: self._switch_page(0))
        self.nav_history_btn.clicked.connect(lambda: self._switch_page(1))

        # 上传
        self.upload_widget.image_loaded.connect(self._on_image_loaded)
        self.upload_widget.crop_changed.connect(self._on_crop_changed)
        self.upload_widget.crop_cleared.connect(self._on_crop_cleared)

        # 设置
        self.settings_panel.settings_changed.connect(self._on_settings_changed)
        self.settings_panel.generate_clicked.connect(self._on_generate)

        # 历史
        self.history_widget.project_selected.connect(self._on_history_selected)

    def _switch_page(self, index: int):
        self.content_stack.setCurrentIndex(index)
        self.nav_workspace_btn.setChecked(index == 0)
        self.nav_history_btn.setChecked(index == 1)
        if index == 1:
            self.history_widget.refresh()

    def _on_image_loaded(self, filepath: str):
        self.preview_widget.set_original_image(filepath)
        self.settings_panel.set_enabled(True)
        self._current_result = None
        self.statusBar().showMessage(f'图片已加载: {os.path.basename(filepath)}')

    def _on_crop_changed(self, rect: tuple):
        self._current_result = None  # 裁剪变了，清除缓存
        self.statusBar().showMessage(
            f'裁剪区域已更新: ({rect[0]},{rect[1]}) → ({rect[2]},{rect[3]})'
        )

    def _on_crop_cleared(self):
        self._current_result = None
        self.statusBar().showMessage('裁剪已重置')

    def _on_settings_changed(self):
        """点击预览"""
        if self.upload_widget.current_image_path:
            self._update_preview()

    def _update_preview(self):
        settings = self.settings_panel.get_settings()
        image_path = self.upload_widget.current_image_path

        if not image_path:
            return

        try:
            self.statusBar().showMessage('正在生成预览...')
            QApplication.processEvents()

            pixelizer = Pixelizer(self.palette_manager)
            config = PixelizeConfig(
                grid_width=settings['grid_width'],
                grid_height=settings['grid_height'],
                palette_brand=settings['palette_brand'],
                max_colors=settings['max_colors'],
                dithering=settings['dithering'],
                crop_rect=self.upload_widget.get_crop_rect()
            )

            result = pixelizer.process(image_path, config)
            self._current_result = result

            self.preview_widget.update_preview(
                result.matched_rgb,
                result.color_index_map,
                result.palette,
                result.usage_stats
            )

            self.statusBar().showMessage(
                f'预览已更新 | {result.grid_width}×{result.grid_height} | '
                f'{result.color_count} 种颜色 | {result.total_beads} 颗豆子'
            )

        except Exception as e:
            self.statusBar().showMessage(f'预览失败: {str(e)}')
            QMessageBox.warning(self, '错误', f'处理图片时出错:\n{str(e)}')

    def _on_generate(self):
        settings = self.settings_panel.get_settings()
        image_path = self.upload_widget.current_image_path

        if not image_path:
            QMessageBox.warning(self, '提示', '请先上传图片')
            return

        try:
            self.statusBar().showMessage('正在生成图纸...')
            QApplication.processEvents()

            # 如果没有预览缓存，重新处理
            if self._current_result is None:
                pixelizer = Pixelizer(self.palette_manager)
                config = PixelizeConfig(
                    grid_width=settings['grid_width'],
                    grid_height=settings['grid_height'],
                    palette_brand=settings['palette_brand'],
                    max_colors=settings['max_colors'],
                    dithering=settings['dithering'],
                    crop_rect=self.upload_widget.get_crop_rect()
                )
                self._current_result = pixelizer.process(image_path, config)

            result = self._current_result

            # 生成PDF
            project_name = settings.get('project_name', 'beads_pattern')
            pdf_path = self.history_manager.get_output_path(project_name, '.pdf')

            pdf_gen = PDFGenerator()
            pdf_gen.generate(
                filepath=pdf_path,
                color_id_map=result.color_index_map,
                palette=result.palette,
                usage_stats=result.usage_stats,
                title=project_name,
                grid_width=result.grid_width,
                grid_height=result.grid_height
            )

            # 保存预览图
            from PIL import Image as PILImage
            preview_path = self.history_manager.get_output_path(project_name, '.png')
            preview_img = PILImage.fromarray(result.matched_rgb)
            scale = max(1, 400 // max(result.grid_width, result.grid_height))
            preview_img_resized = preview_img.resize(
                (result.grid_width * scale, result.grid_height * scale),
                PILImage.Resampling.NEAREST
            )
            preview_img_resized.save(preview_path)

            # 保存历史记录
            stored_image = self.history_manager.copy_image_to_storage(
                image_path, project_name
            )
            crop_rect = self.upload_widget.get_crop_rect()
            record = ProjectRecord(
                name=project_name,
                original_image_path=stored_image,
                grid_width=result.grid_width,
                grid_height=result.grid_height,
                palette_brand=settings['palette_brand'],
                max_colors=settings['max_colors'],
                dithering=settings['dithering'],
                pdf_path=pdf_path,
                preview_path=preview_path,
                usage_stats_json=json.dumps(result.usage_stats),
                crop_rect_json=json.dumps(list(crop_rect)) if crop_rect else ''
            )
            self.history_manager.save_project(record)

            self.statusBar().showMessage(f'图纸已生成: {pdf_path}')

            QMessageBox.information(
                self, '完成',
                f'PDF图纸已生成！\n\n'
                f'尺寸: {result.grid_width}×{result.grid_height}\n'
                f'颜色: {result.color_count} 种\n'
                f'总数: {result.total_beads} 颗\n\n'
                f'保存路径:\n{pdf_path}'
            )

            # 打开PDF
            if sys.platform == 'win32':
                os.startfile(pdf_path)
            elif sys.platform == 'darwin':
                os.system(f'open "{pdf_path}"')
            else:
                os.system(f'xdg-open "{pdf_path}"')

        except Exception as e:
            self.statusBar().showMessage(f'生成失败: {str(e)}')
            QMessageBox.critical(self, '错误', f'生成图纸时出错:\n{str(e)}')

    def _on_history_selected(self, project_id: int):
        project = self.history_manager.get_project(project_id)
        if project and project.pdf_path and os.path.exists(project.pdf_path):
            if sys.platform == 'win32':
                os.startfile(project.pdf_path)
            elif sys.platform == 'darwin':
                os.system(f'open "{project.pdf_path}"')
            else:
                os.system(f'xdg-open "{project.pdf_path}"')