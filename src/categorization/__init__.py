"""
文档分类模块 — 层次摘要 + 聚类 + 分类存储

提供:
  - CategoryStore: 类别持久化（JSON 文件）
  - Summarizer: 层次摘要生成（chunk → parent → document）
  - Clusterer: 文档聚类 + 单文档分类
  - IncrementalCategorizer: 增量分类编排器（上传后自动分类）
"""
from src.categorization.category_store import CategoryStore, get_category_store
from src.categorization.summarizer import Summarizer
from src.categorization.clusterer import Clusterer
from src.categorization.incremental import IncrementalCategorizer
