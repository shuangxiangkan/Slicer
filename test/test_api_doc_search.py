#!/usr/bin/env python3
"""
API文档搜索测试
测试单个cJSON API的文档搜索功能并打印完整结果

关于条件导入的说明:
条件导入是为了处理可选依赖库。如果直接导入PyPDF2、pdfplumber、python-docx等库，
当这些库未安装时会导致ImportError，使整个程序无法运行。
使用条件导入可以让程序在缺少某些库时仍能正常工作，只是跳过相应格式的文档处理。
这样提高了程序的健壮性和兼容性。
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.repo_analyzer import RepoAnalyzer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)  # 显示更多信息

def print_repo_analyzer_results(results, api_name):
    """打印RepoAnalyzer搜索结果的完整信息"""
    if not results:
        print(f"❌ 未找到 {api_name} 的相关文档")
        return
    
    print(f"\n🔍 找到 {len(results)} 个 {api_name} 的匹配项:\n")
    
    for i, result in enumerate(results, 1):
        file_name = os.path.basename(result['file_path'])
        print(f"🔍 结果 {i}:")
        print(f"   📄 文件: {file_name}")
        print(f"   📁 路径: {result['file_path']}")
        print(f"   📍 行号: {result['line_number']}")
        print(f"   🎯 匹配类型: {result['match_type']}")
        print(f"   📝 上下文 (基于段落提取):")
        print(f"      {result['context']}")
        print("-" * 80)

def test_single_api_documentation():
    """
    测试单个cJSON API的文档搜索并打印完整结果
    使用RepoAnalyzer接口进行搜索
    """
    print("🧪 测试单个cJSON API文档搜索")
    print("=" * 80)
    
    # 切换到项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    try:
        # 测试函数 - 测试cJSON_CreateObject以验证搜索准确性
        test_function = "cJSON_ParseWithOpts"
        config_path = "benchmarks/configs/cjson_config.json"
        
        print(f"🔍 测试API: {test_function}")
        print(f"📁 配置文件: {config_path}")
        print("=" * 80)
        
        # 初始化RepoAnalyzer
        repo_analyzer = RepoAnalyzer(config_path)
        
        print("📊 执行基本分析...")
        result = repo_analyzer.analyze()
        
        if 'error' in result:
            print(f"❌ 分析失败: {result['error']}")
            return
        
        print(f"✅ 基本分析完成")
        
        # 使用RepoAnalyzer的search_api_in_documents接口
        print(f"\n🔍 使用RepoAnalyzer搜索API文档...")
        doc_results = repo_analyzer.search_api_in_documents(test_function)
        
        print(f"\n📋 搜索完成！")
        print_repo_analyzer_results(doc_results, test_function)
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()



def main():
    """
    主函数
    """
    print("🚀 cJSON API文档搜索测试")
    print("\n💡 关于条件导入的说明:")
    print("   条件导入是为了处理可选依赖库。如果直接导入PyPDF2、pdfplumber、")
    print("   python-docx等库，当这些库未安装时会导致ImportError，使整个")
    print("   程序无法运行。使用条件导入可以让程序在缺少某些库时仍能正常")
    print("   工作，只是跳过相应格式的文档处理，提高了程序的健壮性。")
    print("\n" + "=" * 80)
    
    # 测试单个API的文档搜索
    test_single_api_documentation()
    
    print("\n" + "=" * 80)
    print("✅ 测试完成！")
    
    print("\n💡 说明:")
    print("   - 可以修改 test_function 变量来测试不同的cJSON API")
    print("   - 输出包含完整的文件路径、行号、匹配类型和上下文")
    print("   - 支持多种文档格式: .md, .txt, .rst, .pdf, .doc等")

if __name__ == "__main__":
    main()