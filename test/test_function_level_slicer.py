#!/usr/bin/env python3
"""
函数级切片功能测试 - 测试benchmarks中各个库的函数切片
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from slicer.function_slice import slice_function_by_variable
from parser import RepoAnalyzer


def test_library_function_slice(config_file: str, library_name: str, target_functions: list, test_variables: dict):
    """
    测试指定库中函数的切片功能
    
    Args:
        config_file: 配置文件路径
        library_name: 库名称
        target_functions: 目标函数名列表
        test_variables: 函数名到测试变量的映射
    """
    print("=" * 80)
    print(f"📚 {library_name} 库函数级切片测试")
    print("=" * 80)
    
    # 检查配置文件是否存在
    if not os.path.exists(config_file):
        print(f"❌ 配置文件不存在: {config_file}")
        return False
    
    try:
        # 初始化分析器
        print("🔧 初始化分析器...")
        analyzer = RepoAnalyzer(config_file)
        
        # 分析代码
        print(f"📊 分析 {library_name} 代码库...")
        result = analyzer.analyze()
        print(f"✅ 分析完成，总共找到 {result['total_functions']} 个函数")
        
        # 获取所有函数
        functions = analyzer.get_functions()
        
        # 查找目标函数
        found_functions = {}
        for func in functions:
            if not func.is_declaration and func.name in target_functions:
                found_functions[func.name] = func
        
        if not found_functions:
            print(f"❌ 未找到任何目标函数: {target_functions}")
            return False
        
        print(f"\n🎯 找到 {len(found_functions)} 个目标函数:")
        for func_name in found_functions:
            print(f"  - {func_name}")
        
        # 对每个找到的函数进行切片测试
        success_count = 0
        for func_name, func in found_functions.items():
            print(f"\n{'='*60}")
            print(f"🔍 测试函数: {func_name}")
            print(f"📁 文件: {os.path.basename(func.file_path)}")
            print(f"📍 行号: {func.start_line}-{func.end_line}")
            print(f"{'='*60}")
            
            # 获取函数体
            function_body = func.get_body()
            if not function_body:
                print("❌ 无法获取函数体")
                continue
            
            # 显示函数体预览
            body_lines = function_body.split('\n')
            print(f"\n📖 函数体预览 (前10行):")
            for j, line in enumerate(body_lines[:10]):
                print(f"  {j+1:2d}: {line}")
            if len(body_lines) > 10:
                print(f"  ... (总共{len(body_lines)}行)")
            
            # 获取测试变量
            variables_to_test = test_variables.get(func_name, [])
            if not variables_to_test:
                # 自动检测变量
                variables_to_test = auto_detect_variables(function_body)
                print(f"\n🔍 自动检测到的变量: {variables_to_test}")
            else:
                print(f"\n🎯 预设测试变量: {variables_to_test}")
            
            # 对每个函数只测试一个参数变量
            if variables_to_test:
                var = variables_to_test[0]  # 只取第一个变量（通常是函数参数）
                print(f"\n🔬 切片变量: '{var}' (函数参数)")
                print("-" * 40)

                try:
                    # 使用新的切片功能，包含函数签名和保存到文件
                    slice_result = slice_function_by_variable(
                        function_body, var, language="c",
                        function_name=func_name, save_to_file=True
                    )
                    if slice_result.strip():
                        print("✅ 切片结果:")
                        # 显示切片结果，限制行数
                        slice_lines = slice_result.split('\n')
                        for i, line in enumerate(slice_lines[:20]):  # 增加显示行数
                            print(f"  {i+1:2d}: {line}")
                        if len(slice_lines) > 20:
                            print(f"  ... (总共{len(slice_lines)}行)")

                        # 显示统计信息
                        original_lines = len(function_body.split('\n'))
                        sliced_lines = len(slice_lines)
                        reduction = original_lines - sliced_lines
                        reduction_pct = (reduction / original_lines * 100) if original_lines > 0 else 0
                        print(f"\n📊 统计信息:")
                        print(f"   原始行数: {original_lines}")
                        print(f"   切片行数: {sliced_lines}")
                        print(f"   压缩率: {reduction_pct:.1f}%")

                        success_count += 1
                    else:
                        print("⚠️  未找到相关代码")
                except Exception as e:
                    print(f"❌ 切片失败: {e}")
            else:
                print("⚠️  未找到测试变量")
            
            print()
        
        print(f"\n📊 测试总结: 成功切片 {success_count} 个函数参数")
        return success_count > 0
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def auto_detect_variables(function_body: str) -> list:
    """自动检测函数体中的变量"""
    import re
    
    # 变量检测模式
    var_patterns = [
        r'^\s*(?:int|char|const|unsigned|size_t|double|float|void)\s+\*?\s*(\w+)',  # 基本类型
        r'^\s*cJSON\s*\*\s*(\w+)',  # cJSON指针
        r'^\s*unsigned\s+char\s+\*\s*(\w+)',  # unsigned char *
        r'^\s*cJSON_bool\s+(\w+)',  # cJSON_bool类型
        r'^\s*mz_\w+\s+(\w+)',  # miniz类型
        r'^\s*z_stream\s*\*?\s*(\w+)',  # zlib类型
        r'^\s*utf8_\w+\s+(\w+)',  # utf8类型
    ]
    
    detected_vars = set()
    type_keywords = {'int', 'char', 'const', 'unsigned', 'size_t', 'double', 'float', 'void', 'cJSON', 'bool'}
    
    body_lines = function_body.split('\n')
    for line in body_lines:
        for pattern in var_patterns:
            matches = re.findall(pattern, line)
            for match in matches:
                # 过滤掉类型关键字和控制流关键字
                if (match not in type_keywords and 
                    match not in ['if', 'while', 'for', 'switch', 'return', 'break', 'continue'] and
                    not match.endswith('_t') and  # 过滤类型后缀
                    len(match) > 1):  # 过滤单字符变量
                    detected_vars.add(match)
    
    # 优先选择一些常见的有意义的变量名
    preferred_vars = ['result', 'length', 'size', 'count', 'index', 'buffer', 'data', 'value', 'item', 'node']
    final_vars = []
    
    for pref_var in preferred_vars:
        if pref_var in detected_vars:
            final_vars.append(pref_var)
    
    # 添加其他检测到的变量
    for var in sorted(detected_vars):
        if var not in final_vars:
            final_vars.append(var)
    
    return final_vars[:5]  # 返回前5个变量


def test_cjson_library():
    """测试cJSON库 - 选择parse_number函数（复杂的数字解析逻辑）"""
    config_file = 'benchmarks/configs/cjson_config.json'
    target_functions = ['parse_number']  # 复杂的数字解析函数
    test_variables = {
        'parse_number': ['item']  # 函数参数作为切片起点
    }

    return test_library_function_slice(config_file, "cJSON", target_functions, test_variables)


def test_miniz_library():
    """测试miniz库 - 选择mz_deflate函数（复杂的压缩流处理）"""
    config_file = 'benchmarks/configs/miniz_config.json'
    target_functions = ['mz_deflate']  # 复杂的压缩流处理函数
    test_variables = {
        'mz_deflate': ['pStream']  # 函数参数作为切片起点
    }

    return test_library_function_slice(config_file, "miniz", target_functions, test_variables)


def test_zlib_library():
    """测试zlib库 - 选择deflate函数（复杂的压缩算法核心）"""
    config_file = 'benchmarks/configs/zlib_config.json'
    target_functions = ['deflate']  # 复杂的压缩算法核心函数
    test_variables = {
        'deflate': ['strm']  # 函数参数作为切片起点
    }

    return test_library_function_slice(config_file, "zlib", target_functions, test_variables)


def test_utf8_library():
    """测试utf8库 - 选择utf8str函数（复杂的字符串搜索算法）"""
    config_file = 'benchmarks/configs/utf8_config.json'
    target_functions = ['utf8str']  # 复杂的字符串搜索函数
    test_variables = {
        'utf8str': ['haystack']  # 函数参数作为切片起点
    }

    return test_library_function_slice(config_file, "utf8", target_functions, test_variables)


def main():
    """主测试函数"""
    print("🚀 开始函数级切片测试")
    print("测试目标: 每个库选择一个复杂函数，以函数参数作为切片起点")
    print()
    
    test_results = []
    
    # 测试各个库
    libraries = [
        ("cJSON", test_cjson_library),
        ("miniz", test_miniz_library), 
        ("zlib", test_zlib_library),
        ("utf8", test_utf8_library)
    ]
    
    for lib_name, test_func in libraries:
        try:
            print(f"\n🔄 开始测试 {lib_name} 库...")
            success = test_func()
            test_results.append((lib_name, success))
            print(f"{'✅' if success else '❌'} {lib_name} 库测试{'成功' if success else '失败'}")
        except Exception as e:
            print(f"❌ {lib_name} 库测试异常: {e}")
            test_results.append((lib_name, False))
    
    # 输出总结
    print("\n" + "="*80)
    print("📊 测试总结")
    print("="*80)
    
    success_count = sum(1 for _, success in test_results if success)
    total_count = len(test_results)
    
    for lib_name, success in test_results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {lib_name:10s}: {status}")
    
    print(f"\n总体结果: {success_count}/{total_count} 个库的复杂函数切片成功")

    if success_count == total_count:
        print("🎉 所有复杂函数切片测试通过！")
        print("✨ 每个库都成功展示了以函数参数为起点的切片能力")
    elif success_count > 0:
        print("⚠️  部分测试通过")
    else:
        print("💥 所有测试失败")


if __name__ == "__main__":
    main()
