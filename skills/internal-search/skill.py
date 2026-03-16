"""
OpenClaw Internal Knowledge Search Skill
"""

import sys
import os
from pathlib import Path

# 添加项目路径
SKILL_DIR = Path(__file__).parent
PROJECT_ROOT = SKILL_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_engine import RAGEngine


# 全局 RAG 引擎实例（延迟初始化）
_rag_engine = None


def get_rag_engine():
    """获取或创建 RAG 引擎实例"""
    global _rag_engine
    if _rag_engine is None:
        config_path = PROJECT_ROOT / "config" / "config.yaml"
        _rag_engine = RAGEngine(str(config_path))
    return _rag_engine


def is_internal_query(query: str) -> bool:
    """
    判断是否为内部问题
    
    Args:
        query: 用户查询
    
    Returns:
        bool: 是否为内部问题
    """
    try:
        engine = get_rag_engine()
        return engine.is_internal_query(query)
    except Exception as e:
        print(f"[RAG Skill] Error checking query type: {e}")
        return False


def search_knowledge(query: str, top_k: int = 5) -> str:
    """
    搜索内部知识库
    
    Args:
        query: 搜索查询
        top_k: 返回结果数量
    
    Returns:
        str: 检索到的上下文
    """
    try:
        engine = get_rag_engine()
        context = engine.build_context(query)
        return context
    except Exception as e:
        print(f"[RAG Skill] Search error: {e}")
        return ""


def search_with_rerank(query: str, top_k: int = 10, rerank_top_k: int = 5) -> list:
    """
    搜索并重排序
    
    Args:
        query: 搜索查询
        top_k: 初始召回数量
        rerank_top_k: 重排后返回数量
    
    Returns:
        list: 检索结果列表
    """
    try:
        engine = get_rag_engine()
        results = engine.retrieve_with_rerank(query, top_k)
        return results
    except Exception as e:
        print(f"[RAG Skill] Search with rerank error: {e}")
        return []


# 供 OpenClaw 调用的主函数
def handle_query(query: str) -> dict:
    """
    处理查询请求
    
    Args:
        query: 用户查询
    
    Returns:
        dict: {
            "is_internal": bool,
            "context": str (if internal),
            "results": list (if internal)
        }
    """
    is_internal = is_internal_query(query)
    
    result = {
        "is_internal": is_internal,
        "query": query
    }
    
    if is_internal:
        context = search_knowledge(query)
        result["context"] = context
        result["message"] = f"[RAG] 已检索内部知识库，找到相关内容"
    
    return result


if __name__ == "__main__":
    # 测试
    test_queries = [
        "我们公司的请假流程是什么？",
        "今天天气怎么样？",
        "员工报销需要什么材料？",
        "Python怎么安装？"
    ]
    
    for q in test_queries:
        result = handle_query(q)
        print(f"\n查询: {q}")
        print(f"内部问题: {result['is_internal']}")
        if result['is_internal']:
            print(f"上下文: {result.get('context', '')[:200]}...")