#!/usr/bin/env python3
"""
文件扩展名常量定义 - 统一管理C/C++文件扩展名
"""

# C语言文件扩展名
C_EXTENSIONS = {'.c', '.h'}

# C++语言文件扩展名
CPP_EXTENSIONS = {'.cpp', '.cxx', '.cc', '.hpp', '.hxx', '.hh'}

# 所有支持的C/C++文件扩展名
ALL_C_CPP_EXTENSIONS = C_EXTENSIONS | CPP_EXTENSIONS

# 头文件扩展名（包含更多类型）
HEADER_EXTENSIONS = {'.h', '.hpp', '.hxx', '.hh', '.h++', '.inc'}

# 源文件扩展名
SOURCE_EXTENSIONS = {'.c', '.cpp', '.cxx', '.cc'}

# C++特有的扩展名（用于判断是否为C++文件）
CPP_SPECIFIC_EXTENSIONS = {'.cpp', '.cxx', '.cc', '.hpp', '.hxx', '.hh'}

# C特有的扩展名
C_SPECIFIC_EXTENSIONS = {'.c', '.h'}

# 可能包含API使用说明的文档文件扩展名
DOCUMENT_EXTENSIONS = {
    '.txt', '.md', '.rst', '.doc', '.docx', '.pdf', '.rtf', '.tex', '.html', '.htm'
}

# 可以直接读取的文本格式文档扩展名
TEXT_BASED_DOCUMENT_EXTENSIONS = {
    '.txt', '.md', '.rst', '.html', '.htm', '.tex', '.rtf'
}


def is_c_file(file_path: str) -> bool:
    """判断是否为C文件"""
    return any(file_path.endswith(ext) for ext in C_EXTENSIONS)


def is_cpp_file(file_path: str) -> bool:
    """判断是否为C++文件"""
    return any(file_path.endswith(ext) for ext in CPP_SPECIFIC_EXTENSIONS)


def is_header_file(file_path: str) -> bool:
    """判断是否为头文件"""
    return any(file_path.endswith(ext) for ext in HEADER_EXTENSIONS)


def is_source_file(file_path: str) -> bool:
    """判断是否为源文件"""
    return any(file_path.endswith(ext) for ext in SOURCE_EXTENSIONS)


def is_supported_file(file_path: str) -> bool:
    """判断是否为支持的C/C++文件"""
    return any(file_path.endswith(ext) for ext in ALL_C_CPP_EXTENSIONS)


def is_document_file(file_path: str) -> bool:
    """判断是否为文档文件"""
    import os
    
    # 检查文件扩展名
    ext = os.path.splitext(file_path)[1].lower()
    return ext in DOCUMENT_EXTENSIONS


def is_text_based_document(file_path: str) -> bool:
    """判断是否为基于文本的文档文件（可以直接读取内容）"""
    import os
    ext = os.path.splitext(file_path)[1].lower()
    return ext in TEXT_BASED_DOCUMENT_EXTENSIONS


def get_file_type(file_path: str) -> str:
    """获取文件类型"""
    if is_cpp_file(file_path):
        return 'cpp'
    elif is_c_file(file_path):
        return 'c'
    elif is_document_file(file_path):
        return 'document'
    else:
        return 'unknown'