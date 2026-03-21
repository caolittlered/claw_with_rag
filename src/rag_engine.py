"""
RAG 引擎核心模块
负责文档索引、检索和生成
"""

import os
import hashlib
from typing import List, Optional
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

import chromadb
from chromadb.config import Settings
import yaml


# ModelScope 模型 ID 映射
MODELSCOPE_MODELS = {
    "BAAI/bge-large-zh-v1.5": "Xorbits/bge-large-zh-v1.5",
    "BAAI/bge-reranker-large": "Xorbits/bge-reranker-large",
}


def find_local_model(model_id: str) -> Optional[str]:
    """查找本地缓存的模型路径
    
    优先查找 ModelScope 缓存，其次 HuggingFace 缓存
    """
    # ModelScope 缓存目录 (新版结构: hub/models/org/model-name)
    modelscope_cache = Path.home() / ".cache" / "modelscope" / "hub" / "models"
    
    # 检查 ModelScope 缓存
    ms_model_id = MODELSCOPE_MODELS.get(model_id, model_id)
    org, model_name = ms_model_id.split("/")
    
    # 尝试多种可能的目录名格式
    possible_names = [
        model_name,                    # bge-large-zh-v1.5
        model_name.replace(".", "___"), # bge-large-zh-v1___5 (modelscope 转义格式)
        model_name.replace("-", "_"),   # bge_large_zh_v1_5
    ]
    
    for name in possible_names:
        ms_cache_path = modelscope_cache / org / name
        if ms_cache_path.exists():
            print(f"[RAG] 使用 ModelScope 缓存: {ms_cache_path}")
            return str(ms_cache_path)
    
    # 旧版 ModelScope 缓存结构 (hub/org__model)
    modelscope_cache_old = Path.home() / ".cache" / "modelscope" / "hub"
    ms_cache_path_old = modelscope_cache_old / ms_model_id.replace("/", "__")
    if ms_cache_path_old.exists():
        print(f"[RAG] 使用 ModelScope 缓存 (旧版): {ms_cache_path_old}")
        return str(ms_cache_path_old)
    
    # HuggingFace 缓存目录
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    hf_cache_path = hf_cache / f"models--{model_id.replace('/', '--')}"
    if hf_cache_path.exists():
        print(f"[RAG] 使用 HuggingFace 缓存: {hf_cache_path}")
        return model_id  # 返回原始 ID，transformers 会自动找到缓存
    
    return None


class RAGEngine:
    """RAG 检索引擎"""
    
    def __init__(self, config_path: str = "./config/config.yaml"):
        """初始化 RAG 引擎"""
        self.config = self._load_config(config_path)
        
        # 配置 Hugging Face 镜像（中国大陆用户）
        rag_config = self.config.get('rag', {})
        hf_endpoint = rag_config.get('hf_endpoint')
        if hf_endpoint:
            os.environ['HF_ENDPOINT'] = hf_endpoint
            print(f"[RAG] 使用镜像: {hf_endpoint}")
        
        self.embeddings = self._init_embeddings()
        self.reranker = None  # 延迟加载
        self.vectorstore = None
        self._init_vectorstore()
    
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _init_embeddings(self) -> HuggingFaceEmbeddings:
        """初始化 Embedding 模型"""
        embedding_config = self.config['rag']['embedding']
        model_name = embedding_config['model']
        device = embedding_config.get('device', 'cpu')
        
        # 尝试查找本地缓存
        local_path = find_local_model(model_name)
        if local_path:
            model_name = local_path
        else:
            # 没找到本地缓存，设置镜像重试
            if 'HF_ENDPOINT' not in os.environ:
                print("[RAG] 未找到本地缓存，尝试使用镜像...")
                os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
        
        print(f"[RAG] 加载 Embedding 模型: {model_name}")
        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': device},
            encode_kwargs={'normalize_embeddings': True}
        )
    
    def _init_reranker(self):
        """初始化 Reranker 模型（延迟加载）"""
        if self.reranker is not None:
            return
        
        from sentence_transformers import CrossEncoder
        reranker_config = self.config['rag']['reranker']
        model_name = reranker_config['model']
        
        # 尝试查找本地缓存
        local_path = find_local_model(model_name)
        if local_path:
            model_name = local_path
        elif 'HF_ENDPOINT' not in os.environ:
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
        
        print(f"[RAG] 加载 Reranker 模型: {model_name}")
        self.reranker = CrossEncoder(
            model_name,
            max_length=512,
            device=reranker_config.get('device', 'cpu')
        )
    
    def _init_vectorstore(self):
        """初始化向量数据库"""
        db_config = self.config['rag']['vector_db']
        persist_dir = db_config.get('persist_directory', './data/chroma')
        
        # 确保目录存在
        os.makedirs(persist_dir, exist_ok=True)
        
        # 创建 Chroma 客户端
        client = chromadb.PersistentClient(path=persist_dir)
        
        # 初始化向量存储
        self.vectorstore = Chroma(
            client=client,
            embedding_function=self.embeddings,
            collection_name="knowledge_base"
        )
    
    def _get_text_splitter(self) -> RecursiveCharacterTextSplitter:
        """获取文本切分器"""
        chunking_config = self.config['rag']['chunking']
        return RecursiveCharacterTextSplitter(
            chunk_size=chunking_config['chunk_size'],
            chunk_overlap=chunking_config['chunk_overlap'],
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
        )
    
    def index_documents(self, documents: List[Document]):
        """索引文档（使用内容 hash 去重）"""
        text_splitter = self._get_text_splitter()
        split_docs = text_splitter.split_documents(documents)
        
        # 用内容 hash 作为 ID，重复内容不会重复存储
        ids = []
        for doc in split_docs:
            # 使用文件路径 + 内容生成 hash，保证唯一性
            source = doc.metadata.get('source', '')
            content_hash = hashlib.md5(f"{source}:{doc.page_content}".encode()).hexdigest()
            ids.append(content_hash)
        
        print(f"正在索引 {len(split_docs)} 个文档片段...")
        self.vectorstore.add_documents(split_docs, ids=ids)
        print(f"索引完成！（重复内容已自动跳过）")
    
    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Document]:
        """检索相关文档"""
        retrieval_config = self.config['rag']['retrieval']
        top_k = top_k or retrieval_config['top_k']
        
        # 初始检索
        docs = self.vectorstore.similarity_search(query, k=top_k)
        
        return docs
    
    def retrieve_with_rerank(self, query: str, top_k: Optional[int] = None) -> List[dict]:
        """检索并重排序"""
        retrieval_config = self.config['rag']['retrieval']
        top_k = top_k or retrieval_config['top_k']
        rerank_top_k = retrieval_config['rerank_top_k']
        
        # 初始检索
        docs = self.retrieve(query, top_k)
        
        if not docs:
            return []
        
        # 加载 reranker
        self._init_reranker()
        
        # 重排序
        pairs = [[query, doc.page_content] for doc in docs]
        scores = self.reranker.predict(pairs)
        
        # 组合并排序
        scored_docs = list(zip(docs, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # 过滤低分结果
        threshold = retrieval_config['similarity_threshold']
        results = []
        for doc, score in scored_docs[:rerank_top_k]:
            if score >= threshold:
                results.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'score': float(score)
                })
        
        return results
    
    def build_context(self, query: str) -> str:
        """构建上下文"""
        results = self.retrieve_with_rerank(query)
        
        if not results:
            return ""
        
        context_parts = ["以下是相关的内部知识：\n"]
        for i, result in enumerate(results, 1):
            context_parts.append(f"[文档{i}] (相关度: {result['score']:.2f})")
            context_parts.append(result['content'])
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def is_internal_query(self, query: str) -> bool:
        """判断是否为内部问题"""
        keywords = self.config.get('internal_keywords', [])
        query_lower = query.lower()
        return any(kw in query_lower for kw in keywords)