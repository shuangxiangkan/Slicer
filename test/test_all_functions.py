import sys
import os

# 将项目根目录添加到Python模块搜索路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.repo_analyzer import RepoAnalyzer

def main():
    # 使用 benchmarks/utf8/utf8.h 进行测试
    # test_file = 'benchmarks/utf8/utf8.h'
    config_path = os.path.join(os.path.dirname(__file__), "../benchmarks/configs/cjson_config.json")
    analyzer = RepoAnalyzer(config_path)

    # 分析文件中的所有函数
    analyzer.analyze()
    functions = analyzer.get_functions()

    # 分离函数声明和定义
    declarations = [f for f in functions if f.is_declaration]
    definitions = [f for f in functions if not f.is_declaration]

    print("--- Function Declarations ---")
    for func in declarations:
        print(f"函数声明：{func.name}")
        print(f"返回类型：{func.return_type}")
        param_list = []
        for param in func.parameter_details:
            param_str = f"{param.param_type} {param.name if param.name else ''}".strip()
            param_list.append(param_str)
        print(f"参数列表：{', '.join(param_list)}")
        print(f"作用域：{func.scope}")
        print(f"位置：第{func.start_line}-{func.end_line}行")
        print("--------------------------------------------------------------------------------")

    print("\n--- Function Definitions ---")
    for func in definitions:
        print(f"函数定义：{func.name}")
        print(f"返回类型：{func.return_type}")
        param_list = []
        for param in func.parameter_details:
            param_str = f"{param.param_type} {param.name if param.name else ''}".strip()
            param_list.append(param_str)
        print(f"参数列表：{', '.join(param_list)}")
        print(f"作用域：{func.scope}")
        print(f"位置：第{func.start_line}-{func.end_line}行")
        print("--------------------------------------------------------------------------------")

if __name__ == "__main__":
    main()