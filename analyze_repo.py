#!/usr/bin/env python3
"""
简化的代码仓库分析工具
使用方法: python analyze_repo.py <目录或文件路径> [选项]
"""

import sys
import argparse
import logging
from parser import RepoAnalyzer, setup_logging

# 配置日志
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='C/C++ 代码仓库函数分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python analyze_repo.py .                    # 分析当前目录
  python analyze_repo.py example.c            # 分析单个文件
  python analyze_repo.py /path/to/project     # 分析指定项目
  python analyze_repo.py . --search main      # 搜索包含"main"的函数
  python analyze_repo.py . --report report.md # 生成分析报告
  python analyze_repo.py . --flat --no-details # 简化输出
        """
    )
    
    parser.add_argument('path', help='要分析的文件或目录路径')
    parser.add_argument('--no-recursive', action='store_true', 
                       help='不递归搜索子目录')
    parser.add_argument('--no-progress', action='store_true', 
                       help='不显示处理进度')
    parser.add_argument('--no-details', action='store_true', 
                       help='不显示详细信息（行号、文件路径等）')
    parser.add_argument('--flat', action='store_true', 
                       help='平铺显示函数，不按文件分组')
    parser.add_argument('--search', type=str, 
                       help='搜索函数名匹配的模式（支持正则表达式）')
    parser.add_argument('--case-sensitive', action='store_true', 
                       help='区分大小写搜索')
    parser.add_argument('--report', type=str, 
                       help='保存分析报告到指定文件')
    parser.add_argument('--duplicates-only', action='store_true', 
                       help='只显示重复的函数定义')
    parser.add_argument('--stats-only', action='store_true', 
                       help='只显示统计信息，不显示函数列表')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='显示详细的日志信息')
    parser.add_argument('--debug', action='store_true',
                       help='显示调试信息')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        setup_logging(logging.DEBUG)
    elif args.verbose:
        setup_logging(logging.INFO)
    else:
        setup_logging(logging.WARNING)
    
    # 创建分析器
    analyzer = RepoAnalyzer()
    
    try:
        print(f"🚀 开始分析: {args.path}")
        print("=" * 60)
        
        logger.info(f"开始分析路径: {args.path}")
        
        # 执行分析
        result = analyzer.analyze_repository(
            args.path, 
            recursive=not args.no_recursive,
            show_progress=not args.no_progress
        )
        
        if not result:
            print("❌ 分析失败或未找到任何文件")
            logger.error("分析失败")
            return 1
        
        # 处理搜索模式
        if args.search:
            print(f"\n🔍 搜索函数名包含 '{args.search}' 的函数:")
            print("=" * 60)
            matched = analyzer.search_functions(args.search, args.case_sensitive)
            if matched:
                # 为搜索结果创建临时的打印函数
                _print_functions_for_search(matched, not args.no_details)
            else:
                print("❌ 没有找到匹配的函数")
            return 0
        
        # 只显示重复函数
        if args.duplicates_only:
            analyzer.print_duplicate_functions()
            return 0
        
        # 只显示统计信息
        if args.stats_only:
            print("\n📊 分析完成！")
            return 0
        
        # 显示所有函数
        if not args.stats_only:
            analyzer.print_all_functions(
                group_by_file=not args.flat, 
                show_details=not args.no_details
            )
            
            # 显示重复函数（如果有）
            if analyzer.analysis_stats.get('duplicate_functions'):
                analyzer.print_duplicate_functions()
        
        # 保存报告
        if args.report:
            analyzer.save_analysis_report(args.report)
        
        logger.info("分析完成")
        return 0
        
    except KeyboardInterrupt:
        print("\n❌ 用户中断分析")
        logger.warning("用户中断分析")
        return 1
    except Exception as e:
        print(f"❌ 分析出错: {e}")
        logger.error(f"分析出错: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


def _print_functions_for_search(functions, show_details=True):
    """为搜索结果打印函数列表"""
    from pathlib import Path
    
    if not functions:
        print("未找到任何函数")
        return
    
    print(f"找到 {len(functions)} 个匹配的函数:")
    print("=" * 80)
    
    # 按文件分组
    files_functions = {}
    for func in functions:
        file_name = Path(func.file_path).name if func.file_path else "Unknown"
        if file_name not in files_functions:
            files_functions[file_name] = []
        files_functions[file_name].append(func)
    
    for file_name, file_functions in files_functions.items():
        print(f"\n📁 文件: {file_name}")
        print("-" * 60)
        
        for i, func in enumerate(file_functions, 1):
            decl_marker = "🔗" if func.is_declaration else "🔧"
            print(f"{i:2d}. {decl_marker} {func}")
            
            if show_details:
                print(f"    📍 位置: 第{func.start_line}-{func.end_line}行")
                if func.file_path:
                    print(f"    📂 文件: {func.file_path}")
                print()
    
    # 统计信息
    definitions = [f for f in functions if not f.is_declaration]
    declarations = [f for f in functions if f.is_declaration]
    
    print("=" * 80)
    print("统计信息:")
    print(f"  总函数数: {len(functions)}")
    print(f"  函数定义: {len(definitions)}")
    print(f"  函数声明: {len(declarations)}")


if __name__ == "__main__":
    sys.exit(main()) 