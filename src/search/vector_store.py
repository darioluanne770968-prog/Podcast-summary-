"""
向量数据库模块

支持多种向量存储后端
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import json
import numpy as np

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


@dataclass
class VectorDocument:
    """向量文档"""
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class VectorStoreBackend(ABC):
    """向量存储后端抽象类"""

    @abstractmethod
    def add(self, documents: List[VectorDocument]):
        pass

    @abstractmethod
    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[Tuple[VectorDocument, float]]:
        pass

    @abstractmethod
    def delete(self, doc_ids: List[str]):
        pass

    @abstractmethod
    def clear(self):
        pass


class LocalVectorStore(VectorStoreBackend):
    """本地向量存储（基于 NumPy）"""

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        ensure_dir(storage_path.parent)
        self._documents: Dict[str, VectorDocument] = {}
        self._embeddings: Optional[np.ndarray] = None
        self._doc_ids: List[str] = []
        self._load()

    def _load(self):
        """加载数据"""
        docs_file = self.storage_path / "docs.json"
        embeddings_file = self.storage_path / "vectors.npy"

        if docs_file.exists():
            with open(docs_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for doc_data in data:
                    doc = VectorDocument(
                        id=doc_data["id"],
                        content=doc_data["content"],
                        metadata=doc_data.get("metadata", {}),
                    )
                    self._documents[doc.id] = doc
                self._doc_ids = list(self._documents.keys())

        if embeddings_file.exists():
            self._embeddings = np.load(embeddings_file)

    def _save(self):
        """保存数据"""
        ensure_dir(self.storage_path)
        docs_file = self.storage_path / "docs.json"
        embeddings_file = self.storage_path / "vectors.npy"

        data = [
            {
                "id": doc.id,
                "content": doc.content,
                "metadata": doc.metadata,
            }
            for doc in self._documents.values()
        ]

        with open(docs_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if self._embeddings is not None:
            np.save(embeddings_file, self._embeddings)

    def add(self, documents: List[VectorDocument]):
        """添加文档"""
        new_embeddings = []

        for doc in documents:
            if doc.embedding is None:
                logger.warning(f"文档 {doc.id} 缺少嵌入向量")
                continue

            self._documents[doc.id] = doc
            new_embeddings.append(doc.embedding)

        self._doc_ids = list(self._documents.keys())

        if new_embeddings:
            new_arr = np.array(new_embeddings)
            if self._embeddings is None:
                self._embeddings = new_arr
            else:
                self._embeddings = np.vstack([self._embeddings, new_arr])

        self._save()

    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[Tuple[VectorDocument, float]]:
        """搜索"""
        if self._embeddings is None or len(self._embeddings) == 0:
            return []

        query = np.array(query_vector)
        query_norm = query / np.linalg.norm(query)
        doc_norms = self._embeddings / np.linalg.norm(self._embeddings, axis=1, keepdims=True)
        scores = np.dot(doc_norms, query_norm)

        sorted_indices = np.argsort(scores)[::-1]

        results = []
        for idx in sorted_indices:
            if len(results) >= top_k:
                break

            doc_id = self._doc_ids[idx]
            doc = self._documents[doc_id]

            # 应用过滤器
            if filters:
                match = True
                for key, value in filters.items():
                    if doc.metadata.get(key) != value:
                        match = False
                        break
                if not match:
                    continue

            results.append((doc, float(scores[idx])))

        return results

    def delete(self, doc_ids: List[str]):
        """删除文档"""
        indices_to_keep = []
        for i, doc_id in enumerate(self._doc_ids):
            if doc_id not in doc_ids:
                indices_to_keep.append(i)
            elif doc_id in self._documents:
                del self._documents[doc_id]

        self._doc_ids = list(self._documents.keys())

        if self._embeddings is not None and indices_to_keep:
            self._embeddings = self._embeddings[indices_to_keep]

        self._save()

    def clear(self):
        """清空存储"""
        self._documents.clear()
        self._embeddings = None
        self._doc_ids = []
        self._save()


class ChromaDBBackend(VectorStoreBackend):
    """ChromaDB 后端"""

    def __init__(
        self,
        collection_name: str = "podcast_summary",
        persist_directory: Optional[str] = None,
    ):
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            raise ImportError("请安装 chromadb: pip install chromadb")

        settings = Settings(
            anonymized_telemetry=False,
        )

        if persist_directory:
            self._client = chromadb.PersistentClient(
                path=persist_directory,
                settings=settings,
            )
        else:
            self._client = chromadb.Client(settings)

        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, documents: List[VectorDocument]):
        """添加文档"""
        ids = []
        embeddings = []
        contents = []
        metadatas = []

        for doc in documents:
            if doc.embedding is None:
                continue
            ids.append(doc.id)
            embeddings.append(doc.embedding)
            contents.append(doc.content)
            metadatas.append(doc.metadata)

        if ids:
            self._collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=contents,
                metadatas=metadatas,
            )

    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[Tuple[VectorDocument, float]]:
        """搜索"""
        where = filters if filters else None

        results = self._collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where,
        )

        docs = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                doc = VectorDocument(
                    id=doc_id,
                    content=results["documents"][0][i] if results["documents"] else "",
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                )
                # ChromaDB 返回距离，转换为相似度
                distance = results["distances"][0][i] if results["distances"] else 0
                score = 1 - distance  # 余弦距离转相似度
                docs.append((doc, score))

        return docs

    def delete(self, doc_ids: List[str]):
        """删除文档"""
        self._collection.delete(ids=doc_ids)

    def clear(self):
        """清空集合"""
        self._client.delete_collection(self._collection.name)
        self._collection = self._client.create_collection(
            name=self._collection.name,
            metadata={"hnsw:space": "cosine"},
        )


class PineconeBackend(VectorStoreBackend):
    """Pinecone 后端"""

    def __init__(
        self,
        index_name: str,
        api_key: str,
        environment: str,
        dimension: int = 1536,
    ):
        try:
            from pinecone import Pinecone
        except ImportError:
            raise ImportError("请安装 pinecone-client: pip install pinecone-client")

        self._pc = Pinecone(api_key=api_key)

        # 获取或创建索引
        if index_name not in [idx.name for idx in self._pc.list_indexes()]:
            self._pc.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine",
            )

        self._index = self._pc.Index(index_name)

    def add(self, documents: List[VectorDocument]):
        """添加文档"""
        vectors = []
        for doc in documents:
            if doc.embedding is None:
                continue
            vectors.append({
                "id": doc.id,
                "values": doc.embedding,
                "metadata": {
                    "content": doc.content[:1000],  # Pinecone metadata 有大小限制
                    **doc.metadata,
                },
            })

        if vectors:
            self._index.upsert(vectors=vectors)

    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[Tuple[VectorDocument, float]]:
        """搜索"""
        results = self._index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            filter=filters,
        )

        docs = []
        for match in results["matches"]:
            metadata = match.get("metadata", {})
            doc = VectorDocument(
                id=match["id"],
                content=metadata.pop("content", ""),
                metadata=metadata,
            )
            docs.append((doc, match["score"]))

        return docs

    def delete(self, doc_ids: List[str]):
        """删除文档"""
        self._index.delete(ids=doc_ids)

    def clear(self):
        """清空索引"""
        self._index.delete(delete_all=True)


class VectorStore:
    """向量存储统一接口"""

    def __init__(
        self,
        backend: str = "local",
        storage_dir: Optional[Path] = None,
        **kwargs,
    ):
        self.storage_dir = storage_dir or Path.home() / ".podcast_summary" / "vectors"

        if backend == "local":
            self._backend = LocalVectorStore(self.storage_dir)
        elif backend == "chromadb":
            self._backend = ChromaDBBackend(
                persist_directory=str(self.storage_dir),
                **kwargs,
            )
        elif backend == "pinecone":
            self._backend = PineconeBackend(**kwargs)
        else:
            raise ValueError(f"不支持的后端: {backend}")

        self._embedder = None
        logger.info(f"初始化向量存储: {backend}")

    def set_embedder(self, embedder):
        """设置嵌入生成器"""
        self._embedder = embedder

    def add(
        self,
        documents: List[VectorDocument],
        generate_embeddings: bool = True,
    ):
        """添加文档"""
        if generate_embeddings and self._embedder:
            texts = [doc.content for doc in documents]
            embeddings = self._embedder.embed(texts)
            for doc, emb in zip(documents, embeddings):
                doc.embedding = emb.tolist()

        self._backend.add(documents)
        logger.info(f"添加 {len(documents)} 个文档到向量存储")

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[Tuple[VectorDocument, float]]:
        """搜索"""
        if self._embedder is None:
            raise ValueError("未设置嵌入生成器")

        query_vector = self._embedder.embed([query])[0].tolist()
        return self._backend.search(query_vector, top_k, filters)

    def search_by_vector(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[Tuple[VectorDocument, float]]:
        """按向量搜索"""
        return self._backend.search(query_vector, top_k, filters)

    def delete(self, doc_ids: List[str]):
        """删除文档"""
        self._backend.delete(doc_ids)
        logger.info(f"删除 {len(doc_ids)} 个文档")

    def clear(self):
        """清空存储"""
        self._backend.clear()
        logger.info("清空向量存储")
