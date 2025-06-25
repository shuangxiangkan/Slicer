#!/usr/bin/env python3
"""
文件查找器 - 在目录中查找C/C++相关文件
"""

import os
import glob
from pathlib import Path
from typing import List, Set


class FileFinder:
    """C/C++文件查找器"""
    
    # 支持的文件扩展名
    C_EXTENSIONS = {'.c', '.h'}
    CPP_EXTENSIONS = {'.cpp', '.cxx', '.cc', '.hpp', '.hxx', '.hh'}
    ALL_EXTENSIONS = C_EXTENSIONS | CPP_EXTENSIONS
    
    def __init__(self):
        self.found_files = []
    
    def find_files(self, path: str, recursive: bool = True) -> List[str]:
        """
        查找指定路径下的C/C++文件
        
        Args:
            path: 文件或目录路径
            recursive: 是否递归查找子目录
            
        Returns:
            找到的文件路径列表
        """
        path_obj = Path(path)
        
        if not path_obj.exists():
            raise FileNotFoundError(f"路径不存在: {path}")
        
        self.found_files = []
        
        if path_obj.is_file():
            # 如果是单个文件，检查是否为C/C++文件
            if self._is_c_cpp_file(path_obj):
                self.found_files.append(str(path_obj.absolute()))
        else:
            # 如果是目录，搜索其中的C/C++文件
            self._search_directory(path_obj, recursive)
        
        return sorted(self.found_files)
    
    def _is_c_cpp_file(self, file_path: Path) -> bool:
        """检查文件是否为C/C++文件"""
        return file_path.suffix.lower() in self.ALL_EXTENSIONS
    
    def _search_directory(self, dir_path: Path, recursive: bool):
        """搜索目录中的C/C++文件"""
        try:
            if recursive:
                # 递归搜索
                for root, dirs, files in os.walk(dir_path):
                    # 跳过一些常见的无关目录
                    dirs[:] = [d for d in dirs if not self._should_skip_directory(d)]
                    
                    for file in files:
                        file_path = Path(root) / file
                        if self._is_c_cpp_file(file_path):
                            self.found_files.append(str(file_path.absolute()))
            else:
                # 只搜索当前目录
                for item in dir_path.iterdir():
                    if item.is_file() and self._is_c_cpp_file(item):
                        self.found_files.append(str(item.absolute()))
        except PermissionError as e:
            print(f"警告: 无法访问目录 {dir_path}: {e}")
    
    def _should_skip_directory(self, dir_name: str) -> bool:
        """判断是否应该跳过某个目录"""
        skip_dirs = {
            '.git', '.svn', '.hg',  # 版本控制
            'build', 'Build', 'BUILD',  # 构建目录
            'bin', 'obj',  # 二进制目录
            'venv', 'env', '.env',  # Python虚拟环境
            'node_modules',  # Node.js
            '.vscode', '.idea',  # IDE配置
            'CMakeFiles',  # CMake生成的文件
            '__pycache__',  # Python缓存
        }
        return dir_name in skip_dirs
    
    def get_file_stats(self) -> dict:
        """获取文件统计信息"""
        if not self.found_files:
            return {}
        
        stats = {
            'total_files': len(self.found_files),
            'c_files': 0,
            'cpp_files': 0,
            'header_files': 0,
        }
        
        for file_path in self.found_files:
            ext = Path(file_path).suffix.lower()
            if ext == '.c':
                stats['c_files'] += 1
            elif ext in {'.cpp', '.cxx', '.cc'}:
                stats['cpp_files'] += 1
            elif ext in {'.h', '.hpp', '.hxx', '.hh'}:
                stats['header_files'] += 1
        
        return stats
    
    def print_file_list(self, show_stats: bool = True):
        """打印找到的文件列表"""
        if not self.found_files:
            print("未找到任何C/C++文件")
            return
        
        print(f"找到 {len(self.found_files)} 个C/C++文件:")
        print("-" * 60)
        
        for i, file_path in enumerate(self.found_files, 1):
            file_obj = Path(file_path)
            print(f"{i:3d}. {file_obj.name} ({file_obj.suffix})")
            print(f"     路径: {file_path}")
        
        if show_stats:
            print("\n" + "=" * 60)
            stats = self.get_file_stats()
            print("文件统计:")
            print(f"  总文件数: {stats.get('total_files', 0)}")
            print(f"  C文件: {stats.get('c_files', 0)}")
            print(f"  C++文件: {stats.get('cpp_files', 0)}")
            print(f"  头文件: {stats.get('header_files', 0)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("使用方法: python file_finder.py <目录或文件路径>")
        sys.exit(1)
    
    finder = FileFinder()
    try:
        files = finder.find_files(sys.argv[1])
        finder.print_file_list()
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1) 