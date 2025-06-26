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
        
        # Call Graph相关信息
        self.callees = set()  # 直接调用的函数名集合
        self._parsed_calls = False  # 是否已解析过函数调用
        
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
    
    def parse_function_calls(self):
        """解析函数体中的函数调用"""
        if self._parsed_calls or self.is_declaration:
            return
        
        import re
        
        body = self.get_body()
        if not body:
            self._parsed_calls = True
            return
        
        # 函数调用的正则表达式
        # 匹配形如 function_name( 的模式，但排除一些常见的非函数调用情况
        function_call_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        
        # 需要排除的关键字
        exclude_keywords = {
            'if', 'while', 'for', 'switch', 'sizeof', 'typeof', 
            'struct', 'union', 'enum', 'return', 'const', 'static',
            'extern', 'inline', 'volatile', 'typedef'
        }
        
        lines = body.split('\n')
        for line in lines:
            # 清理行内容
            line = line.strip()
            
            # 跳过空行、注释和预处理指令
            if not line or line.startswith('//') or line.startswith('#'):
                continue
            
            # 简单处理块注释（单行内的）
            if '/*' in line and '*/' in line:
                # 移除注释部分
                comment_start = line.find('/*')
                comment_end = line.find('*/', comment_start)
                if comment_end != -1:
                    line = line[:comment_start] + line[comment_end + 2:]
                else:
                    continue
            elif '/*' in line:
                # 块注释开始，跳过这行
                continue
            elif '*/' in line:
                # 块注释结束，跳过这行
                continue
            
            # 查找函数调用
            matches = re.finditer(function_call_pattern, line)
            for match in matches:
                func_name = match.group(1)
                
                # 排除关键字
                if func_name.lower() in exclude_keywords:
                    continue
                
                # 排除自己调用自己（递归调用的情况）
                if func_name != self.name:
                    self.callees.add(func_name)
        
        self._parsed_calls = True
    
    def get_callees(self) -> set:
        """获取直接调用的函数列表"""
        if not self._parsed_calls:
            self.parse_function_calls()
        return self.callees.copy()
    
    def add_callee(self, func_name: str):
        """手动添加被调用的函数"""
        self.callees.add(func_name)
    
    def has_callee(self, func_name: str) -> bool:
        """检查是否调用了指定函数"""
        if not self._parsed_calls:
            self.parse_function_calls()
        return func_name in self.callees
    
    def clear_call_cache(self):
        """清除函数调用解析缓存，强制重新解析"""
        self._parsed_calls = False
        self.callees.clear()
    
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
    
    def get_detailed_info_dict(self) -> dict:
        """
        获取详细信息字典，用于外部显示
        
        Returns:
            包含所有详细信息的字典
        """
        func_type = "🔧 函数定义" if not self.is_declaration else "🔗 函数声明"
        
        # 基本信息
        info = {
            'type': func_type,
            'name': self.name,
            'file_path': self.file_path,
            'start_line': self.start_line,
            'end_line': self.end_line,
            'scope': self.scope,
            'return_type': {
                'signature': self.return_type_details.get_type_signature(),
                'is_pointer': self.return_type_details.is_actually_pointer(),
                'pointer_analysis': self.return_type_details.get_pointer_analysis() if self.return_type_details.is_actually_pointer() else None,
                'is_const': self.return_type_details.is_const,
                'type_chain': self.return_type_details.get_type_chain()
            },
            'parameters': [],
            'parameter_summary': self.get_parameter_summary()
        }
        
        # 参数详细信息
        if self.parameter_details:
            for i, param in enumerate(self.parameter_details, 1):
                param_info = {
                    'index': i,
                    'signature': param.get_full_signature(),
                    'name': param.name,
                    'type': param.param_type,
                    'is_pointer': param.is_actually_pointer(),
                    'pointer_analysis': param.get_pointer_analysis() if param.is_actually_pointer() else None,
                    'is_const': param.is_const,
                    'is_reference': param.is_reference,
                    'is_basic_type': param.is_basic_type(),
                    'type_chain': param.get_type_chain()
                }
                info['parameters'].append(param_info)
        
        return info  