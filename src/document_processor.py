"""
文档处理模块
支持 txt, pdf, docx, xlsx 等格式
"""

import os
from typing import List, Optional
from pathlib import Path

from langchain.schema import Document
import pypdf
from docx import Document as DocxDocument
import pandas as pd
import openpyxl


class DocumentProcessor:
    """文档处理器"""
    
    SUPPORTED_EXTENSIONS = ['.txt', '.pdf', '.docx', '.doc', '.xlsx', '.xls']
    
    def __init__(self, input_dir: str):
        self.input_dir = Path(input_dir)
        self.input_dir.mkdir(parents=True, exist_ok=True)
    
    def load_all_documents(self) -> List[Document]:
        """加载所有文档"""
        documents = []
        
        for file_path in self._find_documents():
            try:
                docs = self.load_document(file_path)
                documents.extend(docs)
                print(f"已加载: {file_path.name}")
            except Exception as e:
                print(f"加载失败 {file_path.name}: {e}")
        
        return documents
    
    def _find_documents(self) -> List[Path]:
        """查找所有支持的文档"""
        files = []
        for ext in self.SUPPORTED_EXTENSIONS:
            files.extend(self.input_dir.glob(f"*{ext}"))
        return files
    
    def load_document(self, file_path: Path) -> List[Document]:
        """加载单个文档"""
        suffix = file_path.suffix.lower()
        
        loaders = {
            '.txt': self._load_txt,
            '.pdf': self._load_pdf,
            '.docx': self._load_docx,
            '.xlsx': self._load_xlsx,
            '.xls': self._load_xlsx,
        }
        
        loader = loaders.get(suffix)
        if not loader:
            raise ValueError(f"不支持的文件格式: {suffix}")
        
        content = loader(file_path)
        
        return [Document(
            page_content=content,
            metadata={
                'source': str(file_path),
                'filename': file_path.name,
                'type': suffix[1:]
            }
        )]
    
    def _load_txt(self, file_path: Path) -> str:
        """加载文本文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _load_pdf(self, file_path: Path) -> str:
        """加载 PDF 文件"""
        reader = pypdf.PdfReader(str(file_path))
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text())
        return "\n\n".join(text_parts)
    
    def _load_docx(self, file_path: Path) -> str:
        """加载 Word 文档"""
        doc = DocxDocument(str(file_path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    
    def _load_xlsx(self, file_path: Path) -> str:
        """加载 Excel 文件"""
        # 读取所有工作表
        excel_file = pd.ExcelFile(file_path)
        all_text = []
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            # 将表格转换为文本格式
            text = f"【工作表: {sheet_name}】\n"
            text += df.to_string(index=False, na_rep='')
            all_text.append(text)
        
        return "\n\n".join(all_text)


def process_directory(input_dir: str) -> List[Document]:
    """处理目录中的所有文档"""
    processor = DocumentProcessor(input_dir)
    return processor.load_all_documents()


if __name__ == "__main__":
    # 测试
    docs = process_directory("./docs")
    print(f"共加载 {len(docs)} 个文档")
    for doc in docs[:3]:
        print(f"- {doc.metadata['filename']}: {len(doc.page_content)} 字符")