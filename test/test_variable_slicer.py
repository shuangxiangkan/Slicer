#!/usr/bin/env python3
"""
变量切片功能测试 - 简化版本，只测试cJSON项目中的一个函数
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from slicer.slice import slice_function_by_variable
from parser import RepoAnalyzer

def test_cjson_single_function():
    """测试cJSON项目中的单个函数变量切片"""
    print("=" * 60)
    print("cJSON项目单函数变量切片测试")
    print("=" * 60)
    
    config_file = 'benchmarks/configs/cjson_config.json'
    
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
        
        # 获取所有函数
        functions = analyzer.get_functions()
        
        # 找到目标函数 - 优先选择parse_number
        target_func = None
        for func in functions:
            if not func.is_declaration and func.name == 'parse_number':
                target_func = func
                break
        
        # 如果没找到parse_number，找其他函数
        if not target_func:
            for func in functions:
                if not func.is_declaration and func.name in ['parse_string', 'cJSON_Parse', 'parse_value']:
                    target_func = func
                    break
        
        # 最后备选：任意非声明函数
        if not target_func:
            for func in functions:
                if not func.is_declaration:
                    target_func = func
                    break
        
        if not target_func:
            print("❌ 未找到合适的测试函数")
            return
        
        print(f"\n选择测试函数: {target_func.name}")
        print(f"文件: {os.path.basename(target_func.file_path)}")
        print(f"行号: {target_func.start_line}-{target_func.end_line}")
        print("=" * 40)
        
        # 获取函数体
        function_body = target_func.get_body()
        if not function_body:
            print("❌ 无法获取函数体")
            return
        
        print(f"函数体预览 (前15行):")
        body_lines = function_body.split('\n')
        for j, line in enumerate(body_lines[:15]):
            print(f"  {j+1:2d}: {line}")
        if len(body_lines) > 15:
            print(f"  ... (总共{len(body_lines)}行)")
        
        # 改进的变量检测
        print(f"\n🔍 自动检测变量:")
        import re
        
        # 更精确的变量检测模式
        var_patterns = [
            r'^\s*(?:int|char|const|unsigned|size_t|double|float)\s+\*?\s*(\w+)',  # 基本类型
            r'^\s*cJSON\s*\*\s*(\w+)',  # cJSON指针
            r'^\s*unsigned\s+char\s+\*\s*(\w+)',  # unsigned char *
            r'^\s*cJSON_bool\s+(\w+)',  # cJSON_bool类型
        ]
        
        detected_vars = set()
        type_keywords = {'int', 'char', 'const', 'unsigned', 'size_t', 'double', 'float', 'cJSON', 'bool'}
        
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
        
        print(f"检测到的变量: {sorted(list(detected_vars))}")
        
        # 选择一个合适的变量进行测试
        # 优先选择一些常见的有意义的变量名
        preferred_vars = ['number', 'result', 'length', 'size', 'count', 'index', 'buffer']
        test_var = None
        
        for pref_var in preferred_vars:
            if pref_var in detected_vars:
                test_var = pref_var
                break
        
        # 如果没有找到偏好变量，选择第一个
        if not test_var and detected_vars:
            test_var = sorted(list(detected_vars))[0]
        
        if test_var:
            print(f"\n测试变量: '{test_var}'")
            print("=" * 40)
            
            try:
                slice_result = slice_function_by_variable(function_body, test_var, language="c")
                if slice_result.strip():
                    print("切片结果:")
                    print(slice_result)
                else:
                    print("(未找到相关代码)")
            except Exception as e:
                print(f"切片失败: {e}")
        else:
            print("未检测到合适的变量")
            # 尝试手动指定一个常见变量
            manual_vars = ['number', 'i', 'length', 'size', 'result']
            for var in manual_vars:
                if var in function_body:
                    print(f"\n手动测试变量: '{var}'")
                    print("=" * 40)
                    try:
                        slice_result = slice_function_by_variable(function_body, var, language="c")
                        if slice_result.strip():
                            print("切片结果:")
                            print(slice_result)
                            break
                    except Exception as e:
                        continue
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cjson_single_function() 