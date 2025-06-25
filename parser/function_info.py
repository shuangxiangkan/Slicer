#!/usr/bin/env python3
"""
函数信息类 - 存储函数的基本信息
"""

from typing import List


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
    
    def __str__(self):
        decl_type = "声明" if self.is_declaration else "定义"
        scope_info = f" [{self.scope}]" if self.scope else ""
        return f"{self.name}({', '.join(self.parameters)}) -> {self.return_type} ({decl_type}){scope_info}"
    
    def get_signature(self):
        """获取函数签名"""
        params = ', '.join(self.parameters) if self.parameters else ""
        scope_prefix = f"{self.scope}::" if self.scope else ""
        return f"{self.return_type} {scope_prefix}{self.name}({params})" 