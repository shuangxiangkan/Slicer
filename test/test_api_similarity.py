#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试libtiff API相似度计算
获取libtiff中每个API最相近的前三个API
"""

import sys
import os
from pathlib import Path
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from parser.repo_analyzer import RepoAnalyzer
from tools.driver.similarity_analyzer import APISimilarityAnalyzer


class LibtiffAPISimilarity:
    """libtiff API相似度分析类"""
    
    def __init__(self):
        """初始化"""
        # libtiff配置
        self.libtiff_config = {
            'config_file': 'benchmarks/configs/libtiff_config.json',
            'api_keywords': ['extern'],
            'api_prefix': 'TIFF'  # libtiff的API函数以TIFF开头
        }
        
        # 切换到项目根目录
        os.chdir(project_root)
        
        # 创建输出目录
        self.output_dir = Path('tools/driver/library_api_similarity_results')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化API相似性分析器
        self.similarity_analyzer = APISimilarityAnalyzer(similarity_threshold=0.1)
    
    def get_all_functions_with_keywords(self, analyzer, keywords, api_prefix=None):
        """获取包含关键字的所有函数"""
        all_api_functions = []
        
        # 获取header_files配置
        header_files = None
        if hasattr(analyzer, 'config_parser') and analyzer.config_parser:
            header_files = analyzer.config_parser.get_header_files()
        
        for keyword in keywords:
            api_functions = analyzer.get_api_functions(keyword, header_files=header_files, api_prefix=api_prefix)
            all_api_functions.extend(api_functions)
        
        # 去重（基于函数名）
        seen_names = set()
        unique_functions = []
        for func in all_api_functions:
            if func.name not in seen_names:
                seen_names.add(func.name)
                unique_functions.append(func)
        
        return unique_functions
    
    def analyze_api_similarity(self):
        """分析libtiff API相似度"""
        print("🚀 libtiff API相似度分析工具")
        print("=" * 60)
        
        # 检查配置文件是否存在
        config_file = self.libtiff_config['config_file']
        if not os.path.exists(config_file):
            print(f"❌ 配置文件不存在: {config_file}")
            return None
        
        try:
            # 初始化分析器
            print(f"📚 分析库: libtiff")
            print("-" * 50)
            analyzer = RepoAnalyzer(config_file)
            
            # 分析代码
            print("正在分析代码...")
            result = analyzer.analyze()
            print(f"✅ 基础分析完成，总共找到 {result['total_functions']} 个函数")
            
            # 获取API函数
            api_prefix = self.libtiff_config.get('api_prefix')
            print(f"🔍 搜索API关键字: {', '.join(self.libtiff_config['api_keywords'])}")
            if api_prefix:
                print(f"🏷️  限制函数前缀: '{api_prefix}'")
            
            api_functions = self.get_all_functions_with_keywords(
                analyzer, 
                self.libtiff_config['api_keywords'], 
                api_prefix
            )
            
            if not api_functions:
                print("⚠️  未找到API函数")
                return None
            
            print(f"📊 找到 {len(api_functions)} 个API函数")
            
            # 获取所有函数（用于相似度比较）
            all_functions = analyzer.get_functions()
            print(f"📋 总共有 {len(all_functions)} 个函数可用于相似度比较")
            
            # 计算每个API的相似度
            print("\n🔍 开始计算API相似度...")
            print("=" * 60)
            
            similarity_results = {}
            
            for i, target_api in enumerate(api_functions, 1):
                target_signature = target_api.get_signature()
                print(f"\n[{i}/{len(api_functions)}] 分析API: {target_api.name}")
                print(f"   完整签名: {target_signature}")
                
                # 查找最相似的前3个API
                similar_apis = self.similarity_analyzer.find_most_similar_apis(
                    target_function=target_api,
                    all_functions=all_functions,
                    similarity_threshold=0.1,  # 降低阈值以获得更多结果
                    max_results=3
                )
                
                if similar_apis:
                    print(f"   找到 {len(similar_apis)} 个相似API:")
                    for j, (similar_func, score) in enumerate(similar_apis, 1):
                        similar_signature = similar_func.get_signature()
                        print(f"      {j}. {similar_func.name} (相似度: {score:.3f})")
                        print(f"         签名: {similar_signature}")
                    
                    similarity_results[target_api.name] = {
                        'target_signature': target_signature,
                        'similar_apis': [
                            {
                                'name': func.name,
                                'similarity': score,
                                'signature': func.get_signature(),
                                'return_type': func.return_type,
                                'parameters': func.parameters
                            }
                            for func, score in similar_apis
                        ]
                    }
                else:
                    print("   ❌ 未找到相似的API")
                    similarity_results[target_api.name] = {
                        'target_signature': target_signature,
                        'similar_apis': []
                    }
            
            # 输出汇总结果
            print("\n" + "=" * 60)
            print("📊 相似度分析汇总")
            print("=" * 60)
            
            apis_with_similar = sum(1 for results in similarity_results.values() if results.get('similar_apis', []))
            print(f"总API数量: {len(api_functions)}")
            print(f"找到相似API的数量: {apis_with_similar}")
            print(f"相似度覆盖率: {(apis_with_similar/len(api_functions)*100):.1f}%")
            
            # 保存结果到文件
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f'libtiff_api_similarity_results_{timestamp}.json'
            output_data = {
                'library': 'libtiff',
                'total_apis': len(api_functions),
                'apis_with_similar': apis_with_similar,
                'coverage_rate': apis_with_similar/len(api_functions)*100,
                'api_list': [func.name for func in api_functions],
                'similarity_results': similarity_results
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 结果已保存到: {output_file}")
            
            return output_data
            
        except Exception as e:
            print(f"❌ 分析失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def print_detailed_results(self, results):
        """打印详细的相似度结果"""
        if not results:
            return
        
        print("\n" + "=" * 80)
        print("📋 详细相似度结果")
        print("=" * 80)
        
        for api_name, api_data in results['similarity_results'].items():
            print(f"\n🎯 API: {api_name}")
            print(f"   完整签名: {api_data.get('target_signature', 'N/A')}")
            similar_apis = api_data.get('similar_apis', [])
            if similar_apis:
                for i, similar in enumerate(similar_apis, 1):
                    print(f"   {i}. {similar['name']} (相似度: {similar['similarity']:.3f})")
                    print(f"      完整签名: {similar.get('signature', 'N/A')}")
                    print(f"      返回类型: {similar['return_type']}")
                    if similar['parameters']:
                        params = ', '.join(similar['parameters'])
                        print(f"      参数: {params}")
                    else:
                        print(f"      参数: 无")
            else:
                print("   ❌ 未找到相似的API")


def main():
    """主函数"""
    analyzer = LibtiffAPISimilarity()
    results = analyzer.analyze_api_similarity()
    
    if results:
        print("\n✅ 分析完成！")
        
        # 询问是否显示详细结果
        print("\n💡 提示: 详细结果已保存到 test/libtiff_api_similarity_results.json")
        print("   可以查看该文件获取完整的相似度分析结果")
    else:
        print("\n❌ 分析失败")


if __name__ == '__main__':
    main()