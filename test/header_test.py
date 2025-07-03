#!/usr/bin/env python3
"""
C/C++文件分析示例 - 严格按照要求
提取 single_file_example.c 的头文件、main()和multiply_numbers()函数调用、参数和返回值
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from parser import RepoAnalyzer


def extract_headers(analyzer):
    """提取所有头文件"""
    print("📦 头文件提取")
    print("=" * 50)
    
    # 使用analyzer的头文件分析功能
    header_result = analyzer.analyze_headers()
    
    if 'results' in header_result and header_result['results']:
        for file_path, file_result in header_result['results'].items():
            includes = file_result['includes']
            print(f"发现 {len(includes)} 个头文件:")
            for include in includes:
                include_type = "系统" if include.is_system else "本地"
                print(f"  - {include.include_path} (行{include.line_number}, {include_type})")
    else:
        # 如果不是头文件，直接从文件读取include语句
        functions = analyzer.get_functions()
        if functions:
            file_path = functions[0].file_path
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            includes = []
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if line.startswith('#include'):
                    if '<' in line and '>' in line:
                        header = line[line.find('<')+1:line.find('>')]
                        includes.append(f"{header} (行{line_num}, 系统)")
                    elif '"' in line:
                        header = line[line.find('"')+1:line.rfind('"')]
                        includes.append(f"{header} (行{line_num}, 本地)")
            
            print(f"发现 {len(includes)} 个头文件:")
            for include in includes:
                print(f"  - {include}")


def extract_main_function_calls_and_params(analyzer):
    """提取main函数的调用、参数和返回值"""
    print(f"\n🔧 函数: main")
    print("=" * 50)
    
    # 获取main函数信息
    functions = analyzer.get_functions()
    main_func = None
    for func in functions:
        if func.name == "main":
            main_func = func
            break
    
    if not main_func:
        print(f"❌ 未找到函数: main")
        return
    
    # 1. 函数基本信息
    print(f"📍 函数定义: 行 {main_func.start_line}-{main_func.end_line}")
    
    # 2. 返回值
    print(f"📤 返回值: {main_func.return_type}")
    
    # 3. 参数
    print(f"📥 参数:")
    if main_func.parameter_details:
        for i, param in enumerate(main_func.parameter_details, 1):
            print(f"  {i}. {param.get_full_signature()}")
    elif main_func.parameters:
        for i, param_str in enumerate(main_func.parameters, 1):
            print(f"  {i}. {param_str}")
    else:
        print("  无参数")
    
    # 4. main函数调用的函数
    call_graph = analyzer.get_call_graph()
    callees = call_graph.get_direct_callees("main")
    print(f"📞 函数调用:")
    if callees:
        for callee in callees:
            print(f"  - {callee}")
    else:
        print("  无调用")


def extract_multiply_numbers_usage(analyzer):
    """提取multiply_numbers被调用的位置和定义信息"""
    print(f"\n🔧 函数: multiply_numbers")
    print("=" * 50)
    
    # 获取multiply_numbers函数信息
    functions = analyzer.get_functions()
    multiply_func = None
    for func in functions:
        if func.name == "multiply_numbers":
            multiply_func = func
            break
    
    if not multiply_func:
        print(f"❌ 未找到函数: multiply_numbers")
        return
    
    # 1. 函数定义信息
    print(f"📍 函数定义: 行 {multiply_func.start_line}-{multiply_func.end_line}")
    
    # 2. 返回值
    print(f"📤 返回值: {multiply_func.return_type}")
    
    # 3. 形参
    print(f"📥 形参:")
    if multiply_func.parameter_details:
        for i, param in enumerate(multiply_func.parameter_details, 1):
            print(f"  {i}. {param.get_full_signature()}")
    elif multiply_func.parameters:
        for i, param_str in enumerate(multiply_func.parameters, 1):
            print(f"  {i}. {param_str}")
    else:
        print("  无参数")
    
    # 4. 被调用的位置
    call_graph = analyzer.get_call_graph()
    callers = call_graph.get_direct_callers("multiply_numbers")
    print(f"📞 被调用位置:")
    if callers:
        for caller in callers:
            print(f"  - 在函数 {caller} 中被调用")
    else:
        print("  未被调用")


def main():
    """主函数"""
    print("🚀 C/C++文件分析")
    print("=" * 80)
    
    # 目标文件
    target_file = "test/single_file_example.c"
    
    if not os.path.exists(target_file):
        print(f"❌ 文件不存在: {target_file}")
        return
    
    print(f"📁 分析文件: {target_file}\n")
    
    # 创建分析器
    analyzer = RepoAnalyzer(target_file)
    analyzer.analyze()
    
    # 1. 提取所有头文件
    extract_headers(analyzer)
    
    # 2. 提取main()函数的调用、参数和返回值
    extract_main_function_calls_and_params(analyzer)
    
    # 3. 提取multiply_numbers()被调用的位置和定义信息
    extract_multiply_numbers_usage(analyzer)
    
    print(f"\n✅ 分析完成!")


if __name__ == "__main__":
    main() 
    
