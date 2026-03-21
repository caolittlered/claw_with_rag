"""
RAG API 服务
FastAPI 服务，模型常驻内存
"""

import os
import time
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yaml

from rag_engine import RAGEngine
from document_processor import process_directory


# 配置
CONFIG_PATH = os.getenv("RAG_CONFIG", "./config/config.yaml")


# 全局 RAG 引擎（启动时加载）
rag_engine: Optional[RAGEngine] = None
startup_time: float = 0  # 启动时间戳
load_time: float = 0     # 加载耗时
request_count: int = 0


# 请求/响应模型
class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    content: str
    metadata: dict
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


class IndexRequest(BaseModel):
    docs_dir: str


class IndexResponse(BaseModel):
    message: str
    doc_count: int


class HealthResponse(BaseModel):
    status: str
    embedding_model: str
    reranker_model: str


# FastAPI 应用
app = FastAPI(
    title="RAG API",
    description="企业知识库 RAG 服务",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """启动时加载模型"""
    global rag_engine, startup_time, load_time
    print("[API] ========================================")
    print("[API] 正在加载 RAG 引擎...")
    print("[API] ========================================")
    start = time.time()
    rag_engine = RAGEngine(CONFIG_PATH)
    load_time = time.time() - start
    startup_time = time.time()
    print("[API] ========================================")
    print(f"[API] RAG 引擎加载完成！耗时: {load_time:.2f}s")
    print("[API] 模型已常驻内存，后续请求无需重新加载")
    print("[API] ========================================")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    config = yaml.safe_load(open(CONFIG_PATH, 'r', encoding='utf-8'))
    return HealthResponse(
        status="healthy",
        embedding_model=config['rag']['embedding']['model'],
        reranker_model=config['rag']['reranker']['model']
    )


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    搜索知识库
    
    - **query**: 搜索内容
    - **top_k**: 返回结果数量
    """
    global request_count
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG 引擎未初始化")
    
    request_count += 1
    req_id = request_count
    start = time.time()
    print(f"[API] 请求 #{req_id} 搜索: {request.query[:50]}...")
    
    results = rag_engine.retrieve_with_rerank(request.query, request.top_k)
    
    elapsed = time.time() - start
    print(f"[API] 请求 #{req_id} 完成，耗时: {elapsed:.3f}s，返回 {len(results)} 条结果")
    
    return SearchResponse(
        query=request.query,
        results=[SearchResult(**r) for r in results]
    )


@app.post("/index", response_model=IndexResponse)
async def index_documents(request: IndexRequest, background_tasks: BackgroundTasks):
    """
    索引文档目录（后台执行）
    
    - **docs_dir**: 文档目录路径
    """
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG 引擎未初始化")
    
    if not Path(request.docs_dir).exists():
        raise HTTPException(status_code=404, detail=f"目录不存在: {request.docs_dir}")
    
    docs = process_directory(request.docs_dir)
    if not docs:
        raise HTTPException(status_code=400, detail="未找到可索引的文档")
    
    # 后台执行索引
    background_tasks.add_task(rag_engine.index_documents, docs)
    
    return IndexResponse(
        message=f"正在索引 {len(docs)} 个文档",
        doc_count=len(docs)
    )


@app.post("/index-sync", response_model=IndexResponse)
async def index_documents_sync(request: IndexRequest):
    """
    索引文档目录（同步执行）
    
    - **docs_dir**: 文档目录路径
    """
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG 引擎未初始化")
    
    if not Path(request.docs_dir).exists():
        raise HTTPException(status_code=404, detail=f"目录不存在: {request.docs_dir}")
    
    docs = process_directory(request.docs_dir)
    if not docs:
        raise HTTPException(status_code=400, detail="未找到可索引的文档")
    
    rag_engine.index_documents(docs)
    
    return IndexResponse(
        message="索引完成",
        doc_count=len(docs)
    )


@app.get("/context")
async def build_context(query: str):
    """
    构建 RAG 上下文（用于 LLM 输入）
    
    - **query**: 查询内容
    """
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG 引擎未初始化")
    
    context = rag_engine.build_context(query)
    return {"query": query, "context": context}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)