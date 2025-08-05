#!/usr/bin/env python3
"""
函数信息类 - 存储函数的基本信息
"""

from typing import List, Optional
from .param_ret_info import ParameterInfo, ReturnTypeInfo
from .type_registry import TypeRegistry
import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser
import logging
import re


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
        
        # API相关信息
        self._api_keywords_cache = {}  # 缓存API关键字检查结果: {keyword: bool}
        
        # 注释相关信息
        self.comments = ""  # 函数注释内容
        self._cached_comments = None  # 缓存注释内容
        
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
        """解析函数体中的函数调用 - 使用tree-sitter进行精确解析"""
        if self._parsed_calls or self.is_declaration:
            return
        
        body = self.get_body()
        if not body:
            self._parsed_calls = True
            return
        
        try:
            # 导入tree-sitter相关模块
            
            # 判断是否为C++文件
            is_cpp = any(self.file_path.endswith(ext) for ext in ['.cpp', '.cxx', '.cc', '.hpp', '.hxx', '.hh'])
            
            # 初始化解析器
            if is_cpp:
                language = Language(tscpp.language(), "cpp")
            else:
                language = Language(tsc.language(), "c")
            
            parser = Parser()
            parser.set_language(language)
            
            # 解析函数体
            tree = parser.parse(body.encode('utf-8'))
            root_node = tree.root_node
            
            # 递归查找函数调用
            self._find_function_calls_recursive(root_node)
            
        except Exception as e:
            # 如果tree-sitter解析失败，回退到正则表达式方法
            logger = logging.getLogger(__name__)
            logger.warning(f"tree-sitter解析失败，回退到正则表达式方法: {e}")
            self._parse_function_calls_regex()
        
        self._parsed_calls = True
    
    def _find_function_calls_recursive(self, node):
        """递归查找函数调用节点"""
        # 检查当前节点是否为函数调用
        if node.type == 'call_expression':
            # 获取函数名
            function_node = node.child_by_field_name('function')
            if function_node:
                func_name = self._extract_function_name(function_node)
                if func_name and func_name != self.name:  # 排除递归调用
                    # 过滤常见的宏调用
                    if not self._is_likely_macro(func_name):
                        self.callees.add(func_name)
        
        # 递归处理子节点
        for child in node.children:
            self._find_function_calls_recursive(child)
    
    def _extract_function_name(self, function_node) -> str:
        """从函数调用节点中提取函数名"""
        try:
            if function_node.type == 'identifier':
                # 简单的函数调用: func_name()
                return function_node.text.decode('utf-8').strip()
            elif function_node.type == 'field_expression':
                # 成员函数调用: obj.func_name() 或 obj->func_name()
                field_node = function_node.child_by_field_name('field')
                if field_node and field_node.type == 'field_identifier':
                    return field_node.text.decode('utf-8').strip()
            elif function_node.type == 'subscript_expression':
                # 可能是函数指针调用，暂时跳过
                return None
            elif function_node.type == 'parenthesized_expression':
                # 括号包围的表达式，递归提取
                inner_node = function_node.children[1] if len(function_node.children) > 1 else None
                if inner_node:
                    return self._extract_function_name(inner_node)
            elif function_node.type == 'cast_expression':
                # 类型转换，不是函数调用
                return None
            
            # 对于其他未知类型，尝试提取文本并进行基本验证
            func_text = function_node.text.decode('utf-8').strip()
            
            # 基本验证：应该是有效的标识符
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', func_text):
                return func_text
            
            return None
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"提取函数名时出错: {e}")
            return None
    
    def _parse_function_calls_regex(self):
        """回退的正则表达式方法（保留原有逻辑作为备用）"""
        
        body = self.get_body()
        if not body:
            return
        
        # 函数调用的正则表达式
        function_call_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        
        # 需要排除的关键字（扩展列表，包含常见宏）
        exclude_keywords = {
            'if', 'while', 'for', 'switch', 'sizeof', 'typeof', 
            'struct', 'union', 'enum', 'return', 'const', 'static',
            'extern', 'inline', 'volatile', 'typedef',
            # 添加常见的宏
            'CJSON_PUBLIC', 'API', 'EXPORT', 'INLINE', 'FORCEINLINE',
            'CALLBACK', 'WINAPI', 'STDCALL', 'CDECL', 'FASTCALL'
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
                
                # 排除关键字和宏
                if func_name in exclude_keywords:
                    continue
                
                # 排除自己调用自己（递归调用的情况）
                if func_name != self.name:
                    self.callees.add(func_name)
    
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
    
    def get_comments(self, force_reload: bool = False, max_lines_above: int = 20) -> str:
        """
        获取函数注释内容
        
        Args:
            force_reload: 是否强制重新加载，忽略缓存
            max_lines_above: 向上搜索注释的最大行数
            
        Returns:
            函数注释字符串，如果无法读取或没有注释则返回空字符串
        """
        if self._cached_comments is not None and not force_reload:
            return self._cached_comments
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 从函数开始行向上搜索注释
            start_idx = max(0, self.start_line - 1)  # 转换为0-based索引
            search_start = max(0, start_idx - max_lines_above)
            
            comments = []
            in_block_comment = False
            block_comment_lines = []
            
            # 从搜索起始位置到函数开始位置，向上搜索注释
            for i in range(start_idx - 1, search_start - 1, -1):
                if i < 0 or i >= len(lines):
                    continue
                    
                line = lines[i].rstrip()
                stripped_line = line.strip()
                
                # 跳过空行（在注释块中间允许空行）
                if not stripped_line:
                    if comments or in_block_comment:
                        comments.insert(0, "")
                    continue
                
                # 处理单行注释
                if stripped_line.startswith('//'):
                    comment_text = stripped_line[2:].strip()
                    comments.insert(0, comment_text)
                    continue
                
                # 处理块注释结束
                if '*/' in stripped_line and not in_block_comment:
                    in_block_comment = True
                    block_comment_lines = []
                    
                    # 处理单行的块注释
                    if '/*' in stripped_line:
                        start_pos = stripped_line.find('/*')
                        end_pos = stripped_line.find('*/')
                        if start_pos < end_pos:
                            comment_text = stripped_line[start_pos + 2:end_pos].strip()
                            if comment_text:
                                comments.insert(0, comment_text)
                            in_block_comment = False
                            continue
                    
                    # 多行块注释的结束行
                    if stripped_line.endswith('*/'):
                        comment_part = stripped_line[:-2].strip()
                        if comment_part.startswith('*'):
                            comment_part = comment_part[1:].strip()
                        if comment_part:
                            block_comment_lines.insert(0, comment_part)
                        continue
                
                # 处理块注释内容
                if in_block_comment:
                    comment_line = stripped_line
                    if comment_line.startswith('*'):
                        comment_line = comment_line[1:].strip()
                    if comment_line or block_comment_lines:  # 保留非空行或已有内容时的空行
                        block_comment_lines.insert(0, comment_line)
                    
                    # 检查是否是块注释开始
                    if '/*' in line:
                        start_pos = line.find('/*')
                        before_comment = line[:start_pos].strip()
                        # 如果/*前面还有其他内容（非空白），则停止搜索
                        if before_comment:
                            break
                        
                        comment_start = line[start_pos + 2:].strip()
                        if comment_start.startswith('*'):
                            comment_start = comment_start[1:].strip()
                        if comment_start:
                            block_comment_lines.insert(0, comment_start)
                        
                        # 块注释搜集完成
                        comments = block_comment_lines + comments
                        in_block_comment = False
                        block_comment_lines = []
                        continue
                else:
                    # 遇到非注释行，停止搜索
                    break
            
            # 处理未完成的块注释（从文件开头开始的块注释）
            if in_block_comment and block_comment_lines:
                comments = block_comment_lines + comments
            
            # 清理注释内容
            cleaned_comments = []
            for comment in comments:
                cleaned_comment = comment.strip()
                if cleaned_comment:
                    cleaned_comments.append(cleaned_comment)
            
            comment_text = '\n'.join(cleaned_comments) if cleaned_comments else ""
            self._cached_comments = comment_text
            return comment_text
            
        except Exception as e:
            self._cached_comments = ""
            return ""
    
    def has_comments(self) -> bool:
        """检查函数是否有注释"""
        return bool(self.get_comments().strip())
    
    def get_comment_summary(self) -> dict:
        """获取注释摘要信息"""
        comments = self.get_comments()
        if not comments:
            return {
                'has_comments': False,
                'total_lines': 0,
                'non_empty_lines': 0,
                'comment_length': 0
            }
        
        lines = comments.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        return {
            'has_comments': True,
            'total_lines': len(lines),
            'non_empty_lines': len(non_empty_lines),
            'comment_length': len(comments),
            'preview': comments[:100] + '...' if len(comments) > 100 else comments
        }
    
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
            'has_pointer_return': self.has_pointer_return(),
            'comments': self.get_comments(),
            'comment_summary': self.get_comment_summary(),
            'has_comments': self.has_comments()
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
            'parameter_summary': self.get_parameter_summary(),
            'comments': self.get_comments(),
            'comment_summary': self.get_comment_summary(),
            'has_comments': self.has_comments()
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

    def _is_likely_macro(self, name: str) -> bool:
        """判断是否可能是宏调用"""
        # 常见的宏命名模式
        macro_patterns = [
            # 全大写
            lambda n: n.isupper() and len(n) > 2,
            # 以特定前缀开头的大写宏
            lambda n: any(n.startswith(prefix) for prefix in ['CJSON_', 'API_', 'EXPORT_', 'INLINE_']),
            # 常见的宏名
            lambda n: n in {'MACRO_CALL', 'DEBUG', 'ASSERT', 'TRACE', 'LOG', 'PRINT'}
        ]
        
        return any(pattern(name) for pattern in macro_patterns)
    
    def contains_api_keyword(self, api_keyword: str) -> bool:
        """
        检查函数是否包含指定的API关键字
        
        Args:
            api_keyword: API关键字（如 "CJSON_PUBLIC", "API", "EXPORT" 等）
            
        Returns:
            是否包含API关键字
        """
        # 检查缓存
        if api_keyword in self._api_keywords_cache:
            return self._api_keywords_cache[api_keyword]
        
        # 获取函数的完整文本
        function_text = self.get_body()
        
        # 检查是否包含关键字
        result = function_text is not None and api_keyword in function_text
        
        # 缓存结果
        self._api_keywords_cache[api_keyword] = result
        
        return result
    
    def is_api_function(self, api_keyword: str) -> bool:
        """
        判断函数是否是API函数（包含指定关键字）
        
        Args:
            api_keyword: API关键字
            
        Returns:
            是否是API函数
        """
        return self.contains_api_keyword(api_keyword)
    
    def get_api_keywords(self) -> List[str]:
        """
        获取已检查过的API关键字列表
        
        Returns:
            已检查的API关键字列表（包含该关键字的）
        """
        return [keyword for keyword, contains in self._api_keywords_cache.items() if contains]
    
    def clear_api_cache(self):
        """清除API关键字缓存"""
        self._api_keywords_cache.clear()  