#!/usr/bin/env python3
"""
简化的代码仓库分析工具
使用方法: python analyze_repo.py <目录或文件路径> [选项]
"""

import sys
import argparse
from parser import RepoAnalyzer

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
    
    args = parser.parse_args()
    
    # 创建分析器
    analyzer = RepoAnalyzer()
    
    try:
        print(f"🚀 开始分析: {args.path}")
        print("=" * 60)
        
        # 执行分析
        result = analyzer.analyze_repository(
            args.path, 
            recursive=not args.no_recursive,
            show_progress=not args.no_progress
        )
        
        if not result:
            print("❌ 分析失败或未找到任何文件")
            return 1
        
        # 处理搜索模式
        if args.search:
            print(f"\n🔍 搜索函数名包含 '{args.search}' 的函数:")
            print("=" * 60)
            matched = analyzer.search_functions(args.search, args.case_sensitive)
            if matched:
                analyzer.function_extractor.print_functions(matched, not args.no_details)
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
        
        return 0
        
    except KeyboardInterrupt:
        print("\n❌ 用户中断分析")
        return 1
    except Exception as e:
        print(f"❌ 分析出错: {e}")
        import traceback
        if "--debug" in sys.argv:
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 