"""
主窗口 v3
修复：顶部步骤按钮始终可见，按流程启用/禁用
"""

import sys
import os
import json

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QMessageBox,
    QSplitter, QLabel, QFrame
)
from PyQt6.QtCore import Qt
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

    def __init__(self):
        super().__init__()
        self.setWindowTitle('拼豆图纸生成器 - Beads Designer')
        self._adapt_to_screen()
        self._current_result: PixelizeResult = None
        self._init_managers()
        self._init_ui()
        self._connect_signals()
        self._update_step_state()

    def _adapt_to_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            a = screen.availableGeometry()
            w = max(1000, min(int(a.width() * 0.85), 1700))
            h = max(650, min(int(a.height() * 0.85), 1050))
            self.resize(w, h)
            self.move(a.x() + (a.width() - w) // 2, a.y() + (a.height() - h) // 2)
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
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._create_nav())

        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self._create_workspace())
        self.history_widget = HistoryWidget(self.history_manager)
        self.content_stack.addWidget(self.history_widget)
        root.addWidget(self.content_stack, 1)

        self.statusBar().showMessage('Ready - 请上传图片开始制作')
        self.statusBar().setStyleSheet(
            'background: #2c3e50; color: white; font-size: 11px; padding: 2px 8px;'
        )

    # ==================== 导航 ====================

    def _create_nav(self):
        nav = QWidget()
        nav.setFixedWidth(150)
        nav.setStyleSheet("""
            QWidget { background: #2c3e50; }
            QPushButton {
                color: white; background: transparent; border: none;
                padding: 12px 14px; text-align: left; font-size: 13px;
                border-left: 3px solid transparent;
            }
            QPushButton:hover { background: #34495e; border-left-color: #3498db; }
            QPushButton:checked { background: #34495e; border-left-color: #3498db; }
        """)
        lo = QVBoxLayout(nav)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        t = QLabel('🎨 拼豆设计器')
        t.setStyleSheet(
            'color:white; font-size:15px; font-weight:bold;'
            'padding:14px 10px; border-bottom:1px solid #34495e;'
        )
        lo.addWidget(t)

        self.nav_work = QPushButton('📋 新建图纸')
        self.nav_work.setCheckable(True)
        self.nav_work.setChecked(True)
        lo.addWidget(self.nav_work)

        self.nav_hist = QPushButton('📁 历史记录')
        self.nav_hist.setCheckable(True)
        lo.addWidget(self.nav_hist)

        lo.addStretch()
        v = QLabel('v1.2.0')
        v.setStyleSheet('color:#7f8c8d; padding:8px 10px; font-size:10px;')
        lo.addWidget(v)
        return nav

    # ==================== 工作区 ====================

    def _create_workspace(self):
        ws = QWidget()
        lo = QHBoxLayout(ws)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        # ---- 左侧 ----
        left = QWidget()
        left.setFixedWidth(280)
        left.setStyleSheet('background: #fafbfc; border-right: 1px solid #e8e8e8;')
        ll = QVBoxLayout(left)
        ll.setContentsMargins(10, 10, 10, 10)
        ll.setSpacing(8)

        self.upload_widget = UploadWidget()
        ll.addWidget(self.upload_widget)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet('color: #e8e8e8;')
        ll.addWidget(sep)

        self.settings_panel = SettingsPanel(self.palette_manager)
        ll.addWidget(self.settings_panel, 1)

        lo.addWidget(left)

        # ---- 右侧 ----
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        # 顶部操作栏 - 始终可见
        rl.addWidget(self._create_action_bar())

        # 内容切换
        self.work_stack = QStackedWidget()
        self.preview_widget = PreviewWidget()
        self.work_stack.addWidget(self.preview_widget)
        self.grid_editor = GridEditorWidget()
        self.work_stack.addWidget(self.grid_editor)
        rl.addWidget(self.work_stack, 1)

        lo.addWidget(right, 1)
        return ws

    def _create_action_bar(self):
        """顶部操作栏 - 所有按钮始终可见"""
        bar = QWidget()
        bar.setFixedHeight(52)
        bar.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border-bottom: 1px solid #e8e8e8;
            }
        """)
        lo = QHBoxLayout(bar)
        lo.setContentsMargins(16, 6, 16, 6)
        lo.setSpacing(12)

        # 步骤指示
        self.step_label = QLabel('')
        self.step_label.setStyleSheet('font-size: 13px; color: #636e72;')
        lo.addWidget(self.step_label)

        lo.addStretch()

        # ===== 三个主按钮 - 始终可见 =====

        self.btn_preview = QPushButton('  👁️  预览效果  ')
        self.btn_preview.setStyleSheet(self._action_style(
            '#00b894', '#00a381', '#dfe6e9'
        ))
        lo.addWidget(self.btn_preview)

        # 步骤箭头
        arrow1 = QLabel('▸')
        arrow1.setStyleSheet('font-size: 16px; color: #b2bec3;')
        lo.addWidget(arrow1)

        self.btn_edit = QPushButton('  📐  生成图纸  ')
        self.btn_edit.setStyleSheet(self._action_style(
            '#0984e3', '#0876cc', '#dfe6e9'
        ))
        lo.addWidget(self.btn_edit)

        arrow2 = QLabel('▸')
        arrow2.setStyleSheet('font-size: 16px; color: #b2bec3;')
        lo.addWidget(arrow2)

        self.btn_pdf = QPushButton('  📄  导出PDF  ')
        self.btn_pdf.setStyleSheet(self._action_style(
            '#d63031', '#c0392b', '#dfe6e9'
        ))
        lo.addWidget(self.btn_pdf)

        # 辅助按钮
        lo.addSpacing(8)

        self.btn_back = QPushButton('← 返回预览')
        self.btn_back.setStyleSheet("""
            QPushButton {
                background: transparent; color: #636e72; border: 1px solid #ddd;
                padding: 6px 12px; border-radius: 4px; font-size: 11px;
            }
            QPushButton:hover { background: #f0f0f0; border-color: #bbb; }
            QPushButton:disabled { color: #ccc; border-color: #eee; }
        """)
        lo.addWidget(self.btn_back)

        return bar

    @staticmethod
    def _action_style(bg, hover, disabled_bg):
        return f"""
            QPushButton {{
                background-color: {bg}; color: white; border: none;
                padding: 7px 16px; border-radius: 5px;
                font-size: 12px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:disabled {{
                background-color: {disabled_bg}; color: #b2bec3;
            }}
        """

    # ==================== 状态管理 ====================

    def _update_step_state(self):
        """根据当前状态更新所有按钮的启用/禁用"""
        has_image = self.upload_widget.current_image_path is not None
        has_preview = self._current_result is not None
        is_editing = self.work_stack.currentIndex() == 1

        # 预览按钮：有图片就可以点
        self.btn_preview.setEnabled(has_image)

        # 生成图纸：有预览结果就可以点
        self.btn_edit.setEnabled(has_preview)

        # 导出PDF：在编辑模式且有数据就可以点
        self.btn_pdf.setEnabled(is_editing and has_preview)

        # 返回预览：只在编辑模式可点
        self.btn_back.setEnabled(is_editing)

        # 步骤提示
        if is_editing:
            self.step_label.setText('📐 编辑图纸 — 点击格子修改颜色')
        elif has_preview:
            self.step_label.setText('👁️ 预览完成 — 确认后点击「生成图纸」')
        elif has_image:
            self.step_label.setText('📷 图片已加载 — 调整参数后点击「预览效果」')
        else:
            self.step_label.setText('请先上传一张图片')

    # ==================== 信号连接 ====================

    def _connect_signals(self):
        self.nav_work.clicked.connect(lambda: self._switch_page(0))
        self.nav_hist.clicked.connect(lambda: self._switch_page(1))

        self.upload_widget.image_loaded.connect(self._on_image_loaded)
        self.upload_widget.crop_changed.connect(self._on_crop_changed)
        self.upload_widget.crop_cleared.connect(self._on_crop_cleared)
        self.upload_widget.detail_requested.connect(self._on_detail)

        self.btn_preview.clicked.connect(self._on_preview)
        self.btn_edit.clicked.connect(self._on_generate_grid)
        self.btn_pdf.clicked.connect(self._on_export_pdf)
        self.btn_back.clicked.connect(self._on_back)

        self.grid_editor.grid_modified.connect(self._on_grid_modified)
        self.history_widget.project_selected.connect(self._on_hist_selected)

    def _switch_page(self, idx):
        self.content_stack.setCurrentIndex(idx)
        self.nav_work.setChecked(idx == 0)
        self.nav_hist.setChecked(idx == 1)
        if idx == 1:
            self.history_widget.refresh()

    # ==================== 事件 ====================

    def _on_image_loaded(self, fp):
        self._current_result = None
        self.work_stack.setCurrentIndex(0)
        self._update_step_state()
        self.statusBar().showMessage(f'已加载: {os.path.basename(fp)}')

    def _on_crop_changed(self, rect):
        self._current_result = None
        self._update_step_state()

    def _on_crop_cleared(self):
        self._current_result = None
        self._update_step_state()

    def _on_detail(self):
        if not self.upload_widget.current_image_path:
            return
        dlg = ImageDetailDialog(
            self.upload_widget.current_image_path,
            self.upload_widget.get_crop_rect(),
            self
        )
        if dlg.exec():
            cr = dlg.get_crop_rect()
            if cr:
                self.upload_widget.apply_external_crop(cr)
            else:
                self.upload_widget.clear_crop()

    def _on_preview(self):
        path = self.upload_widget.current_image_path
        if not path:
            QMessageBox.warning(self, '提示', '请先上传图片')
            return
        try:
            self.statusBar().showMessage('正在生成预览...')
            QApplication.processEvents()

            s = self.settings_panel.get_settings()
            pxl = Pixelizer(self.palette_manager)
            cfg = PixelizeConfig(
                grid_width=s['grid_width'], grid_height=s['grid_height'],
                palette_brand=s['palette_brand'], max_colors=s['max_colors'],
                dithering=s['dithering'],
                crop_rect=self.upload_widget.get_crop_rect()
            )
            result = pxl.process(path, cfg)
            self._current_result = result

            self.preview_widget.update_preview(
                result.matched_rgb, result.color_index_map,
                result.palette, result.usage_stats
            )

            # 保持在预览页面
            self.work_stack.setCurrentIndex(0)
            self._update_step_state()

            self.statusBar().showMessage(
                f'预览完成 | {result.grid_width}×{result.grid_height} | '
                f'{result.color_count} 色 | {result.total_beads} 颗'
            )
        except Exception as e:
            self.statusBar().showMessage(f'失败: {e}')
            QMessageBox.warning(self, '错误', f'处理出错:\n{e}')

    def _on_generate_grid(self):
        if self._current_result is None:
            QMessageBox.warning(self, '提示', '请先预览效果')
            return
        self.grid_editor.load_result(self._current_result)
        self.work_stack.setCurrentIndex(1)
        self._update_step_state()
        self.statusBar().showMessage('图纸已生成 — 点击格子可修改颜色，完成后导出PDF')

    def _on_grid_modified(self):
        self.statusBar().showMessage('图纸已修改')

    def _on_back(self):
        if self.grid_editor.is_modified:
            r = QMessageBox.question(
                self, '确认', '返回预览将丢失手动修改，确定吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if r != QMessageBox.StandardButton.Yes:
                return
        self.work_stack.setCurrentIndex(0)
        self._update_step_state()

    def _on_export_pdf(self):
        if self._current_result is None:
            return
        try:
            self.statusBar().showMessage('正在导出PDF...')
            QApplication.processEvents()

            s = self.settings_panel.get_settings()
            name = s.get('project_name', 'beads_pattern')
            result = self.grid_editor.get_current_result()

            pdf_path = self.history_manager.get_output_path(name, '.pdf')
            PDFGenerator().generate(
                filepath=pdf_path,
                color_id_map=result.color_index_map,
                palette=result.palette,
                usage_stats=result.usage_stats,
                title=name,
                grid_width=result.grid_width,
                grid_height=result.grid_height
            )

            # 预览图
            from PIL import Image as PILImage
            pp = self.history_manager.get_output_path(name, '.png')
            img = PILImage.fromarray(result.matched_rgb)
            sc = max(1, 400 // max(result.grid_width, result.grid_height))
            img.resize(
                (result.grid_width * sc, result.grid_height * sc),
                PILImage.Resampling.NEAREST
            ).save(pp)

            # 历史
            path = self.upload_widget.current_image_path
            si = self.history_manager.copy_image_to_storage(path, name)
            cr = self.upload_widget.get_crop_rect()
            self.history_manager.save_project(ProjectRecord(
                name=name, original_image_path=si,
                grid_width=result.grid_width, grid_height=result.grid_height,
                palette_brand=s['palette_brand'], max_colors=s['max_colors'],
                dithering=s['dithering'], pdf_path=pdf_path, preview_path=pp,
                usage_stats_json=json.dumps(result.usage_stats),
                crop_rect_json=json.dumps(list(cr)) if cr else ''
            ))

            self.statusBar().showMessage(f'已导出: {pdf_path}')
            QMessageBox.information(
                self, '导出成功',
                f'PDF图纸已生成！\n\n'
                f'尺寸: {result.grid_width}×{result.grid_height}\n'
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

    def _on_hist_selected(self, pid):
        p = self.history_manager.get_project(pid)
        if p and p.pdf_path and os.path.exists(p.pdf_path):
            if sys.platform == 'win32':
                os.startfile(p.pdf_path)
            elif sys.platform == 'darwin':
                os.system(f'open "{p.pdf_path}"')
            else:
                os.system(f'xdg-open "{p.pdf_path}"')