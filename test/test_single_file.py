#!/usr/bin/env python3
"""
测试RepoAnalyzer单文件模式 - 解析test_functions.c文件
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from parser.repo_analyzer import RepoAnalyzer
import logging

def test_single_file_analysis():
    """测试单文件分析功能"""
    
    # 设置日志级别
    logging.basicConfig(level=logging.WARNING)
    
    # 获取测试文件路径
    test_file = os.path.join(os.path.dirname(__file__), 'test_functions.c')
    
    print("=" * 60)
    print("🔍 RepoAnalyzer 单文件模式测试")
    print("=" * 60)
    print(f"📁 分析文件: {test_file}")
    print()
    
    try:
        # 创建RepoAnalyzer实例（单文件模式）
        analyzer = RepoAnalyzer(test_file)
        
        # 执行分析
        print("🚀 开始分析...")
        result = analyzer.analyze()
        
        if 'error' in result:
            print(f"❌ 分析失败: {result['error']}")
            return
        
        # 获取所有函数
        all_functions = analyzer.get_functions()
        
        print(f"✅ 分析完成! 共找到 {len(all_functions)} 个函数")
        print()
        
        # 打印函数信息
        print("📋 函数列表及函数体:")
        print("=" * 60)
        
        # 按行号排序函数
        sorted_functions = sorted(all_functions, key=lambda f: f.start_line)
        
        for i, func in enumerate(sorted_functions, 1):
            print(f"\n🔸 函数 #{i}: {func.name}")
            print(f"   📍 位置: 第 {func.start_line} - {func.end_line} 行")
            print(f"   🔄 返回类型: {func.return_type}")
            print(f"   📥 参数: {', '.join(func.parameters) if func.parameters else '无参数'}")
            print(f"   📄 类型: {'声明' if func.is_declaration else '定义'}")
            
            # 获取函数体 - 通过读取文件来获取更准确的内容
            if not func.is_declaration:
                try:
                    with open(func.file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # 提取函数定义的行（包括函数签名）
                    if func.start_line <= len(lines) and func.end_line <= len(lines):
                        function_lines = lines[func.start_line-1:func.end_line]
                        function_text = ''.join(function_lines).rstrip()
                        
                        print(f"   📝 函数完整定义:")
                        # 为函数体添加缩进以便阅读
                        indented_body = "\n".join(f"      {line.rstrip()}" for line in function_text.split("\n"))
                        print(indented_body)
                    else:
                        print(f"   📝 函数体: (行号超出范围: {func.start_line}-{func.end_line})")
                        
                except Exception as e:
                    print(f"   📝 函数体: (读取失败: {e})")
            else:
                print("   📝 函数体: (仅声明，无函数体)")
            
            print("-" * 40)
        
        # 测试函数调用关系
        print(f"\n🔗 函数调用关系分析:")
        print("=" * 60)
        
        for func in sorted_functions:
            if not func.is_declaration:
                # 解析函数调用
                func.parse_function_calls()
                callees = func.get_callees()
                
                if callees:
                    print(f"\n🔸 {func.name} 调用了:")
                    for callee in callees:
                        print(f"   → {callee}")
                else:
                    print(f"\n🔸 {func.name} 没有调用其他函数")
        
        # 打印统计信息
        print(f"\n📊 统计信息:")
        definitions = [f for f in all_functions if not f.is_declaration]
        declarations = [f for f in all_functions if f.is_declaration]
        print(f"   总函数数量: {len(all_functions)}")
        print(f"   函数定义: {len(definitions)}")
        print(f"   函数声明: {len(declarations)}")
        
        # 如果分析结果包含统计信息，也打印出来
        if 'stats' in result:
            stats = result['stats']
            print(f"\n🔢 分析统计:")
            print(f"   处理文件数: {stats.get('processed_files', 0)}")
            print(f"   分析耗时: {stats.get('analysis_time', 0):.2f} 秒")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_file_analysis()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)