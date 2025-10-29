#!/usr/bin/env python3
"""
KK文档处理工具 - 主程序入口
完整独立版本，包含所有功能整合
支持：摘要提取、文档转换、中英文文档对生成
中英文版本互相指向对方链接
"""

import sys
import os
import argparse
import re
import signal
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
DEFAULT_TEXT = """这是一个默认示例文档。当没有提供输入文本时使用此内容。

## 章节标题
- 项目1：示例内容
- 项目2：更多示例

主要段落内容会在这里展示。这个工具用于处理文档转换和摘要提取。
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
            print(f"⚠️  指定文件不存在或为空: {args.file}")
    
    # 3. text.txt 文件（后备）
    content = read_file_content("text.txt")
    if content:
        print(f"📁 从text.txt读取")
        return content
    
    # 4. 默认示例文本
    print("⚠️  使用默认示例文本")
    return DEFAULT_TEXT

def _split_paragraphs(content: str) -> list:
    """
    将内容分割成自然段数组
    分割逻辑：通过连续换行（空行）来分割段落
    
    Args:
        content: 原始文本内容
        
    Returns:
        list: 自然段数组，每个元素是一个段落（保留内部格式）
    """
    paragraphs = []
    current_paragraph = []
    
    # 按行处理，保留原有的换行结构
    lines = content.split('\n')
    
    for line in lines:
        stripped_line = line.strip()
        
        if not stripped_line:  # 空行，表示段落分隔
            if current_paragraph:  # 当前段落有内容
                paragraph_text = '\n'.join(current_paragraph)
                paragraphs.append(paragraph_text)
                current_paragraph = []
        else:
            # 非空行，添加到当前段落
            current_paragraph.append(line)
    
    # 处理最后一个段落（如果存在）
    if current_paragraph:
        paragraph_text = '\n'.join(current_paragraph)
        paragraphs.append(paragraph_text)
    
    # 如果没有检测到空行分隔，但内容非空，则将整个内容作为一个段落
    if not paragraphs and content.strip():
        paragraphs = [content.strip()]
    
    return paragraphs

def _generate_heading(paragraph: str, max_words: int = 4) -> str:
    """
    为段落生成二级标题，调用document_processor的summary功能
    添加死循环保护机制和超时保护
    
    Args:
        paragraph: 段落文本
        max_words: 摘要最大单词数
        
    Returns:
        str: 生成的标题文本
    """
    # 递归保护：防止函数调用自身导致死循环
    if hasattr(_generate_heading, '_in_progress'):
        return "内容摘要"
    
    # 设置执行中标志
    _generate_heading._in_progress = True
    
    try:
        if DocumentProcessor is not None:
            # 确保DocumentProcessor只初始化一次（单例模式）
            if not hasattr(_generate_heading, '_processor'):
                _generate_heading._processor = DocumentProcessor()
            
            processor = _generate_heading._processor
            
            # 超时处理函数
            def timeout_handler(signum, frame):
                raise TimeoutError("标题生成超时")
            
            # 设置超时（10秒）
            original_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)
            
            try:
                # 调用document_processor的摘要功能
                summary = processor.extract_summary(paragraph, max_words=max_words)
                signal.alarm(0)  # 取消超时
                
                if summary and summary.strip():
                    # 清理标题格式
                    heading = summary.strip()
                    heading = re.sub(r'[.!?。！？]+$', '', heading)
                    return heading
                    
            except TimeoutError:
                print("⚠️  标题生成超时，使用默认标题")
                return "内容摘要"
            except Exception as e:
                print(f"❌ 调用document_processor摘要功能失败: {e}")
            finally:
                signal.alarm(0)  # 确保取消超时
                # 恢复原来的信号处理器
                signal.signal(signal.SIGALRM, original_handler)
                
    except Exception as e:
        print(f"❌ 标题生成过程中出错: {e}")
    finally:
        # 清除执行中标志
        if hasattr(_generate_heading, '_in_progress'):
            delattr(_generate_heading, '_in_progress')
    
    # 如果生成失败，返回简单标题
    return "内容摘要"

def _format_heading_markdown(heading_text: str) -> str:
    """
    将标题文本格式化为Markdown二级标题格式
    
    Args:
        heading_text: 标题文本
        
    Returns:
        str: Markdown格式的二级标题，如 "## 标题内容"
    """
    # 清理标题文本
    cleaned_heading = heading_text.strip()
    
    # 移除可能的多余标点
    cleaned_heading = re.sub(r'^[:\-\s]+|[:\-\s]+$', '', cleaned_heading)
    
    # 确保标题格式正确
    if not cleaned_heading:
        cleaned_heading = "内容摘要"
    
    # 返回Markdown二级标题格式
    return f"## {cleaned_heading}"

def _process_content_with_headings(content: str, max_words: int = 4) -> str:
    """
    处理内容，为自然段添加二级标题
    
    Args:
        content: 原始文本内容
        max_words: 标题摘要单词数
        
    Returns:
        str: 添加了二级标题的文本内容
    """
    print(f"🔍 开始处理内容，长度: {len(content)} 字符")
    
    try:
        # 使用_split_paragraphs分割内容
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
                    
                # 为长段落生成标题
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
                import traceback
                traceback.print_exc()
                # 出错时保留原段落
                processed_paragraphs.append(paragraph.strip())
        
        print(f"✅ 所有段落处理完成，共 {len(processed_paragraphs)} 个段落")
        return '\n\n'.join(processed_paragraphs)
        
    except Exception as e:
        print(f"❌ 处理内容时发生严重错误: {e}")
        import traceback
        traceback.print_exc()
        # 出错时返回原始内容
        return content

def _generate_markdown_pair(content: str, title: str, 
                           subject: str = "通用",
                           original_url: str = "", 
                           publish_date: str = "",
                           output_dir: str = "."):
    """
    生成中英文Markdown文件对（内部函数）
    中英文版本互相指向对方链接
    
    Args:
        content: 原始文本内容
        title: 文档标题
        subject: 文档主题（如AI、科技等）
        original_url: 原文URL（可选）
        publish_date: 发布日期（可选）
        output_dir: 输出目录（默认当前目录）
        
    Returns:
        英文版和中文版文件路径
    """
    # 确保输出目录存在
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # 默认处理内容，添加二级标题
    print("📝 正在为内容添加二级标题...")
    processed_content = _process_content_with_headings(content)
    
    # 处理发布日期
    if not publish_date:
        publish_date = datetime.now().strftime("%Y-%m-%d")
    
    # 生成文件名
    def _sanitize_filename(filename: str) -> str:
        """清理文件名中的特殊字符"""
        return re.sub(r'[\\/*?:"<>|]', "", filename).replace(" ", "_")
    
    # 生成文件名
    en_filename = f"{_sanitize_filename(title)}.md"
    cn_filename = f"{_sanitize_filename(title)}_cn.md"
    
    # 生成文件路径
    en_filepath = output_path / en_filename
    cn_filepath = output_path / cn_filename
    
    # 生成互相指向的URL
    en_url = f"https://github.com/Angelagoodboy/KK_Archive/blob/main/{en_filename}"
    cn_url = f"https://github.com/Angelagoodboy/KK_Archive/blob/main/{cn_filename}"
    
    # 生成英文版（指向中文版）
    en_metadata = f"""> **Publish Date**: {publish_date}  
> **Author**: Kevin Kelly  
> **Subject**: {subject}  

**Document Information**
- Original URL: {original_url if original_url else "Not provided"}
- Chinese Version: [{cn_url}]({cn_url})"""
    
    en_md = f"""# {title}

{en_metadata}

{processed_content}

---

*Document generated by KK Document Processor*
"""
    
    # 生成中文版（指向英文版）
    cn_title = f"{title}（中文版）"
    cn_metadata = f"""> **发布时间**: {publish_date}  
> **作者**: 凯文·凯利 (Kevin Kelly)  
> **主题**: {subject}  

**文档信息**
- 原文地址: {original_url if original_url else "未提供"}
- 英文版本: [{en_url}]({en_url})"""
    
    cn_md = f"""# {cn_title}

{cn_metadata}

{processed_content}

---

*文档由 KK 文档处理器生成*
"""
    
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
        # 备用方案：提取前N个单词
        words = text.split()[:args.max_words]
        fallback_summary = " ".join(words)
        print(f"🔄 使用备用摘要: {fallback_summary}")

def convert_to_markdown(args):
    """转换文档为结构化Markdown"""
    if DocumentProcessor is None:
        print("❌ document_processor 不可用，无法执行文档转换")
        return
    
    text = get_input_text(args)
    
    # 处理内容，添加二级标题
    print("📝 正在为内容添加二级标题...")
    processed_text = _process_content_with_headings(text)
    
    processor = DocumentProcessor()
    print(f"📄 正在处理文档: {args.title}")
    
    try:
        structured_md = processor.convert_to_structured_md(
            processed_text, args.title, args.url, args.date
        )
        
        # 确定输出文件名
        if args.output:
            output_dir = Path(args.output)
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / f"{processor.generate_cn_filename(args.title)}.md"
        else:
            output_file = Path(f"{processor.generate_cn_filename(args.title)}.md")
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(structured_md)
        
        print(f"✅ 转换完成!")
        print(f"💾 输出文件: {output_file}")
        print(f"📊 文档大小: {len(structured_md)} 字符")
        
        if args.verbose:
            print(f"📄 内容预览:")
            print(structured_md[:300] + "..." if len(structured_md) > 300 else structured_md)
        
    except Exception as e:
        print(f"❌ 转换失败: {e}")

def generate_markdown_pair(args):
    """生成中英文Markdown文件对"""
    text = get_input_text(args)
    
    print(f"📄 正在生成文档对: {args.title}")
    print(f"🏷️ 文档主题: {args.subject}")
    if args.output:
        print(f"📁 输出目录: {args.output}")
    
    try:
        # 使用内部函数生成文档对
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
  文档转换: python main.py convert --title "文档标题" --text "内容"
  生成文档对: python main.py generate --title "标题" --subject "AI" --file input.txt --output docs/
        """
    )
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='选择操作命令')
    
    # 通用参数组（所有命令共享）
    input_group = argparse.ArgumentParser(add_help=False)
    input_group.add_argument('--text', '-t', help='直接输入文本内容')
    input_group.add_argument('--file', '-f', help='从文件读取内容')
    input_group.add_argument('--verbose', '-v', action='store_true', help='详细输出模式')
    input_group.add_argument('--quiet', '-q', action='store_true', help='静默模式')
    
    # summary 命令
    summary_parser = subparsers.add_parser('summary', help='提取文本摘要', parents=[input_group])
    summary_parser.add_argument('--max-words', '-w', type=int, default=5, help='摘要最大单词数')
    
    # convert 命令
    convert_parser = subparsers.add_parser('convert', help='转换为Markdown文档', parents=[input_group])
    convert_parser.add_argument('--title', required=True, help='文档标题')
    convert_parser.add_argument('--url', '-u', default='', help='原文URL')
    convert_parser.add_argument('--date', '-d', default='', help='发布日期')
    convert_parser.add_argument('--output', '-o', help='输出目录')
    
    # generate 命令
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
        elif args.command == 'convert':
            convert_to_markdown(args)
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