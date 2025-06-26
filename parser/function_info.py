#!/usr/bin/env python3
"""
函数信息类 - 存储函数的基本信息
"""

from typing import List, Optional
from .param_ret_info import ParameterInfo, ReturnTypeInfo
from .type_registry import TypeRegistry


class FunctionInfo:
    """函数信息类"""
    
    def __init__(self, name: str, return_type: str, parameters: List[str], 
                 start_line: int, end_line: int, file_path: str, 
                 is_declaration: bool = False, scope: str = "",
                 parameter_details: List[ParameterInfo] = None,
                 return_type_details: ReturnTypeInfo = None,
                 type_registry: TypeRegistry = None):
        self.name = name
        self.return_type = return_type  # 保持向后兼容的简单字符串
        self.parameters = parameters    # 保持向后兼容的简单字符串列表
        self.start_line = start_line
        self.end_line = end_line
        self.file_path = file_path
        self.is_declaration = is_declaration
        self.scope = scope
        self._cached_body = None  # 缓存函数体内容
        self.type_registry = type_registry  # 类型注册表
        
        # 新增：详细的参数和返回类型信息
        self.parameter_details = parameter_details if parameter_details is not None else []
        self.return_type_details = return_type_details if return_type_details is not None else ReturnTypeInfo(return_type, type_registry)
        
        # 如果没有提供详细信息，自动解析
        if not self.parameter_details and self.parameters:
            self._parse_parameter_details()
    
    def _parse_parameter_details(self):
        """解析参数详细信息"""
        self.parameter_details = []
        for param_str in self.parameters:
            if param_str and param_str.strip() and param_str.strip() != "void":
                param_info = ParameterInfo(param_str, type_registry=self.type_registry)
                # 只添加有效的参数（非空参数）
                if param_info.param_type or param_info.name:
                    self.parameter_details.append(param_info)
    
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
    
    def get_parameter_summary(self) -> dict:
        """获取参数摘要信息"""
        summary = {
            'total_params': len(self.parameter_details),
            'pointer_params': 0,
            'const_params': 0,
            'reference_params': 0,
            'basic_type_params': 0,
            'custom_type_params': 0
        }
        
        for param in self.parameter_details:
            if param.is_actually_pointer():
                summary['pointer_params'] += 1
            if param.is_const:
                summary['const_params'] += 1
            if param.is_reference:
                summary['reference_params'] += 1
            if param.is_basic_type():
                summary['basic_type_params'] += 1
            else:
                summary['custom_type_params'] += 1
        
        return summary
    
    def get_detailed_signature(self) -> str:
        """获取详细的函数签名（包含类型修饰符）"""
        if not self.parameter_details:
            return self.get_signature()
        
        detailed_params = []
        for param in self.parameter_details:
            detailed_params.append(param.get_full_signature())
        
        params_str = ', '.join(detailed_params) if detailed_params else ""
        return_sig = self.return_type_details.get_type_signature()
        scope_prefix = f"{self.scope}::" if self.scope else ""
        
        return f"{return_sig} {scope_prefix}{self.name}({params_str})"
    
    def get_parameters_by_type(self, type_filter: str = "all") -> List[ParameterInfo]:
        """
        根据类型过滤参数
        
        Args:
            type_filter: 过滤类型 - "pointer", "const", "reference", "basic", "custom", "all"
        """
        if type_filter == "all":
            return self.parameter_details
        elif type_filter == "pointer":
            return [p for p in self.parameter_details if p.is_actually_pointer()]
        elif type_filter == "const":
            return [p for p in self.parameter_details if p.is_const]
        elif type_filter == "reference":
            return [p for p in self.parameter_details if p.is_reference]
        elif type_filter == "basic":
            return [p for p in self.parameter_details if p.is_basic_type()]
        elif type_filter == "custom":
            return [p for p in self.parameter_details if not p.is_basic_type()]
        else:
            return []
    
    def has_pointer_params(self) -> bool:
        """检查是否有指针参数"""
        return any(param.is_actually_pointer() for param in self.parameter_details)
    
    def has_const_params(self) -> bool:
        """检查是否有const参数"""
        return any(param.is_const for param in self.parameter_details)
    
    def has_pointer_return(self) -> bool:
        """检查返回值是否是指针"""
        return self.return_type_details.is_actually_pointer() if self.return_type_details else False
    
    def get_info_dict(self) -> dict:
        """获取函数信息的字典表示"""
        basic_info = {
            'name': self.name,
            'return_type': self.return_type,
            'parameters': self.parameters,
            'signature': self.get_signature(),
            'detailed_signature': self.get_detailed_signature(),
            'start_line': self.start_line,
            'end_line': self.end_line,
            'file_path': self.file_path,
            'is_declaration': self.is_declaration,
            'scope': self.scope,
            'type': '声明' if self.is_declaration else '定义'
        }
        
        # 添加详细的类型信息
        basic_info.update({
            'return_type_details': self.return_type_details.to_dict(),
            'parameter_details': [param.to_dict() for param in self.parameter_details],
            'parameter_summary': self.get_parameter_summary(),
            'has_pointer_params': self.has_pointer_params(),
            'has_const_params': self.has_const_params(),
            'has_pointer_return': self.has_pointer_return()
        })
        
        return basic_info
    
    def print_detailed_info(self):
        """打印详细的函数信息"""
        func_type = "🔧 函数定义" if not self.is_declaration else "🔗 函数声明"
        print(f"{func_type}: {self.name}")
        print(f"📁 位置: {self.file_path}:{self.start_line}-{self.end_line}")
        if self.scope:
            print(f"📂 作用域: {self.scope}")
        
        # 返回类型信息
        print(f"↩️  返回类型: {self.return_type_details.get_type_signature()}")
        if self.return_type_details.is_actually_pointer():
            print(f"   └─ {self.return_type_details.get_pointer_analysis()}")
        if self.return_type_details.is_const:
            print(f"   └─ const修饰")
        
        # 参数信息
        if self.parameter_details:
            print(f"📋 参数列表 ({len(self.parameter_details)} 个):")
            for i, param in enumerate(self.parameter_details, 1):
                print(f"   {i}. {param.get_full_signature()}")
                details = []
                if param.is_actually_pointer():
                    details.append(param.get_pointer_analysis())
                if param.is_const:
                    details.append("const")
                if param.is_reference:
                    details.append("引用")
                if param.is_basic_type():
                    details.append("基本类型")
                else:
                    details.append("自定义类型")
                
                # 类型链信息
                type_chain = param.get_type_chain()
                if len(type_chain) > 1:
                    details.append(f"类型链: {' → '.join(type_chain)}")
                
                if details:
                    print(f"      └─ {', '.join(details)}")
        else:
            print("📋 参数列表: 无参数")
        
        # 参数摘要
        summary = self.get_parameter_summary()
        if summary['total_params'] > 0:
            print(f"📊 参数摘要: 指针参数:{summary['pointer_params']}, const参数:{summary['const_params']}, 基本类型:{summary['basic_type_params']}")  