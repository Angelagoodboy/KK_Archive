#!/usr/bin/env python3
"""
KK文档处理工具 - 主程序入口
新增功能：生成中英文Markdown文件对
"""

import sys
import os
from pathlib import Path
from markdown_generator import MarkdownGenerator
from document_processor import DocumentProcessor  # 如果需要摘要功能

def read_input_text(filename="text.txt"):
    """
    读取输入文本：优先从文件读取，其次从命令行参数读取
    
    Args:
        filename: 输入文件名（默认text.txt）
        
    Returns:
        文本内容字符串
    """
    # 1. 尝试从文件读取
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    print(f"📁 从 {filename} 读取内容")
                    return content
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
    
    # 2. 检查是否有命令行参数提供内容
    if len(sys.argv) > 3:
        content_param = sys.argv[3]
        print(f"💬 使用命令行参数内容")
        return content_param
    
    # 3. 返回默认文本
    default_text = """这是一个示例文档内容。

## 章节1
- 项目1
- 项目2

## 章节2
主要内容在这里..."""
    
    print("⚠️  使用默认示例文本")
    return default_text

def extract_summary():
    """提取文本摘要"""
    text = read_input_text()
    processor = DocumentProcessor()
    
    print(f"📝 输入文本: {text[:100]}..." if len(text) > 100 else f"📝 输入文本: {text}")
    print("🤖 正在处理文本...")
    
    summary = processor.extract_summary(text)
    word_count = len(summary.split())
    
    print(f"✅ 处理完成!")
    print(f"📋 摘要 ({word_count} 个单词):")
    print(f"   {summary}")

def convert_to_markdown():
    """转换文档为结构化Markdown（原有功能）"""
    if len(sys.argv) < 3:
        print("使用方法: python main.py convert \"文档标题\" [原文URL] [发布日期]")
        print("示例: python main.py convert \"AI技术指南\" https://example.com 2024-01-01")
        return
    
    doc_name = sys.argv[2]
    original_url = sys.argv[3] if len(sys.argv) > 3 else ""
    publish_date = sys.argv[4] if len(sys.argv) > 4 else ""
    
    # 读取内容
    content = read_input_text()
    if not content:
        print("❌ 没有可处理的内容")
        return
    
    # 处理文档（使用原有的DocumentProcessor）
    processor = DocumentProcessor()
    print(f"📄 正在处理文档: {doc_name}")
    
    try:
        structured_md = processor.convert_to_structured_md(
            content, doc_name, original_url, publish_date
        )
        
        # 保存到文件
        output_filename = f"{processor.generate_cn_filename(doc_name)}.md"
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(structured_md)
        
        print(f"✅ 转换完成!")
        print(f"💾 输出文件: {output_filename}")
        print(f"📊 文档大小: {len(structured_md)} 字符")
        
    except Exception as e:
        print(f"❌ 转换失败: {e}")

def generate_markdown_pair():
    """生成中英文Markdown文件对（新功能）"""
    if len(sys.argv) < 3:
        print("使用方法: python main.py generate \"文档标题\" [原文URL] [发布日期] [输出目录]")
        print("示例: python main.py generate \"AI技术指南\" https://example.com 2024-01-01 output_docs")
        return
    
    title = sys.argv[2]
    original_url = sys.argv[3] if len(sys.argv) > 3 else ""
    publish_date = sys.argv[4] if len(sys.argv) > 4 else ""
    output_dir = sys.argv[5] if len(sys.argv) > 5 else "."
    
    # 读取内容
    content = read_input_text()
    if not content:
        print("❌ 没有可处理的内容")
        return
    
    print(f"📄 正在生成文档对: {title}")
    print(f"📁 输出目录: {output_dir}")
    
    # 生成文档
    generator = MarkdownGenerator()
    generator.generate_pair(
        content=content,
        title=title,
        original_url=original_url,
        publish_date=publish_date,
        output_dir=output_dir
    )

def print_help():
    """显示帮助信息"""
    print("=" * 50)
    print("🦊 KK 文档处理工具")
    print("=" * 50)
    print("使用方法:")
    print("  python main.py summary                    # 提取摘要")
    print("  python main.py convert \"标题\"            # 转换为Markdown")
    print("  python main.py convert \"标题\" URL 日期    # 完整转换")
    print("  python main.py generate \"标题\"           # 生成中英文文档对")
    print("  python main.py generate \"标题\" URL 日期 目录")
    print()
    print("📝 输入文本来源:")
    print("  1. text.txt 文件（优先）")
    print("  2. 命令行参数")
    print("  3. 默认示例文本")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1]
    
    if command == "summary":
        extract_summary()
    elif command == "convert":
        convert_to_markdown()
    elif command == "generate":
        generate_markdown_pair()
    else:
        print(f"❌ 未知命令: {command}")
        print_help()

if __name__ == "__main__":
    main()