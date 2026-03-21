"""
OpenClaw Internal Knowledge Search Skill
通过 RAG API 服务获取内部知识
"""

import os
import requests
from typing import Optional


# API 配置
RAG_API_URL = os.getenv("RAG_API_URL", "http://localhost:8000")
RAG_API_TIMEOUT = int(os.getenv("RAG_API_TIMEOUT", "30"))


def is_internal_query(query: str) -> bool:
    """
    判断是否为内部问题（本地关键词匹配）
    
    Args:
        query: 用户查询
    
    Returns:
        bool: 是否为内部问题
    """
    # 简单的关键词匹配
    internal_keywords = [
        "公司", "内部", "员工", "流程", "制度", 
        "报销", "请假", "年假", "考勤", "工资",
        "福利", "入职", "离职", "合同", "培训",
        "部门", "岗位", "职位", "晋升", "调岗"
    ]
    query_lower = query.lower()
    return any(kw in query_lower for kw in internal_keywords)


def check_api_health() -> bool:
    """
    检查 API 服务是否可用
    
    Returns:
        bool: API 是否可用
    """
    try:
        response = requests.get(
            f"{RAG_API_URL}/health",
            timeout=5
        )
        return response.status_code == 200
    except Exception:
        return False


def search_knowledge(query: str, top_k: int = 5) -> str:
    """
    搜索内部知识库（通过 API）
    
    Args:
        query: 搜索查询
        top_k: 返回结果数量
    
    Returns:
        str: 检索到的上下文
    """
    try:
        response = requests.post(
            f"{RAG_API_URL}/search",
            json={"query": query, "top_k": top_k},
            timeout=RAG_API_TIMEOUT
        )
        
        if response.status_code != 200:
            print(f"[RAG Skill] API error: {response.status_code}")
            return ""
        
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            return ""
        
        # 构建上下文
        context_parts = ["以下是相关的内部知识：\n"]
        for i, r in enumerate(results, 1):
            context_parts.append(f"[文档{i}] (相关度: {r['score']:.2f})")
            context_parts.append(r["content"])
            context_parts.append("")
        
        return "\n".join(context_parts)
        
    except requests.exceptions.ConnectionError:
        print(f"[RAG Skill] 无法连接 RAG API: {RAG_API_URL}")
        print("[RAG Skill] 请确保 API 服务已启动: python src/api.py")
        return ""
    except Exception as e:
        print(f"[RAG Skill] Search error: {e}")
        return ""


def search_with_rerank(query: str, top_k: int = 10) -> list:
    """
    搜索并重排序（通过 API）
    
    Args:
        query: 搜索查询
        top_k: 返回结果数量
    
    Returns:
        list: 检索结果列表
    """
    try:
        response = requests.post(
            f"{RAG_API_URL}/search",
            json={"query": query, "top_k": top_k},
            timeout=RAG_API_TIMEOUT
        )
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        return data.get("results", [])
        
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
        # 检查 API 是否可用
        if not check_api_health():
            result["warning"] = "RAG API 服务未启动，无法检索内部知识"
            result["context"] = ""
            return result
        
        context = search_knowledge(query)
        result["context"] = context
        if context:
            result["message"] = f"[RAG] 已检索内部知识库，找到相关内容"
        else:
            result["message"] = f"[RAG] 未找到相关内容"
    
    return result


if __name__ == "__main__":
    # 测试
    print(f"API URL: {RAG_API_URL}")
    print(f"API Health: {check_api_health()}")
    print()
    
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
            if result.get('warning'):
                print(f"警告: {result['warning']}")
            elif result.get('context'):
                print(f"上下文: {result['context'][:200]}...")
            else:
                print("未找到相关内容")