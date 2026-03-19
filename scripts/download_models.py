#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型下载脚本
预先下载所需模型，避免运行时等待
"""

import os
import sys

# 配置 Hugging Face 镜像（可选）
# 如果在中国大陆，取消下面的注释
# os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

from sentence_transformers import SentenceTransformer, CrossEncoder


def download_models():
    """下载所有需要的模型"""
    
    models = [
        ("BAAI/bge-large-zh-v1.5", "Embedding 模型"),
        ("BAAI/bge-reranker-large", "Reranker 模型"),
    ]
    
    print("=" * 50)
    print("开始下载模型...")
    print("=" * 50)
    
    for model_name, desc in models:
        print(f"\n>>> 下载 {desc}: {model_name}")
        try:
            if "reranker" in model_name:
                # 下载 Reranker
                model = CrossEncoder(model_name)
            else:
                # 下载 Embedding
                model = SentenceTransformer(model_name)
            print(f"✓ {desc} 下载完成")
        except Exception as e:
            print(f"✗ 下载失败: {e}")
            print("\n如果下载失败，请尝试：")
            print("1. 使用镜像: export HF_ENDPOINT=https://hf-mirror.com")
            print("2. 或手动下载: https://hf-mirror.com/{model_name}")
            return False
    
    print("\n" + "=" * 50)
    print("所有模型下载完成！")
    print("=" * 50)
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='预下载模型')
    parser.add_argument('--mirror', action='store_true',
                        help='使用国内镜像 (hf-mirror.com)')
    args = parser.parse_args()
    
    if args.mirror:
        os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
        print("已启用国内镜像: https://hf-mirror.com")
    
    success = download_models()
    sys.exit(0 if success else 1)