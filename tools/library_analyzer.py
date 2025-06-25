#!/usr/bin/env python3
"""
C/C++ 库函数分析工具
自动在第三方库中查找函数定义，并使用参数切片分析工具进行分析
"""

import argparse
import os
import sys
import glob
import tempfile
import shutil
import subprocess
from typing import List, Tuple, Optional

# 添加父目录到路径，以便导入slicer包
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tree_sitter
from tree_sitter import Language
import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp


class LibraryAnalyzer:
    """C/C++库分析器"""
    
    def __init__(self, language: str = "c"):
        """
        初始化库分析器
        
        Args:
            language: 语言类型，"c" 或 "cpp"
        """
        self.language = language
        self.parser = tree_sitter.Parser()
        
        if language == "c":
            lang_capsule = tsc.language()
            language_obj = Language(lang_capsule, 'c')
            self.parser.set_language(language_obj)
            self.file_extensions = ['.c', '.h']
        else:
            lang_capsule = tscpp.language()
            language_obj = Language(lang_capsule, 'cpp')
            self.parser.set_language(language_obj)
            self.file_extensions = ['.cpp', '.cc', '.cxx', '.hpp', '.h', '.hh', '.hxx']
    
    def find_source_files(self, library_path: str) -> List[str]:
        """
        在库目录中查找所有源文件
        
        Args:
            library_path: 库目录路径
            
        Returns:
            源文件路径列表
        """
        source_files = []
        
        # 常见的需要跳过的目录
        skip_dirs = {
            '.git', '.svn', '.hg',  # 版本控制
            '__pycache__', '.pytest_cache',  # Python
            'build', 'dist', 'out', 'bin', 'obj',  # 构建输出
            'node_modules', 'vendor',  # 依赖
            'test', 'tests', 'testing',  # 测试（可能包含测试代码而非库代码）
            'examples', 'example', 'samples', 'demo', 'demos',  # 示例
            'docs', 'doc', 'documentation',  # 文档
            '.vscode', '.idea', '.vs',  # IDE配置
            'cmake-build-debug', 'cmake-build-release'  # CMake构建目录
        }
        
        for root, dirs, files in os.walk(library_path):
            # 动态过滤目录，保留原始列表的引用
            dirs[:] = [d for d in dirs if d.lower() not in skip_dirs and not d.startswith('.')]
            
            for file in files:
                if any(file.endswith(ext) for ext in self.file_extensions):
                    # 跳过一些明显的非库文件
                    if not any(keyword in file.lower() for keyword in ['test', 'example', 'demo', 'sample']):
                        source_files.append(os.path.join(root, file))
        
        return source_files
    
    def _extract_function_name(self, function_node: tree_sitter.Node) -> Optional[str]:
        """
        从函数定义节点中提取函数名
        
        Args:
            function_node: 函数定义节点
            
        Returns:
            函数名或None
        """
        def extract_name_from_node(node: tree_sitter.Node) -> Optional[str]:
            if node.type == "identifier":
                return node.text.decode("utf8")
            elif node.type == "function_declarator":
                # 在function_declarator中查找identifier
                for child in node.children:
                    name = extract_name_from_node(child)
                    if name:
                        return name
            elif node.type in ["pointer_declarator", "reference_declarator"]:
                # 处理指针和引用类型的函数
                for child in node.children:
                    name = extract_name_from_node(child)
                    if name:
                        return name
            
            return None
        
        # 遍历函数定义的所有子节点
        for child in function_node.children:
            name = extract_name_from_node(child)
            if name:
                return name
        
        return None
    
    def parse_function_from_file(self, file_path: str, function_name: str) -> Optional[Tuple[tree_sitter.Node, str]]:
        """
        在指定文件中查找函数定义
        
        Args:
            file_path: 文件路径
            function_name: 函数名
            
        Returns:
            (函数节点, 文件内容) 或 None
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
        except Exception as e:
            print(f"警告：无法读取文件 {file_path}: {e}")
            return None
        
        tree = self.parser.parse(bytes(code, "utf8"))
        root_node = tree.root_node
        
        def find_function(node: tree_sitter.Node) -> Optional[tree_sitter.Node]:
            if node.type == "function_definition":
                # 查找函数名 - 支持多种函数声明模式
                function_identifier = self._extract_function_name(node)
                if function_identifier == function_name:
                    return node
            
            # 递归查找子节点
            for child in node.children:
                result = find_function(child)
                if result:
                    return result
            
            return None
        
        function_node = find_function(root_node)
        if function_node:
            return function_node, code
        
        return None
    
    def list_functions_in_file(self, file_path: str) -> List[str]:
        """
        列出指定文件中的所有函数
        
        Args:
            file_path: 文件路径
            
        Returns:
            函数名列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
        except Exception:
            return []
        
        tree = self.parser.parse(bytes(code, "utf8"))
        root_node = tree.root_node
        
        functions = []
        
        def find_all_functions(node: tree_sitter.Node):
            if node.type == "function_definition":
                function_name = self._extract_function_name(node)
                if function_name:
                    functions.append(function_name)
            
            # 递归查找子节点
            for child in node.children:
                find_all_functions(child)
        
        find_all_functions(root_node)
        return functions
    
    def list_all_functions_in_library(self, library_path: str) -> dict:
        """
        列出库中所有函数
        
        Args:
            library_path: 库目录路径
            
        Returns:
            {文件路径: [函数名列表]}
        """
        source_files = self.find_source_files(library_path)
        all_functions = {}
        
        for file_path in source_files:
            functions = self.list_functions_in_file(file_path)
            if functions:
                rel_path = os.path.relpath(file_path, library_path)
                all_functions[rel_path] = functions
        
        return all_functions
    
    def search_function_in_library(self, library_path: str, function_name: str) -> Optional[Tuple[str, tree_sitter.Node, str]]:
        """
        在整个库中搜索函数定义
        
        Args:
            library_path: 库目录路径
            function_name: 函数名
            
        Returns:
            (文件路径, 函数节点, 文件内容) 或 None
        """
        print(f"正在搜索函数 '{function_name}' 在库 '{library_path}' 中...")
        
        source_files = self.find_source_files(library_path)
        print(f"找到 {len(source_files)} 个源文件")
        
        for file_path in source_files:
            print(f"  检查文件: {os.path.relpath(file_path, library_path)}")
            result = self.parse_function_from_file(file_path, function_name)
            if result:
                function_node, code = result
                print(f"✅ 找到函数定义在: {os.path.relpath(file_path, library_path)}")
                return file_path, function_node, code
        
        return None
    
    def extract_function_code(self, function_node: tree_sitter.Node, code: str) -> str:
        """
        提取函数完整代码
        
        Args:
            function_node: 函数节点
            code: 完整文件内容
            
        Returns:
            函数代码字符串
        """
        start_byte = function_node.start_byte
        end_byte = function_node.end_byte
        function_code = code[start_byte:end_byte]
        return function_code
    
    def create_temporary_file(self, function_code: str, function_name: str, original_file_path: str = None) -> str:
        """
        创建包含函数代码的临时文件
        
        Args:
            function_code: 函数代码
            function_name: 函数名
            original_file_path: 原始文件路径（用于分析依赖）
            
        Returns:
            临时文件路径
        """
        temp_dir = tempfile.mkdtemp(prefix=f"library_analyzer_{function_name}_")
        temp_file = os.path.join(temp_dir, f"{function_name}_extracted.{self.language}")
        
        # 添加必要的头文件包含
        if self.language == "c":
            header = """#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

"""
        else:
            header = """#include <iostream>
#include <string>
#include <vector>
#include <memory>
#include <cstdint>
#include <cstddef>

"""
        
        # 如果有原始文件，尝试提取完整的类型定义
        additional_includes = ""
        if original_file_path:
            try:
                with open(original_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    original_content = f.read()
                
                # 只提取完整的、简单的定义，避免复杂的宏
                lines = original_content.split('\n')
                in_multiline_comment = False
                
                for line in lines:
                    stripped = line.strip()
                    
                    # 跳过注释
                    if '/*' in stripped:
                        in_multiline_comment = True
                    if '*/' in stripped:
                        in_multiline_comment = False
                        continue
                    if in_multiline_comment or stripped.startswith('//'):
                        continue
                    
                    # 只包含完整的、简单的定义
                    if (stripped.startswith('typedef struct') and stripped.endswith(';') or
                        stripped.startswith('typedef enum') and stripped.endswith(';') or
                        stripped.startswith('typedef ') and ' *' not in stripped and stripped.endswith(';')):
                        additional_includes += line + '\n'
                    elif stripped.startswith('#include ') and not 'cJSON' in stripped:
                        additional_includes += line + '\n'
            except:
                pass
        
        # 添加常见的cJSON类型定义（如果是cJSON库的话）
        if 'cJSON' in str(original_file_path):
            additional_includes += """
#ifndef CJSON_PUBLIC
#define CJSON_PUBLIC(type) type
#endif

typedef int cJSON_bool;

typedef struct cJSON
{
    struct cJSON *next;
    struct cJSON *prev; 
    struct cJSON *child;
    int type;
    char *valuestring;
    int valueint;
    double valuedouble;
    char *string;
} cJSON;
"""
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(header + additional_includes + '\n' + function_code)
        
        return temp_file
    
    def analyze_function_with_param_analyzer(self, temp_file: str, function_name: str, 
                                            verbose: bool = False, save_output: bool = True) -> bool:
        """
        使用参数分析器分析函数
        
        Args:
            temp_file: 临时文件路径
            function_name: 函数名
            verbose: 是否显示详细信息
            save_output: 是否保存输出
            
        Returns:
            是否成功分析
        """
        # 构建param_analyzer命令
        script_dir = os.path.dirname(os.path.abspath(__file__))
        param_analyzer_path = os.path.join(script_dir, "param_analyzer.py")
        
        cmd = ["python", param_analyzer_path, temp_file, function_name]
        cmd.extend(["--language", self.language])
        
        if verbose:
            cmd.append("--verbose")
        
        if not save_output:
            cmd.append("--no-save")
        
        try:
            print(f"\n{'='*60}")
            print(f"使用参数分析器分析函数 '{function_name}'")
            print(f"{'='*60}")
            
            # 运行参数分析器
            result = subprocess.run(cmd, capture_output=False, text=True)
            
            if result.returncode == 0:
                print(f"\n✅ 函数 '{function_name}' 分析完成！")
                return True
            else:
                print(f"\n❌ 函数 '{function_name}' 分析失败")
                return False
                
        except Exception as e:
            print(f"❌ 运行参数分析器时出错: {e}")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="C/C++ 库函数分析工具")
    parser.add_argument("library_path", help="库目录路径")
    parser.add_argument("function_name", nargs="?", help="要分析的函数名（可选，如果不提供则列出所有函数）")
    parser.add_argument("--language", choices=["c", "cpp"], default="c", help="语言类型")
    parser.add_argument("--list", action="store_true",
                       help="仅列出库中所有可用的函数，不进行分析")
    parser.add_argument("--verbose", action="store_true", 
                       help="显示详细的分析提示信息")
    parser.add_argument("--no-save", action="store_true", 
                       help="不保存分析结果到文件，只显示")
    parser.add_argument("--keep-temp", action="store_true",
                       help="保留临时文件（用于调试）")
    
    args = parser.parse_args()
    
    # 检查库路径是否存在
    if not os.path.exists(args.library_path):
        print(f"错误：库路径 '{args.library_path}' 不存在")
        return
    
    if not os.path.isdir(args.library_path):
        print(f"错误：'{args.library_path}' 不是一个目录")
        return
    
    # 创建库分析器
    analyzer = LibraryAnalyzer(args.language)
    
    try:
        # 如果只是列出函数或没有指定函数名
        if args.list or not args.function_name:
            print(f"正在扫描库 '{args.library_path}' 中的所有函数...")
            all_functions = analyzer.list_all_functions_in_library(args.library_path)
            
            if not all_functions:
                print("❌ 未找到任何函数定义")
                return
            
            print(f"\n📋 库中发现的函数:")
            print("=" * 60)
            total_functions = 0
            for file_path, functions in all_functions.items():
                print(f"\n📄 {file_path}:")
                for func in functions:
                    print(f"  - {func}")
                    total_functions += 1
            
            print(f"\n总共找到 {total_functions} 个函数")
            
            if not args.function_name:
                print("\n💡 使用以下命令分析特定函数:")
                print(f"   python {os.path.basename(__file__)} {args.library_path} <函数名>")
                return
        
        # 搜索指定函数
        result = analyzer.search_function_in_library(args.library_path, args.function_name)
        
        if not result:
            print(f"\n❌ 在库 '{args.library_path}' 中未找到函数 '{args.function_name}'")
            return
        
        file_path, function_node, code = result
        
        # 提取函数代码
        function_code = analyzer.extract_function_code(function_node, code)
        
        print(f"\n📋 函数代码预览:")
        print("-" * 50)
        lines = function_code.split('\n')
        for i, line in enumerate(lines[:10], 1):  # 显示前10行
            print(f"{i:3d}: {line}")
        if len(lines) > 10:
            print(f"... (还有 {len(lines) - 10} 行)")
        print()
        
        # 创建临时文件
        temp_file = analyzer.create_temporary_file(function_code, args.function_name, file_path)
        print(f"📄 临时文件创建于: {temp_file}")
        
        # 使用参数分析器分析
        success = analyzer.analyze_function_with_param_analyzer(
            temp_file, args.function_name, args.verbose, not args.no_save
        )
        
        # 清理临时文件（除非用户要求保留）
        if not args.keep_temp:
            temp_dir = os.path.dirname(temp_file)
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"\n🗑️  临时文件已清理")
        else:
            print(f"\n📁 临时文件保留在: {temp_file}")
    
    except Exception as e:
        print(f"❌ 分析过程中出错: {e}")
        return


if __name__ == "__main__":
    main() 