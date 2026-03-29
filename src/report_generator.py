"""
报告生成模块
支持生成 Markdown、HTML、PDF 和 Word 格式的报告
"""

import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional


def generate_report_md(title: str, content: str, sources: list = None) -> str:
    """生成 Markdown 格式的报告"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md_content = f"""# {title}

**生成时间**: {timestamp}

---

{content}

---
"""

    if sources:
        md_content += "\n## 参考来源\n\n"
        for i, source in enumerate(sources, 1):
            # 支持字符串或字典格式
            if isinstance(source, dict):
                source_text = f"[{source.get('title', '未知')}]({source.get('url', '#')})"
            else:
                source_text = str(source)
            md_content += f"{i}. {source_text}\n"

    return md_content


def generate_report_html(title: str, content: str, sources: list = None) -> str:
    """生成 HTML 格式的报告"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 将 Markdown 转换为 HTML
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1 {{ color: #1a1a1a; border-bottom: 2px solid #6366f1; padding-bottom: 10px; }}
        h2 {{ color: #2d2d2d; margin-top: 30px; }}
        .meta {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
        .content {{ background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .sources {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; }}
        .sources ol {{ padding-left: 20px; }}
        .sources li {{ margin: 8px 0; }}
        .sources a {{ color: #6366f1; text-decoration: none; }}
        .sources a:hover {{ text-decoration: underline; }}
        code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
        pre {{ background: #1e293b; color: #e2e8f0; padding: 16px; border-radius: 8px; overflow-x: auto; }}
        pre code {{ background: transparent; padding: 0; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="meta">生成时间: {timestamp}</div>
    <div class="content">
        {markdown_to_html(content)}
    </div>
"""
    
    if sources:
        html_content += "    <div class=\"sources\">\n        <h2>参考来源</h2>\n        <ol>\n"
        for source in sources:
            # 支持字符串或字典格式
            if isinstance(source, dict):
                title = source.get('title', '未知')
                url = source.get('url', '#')
            else:
                title = str(source)
                url = '#'
            html_content += f'            <li><a href="{url}" target="_blank">{title}</a></li>\n'
        html_content += "        </ol>\n    </div>\n"
    
    html_content += "</body>\n</html>"
    
    return html_content


def generate_report_txt(title: str, content: str, sources: list = None) -> str:
    """生成纯文本格式的报告"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    txt_content = f"""{title}
{'=' * len(title)}

生成时间: {timestamp}

{content}

"""
    
    if sources:
        txt_content += "\n参考来源:\n"
        for i, source in enumerate(sources, 1):
            # 支持字符串或字典格式
            if isinstance(source, dict):
                source_text = f"{source.get('title', '未知')} - {source.get('url', '#')}"
            else:
                source_text = str(source)
            txt_content += f"{i}. {source_text}\n"
    
    return txt_content


def markdown_to_html(md: str) -> str:
    """简单的 Markdown 转 HTML"""
    # 代码块
    md = re.sub(r'```(\w+)?\n(.*?)```', r'<pre><code>\2</code></pre>', md, flags=re.DOTALL)
    
    # 行内代码
    md = re.sub(r'`([^`]+)`', r'<code>\1</code>', md)
    
    # 粗体
    md = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', md)
    
    # 斜体
    md = re.sub(r'\*(.+?)\*', r'<em>\1</em>', md)
    
    # 标题
    md = re.sub(r'^### (.+)$', r'<h3>\1</h3>', md, flags=re.MULTILINE)
    md = re.sub(r'^## (.+)$', r'<h2>\1</h2>', md, flags=re.MULTILINE)
    md = re.sub(r'^# (.+)$', r'<h1>\1</h1>', md, flags=re.MULTILINE)
    
    # 列表
    md = re.sub(r'^\- (.+)$', r'<li>\1</li>', md, flags=re.MULTILINE)
    md = re.sub(r'(<li>.+</li>\n)+', r'<ul>\g<0></ul>', md)
    
    # 链接
    md = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', md)
    
    # 段落
    paragraphs = md.split('\n\n')
    html = []
    for p in paragraphs:
        p = p.strip()
        if p and not p.startswith('<') and not p.endswith('>'):
            p = f'<p>{p}</p>'
        html.append(p)
    
    return '\n'.join(html)


def save_report(content: str, filename: str, directory: str = "/tmp/reports") -> str:
    """保存报告到文件"""
    os.makedirs(directory, exist_ok=True)
    filepath = os.path.join(directory, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return filepath