import sys
import os

# 将项目根目录添加到Python模块搜索路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.repo_analyzer import RepoAnalyzer

def main():
    # 使用直接参数方式初始化RepoAnalyzer，分析cJSON库
    library_path = os.path.join(os.path.dirname(__file__), "../benchmarks/cJSON")
    library_path = os.path.abspath(library_path)
    
    analyzer = RepoAnalyzer(
        library_path=library_path,
        header_files=["cJSON.h"],
        include_files=["cJSON.h", "cJSON.c"],
        exclude_files=[]
    )

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

    print(f"\n总计找到 {len(functions)} 个函数")
    print(f"其中声明：{len(declarations)} 个")
    print(f"其中定义：{len(definitions)} 个")

if __name__ == "__main__":
    main()