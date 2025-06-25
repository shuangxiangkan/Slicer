#!/usr/bin/env python3
"""参数切片分析演示脚本"""

import sys
import os

# 添加当前目录到路径，以便导入tools和slicer
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from slicer.slicer_core import CFunctionSlicer
from slicer.output_utils import print_parameter_slice_result, save_parameter_slice_to_file


def demo_parameter_slice():
    """演示参数切片分析功能"""
    
    # 示例代码：复杂的参数交互
    test_code = '''
int complex_function(int a, int b, int c) {
    int temp1 = a + b;
    int temp2 = c * 2;
    
    if (temp1 > 10) {
        b = temp1 + 5;
        temp2 = b * c;
    }
    
    int result = temp1 + temp2;
    
    if (a > 0) {
        result = result * a;
    }
    
    return result;
}
'''
    
    print("参数切片分析演示")
    print("=" * 60)
    
    # 创建切片器
    slicer = CFunctionSlicer("c")
    
    # 分析函数
    print("正在分析函数 'complex_function'...")
    slicer.analyze_function(test_code, "complex_function")
    print("函数分析完成！\n")
    
    # 执行参数切片分析
    print("执行参数切片分析...")
    result = slicer.perform_parameter_slice_analysis(test_code)
    
    # 打印结果
    print_parameter_slice_result(result)
    
    # 保存分析结果
    output_file = save_parameter_slice_to_file(result, "complex_example.c", "complex_function")
    print(f"分析结果已保存到: {output_file}")
    
    print("\n" + "=" * 60)
    print("代码片段分析：")
    print("=" * 60)
    
    # 显示具体的代码片段
    for snippet_name, snippet_code in result.slice_code_snippets.items():
        print(f"\n📋 {snippet_name}:")
        print("-" * 40)
        print(snippet_code)
        print("\n" + "🤖 建议问大模型的问题：")
        if "forward" in snippet_name:
            param_name = snippet_name.split('_')[1]
            print(f"   '参数{param_name}是否会影响这些代码行的执行？是否存在数据流依赖？'")
        elif "return" in snippet_name:
            print("   '这些代码行是否会影响函数的返回值？存在什么样的数据流关系？'")
        elif "affects" in snippet_name:
            params = snippet_name.split('_')[1::2]  # 提取参数名
            print(f"   '参数{params[0]}是否会影响参数{params[1]}的值？是否存在数据流依赖？'")
        print()


if __name__ == "__main__":
    demo_parameter_slice() 