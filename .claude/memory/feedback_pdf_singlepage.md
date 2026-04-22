---
name: PDF 单页显示要求
description: 用户要求 PDF 始终单页显示，不分页，自适应格子大小
type: feedback
---

PDF 图纸必须始终在一页内显示完整网格，不允许跨页分割。

**Why:** 用户明确要求"无论选择多少，最终 PDF 输出都是一页显示，无非是自适应大小"。

**How to apply:** `pdf_generator.py` 的 `_calc_cell_size` 不设 min_cell_size，让格子随网格尺寸自动缩小以适应单页。图例溢出可放第二页，但网格本身必须单页。
