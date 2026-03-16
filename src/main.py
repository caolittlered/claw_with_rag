"""
主程序入口
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rag_engine import RAGEngine
from document_processor import process_directory


def main():
    parser = argparse.ArgumentParser(description='企业知识库 RAG 系统')
    
    subparsers = parser.add_subparsers(dest='command')
    
    # 索引命令
    index_parser = subparsers.add_parser('index', help='索引文档到知识库')
    index_parser.add_argument('--docs-dir', '-d', default='./docs',
                              help='文档目录')
    index_parser.add_argument('--config', '-c', default='./config/config.yaml',
                              help='配置文件')
    
    # 搜索命令
    search_parser = subparsers.add_parser('search', help='搜索知识库')
    search_parser.add_argument('query', help='搜索内容')
    search_parser.add_argument('--top-k', '-k', type=int, default=5)
    search_parser.add_argument('--config', '-c', default='./config/config.yaml')
    
    args = parser.parse_args()
    
    if args.command == 'index':
        print(f"加载文档: {args.docs_dir}")
        docs = process_directory(args.docs_dir)
        print(f"共 {len(docs)} 个文档")
        
        engine = RAGEngine(args.config)
        engine.index_documents(docs)
        print("索引完成!")
        
    elif args.command == 'search':
        engine = RAGEngine(args.config)
        results = engine.retrieve_with_rerank(args.query, args.top_k)
        
        print(f"\n查询: {args.query}\n")
        for i, r in enumerate(results, 1):
            print(f"[{i}] 分数: {r['score']:.3f}")
            print(f"来源: {r['metadata'].get('filename')}")
            print(f"内容: {r['content'][:300]}...\n")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()