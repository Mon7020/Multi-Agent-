#!/usr/bin/env python3
"""
Markdown to PDF converter
使用Python内置库将Markdown转换为HTML，再转换为PDF
"""

import re
import os
import sys

def md_to_html(md_content: str) -> str:
    """将Markdown内容转换为HTML"""
    lines = md_content.split('\n')
    html_lines = []
    in_code_block = False
    code_lang = ""
    
    # HTML头部
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
body { font-family: "Microsoft YaHei", "SimSun", sans-serif; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 20px; }
h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
h2 { color: #2980b9; border-bottom: 2px solid #3498db; padding-bottom: 8px; margin-top: 30px; }
h3 { color: #27ae60; }
h4 { color: #8e44ad; }
table { border-collapse: collapse; width: 100%; margin: 15px 0; }
th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
th { background-color: #3498db; color: white; }
tr:nth-child(even) { background-color: #f2f2f2; }
code { background-color: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: Consolas, monospace; font-size: 0.9em; }
pre { background-color: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; overflow-x: auto; }
pre code { background: none; color: inherit; }
blockquote { border-left: 4px solid #3498db; margin: 15px 0; padding-left: 20px; color: #7f8c8d; }
ul, ol { margin: 10px 0; padding-left: 25px; }
li { margin: 5px 0; }
strong { color: #e74c3c; }
hr { border: none; border-top: 2px solid #eee; margin: 30px 0; }
.highlight { background-color: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107; }
</style>
</head>
<body>
"""
    html_lines.append(html)
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 代码块处理
        if line.strip().startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_lang = line.strip()[3:].strip()
                html_lines.append(f'<pre><code class="language-{code_lang}">')
            else:
                in_code_block = False
                html_lines.append('</code></pre>')
            i += 1
            continue
        
        if in_code_block:
            # 转义HTML特殊字符
            escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            html_lines.append(escaped)
            i += 1
            continue
        
        # 空行
        if not line.strip():
            html_lines.append('<br>')
            i += 1
            continue
        
        # 标题
        if line.startswith('# '):
            html_lines.append(f'<h1>{line[2:]}</h1>')
        elif line.startswith('## '):
            html_lines.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith('### '):
            html_lines.append(f'<h3>{line[4:]}</h3>')
        elif line.startswith('#### '):
            html_lines.append(f'<h4>{line[5:]}</h4>')
        
        # 分隔线
        elif line.strip() == '---' or line.strip().startswith('---'):
            html_lines.append('<hr>')
        
        # 表格
        elif '|' in line and i + 1 < len(lines) and '|---' in lines[i+1]:
            # 解析表格
            table_rows = []
            while i < len(lines) and '|' in lines[i]:
                cells = [c.strip() for c in line.split('|')[1:-1]]
                table_rows.append(cells)
                i += 1
            
            if table_rows:
                # 表头
                html_lines.append('<table><thead><tr>')
                for cell in table_rows[0]:
                    html_lines.append(f'<th>{cell}</th>')
                html_lines.append('</tr></thead><tbody>')
                # 表体（跳过分隔行）
                for row in table_rows[2:]:
                    html_lines.append('<tr>')
                    for cell in row:
                        html_lines.append(f'<td>{cell}</td>')
                    html_lines.append('</tr>')
                html_lines.append('</tbody></table>')
            continue
        
        # 列表项
        elif line.strip().startswith('- ') or line.strip().startswith('* '):
            content = re.sub(r'^[-*]\s+', '', line.strip())
            content = format_inline(content)
            html_lines.append(f'<li>{content}</li>')
        
        # 有序列表
        elif re.match(r'^\d+\.\s', line.strip()):
            content = re.sub(r'^\d+\.\s+', '', line.strip())
            content = format_inline(content)
            html_lines.append(f'<li>{content}</li>')
        
        # 引用块
        elif line.startswith('> '):
            content = line[2:]
            content = format_inline(content)
            html_lines.append(f'<blockquote>{content}</blockquote>')
        
        # 普通段落
        else:
            content = format_inline(line.strip())
            if content:
                html_lines.append(f'<p>{content}</p>')
        
        i += 1
    
    html_lines.append('</body></html>')
    return '\n'.join(html_lines)

def format_inline(text: str) -> str:
    """格式化行内元素"""
    # 粗体
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # 斜体
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # 行内代码
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    # 链接
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    return text

def main():
    if len(sys.argv) < 2:
        print("用法: python md_to_pdf.py <input.md> [output.pdf]")
        print("或: python md_to_pdf.py <input.md> (输出同目录PDF)")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.rsplit('.', 1)[0] + '.pdf'
    
    # 读取Markdown文件
    with open(input_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # 转换为HTML
    html_content = md_to_html(md_content)
    
    # 保存HTML中间文件
    html_file = input_file.rsplit('.', 1)[0] + '.html'
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"HTML文件已生成: {html_file}")
    
    # 尝试使用浏览器打印为PDF (Windows)
    try:
        import subprocess
        import webbrowser
        import tempfile
        
        # 使用 wkhtmltopdf 或浏览器
        # 先尝试直接用浏览器打开并提示用户手动保存为PDF
        print("\n" + "="*60)
        print("PDF生成说明")
        print("="*60)
        print(f"已生成HTML文件: {html_file}")
        print(f"\n请使用以下方式之一转换为PDF:")
        print("1. 用浏览器打开HTML文件，然后 Ctrl+P 打印为PDF")
        print("2. 使用VS Code: 打开HTML → 右键 → Open with Live Server → 打印PDF")
        print("3. 安装pandoc后运行: pandoc {input_file} -o {output_file}")
        print("="*60)
        
        # 尝试自动打开
        os.startfile(html_file)
        
    except Exception as e:
        print(f"无法自动打开: {e}")

if __name__ == "__main__":
    main()