import os
from pathlib import Path
from dotenv import load_dotenv

class Config:
    def __init__(self):
        load_dotenv()  # 加载.env文件
        
        # API配置
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.deepseek_api_url = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
        
        # 路径配置 - 使用绝对路径确保准确性
        current_dir = Path(__file__).parent.absolute()
        self.prompts_dir = current_dir / "prompts"
        
        # 验证配置
        self._validate_config()
    
    def _validate_config(self):
        """验证配置是否正确"""
        print("🔍 配置验证:")
        print(f"   项目目录: {Path(__file__).parent}")
        print(f"   Prompts目录: {self.prompts_dir}")
        print(f"   目录存在: {self.prompts_dir.exists()}")
        
        if self.prompts_dir.exists():
            print(f"   目录内容: {[f.name for f in self.prompts_dir.iterdir()]}")
        else:
            print("   ❌ Prompts目录不存在!")
        
        if not self.deepseek_api_key:
            print("   ⚠️  DEEPSEEK_API_KEY 未配置")

config = Config()