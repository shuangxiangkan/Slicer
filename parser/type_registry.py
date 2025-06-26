#!/usr/bin/env python3
"""
类型注册表 - 管理和解析各种类型定义
"""

import re
from typing import Dict, Set, Optional, List, Tuple
from enum import Enum


class TypeKind(Enum):
    """类型种类"""
    BASIC = "basic"          # 基本类型 (int, char, etc.)
    POINTER = "pointer"      # 指针类型
    STRUCT = "struct"        # 结构体
    UNION = "union"          # 联合体  
    ENUM = "enum"           # 枚举
    TYPEDEF = "typedef"      # 类型别名
    FUNCTION = "function"    # 函数指针
    ARRAY = "array"         # 数组
    UNKNOWN = "unknown"      # 未知类型


class TypeInfo:
    """类型信息"""
    
    def __init__(self, name: str, kind: TypeKind, underlying_type: str = "", 
                 is_pointer: bool = False, pointer_level: int = 0,
                 is_const: bool = False, is_volatile: bool = False):
        self.name = name                    # 类型名
        self.kind = kind                    # 类型种类
        self.underlying_type = underlying_type  # 底层类型（对于typedef）
        self.is_pointer = is_pointer        # 是否是指针
        self.pointer_level = pointer_level  # 指针层级
        self.is_const = is_const           # 是否const
        self.is_volatile = is_volatile     # 是否volatile
        
        # 额外信息
        self.members = []                  # 结构体/联合体成员
        self.enum_values = []              # 枚举值列表
        
    def is_basic_type(self) -> bool:
        """判断是否是基本类型（最终解析后）"""
        if self.kind == TypeKind.BASIC:
            return True
        elif self.kind == TypeKind.TYPEDEF:
            # 递归检查底层类型
            return self._is_underlying_basic()
        return False
    
    def _is_underlying_basic(self) -> bool:
        """检查底层类型是否是基本类型"""
        basic_types = {
            'void', 'char', 'short', 'int', 'long', 'float', 'double',
            'signed', 'unsigned', 'bool', '_Bool',
            'int8_t', 'int16_t', 'int32_t', 'int64_t',
            'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t',
            'size_t', 'ssize_t', 'ptrdiff_t'
        }
        
        # 移除修饰符和指针符号
        clean_type = re.sub(r'\b(const|volatile|static|extern|inline)\b', '', self.underlying_type)
        clean_type = re.sub(r'[*&]', '', clean_type).strip()
        clean_type = ' '.join(clean_type.split())  # 标准化空格
        
        return clean_type in basic_types
    
    def get_final_type(self) -> Tuple[str, bool, int]:
        """
        获取最终解析的类型信息
        
        Returns:
            (final_type, is_pointer, pointer_level)
        """
        if self.kind == TypeKind.TYPEDEF:
            # 解析typedef的底层类型
            underlying = self.underlying_type
            pointer_count = underlying.count('*')
            clean_type = re.sub(r'[*&]', '', underlying).strip()
            clean_type = re.sub(r'\b(const|volatile)\b', '', clean_type).strip()
            clean_type = ' '.join(clean_type.split())
            
            total_pointer_level = self.pointer_level + pointer_count
            return clean_type, total_pointer_level > 0, total_pointer_level
        
        return self.name, self.is_pointer, self.pointer_level
    
    def to_dict(self) -> dict:
        """转换为字典"""
        final_type, is_final_pointer, final_pointer_level = self.get_final_type()
        
        return {
            'name': self.name,
            'kind': self.kind.value,
            'underlying_type': self.underlying_type,
            'is_pointer': self.is_pointer,
            'pointer_level': self.pointer_level,
            'is_const': self.is_const,
            'is_volatile': self.is_volatile,
            'is_basic_type': self.is_basic_type(),
            'final_type': final_type,
            'is_final_pointer': is_final_pointer,
            'final_pointer_level': final_pointer_level,
            'members_count': len(self.members),
            'enum_values_count': len(self.enum_values)
        }


class TypeRegistry:
    """类型注册表"""
    
    def __init__(self):
        self.types: Dict[str, TypeInfo] = {}
        self._initialize_builtin_types()
    
    def _initialize_builtin_types(self):
        """初始化内置基本类型"""
        basic_types = [
            'void', 'char', 'short', 'int', 'long', 'float', 'double',
            'signed', 'unsigned', 'bool', '_Bool',
            'int8_t', 'int16_t', 'int32_t', 'int64_t',
            'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t',
            'size_t', 'ssize_t', 'ptrdiff_t'
        ]
        
        for type_name in basic_types:
            self.types[type_name] = TypeInfo(type_name, TypeKind.BASIC)
    
    def register_typedef(self, type_name: str, underlying_type: str):
        """注册typedef定义"""
        # 解析底层类型的修饰符
        is_const = 'const' in underlying_type
        is_volatile = 'volatile' in underlying_type
        pointer_level = underlying_type.count('*')
        is_pointer = pointer_level > 0
        
        type_info = TypeInfo(
            name=type_name,
            kind=TypeKind.TYPEDEF,
            underlying_type=underlying_type,
            is_pointer=is_pointer,
            pointer_level=pointer_level,
            is_const=is_const,
            is_volatile=is_volatile
        )
        
        self.types[type_name] = type_info
    
    def register_struct(self, struct_name: str, members: List[str] = None):
        """注册结构体定义"""
        type_info = TypeInfo(struct_name, TypeKind.STRUCT)
        if members:
            type_info.members = members
        self.types[struct_name] = type_info
    
    def register_union(self, union_name: str, members: List[str] = None):
        """注册联合体定义"""
        type_info = TypeInfo(union_name, TypeKind.UNION)
        if members:
            type_info.members = members
        self.types[union_name] = type_info
    
    def register_enum(self, enum_name: str, values: List[str] = None):
        """注册枚举定义"""
        type_info = TypeInfo(enum_name, TypeKind.ENUM)
        if values:
            type_info.enum_values = values
        self.types[enum_name] = type_info
    
    def lookup_type(self, type_name: str) -> Optional[TypeInfo]:
        """查找类型信息"""
        # 移除修饰符，只保留核心类型名
        clean_name = self._extract_core_type_name(type_name)
        return self.types.get(clean_name)
    
    def _extract_core_type_name(self, type_name: str) -> str:
        """提取核心类型名（移除修饰符）"""
        # 移除const, volatile等修饰符
        clean = re.sub(r'\b(const|volatile|static|extern|inline|register)\b', '', type_name)
        # 移除指针和引用符号
        clean = re.sub(r'[*&]', '', clean)
        # 标准化空格
        clean = ' '.join(clean.split()).strip()
        return clean
    
    def is_pointer_type(self, type_name: str) -> Tuple[bool, int]:
        """
        判断类型是否是指针类型
        
        Returns:
            (is_pointer, pointer_level)
        """
        # 首先检查字面上的指针符号
        literal_pointer_level = type_name.count('*')
        
        # 然后检查是否是typedef的指针类型
        core_type = self._extract_core_type_name(type_name)
        type_info = self.lookup_type(core_type)
        
        if type_info:
            final_type, is_final_pointer, final_pointer_level = type_info.get_final_type()
            total_pointer_level = literal_pointer_level + final_pointer_level
            return total_pointer_level > 0, total_pointer_level
        
        return literal_pointer_level > 0, literal_pointer_level
    
    def is_basic_type(self, type_name: str) -> bool:
        """判断是否是基本类型"""
        core_type = self._extract_core_type_name(type_name)
        type_info = self.lookup_type(core_type)
        
        if type_info:
            return type_info.is_basic_type()
        
        # 如果没有注册，尝试直接匹配基本类型
        basic_types = {
            'void', 'char', 'short', 'int', 'long', 'float', 'double',
            'signed', 'unsigned', 'bool', '_Bool'
        }
        return core_type in basic_types
    
    def get_type_kind(self, type_name: str) -> TypeKind:
        """获取类型种类"""
        core_type = self._extract_core_type_name(type_name)
        type_info = self.lookup_type(core_type)
        
        if type_info:
            return type_info.kind
        
        return TypeKind.UNKNOWN
    
    def resolve_type_chain(self, type_name: str) -> List[str]:
        """解析类型链（typedef链）"""
        chain = []
        current_type = self._extract_core_type_name(type_name)
        
        visited = set()  # 防止循环引用
        
        while current_type and current_type not in visited:
            visited.add(current_type)
            chain.append(current_type)
            
            type_info = self.lookup_type(current_type)
            if type_info and type_info.kind == TypeKind.TYPEDEF:
                current_type = self._extract_core_type_name(type_info.underlying_type)
            else:
                break
        
        return chain
    
    def get_all_types_by_kind(self, kind: TypeKind) -> List[TypeInfo]:
        """获取指定种类的所有类型"""
        return [type_info for type_info in self.types.values() if type_info.kind == kind]
    
    def get_statistics(self) -> dict:
        """获取类型统计信息"""
        stats = {}
        for kind in TypeKind:
            stats[kind.value] = len(self.get_all_types_by_kind(kind))
        
        # 额外统计
        pointer_typedefs = len([t for t in self.types.values() 
                              if t.kind == TypeKind.TYPEDEF and t.is_pointer])
        
        stats.update({
            'total_types': len(self.types),
            'pointer_typedefs': pointer_typedefs
        })
        
        return stats
    
    def print_type_info(self, type_name: str):
        """打印类型详细信息"""
        type_info = self.lookup_type(type_name)
        
        if not type_info:
            print(f"❌ 未找到类型: {type_name}")
            return
        
        print(f"🔍 类型信息: {type_name}")
        print(f"   种类: {type_info.kind.value}")
        print(f"   是否指针: {type_info.is_pointer}")
        
        if type_info.pointer_level > 0:
            print(f"   指针层级: {type_info.pointer_level}")
        
        if type_info.is_const:
            print(f"   const修饰: 是")
        
        if type_info.kind == TypeKind.TYPEDEF:
            print(f"   底层类型: {type_info.underlying_type}")
            final_type, is_final_pointer, final_pointer_level = type_info.get_final_type()
            print(f"   最终类型: {final_type}")
            print(f"   最终是否指针: {is_final_pointer}")
            if final_pointer_level > 0:
                print(f"   最终指针层级: {final_pointer_level}")
        
        if type_info.members:
            print(f"   成员数量: {len(type_info.members)}")
        
        if type_info.enum_values:
            print(f"   枚举值数量: {len(type_info.enum_values)}")
    
    def export_types(self) -> dict:
        """导出所有类型信息"""
        return {
            name: type_info.to_dict() 
            for name, type_info in self.types.items()
        } 