import re
import requests
import json
import time
from tqdm import tqdm
from config import config
from prompts_manager import PromptsManager
from typing import Dict, List, Optional

class DocumentProcessor:
    def __init__(self, show_progress: bool = True):
        """
        文档处理器 - 完整修正版本
        """
        self.prompts = PromptsManager(config.prompts_dir)
        self.api_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.deepseek_api_key}"
        }
        self.show_progress = show_progress
        self._preload_translation_prompts()

    def _preload_translation_prompts(self):
        """静默预加载翻译相关的prompts"""
        try:
            # 临时禁用verbose
            original_verbose = getattr(self.prompts, 'verbose', True)
            self.prompts.verbose = False
            
            # 预加载模板
            self.prompts.get_template("translation_prompt")
            self.prompts.get_template("translation_system_prompt")
            self.prompts.get_template("summary_prompt")
            self.prompts.get_template("system_prompt")
            
            # 恢复原始设置
            self.prompts.verbose = original_verbose
        except Exception:
            pass

    def _estimate_translated_length(self, english_text: str) -> int:
        """
        修正预估逻辑：英文->中文翻译后字符数通常减少
        """
        if not english_text.strip():
            return 0
        
        original_length = len(english_text)
        
        # 修正：英文->中文翻译后字符数通常减少
        # 经验值：0.3-0.8倍，取中间值0.5
        base_ratio = 0.5
        
        # 根据文本特征微调比例
        ratio = self._adjust_ratio_by_text_features(english_text, base_ratio)
        
        # 计算预估长度（至少保留一定长度）
        estimated_length = max(100, int(original_length * ratio))
        
        return estimated_length

    def _adjust_ratio_by_text_features(self, text: str, base_ratio: float) -> float:
        """
        根据文本特征微调比例（修正版）
        """
        ratio = base_ratio
        
        # 分析文本特征
        words = re.findall(r'\b[a-zA-Z]+\b', text)
        total_chars = len(text)
        
        if words and total_chars > 0:
            # 计算单词密度（单词数/总字符数）
            word_density = len(words) / total_chars
            
            # 计算平均单词长度
            avg_word_len = sum(len(word) for word in words) / len(words)
            
            # 特征1：单词密度高（说明空格多），翻译后比例更低
            if word_density > 0.15:  # 高单词密度
                ratio -= 0.1
            
            # 特征2：长单词多（技术术语），翻译后比例可能略高
            if avg_word_len > 7:  # 长单词多为技术术语
                ratio += 0.1
        
        # 特征3：数字和符号多的文本，翻译后比例较高
        digit_symbol_ratio = len(re.findall(r'[0-9@#$%&*+=<>]', text)) / total_chars if total_chars > 0 else 0
        if digit_symbol_ratio > 0.2:
            ratio += 0.2
        
        # 确保比例在合理范围内
        ratio = max(0.3, min(ratio, 0.8))  # 限制在 0.3-0.8 倍之间
        
        return ratio

    def translate_text(self, text: str, source_lang: str = "auto", target_lang: str = "中文") -> str:
        """
        翻译文本 - 流式API真实进度条版本
        """
        if not text.strip():
            return ""

        original_length = len(text)
        
        if self.show_progress:
            print(f"🌐 开始翻译: {original_length} 字符")

        # 准备prompt
        try:
            prompt = self.prompts.get_template_with_params(
                "translation_prompt",
                text=text
            )
            system_prompt = self.prompts.get_template("translation_system_prompt")
        except Exception as e:
            if self.show_progress:
                print(f"❌ 准备翻译模板失败: {e}")
            return f"[翻译失败] {text}"

        # 使用流式API
        return self._translate_with_streaming_api(text, prompt, system_prompt, original_length)

    def _translate_with_streaming_api(self, text: str, prompt: str, system_prompt: str, original_length: int) -> str:
        """使用流式API和真实进度条"""
        progress_bar = None
        start_time = time.time()
        
        # 修正预估长度
        estimated_length = self._estimate_translated_length(text)
        
        if self.show_progress:
            print(f"📊 预估翻译: {original_length} 英文字符 -> ~{estimated_length} 中文字符")
            print("💡 注意: 英文->中文翻译后字符数通常减少")
            
            # 创建进度条
            progress_bar = tqdm(
                total=estimated_length,
                desc="接收翻译内容",
                ncols=70,
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} 字符',
                unit='char'
            )

        try:
            # 发送流式API请求
            response = requests.post(
                config.deepseek_api_url,
                headers=self.api_headers,
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 8000,
                    "stream": True
                },
                timeout=120,
                stream=True
            )

            response.raise_for_status()

            translated_parts = []
            received_chars = 0
            chunk_count = 0
            last_update_time = time.time()

            # 处理流式响应
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8').strip()
                    
                    if not line_str:
                        continue
                    
                    if line_str == 'data: [DONE]':
                        if self.show_progress:
                            print("📨 接收到结束标记 [DONE]")
                        break
                    
                    if line_str.startswith('data: '):
                        chunk_count += 1
                        try:
                            json_data = json.loads(line_str[6:])
                            
                            if 'choices' in json_data and json_data['choices']:
                                choice = json_data['choices'][0]
                                
                                # 检查是否结束
                                if choice.get('finish_reason') is not None:
                                    if self.show_progress:
                                        print(f"🏁 翻译完成，原因: {choice['finish_reason']}")
                                    break
                                
                                # 获取内容
                                if 'delta' in choice and 'content' in choice['delta']:
                                    content = choice['delta']['content']
                                    if content:
                                        translated_parts.append(content)
                                        received_chars += len(content)
                                        
                                        # 实时更新进度条
                                        if progress_bar:
                                            # 动态调整进度条上限
                                            if received_chars > progress_bar.total:
                                                progress_bar.total = received_chars + 100
                                                progress_bar.refresh()
                                            progress_bar.update(len(content))
                                        
                                        # 计算实时速度
                                        current_time = time.time()
                                        if current_time - last_update_time > 1.0:
                                            elapsed = current_time - start_time
                                            speed = received_chars / elapsed if elapsed > 0 else 0
                                            if progress_bar:
                                                progress_bar.set_postfix(speed=f"{speed:.1f} char/s")
                                            last_update_time = current_time
                                        
                        except (json.JSONDecodeError, KeyError) as e:
                            continue

            # 完成进度条
            if progress_bar:
                progress_bar.close()

            translated_text = ''.join(translated_parts)
            
            # 检查结果是否为空
            if not translated_text.strip():
                if self.show_progress:
                    print("❌ 翻译结果为空，尝试备用方案")
                return self._fallback_translate_text(text, prompt, system_prompt)
            
            cleaned_text = self._clean_translation_result(translated_text)

            # 计算统计信息
            elapsed_time = time.time() - start_time
            actual_ratio = len(cleaned_text) / original_length if original_length > 0 else 0
            avg_speed = len(cleaned_text) / elapsed_time if elapsed_time > 0 else 0
            
            # 计算无空格比例
            original_no_spaces = len(re.sub(r'\s+', '', text))
            translated_no_spaces = len(re.sub(r'\s+', '', cleaned_text))
            ratio_no_spaces = translated_no_spaces / original_no_spaces if original_no_spaces > 0 else 0

            if self.show_progress:
                print(f"✅ 翻译完成!")
                print(f"📊 原文: {original_length} 字符")
                print(f"📊 译文: {len(cleaned_text)} 字符")
                print(f"📈 实际比例: {actual_ratio:.2f}x")
                print(f"📈 无空格比例: {ratio_no_spaces:.2f}x")
                print(f"⏱️  耗时: {elapsed_time:.1f}秒")
                print(f"🚀 速度: {avg_speed:.1f}字符/秒")
                print(f"📦 数据块: {chunk_count} 个")
                
                # 给出解释
                if actual_ratio < 0.6:
                    print("💡 比例较低是正常的：英文空格多，中文表达更简洁")

            return cleaned_text

        except Exception as e:
            if progress_bar:
                progress_bar.close()
            if self.show_progress:
                print(f"❌ 流式翻译失败: {e}")
            return self._fallback_translate_text(text, prompt, system_prompt)

    def _fallback_translate_text(self, text: str, prompt: str, system_prompt: str) -> str:
        """备用翻译方案（非流式）"""
        if self.show_progress:
            print("🔄 使用备用翻译方案")

        try:
            # 创建简单的进度动画
            if self.show_progress:
                fallback_bar = tqdm(
                    total=100,
                    desc="备用翻译",
                    ncols=50,
                    bar_format='{l_bar}{bar}| {n_fmt}%'
                )
                
                # 模拟进度
                for i in range(0, 100, 20):
                    time.sleep(0.3)
                    fallback_bar.update(20)
                
                fallback_bar.close()

            response = requests.post(
                config.deepseek_api_url,
                headers=self.api_headers,
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 8000
                },
                timeout=60
            )

            response.raise_for_status()
            translated_text = response.json()["choices"][0]["message"]["content"]
            cleaned_text = self._clean_translation_result(translated_text)

            if self.show_progress:
                actual_ratio = len(cleaned_text) / len(text) if len(text) > 0 else 0
                print(f"✅ 备用翻译完成: {len(cleaned_text)} 字符 (比例: {actual_ratio:.2f}x)")

            return cleaned_text

        except Exception as e:
            if self.show_progress:
                print(f"❌ 备用翻译也失败: {e}")
            return f"[翻译失败] {text}"

    def batch_translate(self, texts: List[str], source_lang: str = "auto", 
                       target_lang: str = "中文", batch_size: int = 2) -> List[str]:
        """
        批量翻译
        """
        if not texts:
            return []

        total_texts = len(texts)
        
        if self.show_progress:
            print(f"🔄 开始批量翻译 {total_texts} 个文本")
            total_chars = sum(len(text) for text in texts)
            print(f"📊 总字符数: {total_chars}")

        results = []
        successful_count = 0

        for i, text in enumerate(texts, 1):
            if self.show_progress:
                print(f"\n--- 处理第 {i}/{total_texts} 个文本 ---")
                print(f"📝 原文长度: {len(text)} 字符")

            try:
                result = self.translate_text(text, source_lang, target_lang)
                results.append(result)
                successful_count += 1

                if self.show_progress:
                    print(f"✅ 第 {i} 个文本完成")

            except Exception as e:
                if self.show_progress:
                    print(f"❌ 第 {i} 个文本翻译失败: {e}")
                results.append(f"[翻译失败] {text}")

            # 延迟避免API限制
            if i < total_texts:
                time.sleep(1)

        if self.show_progress:
            print(f"\n🎉 批量翻译完成: {successful_count}/{total_texts} 成功")

        return results

    def translate_large_document(self, text: str, chunk_size: int = 2000, 
                                target_lang: str = "中文") -> str:
        """
        大文档翻译
        """
        if not text.strip():
            return ""

        chunks = self._split_text_by_paragraphs(text, chunk_size)
        total_chunks = len(chunks)

        if self.show_progress:
            print(f"📄 大文档翻译: {len(text)} 字符 -> {total_chunks} 个块")

        if total_chunks == 1:
            return self.translate_text(text, "auto", target_lang)

        translated_chunks = []
        successful_chunks = 0

        for i, chunk in enumerate(chunks, 1):
            if self.show_progress:
                print(f"\n--- 翻译块 {i}/{total_chunks} ---")
                print(f"🔤 块长度: {len(chunk)} 字符")

            try:
                translated_chunk = self.translate_text(chunk, "auto", target_lang)
                translated_chunks.append(translated_chunk)
                successful_chunks += 1

                if self.show_progress:
                    print(f"✅ 块 {i} 完成")

            except Exception as e:
                if self.show_progress:
                    print(f"❌ 块 {i} 翻译失败: {e}")
                translated_chunks.append(f"[翻译失败: 块{i}]")

            # 块间延迟
            if i < total_chunks:
                time.sleep(1)

        result = "\n\n".join(translated_chunks)
        
        if self.show_progress:
            print(f"\n🎉 大文档翻译完成: {successful_chunks}/{total_chunks} 块成功")

        return result

    def extract_summary(self, text: str, max_words: int = 5) -> str:
        """
        提取摘要
        """
        if not text.strip():
            return ""

        if self.show_progress:
            print(f"📝 提取摘要: {max_words} 单词")

        try:
            prompt = self.prompts.get_template_with_params(
                "summary_prompt",
                max_words=max_words,
                paragraph=text
            )
            
            response = requests.post(
                config.deepseek_api_url,
                headers=self.api_headers,
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": self.prompts.get_template("system_prompt")},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3
                },
                timeout=30
            )
            response.raise_for_status()
            
            summary = response.json()["choices"][0]["message"]["content"]
            cleaned_summary = self._validate_summary(summary, max_words)
            
            if self.show_progress:
                print(f"✅ 摘要提取完成: {len(cleaned_summary)} 字符")
            
            return cleaned_summary
            
        except Exception as e:
            if self.show_progress:
                print(f"❌ 摘要提取失败: {e}")
            return self._fallback_summary(text, max_words)

    def generate_heading(self, text: str, max_words: int = 4) -> str:
        """
        生成标题
        """
        if self.show_progress:
            print(f"🏷️ 生成标题: {max_words} 单词")
        
        return self.extract_summary(text, max_words)

    def _split_text_by_paragraphs(self, text: str, max_chunk_size: int) -> List[str]:
        """按段落分割文本"""
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) <= max_chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = paragraph
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

    def _clean_translation_result(self, text: str) -> str:
        """清理翻译结果"""
        patterns = [
            r'^翻译[：:]?\s*',
            r'^以下是翻译[：:]?\s*',
            r'^译文[：:]?\s*'
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text.strip())
        
        return text.strip()

    def _validate_summary(self, text: str, max_words: int) -> str:
        """验证摘要格式"""
        text = re.sub(r'^["\']|["\']$', '', text.strip())
        words = text.split()[:max_words]
        return " ".join(words)

    def _fallback_summary(self, text: str, max_words: int) -> str:
        """备用摘要提取方法"""
        sentences = re.split(r'[.!?]+', text)
        first_sentence = sentences[0].strip() if sentences else ""
        words = first_sentence.split()[:max_words]
        return " ".join(words)

# 测试代码
if __name__ == "__main__":
    # 测试翻译功能
    processor = DocumentProcessor(show_progress=True)
    
    test_text = "This is a test document for translation. It contains some sample content to demonstrate the translation functionality."
    
    print("=== 测试单个翻译 ===")
    result = processor.translate_text(test_text)
    print(f"翻译结果: {result}")
    
    print("\n=== 测试批量翻译 ===")
    test_texts = [
        "Hello world",
        "This is the first sample text",
        "Artificial intelligence is transforming various industries"
    ]
    results = processor.batch_translate(test_texts)
    for i, (original, translated) in enumerate(zip(test_texts, results)):
        print(f"{i+1}. 原文: {original}")
        print(f"   翻译: {translated}")
    
    print("\n=== 测试摘要提取 ===")
    summary = processor.extract_summary(test_text, max_words=8)
    print(f"摘要: {summary}")
    
    print("\n=== 测试标题生成 ===")
    heading = processor.generate_heading(test_text, max_words=4)
    print(f"标题: {heading}")