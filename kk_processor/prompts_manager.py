import os
from pathlib import Path
import json

class PromptsManager:
    def __init__(self, prompts_dir="prompts"):
        """初始化Prompt管理器"""
        self.prompts_dir = Path(prompts_dir)
        self.templates = {}
        self.template_metadata = {}  # 存储模板元数据
        self._load_all_templates()
    
    def _load_all_templates(self):
        """加载prompts目录下的所有模板文件"""
        # 确保prompts目录存在
        if not self.prompts_dir.exists():
            print(f"⚠️  Prompt目录不存在: {self.prompts_dir}")
            return
        
        # 加载所有.txt文件
        for file_path in self.prompts_dir.glob("*.txt"):
            try:
                template_name = file_path.stem  # 去掉扩展名的文件名
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    self.templates[template_name] = content
                
                # 尝试加载对应的元数据文件
                metadata_file = file_path.with_suffix('.json')
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as mf:
                        self.template_metadata[template_name] = json.load(mf)
                
                print(f"✅ 加载Prompt模板: {template_name}")
            except Exception as e:
                print(f"❌❌ 加载模板失败 {file_path}: {e}")
    
    def get_template(self, template_name):
        """获取指定名称的模板"""
        if template_name not in self.templates:
            available = list(self.templates.keys())
            raise ValueError(f"模板 '{template_name}' 不存在。可用模板: {available}")
        return self.templates[template_name]
    
    def get_template_with_params(self, template_name, **params):
        """获取模板并格式化参数"""
        template = self.get_template(template_name)
        try:
            return template.format(**params)
        except KeyError as e:
            raise ValueError(f"模板参数错误: {e}，模板需要的参数: {self._extract_template_params(template)}")
    
    def _extract_template_params(self, template):
        """提取模板中的参数名"""
        import re
        return re.findall(r'\{(\w+)\}', template)
    
    def list_templates(self):
        """列出所有可用的模板"""
        return list(self.templates.keys())
    
    def reload_templates(self):
        """重新加载所有模板"""
        self.templates.clear()
        self.template_metadata.clear()
        self._load_all_templates()
        print("🔄🔄 模板重新加载完成")
    
    def get_template_info(self):
        """获取模板信息"""
        info = {}
        for name, content in self.templates.items():
            info[name] = {
                'length': len(content),
                'lines': content.count('\n') + 1,
                'preview': content[:100] + '...' if len(content) > 100 else content,
                'params': self._extract_template_params(content),
                'metadata': self.template_metadata.get(name, {})
            }
        return info
    
    def create_template(self, template_name, content, metadata=None):
        """创建新模板"""
        template_file = self.prompts_dir / f"{template_name}.txt"
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if metadata:
            metadata_file = self.prompts_dir / f"{template_name}.json"
            with open(metadata_file, 'w', encoding='utf-8') as mf:
                json.dump(metadata, mf, ensure_ascii=False, indent=2)
        
        # 重新加载模板
        self.reload_templates()
        print(f"✅ 创建模板: {template_name}")

# 使用示例
if __name__ == "__main__":
    # 测试代码
    manager = PromptsManager()
    print("📋📋 可用模板:", manager.list_templates())
    
    if manager.templates:
        print("📊📊 模板信息:")
        for name, info in manager.get_template_info().items():
            print(f"  {name}: {info['length']}字符, {info['lines']}行, 参数: {info['params']}")