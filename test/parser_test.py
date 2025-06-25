#!/usr/bin/env python3
"""
Parser模块测试脚本
测试文件查找器、函数提取器和仓库分析器的功能
"""

import sys
import os
import tempfile
import json
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser import FileFinder, FunctionExtractor, RepoAnalyzer


class TestData:
    """测试数据类"""
    
    SAMPLE_C_CODE = '''
#include <stdio.h>

int add(int a, int b) {
    return a + b;
}

int multiply(int x, int y) {
    int result = x * y;
    return result;
}

void print_hello() {
    printf("Hello, World!\\n");
}

int main() {
    int sum = add(5, 3);
    int product = multiply(4, 6);
    print_hello();
    return 0;
}
'''

    SAMPLE_H_CODE = '''
#ifndef MATH_H
#define MATH_H

int add(int a, int b);
int multiply(int x, int y);
void print_hello();

#endif
'''

    SAMPLE_CPP_CODE = '''
#include <iostream>

class Calculator {
public:
    int add(int a, int b) {
        return a + b;
    }
    
    int subtract(int a, int b) {
        return a - b;
    }
};

namespace Math {
    double pi() {
        return 3.14159;
    }
}

int main() {
    Calculator calc;
    int result = calc.add(10, 20);
    std::cout << "Result: " << result << std::endl;
    return 0;
}
'''


class ParserTester:
    """Parser模块测试器"""
    
    def __init__(self):
        self.temp_dir = None
        self.test_files = []
        print("🧪 Parser模块测试器初始化")
        print("=" * 60)
    
    def create_test_environment(self):
        """创建测试环境"""
        print("📁 创建测试环境...")
        
        # 创建临时目录
        self.temp_dir = Path(tempfile.mkdtemp(prefix="parser_test_"))
        print(f"   临时目录: {self.temp_dir}")
        
        # 创建测试文件
        test_files_data = [
            ("main.c", TestData.SAMPLE_C_CODE),
            ("math.h", TestData.SAMPLE_H_CODE),
            ("calculator.cpp", TestData.SAMPLE_CPP_CODE),
        ]
        
        # 创建子目录结构
        src_dir = self.temp_dir / "src"
        include_dir = self.temp_dir / "include"
        build_dir = self.temp_dir / "build"  # 这个目录应该被跳过
        
        src_dir.mkdir()
        include_dir.mkdir()
        build_dir.mkdir()
        
        # 创建测试文件
        for filename, content in test_files_data:
            if filename.endswith('.h'):
                file_path = include_dir / filename
            else:
                file_path = src_dir / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.test_files.append(file_path)
            print(f"   创建文件: {file_path}")
        
        # 在build目录创建一个文件（应该被跳过）
        build_file = build_dir / "temp.c"
        with open(build_file, 'w') as f:
            f.write("// This should be skipped\nint temp() { return 0; }")
        
        print(f"✅ 测试环境创建完成，共创建 {len(self.test_files)} 个测试文件")
        return self.temp_dir
    
    def test_file_finder(self):
        """测试文件查找器"""
        print("\n🔍 测试文件查找器...")
        print("-" * 40)
        
        try:
            finder = FileFinder()
            
            # 测试查找所有文件
            files = finder.find_files(str(self.temp_dir), recursive=True)
            
            print(f"✅ 找到 {len(files)} 个文件")
            for file in files:
                print(f"   📄 {Path(file).name}")
            
            # 验证结果
            expected_files = {'main.c', 'math.h', 'calculator.cpp'}
            found_files = {Path(f).name for f in files}
            
            if expected_files <= found_files:
                print("✅ 文件查找测试通过")
            else:
                missing = expected_files - found_files
                print(f"❌ 文件查找测试失败，缺少文件: {missing}")
                return False
            
            # 测试统计信息
            stats = finder.get_file_stats()
            print(f"📊 统计信息: {stats}")
            
            # 验证build目录被跳过
            build_files = [f for f in files if 'build' in f]
            if not build_files:
                print("✅ 成功跳过build目录")
            else:
                print(f"❌ 未能跳过build目录: {build_files}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ 文件查找器测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_function_extractor(self):
        """测试函数提取器"""
        print("\n🔧 测试函数提取器...")
        print("-" * 40)
        
        try:
            extractor = FunctionExtractor()
            all_functions = []
            
            for test_file in self.test_files:
                print(f"\n📄 分析文件: {test_file.name}")
                functions = extractor.extract_from_file(str(test_file))
                all_functions.extend(functions)
                
                print(f"   找到 {len(functions)} 个函数:")
                for func in functions:
                    func_type = "声明" if func.is_declaration else "定义"
                    scope_info = f" (作用域: {func.scope})" if func.scope else ""
                    print(f"   - {func.name} [{func_type}]{scope_info}")
            
            # 验证预期的函数
            expected_functions = {
                'add', 'multiply', 'print_hello', 'main', 'pi'
            }
            found_functions = {func.name for func in all_functions if not func.is_declaration}
            
            if expected_functions <= found_functions:
                print(f"\n✅ 函数提取测试通过，找到 {len(all_functions)} 个函数")
            else:
                missing = expected_functions - found_functions
                print(f"\n❌ 函数提取测试失败，缺少函数: {missing}")
                print(f"   实际找到: {found_functions}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ 函数提取器测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_repo_analyzer(self):
        """测试仓库分析器"""
        print("\n📊 测试仓库分析器...")
        print("-" * 40)
        
        try:
            analyzer = RepoAnalyzer()
            
            # 分析测试目录
            stats = analyzer.analyze_repository(str(self.temp_dir), show_progress=True)
            
            if not stats:
                print("❌ 仓库分析失败")
                return False
            
            print("\n📈 分析结果:")
            print(f"   处理文件: {stats['successful_files']}/{stats['total_files']}")
            print(f"   总函数数: {stats['total_functions']}")
            print(f"   函数定义: {stats['function_definitions']}")
            print(f"   函数声明: {stats['function_declarations']}")
            
            # 测试搜索功能
            print("\n🔍 测试搜索功能...")
            main_functions = analyzer.search_functions("main")
            print(f"   搜索'main': 找到 {len(main_functions)} 个函数")
            
            add_functions = analyzer.search_functions("add")
            print(f"   搜索'add': 找到 {len(add_functions)} 个函数")
            
            # 验证基本要求
            if stats['total_functions'] >= 5:  # 至少应该有几个函数
                print("✅ 仓库分析器测试通过")
                return True
            else:
                print(f"❌ 仓库分析器测试失败，函数数量不足: {stats['total_functions']}")
                return False
            
        except Exception as e:
            print(f"❌ 仓库分析器测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_config_loading(self):
        """测试配置文件加载"""
        print("\n⚙️  测试配置文件加载...")
        print("-" * 40)
        
        try:
            finder = FileFinder()
            
            # 检查是否正确加载了配置
            print(f"   C扩展名: {finder.C_EXTENSIONS}")
            print(f"   C++扩展名: {finder.CPP_EXTENSIONS}")
            print(f"   跳过目录数量: {len(finder.SKIP_DIRECTORIES)}")
            print(f"   跳过目录示例: {list(finder.SKIP_DIRECTORIES)[:5]}...")
            
            # 验证基本配置
            if '.c' in finder.C_EXTENSIONS and '.cpp' in finder.CPP_EXTENSIONS:
                print("✅ 配置文件加载测试通过")
                return True
            else:
                print("❌ 配置文件加载测试失败")
                return False
                
        except Exception as e:
            print(f"❌ 配置文件加载测试失败: {e}")
            return False
    
    def cleanup(self):
        """清理测试环境"""
        if self.temp_dir and self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir)
            print(f"\n🧹 清理测试环境: {self.temp_dir}")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始Parser模块综合测试")
        print("=" * 80)
        
        test_results = []
        
        try:
            # 创建测试环境
            self.create_test_environment()
            
            # 运行各项测试
            tests = [
                ("配置文件加载", self.test_config_loading),
                ("文件查找器", self.test_file_finder),
                ("函数提取器", self.test_function_extractor),
                ("仓库分析器", self.test_repo_analyzer),
            ]
            
            for test_name, test_func in tests:
                try:
                    result = test_func()
                    test_results.append((test_name, result))
                except Exception as e:
                    print(f"❌ {test_name}测试出现异常: {e}")
                    test_results.append((test_name, False))
            
            # 输出测试总结
            self.print_test_summary(test_results)
            
        except Exception as e:
            print(f"❌ 测试过程中出现严重错误: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # 清理测试环境
            self.cleanup()
    
    def print_test_summary(self, test_results):
        """打印测试总结"""
        print("\n" + "=" * 80)
        print("📋 测试总结")
        print("=" * 80)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {test_name:<20} {status}")
            if result:
                passed += 1
        
        print("-" * 40)
        print(f"总计: {passed}/{total} 测试通过")
        
        if passed == total:
            print("🎉 所有测试通过！Parser模块工作正常")
        else:
            print(f"⚠️  有 {total - passed} 个测试失败，请检查相关功能")


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Parser模块测试脚本")
        print("使用方法: python test/parser.py")
        print("该脚本将创建临时测试环境，测试Parser模块的各项功能")
        return
    
    tester = ParserTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main() 