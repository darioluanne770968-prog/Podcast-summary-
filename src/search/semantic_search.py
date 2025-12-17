"""
语义搜索模块

基于嵌入向量的语义搜索
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import json
import numpy as np

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """搜索结果"""
    id: str
    title: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    highlights: List[str] = field(default_factory=list)


class EmbeddingProvider:
    """嵌入向量提供者"""

    def __init__(self, provider: str = "openai", model: str = None):
        self.provider = provider
        self.model = model or self._default_model()
        self._client = None

    def _default_model(self) -> str:
        if self.provider == "openai":
            return "text-embedding-3-small"
        elif self.provider == "sentence-transformers":
            return "all-MiniLM-L6-v2"
        elif self.provider == "cohere":
            return "embed-multilingual-v3.0"
        return "text-embedding-3-small"

    def _get_openai_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI()
            except ImportError:
                raise ImportError("请安装 openai: pip install openai")
        return self._client

    def embed(self, texts: List[str]) -> np.ndarray:
        """生成嵌入向量"""
        if self.provider == "openai":
            return self._embed_openai(texts)
        elif self.provider == "sentence-transformers":
            return self._embed_sentence_transformers(texts)
        elif self.provider == "cohere":
            return self._embed_cohere(texts)
        else:
            raise ValueError(f"不支持的嵌入提供者: {self.provider}")

    def _embed_openai(self, texts: List[str]) -> np.ndarray:
        """使用 OpenAI 生成嵌入"""
        client = self._get_openai_client()
        response = client.embeddings.create(
            model=self.model,
            input=texts,
        )
        embeddings = [item.embedding for item in response.data]
        return np.array(embeddings)

    def _embed_sentence_transformers(self, texts: List[str]) -> np.ndarray:
        """使用 sentence-transformers 生成嵌入"""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError("请安装 sentence-transformers: pip install sentence-transformers")

        if self._client is None:
            self._client = SentenceTransformer(self.model)

        embeddings = self._client.encode(texts, convert_to_numpy=True)
        return embeddings

    def _embed_cohere(self, texts: List[str]) -> np.ndarray:
        """使用 Cohere 生成嵌入"""
        try:
            import cohere
        except ImportError:
            raise ImportError("请安装 cohere: pip install cohere")

        if self._client is None:
            self._client = cohere.Client()

        response = self._client.embed(
            texts=texts,
            model=self.model,
            input_type="search_document",
        )
        return np.array(response.embeddings)

    @property
    def dimension(self) -> int:
        """获取嵌入维度"""
        dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "embed-multilingual-v3.0": 1024,
        }
        return dimensions.get(self.model, 1536)


class SemanticSearch:
    """语义搜索引擎"""

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        embedding_provider: str = "openai",
        embedding_model: str = None,
    ):
        self.storage_dir = storage_dir or Path.home() / ".podcast_summary" / "search"
        ensure_dir(self.storage_dir)

        self.embedder = EmbeddingProvider(embedding_provider, embedding_model)
        self._documents: Dict[str, Dict] = {}
        self._embeddings: Optional[np.ndarray] = None
        self._doc_ids: List[str] = []
        self._load_index()

    def _load_index(self):
        """加载索引"""
        docs_file = self.storage_dir / "documents.json"
        embeddings_file = self.storage_dir / "embeddings.npy"

        if docs_file.exists():
            try:
                with open(docs_file, "r", encoding="utf-8") as f:
                    self._documents = json.load(f)
                    self._doc_ids = list(self._documents.keys())
            except Exception as e:
                logger.error(f"加载文档索引失败: {e}")

        if embeddings_file.exists():
            try:
                self._embeddings = np.load(embeddings_file)
            except Exception as e:
                logger.error(f"加载嵌入向量失败: {e}")

    def _save_index(self):
        """保存索引"""
        docs_file = self.storage_dir / "documents.json"
        embeddings_file = self.storage_dir / "embeddings.npy"

        try:
            with open(docs_file, "w", encoding="utf-8") as f:
                json.dump(self._documents, f, ensure_ascii=False, indent=2)

            if self._embeddings is not None:
                np.save(embeddings_file, self._embeddings)
        except Exception as e:
            logger.error(f"保存索引失败: {e}")

    def add_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        metadata: Optional[Dict] = None,
    ):
        """添加文档"""
        self._documents[doc_id] = {
            "title": title,
            "content": content,
            "metadata": metadata or {},
        }
        self._doc_ids = list(self._documents.keys())

        # 重新构建嵌入
        self._rebuild_embeddings()
        logger.info(f"添加文档: {title}")

    def add_documents(
        self,
        documents: List[Dict[str, Any]],
    ):
        """批量添加文档"""
        for doc in documents:
            self._documents[doc["id"]] = {
                "title": doc["title"],
                "content": doc["content"],
                "metadata": doc.get("metadata", {}),
            }

        self._doc_ids = list(self._documents.keys())
        self._rebuild_embeddings()
        logger.info(f"批量添加 {len(documents)} 个文档")

    def _rebuild_embeddings(self):
        """重建嵌入向量"""
        if not self._documents:
            self._embeddings = None
            return

        texts = [
            f"{doc['title']}\n{doc['content']}"
            for doc in self._documents.values()
        ]

        try:
            self._embeddings = self.embedder.embed(texts)
            self._save_index()
        except Exception as e:
            logger.error(f"生成嵌入向量失败: {e}")

    def remove_document(self, doc_id: str) -> bool:
        """移除文档"""
        if doc_id in self._documents:
            del self._documents[doc_id]
            self._doc_ids = list(self._documents.keys())
            self._rebuild_embeddings()
            return True
        return False

    def search(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.0,
        filters: Optional[Dict] = None,
    ) -> List[SearchResult]:
        """语义搜索"""
        if self._embeddings is None or len(self._embeddings) == 0:
            return []

        # 生成查询向量
        try:
            query_embedding = self.embedder.embed([query])[0]
        except Exception as e:
            logger.error(f"生成查询向量失败: {e}")
            return []

        # 计算余弦相似度
        scores = self._cosine_similarity(query_embedding, self._embeddings)

        # 获取排序索引
        sorted_indices = np.argsort(scores)[::-1]

        results = []
        for idx in sorted_indices:
            if len(results) >= top_k:
                break

            score = float(scores[idx])
            if score < threshold:
                continue

            doc_id = self._doc_ids[idx]
            doc = self._documents[doc_id]

            # 应用过滤器
            if filters and not self._match_filters(doc, filters):
                continue

            # 生成高亮
            highlights = self._generate_highlights(doc["content"], query)

            results.append(SearchResult(
                id=doc_id,
                title=doc["title"],
                content=doc["content"][:500],
                score=score,
                metadata=doc["metadata"],
                highlights=highlights,
            ))

        return results

    def _cosine_similarity(
        self,
        query: np.ndarray,
        documents: np.ndarray,
    ) -> np.ndarray:
        """计算余弦相似度"""
        query_norm = query / np.linalg.norm(query)
        doc_norms = documents / np.linalg.norm(documents, axis=1, keepdims=True)
        return np.dot(doc_norms, query_norm)

    def _match_filters(self, doc: Dict, filters: Dict) -> bool:
        """匹配过滤器"""
        metadata = doc.get("metadata", {})
        for key, value in filters.items():
            if key not in metadata:
                return False
            if isinstance(value, list):
                if metadata[key] not in value:
                    return False
            elif metadata[key] != value:
                return False
        return True

    def _generate_highlights(
        self,
        content: str,
        query: str,
        max_highlights: int = 3,
        context_size: int = 100,
    ) -> List[str]:
        """生成搜索高亮"""
        query_terms = query.lower().split()
        content_lower = content.lower()
        highlights = []

        for term in query_terms:
            idx = content_lower.find(term)
            while idx != -1 and len(highlights) < max_highlights:
                start = max(0, idx - context_size)
                end = min(len(content), idx + len(term) + context_size)

                highlight = content[start:end]
                if start > 0:
                    highlight = "..." + highlight
                if end < len(content):
                    highlight = highlight + "..."

                if highlight not in highlights:
                    highlights.append(highlight)

                idx = content_lower.find(term, idx + 1)

        return highlights

    def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        semantic_weight: float = 0.7,
    ) -> List[SearchResult]:
        """混合搜索（语义 + 关键词）"""
        # 语义搜索
        semantic_results = self.search(query, top_k=top_k * 2)

        # 关键词搜索
        keyword_results = self._keyword_search(query, top_k=top_k * 2)

        # 合并结果
        combined_scores: Dict[str, float] = {}
        all_results: Dict[str, SearchResult] = {}

        for result in semantic_results:
            combined_scores[result.id] = result.score * semantic_weight
            all_results[result.id] = result

        keyword_weight = 1 - semantic_weight
        for result in keyword_results:
            if result.id in combined_scores:
                combined_scores[result.id] += result.score * keyword_weight
            else:
                combined_scores[result.id] = result.score * keyword_weight
                all_results[result.id] = result

        # 按综合得分排序
        sorted_ids = sorted(combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True)

        results = []
        for doc_id in sorted_ids[:top_k]:
            result = all_results[doc_id]
            result.score = combined_scores[doc_id]
            results.append(result)

        return results

    def _keyword_search(
        self,
        query: str,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """关键词搜索"""
        query_terms = query.lower().split()
        results = []

        for doc_id, doc in self._documents.items():
            content_lower = doc["content"].lower()
            title_lower = doc["title"].lower()

            # 计算 TF-IDF 风格的得分
            score = 0.0
            for term in query_terms:
                # 标题匹配权重更高
                title_count = title_lower.count(term)
                content_count = content_lower.count(term)
                score += title_count * 3 + content_count

            if score > 0:
                # 归一化
                score = score / (len(doc["content"]) + 1) * 1000

                results.append(SearchResult(
                    id=doc_id,
                    title=doc["title"],
                    content=doc["content"][:500],
                    score=min(score, 1.0),
                    metadata=doc["metadata"],
                    highlights=self._generate_highlights(doc["content"], query),
                ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def find_similar(
        self,
        doc_id: str,
        top_k: int = 5,
    ) -> List[SearchResult]:
        """查找相似文档"""
        if doc_id not in self._documents:
            return []

        if self._embeddings is None:
            return []

        idx = self._doc_ids.index(doc_id)
        doc_embedding = self._embeddings[idx]

        scores = self._cosine_similarity(doc_embedding, self._embeddings)

        results = []
        sorted_indices = np.argsort(scores)[::-1]

        for i in sorted_indices:
            if self._doc_ids[i] == doc_id:
                continue
            if len(results) >= top_k:
                break

            similar_id = self._doc_ids[i]
            doc = self._documents[similar_id]

            results.append(SearchResult(
                id=similar_id,
                title=doc["title"],
                content=doc["content"][:500],
                score=float(scores[i]),
                metadata=doc["metadata"],
            ))

        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计"""
        return {
            "total_documents": len(self._documents),
            "embedding_dimension": self.embedder.dimension,
            "embedding_provider": self.embedder.provider,
            "embedding_model": self.embedder.model,
            "index_size_bytes": self._embeddings.nbytes if self._embeddings is not None else 0,
        }
