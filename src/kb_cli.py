#!/usr/bin/env python3
"""
知识库管理工具
"""

import argparse
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag_engine import RAGEngine
from src.document_processor import process_directory
import yaml


def cmd_index(args):
    """索引文档命令"""
    print(f"正在处理文档目录: {args.docs_dir}")
    
    # 加载文档
    documents = process_directory(args.docs_dir)
    
    if not documents:
        print("没有找到文档！")
        return
    
    print(f"共加载 {len(documents)} 个文档")
    
    # 初始化 RAG 引擎并索引
    engine = RAGEngine(args.config)
    engine.index_documents(documents)
    
    print("索引完成！")


def cmd_search(args):
    """搜索命令"""
    engine = RAGEngine(args.config)
    
    if args.rerank:
        results = engine.retrieve_with_rerank(args.query, args.top_k)
        print(f"\n搜索结果 (已重排):")
        for i, result in enumerate(results, 1):
            print(f"\n[{i}] 相关度: {result['score']:.3f}")
            print(f"来源: {result['metadata'].get('filename', '未知')}")
            print(f"内容: {result['content'][:200]}...")
    else:
        docs = engine.retrieve(args.query, args.top_k)
        print(f"\n搜索结果:")
        for i, doc in enumerate(docs, 1):
            print(f"\n[{i}]")
            print(f"来源: {doc.metadata.get('filename', '未知')}")
            print(f"内容: {doc.page_content[:200]}...")


def cmd_config(args):
    """显示当前配置"""
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    print("当前配置:")
    print(yaml.dump(config, default_flow_style=False, allow_unicode=True))


def main():
    parser = argparse.ArgumentParser(
        description='企业知识库 RAG 管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # index 命令
    index_parser = subparsers.add_parser('index', help='索引文档')
    index_parser.add_argument('--docs-dir', '-d', default='./docs',
                              help='文档目录路径')
    index_parser.add_argument('--config', '-c', default='./config/config.yaml',
                              help='配置文件路径')
    
    # search 命令
    search_parser = subparsers.add_parser('search', help='搜索知识库')
    search_parser.add_argument('query', help='搜索查询')
    search_parser.add_argument('--top-k', '-k', type=int, default=5,
                               help='返回结果数量')
    search_parser.add_argument('--rerank', '-r', action='store_true',
                               help='使用 reranker 重排')
    search_parser.add_argument('--config', '-c', default='./config/config.yaml',
                               help='配置文件路径')
    
    # config 命令
    config_parser = subparsers.add_parser('config', help='显示配置')
    config_parser.add_argument('--config', '-c', default='./config/config.yaml',
                               help='配置文件路径')
    
    args = parser.parse_args()
    
    if args.command == 'index':
        cmd_index(args)
    elif args.command == 'search':
        cmd_search(args)
    elif args.command == 'config':
        cmd_config(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()