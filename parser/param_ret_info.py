#!/usr/bin/env python3
"""
参数和返回值信息类 - 存储函数参数和返回值的详细信息
"""

from typing import List, Optional
import re
from .type_registry import TypeRegistry, TypeKind


class ParameterInfo:
    """函数参数信息类"""
    
    def __init__(self, raw_text: str, name: str = "", param_type: str = "", 
                 is_pointer: bool = False, pointer_level: int = 0,
                 is_const: bool = False, is_reference: bool = False,
                 type_registry: TypeRegistry = None):
        self.raw_text = raw_text.strip()  # 原始参数文本
        self.name = name.strip()          # 参数名
        self.param_type = param_type.strip()  # 参数类型
        self.is_pointer = is_pointer      # 是否是字面指针
        self.pointer_level = pointer_level  # 字面指针层级 (*=1, **=2, etc.)
        self.is_const = is_const          # 是否是const
        self.is_reference = is_reference  # 是否是引用 (C++)
        self.type_registry = type_registry  # 类型注册表
        
        # typedef指针信息
        self.typedef_is_pointer = False   # typedef是否是指针类型
        self.typedef_pointer_level = 0    # typedef的指针层级
        
        # 如果没有提供解析的信息，尝试自动解析
        if not name and not param_type:
            self._parse_parameter()
        
        # 如果有类型注册表，进行增强分析
        if self.type_registry and self.param_type:
            self._enhance_with_registry()
    
    def _parse_parameter(self):
        """解析参数字符串，提取类型和名称信息"""
        if not self.raw_text or self.raw_text == "void" or self.raw_text.strip() == "":
            return
        
        # 清理文本
        text = self.raw_text.strip()
        
        # 检查是否是const
        self.is_const = 'const' in text
        
        # 检查是否是引用 (C++)
        self.is_reference = '&' in text
        
        # 计算指针层级
        self.pointer_level = text.count('*')
        self.is_pointer = self.pointer_level > 0
        
        # 移除const关键字用于进一步解析
        clean_text = re.sub(r'\bconst\b', '', text).strip()
        
        # 移除指针和引用符号用于解析
        clean_text = re.sub(r'[*&]', ' ', clean_text).strip()
        
        # 分割成词，最后一个通常是参数名，前面的是类型
        parts = clean_text.split()
        parts = [p for p in parts if p]  # 移除空字符串
        
        if len(parts) >= 2:
            # 最后一个词是参数名，前面的是类型
            self.name = parts[-1]
            self.param_type = ' '.join(parts[:-1])
        elif len(parts) == 1:
            # 只有一个词，可能是类型没有参数名，或者只有参数名
            if parts[0] in ['int', 'char', 'float', 'double', 'void', 'bool', 'long', 'short', 'unsigned', 'signed']:
                self.param_type = parts[0]
                self.name = ""
            else:
                # 可能是自定义类型或参数名
                self.param_type = parts[0]
                self.name = ""
        
        # 清理类型名（移除多余空格）
        self.param_type = ' '.join(self.param_type.split())
    
    def _enhance_with_registry(self):
        """使用类型注册表增强分析"""
        if not self.type_registry:
            return
        
        # 检查是否是typedef的指针类型
        is_reg_pointer, reg_pointer_level = self.type_registry.is_pointer_type(self.param_type)
        
        if is_reg_pointer:
            # 记录typedef指针信息，但不改变原始的pointer_level
            # 这样可以保持原始签名的显示，同时在分析中知道它是指针
            self.typedef_is_pointer = True
            self.typedef_pointer_level = reg_pointer_level
        else:
            self.typedef_is_pointer = False
            self.typedef_pointer_level = 0
    
    def get_type_signature(self) -> str:
        """获取类型签名（保持原始形式）"""
        signature = ""
        
        if self.is_const:
            signature += "const "
        
        signature += self.param_type
        
        # 只显示字面上的指针符号，不展开typedef
        if self.is_pointer:
            signature += " " + "*" * self.pointer_level
        
        if self.is_reference:
            signature += " &"
        
        return signature.strip()
    
    def is_actually_pointer(self) -> bool:
        """判断是否实际上是指针类型（包括typedef指针）"""
        return self.is_pointer or self.typedef_is_pointer
    
    def get_total_pointer_level(self) -> int:
        """获取总的指针层级（字面指针 + typedef指针）"""
        return self.pointer_level + self.typedef_pointer_level
    
    def get_pointer_analysis(self) -> str:
        """获取指针分析说明"""
        if not self.is_actually_pointer():
            return "非指针类型"
        
        analysis_parts = []
        
        if self.is_pointer:
            analysis_parts.append(f"字面指针({self.pointer_level}级)")
        
        if self.typedef_is_pointer:
            analysis_parts.append(f"typedef指针({self.typedef_pointer_level}级)")
        
        total_level = self.get_total_pointer_level()
        if total_level > 0:
            analysis_parts.append(f"总层级:{total_level}")
        
        return ", ".join(analysis_parts)
    
    def get_full_signature(self) -> str:
        """获取完整签名（类型 + 参数名）"""
        type_sig = self.get_type_signature()
        if self.name:
            return f"{type_sig} {self.name}"
        else:
            return type_sig
    
    def is_basic_type(self) -> bool:
        """判断是否是基本类型"""
        if self.type_registry:
            return self.type_registry.is_basic_type(self.param_type)
        
        # 回退到静态判断
        basic_types = {
            'int', 'char', 'float', 'double', 'void', 'bool', 
            'long', 'short', 'unsigned', 'signed', 'size_t',
            'int8_t', 'int16_t', 'int32_t', 'int64_t',
            'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t'
        }
        
        # 移除修饰符，检查核心类型
        core_type = self.param_type.replace('unsigned', '').replace('signed', '').strip()
        return core_type in basic_types
    
    def get_type_kind(self) -> str:
        """获取类型种类"""
        if self.type_registry:
            kind = self.type_registry.get_type_kind(self.param_type)
            return kind.value
        
        # 回退判断
        if self.is_basic_type():
            return "basic"
        else:
            return "unknown"
    
    def get_type_chain(self) -> List[str]:
        """获取类型解析链（typedef链）"""
        if self.type_registry:
            return self.type_registry.resolve_type_chain(self.param_type)
        
        return [self.param_type]
    
    def __str__(self):
        return self.get_full_signature()
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        result = {
            'raw_text': self.raw_text,
            'name': self.name,
            'type': self.param_type,
            'type_signature': self.get_type_signature(),
            'full_signature': self.get_full_signature(),
            'is_pointer': self.is_pointer,
            'pointer_level': self.pointer_level,
            'is_const': self.is_const,
            'is_reference': self.is_reference,
            'is_basic_type': self.is_basic_type(),
            'type_kind': self.get_type_kind(),
            'type_chain': self.get_type_chain()
        }
        
        return result


class ReturnTypeInfo:
    """返回类型信息类"""
    
    def __init__(self, raw_text: str, type_registry: TypeRegistry = None):
        self.raw_text = raw_text.strip()
        self.return_type = ""
        self.is_pointer = False
        self.pointer_level = 0
        self.is_const = False
        self.is_reference = False
        self.type_registry = type_registry
        
        # typedef指针信息
        self.typedef_is_pointer = False
        self.typedef_pointer_level = 0
        
        self._parse_return_type()
        
        # 如果有类型注册表，进行增强分析
        if self.type_registry and self.return_type:
            self._enhance_with_registry()
    
    def _parse_return_type(self):
        """解析返回类型"""
        if not self.raw_text:
            self.return_type = "void"
            return
        
        text = self.raw_text.strip()
        
        # 检查是否是const
        self.is_const = 'const' in text
        
        # 检查是否是引用 (C++)
        self.is_reference = '&' in text
        
        # 计算指针层级
        self.pointer_level = text.count('*')
        self.is_pointer = self.pointer_level > 0
        
        # 移除修饰符，提取核心类型
        clean_text = re.sub(r'\bconst\b', '', text).strip()
        clean_text = re.sub(r'[*&]', ' ', clean_text).strip()
        clean_text = ' '.join(clean_text.split())  # 标准化空格
        
        self.return_type = clean_text if clean_text else "void"
    
    def _enhance_with_registry(self):
        """使用类型注册表增强分析"""
        if not self.type_registry:
            return
        
        # 检查是否是typedef的指针类型
        is_reg_pointer, reg_pointer_level = self.type_registry.is_pointer_type(self.return_type)
        
        if is_reg_pointer:
            # 记录typedef指针信息，但不改变原始的pointer_level
            self.typedef_is_pointer = True
            self.typedef_pointer_level = reg_pointer_level
        else:
            self.typedef_is_pointer = False
            self.typedef_pointer_level = 0
    
    def get_type_signature(self) -> str:
        """获取类型签名（保持原始形式）"""
        signature = ""
        
        if self.is_const:
            signature += "const "
        
        signature += self.return_type
        
        # 只显示字面上的指针符号，不展开typedef
        if self.is_pointer:
            signature += " " + "*" * self.pointer_level
        
        if self.is_reference:
            signature += " &"
        
        return signature.strip()
    
    def is_actually_pointer(self) -> bool:
        """判断是否实际上是指针类型（包括typedef指针）"""
        return self.is_pointer or self.typedef_is_pointer
    
    def get_total_pointer_level(self) -> int:
        """获取总的指针层级（字面指针 + typedef指针）"""
        return self.pointer_level + self.typedef_pointer_level
    
    def get_pointer_analysis(self) -> str:
        """获取指针分析说明"""
        if not self.is_actually_pointer():
            return "非指针类型"
        
        analysis_parts = []
        
        if self.is_pointer:
            analysis_parts.append(f"字面指针({self.pointer_level}级)")
        
        if self.typedef_is_pointer:
            analysis_parts.append(f"typedef指针({self.typedef_pointer_level}级)")
        
        total_level = self.get_total_pointer_level()
        if total_level > 0:
            analysis_parts.append(f"总层级:{total_level}")
        
        return ", ".join(analysis_parts)
    
    def is_basic_type(self) -> bool:
        """判断是否是基本类型"""
        if self.type_registry:
            return self.type_registry.is_basic_type(self.return_type)
        
        # 回退到静态判断
        basic_types = {
            'int', 'char', 'float', 'double', 'void', 'bool', 
            'long', 'short', 'unsigned', 'signed', 'size_t',
            'int8_t', 'int16_t', 'int32_t', 'int64_t',
            'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t'
        }
        
        core_type = self.return_type.replace('unsigned', '').replace('signed', '').strip()
        return core_type in basic_types
    
    def get_type_kind(self) -> str:
        """获取类型种类"""
        if self.type_registry:
            kind = self.type_registry.get_type_kind(self.return_type)
            return kind.value
        
        # 回退判断
        if self.is_basic_type():
            return "basic"
        else:
            return "unknown"
    
    def get_type_chain(self) -> List[str]:
        """获取类型解析链（typedef链）"""
        if self.type_registry:
            return self.type_registry.resolve_type_chain(self.return_type)
        
        return [self.return_type]
    
    def __str__(self):
        return self.get_type_signature()
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'raw_text': self.raw_text,
            'type': self.return_type,
            'type_signature': self.get_type_signature(),
            'is_pointer': self.is_pointer,
            'pointer_level': self.pointer_level,
            'is_const': self.is_const,
            'is_reference': self.is_reference,
            'is_basic_type': self.is_basic_type(),
            'type_kind': self.get_type_kind(),
            'type_chain': self.get_type_chain()
        } 