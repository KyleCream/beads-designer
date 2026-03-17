"""
主窗口模块
应用程序的主界面，管理整体布局和页面流转
"""

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QToolBar, QPushButton, QStatusBar, QMessageBox,
    QSplitter, QLabel
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QAction

from .upload_widget import UploadWidget
from .settings_panel import SettingsPanel
from .preview_widget import PreviewWidget
from .history_widget import HistoryWidget

from core.palette import PaletteManager
from core.project import HistoryManager


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("拼豆图纸生成器 - Beads Designer")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        # 初始化核心组件
        self._init_managers()
        self._init_ui()
        self._connect_signals()

    def _init_managers(self):
        """初始化管理器"""
        self.palette_manager = PaletteManager()
        self.palette_manager.load_builtin_palettes()
        self.history_manager = HistoryManager()

    def _init_ui(self):
        """初始化UI"""
        # 中央widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧导航栏
        nav_widget = self._create_nav_bar()
        main_layout.addWidget(nav_widget)

        # 右侧内容区域 - 使用 QStackedWidget
        self.content_stack = QStackedWidget()

        # 页面1: 工作区（上传+设置+预览）
        self.workspace_page = self._create_workspace()
        self.content_stack.addWidget(self.workspace_page)

        # 页面2: 历史记录
        self.history_widget = HistoryWidget(self.history_manager)
        self.content_stack.addWidget(self.history_widget)

        main_layout.addWidget(self.content_stack, 1)

        # 状态栏
        self.statusBar().showMessage("Ready - 请上传图片开始制作")

    def _create_nav_bar(self) -> QWidget:
        """创建左侧导航栏"""
        nav = QWidget()
        nav.setFixedWidth(180)
        nav.setStyleSheet("""
            QWidget {
                background-color: #2c3e50;
            }
            QPushButton {
                color: white;
                background-color: transparent;
                border: none;
                padding: 15px 20px;
                text-align: left;
                font-size: 14px;
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

        # 标题
        title_label = QLabel("🎨 拼豆设计器")
        title_label.setStyleSheet("""
            color: white;
            font-size: 18px;
            font-weight: bold;
            padding: 20px;
            border-bottom: 1px solid #34495e;
        """)
        layout.addWidget(title_label)

        # 导航按钮
        self.nav_workspace_btn = QPushButton("📋 新建图纸")
        self.nav_workspace_btn.setCheckable(True)
        self.nav_workspace_btn.setChecked(True)
        layout.addWidget(self.nav_workspace_btn)

        self.nav_history_btn = QPushButton("📁 历史记录")
        self.nav_history_btn.setCheckable(True)
        layout.addWidget(self.nav_history_btn)

        layout.addStretch()

        # 版本信息
        version_label = QLabel("v1.0.0")
        version_label.setStyleSheet("color: #7f8c8d; padding: 10px;")
        layout.addWidget(version_label)

        return nav

    def _create_workspace(self) -> QWidget:
        """创建工作区"""
        workspace = QWidget()
        layout = QHBoxLayout(workspace)
        layout.setContentsMargins(10, 10, 10, 10)

        # 使用 QSplitter 分割
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧: 上传和设置
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.upload_widget = UploadWidget()
        left_layout.addWidget(self.upload_widget, 2)

        self.settings_panel = SettingsPanel(self.palette_manager)
        left_layout.addWidget(self.settings_panel, 1)

        splitter.addWidget(left_panel)

        # 右侧: 预览
        self.preview_widget = PreviewWidget()
        splitter.addWidget(self.preview_widget)

        splitter.setSizes([400, 800])
        layout.addWidget(splitter)

        return workspace

    def _connect_signals(self):
        """连接信号"""
        # 导航
        self.nav_workspace_btn.clicked.connect(lambda: self._switch_page(0))
        self.nav_history_btn.clicked.connect(lambda: self._switch_page(1))

        # 上传 -> 预览
        self.upload_widget.image_loaded.connect(self._on_image_loaded)
        self.upload_widget.crop_changed.connect(self._on_crop_changed)

        # 设置变更 -> 更新预览
        self.settings_panel.settings_changed.connect(self._on_settings_changed)
        self.settings_panel.generate_clicked.connect(self._on_generate)

        # 历史记录
        self.history_widget.project_selected.connect(self._on_history_selected)

    def _switch_page(self, index: int):
        """切换页面"""
        self.content_stack.setCurrentIndex(index)
        self.nav_workspace_btn.setChecked(index == 0)
        self.nav_history_btn.setChecked(index == 1)
        if index == 1:
            self.history_widget.refresh()

    def _on_image_loaded(self, filepath: str):
        """图片加载完成"""
        self.preview_widget.set_original_image(filepath)
        self.settings_panel.set_enabled(True)
        self.statusBar().showMessage(f"图片已加载: {os.path.basename(filepath)}")

    def _on_crop_changed(self, rect: tuple):
        """裁剪区域变更"""
        self.preview_widget.update_crop(rect)

    def _on_settings_changed(self):
        """设置变更，更新预览"""
        if self.upload_widget.current_image_path:
            self._update_preview()

    def _update_preview(self):
        """更新预览 - 使用Pixelizer引擎"""
        from core.pixelizer import Pixelizer, PixelizeConfig

        settings = self.settings_panel.get_settings()
        image_path = self.upload_widget.current_image_path

        if not image_path:
            return

        try:
            pixelizer = Pixelizer(self.palette_manager)

            config = PixelizeConfig(
                grid_width=settings["grid_width"],
                grid_height=settings["grid_height"],
                palette_brand=settings["palette_brand"],
                max_colors=settings["max_colors"],
                dithering=settings["dithering"],
                crop_rect=self.upload_widget.get_crop_rect()
            )

            result = pixelizer.process(image_path, config)

            # 缓存结果供生成PDF时复用
            self._current_result = result
            self._current_config = config

            self.preview_widget.update_preview(
                result.matched_rgb,
                result.color_index_map,
                result.palette,
                result.usage_stats
            )

            self.statusBar().showMessage(
                f"预览已更新 | {result.grid_width}×{result.grid_height} | "
                f"{result.color_count} colors | {result.total_beads} beads"
            )

        except Exception as e:
            self.statusBar().showMessage(f"Error: {str(e)}")
            QMessageBox.warning(self, "错误", f"处理图片时出错:\n{str(e)}")

    def _on_generate(self):
        """生成PDF图纸 - 使用Pixelizer引擎"""
        from core.pixelizer import Pixelizer, PixelizeConfig
        from core.pdf_generator import PDFGenerator
        from core.project import ProjectRecord
        from PIL import Image as PILImage
        import json

        settings = self.settings_panel.get_settings()
        image_path = self.upload_widget.current_image_path

        if not image_path:
            QMessageBox.warning(self, "提示", "请先上传图片")
            return

        try:
            self.statusBar().showMessage("正在生成图纸...")

            # 如果有缓存的结果且配置一致，直接使用
            if (
                hasattr(self, '_current_result')
                and self._current_result is not None
            ):
                result = self._current_result
            else:
                pixelizer = Pixelizer(self.palette_manager)
                config = PixelizeConfig(
                    grid_width=settings["grid_width"],
                    grid_height=settings["grid_height"],
                    palette_brand=settings["palette_brand"],
                    max_colors=settings["max_colors"],
                    dithering=settings["dithering"],
                    crop_rect=self.upload_widget.get_crop_rect()
                )
                result = pixelizer.process(image_path, config)

            # 生成PDF
            project_name = settings.get("project_name", "beads_pattern")
            pdf_path = self.history_manager.get_output_path(
                project_name, ".pdf"
            )

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
            preview_path = self.history_manager.get_output_path(
                project_name, ".png"
            )
            preview_img = PILImage.fromarray(result.matched_rgb)
            scale = max(1, 400 // max(result.grid_width, result.grid_height))
            preview_img_resized = preview_img.resize(
                (result.grid_width * scale, result.grid_height * scale),
                PILImage.Resampling.NEAREST
            )
            preview_img_resized.save(preview_path)

            # 保存到历史记录
            stored_image = self.history_manager.copy_image_to_storage(
                image_path, project_name
            )
            crop_rect = self.upload_widget.get_crop_rect()
            record = ProjectRecord(
                name=project_name,
                original_image_path=stored_image,
                grid_width=result.grid_width,
                grid_height=result.grid_height,
                palette_brand=settings["palette_brand"],
                max_colors=settings["max_colors"],
                dithering=settings["dithering"],
                pdf_path=pdf_path,
                preview_path=preview_path,
                usage_stats_json=json.dumps(result.usage_stats),
                crop_rect_json=(
                    json.dumps(list(crop_rect)) if crop_rect else ""
                )
            )
            self.history_manager.save_project(record)

            self.statusBar().showMessage(f"图纸已生成: {pdf_path}")
            QMessageBox.information(
                self, "完成",
                f"PDF图纸已生成！\n\n"
                f"尺寸: {result.grid_width}×{result.grid_height}\n"
                f"颜色: {result.color_count} 种\n"
                f"总数: {result.total_beads} 颗\n\n"
                f"保存路径:\n{pdf_path}"
            )

            # 打开文件
            if sys.platform == 'win32':
                os.startfile(pdf_path)
            elif sys.platform == 'darwin':
                os.system(f'open "{pdf_path}"')
            else:
                os.system(f'xdg-open "{pdf_path}"')

        except Exception as e:
            self.statusBar().showMessage(f"生成失败: {str(e)}")
            QMessageBox.critical(
                self, "错误", f"生成图纸时出错:\n{str(e)}"
            )

    def _on_history_selected(self, project_id: int):
        """从历史记录中选择项目"""
        project = self.history_manager.get_project(project_id)
        if project and project.pdf_path and os.path.exists(project.pdf_path):
            if sys.platform == 'win32':
                os.startfile(project.pdf_path)
            else:
                os.system(f'open "{project.pdf_path}"')