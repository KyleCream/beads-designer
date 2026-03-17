"""
主窗口模块 v2
新布局：左侧(上传缩略图+设置面板) | 中间(预览/编辑区) | 流程按钮
新流程：上传 → 设置 → 预览 → 编辑图纸 → 导出PDF
"""

import sys
import os
import json

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QMessageBox,
    QSplitter, QLabel, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap

from .upload_widget import UploadWidget, ImageDetailDialog
from .settings_panel import SettingsPanel
from .preview_widget import PreviewWidget
from .grid_editor_widget import GridEditorWidget
from .history_widget import HistoryWidget

from core.palette import PaletteManager
from core.project import HistoryManager, ProjectRecord
from core.pixelizer import Pixelizer, PixelizeConfig, PixelizeResult
from core.pdf_generator import PDFGenerator


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle('拼豆图纸生成器 - Beads Designer')
        self._adapt_to_screen()

        self._current_result: PixelizeResult = None

        self._init_managers()
        self._init_ui()
        self._connect_signals()

    def _adapt_to_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            w = max(1000, min(int(avail.width() * 0.85), 1700))
            h = max(650, min(int(avail.height() * 0.85), 1050))
            self.resize(w, h)
            self.move(
                avail.x() + (avail.width() - w) // 2,
                avail.y() + (avail.height() - h) // 2
            )
        else:
            self.resize(1200, 800)
        self.setMinimumSize(900, 600)

    def _init_managers(self):
        self.palette_manager = PaletteManager()
        self.palette_manager.load_builtin_palettes()
        self.history_manager = HistoryManager()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # === 左侧导航 ===
        root_layout.addWidget(self._create_nav_bar())

        # === 内容区 ===
        self.content_stack = QStackedWidget()

        # 页面0: 工作区
        self.content_stack.addWidget(self._create_workspace())

        # 页面1: 历史记录
        self.history_widget = HistoryWidget(self.history_manager)
        self.content_stack.addWidget(self.history_widget)

        root_layout.addWidget(self.content_stack, 1)

        self.statusBar().showMessage('Ready - 请上传图片开始制作')

    # ==================== 导航栏 ====================

    def _create_nav_bar(self) -> QWidget:
        nav = QWidget()
        nav.setFixedWidth(150)
        nav.setStyleSheet("""
            QWidget { background-color: #2c3e50; }
            QPushButton {
                color: white; background: transparent; border: none;
                padding: 12px 14px; text-align: left; font-size: 13px;
                border-left: 3px solid transparent;
            }
            QPushButton:hover {
                background-color: #34495e; border-left-color: #3498db;
            }
            QPushButton:checked {
                background-color: #34495e; border-left-color: #3498db;
            }
        """)
        layout = QVBoxLayout(nav)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel('🎨 拼豆设计器')
        title.setStyleSheet(
            'color:white; font-size:15px; font-weight:bold;'
            'padding:14px 10px; border-bottom:1px solid #34495e;'
        )
        layout.addWidget(title)

        self.nav_workspace_btn = QPushButton('📋 新建图纸')
        self.nav_workspace_btn.setCheckable(True)
        self.nav_workspace_btn.setChecked(True)
        layout.addWidget(self.nav_workspace_btn)

        self.nav_history_btn = QPushButton('📁 历史记录')
        self.nav_history_btn.setCheckable(True)
        layout.addWidget(self.nav_history_btn)

        layout.addStretch()
        v = QLabel('v1.1.0')
        v.setStyleSheet('color:#7f8c8d; padding:8px 10px; font-size:10px;')
        layout.addWidget(v)
        return nav

    # ==================== 工作区 ====================

    def _create_workspace(self) -> QWidget:
        workspace = QWidget()
        layout = QHBoxLayout(workspace)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- 左侧面板（上传缩略图 + 设置） ----
        left_panel = QWidget()
        left_panel.setFixedWidth(280)
        left_panel.setStyleSheet('background-color: #fafbfc; border-right: 1px solid #dcdde1;')
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        # 上传缩略图区
        self.upload_widget = UploadWidget()
        left_layout.addWidget(self.upload_widget)

        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet('color: #dcdde1;')
        left_layout.addWidget(line)

        # 设置面板
        self.settings_panel = SettingsPanel(self.palette_manager)
        left_layout.addWidget(self.settings_panel, 1)

        layout.addWidget(left_panel)

        # ---- 中间/右侧 内容区（预览 和 编辑 切换） ----
        right_area = QWidget()
        right_layout = QVBoxLayout(right_area)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # 顶部流程步骤条
        self.step_bar = self._create_step_bar()
        right_layout.addWidget(self.step_bar)

        # 内容切换区
        self.work_stack = QStackedWidget()

        # step0: 预览
        self.preview_widget = PreviewWidget()
        self.work_stack.addWidget(self.preview_widget)

        # step1: 图纸编辑
        self.grid_editor = GridEditorWidget()
        self.work_stack.addWidget(self.grid_editor)

        right_layout.addWidget(self.work_stack, 1)

        layout.addWidget(right_area, 1)

        return workspace

    def _create_step_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(50)
        bar.setStyleSheet('background-color: #fff; border-bottom: 1px solid #dcdde1;')
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(15, 5, 15, 5)
        layout.setSpacing(10)

        # 步骤指示
        self.step_label = QLabel('Step 1: 上传图片并设置参数')
        self.step_label.setStyleSheet('font-size: 14px; font-weight: bold; color: #2d3436;')
        layout.addWidget(self.step_label)

        layout.addStretch()

        # 流程按钮
        self.btn_preview = QPushButton('👁️ 预览效果')
        self.btn_preview.setStyleSheet(self._action_btn_style('#00b894', '#00a381'))
        self.btn_preview.setEnabled(False)
        layout.addWidget(self.btn_preview)

        self.btn_generate_grid = QPushButton('📐 生成图纸')
        self.btn_generate_grid.setStyleSheet(self._action_btn_style('#0984e3', '#0876cc'))
        self.btn_generate_grid.setEnabled(False)
        layout.addWidget(self.btn_generate_grid)

        self.btn_export_pdf = QPushButton('📄 导出PDF')
        self.btn_export_pdf.setStyleSheet(self._action_btn_style('#d63031', '#b71c1c'))
        self.btn_export_pdf.setEnabled(False)
        layout.addWidget(self.btn_export_pdf)

        self.btn_back_preview = QPushButton('← 返回预览')
        self.btn_back_preview.setStyleSheet(self._action_btn_style('#636e72', '#2d3436'))
        self.btn_back_preview.setVisible(False)
        layout.addWidget(self.btn_back_preview)

        return bar

    @staticmethod
    def _action_btn_style(bg: str, hover: str) -> str:
        return f"""
            QPushButton {{
                background-color: {bg}; color: white; border: none;
                padding: 7px 16px; border-radius: 4px;
                font-size: 12px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:disabled {{ background-color: #dfe6e9; color: #b2bec3; }}
        """

    # ==================== 信号连接 ====================

    def _connect_signals(self):
        # 导航
        self.nav_workspace_btn.clicked.connect(lambda: self._switch_page(0))
        self.nav_history_btn.clicked.connect(lambda: self._switch_page(1))

        # 上传
        self.upload_widget.image_loaded.connect(self._on_image_loaded)
        self.upload_widget.crop_changed.connect(self._on_crop_changed)
        self.upload_widget.crop_cleared.connect(self._on_crop_cleared)
        self.upload_widget.detail_requested.connect(self._on_detail_requested)

        # 流程按钮
        self.btn_preview.clicked.connect(self._on_preview)
        self.btn_generate_grid.clicked.connect(self._on_generate_grid)
        self.btn_export_pdf.clicked.connect(self._on_export_pdf)
        self.btn_back_preview.clicked.connect(self._on_back_to_preview)

        # 图纸编辑器
        self.grid_editor.grid_modified.connect(self._on_grid_modified)

        # 历史
        self.history_widget.project_selected.connect(self._on_history_selected)

    def _switch_page(self, index: int):
        self.content_stack.setCurrentIndex(index)
        self.nav_workspace_btn.setChecked(index == 0)
        self.nav_history_btn.setChecked(index == 1)
        if index == 1:
            self.history_widget.refresh()

    # ==================== 事件处理 ====================

    def _on_image_loaded(self, filepath: str):
        self.settings_panel.set_enabled(True)
        self.btn_preview.setEnabled(True)
        self._current_result = None
        self.btn_generate_grid.setEnabled(False)
        self.btn_export_pdf.setEnabled(False)
        self._switch_to_preview_mode()
        self.statusBar().showMessage(f'图片已加载: {os.path.basename(filepath)}')

    def _on_crop_changed(self, rect: tuple):
        self._current_result = None
        self.btn_generate_grid.setEnabled(False)

    def _on_crop_cleared(self):
        self._current_result = None
        self.btn_generate_grid.setEnabled(False)

    def _on_detail_requested(self):
        """打开图片详情弹窗进行精细裁剪"""
        if not self.upload_widget.current_image_path:
            return
        dialog = ImageDetailDialog(
            self.upload_widget.current_image_path,
            self.upload_widget.get_crop_rect(),
            self
        )
        if dialog.exec():
            crop_rect = dialog.get_crop_rect()
            if crop_rect:
                self.upload_widget.apply_external_crop(crop_rect)
            else:
                self.upload_widget.clear_crop()

    def _on_preview(self):
        """生成预览"""
        image_path = self.upload_widget.current_image_path
        if not image_path:
            QMessageBox.warning(self, '提示', '请先上传图片')
            return

        try:
            self.statusBar().showMessage('正在生成预览...')
            QApplication.processEvents()

            settings = self.settings_panel.get_settings()
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
                result.matched_rgb, result.color_index_map,
                result.palette, result.usage_stats
            )

            self.btn_generate_grid.setEnabled(True)
            self.step_label.setText('Step 2: 确认预览效果，点击「生成图纸」进入编辑')

            self.statusBar().showMessage(
                f'预览完成 | {result.grid_width}x{result.grid_height} | '
                f'{result.color_count} 色 | {result.total_beads} 颗'
            )
        except Exception as e:
            self.statusBar().showMessage(f'预览失败: {e}')
            QMessageBox.warning(self, '错误', f'处理出错:\n{e}')

    def _on_generate_grid(self):
        """从预览进入图纸编辑"""
        if self._current_result is None:
            QMessageBox.warning(self, '提示', '请先预览效果')
            return

        self.grid_editor.load_result(self._current_result)
        self._switch_to_editor_mode()
        self.btn_export_pdf.setEnabled(True)
        self.step_label.setText('Step 3: 编辑图纸（点击格子可修改颜色），完成后导出PDF')
        self.statusBar().showMessage('图纸已生成，可点击格子修改颜色')

    def _on_grid_modified(self):
        """图纸被编辑了"""
        self.statusBar().showMessage('图纸已修改（未保存）')

    def _on_back_to_preview(self):
        """返回预览"""
        # 如果编辑过，提示
        if self.grid_editor.is_modified:
            reply = QMessageBox.question(
                self, '确认',
                '返回预览将丢失对图纸的手动修改，确定吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._switch_to_preview_mode()
        self.step_label.setText('Step 2: 确认预览效果')

    def _switch_to_preview_mode(self):
        self.work_stack.setCurrentIndex(0)
        self.btn_preview.setVisible(True)
        self.btn_generate_grid.setVisible(True)
        self.btn_export_pdf.setVisible(False)
        self.btn_back_preview.setVisible(False)
        self.step_label.setText('Step 1: 上传图片并设置参数')

    def _switch_to_editor_mode(self):
        self.work_stack.setCurrentIndex(1)
        self.btn_preview.setVisible(False)
        self.btn_generate_grid.setVisible(False)
        self.btn_export_pdf.setVisible(True)
        self.btn_back_preview.setVisible(True)

    def _on_export_pdf(self):
        """导出PDF"""
        if self._current_result is None:
            return

        try:
            self.statusBar().showMessage('正在导出PDF...')
            QApplication.processEvents()

            settings = self.settings_panel.get_settings()
            project_name = settings.get('project_name', 'beads_pattern')

            # 从编辑器获取最新数据（可能被修改过）
            result = self.grid_editor.get_current_result()

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

            # 保存历史
            image_path = self.upload_widget.current_image_path
            stored_image = self.history_manager.copy_image_to_storage(image_path, project_name)
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

            self.statusBar().showMessage(f'PDF已导出: {pdf_path}')
            QMessageBox.information(
                self, '导出成功',
                f'PDF图纸已生成！\n\n'
                f'尺寸: {result.grid_width}x{result.grid_height}\n'
                f'颜色: {result.color_count} 种\n'
                f'总数: {result.total_beads} 颗\n\n'
                f'路径: {pdf_path}'
            )

            if sys.platform == 'win32':
                os.startfile(pdf_path)
            elif sys.platform == 'darwin':
                os.system(f'open "{pdf_path}"')
            else:
                os.system(f'xdg-open "{pdf_path}"')

        except Exception as e:
            self.statusBar().showMessage(f'导出失败: {e}')
            QMessageBox.critical(self, '错误', f'导出出错:\n{e}')

    def _on_history_selected(self, project_id: int):
        project = self.history_manager.get_project(project_id)
        if project and project.pdf_path and os.path.exists(project.pdf_path):
            if sys.platform == 'win32':
                os.startfile(project.pdf_path)
            elif sys.platform == 'darwin':
                os.system(f'open "{project.pdf_path}"')
            else:
                os.system(f'xdg-open "{project.pdf_path}"')