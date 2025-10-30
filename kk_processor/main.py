#!/usr/bin/env python3
"""
KK文档处理工具 - 主程序入口
"""

import sys
import os
import argparse
import re
import signal
import time
from pathlib import Path
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 尝试导入document_processor
try:
    from document_processor import DocumentProcessor
    print("✅ document_processor 导入成功")
except ImportError:
    print("⚠️  document_processor 导入失败，部分功能可能不可用")
    DocumentProcessor = None

# 默认示例文本
DEFAULT_TEXT = """This is a default example document. Used when no input text is provided.

## Chapter Title
- Item 1: Example content
- Item 2: More examples

Main paragraph content will be displayed here. This tool is used for document conversion and summary extraction.
"""

def read_file_content(filename):
    """读取文件内容"""
    try:
        filepath = Path(filename)
        if not filepath.exists():
            return None
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return content if content else None
    except Exception as e:
        print(f"❌ 读取文件失败 {filename}: {e}")
        return None

def get_input_text(args):
    """
    获取输入文本，按优先级处理：
    1. --text 参数（最高优先级）
    2. --file 参数
    3. text.txt 文件（后备）
    4. 默认示例文本（最后）
    """
    # 1. 命令行直接输入文本
    if args.text:
        print(f"💬 使用命令行文本输入")
        return args.text
    
    # 2. 指定文件
    if args.file:
        content = read_file_content(args.file)
        if content:
            print(f"📁 从指定文件读取: {args.file}")
            return content
        else:
            print(f"⚠️ 指定文件不存在或为空: {args.file}")
    
    # 3. text.txt 文件（后备）
    content = read_file_content("text.txt")
    if content:
        print(f"📁 从text.txt读取")
        return content
    
    # 4. 默认示例文本
    print("⚠️ 使用默认示例文本")
    return DEFAULT_TEXT

def _split_paragraphs(content: str) -> list:
    """
    将内容分割成自然段数组
    """
    paragraphs = []
    current_paragraph = []
    
    lines = content.split('\n')
    
    for line in lines:
        stripped_line = line.strip()
        
        if not stripped_line:  # 空行，表示段落分隔
            if current_paragraph:  # 当前段落有内容
                paragraph_text = '\n'.join(current_paragraph)
                paragraphs.append(paragraph_text)
                current_paragraph = []
        else:
            current_paragraph.append(line)
    
    if current_paragraph:
        paragraph_text = '\n'.join(current_paragraph)
        paragraphs.append(paragraph_text)
    
    if not paragraphs and content.strip():
        paragraphs = [content.strip()]
    
    return paragraphs

def _generate_heading(paragraph: str, max_words: int = 4) -> str:
    """
    为段落生成二级标题
    """
    if hasattr(_generate_heading, '_in_progress'):
        return "Content Summary"
    
    _generate_heading._in_progress = True
    
    try:
        if DocumentProcessor is not None:
            if not hasattr(_generate_heading, '_processor'):
                _generate_heading._processor = DocumentProcessor()
            
            processor = _generate_heading._processor
            
            def timeout_handler(signum, frame):
                raise TimeoutError("标题生成超时")
            
            original_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)
            
            try:
                # 使用 generate_heading 方法
                heading = processor.generate_heading(paragraph, max_words=max_words)
                signal.alarm(0)
                
                if heading and heading.strip():
                    heading = heading.strip()
                    heading = re.sub(r'[.!?。！？]+$', '', heading)
                    return heading
                    
            except TimeoutError:
                print("⚠️ 标题生成超时，使用默认标题")
                return "Content Summary"
            except Exception as e:
                print(f"❌ 调用标题生成功能失败: {e}")
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, original_handler)
                
    except Exception as e:
        print(f"❌ 标题生成过程中出错: {e}")
    finally:
        if hasattr(_generate_heading, '_in_progress'):
            delattr(_generate_heading, '_in_progress')
    
    return "Content Summary"

def _format_heading_markdown(heading_text: str) -> str:
    """
    将标题文本格式化为Markdown二级标题格式
    """
    cleaned_heading = heading_text.strip()
    cleaned_heading = re.sub(r'^[:\-\s]+|[:\-\s]+$', '', cleaned_heading)
    
    if not cleaned_heading:
        cleaned_heading = "Content Summary"
    
    return f"## {cleaned_heading}"

def _process_content_with_headings(content: str, max_words: int = 4) -> str:
    """
    处理内容，为自然段添加二级标题（仅用于英文内容）
    """
    print(f"🔍 开始处理英文内容，长度: {len(content)} 字符")
    
    try:
        paragraphs = _split_paragraphs(content)
        print(f"📊 分割出 {len(paragraphs)} 个自然段")
        
        processed_paragraphs = []
        
        for i, paragraph in enumerate(paragraphs):
            print(f"🔍 正在处理段落 {i+1}/{len(paragraphs)}")
            
            try:
                cleaned_paragraph = paragraph.strip()
                if not cleaned_paragraph:
                    print(f"  段落 {i+1}: 空段落，跳过")
                    continue
                
                print(f"  段落 {i+1} 长度: {len(cleaned_paragraph)} 字符")
                    
                if len(cleaned_paragraph) > 100:
                    print(f"  段落 {i+1}: 需要生成标题")
                    heading_text = _generate_heading(cleaned_paragraph, max_words)
                    markdown_heading = _format_heading_markdown(heading_text)
                    processed_paragraphs.append(f"{markdown_heading}\n\n{cleaned_paragraph}")
                    
                    print(f"  段落 {i+1}: 添加标题 '{heading_text}'")
                else:
                    processed_paragraphs.append(cleaned_paragraph)
                    print(f"  段落 {i+1}: 保留原格式")
                        
            except Exception as e:
                print(f"❌ 处理段落 {i+1} 时出错: {e}")
                processed_paragraphs.append(paragraph.strip())
        
        print(f"✅ 所有段落处理完成，共 {len(processed_paragraphs)} 个段落")
        return '\n\n'.join(processed_paragraphs)
        
    except Exception as e:
        print(f"❌ 处理内容时发生严重错误: {e}")
        return content

def _translate_to_chinese(content: str) -> str:
    """
    将整篇英文文档翻译成中文
    """
    if DocumentProcessor is None:
        print("⚠️  document_processor 不可用，无法翻译内容")
        return content
    
    try:
        processor = DocumentProcessor()
        print("🌐 开始整体翻译文档...")
        print(f"📊 翻译内容长度: {len(content)} 字符")
        
        translated = processor.translate_text(content, "英文", "中文")
        
        print("✅ 整体翻译完成")
        return translated
        
    except Exception as e:
        print(f"❌ 翻译失败: {e}")
        return content

def _format_chinese_document(chinese_doc: str, original_title: str, cn_url: str, 
                           publish_date: str, subject: str, original_url: str) -> str:
    """
    格式化翻译后的中文文档
    """
    return chinese_doc

def _generate_markdown_pair(content: str, title: str, 
                           subject: str = "通用",
                           original_url: str = "", 
                           publish_date: str = "",
                           output_dir: str = "."):
    """
    生成中英文Markdown文件对
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    if not publish_date:
        publish_date = datetime.now().strftime("%Y-%m-%d")
    
    def _sanitize_filename(filename: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "", filename).replace(" ", "_")
    
    en_filename = f"{_sanitize_filename(title)}.md"
    cn_filename = f"{_sanitize_filename(title)}_cn.md"
    
    en_filepath = output_path / en_filename
    cn_filepath = output_path / cn_filename
    
    en_url = f"https://github.com/Angelagoodboy/KK_Archive/blob/main/{en_filename}"
    cn_url = f"https://github.com/Angelagoodboy/KK_Archive/blob/main/{cn_filename}"
    
    # 处理英文版
    print("📝 正在为英文内容添加二级标题...")
    processed_en_content = _process_content_with_headings(content)
    
    # 生成英文版元数据
    en_metadata = f"""> **Publish Date**: {publish_date}  
> **Author**: Kevin Kelly  
> **Subject**: {subject}  

**Document Information**
- Original URL: {original_url if original_url else "Not provided"}
- Chinese Version: [{cn_url}]({cn_url})"""
    
    # 已去掉 "Document generated by KK Document Processor" 标记
    en_md = f"""# {title}

{en_metadata}

{processed_en_content}
"""
    
    # 翻译成中文
    print("🌐 正在翻译完整的英文Markdown文档...")
    print(f"📊 翻译内容长度: {len(en_md)} 字符")
    
    chinese_md = _translate_to_chinese(en_md)
    cn_md = _format_chinese_document(chinese_md, title, cn_url, publish_date, subject, original_url)
    
    # 写入文件
    with open(en_filepath, 'w', encoding='utf-8') as f:
        f.write(en_md)
    
    with open(cn_filepath, 'w', encoding='utf-8') as f:
        f.write(cn_md)
    
    print(f"✅ 文件生成完成:")
    print(f"   • 英文版: {en_filepath}")
    print(f"   • 中文版: {cn_filepath}")
    
    return str(en_filepath), str(cn_filepath)

def extract_summary(args):
    """提取文本摘要"""
    if DocumentProcessor is None:
        print("❌ document_processor 不可用，无法执行摘要提取")
        return
    
    text = get_input_text(args)
    
    processor = DocumentProcessor()
    
    print(f"📝 输入文本长度: {len(text)} 字符")
    if args.verbose:
        preview = text[:200] + "..." if len(text) > 200 else text
        print(f"📋 内容预览: {preview}")
    
    print("🤖 正在提取摘要...")
    try:
        summary = processor.extract_summary(text, args.max_words)
        word_count = len(summary.split())
        
        print(f"✅ 摘要提取完成!")
        print(f"📊 摘要 ({word_count}/{args.max_words} 单词):")
        print(f"   {summary}")
    except Exception as e:
        print(f"❌ 摘要提取失败: {e}")
        words = text.split()[:args.max_words]
        fallback_summary = " ".join(words)
        print(f"🔄 使用备用摘要: {fallback_summary}")

def generate_markdown_pair(args):
    """生成中英文Markdown文件对"""
    text = get_input_text(args)
    
    print(f"📄 正在生成文档对: {args.title}")
    print(f"🏷️ 文档主题: {args.subject}")
    if args.output:
        print(f"📁 输出目录: {args.output}")
    
    try:
        en_file, cn_file = _generate_markdown_pair(
            content=text,
            title=args.title,
            subject=args.subject,
            original_url=args.url,
            publish_date=args.date,
            output_dir=args.output
        )
        
        print(f"✅ 生成完成!")
        print(f"   • 英文版: {en_file}")
        print(f"   • 中文版: {cn_file}")
        
    except Exception as e:
        print(f"❌ 文档生成失败: {e}")

def setup_parser():
    """设置命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="KK文档处理工具 - 智能文档转换和摘要提取",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  摘要提取: python main.py summary --text "要摘要的文本"
  生成文档对: python main.py generate --title "标题" --subject "AI" --file input.txt --output docs/
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='选择操作命令')
    
    input_group = argparse.ArgumentParser(add_help=False)
    input_group.add_argument('--text', '-t', help='直接输入文本内容')
    input_group.add_argument('--file', '-f', help='从文件读取内容')
    input_group.add_argument('--verbose', '-v', action='store_true', help='详细输出模式')
    input_group.add_argument('--quiet', '-q', action='store_true', help='静默模式')
    
    summary_parser = subparsers.add_parser('summary', help='提取文本摘要', parents=[input_group])
    summary_parser.add_argument('--max-words', '-w', type=int, default=5, help='摘要最大单词数')
    
    generate_parser = subparsers.add_parser('generate', help='生成中英文文档对', parents=[input_group])
    generate_parser.add_argument('--title', required=True, help='文档标题')
    generate_parser.add_argument('--subject', '-s', default='通用', help='文档主题（如AI、科技等）')
    generate_parser.add_argument('--url', '-u', default='', help='原文URL')
    generate_parser.add_argument('--date', '-d', default='', help='发布日期')
    generate_parser.add_argument('--output', '-o', default='.', help='输出目录')
    
    return parser

def main():
    """主函数"""
    parser = setup_parser()
    
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'summary':
            extract_summary(args)
        elif args.command == 'generate':
            generate_markdown_pair(args)
        else:
            parser.print_help()
            
    except KeyboardInterrupt:
        print("\n\n👋 程序被用户中断")
    except Exception as e:
        print(f"❌ 程序执行错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()