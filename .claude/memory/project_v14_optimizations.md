---
name: v1.4 优化内容记录
description: 2026-04-22 完成的核心优化，图纸质量和 PDF 导出改进
type: project
---

v1.4（2026-04-22）完成以下优化，已推送到 GitHub main 分支（commit 0f3eeb2）。

**图纸生成质量：**
- 修复超采样 bug：`image_processor.py:83`，原来 `mid = target*4` 可能大于原图，改为只有 `mid < src` 时才做中间缩放
- K-Means 颜色优选：`color_matcher.py._select_optimal_colors_kmeans`，在 LAB 空间聚类替代频率 Top N，回退方案保留
- Floyd-Steinberg 优化：预批量转 LAB，误差扩散在 LAB 空间进行，结果向量化构建

**PDF 导出：**
- 单页自适应：去掉 `min_cell_size`，`_calc_cell_size` 纯计算无下限
- 板块边界线：`BOARD_SIZE=29`，`_draw_board_boundaries` 每29格画粗线（1.4pt），外框2pt
- 色号不截断：格子 ≥3mm 显示完整 ID，更小则省略整行文字
- 图例完整：溢出放第二页（`_draw_legend_overflow_page`），显示占比 %
- 新增 `.gitignore`

**Why:** 用户反馈图纸效果一般，PDF 分页使用不便。

**How to apply:** 后续如需调整 PDF 布局参数，主要常量都在 `PDFGenerator` 类顶部（`BOARD_SIZE`, `MARGIN`, `LEGEND_H` 等）。
