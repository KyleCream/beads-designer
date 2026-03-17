"""
项目管理模块
负责项目数据模型和历史记录的保存/加载
"""

import os
import json
import sqlite3
import shutil
from datetime import datetime
from typing import List, Optional, Dict
from dataclasses import dataclass, asdict


@dataclass
class ProjectRecord:
    """项目记录"""
    id: Optional[int] = None
    name: str = ""
    original_image_path: str = ""
    grid_width: int = 52
    grid_height: int = 52
    palette_brand: str = "Perler"
    max_colors: int = 0
    dithering: bool = False
    pdf_path: str = ""
    preview_path: str = ""
    usage_stats_json: str = "{}"
    crop_rect_json: str = ""
    created_at: str = ""
    updated_at: str = ""

    @property
    def usage_stats(self) -> Dict[str, int]:
        return json.loads(self.usage_stats_json) if self.usage_stats_json else {}

    @property
    def crop_rect(self) -> Optional[tuple]:
        if self.crop_rect_json:
            return tuple(json.loads(self.crop_rect_json))
        return None


class HistoryManager:
    """历史记录管理器"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "data"
            )
        self.data_dir = data_dir
        self.images_dir = os.path.join(data_dir, "images")
        self.outputs_dir = os.path.join(data_dir, "outputs")
        self.db_path = os.path.join(data_dir, "history.db")

        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.outputs_dir, exist_ok=True)

        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                original_image_path TEXT,
                grid_width INTEGER DEFAULT 52,
                grid_height INTEGER DEFAULT 52,
                palette_brand TEXT DEFAULT 'Perler',
                max_colors INTEGER DEFAULT 0,
                dithering INTEGER DEFAULT 0,
                pdf_path TEXT,
                preview_path TEXT,
                usage_stats_json TEXT DEFAULT '{}',
                crop_rect_json TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def save_project(self, project: ProjectRecord) -> int:
        """保存项目"""
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if project.id is None:
            project.created_at = now
            project.updated_at = now
            cursor.execute("""
                INSERT INTO projects (
                    name, original_image_path, grid_width, grid_height,
                    palette_brand, max_colors, dithering,
                    pdf_path, preview_path, usage_stats_json,
                    crop_rect_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project.name, project.original_image_path,
                project.grid_width, project.grid_height,
                project.palette_brand, project.max_colors,
                int(project.dithering),
                project.pdf_path, project.preview_path,
                project.usage_stats_json, project.crop_rect_json,
                project.created_at, project.updated_at
            ))
            project.id = cursor.lastrowid
        else:
            project.updated_at = now
            cursor.execute("""
                UPDATE projects SET
                    name=?, original_image_path=?, grid_width=?, grid_height=?,
                    palette_brand=?, max_colors=?, dithering=?,
                    pdf_path=?, preview_path=?, usage_stats_json=?,
                    crop_rect_json=?, updated_at=?
                WHERE id=?
            """, (
                project.name, project.original_image_path,
                project.grid_width, project.grid_height,
                project.palette_brand, project.max_colors,
                int(project.dithering),
                project.pdf_path, project.preview_path,
                project.usage_stats_json, project.crop_rect_json,
                project.updated_at, project.id
            ))

        conn.commit()
        conn.close()
        return project.id

    def get_all_projects(self) -> List[ProjectRecord]:
        """获取所有历史项目"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC"
        )
        rows = cursor.fetchall()
        conn.close()

        projects = []
        for row in rows:
            projects.append(ProjectRecord(
                id=row[0], name=row[1], original_image_path=row[2],
                grid_width=row[3], grid_height=row[4],
                palette_brand=row[5], max_colors=row[6],
                dithering=bool(row[7]),
                pdf_path=row[8], preview_path=row[9],
                usage_stats_json=row[10], crop_rect_json=row[11],
                created_at=row[12], updated_at=row[13]
            ))
        return projects

    def get_project(self, project_id: int) -> Optional[ProjectRecord]:
        """获取单个项目"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id=?", (project_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return ProjectRecord(
                id=row[0], name=row[1], original_image_path=row[2],
                grid_width=row[3], grid_height=row[4],
                palette_brand=row[5], max_colors=row[6],
                dithering=bool(row[7]),
                pdf_path=row[8], preview_path=row[9],
                usage_stats_json=row[10], crop_rect_json=row[11],
                created_at=row[12], updated_at=row[13]
            )
        return None

    def delete_project(self, project_id: int):
        """删除项目"""
        project = self.get_project(project_id)
        if project:
            # 删除关联文件
            for path in [project.original_image_path, project.pdf_path, project.preview_path]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM projects WHERE id=?", (project_id,))
        conn.commit()
        conn.close()

    def copy_image_to_storage(self, source_path: str, project_name: str) -> str:
        """复制原图到数据目录"""
        ext = os.path.splitext(source_path)[1]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_filename = f"{project_name}_{timestamp}{ext}"
        dest_path = os.path.join(self.images_dir, dest_filename)
        shutil.copy2(source_path, dest_path)
        return dest_path

    def get_output_path(self, project_name: str, ext: str = ".pdf") -> str:
        """生成输出文件路径"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{project_name}_{timestamp}{ext}"
        return os.path.join(self.outputs_dir, filename)