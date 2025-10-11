#!/usr/bin/env python3
"""
简单的API提取测试
测试cJSON、utf8、zlib三个库的API函数提取功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from parser import RepoAnalyzer


def test_api_extraction():
    """测试API提取功能"""
    
    # 测试配置
    # test_configs = {
    #     'cJSON': {
    #         'config_file': 'benchmarks/configs/cjson_config.json',
    #         'api_keywords': ['CJSON_PUBLIC'],
    #         'api_prefix': 'cJSON'
    #     }
    #     ,
    #     'miniz': {
    #         'config_file': 'benchmarks/configs/miniz_config.json', 
    #         'api_keywords': ['MINIZ_EXPORT'],
    #         'api_prefix': 'mz_'
    #     },
    #     'zlib': {
    #         'config_file': 'benchmarks/configs/zlib_config.json',
    #         'api_keywords': ['ZEXPORT'],
    #         'api_prefix': None  # zlib没有统一前缀
    #     }
    # }
    
    test_configs = {
        'mocklib': {
            'config_file': 'benchmarks/configs/mocklib_config.json',
            'api_keywords': ['MOCKLIB_API'],
            'api_prefix': 'mock_'
        }
        ,
        'libucl': {
            'config_file': 'benchmarks/configs/libucl_config.json',
            'api_keywords': ['UCL_EXTERN'],
            'api_prefix': 'ucl_'
        }
    }
    
    print("=" * 60)
    print("API提取功能测试")
    print("=" * 60)
    
    for lib_name, config in test_configs.items():
        print(f"\n📚 测试库: {lib_name}")
        print("-" * 40)
        
        # 检查配置文件是否存在
        if not os.path.exists(config['config_file']):
            print(f"❌ 配置文件不存在: {config['config_file']}")
            continue
        
        try:
            # 初始化分析器
            analyzer = RepoAnalyzer(config['config_file'])
            
            # 分析代码
            print("正在分析代码...")
            result = analyzer.analyze()
            print(f"✅ 分析完成，总共找到 {result['total_functions']} 个函数")
            
            # 提取API函数
            header_files = analyzer.config_parser.get_header_files() if analyzer.config_parser else None
            api_prefix = config.get('api_prefix')
            
            for keyword in config['api_keywords']:
                print(f"\n🔍 搜索关键字: '{keyword}'")
                if header_files:
                    print(f"📁 限制在头文件: {header_files}")
                if api_prefix:
                    print(f"🏷️  限制函数前缀: '{api_prefix}'")
                    
                api_functions = analyzer.get_api_functions(keyword, api_prefix=api_prefix, header_files=header_files)
                
                if api_functions:
                    print(f"找到 {len(api_functions)} 个API函数:")
                    
                    for i, func in enumerate(api_functions):
                        func_type = "声明" if func.is_declaration else "定义"
                        print(f"  {i+1:2d}. {func.name} ({func_type})")
                        
                else:
                    print("未找到包含该关键字的函数")
                    
        except Exception as e:
            print(f"❌ 分析失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")


if __name__ == '__main__':
    test_api_extraction()