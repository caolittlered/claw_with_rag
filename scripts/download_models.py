#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型下载脚本
预先下载所需模型，避免运行时等待
支持 HuggingFace、HF镜像、ModelScope 三种下载源
"""

import os
import sys

from sentence_transformers import SentenceTransformer
from transformers import AutoModelForSequenceClassification, AutoTokenizer


def download_from_modelscope(model_id: str, desc: str) -> bool:
    """从 ModelScope 下载模型"""
    try:
        from modelscope import snapshot_download
        
        # ModelScope 上的模型 ID 映射
        modelscope_ids = {
            "BAAI/bge-large-zh-v1.5": "Xorbits/bge-large-zh-v1.5",
            "BAAI/bge-reranker-large": "Xorbits/bge-reranker-large",
        }
        
        ms_model_id = modelscope_ids.get(model_id, model_id)
        print(f"从 ModelScope 下载: {ms_model_id}")
        
        cache_dir = snapshot_download(ms_model_id)
        print(f"✓ {desc} 下载完成，缓存路径: {cache_dir}")
        return True
    except ImportError:
        print("✗ ModelScope 未安装，请先安装: pip install modelscope")
        return False
    except Exception as e:
        print(f"✗ ModelScope 下载失败: {e}")
        return False


def download_from_hf(model_id: str, desc: str, use_mirror: bool = False) -> bool:
    """从 HuggingFace 或镜像下载"""
    try:
        if "reranker" in model_id:
            # Reranker 模型
            AutoModelForSequenceClassification.from_pretrained(model_id)
            AutoTokenizer.from_pretrained(model_id)
        else:
            # Embedding 模型
            SentenceTransformer(model_id)
        print(f"✓ {desc} 下载完成")
        return True
    except Exception as e:
        print(f"✗ HuggingFace 下载失败: {e}")
        return False


def download_models(source: str = "auto"):
    """下载所有需要的模型
    
    Args:
        source: 下载源 - "hf" (HuggingFace), "mirror" (HF镜像), "modelscope" (ModelScope), "auto" (自动选择)
    """
    
    models = [
        ("BAAI/bge-large-zh-v1.5", "Embedding 模型"),
        ("BAAI/bge-reranker-large", "Reranker 模型"),
    ]
    
    print("=" * 50)
    print(f"开始下载模型... (源: {source})")
    print("=" * 50)
    
    all_success = True
    
    for model_id, desc in models:
        print(f"\n>>> 下载 {desc}: {model_id}")
        
        success = False
        
        # 根据指定源下载
        if source == "modelscope":
            success = download_from_modelscope(model_id, desc)
        elif source == "mirror":
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            print("使用 HF 镜像: https://hf-mirror.com")
            success = download_from_hf(model_id, desc, use_mirror=True)
        elif source == "hf":
            success = download_from_hf(model_id, desc)
        else:  # auto
            # 自动尝试：ModelScope -> HF镜像 -> HF
            print("自动选择下载源...")
            success = download_from_modelscope(model_id, desc)
            if not success:
                print("尝试 HF 镜像...")
                os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
                success = download_from_hf(model_id, desc, use_mirror=True)
            if not success:
                print("尝试 HF 原站...")
                if 'HF_ENDPOINT' in os.environ:
                    del os.environ['HF_ENDPOINT']
                success = download_from_hf(model_id, desc)
        
        if not success:
            all_success = False
            print(f"\n所有下载源均失败，请检查网络或手动下载：")
            print(f"  ModelScope: https://modelscope.cn/models/Xorbits/bge-large-zh-v1.5")
            print(f"  HF 镜像: https://hf-mirror.com/{model_id}")
            return False
    
    if all_success:
        print("\n" + "=" * 50)
        print("所有模型下载完成！")
        print("=" * 50)
    
    return all_success


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='预下载模型')
    parser.add_argument('--mirror', action='store_true',
                        help='使用 HF 镜像 (hf-mirror.com)')
    parser.add_argument('--modelscope', action='store_true',
                        help='从 ModelScope 下载 (国内推荐)')
    parser.add_argument('--hf', action='store_true',
                        help='从 HuggingFace 原站下载')
    args = parser.parse_args()
    
    # 确定下载源
    if args.modelscope:
        source = "modelscope"
    elif args.mirror:
        source = "mirror"
    elif args.hf:
        source = "hf"
    else:
        source = "auto"
    
    success = download_models(source)
    sys.exit(0 if success else 1)