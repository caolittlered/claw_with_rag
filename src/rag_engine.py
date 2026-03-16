"""
RAG 引擎核心模块
负责文档索引、检索和生成
"""

import os
from typing import List, Optional
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain.schema import Document

import chromadb
from chromadb.config import Settings
import yaml


class RAGEngine:
    """RAG 检索引擎"""
    
    def __init__(self, config_path: str = "./config/config.yaml"):
        """初始化 RAG 引擎"""
        self.config = self._load_config(config_path)
        
        # 配置 Hugging Face 镜像（中国大陆用户）
        hf_endpoint = self.config.get('rag', {}).get('hf_endpoint')
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
        self.reranker = CrossEncoder(
            reranker_config['model'],
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
        """索引文档"""
        text_splitter = self._get_text_splitter()
        split_docs = text_splitter.split_documents(documents)
        
        print(f"正在索引 {len(split_docs)} 个文档片段...")
        self.vectorstore.add_documents(split_docs)
        print(f"索引完成！")
    
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