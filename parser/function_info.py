#!/usr/bin/env python3
"""
函数信息类 - 存储函数的基本信息
"""

from typing import List, Optional


class FunctionInfo:
    """函数信息类"""
    
    def __init__(self, name: str, return_type: str, parameters: List[str], 
                 start_line: int, end_line: int, file_path: str, 
                 is_declaration: bool = False, scope: str = ""):
        self.name = name
        self.return_type = return_type
        self.parameters = parameters
        self.start_line = start_line
        self.end_line = end_line
        self.file_path = file_path
        self.is_declaration = is_declaration
        self.scope = scope
        self._cached_body = None  # 缓存函数体内容
    
    def __str__(self):
        decl_type = "声明" if self.is_declaration else "定义"
        scope_info = f" [{self.scope}]" if self.scope else ""
        return f"{self.name}({', '.join(self.parameters)}) -> {self.return_type} ({decl_type}){scope_info}"
    
    def get_signature(self):
        """获取函数签名"""
        params = ', '.join(self.parameters) if self.parameters else ""
        scope_prefix = f"{self.scope}::" if self.scope else ""
        return f"{self.return_type} {scope_prefix}{self.name}({params})"
    
    def get_body(self, force_reload: bool = False) -> Optional[str]:
        """
        获取函数体内容
        
        Args:
            force_reload: 是否强制重新加载，忽略缓存
            
        Returns:
            函数体内容字符串，如果无法读取则返回None
        """
        if self._cached_body is not None and not force_reload:
            return self._cached_body
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 提取函数代码（注意：行号是1-based，列表索引是0-based）
            start_idx = max(0, self.start_line - 1)
            end_idx = min(len(lines), self.end_line)
            
            func_body = ''.join(lines[start_idx:end_idx]).rstrip()
            self._cached_body = func_body
            return func_body
            
        except Exception as e:
            return None
    
    def get_info_dict(self) -> dict:
        """获取函数信息的字典表示"""
        return {
            'name': self.name,
            'return_type': self.return_type,
            'parameters': self.parameters,
            'signature': self.get_signature(),
            'start_line': self.start_line,
            'end_line': self.end_line,
            'file_path': self.file_path,
            'is_declaration': self.is_declaration,
            'scope': self.scope,
            'type': '声明' if self.is_declaration else '定义'
        } 