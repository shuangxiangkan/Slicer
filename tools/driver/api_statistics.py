#!/usr/bin/env python3
"""
API统计工具
统计benchmarks中每个library的:
1. API数量
2. 有usage的API数量 
3. 在test中有usage的API数量
"""

import sys
import os
from pathlib import Path
import json
import logging
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from parser.repo_analyzer import RepoAnalyzer

# 配置日志
logging.basicConfig(level=logging.WARNING)

class APIStatistics:
    """API统计类"""
    
    def __init__(self):
        """初始化"""
        self.libraries = {
            'cJSON': {
                'config_file': 'benchmarks/configs/cjson_config.json',
                'api_keywords': ['CJSON_PUBLIC']
            },
            'miniz': {
                'config_file': 'benchmarks/configs/miniz_config.json', 
                'api_keywords': ['MINIZ_EXPORT']
            },
            'utf8': {
                'config_file': 'benchmarks/configs/utf8_config.json',
                'api_keywords': ['utf8']  # utf8库的函数都以utf8开头
            },
            'zlib': {
                'config_file': 'benchmarks/configs/zlib_config.json',
                'api_keywords': ['ZEXPORT', 'ZEXTERN']
            }
        }
        
        # 切换到项目根目录
        os.chdir(project_root)
        
        # 创建输出目录
        self.output_dir = Path('/home/kansx/SVF-Tools/Slicer/tools/driver/library_api_usage_statistics')
        self.output_dir.mkdir(exist_ok=True)
    
    def get_usage_details(self, file_path, function_name):
        """
        获取函数在文件中的详细usage信息
        返回: [(line_number, context_lines), ...]
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            usages = []
            for i, line in enumerate(lines, 1):
                if function_name in line:
                    # 获取前后各2行作为上下文
                    start_idx = max(0, i - 3)
                    end_idx = min(len(lines), i + 2)
                    context_lines = []
                    for j in range(start_idx, end_idx):
                        prefix = ">>> " if j == i - 1 else "    "
                        context_lines.append(f"{prefix}{j+1:4d}: {lines[j].rstrip()}")
                    
                    usages.append((i, context_lines))
            
            return usages
        except Exception as e:
            print(f"   ❌ 读取文件失败 {file_path}: {e}")
            return []
    
    def get_all_functions_with_keywords(self, analyzer, keywords):
        """获取包含关键字的所有函数"""
        all_api_functions = []
        
        for keyword in keywords:
            api_functions = analyzer.get_api_functions(keyword)
            all_api_functions.extend(api_functions)
        
        # 去重（基于函数名）
        seen_names = set()
        unique_functions = []
        for func in all_api_functions:
            if func.name not in seen_names:
                seen_names.add(func.name)
                unique_functions.append(func)
        
        return unique_functions
    
    def count_api_with_usage(self, analyzer, api_functions):
        """统计有usage的API数量"""
        api_with_usage = 0
        api_usage_details = {}
        
        for func in api_functions:
            # 查找所有文件中的usage
            all_usage = analyzer.find_usage_in_all_files(function_name=func.name)
            
            if all_usage:
                api_with_usage += 1
                file_details = {}
                
                for file_path, callers in all_usage.items():
                    # 获取详细的usage信息（行号和上下文）
                    usage_details = self.get_usage_details(file_path, func.name)
                    
                    file_details[file_path] = {
                        'callers': callers,
                        'usage_count': len(usage_details),
                        'usage_locations': [
                            {
                                'line_number': line_num,
                                'context': context_lines
                            }
                            for line_num, context_lines in usage_details
                        ]
                    }
                
                api_usage_details[func.name] = {
                    'total_files': len(all_usage),
                    'total_usages': sum(len(self.get_usage_details(fp, func.name)) for fp in all_usage.keys()),
                    'files': file_details
                }
        
        return api_with_usage, api_usage_details
    
    def count_api_with_test_usage(self, analyzer, api_functions):
        """统计在test中有usage的API数量"""
        api_with_test_usage = 0
        test_usage_details = {}
        
        for func in api_functions:
            # 查找测试文件中的usage
            test_usage = analyzer.find_usage_in_test_files(function_name=func.name)
            
            if test_usage:
                api_with_test_usage += 1
                test_file_details = {}
                
                for file_path, callers in test_usage.items():
                    # 获取详细的usage信息（行号和上下文）
                    usage_details = self.get_usage_details(file_path, func.name)
                    
                    test_file_details[file_path] = {
                        'callers': callers,
                        'usage_count': len(usage_details),
                        'usage_locations': [
                            {
                                'line_number': line_num,
                                'context': context_lines
                            }
                            for line_num, context_lines in usage_details
                        ]
                    }
                
                test_usage_details[func.name] = {
                    'test_files': len(test_usage),
                    'total_test_usages': sum(len(self.get_usage_details(fp, func.name)) for fp in test_usage.keys()),
                    'files': test_file_details
                }
        
        return api_with_test_usage, test_usage_details
    
    def analyze_library(self, lib_name, config):
        """分析单个library"""
        print(f"\n📚 分析库: {lib_name}")
        print("-" * 50)
        
        # 检查配置文件是否存在
        if not os.path.exists(config['config_file']):
            print(f"❌ 配置文件不存在: {config['config_file']}")
            return None
        
        try:
            # 初始化分析器
            analyzer = RepoAnalyzer(config['config_file'])
            
            # 分析代码
            print("正在分析代码...")
            result = analyzer.analyze()
            print(f"✅ 基础分析完成，总共找到 {result['total_functions']} 个函数")
            
            # 获取API函数
            print(f"🔍 搜索API关键字: {', '.join(config['api_keywords'])}")
            api_functions = self.get_all_functions_with_keywords(analyzer, config['api_keywords'])
            
            if not api_functions:
                print("⚠️  未找到API函数")
                return {
                    'library': lib_name,
                    'total_functions': result['total_functions'],
                    'api_count': 0,
                    'api_with_usage': 0,
                    'api_with_test_usage': 0,
                    'usage_rate': 0.0,
                    'test_usage_rate': 0.0
                }
            
            print(f"📊 找到 {len(api_functions)} 个API函数")
            
            # 统计有usage的API
            print("🔍 统计API usage...")
            api_with_usage, usage_details = self.count_api_with_usage(analyzer, api_functions)
            
            # 统计在test中有usage的API
            print("🧪 统计test usage...")
            api_with_test_usage, test_usage_details = self.count_api_with_test_usage(analyzer, api_functions)
            
            # 计算比率
            usage_rate = (api_with_usage / len(api_functions)) * 100 if api_functions else 0
            test_usage_rate = (api_with_test_usage / len(api_functions)) * 100 if api_functions else 0
            
            # 统计没有usage的API
            api_functions_with_usage = set(usage_details.keys())
            api_functions_with_test_usage = set(test_usage_details.keys())
            all_api_functions = set(func.name for func in api_functions)
            
            apis_without_usage = list(all_api_functions - api_functions_with_usage)
            apis_without_test_usage = list(all_api_functions - api_functions_with_test_usage)
            
            # 输出结果
            print(f"\n📈 统计结果:")
            print(f"   总API数量: {len(api_functions)}")
            print(f"   有usage的API: {api_with_usage} ({usage_rate:.1f}%)")
            print(f"   有test usage的API: {api_with_test_usage} ({test_usage_rate:.1f}%)")
            print(f"   完全没有usage的API: {len(apis_without_usage)}")
            print(f"   没有test usage的API: {len(apis_without_test_usage)}")
            
            return {
                'library': lib_name,
                'total_functions': result['total_functions'],
                'api_count': len(api_functions),
                'api_with_usage': api_with_usage,
                'api_with_test_usage': api_with_test_usage,
                'usage_rate': usage_rate,
                'test_usage_rate': test_usage_rate,
                'api_functions': [func.name for func in api_functions],
                'apis_without_usage': apis_without_usage,
                'apis_without_test_usage': apis_without_test_usage,
                'usage_details': usage_details,
                'test_usage_details': test_usage_details
            }
            
        except Exception as e:
            print(f"❌ 分析失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run_statistics(self):
        """运行统计分析"""
        print("🚀 API统计分析工具")
        print("=" * 60)
        
        results = []
        
        for lib_name, config in self.libraries.items():
            result = self.analyze_library(lib_name, config)
            if result:
                results.append(result)
                # 为每个library单独保存文件
                self.save_library_report(lib_name, result)
        
        # 输出汇总报告
        self.print_summary_report(results)
        
        # 保存汇总报告
        self.save_summary_report(results)
        
        return results
    
    def print_summary_report(self, results):
        """打印汇总报告"""
        print("\n" + "=" * 60)
        print("📊 汇总报告")
        print("=" * 60)
        
        if not results:
            print("❌ 没有成功分析的库")
            return
        
        # 表格头
        print(f"{'库名':<10} {'总函数':<8} {'API数量':<8} {'有Usage':<8} {'Test Usage':<10} {'无Usage':<8} {'无Test':<8} {'Usage率':<8} {'Test率':<8}")
        print("-" * 90)
        
        total_apis = 0
        total_with_usage = 0
        total_with_test_usage = 0
        total_without_usage = 0
        total_without_test_usage = 0
        
        for result in results:
            total_apis += result['api_count']
            total_with_usage += result['api_with_usage']
            total_with_test_usage += result['api_with_test_usage']
            
            apis_without_usage = len(result.get('apis_without_usage', []))
            apis_without_test_usage = len(result.get('apis_without_test_usage', []))
            total_without_usage += apis_without_usage
            total_without_test_usage += apis_without_test_usage
            
            print(f"{result['library']:<10} "
                  f"{result['total_functions']:<8} "
                  f"{result['api_count']:<8} "
                  f"{result['api_with_usage']:<8} "
                  f"{result['api_with_test_usage']:<10} "
                  f"{apis_without_usage:<8} "
                  f"{apis_without_test_usage:<8} "
                  f"{result['usage_rate']:<7.1f}% "
                  f"{result['test_usage_rate']:<7.1f}%")
        
        # 总计
        print("-" * 90)
        overall_usage_rate = (total_with_usage / total_apis) * 100 if total_apis else 0
        overall_test_rate = (total_with_test_usage / total_apis) * 100 if total_apis else 0
        
        print(f"{'总计':<10} "
              f"{'N/A':<8} "
              f"{total_apis:<8} "
              f"{total_with_usage:<8} "
              f"{total_with_test_usage:<10} "
              f"{total_without_usage:<8} "
              f"{total_without_test_usage:<8} "
              f"{overall_usage_rate:<7.1f}% "
              f"{overall_test_rate:<7.1f}%")
    
    def save_library_report(self, lib_name, result):
        """为单个library保存详细报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"{lib_name}_api_usage_report_{timestamp}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"💾 {lib_name} 详细报告已保存到: {report_file}")
            
        except Exception as e:
            print(f"❌ 保存 {lib_name} 报告失败: {e}")
    
    def save_summary_report(self, results):
        """保存汇总报告到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"summary_api_statistics_{timestamp}.json"
        
        # 创建汇总数据
        summary_data = {
            'timestamp': timestamp,
            'total_libraries': len(results),
            'libraries_summary': [],
            'overall_statistics': {
                'total_apis': sum(r['api_count'] for r in results),
                'total_with_usage': sum(r['api_with_usage'] for r in results),
                'total_with_test_usage': sum(r['api_with_test_usage'] for r in results),
                'total_without_usage': sum(len(r.get('apis_without_usage', [])) for r in results),
                'total_without_test_usage': sum(len(r.get('apis_without_test_usage', [])) for r in results)
            }
        }
        
        for result in results:
            summary_data['libraries_summary'].append({
                'library': result['library'],
                'total_functions': result['total_functions'],
                'api_count': result['api_count'],
                'api_with_usage': result['api_with_usage'],
                'api_with_test_usage': result['api_with_test_usage'],
                'apis_without_usage': len(result.get('apis_without_usage', [])),
                'apis_without_test_usage': len(result.get('apis_without_test_usage', [])),
                'usage_rate': result['usage_rate'],
                'test_usage_rate': result['test_usage_rate']
            })
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 汇总报告已保存到: {report_file}")
            
        except Exception as e:
            print(f"❌ 保存汇总报告失败: {e}")


def main():
    """主函数"""
    statistics = APIStatistics()
    results = statistics.run_statistics()
    
    print("\n" + "=" * 60)
    print("✅ 统计完成！")
    
    print("\n💡 说明:")
    print("   - API数量: 包含指定关键字的函数数量")
    print("   - 有Usage: 在所有文件中被调用的API数量")
    print("   - Test Usage: 在测试文件中被调用的API数量")
    print("   - Usage率: 有usage的API占总API的百分比")
    print("   - Test率: 有test usage的API占总API的百分比")
    print("\n📁 输出文件:")
    print("   - library_api_usage_statistics/ 目录下为每个library保存详细报告")
    print("   - 每个API的usage包含具体的文件位置和行号信息")
    print("   - 汇总报告包含所有library的统计概览")


if __name__ == '__main__':
    main()