"""
类别持久化存储 — JSON 文件读写

数据结构 (data/categories.json):
{
  "categories": [{
    "id": "cat-uuid", "name": "类别名", "description": "...",
    "doc_ids": ["doc1", "doc2"], "document_count": 5
  }],
  "doc_to_category": {"doc1": "cat-uuid", ...},
  "last_generated": "2026-06-27T10:00:00" | null
}
"""
import json
import uuid
from pathlib import Path
from typing import List, Dict, Optional

from config import DATA_DIR


class CategoryStore:
    """类别 JSON 持久化存储"""

    def __init__(self, file_path: Path = None):
        self._path = Path(file_path or DATA_DIR / "categories.json")
        self._data = self._load()

    def _load(self) -> dict:
        """从 JSON 文件加载，文件不存在返回空结构"""
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass
        return {"categories": [], "doc_to_category": {}, "last_generated": None}

    def _save(self) -> None:
        """保存到 JSON 文件"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 读取 ──────────────────────────────────────────────

    def get_all(self) -> List[dict]:
        """获取所有类别"""
        return self._data.get("categories", [])

    def get_doc_ids(self, category_ids: List[str]) -> List[str]:
        """根据类别 ID 列表获取关联的所有 doc_id"""
        if not category_ids:
            return []
        doc_ids = set()
        for cat in self._data.get("categories", []):
            if cat["id"] in category_ids:
                doc_ids.update(cat.get("doc_ids", []))
        return list(doc_ids)

    def get_category_for_doc(self, doc_id: str) -> Optional[str]:
        """查询文档所属类别 ID"""
        return self._data.get("doc_to_category", {}).get(doc_id)

    def get_last_generated(self) -> Optional[str]:
        """获取上次生成时间"""
        return self._data.get("last_generated")

    # ── 写入 ──────────────────────────────────────────────

    def save_categories(self, categories: List[dict]) -> None:
        """
        保存类别数据

        Args:
            categories: [{"name": "...", "description": "...", "doc_ids": [...]}, ...]
        """
        import datetime
        cat_list = []
        doc_to_cat = {}
        for c in categories:
            cat_id = str(uuid.uuid4())[:8]
            cat_entry = {
                "id": cat_id,
                "name": c.get("name", ""),
                "description": c.get("description", ""),
                "doc_ids": c.get("doc_ids", []),
                "document_count": len(c.get("doc_ids", [])),
            }
            cat_list.append(cat_entry)
            for doc_id in c.get("doc_ids", []):
                doc_to_cat[doc_id] = cat_id

        self._data = {
            "categories": cat_list,
            "doc_to_category": doc_to_cat,
            "last_generated": datetime.datetime.now().isoformat(),
        }
        self._save()

    def clear(self) -> None:
        """清空所有类别"""
        self._data = {"categories": [], "doc_to_category": {}, "last_generated": None}
        self._save()

    # ── 增量写入（供自动分类使用）──────────────────────────

    def create_category(self, name: str, description: str = "", doc_ids: List[str] = None) -> str:
        """
        创建新类别，返回 category_id。
        不影响已有类别。
        """
        cat_id = str(uuid.uuid4())[:8]
        doc_ids = doc_ids or []
        self._data["categories"].append({
            "id": cat_id,
            "name": name,
            "description": description,
            "doc_ids": list(doc_ids),
            "document_count": len(doc_ids),
        })
        for did in doc_ids:
            self._data["doc_to_category"][did] = cat_id
        self._touch_timestamp()
        return cat_id

    def add_doc_to_category(self, doc_id: str, category_id: str) -> bool:
        """
        将文档加入已有类别。返回 True 表示成功，False 表示类别不存在。

        如果文档已在其他类别中，先移除。
        """
        # 先移除旧归属
        old_cat = self._data["doc_to_category"].get(doc_id)
        if old_cat:
            self._remove_doc_from_category(doc_id, old_cat)

        # 找到目标类别并添加
        for cat in self._data["categories"]:
            if cat["id"] == category_id:
                if doc_id not in cat["doc_ids"]:
                    cat["doc_ids"].append(doc_id)
                    cat["document_count"] = len(cat["doc_ids"])
                self._data["doc_to_category"][doc_id] = category_id
                self._touch_timestamp()
                return True
        return False

    def _remove_doc_from_category(self, doc_id: str, category_id: str) -> None:
        """内部：从类别中移除文档（不更新 last_generated）"""
        for cat in self._data["categories"]:
            if cat["id"] == category_id:
                if doc_id in cat["doc_ids"]:
                    cat["doc_ids"].remove(doc_id)
                    cat["document_count"] = len(cat["doc_ids"])
                # 如果类别为空则删除
                if not cat["doc_ids"]:
                    self._data["categories"].remove(cat)
                break
        self._data["doc_to_category"].pop(doc_id, None)

    def _touch_timestamp(self) -> None:
        """更新 last_generated 时间戳"""
        import datetime
        self._data["last_generated"] = datetime.datetime.now().isoformat()
        self._save()

    @property
    def is_empty(self) -> bool:
        return len(self._data.get("categories", [])) == 0


# 全局单例
_store: Optional[CategoryStore] = None


def get_category_store() -> CategoryStore:
    global _store
    if _store is None:
        _store = CategoryStore()
    return _store
