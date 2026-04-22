---
name: 项目概览
description: beads-designer 项目的整体介绍、技术栈和核心流程
type: project
---

拼豆图纸生成器（Beads Designer），版本 1.4，PyQt6 桌面应用。将图片转换成可打印的拼豆（Perler/Artkal）图纸 PDF。

**Why:** 手工艺用途，帮助用户把照片转成拼豆配色图纸。

**技术栈：**
- GUI：PyQt6
- 图像处理：Pillow + NumPy
- 颜色匹配：SciPy KD-Tree + CIELAB Delta E 2000
- PDF 生成：ReportLab
- 历史记录：SQLite3

**核心流程（4步）：**
1. 上传图片（支持拖拽 + 可缩放裁剪）
2. 生成预览（像素化 + CIELAB 色板匹配 + 统计）
3. 格子编辑（逐格点击改色，实时统计）
4. 导出 PDF（带色号、板块线、图例）

**主要模块：**
- `core/image_processor.py` — 图像加载、超采样缩放、预处理增强
- `core/color_matcher.py` — CIELAB 匹配、K-Means 颜色优选、Floyd-Steinberg 抖动
- `core/pdf_generator.py` — PDF 布局生成
- `core/pixelizer.py` — 完整处理流水线
- `core/palette.py` — 色板管理（Perler 270色 / Artkal）
- `core/project.py` — SQLite 历史记录
- `ui/` — PyQt6 界面层（主窗口、上传、预览、编辑、历史）

**How to apply:** 修改核心逻辑时注意 core/ 和 ui/ 完全分离，core 层不应依赖 PyQt6。
