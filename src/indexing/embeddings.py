"""
Embedding 模型封装 — 支持本地 (sentence-transformers)、OpenAI、Voyage
"""
import os
from typing import List

from openai import OpenAI

from config import (
    EMBEDDING_PROVIDER,
    EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
    HF_ENDPOINT,
    OPENAI_API_KEY,
    VOYAGE_API_KEY,
)


class EmbeddingModel:
    """Embedding 模型统一接口"""

    def __init__(
        self,
        provider: str = EMBEDDING_PROVIDER,
        model: str = EMBEDDING_MODEL,
    ):
        self.provider = provider
        self.model = model

        if provider == "local":
            # 使用 HF 镜像（国内用户可通过 HF_ENDPOINT 环境变量设置）
            if HF_ENDPOINT and HF_ENDPOINT != "https://huggingface.co":
                os.environ.setdefault("HF_ENDPOINT", HF_ENDPOINT)
                print(f"  使用 HuggingFace 镜像: {HF_ENDPOINT}")

            # 优先本地缓存，跳过网络检查（模型已下载则秒开）
            os.environ.setdefault("HF_HUB_OFFLINE", "1")

            from sentence_transformers import SentenceTransformer
            local_model = LOCAL_EMBEDDING_MODEL
            print(f"  加载本地 Embedding 模型: {local_model} ...")
            try:
                self._local_model = SentenceTransformer(local_model)
            except Exception as e:
                raise RuntimeError(
                    f"无法加载本地 Embedding 模型 '{local_model}'。\n"
                    f"原因: {e}\n"
                    f"解决方法:\n"
                    f"  1. 使用镜像: 在 .env 中设置 HF_ENDPOINT=https://hf-mirror.com\n"
                    f"  2. 切换到 OpenAI: 在 .env 中设置 EMBEDDING_PROVIDER=openai + OPENAI_API_KEY\n"
                    f"  3. 手动下载: 从 https://hf-mirror.com/{local_model} 下载到本地，\n"
                    f"     然后设置 LOCAL_EMBEDDING_MODEL=/path/to/model"
                )
            self.model = local_model  # 让 self.model 反映真实模型名
        elif provider == "openai":
            self._client = OpenAI(api_key=OPENAI_API_KEY)
        elif provider == "voyage":
            self._client = OpenAI(
                api_key=VOYAGE_API_KEY,
                base_url="https://api.voyageai.com/v1/",
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """对文本列表生成 embedding"""
        if not texts:
            return []

        if self.provider == "local":
            # sentence-transformers: encode 返回 numpy array
            embeddings = self._local_model.encode(
                texts,
                normalize_embeddings=True,  # BGE 模型需要 L2 归一化
                show_progress_bar=True,
            )
            return embeddings.tolist()

        # OpenAI / Voyage: API 调用
        cleaned = [t[:8000] for t in texts]
        response = self._client.embeddings.create(
            model=self.model,
            input=cleaned,
        )
        return [d.embedding for d in response.data]

    def embed_single(self, text: str) -> List[float]:
        """对单条文本生成 embedding"""
        return self.embed([text])[0]

    @property
    def model_name(self) -> str:
        """返回实际使用的模型名称"""
        return self.model



# 全局单例
_embedding_model: EmbeddingModel | None = None


def get_embedding_model() -> EmbeddingModel:
    """获取全局 embedding 模型实例"""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel()
    return _embedding_model
