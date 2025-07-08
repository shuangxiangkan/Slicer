#!/usr/bin/env python3
"""
测试函数调用者接口
演示如何获取函数的调用者信息
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from parser import RepoAnalyzer


def test_function_callers():
    """测试函数调用者获取功能"""
    
    print("=" * 80)
    print("🔍 函数调用者获取测试")
    print("=" * 80)
    
    config_file = 'test/cjson_config.json'
    
    # 检查配置文件是否存在
    if not os.path.exists(config_file):
        print(f"❌ 配置文件不存在: {config_file}")
        return
    
    try:
        # 初始化分析器
        print("🔧 初始化分析器...")
        analyzer = RepoAnalyzer(config_file)
        
        # 分析代码
        print("📊 分析cJSON代码库...")
        result = analyzer.analyze()
        print(f"✅ 分析完成，总共找到 {result['total_functions']} 个函数")
        
        # 测试的函数列表
        test_functions = [
            'malloc',
            'free', 
            'cJSON_Parse',
            'cJSON_Delete',
            'cJSON_CreateObject',
            'cJSON_GetObjectItem',
            'printf',  # 外部函数，不会出现在call graph中
            'nonexistent_function'  # 不存在的函数
        ]
        
        for func_name in test_functions:
            print(f"\n{'='*60}")
            print(f"🔍 测试函数: {func_name}")
            print('='*60)
            
            # 获取调用者列表
            callers = analyzer.get_function_callers(func_name)
            
            # 检查函数是否存在（基于call graph）
            function_exists = func_name in analyzer.call_graph.functions
            
            print(f"📋 函数信息:")
            print(f"   - 函数名: {func_name}")
            print(f"   - 是否存在: {function_exists}")
            print(f"   - 调用者数量: {len(callers)}")
            
            if not function_exists:
                print(f"   - 状态: 函数 {func_name} 不存在于当前分析的代码中")
            elif not callers:
                print(f"   - 状态: 没有找到调用者")
            else:
                print(f"   - 状态: 找到 {len(callers)} 个直接调用者")
            
            if callers:
                print(f"\n📞 调用者列表:")
                for i, caller in enumerate(callers, 1):
                    print(f"   {i:2d}. {caller}")
            
            print()
        
        print(f"\n{'='*80}")
        print("✅ 所有函数测试完成！")
        print("💡 说明:")
        print("   - 只显示直接调用者（depth=1）")
        print("   - 基于Call Graph分析结果")
        print("   - 比复杂的代码搜索更高效")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_call_graph_info():
    """测试Call Graph相关信息"""
    
    print("\n" + "=" * 80)
    print("📊 Call Graph信息测试")
    print("=" * 80)
    
    config_file = 'test/cjson_config.json'
    
    if not os.path.exists(config_file):
        print(f"❌ 配置文件不存在: {config_file}")
        return
    
    try:
        analyzer = RepoAnalyzer(config_file)
        analyzer.analyze()
        
        # 获取Call Graph摘要
        summary = analyzer.get_call_graph_summary()
        print(f"📈 Call Graph摘要:")
        print(f"   - 总函数数: {summary['total_functions']}")
        print(f"   - 调用边数: {summary['total_call_edges']}")
        print(f"   - 外部依赖: {summary['external_dependencies']}")
        print(f"   - 循环依赖: {summary['cycles_count']}")
        print(f"   - 叶子函数: {summary['leaf_functions_count']}")
        print(f"   - 根函数: {summary['root_functions_count']}")
        
        # 测试几个具体函数的依赖关系
        test_funcs = ['cJSON_Parse', 'malloc', 'main']
        
        for func_name in test_funcs:
            print(f"\n🔗 {func_name} 的关系:")
            
            # 获取调用者和被调用者
            callers = analyzer.get_direct_callers(func_name)
            callees = analyzer.get_direct_callees(func_name)
            
            print(f"   - 直接调用者: {len(callers)} 个")
            if callers:
                print(f"     {', '.join(sorted(list(callers))[:5])}{'...' if len(callers) > 5 else ''}")
            
            print(f"   - 直接被调用: {len(callees)} 个")  
            if callees:
                print(f"     {', '.join(sorted(list(callees))[:5])}{'...' if len(callees) > 5 else ''}")
        
    except Exception as e:
        print(f"❌ Call Graph信息测试失败: {e}")


def main():
    """主函数"""
    print("🚀 开始函数调用者接口测试")
    
    # 测试基本的调用者获取功能
    test_function_callers()
    
    # 测试Call Graph相关信息
    test_call_graph_info()
    
    print("\n" + "=" * 80)
    print("🎉 测试完成！")
    print("💡 总结:")
    print("   - 新接口基于现有Call Graph功能")
    print("   - 比代码搜索更高效、准确")
    print("   - 返回结构化的调用者信息")
    print("=" * 80)


if __name__ == '__main__':
    main() 