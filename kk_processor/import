import re
import requests
from config import config
from prompts_manager import PromptsManager
from typing import Dict, List, Optional

class DocumentProcessor:
    def __init__(self):
        self.prompts = PromptsManager(config.prompts_dir)
        self.api_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.deepseek_api_key}"
        }

    def extract_summary(self, text: str, max_words: int = 5) -> str:
        """使用DeepSeek API提取摘要"""
        if not text.strip():
            return ""
        
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
            return self._validate_summary(summary, max_words)
            
        except Exception as e:
            print(f"API调用失败: {e}")
            return self._fallback_summary(text, max_words)

    def generate_heading(self, text: str, max_words: int = 4) -> str:
        """生成标题（复用摘要功能）"""
        # 复用摘要功能来生成标题
        return self.extract_summary(text, max_words)

    def _validate_summary(self, text: str, max_words: int) -> str:
        """验证摘要格式"""
        text = re.sub(r'^["\']|["\']$', '', text.strip())
        words = text.split()[:max_words]
        return " ".join(words)

    def _fallback_summary(self, text: str, max_words: int) -> str:
        """备用摘要提取方法"""
        sentences = re.split(r'[.!?]+', text)
        first_sentence = sentences[0].strip() if sentences else ""
        return " ".join(first_sentence.split()[:max_words])

    def translate_text(self, text: str, source_lang: str = "auto", target_lang: str = "中文") -> str:
        """
        翻译文本（使用独立的prompt模板）
        """
        if not text.strip():
            return ""
        
        try:
            # 使用独立的翻译prompt模板
            prompt = self.prompts.get_template_with_params(
                "translation_prompt",
                text=text
            )
            
            # 使用独立的翻译系统提示词
            system_prompt = self.prompts.get_template("translation_system_prompt")
            
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
            return self._clean_translation_result(translated_text)
            
        except Exception as e:
            print(f"❌ 翻译API调用失败: {e}")
            return self._fallback_translation(text, target_lang)

    def _clean_translation_result(self, text: str) -> str:
        """清理翻译结果"""
        # 移除可能的引导文本
        patterns = [
            r'^翻译[：:]?\s*',
            r'^以下是翻译[：:]?\s*',
            r'^译文[：:]?\s*'
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text.strip())
        
        return text.strip()

    def _fallback_translation(self, text: str, target_lang: str) -> str:
        """备用翻译方法"""
        print(f"⚠️ 使用备用翻译方案 for {target_lang}")
        return f"[备用翻译] {text}"

    def batch_translate(self, texts: List[str], source_lang: str = "auto", 
                       target_lang: str = "中文", batch_size: int = 5) -> List[str]:
        """
        批量翻译文本
        """
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            print(f"🔄 翻译批次 {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
            
            for text in batch:
                try:
                    translated = self.translate_text(text, source_lang, target_lang)
                    results.append(translated)
                except Exception as e:
                    print(f"❌ 翻译失败: {e}")
                    results.append(f"[翻译失败] {text}")
            
            # 添加延迟避免API限制
            if i + batch_size < len(texts):
                import time
                time.sleep(1)
        
        return results