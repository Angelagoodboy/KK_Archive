import re
import requests
from config import config
from prompts_manager import PromptsManager

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
            prompt = self.prompts.get_template("summary_prompt").format(
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