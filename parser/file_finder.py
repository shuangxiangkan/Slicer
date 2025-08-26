#!/usr/bin/env python3
"""
文件查找器 - 在目录中查找C/C++相关文件
"""

import os
import logging
from pathlib import Path
from typing import List

from .file_extensions import (
    C_EXTENSIONS, CPP_EXTENSIONS, ALL_C_CPP_EXTENSIONS,
    is_c_file, is_cpp_file, is_header_file, is_supported_file
)

# Configure logging
logger = logging.getLogger(__name__)


class FileFinder:
    """C/C++ file finder"""
    
    def __init__(self):
        self.found_files = []
    
    def find_files(self, path: str, recursive: bool = True) -> List[str]:
        """
        Find C/C++ files in the specified path.
        
        Args:
            path: File or directory path
            recursive: Whether to search recursively in subdirectories
            
        Returns:
            List of found file paths
        """
        path_obj = Path(path)
        
        if not path_obj.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        
        self.found_files = []
        
        if path_obj.is_file():
            # If it's a single file, check if it's a C/C++ file
            if self._is_c_cpp_file(path_obj):
                self.found_files.append(str(path_obj.absolute()))
        else:
            # If it's a directory, search for C/C++ files in it
            self._search_directory(path_obj, recursive)
        
        return sorted(self.found_files)
    
    def _is_c_cpp_file(self, file_path: Path) -> bool:
        """Check if the file is a C/C++ file"""
        return is_supported_file(str(file_path))
    
    def _search_directory(self, dir_path: Path, recursive: bool):
        """Search for C/C++ files in the directory"""
        try:
            if recursive:
                # Recursively search
                for root, dirs, files in os.walk(dir_path):
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
            logger.warning(f"无法访问目录 {dir_path}: {e}")
    
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
            if is_c_file(file_path) and not is_header_file(file_path):
                stats['c_files'] += 1
            elif is_cpp_file(file_path) and not is_header_file(file_path):
                stats['cpp_files'] += 1
            elif is_header_file(file_path):
                stats['header_files'] += 1
        
        return stats
    
    def get_file_list_info(self, show_stats: bool = True) -> dict:
        """获取文件列表信息（用于日志或返回）"""
        if not self.found_files:
            return {"message": "未找到任何C/C++文件", "files": [], "stats": {}}
        
        file_info = {
            "message": f"找到 {len(self.found_files)} 个C/C++文件",
            "files": []
        }
        
        for i, file_path in enumerate(self.found_files, 1):
            file_obj = Path(file_path)
            file_info["files"].append({
                "index": i,
                "name": file_obj.name,
                "extension": file_obj.suffix,
                "path": file_path
            })
        
        if show_stats:
            file_info["stats"] = self.get_file_stats()
        
        return file_info