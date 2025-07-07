#!/usr/bin/env python3
"""
简单的函数注释提取测试
测试cJSON、utf8、zlib三个库的函数注释提取功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from parser import RepoAnalyzer


def test_comments_extraction():
    """测试函数注释提取功能"""
    
    # 测试配置
    test_configs = {
        'cJSON': {
            'config_file': 'test/cjson_config.json',
            'sample_functions': ['cJSON_Parse', 'cJSON_Delete', 'cJSON_ParseWithLength', 'cJSON_GetArraySize']
        },
        'utf8': {
            'config_file': 'test/utf8_config.json', 
            'sample_functions': ['utf8len', 'utf8cpy', 'utf8str', 'utf8chr']
        },
        'zlib': {
            'config_file': 'test/zlib_config.json',
            'sample_functions': ['deflate', 'inflate', 'compress', 'uncompress']
        }
    }
    
    print("=" * 70)
    print("函数注释提取测试")
    print("=" * 70)
    
    for lib_name, config in test_configs.items():
        print(f"\n📚 测试库: {lib_name}")
        print("-" * 50)
        
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
            
            # 获取所有函数
            all_functions = analyzer.get_functions()
            
            # 统计注释情况（基于单个函数实例）
            functions_with_comments = [func for func in all_functions if func.has_comments()]
            functions_without_comments = [func for func in all_functions if not func.has_comments()]
            
            # 获取唯一函数名列表
            unique_function_names = list(set(func.name for func in all_functions))
            
            # 统计完整注释情况（基于函数名，包含声明和定义）
            functions_with_complete_comments = []
            functions_without_complete_comments = []
            
            for func_name in unique_function_names:
                complete_comments = analyzer.get_function_complete_comments(func_name)
                if complete_comments:
                    functions_with_complete_comments.append(func_name)
                else:
                    functions_without_complete_comments.append(func_name)
            
            print(f"\n📊 注释统计:")
            print(f"  • 函数实例总数: {len(all_functions)} 个")
            print(f"  • 唯一函数名: {len(unique_function_names)} 个")
            print(f"  • 有注释的函数实例: {len(functions_with_comments)} 个")
            print(f"  • 有完整注释的函数: {len(functions_with_complete_comments)} 个")
            print(f"  • 完整注释覆盖率: {len(functions_with_complete_comments)/len(unique_function_names)*100:.1f}%")
            
            # 查找示例函数并显示其完整注释
            print(f"\n🔍 示例函数完整注释:")
            found_samples = 0
            
            for sample_func_name in config['sample_functions']:
                if sample_func_name in unique_function_names:
                    found_samples += 1
                    
                    # 获取完整注释和摘要信息
                    complete_comments = analyzer.get_function_complete_comments(sample_func_name)
                    comment_summary = analyzer.get_function_comment_summary(sample_func_name)
                    
                    print(f"\n  {found_samples}. {sample_func_name}")
                    print(f"     实例数: {comment_summary['total_instances']} 个 "
                          f"(声明: {comment_summary['declarations']}, "
                          f"定义: {comment_summary['definitions']})")
                    
                    # 显示各实例的注释情况
                    print(f"     注释情况:")
                    for source in comment_summary['comment_sources']:
                        file_name = os.path.basename(source['file'])
                        status = f"✅ {source['comment_length']}字符" if source['has_comments'] else "❌ 无注释"
                        print(f"       • {source['type']} ({file_name}:{source['line']}): {status}")
                    
                    if complete_comments:
                        print(f"     完整注释长度: {len(complete_comments)} 字符")
                        print(f"     完整注释内容:")
                        
                        # 显示完整注释内容，每行前面加上缩进
                        for line in complete_comments.split('\n'):
                            if line.strip():
                                print(f"       {line}")
                            else:
                                print()
                    else:
                        print(f"     ❌ 该函数没有任何注释")
                
                if found_samples >= 3:  # 只显示前3个找到的函数
                    break
            
            if found_samples == 0:
                print(f"     ⚠️  未找到示例函数: {config['sample_functions']}")
            
            # 显示注释最丰富的函数（基于完整注释）
            if functions_with_complete_comments:
                print(f"\n📝 注释最丰富的函数 (前3个):")
                
                # 获取每个函数的完整注释并按长度排序
                function_comment_data = []
                for func_name in functions_with_complete_comments:
                    complete_comments = analyzer.get_function_complete_comments(func_name)
                    comment_summary = analyzer.get_function_comment_summary(func_name)
                    function_comment_data.append({
                        'name': func_name,
                        'complete_comments': complete_comments,
                        'comment_summary': comment_summary,
                        'length': len(complete_comments)
                    })
                
                # 按注释长度排序
                sorted_functions = sorted(function_comment_data, 
                                        key=lambda f: f['length'], 
                                        reverse=True)
                
                for i, func_data in enumerate(sorted_functions[:3], 1):
                    comments = func_data['complete_comments']
                    summary = func_data['comment_summary']
                    
                    # 创建预览（显示前100个字符）
                    preview = comments.replace('\n', ' ').strip()
                    if len(preview) > 100:
                        preview = preview[:100] + "..."
                    
                    print(f"  {i}. {func_data['name']}")
                    print(f"     实例数: {summary['total_instances']} 个")
                    print(f"     完整注释长度: {func_data['length']} 字符")
                    print(f"     注释来源: ", end="")
                    
                    # 显示注释来源
                    sources = []
                    for source in summary['comment_sources']:
                        if source['has_comments']:
                            sources.append(f"{source['type']}")
                    print(" + ".join(sources) if sources else "无")
                    
                    print(f"     预览: {preview}")
                    print()
                    
        except Exception as e:
            print(f"❌ 分析失败: {e}")
    
    print("\n" + "=" * 70)
    print("测试完成")


if __name__ == '__main__':
    test_comments_extraction() 