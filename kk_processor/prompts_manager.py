import os
from pathlib import Path
import json
import re
from typing import Dict, Set, Optional

class PromptsManager:
    def __init__(self, prompts_dir="prompts", enable_lazy_load=True):
        """
        简约版的Prompt管理器
        
        Args:
            prompts_dir: prompts目录路径
            enable_lazy_load: 是否启用懒加载模式
        """
        self.prompts_dir = Path(prompts_dir)
        self.enable_lazy_load = enable_lazy_load
        
        # 存储模板内容和元数据
        self.templates = {}
        self.template_metadata = {}
        
        # 使用统计
        self.usage_stats = {}
        self.loaded_templates: Set[str] = set()
        
        print(f"📁 Prompts目录: {self.prompts_dir}")
        
        # 根据模式选择初始化方式
        if enable_lazy_load:
            print("✅ 懒加载模式 - 模板将按需加载")
            self._validate_prompts_dir()
        else:
            print("🔄 预加载模式 - 加载所有模板")
            self._load_all_templates()
    
    def _validate_prompts_dir(self):
        """验证prompts目录是否存在"""
        if not self.prompts_dir.exists():
            print(f"❌ 目录不存在: {self.prompts_dir}")
            try:
                self.prompts_dir.mkdir(parents=True, exist_ok=True)
                print(f"✅ 已创建目录")
            except Exception as e:
                print(f"❌ 创建目录失败: {e}")
        else:
            txt_files = list(self.prompts_dir.glob("*.txt"))
            print(f"📋 发现 {len(txt_files)} 个模板文件")
    
    def _load_all_templates(self):
        """预加载模式：加载所有模板文件"""
        if not self.prompts_dir.exists():
            print(f"❌ 目录不存在: {self.prompts_dir}")
            return
        
        txt_files = list(self.prompts_dir.glob("*.txt"))
        if not txt_files:
            print("ℹ️ 目录中没有模板文件")
            return
        
        print(f"🔄 加载 {len(txt_files)} 个模板:")
        for file_path in txt_files:
            template_name = file_path.stem
            try:
                self._load_single_template(template_name)
                print(f"   ✅ {template_name}")
            except Exception as e:
                print(f"   ❌ {template_name} - 加载失败: {e}")
        
        print(f"✅ 加载完成: {len(self.templates)}/{len(txt_files)} 个模板")
    
    def _load_single_template(self, template_name: str) -> bool:
        """加载单个模板文件"""
        file_path = self.prompts_dir / f"{template_name}.txt"
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        try:
            # 读取模板内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                self.templates[template_name] = content
            
            # 加载元数据文件（如果有）
            metadata_file = file_path.with_suffix('.json')
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as mf:
                    self.template_metadata[template_name] = json.load(mf)
            
            self.loaded_templates.add(template_name)
            return True
            
        except Exception as e:
            raise ValueError(f"加载失败: {e}")
    
    def get_template(self, template_name: str) -> str:
        """
        获取指定名称的模板
        """
        # 懒加载模式：按需加载
        if self.enable_lazy_load and template_name not in self.templates:
            print(f"📥 懒加载: {template_name}")
            self._load_single_template(template_name)
        
        if template_name not in self.templates:
            available = self.list_available_templates()
            raise ValueError(f"模板 '{template_name}' 不存在。可用模板: {available}")
        
        # 记录使用统计
        self.usage_stats[template_name] = self.usage_stats.get(template_name, 0) + 1
        
        return self.templates[template_name]
    
    def get_template_with_params(self, template_name: str, **params) -> str:
        """
        获取模板并格式化参数
        """
        template = self.get_template(template_name)
        try:
            return template.format(**params)
        except KeyError as e:
            raise ValueError(f"参数错误: {e}，所需参数: {self._extract_template_params(template)}")
    
    def _extract_template_params(self, template: str) -> list:
        """提取模板中的参数名"""
        return re.findall(r'\{(\w+)\}', template)
    
    def list_available_templates(self) -> list:
        """列出目录中所有可用的模板名称"""
        if not self.prompts_dir.exists():
            return []
        return [f.stem for f in self.prompts_dir.glob("*.txt")]
    
    def list_loaded_templates(self) -> list:
        """列出当前已加载的模板名称"""
        loaded = list(self.templates.keys())
        print(f"📦 已加载 {len(loaded)} 个模板: {loaded}")
        return loaded
    
    def reload_templates(self, template_name: Optional[str] = None):
        """
        重新加载模板
        """
        if template_name:
            print(f"🔄 重新加载: {template_name}")
            if template_name in self.templates:
                del self.templates[template_name]
                if template_name in self.template_metadata:
                    del self.template_metadata[template_name]
                self.loaded_templates.discard(template_name)
            
            try:
                self._load_single_template(template_name)
            except Exception as e:
                print(f"❌ 重新加载失败: {e}")
        else:
            print("🔄 重新加载所有模板")
            if self.enable_lazy_load:
                loaded_names = list(self.templates.keys())
                self.templates.clear()
                self.template_metadata.clear()
                self.loaded_templates.clear()
                
                for name in loaded_names:
                    try:
                        self._load_single_template(name)
                    except Exception as e:
                        print(f"❌ {name} - 重新加载失败: {e}")
            else:
                self.templates.clear()
                self.template_metadata.clear()
                self.loaded_templates.clear()
                self._load_all_templates()
    
    def get_template_info(self, template_name: Optional[str] = None) -> Dict:
        """
        获取模板信息
        """
        if template_name:
            template = self.get_template(template_name)
            return {
                'name': template_name,
                'length': len(template),
                'lines': template.count('\n') + 1,
                'params': self._extract_template_params(template),
                'usage_count': self.usage_stats.get(template_name, 0),
            }
        else:
            info = {}
            for name, content in self.templates.items():
                info[name] = {
                    'length': len(content),
                    'lines': content.count('\n') + 1,
                    'params': self._extract_template_params(content),
                    'usage_count': self.usage_stats.get(name, 0),
                }
            return info
    
    def create_template(self, template_name: str, content: str, metadata: Optional[Dict] = None) -> bool:
        """
        创建新模板
        """
        try:
            self.prompts_dir.mkdir(parents=True, exist_ok=True)
            
            template_file = self.prompts_dir / f"{template_name}.txt"
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            if metadata:
                metadata_file = self.prompts_dir / f"{template_name}.json"
                with open(metadata_file, 'w', encoding='utf-8') as mf:
                    json.dump(metadata, mf, ensure_ascii=False, indent=2)
            
            if not self.enable_lazy_load:
                self._load_single_template(template_name)
            
            print(f"✅ 创建模板: {template_name}")
            return True
            
        except Exception as e:
            print(f"❌ 创建失败: {e}")
            return False
    
    def get_usage_statistics(self) -> Dict:
        """获取使用统计信息"""
        return {
            'total_templates': len(self.list_available_templates()),
            'loaded_templates': len(self.loaded_templates),
            'usage_stats': self.usage_stats,
        }

# 使用示例
if __name__ == "__main__":
    print("=== 测试简约版 ===")
    
    # 测试懒加载模式
    manager = PromptsManager(enable_lazy_load=True)
    
    # 查看可用模板
    available = manager.list_available_templates()
    print(f"📋 可用模板: {available}")
    
    if available:
        # 尝试获取模板（触发懒加载）
        try:
            template_name = available[0]
            content = manager.get_template(template_name)
            print(f"✅ 获取模板: {template_name}")
        except Exception as e:
            print(f"❌ 获取失败: {e}")
    
    # 查看已加载的模板
    manager.list_loaded_templates()
    
    # 查看统计
    stats = manager.get_usage_statistics()
    print(f"📊 统计: 总{stats['total_templates']}个, 已加载{stats['loaded_templates']}个")