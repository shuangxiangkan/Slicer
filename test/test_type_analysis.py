#!/usr/bin/env python3
"""
类型分析功能测试
"""

import os
import sys

# 添加父目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from parser.repo_analyzer import RepoAnalyzer


def test_miniz_type_analysis():
    """测试miniz库的类型分析"""
    print("🔍 开始测试miniz库的类型分析功能")
    print("=" * 80)
    
    # 使用miniz配置文件路径
    config_path = os.path.join(os.path.dirname(__file__), "benchmarks/configs/miniz_config.json")
    
    try:
        # 初始化分析器
        analyzer = RepoAnalyzer(config_path)
        
        # 运行分析
        print("📊 开始分析...")
        stats = analyzer.analyze(show_progress=True)
        
        print("\n" + "=" * 80)
        print("🔬 类型分析结果")
        print("=" * 80)
        
        # 获取类型注册表
        type_registry = analyzer.get_type_registry()
        
        # 显示类型统计
        type_stats = analyzer.get_type_statistics()
        print("📋 类型统计摘要:")
        print(f"  • 总计: {type_stats.get('total_types', 0)} 个类型")
        print(f"  • typedef: {type_stats.get('typedef', 0)} 个")
        print(f"  • 结构体: {type_stats.get('struct', 0)} 个")
        print(f"  • 联合体: {type_stats.get('union', 0)} 个")
        print(f"  • 枚举: {type_stats.get('enum', 0)} 个")
        print(f"  • 指针typedef: {type_stats.get('pointer_typedefs', 0)} 个")
        
        # 测试一些具体的类型
        print("\n🔍 具体类型分析:")
        test_types = ['mz_streamp', 'mz_ulong', 'mz_stream', 'uLong', 'Bytef']
        
        for type_name in test_types:
            print(f"\n--- 类型: {type_name} ---")
            analyzer.print_type_info(type_name)
            
            # 测试指针检查
            is_pointer, pointer_level = type_registry.is_pointer_type(type_name)
            print(f"   指针检查: is_pointer={is_pointer}, level={pointer_level}")
            
            # 测试基本类型检查
            is_basic = type_registry.is_basic_type(type_name)
            print(f"   基本类型: {is_basic}")
            
            # 获取类型链
            type_chain = type_registry.resolve_type_chain(type_name)
            print(f"   类型链: {' -> '.join(type_chain)}")
        
        # 测试函数参数的增强分析
        print("\n" + "=" * 80)
        print("🔧 函数参数增强分析")
        print("=" * 80)
        
        # 获取几个函数进行测试
        functions = analyzer.get_functions()
        test_functions = []
        
        # 查找一些有趣的函数
        for func in functions:
            if any(name in func.name for name in ['mz_', 'deflate', 'inflate']) and not func.is_declaration:
                test_functions.append(func)
                if len(test_functions) >= 5:  # 只测试前5个
                    break
        
        for i, func in enumerate(test_functions, 1):
            print(f"\n[{i}/{len(test_functions)}] 🔧 函数: {func.name}")
            print(f"📝 详细签名: {func.get_detailed_signature()}")
            print(f"📁 位置: {func.file_path}:{func.start_line}-{func.end_line}")
            
            # 返回类型分析
            ret_info = func.return_type_details
            print(f"↩️  返回类型: {ret_info.get_type_signature()}")
            print(f"   └─ 类型种类: {ret_info.get_type_kind()}")
            if ret_info.is_actually_pointer():
                print(f"   └─ {ret_info.get_pointer_analysis()}")
            print(f"   └─ 类型链: {' -> '.join(ret_info.get_type_chain())}")
            
            # 参数分析
            if func.parameter_details:
                print(f"📋 参数列表 ({len(func.parameter_details)} 个):")
                for j, param in enumerate(func.parameter_details, 1):
                    print(f"   {j}. {param.get_full_signature()}")
                    details = []
                    if param.is_actually_pointer():
                        details.append(param.get_pointer_analysis())
                    if param.is_const:
                        details.append("const")
                    if param.is_reference:
                        details.append("引用")
                    
                    type_kind = param.get_type_kind()
                    details.append(f"类型种类:{type_kind}")
                    
                    type_chain = param.get_type_chain()
                    if len(type_chain) > 1:
                        details.append(f"类型链:{' -> '.join(type_chain)}")
                    
                    if details:
                        print(f"      └─ {', '.join(details)}")
            else:
                print("📋 参数列表: 无参数")
            
            # 参数摘要
            summary = func.get_parameter_summary()
            if summary['total_params'] > 0:
                print(f"📊 参数摘要: 总数:{summary['total_params']}, 指针:{summary['pointer_params']}, const:{summary['const_params']}, 基本类型:{summary['basic_type_params']}")
        
        print("\n" + "=" * 80)
        print("✅ 类型分析测试完成！")
        print("=" * 80)
        
        # 最终统计
        print(f"📊 最终统计:")
        print(f"  • 文件数: {stats.get('total_files', 0)}")
        print(f"  • 函数数: {stats.get('total_functions', 0)}")
        print(f"  • 类型数: {type_stats.get('total_types', 0)}")
        print(f"  • 处理时间: {stats.get('processing_time', 0):.2f}秒")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_specific_typedef_examples():
    """测试具体的typedef示例"""
    print("\n🧪 测试具体的typedef示例")
    print("=" * 50)
    
    from parser.type_registry import TypeRegistry
    
    # 创建测试注册表
    registry = TypeRegistry()
    
    # 注册一些miniz中的典型typedef
    registry.register_typedef('mz_streamp', 'mz_stream *')
    registry.register_typedef('mz_ulong', 'unsigned long')
    registry.register_typedef('uLong', 'unsigned long')
    registry.register_typedef('Bytef', 'unsigned char')
    registry.register_typedef('voidpf', 'void *')
    
    # 测试类型解析
    test_cases = [
        'mz_streamp',
        'mz_ulong', 
        'const mz_streamp',
        'mz_streamp *',
        'const unsigned char *',
        'voidpf'
    ]
    
    for type_name in test_cases:
        print(f"\n🔍 测试类型: '{type_name}'")
        is_pointer, pointer_level = registry.is_pointer_type(type_name)
        is_basic = registry.is_basic_type(type_name)
        
        print(f"  指针类型: {is_pointer} (层级: {pointer_level})")
        print(f"  基本类型: {is_basic}")
        
        type_info = registry.lookup_type(type_name)
        if type_info:
            final_type, is_final_pointer, final_pointer_level = type_info.get_final_type()
            print(f"  最终类型: {final_type}")
            print(f"  最终指针: {is_final_pointer} (层级: {final_pointer_level})")


if __name__ == "__main__":
    # 运行主要测试
    test_miniz_type_analysis()
    
    # 运行typedef示例测试
    test_specific_typedef_examples() 